"""Erase the accounts whose deletion is due, and delete records past their retention period.

The scheduler (docker-compose.yml) runs it every 10 minutes; running it often is safe.
    python manage.py privacy_cleanup
"""

from django.core.management.base import BaseCommand

from apps.accounts.privacy import erase_due_accounts
from apps.core.retention import purge_expired


class Command(BaseCommand):
    help = "Erase accounts whose deletion grace period is over, and delete records past their retention period."

    def handle(self, *args, **options):
        erased = erase_due_accounts()
        deleted = purge_expired()
        summary = ", ".join(f"{name} {count}" for name, count in deleted.items() if count)
        self.stdout.write(f"Accounts erased: {erased}. Expired records deleted: {summary or 'none'}.")
