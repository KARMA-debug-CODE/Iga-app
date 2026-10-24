"""Who may use Teaching Packs: the class's own teacher, and only in a school with an active subscription."""

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.exceptions import APIException, PermissionDenied

from apps.classroom.models import Classroom
from apps.schools.access import content_access

from .models import TeachingPack


class SubscriptionRequired(PermissionDenied):
    """403 {detail, code, teaser}. The body is kept as given, so the teaser's numbers stay numbers."""

    default_code = "subscription_required"

    def __init__(self, teaser=None):
        super().__init__()
        body = {"detail": _("Teaching packs are part of your school's Iga subscription."), "code": self.default_code}
        if teaser is not None:
            body["teaser"] = teaser
        self.detail = body


class ClassArchived(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "class_archived"

    def __init__(self):
        super().__init__()
        self.detail = {"detail": _("This class is archived."), "code": self.default_code}


def teacher_classroom(user, pk):
    return get_object_or_404(Classroom, pk=pk, teacher=user)


def packs_for(user):
    """The packs of the classes `user` teaches now: a pack follows its class if the class changes teacher."""
    return TeachingPack.objects.filter(classroom__teacher=user)


def require_premium(user, teaser=None):
    if not content_access(user).premium:
        raise SubscriptionRequired(teaser)


def require_active(classroom):
    if classroom.archived:
        raise ClassArchived()
