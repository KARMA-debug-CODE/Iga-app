from django.db import migrations

# The starter lesson and quiz of each subject marked `access: free` in backend/content/. On a fresh
# database load_curriculum sets these flags; this opens them on databases upgraded with `migrate`
# alone, so the free part of Iga isn't empty until someone reloads the content.
FREE_LESSONS = [
    "s1-biology-the-cell",
    "s1-chemistry-atomic-structure",
    "s1-english-parts-of-speech",
    "s1-entrepreneurship-budgeting",
    "s1-geography-map-scale",
    "s1-history-sources",
    "s1-ict-first-web-page",
    "s1-maths-integers",
    "s1-physics-motion",
    "s4-economics-demand-supply",
]
FREE_QUIZZES = [
    ("biology", "S1", "The cell — practice"),
    ("chemistry", "S1", "Inside the atom — practice"),
    ("english", "S1", "Parts of speech — practice"),
    ("entrepreneurship", "S1", "Saving and budgeting — practice"),
    ("geography", "S1", "Map scale — practice"),
    ("history", "S1", "Sources of history — practice"),
    ("ict", "S1", "HTML basics — practice"),
    ("mathematics", "S1", "Integers — quick practice"),
    ("physics", "S1", "Speed, velocity and acceleration — practice"),
    ("economics", "S4", "Demand and supply — practice"),
]


def open_starter_content(apps, schema_editor):
    Lesson = apps.get_model("curriculum", "Lesson")
    Quiz = apps.get_model("assessments", "Quiz")
    Lesson.objects.filter(slug__in=FREE_LESSONS, author__isnull=True).update(is_free=True)
    for subject, grade, title in FREE_QUIZZES:
        Quiz.objects.filter(subject__code=subject, grade=grade, title=title, author__isnull=True).update(is_free=True)


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0006_recheck_teacher_quizzes"),
        ("curriculum", "0004_lesson_is_free"),
    ]

    operations = [
        migrations.RunPython(open_starter_content, migrations.RunPython.noop),
    ]
