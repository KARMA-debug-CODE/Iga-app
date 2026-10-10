from django.utils import timezone

from .models import Enrollment


def follow_grade(student):
    """Make a student's classes follow their grade.

    Classes for another grade become inactive: they leave the student's class list, assignments, class
    leaderboard and parent report, while the teacher keeps the student and their results, marked as moved.
    Classes for the new grade (for example after moving back) become active again. Returns the names of the
    classes the student left.
    """
    if not student.is_student:
        return []
    leaving = Enrollment.objects.filter(student=student, active=True).exclude(classroom__grade=student.grade)
    names = list(leaving.values_list("classroom__name", flat=True))
    leaving.update(active=False, left_at=timezone.now())
    Enrollment.objects.filter(student=student, active=False, classroom__grade=student.grade).update(active=True, left_at=None)
    return names
