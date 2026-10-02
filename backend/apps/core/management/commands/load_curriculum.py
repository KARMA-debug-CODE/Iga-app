from django.core.management.base import BaseCommand

from apps.core.content_loader import DEFAULT_CONTENT_DIR, load_all
from apps.gamification.services import ensure_badges


class Command(BaseCommand):
    help = "Load subjects, units, simulations, lessons, quizzes and sample papers from backend/content/."

    def add_arguments(self, parser):
        parser.add_argument("--content-dir", default=str(DEFAULT_CONTENT_DIR))

    def handle(self, *args, **options):
        load_all(options["content_dir"], log=self.stdout.write)
        ensure_badges()
        self.stdout.write(self.style.SUCCESS("Curriculum content loaded."))
