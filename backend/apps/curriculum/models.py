from django.conf import settings
from django.db import models

from apps.core.constants import GRADES, LANGUAGES, RESOURCE_LANGUAGES, ContentStatus
from apps.core.uploads import RandomName, validate_upload


class Subject(models.Model):
    class Category(models.TextChoices):
        SCIENCES = "sciences", "Sciences"
        MATHEMATICS = "mathematics", "Mathematics"
        LANGUAGES = "languages", "Languages"
        HUMANITIES = "humanities", "Humanities & Social Sciences"
        ICT = "ict", "ICT"
        COMPUTER_SCIENCE = "computer-science", "Computer Science"
        OTHER = "other", "Other"

    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=100)
    name_fr = models.CharField("Name (French)", max_length=100, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    icon = models.CharField(
        max_length=32, default="book", help_text="Name of the line icon shown on subject cards (see Icon.jsx)"
    )
    color = models.CharField(max_length=7, default="#00A1DE", help_text="Hex colour for the subject card")
    offered_o_level = models.BooleanField(default=True)
    offered_a_level = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def localized_name(self, lang):
        return (self.name_fr if lang == "fr" else "") or self.name

    def offered_in(self, grade):
        return self.offered_o_level if grade in ("S1", "S2", "S3") else self.offered_a_level


class Unit(models.Model):
    """A syllabus unit for one subject in one grade (e.g. S2 Physics, Unit 3)."""

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="units")
    grade = models.CharField(max_length=2, choices=GRADES, db_index=True)
    number = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200)
    title_fr = models.CharField("Title (French)", max_length=200, blank=True)
    summary = models.TextField(blank=True)
    key_unit_competence = models.TextField(blank=True, help_text="The competence-based-curriculum statement for this unit")
    syllabus_reference = models.CharField(
        max_length=200, blank=True, help_text="Where this unit appears in the official REB syllabus"
    )
    alignment_verified = models.BooleanField(
        default=False, help_text="Ticked once a reviewer has checked this unit against the official syllabus"
    )

    class Meta:
        ordering = ["subject__order", "grade", "number"]
        constraints = [models.UniqueConstraint(fields=["subject", "grade", "number"], name="unique_unit_number")]

    def __str__(self):
        return f"{self.subject} {self.grade} · Unit {self.number}: {self.title}"

    def localized_title(self, lang):
        return (self.title_fr if lang == "fr" else "") or self.title


class Lesson(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="lessons")
    order = models.PositiveSmallIntegerField(default=1)
    slug = models.SlugField(max_length=120, unique=True)
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    body = models.TextField(
        help_text=(
            "Markdown. Use $...$ for maths, ```sim slug``` to embed a simulation and "
            "```playground html``` for a live code editor."
        )
    )
    video_url = models.URLField(blank=True)
    estimated_minutes = models.PositiveSmallIntegerField(default=15)
    status = models.CharField(max_length=10, choices=ContentStatus.CHOICES, default=ContentStatus.DRAFT, db_index=True)
    # Free lessons are open to everyone; the rest need a school subscription.
    is_free = models.BooleanField(default=False, db_index=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="lessons")
    simulations = models.ManyToManyField("simulations.Simulation", blank=True, related_name="lessons")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["unit", "order"]

    def __str__(self):
        return self.title


def localized_lesson_titles(lessons, lang):
    """{lesson id: title in `lang`}, falling back to the English title where there's no translation."""
    titles = {lesson.id: lesson.title for lesson in lessons}
    if lang != "en" and titles:
        translated = LessonTranslation.objects.filter(lesson_id__in=titles, language=lang).values_list("lesson_id", "title")
        titles.update(dict(translated))
    return titles


class LessonTranslation(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="translations")
    language = models.CharField(max_length=2, choices=LANGUAGES)
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    body = models.TextField()
    reviewed = models.BooleanField(default=False, help_text="Checked by a fluent speaker")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["lesson", "language"], name="unique_lesson_language")]

    def __str__(self):
        return f"{self.lesson} [{self.language}]"


class Resource(models.Model):
    """Textbooks, teacher guides, syllabi, videos and other study material.

    Books listed in content/books.json are loaded with a `content_id` and kept in step with that file;
    material uploaded by teachers has no content_id."""

    class Kind(models.TextChoices):
        TEXTBOOK = "textbook", "Student textbook"
        TEACHER_GUIDE = "teacher_guide", "Teacher's guide"
        SYLLABUS = "syllabus", "Syllabus"
        NOTES = "notes", "Revision notes"
        FORMULA_SHEET = "formula_sheet", "Formula sheet"
        VIDEO = "video", "Video"
        LINK = "link", "Web link"

    class Format(models.TextChoices):
        PDF = "pdf", "PDF download"
        PAGE = "page", "Page that links the book"
        WEB = "web", "Read online"

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="resources")
    grade = models.CharField(max_length=2, choices=GRADES, blank=True)
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.SET_NULL, related_name="resources")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    description_fr = models.TextField("Description (French)", blank=True)
    url = models.URLField(max_length=500, blank=True)
    format = models.CharField(max_length=4, choices=Format.choices, blank=True)
    file = models.FileField(upload_to=RandomName("resources"), blank=True, validators=[validate_upload])
    language = models.CharField(max_length=2, choices=RESOURCE_LANGUAGES, default="en")
    publisher = models.CharField(max_length=120, blank=True)
    licence = models.CharField(max_length=120, blank=True)
    is_official = models.BooleanField(default=False, help_text="Published by REB/NESA")
    content_id = models.CharField(
        max_length=100, blank=True, db_index=True, help_text="Set for books loaded from content/books.json"
    )
    status = models.CharField(max_length=10, choices=ContentStatus.CHOICES, default=ContentStatus.PUBLISHED)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["subject", "grade", "kind", "title"]

    def __str__(self):
        return self.title


class LessonProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "lesson"], name="unique_lesson_progress")]
