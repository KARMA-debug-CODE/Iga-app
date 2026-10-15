from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.core.constants import ContentStatus
from apps.core.serializers import SaveChangedFieldsMixin
from apps.core.text import CleanCharField
from apps.core.utils import request_language, serializer_language
from apps.schools import access
from apps.schools.downloads import signed_download_url

from . import services
from .models import Attempt, Choice, ExamPaper, Question, Quiz, QuizQuestion


class ChoiceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text", "is_correct", "order"]
        read_only_fields = ["id"]


class QuestionSerializer(SaveChangedFieldsMixin, serializers.ModelSerializer):
    """Teacher-facing: includes the answers. Never use this for students."""

    choices = ChoiceWriteSerializer(many=True, required=False)
    subject_code = serializers.CharField(source="subject.code", read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "subject",
            "subject_code",
            "grade",
            "unit",
            "type",
            "prompt",
            "explanation",
            "marks",
            "numeric_answer",
            "numeric_tolerance",
            "accepted_answers",
            "marking_guide",
            "difficulty",
            "source",
            "status",
            "choices",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate_accepted_answers(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list) or not all(isinstance(a, str) for a in value):
            raise serializers.ValidationError(_("Give a list of accepted answers (text)."))
        cleaned = [a.strip() for a in value if a.strip()]
        if len(cleaned) > 50 or any(len(a) > 200 for a in cleaned):
            raise serializers.ValidationError(_("Use at most 50 accepted answers of up to 200 characters each."))
        return cleaned

    def validate(self, attrs):
        qtype = attrs.get("type", getattr(self.instance, "type", None))
        choices = attrs.get("choices")
        if qtype in Question.CHOICE_TYPES and choices is not None:
            if len(choices) < 2:
                raise serializers.ValidationError({"choices": _("Add at least two options.")})
            correct = sum(1 for c in choices if c.get("is_correct"))
            if correct == 0:
                raise serializers.ValidationError({"choices": _("Mark at least one option as correct.")})
            if qtype != Question.Type.MULTI and correct > 1:
                raise serializers.ValidationError({"choices": _("Only one option can be correct.")})
        elif qtype in Question.CHOICE_TYPES and self.instance is None:
            raise serializers.ValidationError({"choices": _("Multiple-choice questions need options.")})
        if qtype == Question.Type.NUMERIC:
            answer = attrs.get("numeric_answer", getattr(self.instance, "numeric_answer", None))
            if answer is None:
                raise serializers.ValidationError({"numeric_answer": _("Numeric questions need an answer.")})
        if attrs.get("source") == Question.Source.PAST_PAPER and not self.context["request"].user.is_platform_admin:
            raise serializers.ValidationError({"source": _("Only administrators can add official past-paper questions.")})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        choices = validated_data.pop("choices", [])
        question = Question.objects.create(**validated_data)
        for i, choice in enumerate(choices):
            Choice.objects.create(
                question=question, order=choice.get("order", i), text=choice["text"], is_correct=choice.get("is_correct", False)
            )
        return question

    ANSWER_KEY_FIELDS = ("type", "marks", "numeric_answer", "numeric_tolerance", "accepted_answers")

    def _keep_answer_key(self, instance, validated_data, choices):
        """Once students have answered, the marking must not change under them.

        Wording can still be fixed (prompt, explanation, option text); the answer key can't.
        Returns True when option texts should be updated in place.
        """
        changed = [f for f in self.ANSWER_KEY_FIELDS if f in validated_data and validated_data[f] != getattr(instance, f)]
        if changed:
            raise serializers.ValidationError(
                {
                    changed[0]: _(
                        "Students have already answered this question, so its answer can't change. Make a new question instead."
                    )
                }
            )
        if choices is None:
            return False
        current = list(instance.choices.order_by("order", "id"))
        same_key = len(current) == len(choices) and all(
            bool(c.get("is_correct")) == old.is_correct for c, old in zip(choices, current, strict=True)
        )
        if not same_key:
            raise serializers.ValidationError(
                {
                    "choices": _(
                        "Students have already answered this question, so its options can't change. Make a new question instead."
                    )
                }
            )
        for old, new in zip(current, choices, strict=True):
            if old.text != new["text"]:
                old.text = new["text"]
                old.save(update_fields=["text"])
        return True

    @transaction.atomic
    def update(self, instance, validated_data):
        choices = validated_data.pop("choices", None)
        if instance.answers.exists() and self._keep_answer_key(instance, validated_data, choices):
            choices = None  # option texts already updated in place; keep the same option rows
        question = super().update(instance, validated_data)
        if choices is not None:
            question.choices.all().delete()
            for i, choice in enumerate(choices):
                Choice.objects.create(
                    question=question,
                    order=choice.get("order", i),
                    text=choice["text"],
                    is_correct=choice.get("is_correct", False),
                )
        return question


def _viewer(serializer):
    request = serializer.context.get("request")
    return request.user if request else None


def paper_is_free(paper):
    return bool(paper.quiz_id and paper.quiz.is_free)


def paper_link(viewer, paper, kind, request=None):
    """Link to a paper or marking guide: withheld when locked; uploaded files go through a
    short-lived signed download instead of a public /media URL."""
    if not (paper_is_free(paper) or access.has_premium(viewer)):
        return None
    file = paper.paper_file if kind == "paper" else paper.marking_guide_file
    if file:
        return signed_download_url(request, paper, kind, viewer)
    return (paper.paper_url if kind == "paper" else paper.marking_guide_url) or None


class ExamPaperSerializer(serializers.ModelSerializer):
    subject_code = serializers.CharField(source="subject.code", read_only=True)
    subject_name = serializers.SerializerMethodField()
    subject_icon = serializers.CharField(source="subject.icon", read_only=True)
    paper_link = serializers.SerializerMethodField()
    marking_guide_link = serializers.SerializerMethodField()
    locked = serializers.SerializerMethodField()

    class Meta:
        model = ExamPaper
        fields = [
            "id",
            "subject",
            "subject_code",
            "subject_name",
            "subject_icon",
            "level",
            "year",
            "paper_code",
            "title",
            "is_official",
            "source_note",
            "paper_link",
            "marking_guide_link",
            "quiz",
            "locked",
        ]

    def get_locked(self, paper):
        return not (paper_is_free(paper) or access.has_premium(_viewer(self)))

    def get_subject_name(self, paper):
        return paper.subject.localized_name(serializer_language(self))

    def get_paper_link(self, paper):
        return paper_link(_viewer(self), paper, "paper", self.context.get("request"))

    def get_marking_guide_link(self, paper):
        return paper_link(_viewer(self), paper, "marking_guide", self.context.get("request"))


class QuizSummarySerializer(serializers.ModelSerializer):
    subject = serializers.SerializerMethodField()
    question_count = serializers.IntegerField(read_only=True)
    total_marks = serializers.DecimalField(max_digits=7, decimal_places=2, read_only=True)
    my_best = serializers.SerializerMethodField()
    my_attempts = serializers.SerializerMethodField()
    exam_paper = serializers.SerializerMethodField()
    locked = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "subject",
            "grade",
            "unit",
            "kind",
            "time_limit_minutes",
            "feedback_mode",
            "max_attempts",
            "status",
            "question_count",
            "total_marks",
            "my_best",
            "my_attempts",
            "exam_paper",
            "author",
            "is_free",
            "locked",
        ]

    def get_locked(self, quiz):
        return not access.can_open(_viewer(self), quiz)

    def get_subject(self, quiz):
        s = quiz.subject
        request = self.context.get("request")
        lang = request_language(request) if request is not None else "en"
        return {"code": s.code, "name": s.localized_name(lang), "icon": s.icon, "color": s.color}

    def _my_attempts(self, quiz):
        stats = self.context.get("attempt_stats", {})
        return stats.get(quiz.id, {"count": 0, "best": None})

    def get_my_best(self, quiz):
        return self._my_attempts(quiz)["best"]

    def get_my_attempts(self, quiz):
        return self._my_attempts(quiz)["count"]

    def get_exam_paper(self, quiz):
        paper = getattr(quiz, "exam_paper", None)
        if not paper:
            return None
        return {
            "id": paper.id,
            "year": paper.year,
            "level": paper.level,
            "is_official": paper.is_official,
            "paper_code": paper.paper_code,
        }


