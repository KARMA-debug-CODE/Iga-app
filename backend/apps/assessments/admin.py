from django.contrib import admin

from .models import Answer, Attempt, Choice, ExamPaper, Question, Quiz, QuizQuestion


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "type", "subject", "grade", "marks", "source", "status")
    list_filter = ("type", "subject", "grade", "source", "status")
    search_fields = ("prompt",)
    inlines = [ChoiceInline]


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    raw_id_fields = ("question",)
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "subject", "grade", "time_limit_minutes", "status")
    list_filter = ("kind", "subject", "grade", "status")
    search_fields = ("title",)
    inlines = [QuizQuestionInline]


@admin.register(ExamPaper)
class ExamPaperAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "level", "year", "paper_code", "is_official")
    list_filter = ("level", "year", "subject", "is_official")
    search_fields = ("title", "paper_code")


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    fields = ("question", "text_answer", "numeric_answer", "is_correct", "marks_awarded", "marked_by")
    readonly_fields = ("question", "text_answer", "numeric_answer")


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "quiz", "status", "score", "max_score", "started_at", "submitted_at")
    list_filter = ("status", "quiz__subject")
    search_fields = ("user__username", "quiz__title")
    inlines = [AnswerInline]
