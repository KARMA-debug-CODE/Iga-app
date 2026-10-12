"""Set up the two PostgreSQL roles Iga runs with (see apps/core/dbroles.py)."""

import os

from django.core.management.base import BaseCommand, CommandError

from apps.core.dbroles import RoleSetupError, role_from_url, setup_roles


class Command(BaseCommand):
    help = (
        "Create or update the owner role (DB_OWNER_URL: owns the tables, runs migrate) and the app role "
        "(DB_APP_URL: may only read and write rows). Run it with a superuser in DATABASE_URL; it is safe to run again."
    )

    def handle(self, *args, **options):
        try:
            owner = role_from_url(os.environ.get("DB_OWNER_URL", ""), "DB_OWNER_URL")
            app = role_from_url(os.environ.get("DB_APP_URL", ""), "DB_APP_URL")
            summary = setup_roles(owner, app)
        except RoleSetupError as exc:
            raise CommandError(str(exc))
        self.stdout.write(
            self.style.SUCCESS(
                f"Database roles ready: {owner.name} owns the {summary['tables']} tables"
                + (f" ({summary['moved']} moved to it)" if summary["moved"] else "")
                + f"; {app.name} may only read and write rows."
            )
        )