class QuizWriteSerializer(SaveChangedFieldsMixin, serializers.ModelSerializer):
    question_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "subject",
            "grade",
            "unit",
            "kind",
            "time_limit_minutes",
            "shuffle_questions",
            "shuffle_choices",
            "feedback_mode",
            "max_attempts",
            "status",
            "is_free",
            "question_ids",
        ]
        read_only_fields = ["id"]

    def validate_kind(self, value):
        if value == Quiz.Kind.PAST_PAPER and not self.context["request"].user.is_platform_admin:
            raise serializers.ValidationError(_("Only administrators can publish past papers."))
        return value

    def validate_status(self, value):
        if value == ContentStatus.PUBLISHED and not self.context["request"].user.is_platform_admin:
            return ContentStatus.REVIEW  # public library needs admin approval; classes can still use it
        return value

    def validate_question_ids(self, ids):
        user = self.context["request"].user
        allowed = Question.objects.filter(id__in=ids)
        if not user.is_platform_admin:
            allowed = allowed.filter(Q(status=ContentStatus.PUBLISHED) | Q(author=user))
            if not access.has_premium(user):
                allowed = allowed.exclude(services.library_questions_q())
        found = set(allowed.values_list("id", flat=True))
        missing = [i for i in ids if i not in found]
        if missing:
            raise serializers.ValidationError(_("Unknown or private questions: %(ids)s") % {"ids": missing})
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError(_("A question appears twice."))
        return ids

    def _set_questions(self, quiz, ids):
        QuizQuestion.objects.filter(quiz=quiz).delete()
        QuizQuestion.objects.bulk_create([QuizQuestion(quiz=quiz, question_id=qid, order=i) for i, qid in enumerate(ids)])

    @transaction.atomic
    def create(self, validated_data):
        ids = validated_data.pop("question_ids", [])
        quiz = Quiz.objects.create(**validated_data)
        self._set_questions(quiz, ids)
        return quiz

    @transaction.atomic
    def update(self, instance, validated_data):
        ids = validated_data.pop("question_ids", None)
        quiz = super().update(instance, validated_data)
        if ids is not None:
            self._set_questions(quiz, ids)
        return quiz


