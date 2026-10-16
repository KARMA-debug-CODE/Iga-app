"""Access-checked downloads for uploaded past papers and marking guides.

Browsers open these as plain links (no Authorization header), so the API hands out a signed,
short-lived URL instead of a public /media path. The file is re-checked against the user's
access when the link is opened, then sent by apps/core/media.py (X-Accel-Redirect behind nginx).
"""

from django.contrib.auth import get_user_model
from django.core import signing
from django.http import Http404
from django.utils.translation import gettext as _
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.core.media import file_response

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
            raise Http404(_("This download link has expired. Go back and open the paper again."))
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
        return file_response(file, paper.title or "paper")
