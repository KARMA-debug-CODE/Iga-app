import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Schools become a list: the old free-text field is kept as `school_name`."""

    dependencies = [
        ("accounts", "0004_must_change_password"),
        ("schools", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(model_name="user", old_name="school", new_name="school_name"),
        migrations.AddField(
            model_name="user",
            name="school",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="members",
                to="schools.school",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="school_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "No school"),
                    ("pending", "Waiting for the school to approve"),
                    ("approved", "Approved"),
                    ("rejected", "Not approved"),
                ],
                default="",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="school_approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="school_approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("student", "Student"),
                    ("teacher", "Teacher"),
                    ("parent", "Parent or guardian"),
                    ("school_admin", "School administrator"),
                    ("admin", "Administrator"),
                ],
                db_index=True,
                default="student",
                max_length=16,
            ),
        ),
    ]
