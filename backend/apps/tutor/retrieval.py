"""Find the passages of Iga's own lessons that best match a question, so Santa answers from them.

Every published lesson (in English, and in French where it has been translated) is cut into passages at its
headings and ranked with BM25, the classic search-engine formula: words that are rare across the lessons
count more, and short passages are not drowned out by long ones. Passages from the student's grade, the
chosen subject and the open lesson rank higher; lessons for students two or more years ahead rank lower.
The index lives in each server process's memory; it is built on first use and again after a lesson changes
(a signal changes a version kept in the shared cache).
"""

import logging
import math
import re
import threading
import time
import unicodedata
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass

from django.core.cache import cache

from apps.core.constants import ContentStatus
from apps.curriculum.models import Lesson
from apps.curriculum.views import visible_lessons
from apps.schools import access

log = logging.getLogger(__name__)

VERSION_KEY = "tutor:lesson-index-version"
# Rebuild now and then even without a signal (a bulk update in a migration sends none).
REBUILD_EVERY = 15 * 60
PASSAGE_CHARS = 1200
K1, B = 1.4, 0.75
# A passage is offered only when it has a good share of the question's meaningful words (weighted by
# rarity), so "who won the match yesterday" doesn't bring up a lesson that mentions football once.


def _plain(text):
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


STOPWORDS = {
    _plain(w)
    for w in (
        "a an the and or but if of to in on at by for with from as is are was were be been being it its this that these "
        "those there here what which who whom whose when where why how do does did done can could would should will shall "
        "may might must i me my we our you your he she they them their his her not no yes so than then too very just also "
        "into about over under more most some any all each other such only own same up down out off again once please "
        "tell explain give show help make let know want need like get use find work way thing things"
        # French
        " le la les un une des du de d l et ou mais si à au aux en dans sur par pour avec sans ce cet cette ces se sa son "
        "ses leur leurs est sont été être a ont avoir que qui quoi dont où comment pourquoi quand je tu il elle nous vous "
        "ils elles me te moi toi lui y ne pas plus moins très aussi comme entre sous chez donc car ni ça cela ceci quel "
        "quelle quels quelles c qu j n s m t est-ce svp expliquez expliquer donnez montrez aidez peux pouvez faire"
        # Words about studying rather than a topic ("explain this lesson more simply", "give me an example")
        " lesson lessons simply simpler example examples question questions quiz understand step steps again another "
        "short hint idea answer answers right wrong correct why mean means meaning called "
        "lecon lecons simplement exemple exemples comprendre etape etapes encore autre indice idee reponse reponses "
        "juste faux bonne mauvaise sert servir veut dire signifie appelle"
    ).split()
}
LATEX_COMMAND = re.compile(r"\\[a-zA-Z]+")
WORD = re.compile(r"[a-z0-9]+")


def _stem(word):
    # A light trim so "fractions"/"fraction" and "équations"/"equation" meet; enough for short lessons.
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    return word


def tokens(text):
    words = WORD.findall(_plain(LATEX_COMMAND.sub(" ", text)))
    return [_stem(w) for w in words if w not in STOPWORDS and (len(w) > 1 or w.isdigit())]


@dataclass(frozen=True)
class Passage:
    lesson_id: int
    slug: str
    language: str
    title: str  # the lesson's title in this language
    heading: str  # the section's heading ("" for the introduction)
    text: str
    subject_id: int
    subject: str
    grade: str
    is_free: bool
    position: int  # order in its lesson


SIM_BLOCK = re.compile(r"^```sim\b.*?^```[ \t]*$", re.S | re.M)
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
HEADING = re.compile(r"^#{1,4}\s+(.+?)\s*#*\s*$")


def clean(body):
    """Lesson Markdown without the parts that mean nothing in a chat: simulation blocks, images, link targets."""
    body = SIM_BLOCK.sub("", body or "")
    body = IMAGE.sub("", body)
    return LINK.sub(r"\1", body)


def _balanced(text):
    """Close a code block or display maths left open where a long section was cut."""
    if text.count("```") % 2:
        text += "\n```"
    if text.count("$$") % 2:
        text += "\n$$"
    return text


