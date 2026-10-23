"""What a class gets wrong in one unit: averages, misconceptions, hardest questions, students needing help.

Only the class's current students count, through marked answers of marked attempts submitted within
TEACHING_LOOKBACK_DAYS; for each student and question only the latest such answer counts, and it is correct only
with full marks. A question's results count once TEACHING_MIN_STUDENTS students answered it."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from apps.accounts.models import User
from apps.assessments.models import Answer, Attempt, Question
from apps.classroom.analytics import class_unit_scores
from apps.core.constants import ContentStatus

MAX_MISCONCEPTIONS = 3
MAX_HARDEST = 5
MAX_OTHER_UNITS = 5
MAX_NEEDING_HELP = 10
HELP_MIN_ANSWERS = 3
HELP_BELOW_AVERAGE = 50


def current_students(classroom):
    return User.objects.filter(enrollments__classroom=classroom, enrollments__active=True).distinct()


def unit_label(unit, lang):
    title = unit.title_fr if lang == "fr" and unit.title_fr else unit.title
    return f"{unit.grade} Unit {unit.number}: {title}"


def _since():
    return timezone.now() - timedelta(days=settings.TEACHING_LOOKBACK_DAYS)


@dataclass(frozen=True)
class QStat:
    question: Question
    answered: int
    correct: int
    choice_counts: dict = field(default_factory=dict)

    @property
    def correct_share(self):
        return self.correct / self.answered if self.answered else 0

    def most_picked_wrong(self):
        """(the wrong choice most students picked, the share of those who answered), or None."""
        if self.question.type not in Question.CHOICE_TYPES or not self.answered:
            return None
        picked = [c for c in self.question.choices.all() if not c.is_correct and self.choice_counts.get(c.id)]
        if not picked:
            return None
        choice = max(picked, key=lambda c: (self.choice_counts[c.id], -c.id))
        return choice, self.choice_counts[choice.id] / self.answered


def _latest_answers(classroom, units):
    """[Answer]: each current student's latest counted answer to each published question of `units`, each with
    `student_id` (the users themselves are not loaded)."""
    answers = (
        Answer.objects.filter(
            attempt__user__in=current_students(classroom),
            attempt__status=Attempt.Status.MARKED,
            attempt__submitted_at__gte=_since(),
            marks_awarded__isnull=False,
            question__unit__in=units,
            question__status=ContentStatus.PUBLISHED,
        )
        .annotate(student_id=F("attempt__user_id"))
        .select_related("question")
        .prefetch_related("selected_choices", "question__choices")
        .order_by("attempt__submitted_at", "id")
    )
    latest = {}
    for answer in answers:
        latest[(answer.student_id, answer.question_id)] = answer
    return list(latest.values())


def _is_correct(answer):
    return answer.marks_awarded == answer.question.marks


def _stats(answers):
    """{question id: QStat} from latest answers."""
    by_question = defaultdict(list)
    for answer in answers:
        by_question[answer.question_id].append(answer)
    stats = {}
    for question_id, question_answers in by_question.items():
        counts = Counter(choice.id for answer in question_answers for choice in answer.selected_choices.all())
        stats[question_id] = QStat(
            question=question_answers[0].question,
            answered=len(question_answers),
            correct=sum(1 for answer in question_answers if _is_correct(answer)),
            choice_counts=dict(counts),
        )
    return stats


def question_stats(classroom, unit):
    """{question id: QStat} for the questions of `unit` the class's current students answered."""
    return _stats(_latest_answers(classroom, [unit]))


def _counted(stats):
    return [s for s in stats.values() if s.answered >= settings.TEACHING_MIN_STUDENTS]


def _misconceptions(counted):
    """[(QStat, wrong choice, share)] for the questions where enough of the class picked the same wrong option,
    most shared first."""
    found = []
    for stat in counted:
        picked = stat.most_picked_wrong()
        if picked and picked[1] >= settings.TEACHING_MISCONCEPTION_SHARE:
            found.append((stat, *picked))
    found.sort(key=lambda item: (-item[2], -item[0].answered, item[0].question.id))
    return found[:MAX_MISCONCEPTIONS]


def _correct_text(question):
    return " / ".join(c.text for c in question.choices.all() if c.is_correct)


def unit_insight(classroom, unit, lang="en"):
    counted = _counted(question_stats(classroom, unit))
    misconceptions = [
        {
            "question_id": stat.question.id,
            "prompt": stat.question.prompt,
            "wrong_choice": choice.text,
            "share": round(share, 2),
            "answered": stat.answered,
            "correct": _correct_text(stat.question),
            "explanation": stat.question.explanation,
        }
        for stat, choice, share in _misconceptions(counted)
    ]

    hardest = [
        {
            "question_id": stat.question.id,
            "prompt": stat.question.prompt,
            "correct_share": round(stat.correct_share, 2),
            "answered": stat.answered,
        }
        for stat in sorted(counted, key=lambda s: (s.correct_share, -s.answered, s.question.id))[:MAX_HARDEST]
    ]

    scores = class_unit_scores(classroom, current_students(classroom), since=_since())
    return {
        "data_enough": bool(counted),
        "average": next((s.average for s in scores if s.unit.id == unit.id), None),
        "other_units": [{"label": unit_label(s.unit, lang), "average": s.average} for s in scores if s.unit.id != unit.id][
            :MAX_OTHER_UNITS
        ],
        "misconceptions": misconceptions,
        "hardest": hardest,
    }


def unit_overview(classroom, units):
    """{unit id: {"answered", "misconceptions_found"}} for the `units` the class answered, from one pass over its
    answers: how many current students answered, and how many misconceptions a pack would find."""
    by_unit = defaultdict(list)
    for answer in _latest_answers(classroom, units):
        by_unit[answer.question.unit_id].append(answer)
    return {
        unit_id: {
            "answered": len({answer.student_id for answer in answers}),
            "misconceptions_found": len(_misconceptions(_counted(_stats(answers)))),
        }
        for unit_id, answers in by_unit.items()
    }


def students_needing_help(classroom, unit):
    """Current students with at least HELP_MIN_ANSWERS answers in `unit` averaging below HELP_BELOW_AVERAGE%,
    lowest first. Computed when asked; never stored in a pack."""
    totals = defaultdict(lambda: [0, 0.0, 0.0])  # answered, got, possible
    for answer in _latest_answers(classroom, [unit]):
        row = totals[answer.student_id]
        row[0] += 1
        row[1] += float(answer.marks_awarded)
        row[2] += float(answer.question.marks)
    found = []
    for student_id, (answered, got, possible) in totals.items():
        if answered < HELP_MIN_ANSWERS or not possible:
            continue
        average = round(got / possible * 100, 1)
        if average < HELP_BELOW_AVERAGE:
            found.append({"id": student_id, "average": average, "answered": answered})
    found = sorted(found, key=lambda row: (row["average"], row["id"]))[:MAX_NEEDING_HELP]
    students = User.objects.in_bulk([row["id"] for row in found])
    return [
        {
            "id": row["id"],
            "display_name": students[row["id"]].display_name,
            "average": row["average"],
            "answered": row["answered"],
        }
        for row in found
    ]
