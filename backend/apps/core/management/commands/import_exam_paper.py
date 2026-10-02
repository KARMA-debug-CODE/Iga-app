from django.core.management.base import BaseCommand, CommandError

from apps.core.content_loader import ContentError, import_quiz_file


class Command(BaseCommand):
    help = (
        "Import exam papers (or quizzes) from JSON files. See docs/CONTENT_GUIDE.md for the format. "
        "Only mark a paper is_official if it was obtained from NESA with permission to publish."
    )

    def add_arguments(self, parser):
        parser.add_argument("files", nargs="+")
        parser.add_argument("--draft", action="store_true", help="Import as draft so an admin can review first")

    def handle(self, *args, **options):
        status = "draft" if options["draft"] else "published"
        for path in options["files"]:
            try:
                quiz, created = import_quiz_file(path, status=status)
            except (ContentError, KeyError, ValueError) as exc:
                raise CommandError(f"{path}: {exc}")
            verb = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{verb}: {quiz.title} ({quiz.quiz_questions.count()} questions)"))
