from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import School


@receiver(pre_delete, sender=School)
def release_members(sender, instance, **kwargs):
    """A deleted school leaves no half-members behind: its members become school-less (so they
    can choose a school again) and teacher approvals it granted end, as when a teacher leaves."""
    from apps.accounts.models import User

    User.objects.filter(teacher_approved_by_school=instance).update(teacher_approved=False, teacher_approved_by_school=None)
    User.objects.filter(school=instance).update(
        school=None, school_status=User.SchoolStatus.NONE, school_approved_at=None, school_approved_by=None
    )
