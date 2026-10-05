from django.db import migrations
from django.db.models import F, Q


def mark_school_confirmations(apps, schema_editor):
    """Before 0007, a school administrator's approval of a pending teacher set only teacher_approved.
    Record those as the school's confirmation, so it ends if the teacher leaves the school like the
    ones granted since. Teachers approved into a school by the Iga team, or who joined with the code
    (no approver), keep their approval as it is."""
    User = apps.get_model("accounts", "User")
    User.objects.filter(
        role="teacher",
        teacher_approved=True,
        teacher_approved_by_school__isnull=True,
        school__isnull=False,
        school_status="approved",
        school_approved_by__isnull=False,
    ).exclude(Q(school_approved_by__role="admin") | Q(school_approved_by__is_superuser=True)).update(
        teacher_approved_by_school_id=F("school_id")
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_teacher_approval_by_school"),
    ]

    operations = [
        migrations.RunPython(mark_school_confirmations, migrations.RunPython.noop),
    ]
