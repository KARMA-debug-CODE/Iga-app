"""Demo data for local development and trials. It refuses to run with DEBUG off: the demo accounts'
password is public, so they must never exist on a real server (see apps/core/demo.py)."""

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import ParentLink, User
from apps.assessments.models import Quiz
from apps.classroom.models import Assignment, Classroom, Enrollment
from apps.community.models import GroupMembership, Message, SharedNote, StudyGroup
from apps.core.demo import DEMO_EMAIL_DOMAIN, DEMO_PASSWORD
from apps.curriculum.models import Lesson, Resource, Subject
from apps.schools.billing import record_manual_payment
from apps.schools.membership import choose_school
from apps.schools.models import School

STUDENTS = [  # username, first name, last name, grade, A-level combination
    ("aline", "Aline", "Uwase", "S2", ""),
    ("eric", "Eric", "Mugisha", "S2", ""),
    ("divine", "Divine", "Ishimwe", "S2", ""),
    ("kevin", "Kevin", "Niyonzima", "S4", "MPC"),
    ("grace", "Grace", "Mukamana", "S1", ""),
]


class Command(BaseCommand):
    help = f"Load curriculum content plus demo users (password: {DEMO_PASSWORD}), a class and a study group."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Refusing to create demo accounts with DEBUG off: their password is public. For a local trial, "
                "run it with DJANGO_DEBUG=true (docker compose exec -e DJANGO_DEBUG=true backend python manage.py "
                "seed_demo); never on a real server."
            )

        call_command("load_curriculum", stdout=self.stdout)

        def make(username, first, last, role, grade="", **extra):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "role": role,
                    "grade": grade,
                    "email": f"{username}@{DEMO_EMAIL_DOMAIN}",
                    **extra,
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            return user

        admin = make("admin", "Ada", "Admin", User.Role.ADMIN, is_staff=True, is_superuser=True)
        teacher = make("teacher", "Jean", "Habimana", User.Role.TEACHER, teacher_approved=True)
        students = [make(u, first, last, User.Role.STUDENT, g, combination=c) for u, first, last, g, c in STUDENTS]
        parent = make("parent", "Claudine", "Uwase", User.Role.PARENT)
        ParentLink.objects.get_or_create(parent=parent, student=students[0])

        # Two verified schools: Lycée de Kigali has paid this month, APADE hasn't.
        lycee, _ = School.objects.get_or_create(
            name="Lycée de Kigali",
            district="Nyarugenge",
            defaults={"status": School.Status.VERIFIED, "phone": "+250 788 000 001", "verified_at": timezone.now()},
        )
        apade, _ = School.objects.get_or_create(
            name="APADE",
            district="Kicukiro",
            defaults={"status": School.Status.VERIFIED, "phone": "+250 788 000 002", "verified_at": timezone.now()},
        )
        if not lycee.payments.exists():
            record_manual_payment(lycee, admin, 1, Decimal("200"), "USD", "Demo: bank transfer received")
        lycee_admin = make("lkadmin", "Josiane", "Mukamana", User.Role.SCHOOL_ADMIN)
        apade_admin = make("apadeadmin", "Patrick", "Nkurunziza", User.Role.SCHOOL_ADMIN)
        apade_student = make("samuel", "Samuel", "Habineza", User.Role.STUDENT, "S2")
        for user in (lycee_admin, teacher, students[0], students[1], students[2], students[3]):
            if user.school_id is None:
                choose_school(user, lycee, approved_by=admin)
        for user in (apade_admin, apade_student, students[4]):
            if user.school_id is None:
                choose_school(user, apade, approved_by=admin)
        # A school waiting for the Iga team to verify it (shows up under Admin → Schools).
        pending_admin = make("gsadmin", "Alice", "Uwimana", User.Role.SCHOOL_ADMIN)
        if pending_admin.school_id is None:
            pending, _ = School.objects.get_or_create(
                name="GS Remera Catholique",
                district="Gasabo",
                defaults={"phone": "+250 788 000 003", "created_by": pending_admin},
            )
            pending_admin.school = pending
            pending_admin.school_status = User.SchoolStatus.PENDING
            pending_admin.save(update_fields=["school", "school_status"])
        school_users = [lycee_admin, apade_admin, apade_student, pending_admin]

        maths = Subject.objects.get(code="mathematics")
        classroom, _ = Classroom.objects.get_or_create(
            name="S2 Mathematics — Stream A", teacher=teacher, defaults={"subject": maths, "grade": "S2"}
        )
        for student in students:
            if student.grade == "S2":
                Enrollment.objects.get_or_create(classroom=classroom, student=student)

        quiz = Quiz.objects.filter(subject=maths, grade="S2").first()
        lesson = Lesson.objects.filter(slug="s2-maths-linear-graphs").first()
        if quiz:
            Assignment.objects.get_or_create(
                classroom=classroom,
                quiz=quiz,
                defaults={
                    "title": "Straight-line graphs quiz",
                    "instructions": "Do this after reading the lesson. You can check each answer as you go.",
                    "due_at": timezone.now() + timedelta(days=5),
                    "created_by": teacher,
                },
            )
        if lesson:
            Assignment.objects.get_or_create(
                classroom=classroom,
                lesson=lesson,
                defaults={
                    "title": "Read: straight-line graphs",
                    "due_at": timezone.now() + timedelta(days=3),
                    "created_by": teacher,
                },
            )

        group, created = StudyGroup.objects.get_or_create(
            name="S2 Maths Squad",
            defaults={
                "description": "We revise maths together every Thursday.",
                "subject": maths,
                "grade": "S2",
                "created_by": students[0],
            },
        )
        if created:
            GroupMembership.objects.create(group=group, user=students[0], role=GroupMembership.Role.OWNER)
            GroupMembership.objects.create(group=group, user=students[1])
            Message.objects.create(group=group, author=students[0], body="Muraho! Who has finished the linear graphs quiz?")
            Message.objects.create(group=group, author=students[1], body="Me! Question 3 was tricky — remember rise over run!")
            SharedNote.objects.create(
                group=group,
                author=students[0],
                title="Gradient cheat sheet",
                body="$m = \\frac{y_2 - y_1}{x_2 - x_1}$\n\n- positive → up\n- negative → down\n- zero → flat",
            )

        Resource.objects.get_or_create(
            title="REB e-learning portal (official textbooks and teacher guides)",
            subject=maths,
            defaults={
                "kind": Resource.Kind.LINK,
                "url": "https://elearning.reb.rw/",
                "is_official": True,
                "description": "Official REB digital textbooks for all subjects and grades.",
            },
        )

        self.stdout.write(self.style.SUCCESS(f"Demo data ready. Log in with any of these (password {DEMO_PASSWORD}):"))
        for user in [admin, teacher, parent, *students, *school_users]:
            school = user.school.name if user.school_id else ""
            self.stdout.write(f"  {user.username:<10} {user.role:<12} {user.grade:<3} {school}")
