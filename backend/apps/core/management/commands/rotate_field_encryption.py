"""Re-encrypt every encrypted field with the first key in FIELD_ENCRYPTION_KEYS.

Key rotation: put a new key first in FIELD_ENCRYPTION_KEYS and keep the old one after it, restart,
run this command, then remove the old key.
"""

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.encryption import ENCRYPTED_FIELDS


class Command(BaseCommand):
    help = "Re-encrypt every encrypted database field with the current (first) FIELD_ENCRYPTION_KEYS key."

    def handle(self, *args, **options):
        total = 0
        for model in apps.get_models():
            fields = [f.name for f in model._meta.concrete_fields if isinstance(f, ENCRYPTED_FIELDS)]
            for name in fields:
                done = 0
                with transaction.atomic():
                    # A list, not an iterator: SQLite can't safely write to a table while reading it.
                    rows = list(model._default_manager.exclude(**{f"{name}__isnull": True}).values_list("pk", name))
                    for pk, value in rows:
                        if value in ("", None):
                            continue  # empty stays empty (never encrypted)
                        # Read with any key, written back with the first one.
                        model._default_manager.filter(pk=pk).update(**{name: value})
                        done += 1
                total += done
                self.stdout.write(f"{model._meta.label}.{name}: {done} re-encrypted")
        self.stdout.write(self.style.SUCCESS(f"Done: {total} values."))
