"""Check the money ledger has not been tampered with: `python manage.py verify_ledger`.

It recomputes every entry's hash and link to the one before, and checks that every paid payment
has exactly one entry with the same amount. It prints the head of the chain ("SEQUENCE:HASH"):
keep that line somewhere outside the database (an email to yourself, a ticket) and pass it back
later with --expect-head, so even a rebuilt chain is noticed. Exits with an error if anything is wrong.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.schools import ledger


class Command(BaseCommand):
    help = "Verify the money ledger's hash chain and that every paid payment is in it."

    def add_arguments(self, parser):
        parser.add_argument("--expect-head", default="", help='The "SEQUENCE:HASH" printed by an earlier run.')

    def handle(self, *args, **options):
        report = ledger.verify(expect_head=options["expect_head"])
        for problem in report.problems:
            self.stderr.write(problem)
        for warning in report.warnings:
            self.stderr.write(f"Warning: {warning}")
        head = f"{report.head_sequence}:{report.head_hash}"
        if not report.ok:
            raise CommandError(f"The ledger failed verification: {len(report.problems)} problem(s). Head {head}.")
        self.stdout.write(f"Ledger verified: {report.entries} entries. Head {head}")
