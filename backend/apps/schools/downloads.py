"""Access-checked downloads for uploaded past papers and marking guides.

Browsers open these as plain links (no Authorization header), so the API hands out a signed,
short-lived URL instead of a public /media path. The file is re-checked against the user's
access when the link is opened. Behind nginx the file itself is sent with X-Accel-Redirect from
an internal location; without nginx (development) Django streams it.
"""

import mimetypes
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.http import FileResponse, Http404, HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from . import access

SALT = "iga.paper-download"
LINK_SECONDS = 10 * 60
KINDS = ("paper", "marking_guide")


def signed_download_url(request, paper, kind, user):
    token = signing.dumps({"p": paper.pk, "k": kind, "u": getattr(user, "pk", None)}, salt=SALT, compress=True)
    path = f"/api/files/papers/{token}/"
    return request.build_absolute_uri(path) if request is not None else path


class PaperDownloadView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        from apps.assessments.models import ExamPaper

        try:
            data = signing.loads(token, salt=SALT, max_age=LINK_SECONDS)
        except signing.BadSignature:
            raise Http404("This download link has expired. Go back and open the paper again.")
        if data.get("k") not in KINDS:
            raise Http404
        paper = ExamPaper.objects.select_related("quiz").filter(pk=data.get("p")).first()
        if paper is None:
            raise Http404
        user = get_user_model().objects.filter(pk=data.get("u"), is_active=True).first() if data.get("u") else None
        free = bool(paper.quiz_id and paper.quiz.is_free)
        if not free and not access.has_premium(user):
            raise access.SubscriptionRequired()
        file = paper.paper_file if data["k"] == "paper" else paper.marking_guide_file
        if not file:
            raise Http404
        filename = f"{paper.title or 'paper'}{os.path.splitext(file.name)[1]}".replace('"', "")
        content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        if settings.PROTECTED_MEDIA_ACCEL:
            response = HttpResponse(content_type=content_type)
            response["X-Accel-Redirect"] = f"/protected-media/{file.name}"
        else:
            response = FileResponse(file.open("rb"), content_type=content_type)
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
