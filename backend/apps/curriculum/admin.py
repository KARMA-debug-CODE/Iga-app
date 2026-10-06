from django.contrib import admin

from .models import Lesson, LessonProgress, LessonTranslation, Resource, Subject, Unit


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("icon", "name", "code", "category", "offered_o_level", "offered_a_level", "order")
    list_editable = ("order",)
    prepopulated_fields = {"code": ("name",)}


class LessonInline(admin.TabularInline):
    model = Lesson
    fields = ("order", "title", "slug", "status")
    extra = 0
    show_change_link = True


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("subject", "grade", "number", "title", "alignment_verified")
    list_filter = ("subject", "grade", "alignment_verified")
    search_fields = ("title",)
    inlines = [LessonInline]


class TranslationInline(admin.StackedInline):
    model = LessonTranslation
    extra = 0


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "unit", "status", "author", "updated_at")
    list_filter = ("status", "unit__subject", "unit__grade")
    search_fields = ("title", "body")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("simulations",)
    inlines = [TranslationInline]
    actions = ["publish"]

    @admin.action(description="Publish selected lessons")
    def publish(self, request, queryset):
        queryset.update(status="published")


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "subject", "grade", "language", "is_official", "status")
    list_filter = ("kind", "subject", "grade", "is_official", "status", "format")
    search_fields = ("title", "content_id")


admin.site.register(LessonProgress)
