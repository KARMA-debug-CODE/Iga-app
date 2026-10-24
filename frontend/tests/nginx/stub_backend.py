"""A stand-in for Django in the nginx tests: answers every request with what it received, as JSON.

/api/tutor/stream/ and /api/code/run/slow/ take a while to answer (a request in progress for the
connection limits). Standard library only; run inside a python image on the test network as "backend".
"""

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _answer(self):
        # A test asks for a failed backend (nginx then shows its own error page): drop the connection with
        # no answer, which nginx reports as 502.
        if self.headers.get("X-Stub-Drop"):
            self.close_connection = True
            return
        length = int(self.headers.get("Content-Length") or 0)
        received = 0
        while received < length:
            chunk = self.rfile.read(min(65536, length - received))
            if not chunk:
                break
            received += len(chunk)
        if self.path.startswith("/api/tutor/stream/"):
            time.sleep(2)
        body = json.dumps(
            {
                "method": self.command,
                "path": self.path,
                "body_bytes": received,
                "headers": {name.lower(): value for name, value in self.headers.items()},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _answer

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
