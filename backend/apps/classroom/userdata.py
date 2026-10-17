"""The classroom app's part of "Download my data" and "Delete my account" (apps/accounts/privacy.py)."""

from django.db.models import Count, Q

from apps.core.exporting import iso

from .models import Assignment, Classroom, Enrollment


def export_for(user):
    taught = Classroom.objects.filter(teacher=user).annotate(
        student_total=Count("enrollments", filter=Q(enrollments__active=True))
    )
    return {
        "classes_joined": [
            {
                "class": e.classroom.name,
                "grade": e.classroom.grade,
                "teacher": e.classroom.teacher.short_name,
                "joined_at": iso(e.joined_at),
                "current": e.active,
                "left_at": iso(e.left_at),
            }
            for e in Enrollment.objects.filter(student=user).select_related("classroom__teacher").order_by("joined_at")
        ],
        # Teachers: their classes (not the students' details, which are the students' own data).
        "classes_taught": [
            {
                "class": c.name,
                "grade": c.grade,
                "students": c.student_total,
                "archived": c.archived,
                "created_at": iso(c.created_at),
            }
            for c in taught.order_by("created_at")
        ],
        "assignments_set": [
            {"title": a.title, "class": a.classroom.name, "due_at": iso(a.due_at), "created_at": iso(a.created_at)}
            for a in Assignment.objects.filter(created_by=user).select_related("classroom").order_by("created_at")
        ],
    }


def erase_for(user):
    # A student leaves every class. A teacher's classes are archived, not deleted: their students keep their
    # results and "previous classes", and the class shows "Deleted account" as its teacher.
    Enrollment.objects.filter(student=user).delete()
    Classroom.objects.filter(teacher=user, archived=False).update(archived=True)
