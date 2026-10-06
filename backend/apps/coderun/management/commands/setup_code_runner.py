"""Install the C++ (gcc) and Java runtimes on the Piston code runner. Safe to run again.

    python manage.py setup_code_runner [--wait 120]

Piston downloads the packages from its package repository, so the code-runner machine needs internet
access while this runs (the programs themselves run with networking off). Docker Compose runs this once
in the `coderunner-setup` service.
"""

import time

from django.core.management.base import BaseCommand, CommandError

from apps.coderun import services


class Command(BaseCommand):
    help = "Install the C++ and Java runtimes on the Piston code runner (CODE_RUNNER_URL)."

    def add_arguments(self, parser):
        parser.add_argument("--wait", type=int, default=0, help="seconds to wait for the code runner to start")
        parser.add_argument("--skip-if-off", action="store_true", help="exit quietly when CODE_RUNNER_URL is empty")

    def handle(self, *args, **options):
        if not services.enabled():
            if options["skip_if_off"]:
                self.stdout.write("CODE_RUNNER_URL is empty: C++ and Java are switched off, nothing to set up.")
                return
            raise CommandError("CODE_RUNNER_URL is not set, so there is no code runner to set up.")
        deadline = time.monotonic() + options["wait"]
        while True:
            try:
                runtimes = services.request("GET", "/api/v2/runtimes", timeout=10)
                break
            except services.RunnerUnavailable as exc:
                if time.monotonic() >= deadline:
                    raise CommandError(f"The code runner at {services.settings.CODE_RUNNER_URL} is not answering: {exc}")
                time.sleep(3)
        installed = {(r["language"], r["version"]) for r in runtimes}
        for code, spec in services.LANGUAGES.items():
            if (spec["runtime"], spec["version"]) in installed:
                self.stdout.write(f"{code}: {spec['runtime']} {spec['version']} already installed.")
                continue
            self.stdout.write(f"{code}: installing {spec['package']} {spec['version']} (this can take a few minutes)...")
            try:
                services.request(
                    "POST", "/api/v2/packages", {"language": spec["package"], "version": spec["version"]}, timeout=900
                )
            except (services.RunnerError, services.RunnerUnavailable) as exc:
                raise CommandError(f"Could not install {spec['package']} {spec['version']}: {exc}")
            self.stdout.write(self.style.SUCCESS(f"{code}: installed."))
        self.stdout.write(self.style.SUCCESS("The code runner is ready for C++ and Java."))
