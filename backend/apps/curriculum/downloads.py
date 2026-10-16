"""Access-checked downloads for files teachers upload as resources.

Like past papers (apps/schools/downloads.py), uploaded resources have no public /media URL: the API hands
out a signed link naming the resource and the viewer, and opening it checks again that this viewer may see
the resource (published, or their own upload, or they run the platform). A resource sent back to review,
rejected or deleted stops being downloadable at once, even through links handed out earlier.
"""

from django.contrib.auth import get_user_model
from django.core import signing
from django.http import Http404
from django.utils.translation import gettext as _
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.core.constants import ContentStatus
from apps.core.media import file_response

SALT = "iga.resource-download"
# Resource lists stay open in a tab for a while, and opening the link checks access again anyway.
LINK_SECONDS = 6 * 60 * 60


def signed_resource_url(request, resource, user):
    token = signing.dumps({"r": resource.pk, "u": getattr(user, "pk", None)}, salt=SALT, compress=True)
    path = f"/api/files/resources/{token}/"
    return request.build_absolute_uri(path) if request is not None else path


def can_download(user, resource):
    if user is None or not resource.file:
        return False
    return resource.status == ContentStatus.PUBLISHED or user.is_platform_admin or resource.uploaded_by_id == user.id


class ResourceDownloadView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        from .models import Resource

        try:
            data = signing.loads(token, salt=SALT, max_age=LINK_SECONDS)
        except signing.BadSignature:
            raise Http404(_("This download link has expired. Go back and open the resource again."))
        resource = Resource.objects.filter(pk=data.get("r")).first()
        user = get_user_model().objects.filter(pk=data.get("u"), is_active=True).first() if data.get("u") else None
        if resource is None or not can_download(user, resource):
            raise Http404
        return file_response(resource.file, resource.title or "resource")
