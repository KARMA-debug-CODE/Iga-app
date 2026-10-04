from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.constants import GRADES, LEVELS, ContentStatus


class Question(models.Model):
    class Type(models.TextChoices):
        MCQ = "mcq", "Multiple choice (one answer)"
        MULTI = "multi", "Multiple choice (several answers)"
        TRUE_FALSE = "true_false", "True / False"
        NUMERIC = "numeric", "Numeric answer"
        SHORT = "short", "Short text answer"
        ESSAY = "essay", "Written / essay (teacher-marked)"

    class Source(models.TextChoices):
        CUSTOM = "custom", "Written by a teacher"
        PAST_PAPER = "past_paper", "Official past paper"
        SAMPLE = "sample", "Sample / practice"

    CHOICE_TYPES = (Type.MCQ, Type.MULTI, Type.TRUE_FALSE)

    subject = models.ForeignKey("curriculum.Subject", on_delete=models.CASCADE, related_name="questions")
    grade = models.CharField(max_length=2, choices=GRADES, db_index=True)
    unit = models.ForeignKey("curriculum.Unit", null=True, blank=True, on_delete=models.SET_NULL, related_name="questions")
    type = models.CharField(max_length=12, choices=Type.choices)
    prompt = models.TextField(help_text="Markdown; $...$ for maths")
    explanation = models.TextField(blank=True, help_text="Shown after answering so students learn from mistakes")
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    numeric_answer = models.FloatField(null=True, blank=True)
    numeric_tolerance = models.FloatField(default=0, help_text="Accepted absolute difference")
    accepted_answers = models.JSONField(
        default=list, blank=True, help_text="Short answers accepted automatically (case/spacing ignored)"
    )
    marking_guide = models.TextField(blank=True, help_text="For teacher-marked questions")
    difficulty = models.PositiveSmallIntegerField(default=2, help_text="1 easy – 3 hard")
    source = models.CharField(max_length=12, choices=Source.choices, default=Source.CUSTOM)
    status = models.CharField(max_length=10, choices=ContentStatus.CHOICES, default=ContentStatus.PUBLISHED)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="questions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["subject", "grade", "id"]

    def __str__(self):
        return self.prompt[:80]

    @property
    def needs_manual_marking(self):
        if self.type == self.Type.ESSAY:
            return True
        return self.type == self.Type.SHORT and not self.accepted_answers


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text


class Quiz(models.Model):
    class Kind(models.TextChoices):
        PRACTICE = "practice", "Practice quiz"
        TEST = "test", "Class test"
        PAST_PAPER = "past_paper", "Past paper"
        MOCK = "mock", "Mock exam"

    class FeedbackMode(models.TextChoices):
        IMMEDIATE = "immediate", "Check each answer straight away"
        AFTER_SUBMIT = "after_submit", "Show results after submitting (exam mode)"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    subject = models.ForeignKey("curriculum.Subject", on_delete=models.CASCADE, related_name="quizzes")
    grade = models.CharField(max_length=2, choices=GRADES, db_index=True)
    unit = models.ForeignKey("curriculum.Unit", null=True, blank=True, on_delete=models.SET_NULL, related_name="quizzes")
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.PRACTICE)
    questions = models.ManyToManyField(Question, through="QuizQuestion", related_name="quizzes")
    time_limit_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    shuffle_questions = models.BooleanField(default=True)
    shuffle_choices = models.BooleanField(default=True)
    feedback_mode = models.CharField(max_length=14, choices=FeedbackMode.choices, default=FeedbackMode.IMMEDIATE)
    max_attempts = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Empty = unlimited")
    status = models.CharField(max_length=10, choices=ContentStatus.CHOICES, default=ContentStatus.DRAFT, db_index=True)
    # Free quizzes are open to everyone; the rest need a school subscription.
    is_free = models.BooleanField(default=False, db_index=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="quizzes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["subject", "grade", "title"]
        verbose_name_plural = "quizzes"

    def __str__(self):
        return self.title


class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="quiz_questions")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="quiz_links")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [models.UniqueConstraint(fields=["quiz", "question"], name="unique_quiz_question")]


class ExamPaper(models.Model):
    """A national exam paper (or an unofficial sample) with its PDF, marking guide and interactive version."""

    subject = models.ForeignKey("curriculum.Subject", on_delete=models.CASCADE, related_name="exam_papers")
    level = models.CharField(max_length=1, choices=LEVELS)
    year = models.PositiveSmallIntegerField(db_index=True)
    paper_code = models.CharField(max_length=40, blank=True, help_text="e.g. 'Paper 1' or the NESA code")
    title = models.CharField(max_length=200)
    is_official = models.BooleanField(
        default=False, help_text="Only tick for papers obtained from NESA (National Examination and School Inspection Authority)"
    )
    source_note = models.CharField(max_length=300, blank=True, help_text="Where this paper came from")
    paper_url = models.URLField(blank=True)
    paper_file = models.FileField(upload_to="exam_papers/", blank=True)
    marking_guide_url = models.URLField(blank=True)
    marking_guide_file = models.FileField(upload_to="exam_papers/marking/", blank=True)
    quiz = models.OneToOneField(Quiz, null=True, blank=True, on_delete=models.SET_NULL, related_name="exam_paper")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "subject", "paper_code"]

    def __str__(self):
        return self.title


class Attempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        NEEDS_MARKING = "needs_marking", "Waiting for teacher marking"
        MARKED = "marked", "Marked"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    assignment = models.ForeignKey(
        "classroom.Assignment", null=True, blank=True, on_delete=models.SET_NULL, related_name="attempts"
    )
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.IN_PROGRESS, db_index=True)
    started_at = models.DateTimeField(default=timezone.now)
    deadline = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    # Per-attempt randomisation, fixed at start so a refresh shows the same order.
    question_order = models.JSONField(default=list)
    choice_order = models.JSONField(default=dict)
    score = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    max_score = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "quiz"],
                condition=models.Q(status="in_progress"),
                name="one_open_attempt_per_quiz",
            )
        ]

    def __str__(self):
        return f"{self.user} · {self.quiz} · {self.status}"

    @property
    def percentage(self):
        if self.score is None or not self.max_score:
            return None
        return round(float(self.score) / float(self.max_score) * 100, 1)

    def is_expired(self, now=None):
        if self.deadline is None:
            return False
        now = now or timezone.now()
        return now > self.deadline

    def accepts_submission(self, now=None):
        if self.deadline is None:
            return True
        now = now or timezone.now()
        return now <= self.deadline + timedelta(seconds=settings.EXAM_SUBMIT_GRACE_SECONDS)


class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    selected_choices = models.ManyToManyField(Choice, blank=True)
    text_answer = models.TextField(blank=True)
    numeric_answer = models.FloatField(null=True, blank=True)
    checked = models.BooleanField(default=False, help_text="Student used 'check answer' in practice mode")
    is_correct = models.BooleanField(null=True)
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    teacher_feedback = models.TextField(blank=True)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="marked_answers"
    )
    marked_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["attempt", "question"], name="unique_attempt_answer")]