def split(body):
    """[(heading, text)] for each section of a lesson, long sections cut at paragraph breaks."""
    sections, heading, lines = [], "", []
    for line in clean(body).splitlines():
        match = HEADING.match(line)
        if match and not (lines and sum(1 for x in lines if x.startswith("```")) % 2):
            sections.append((heading, "\n".join(lines).strip()))
            heading, lines = match.group(1).strip(), []
        else:
            lines.append(line)
    sections.append((heading, "\n".join(lines).strip()))
    passages = []
    for heading, text in sections:
        if not text:
            continue
        chunk = ""
        for paragraph in re.split(r"\n\s*\n", text):
            if chunk and len(chunk) + len(paragraph) > PASSAGE_CHARS:
                passages.append((heading, _balanced(chunk.strip())))
                chunk = ""
            chunk += paragraph + "\n\n"
        if chunk.strip():
            passages.append((heading, _balanced(chunk.strip()[: PASSAGE_CHARS * 2])))
    return passages


def lesson_passages(lesson, language, title, body):
    unit = lesson.unit
    return [
        Passage(
            lesson_id=lesson.id,
            slug=lesson.slug,
            language=language,
            title=title,
            heading=heading,
            text=text,
            subject_id=unit.subject_id,
            subject=unit.subject.localized_name(language),
            grade=unit.grade,
            is_free=lesson.is_free,
            position=i,
        )
        for i, (heading, text) in enumerate(split(body))
    ]


class Index:
    """BM25 over passages."""

    def __init__(self, passages):
        self.passages = passages
        self.postings = defaultdict(list)  # term -> [(passage number, count)]
        self.lengths = []
        for i, passage in enumerate(passages):
            # Words in the title and heading say what a passage is about, so they count twice.
            counts = Counter(tokens(f"{passage.title} {passage.heading} " * 2 + passage.text))
            self.lengths.append(sum(counts.values()))
            for term, count in counts.items():
                self.postings[term].append((i, count))
        self.average = (sum(self.lengths) / len(self.lengths)) if self.lengths else 1.0
        n = len(passages)
        self.idf = {term: math.log(1 + (n - len(hits) + 0.5) / (len(hits) + 0.5)) for term, hits in self.postings.items()}
        # A word no lesson uses: as rare as can be.
        self.unseen_idf = math.log(1 + (n + 0.5) / 0.5)

    def _term_score(self, idf, count, length):
        return idf * count * (K1 + 1) / (count + K1 * (1 - B + B * length / self.average))

    def scores(self, query_terms):
        """{passage number: score} for the passages that share enough of the query's words."""
        terms = set(query_terms)
        total = sum(self.idf.get(term, self.unseen_idf) for term in terms)
        scores, covered = defaultdict(float), defaultdict(float)
        for term in terms:
            idf = self.idf.get(term)
            for i, count in self.postings.get(term, ()):
                scores[i] += self._term_score(idf, count, self.lengths[i])
                covered[i] += idf
        # Short questions need half their meaning matched; long ones (a question with a quiz prompt) less.
        needed = total * min(0.5, 3 / max(len(terms), 1))
        return {i: score for i, score in scores.items() if covered[i] >= needed}

    def score_passage(self, query_terms, passage):
        """The score of a passage that isn't in the index (the open lesson may be a draft)."""
        counts = Counter(tokens(f"{passage.title} {passage.heading} " * 2 + passage.text))
        length = sum(counts.values()) or 1
        return sum(
            self._term_score(self.idf.get(term, self.unseen_idf), counts[term], length)
            for term in set(query_terms)
            if counts.get(term)
        )


def load_passages():
    lessons = (
        Lesson.objects.filter(status=ContentStatus.PUBLISHED)
        .select_related("unit__subject")
        .prefetch_related("translations")
        .order_by("id")
    )
    passages = []
    for lesson in lessons:
        passages += lesson_passages(lesson, "en", lesson.title, lesson.body)
        for translation in lesson.translations.all():
            passages += lesson_passages(lesson, translation.language, translation.title, translation.body)
    return passages


_lock = threading.Lock()
_state = {"index": None, "version": None, "built": 0.0}


def lessons_changed(**kwargs):
    """Signal receiver: a lesson, translation, unit or subject was saved or deleted."""
    try:
        cache.set(VERSION_KEY, uuid.uuid4().hex, None)
    except Exception:  # noqa: BLE001 - saving a lesson must work even when the cache is down
        log.warning("Could not mark the lesson index as changed", exc_info=True)
        _state["index"] = None


def _current_version():
    try:
        version = cache.get(VERSION_KEY)
        if version is None:
            cache.add(VERSION_KEY, uuid.uuid4().hex, None)
            version = cache.get(VERSION_KEY)
        return version
    except Exception:  # noqa: BLE001
        return None