class AttemptSerializer(serializers.ModelSerializer):
    """Student view of an attempt. Solutions only appear once allowed."""

    quiz = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()
    percentage = serializers.FloatField(read_only=True)
    server_now = serializers.SerializerMethodField()
    student = serializers.CharField(source="user.display_name", read_only=True)

    class Meta:
        model = Attempt
        fields = [
            "id",
            "quiz",
            "student",
            "status",
            "started_at",
            "deadline",
            "server_now",
            "submitted_at",
            "score",
            "max_score",
            "percentage",
            "questions",
        ]

    def get_server_now(self, attempt):
        return timezone.now()

    def _full_solutions(self, attempt):
        """Explanations and marking guides are premium: shown when the viewer may open the quiz."""
        if not hasattr(self, "_solutions_cache"):
            self._solutions_cache = {}
        if attempt.quiz_id not in self._solutions_cache:
            self._solutions_cache[attempt.quiz_id] = access.can_open(_viewer(self), attempt.quiz)
        return self._solutions_cache[attempt.quiz_id]

    def get_quiz(self, attempt):
        q = attempt.quiz
        paper = getattr(q, "exam_paper", None)
        return {
            "id": q.id,
            "title": q.title,
            "kind": q.kind,
            "feedback_mode": q.feedback_mode,
            "time_limit_minutes": q.time_limit_minutes,
            "subject": {
                "code": q.subject.code,
                "name": q.subject.localized_name(serializer_language(self)),
                "icon": q.subject.icon,
            },
            "grade": q.grade,
            "marking_guide_link": self._marking_guide(attempt, paper) if attempt.status != Attempt.Status.IN_PROGRESS else None,
            "locked": not self._full_solutions(attempt),
        }

    def _marking_guide(self, attempt, paper):
        if paper is None or not self._full_solutions(attempt):
            return None
        return paper_link(_viewer(self), paper, "marking_guide", self.context.get("request"))

    def get_questions(self, attempt):
        full = self._full_solutions(attempt)
        viewer = _viewer(self)
        if not full and (viewer is None or viewer.id != attempt.user_id):
            # A teacher (or anyone but the student) without the subscription sees the score only:
            # the questions and answer key of a premium quiz stay locked.
            return []
        questions = {q.id: q for q in Question.objects.filter(id__in=attempt.question_order).prefetch_related("choices")}
        answers = {a.question_id: a for a in attempt.answers.prefetch_related("selected_choices")}
        result = []
        for number, qid in enumerate(attempt.question_order, start=1):
            question = questions.get(qid)
            if question is None:
                continue
            answer = answers.get(qid)
            item = {
                "id": question.id,
                "number": number,
                "type": question.type,
                "prompt": question.prompt,
                "marks": question.marks,
                "teacher_marked": question.needs_manual_marking,
                "choices": [{"id": c.id, "text": c.text} for c in services.ordered_choices(attempt, question)],
                "answer": None,
                "solution": None,
            }
            if answer:
                item["answer"] = {
                    "choice_ids": [c.id for c in answer.selected_choices.all()],
                    "text": answer.text_answer,
                    "numeric": answer.numeric_answer,
                    "checked": answer.checked,
                }
            if services.can_see_solutions(attempt, answer):
                item["solution"] = {
                    "correct_choice_ids": services.correct_choice_ids(question),
                    "numeric_answer": question.numeric_answer,
                    "accepted_answers": question.accepted_answers,
                    "explanation": question.explanation if full else "",
                    "marking_guide": question.marking_guide if full and attempt.status != Attempt.Status.IN_PROGRESS else "",
                    "is_correct": answer.is_correct if answer else False,
                    "marks_awarded": answer.marks_awarded if answer else 0,
                    "teacher_feedback": answer.teacher_feedback if answer else "",
                }
            result.append(item)
        return result


class AttemptListSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    quiz_kind = serializers.CharField(source="quiz.kind", read_only=True)
    subject = serializers.SerializerMethodField()
    subject_icon = serializers.CharField(source="quiz.subject.icon", read_only=True)
    percentage = serializers.FloatField(read_only=True)

    class Meta:
        model = Attempt
        fields = [
            "id",
            "quiz",
            "quiz_title",
            "quiz_kind",
            "subject",
            "subject_icon",
            "status",
            "started_at",
            "submitted_at",
            "score",
            "max_score",
            "percentage",
        ]

    def get_subject(self, attempt):
        return attempt.quiz.subject.localized_name(serializer_language(self))


class AnswerInputSerializer(serializers.Serializer):
    question = serializers.IntegerField()
    choice_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    text = CleanCharField(multiline=True, required=False, allow_blank=True, default="", max_length=10000)
    numeric = serializers.FloatField(required=False, allow_null=True, default=None)


class MarkInputSerializer(serializers.Serializer):
    marks = serializers.DecimalField(max_digits=5, decimal_places=2)
    feedback = CleanCharField(multiline=True, required=False, allow_blank=True, default="", max_length=5000)
