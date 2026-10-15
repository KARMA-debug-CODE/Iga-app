"""Encrypt 2FA secrets in the database, and keep parent codes only as keyed hashes."""

from django.db import migrations, models

import apps.core.encryption


def encrypt_totp_secrets(apps, schema_editor):
    """Rows written before encryption hold the plain secret: saving it again encrypts it."""
    User = apps.get_model("accounts", "User")
    for pk, secret in User.objects.exclude(totp_secret="").values_list("pk", "totp_secret"):
        User.objects.filter(pk=pk).update(totp_secret=secret)


def decrypt_totp_secrets(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    rows = list(User.objects.exclude(totp_secret="").values_list("pk", "totp_secret"))
    with schema_editor.connection.cursor() as cursor:
        for pk, secret in rows:
            # Constant SQL (tests/test_sql_safety.py): the plain value goes in as a parameter.
            cursor.execute("UPDATE accounts_user SET totp_secret = %s WHERE id = %s", [secret, pk])


def hash_parent_codes(apps, schema_editor):
    from apps.accounts.models import parent_code_digest

    ParentInvite = apps.get_model("accounts", "ParentInvite")
    for invite in ParentInvite.objects.all():
        invite.code_hash = parent_code_digest(invite.code)
        invite.save(update_fields=["code_hash"])


def forget_parent_codes(apps, schema_editor):
    """Going back: hashed codes can't be turned back into codes, so unused ones are removed."""
    ParentInvite = apps.get_model("accounts", "ParentInvite")
    ParentInvite.objects.filter(used_by__isnull=True).delete()
    for invite in ParentInvite.objects.all():
        invite.code = f"USED{invite.pk}"[:12]
        invite.save(update_fields=["code"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0012_password_reset_and_temporary_password_expiry"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="totp_secret",
            field=apps.core.encryption.EncryptedTextField(blank=True),
        ),
        migrations.RunPython(encrypt_totp_secrets, decrypt_totp_secrets),
        migrations.AddField(
            model_name="parentinvite",
            name="code_hash",
            field=models.CharField(max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name="parentinvite",
            name="code",
            field=models.CharField(max_length=12, null=True),
        ),
        migrations.RunPython(hash_parent_codes, forget_parent_codes),
        migrations.RemoveField(model_name="parentinvite", name="code"),
        migrations.AlterField(
            model_name="parentinvite",
            name="code_hash",
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