def get_index():
    version = _current_version()

    def fresh():
        return (
            _state["index"] is not None
            and version is not None
            and _state["version"] == version
            and time.monotonic() - _state["built"] < REBUILD_EVERY
        )

    if not fresh():
        with _lock:
            if not fresh():
                started = time.monotonic()
                _state.update(index=Index(load_passages()), version=version, built=time.monotonic())
                log.info(
                    "Built Santa's lesson index: %s passages in %.2f s", len(_state["index"].passages), time.monotonic() - started
                )
    return _state["index"]


def _readable_lessons(user):
    """Ids of the published lessons this user may read in full."""
    lessons = visible_lessons(user).filter(status=ContentStatus.PUBLISHED)
    if not access.has_premium(user):
        lessons = lessons.filter(is_free=True)
    return set(lessons.values_list("id", flat=True))


def _level(grade):
    """3 for "S3"; None for anything else."""
    match = re.fullmatch(r"S([1-6])", grade or "")
    return int(match.group(1)) if match else None


def _fill(candidates, budget, per_lesson):
    """Take passages in order until the budget (in characters) is used, at most `per_lesson` from one lesson."""
    chosen, used, taken = [], 0, Counter()
    for passage in candidates:
        if taken[passage.lesson_id] >= per_lesson or used + len(passage.text) > budget:
            continue
        chosen.append(passage)
        used += len(passage.text)
        taken[passage.lesson_id] += 1
    return chosen


def search(user, query, language, *, lesson=None, subject_id=None, budget=2800, lesson_budget=2000, limit=4):
    """The passages to give Santa for this question: (from the open lesson, from other lessons).

    `lesson` is the lesson the student has open, quoted in `language` (its passages come first, in reading
    order; when the question matches none of its words, its beginning). Other lessons must be ones the
    student may read, in the reply language when it matches there too; the student's grade and the subject
    rank higher."""
    index = get_index()
    terms = tokens(query)
    own = []
    if lesson is not None:
        translation = lesson.translations.filter(language=language).first() if language != "en" else None
        title, body = (translation.title, translation.body) if translation else (lesson.title, lesson.body)
        passages = lesson_passages(lesson, language if translation else "en", title, body)
        scored = {p.position: index.score_passage(terms, p) for p in passages} if terms else {}
        matched = sorted((p for p in passages if scored.get(p.position, 0) > 0), key=lambda p: -scored[p.position])
        unmatched = [p for p in passages if scored.get(p.position, 0) <= 0]
        own = _fill(matched + unmatched, lesson_budget, per_lesson=len(passages))
        own.sort(key=lambda p: p.position)
        subject_id = subject_id or lesson.unit.subject_id

    if not terms:
        return own, []
    readable = _readable_lessons(user)
    grade = getattr(user, "grade", "") or ""
    level = _level(grade)
    matches = {
        i: score
        for i, score in index.scores(terms).items()
        if index.passages[i].lesson_id in readable and (lesson is None or index.passages[i].lesson_id != lesson.id)
    }
    # A lesson that matches in the reply language is quoted in that language only, not the same section twice.
    in_reply_language = {index.passages[i].lesson_id for i in matches if index.passages[i].language == language}
    weighted = []
    for i, score in matches.items():
        passage = index.passages[i]
        weight = 1.0
        if passage.language != language:
            if passage.lesson_id in in_reply_language:
                continue
            weight *= 0.8
        if grade and passage.grade == grade:
            weight *= 1.25
        elif level and (_level(passage.grade) or 0) > level + 1:
            weight *= 0.6  # written for students two or more years ahead
        if subject_id and passage.subject_id == subject_id:
            weight *= 1.5
        weighted.append((score * weight, i))
    weighted.sort(reverse=True)
    others = _fill([index.passages[i] for _, i in weighted], budget - sum(len(p.text) for p in own), per_lesson=2)
    return own, others[:limit]


def sources(passages):
    """The lessons the passages came from, once each, for the links under an answer."""
    seen, out = set(), []
    for passage in passages:
        if passage.lesson_id in seen:
            continue
        seen.add(passage.lesson_id)
        out.append(
            {
                "slug": passage.slug,
                "title": passage.title,
                "section": passage.heading,
                "subject": passage.subject,
                "grade": passage.grade,
                "url": f"/lessons/{passage.slug}",
            }
        )
    return out
