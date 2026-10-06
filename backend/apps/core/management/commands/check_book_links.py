"""Check that every book link in content/books.json still opens.

REB re-uploads its books from time to time and the links change, so run this every term from a
machine with normal internet access (`python manage.py check_book_links`) and fix the links it
reports in books.json. It only asks for the first byte of each file, so it is light on data.
"""

import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand, CommandError

from apps.core.content_loader import DEFAULT_CONTENT_DIR

USER_AGENT = "Iga book link checker"


def check(url, timeout=20):
    """Return (ok, detail) for one link: HEAD first, then a one-byte GET for servers that refuse HEAD."""
    last = ""
    for method, headers in (("HEAD", {}), ("GET", {"Range": "bytes=0-0"})):
        request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT, **headers})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return True, f"{response.status}"
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
            if exc.code not in (403, 405, 501):  # these often mean "no HEAD here"; try a GET
                return False, last
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return False, str(getattr(exc, "reason", exc))
    return False, last


class Command(BaseCommand):
    help = "Check that the book links in content/books.json still open (needs internet access)."

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DEFAULT_CONTENT_DIR / "books.json"))
        parser.add_argument("--subject", help="only check books for this subject code")

    def handle(self, *args, **options):
        with open(options["file"], encoding="utf-8") as handle:
            books = json.load(handle)["books"]
        if options["subject"]:
            books = [b for b in books if b["subject"] == options["subject"]]
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda book: check(book["url"]), books))
        broken = 0
        for book, (ok, detail) in zip(books, results, strict=True):
            if not ok:
                broken += 1
                self.stdout.write(self.style.ERROR(f"BROKEN {book['id']} ({detail}): {book['url']}"))
        self.stdout.write(f"Checked {len(books)} links: {len(books) - broken} open, {broken} broken.")
        if broken:
            raise CommandError(f"{broken} book link(s) need fixing in books.json.")
