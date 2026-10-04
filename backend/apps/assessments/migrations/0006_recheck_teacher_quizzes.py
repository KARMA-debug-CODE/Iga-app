from django.db import migrations
from django.db.models import Q


def library_questions_q(prefix):
    # Same rule as services.library_questions_q.
    return (
        Q(**{f"{prefix}author__isnull": True})
        | Q(**{f"{prefix}author__role": "admin"})
        | Q(**{f"{prefix}author__is_superuser": True})
    )


def lock_repackaged_library_questions(apps, schema_editor):
    """An earlier version of 0005 made every teacher quiz free, including quizzes built from premium
    library questions. Put those back behind the subscription on databases that ran it."""
    Quiz = apps.get_model("assessments", "Quiz")
    Quiz.objects.filter(is_free=True, author__role="teacher").filter(
        pk__in=Quiz.objects.filter(library_questions_q("quiz_questions__question__")).values("pk")
    ).update(is_free=False)


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0005_quiz_is_free"),
    ]

    operations = [
        migrations.RunPython(lock_repackaged_library_questions, migrations.RunPython.noop),
    ]
