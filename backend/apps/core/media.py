"""Sending uploaded files to the browser, safely.

Uploads are never reachable at a public /media URL (nginx refuses /media/ and Django has no route for it):
each download goes through a view that checks the viewer may have the file, then calls file_response().
Behind nginx (PROTECTED_MEDIA_ACCEL) the file is sent from the internal /protected-media/ location with
X-Accel-Redirect; otherwise (development) Django streams it. Either way the browser gets:

- the Content-Type of the file's (checked) kind, never one guessed from its contents (nosniff);
- Content-Disposition inline only for PDFs, images, audio and video, attachment for everything else;
- a Content-Security-Policy that stops it running scripts: a sandbox for images, media and documents,
  and no scripts, plugins or connections for PDFs (browsers' PDF viewers don't work in a sandbox);
- private, no-store caching and a same-origin resource policy.

nginx keeps Content-Type and Content-Disposition from Django on an X-Accel-Redirect but drops the other
headers, so frontend/nginx.conf sets the same policy for /protected-media/ (keep the two in step).
"""

import os

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.utils.http import content_disposition_header

CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
}
MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".mp4"}
CSP_DEFAULT = "sandbox; default-src 'none'"
CSP_MEDIA = "sandbox; default-src 'none'; img-src 'self'; media-src 'self'; style-src 'unsafe-inline'"
CSP_PDF = "default-src 'none'; object-src 'none'; script-src 'none'"


def policy(name):
    """(content type, opens inline?, Content-Security-Policy) for a stored file name."""
    ext = os.path.splitext(name)[1].lower()
    content_type = CONTENT_TYPES.get(ext, "application/octet-stream")
    if ext == ".pdf":
        return content_type, True, CSP_PDF
    if ext in MEDIA_EXTENSIONS:
        return content_type, True, CSP_MEDIA
    return content_type, False, CSP_DEFAULT


def file_response(file, download_name):
    """The response sending stored `file` (a FieldFile), offered under `download_name` (its extension is
    added). The caller has already checked access."""
    content_type, inline, csp = policy(file.name)
    ext = os.path.splitext(file.name)[1].lower()
    # Printable characters only: a title can't add a line to the response headers.
    name = "".join(c for c in (download_name or "") if c.isprintable()).strip()[:120] or "file"
    filename = f"{name}{ext}"
    if settings.PROTECTED_MEDIA_ACCEL:
        response = HttpResponse(content_type=content_type)
        response["X-Accel-Redirect"] = f"/protected-media/{file.name}"
    else:
        response = FileResponse(file.open("rb"), content_type=content_type)
    response["Content-Disposition"] = content_disposition_header(not inline, filename)
    response["Content-Security-Policy"] = csp
    response["X-Content-Type-Options"] = "nosniff"
    response["Cross-Origin-Resource-Policy"] = "same-origin"
    response["Cache-Control"] = "private, no-store"
    return response
