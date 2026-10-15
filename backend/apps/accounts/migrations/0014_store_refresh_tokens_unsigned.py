"""Drop the signature from the refresh tokens already recorded, so the database holds no working session."""

from django.db import migrations


def without_signature(token):
    head, dot, _ = str(token or "").rpartition(".")
    return f"{head}." if dot else ""


def strip_signatures(apps, schema_editor):
    OutstandingToken = apps.get_model("token_blacklist", "OutstandingToken")
    signed = OutstandingToken.objects.exclude(token__endswith=".").exclude(token="")
    while True:
        # Small batches, each read before it is written (every pass shrinks the set).
        batch = [OutstandingToken(pk=pk, token=without_signature(token)) for pk, token in signed.values_list("pk", "token")[:1000]]
        if not batch:
            return
        OutstandingToken.objects.bulk_update(batch, ["token"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0013_encrypt_totp_secret_hash_parent_codes"),
        ("token_blacklist", "0012_alter_outstandingtoken_user"),
    ]

    operations = [
        # Going back has nothing to restore: the signatures are gone, and those sessions still work.
        migrations.RunPython(strip_signatures, migrations.RunPython.noop),
    ]
