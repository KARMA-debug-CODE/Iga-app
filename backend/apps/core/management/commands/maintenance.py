"""Switch maintenance mode on or off: every API request but a platform admin's answers 503 "back soon", and
nginx shows its "back soon" page (apps/core/maintenance.py).

    docker compose exec backend python manage.py maintenance on
    docker compose exec backend python manage.py maintenance off
    docker compose exec backend python manage.py maintenance        # say whether it is on
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core.maintenance import maintenance_on, set_maintenance


class Command(BaseCommand):
    help = "Turn maintenance mode on or off, or say whether it is on."

    def add_arguments(self, parser):
        parser.add_argument("state", nargs="?", choices=["on", "off", "status"], default="status")

    def handle(self, *args, state, **options):
        if state in ("on", "off"):
            try:
                set_maintenance(state == "on")
            except OSError as error:
                raise CommandError(f"Couldn't change {settings.MAINTENANCE_FILE}: {error}") from error
        on = maintenance_on()
        reason = " (MAINTENANCE_MODE=true in the environment)" if settings.MAINTENANCE_MODE else ""
        if state == "off" and on:
            self.stdout.write(f"The file is gone, but maintenance mode stays on{reason}.")
        else:
            self.stdout.write(f"Maintenance mode is {'on' if on else 'off'}{reason if on else ''}.")
