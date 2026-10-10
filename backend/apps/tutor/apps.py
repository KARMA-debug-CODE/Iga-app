from django.apps import AppConfig


class TutorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tutor"
    verbose_name = "Santa (learning assistant)"

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from apps.curriculum.models import Lesson, LessonTranslation, Subject, Unit

        from .retrieval import lessons_changed

        # Santa's lesson index is rebuilt after any change to what it quotes.
        for model in (Lesson, LessonTranslation, Unit, Subject):
            post_save.connect(lessons_changed, sender=model, dispatch_uid=f"santa-index-save-{model.__name__}")
            post_delete.connect(lessons_changed, sender=model, dispatch_uid=f"santa-index-delete-{model.__name__}")
