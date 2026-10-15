"""Switch off the demo accounts (public password) on a server that must not have them."""

from django.core.management.base import BaseCommand

from apps.core.demo import demo_accounts


class Command(BaseCommand):
    help = "Deactivate every account that still signs in with the public demo password (from seed_demo)."

    def handle(self, *args, **options):
        accounts = demo_accounts()
        for user in accounts:
            user.is_active = False
            user.set_unusable_password()
            user.save(update_fields=["is_active", "password"])
            self.stdout.write(f"  deactivated {user.username} ({user.role})")
        self.stdout.write(self.style.SUCCESS(f"{len(accounts)} demo account(s) switched off."))
