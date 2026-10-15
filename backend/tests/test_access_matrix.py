"""Cross-user access matrix: nobody reads or changes someone else's rows, through any endpoint.

Iga's browser never talks to the database: every query goes through Django, so this is the guarantee
PostgreSQL row-level security would give, checked where it is enforced. The routes are listed from
Django's URL resolver, so a new endpoint is caught by these tests until it is classified below.

The world has two schools. Everything on side B (a student, their class, teacher, parent, school
admin, attempts, answers, drafts, groups, payments) is the victim; side A's student, teacher, parent
and school admin, and an anonymous visitor, attack it:

* every route x every method x every attacker, with B's ids in the URL, the query string and the body;
* no response may contain any of B's secrets (markers below);
* nothing on side B may change;
* every route aimed at one of B's rows must refuse (401/403/404/405, or 400 for an id in a body);
* anonymous visitors get 401 everywhere except the public routes.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import ParentLink, User
from apps.assessments.models import Answer, Attempt, Question, Quiz, QuizQuestion
from apps.classroom.models import Assignment, Classroom, Enrollment
from apps.community.models import GroupMembership, Message, MessageReport, SharedNote, StudyGroup
from apps.curriculum.models import Lesson, LessonProgress, Resource
from apps.schools.models import LedgerEntry, Payment

from .conftest import add_mcq, make_school, make_user
from .routes import api_routes, fill, view_methods

pytestmark = pytest.mark.django_db

# Routes anyone may call without signing in.
PUBLIC_ROUTES = {
    "api/auth/register/",
    "api/auth/login/",
    "api/auth/refresh/",
    "api/auth/logout/",
    "api/auth/password-reset/",  # the same answer for every name; the email goes to the account's own address
    "api/auth/password-reset/confirm/",  # needs the emailed single-use secret
    "api/health/",
    "api/meta/",
    "api/schools/",
    "api/schools/districts/",
    "api/files/papers/{token}/",  # a signed, short-lived link checked inside
    "api/files/resources/{token}/",  # the same, for teachers' uploaded resources
    "api/billing/webhooks/flutterwave/",  # signed by Flutterwave, checked inside
}
# Routes with an id that name shared catalogue content (no owner), so reading them is allowed.
CATALOGUE_ROUTES = {
    "api/subjects/{code}/",
    "api/units/{pk}/",
    "api/simulations/{slug}/",
    "api/simulations/{slug}/view/",
    "api/exam-papers/{pk}/",
    "api/files/papers/{token}/",
    "api/files/resources/{token}/",
}
DENIED = {400, 401, 403, 404, 405}


@pytest.fixture
def world(subject, unit):
    school_a = make_school("School A", "Gasabo", paid_until=timezone.now() + timedelta(days=90))
    school_b = make_school("School B", "Huye", paid_until=timezone.now() + timedelta(days=90))
    school_b.phone = "+250-SECRET-B"
    school_b.save()
    w = {"school_a": school_a, "school_b": school_b}
    for side, school in (("a", school_a), ("b", school_b)):
        w[f"student_{side}"] = make_user(f"student_{side}", school=school, first_name=f"Pupil{side.upper()}")
        w[f"teacher_{side}"] = make_user(f"teacher_{side}", role=User.Role.TEACHER, teacher_approved=True, school=school)
        w[f"parent_{side}"] = make_user(f"parent_{side}", role=User.Role.PARENT, school=None)
        w[f"admin_{side}"] = make_user(f"schooladmin_{side}", role=User.Role.SCHOOL_ADMIN, school=school)
        ParentLink.objects.create(parent=w[f"parent_{side}"], student=w[f"student_{side}"])
        classroom = Classroom.objects.create(name=f"Class {side.upper()}", grade="S2", teacher=w[f"teacher_{side}"])
        Enrollment.objects.create(classroom=classroom, student=w[f"student_{side}"])
        w[f"class_{side}"] = classroom
    sb, tb = w["student_b"], w["teacher_b"]
    sb.last_name = "Secretlastname-B"
    sb.email = "secret-b@example.com"
    sb.save()
    w["parent_b"].last_name = "Secretparent-B"
    w["parent_b"].save()
    w["class_b"].name = "SECRET-CLASS-B"
    w["class_b"].save()

    # A shared, published quiz both classes use, and B's own material.
    shared_quiz = Quiz.objects.create(
        subject=subject, unit=unit, title="Shared quiz", grade="S2", status="published", is_free=True
    )
    essay = Question.objects.create(
        subject=subject, grade="S2", unit=unit, type=Question.Type.ESSAY, prompt="Explain.", author=tb
    )
    QuizQuestion.objects.create(quiz=shared_quiz, question=essay, order=0)
    w["shared_quiz"] = shared_quiz
    w["assignment_a"] = Assignment.objects.create(
        classroom=w["class_a"], title="Homework A", quiz=shared_quiz, created_by=w["teacher_a"]
    )
    w["assignment_b"] = Assignment.objects.create(
        classroom=w["class_b"], title="SECRET-ASSIGN-B", quiz=shared_quiz, created_by=tb
    )
    attempt = Attempt.objects.create(
        user=sb,
        quiz=shared_quiz,
        assignment=w["assignment_b"],
        status=Attempt.Status.NEEDS_MARKING,
        question_order=[essay.id],
        max_score=Decimal("1"),
        submitted_at=timezone.now(),
    )
    w["attempt_b"] = attempt
    w["answer_b"] = Answer.objects.create(attempt=attempt, question=essay, text_answer="SECRET-ANSWER-B")
    practice_q = add_mcq(subject, unit, prompt="Practice?")
    practice = Quiz.objects.create(subject=subject, unit=unit, title="Practice", grade="S2", status="published", is_free=True)
    QuizQuestion.objects.create(quiz=practice, question=practice_q, order=0)
    w["practice_question"] = practice_q
    w["open_attempt_b"] = Attempt.objects.create(user=sb, quiz=practice, question_order=[practice_q.id], max_score=Decimal("1"))

    w["draft_lesson_b"] = Lesson.objects.create(
        unit=unit, slug="secret-draft-b", title="SECRET-DRAFT-LESSON-B", body="SECRET-DRAFT-BODY-B", status="draft", author=tb
    )
    w["pub_lesson_b"] = Lesson.objects.create(
        unit=unit, slug="pub-b", title="Published by B", body="x", status="published", author=tb, is_free=True
    )
    LessonProgress.objects.create(user=sb, lesson=w["pub_lesson_b"])
    w["draft_quiz_b"] = Quiz.objects.create(
        subject=subject, unit=unit, title="SECRET-DRAFT-QUIZ-B", grade="S2", status="draft", author=tb
    )
    w["pub_quiz_b"] = Quiz.objects.create(
        subject=subject, unit=unit, title="Published quiz B", grade="S2", status="published", author=tb, is_free=True
    )
    w["draft_question_b"] = Question.objects.create(
        subject=subject, grade="S2", type=Question.Type.ESSAY, prompt="SECRET-DRAFT-QUESTION-B", status="draft", author=tb
    )
    w["pub_question_b"] = Question.objects.create(
        subject=subject, grade="S2", type=Question.Type.ESSAY, prompt="Public question B", author=tb
    )
    w["review_resource_b"] = Resource.objects.create(
        subject=subject,
        kind="notes",
        title="SECRET-REVIEW-RESOURCE-B",
        url="https://example.com/b",
        status="review",
        uploaded_by=tb,
    )
    w["pub_resource_b"] = Resource.objects.create(
        subject=subject, kind="notes", title="Resource B", url="https://example.com/p", uploaded_by=tb
    )

    group = StudyGroup.objects.create(name="SECRET-GROUP-B", is_private=True, created_by=sb)
    GroupMembership.objects.create(group=group, user=sb, role=GroupMembership.Role.OWNER)
    w["group_b"] = group
    w["message_b"] = Message.objects.create(group=group, author=sb, body="SECRET-MSG-B")
    w["report_b"] = MessageReport.objects.create(message=w["message_b"], reporter=sb, reason="SECRET-REPORT-B")
    SharedNote.objects.create(group=group, author=sb, title="Notes", body="SECRET-NOTE-B")
    public_group = StudyGroup.objects.create(name="Open group B", created_by=sb)
    GroupMembership.objects.create(group=public_group, user=sb, role=GroupMembership.Role.OWNER)
    w["public_group_b"] = public_group
    w["public_message_b"] = Message.objects.create(group=public_group, author=sb, body="hello")
    w["payment_b"] = Payment.objects.create(
        reference="PAY-B-SECRET-REF",
        school=school_b,
        provider="dev",
        months=1,
        amount=Decimal("200"),
        currency="USD",
        created_by=w["admin_b"],
    )
    return w


def markers(w):
    """Text that only side B (and the Iga team) may ever see."""
    return [
        "Secretlastname-B",
        "secret-b@example.com",
        "Secretparent-B",
        "SECRET-CLASS-B",
        w["class_b"].join_code,
        "SECRET-ASSIGN-B",
        "SECRET-ANSWER-B",
        "SECRET-DRAFT-LESSON-B",
        "SECRET-DRAFT-BODY-B",
        "SECRET-DRAFT-QUIZ-B",
        "SECRET-DRAFT-QUESTION-B",
        "SECRET-REVIEW-RESOURCE-B",
        "SECRET-GROUP-B",
        w["group_b"].join_code,
        "SECRET-MSG-B",
        "SECRET-NOTE-B",
        "SECRET-REPORT-B",
        "PAY-B-SECRET-REF",
        "+250-SECRET-B",
        w["school_b"].join_code,
    ]


def route_targets(w):
    """For every route with an id in its path: the id of one of side B's rows (or a catalogue item)."""
    return {
        "api/auth/parents/{parent_id}/": {"parent_id": w["parent_b"].id},
        "api/children/{student_id}/": {"student_id": w["student_b"].id},
        "api/files/papers/{token}/": {"token": "forged-token"},
        "api/files/resources/{token}/": {"token": "forged-token"},
        "api/school/members/{user_id}/remove/": {"user_id": w["student_b"].id},
        "api/billing/payments/{reference}/": {"reference": w["payment_b"].reference},
        "api/billing/payments/{reference}/confirm/": {"reference": w["payment_b"].reference},
        "api/billing/dev/{reference}/complete/": {"reference": w["payment_b"].reference},
        "api/admin/schools/{school_id}/": {"school_id": w["school_b"].id},
        "api/admin/schools/{school_id}/payments/": {"school_id": w["school_b"].id},
        "api/admin/schools/{school_id}/members/": {"school_id": w["school_b"].id},
        "api/admin/schools/{school_id}/ledger/": {"school_id": w["school_b"].id},
        "api/admin/schools/{school_id}/{action}/": {"school_id": w["school_b"].id, "action": "suspend"},
        "api/subjects/{code}/": {"code": "mathematics"},
        "api/units/{pk}/": {"pk": w["draft_lesson_b"].unit_id},
        "api/lessons/{slug}/": {"slug": w["draft_lesson_b"].slug},
        "api/lessons/{slug}/complete/": {"slug": w["draft_lesson_b"].slug},
        "api/resources/{pk}/": {"pk": w["review_resource_b"].id},
        "api/simulations/{slug}/": {"slug": "no-such-sim"},
        "api/simulations/{slug}/view/": {"slug": "no-such-sim"},
        "api/questions/{pk}/": {"pk": w["draft_question_b"].id},
        "api/quizzes/{pk}/": {"pk": w["draft_quiz_b"].id},
        "api/quizzes/{pk}/analytics/": {"pk": w["draft_quiz_b"].id},
        "api/quizzes/{pk}/start/": {"pk": w["draft_quiz_b"].id},
        "api/exam-papers/{pk}/": {"pk": 999999},
        "api/attempts/{pk}/": {"pk": w["open_attempt_b"].id},
        "api/attempts/{pk}/answer/": {"pk": w["open_attempt_b"].id},
        "api/attempts/{pk}/check/": {"pk": w["open_attempt_b"].id},
        "api/attempts/{pk}/submit/": {"pk": w["open_attempt_b"].id},
        "api/marking/{pk}/mark/": {"pk": w["answer_b"].id},
        "api/classes/{pk}/": {"pk": w["class_b"].id},
        "api/classes/{pk}/import_roster/": {"pk": w["class_b"].id},
        "api/classes/{pk}/leave/": {"pk": w["class_b"].id},
        "api/classes/{pk}/new_code/": {"pk": w["class_b"].id},
        "api/classes/{pk}/remove_student/": {"pk": w["class_b"].id},
        "api/classes/{pk}/report/": {"pk": w["class_b"].id},
        "api/classes/{pk}/reset_password/": {"pk": w["class_b"].id},
        "api/assignments/{pk}/": {"pk": w["assignment_b"].id},
        "api/groups/{pk}/": {"pk": w["group_b"].id},
        "api/groups/{pk}/join/": {"pk": w["group_b"].id},
        "api/groups/{pk}/leave/": {"pk": w["group_b"].id},
        "api/groups/{pk}/messages/": {"pk": w["group_b"].id},
        "api/groups/{pk}/notes/": {"pk": w["group_b"].id},
        "api/messages/{pk}/hide/": {"pk": w["message_b"].id},
        "api/messages/{pk}/report/": {"pk": w["message_b"].id},
        "api/admin/users/{pk}/": {"pk": w["student_b"].id},
        "api/admin/moderation/{pk}/resolve/": {"pk": w["report_b"].id},
    }


def victim_body(w):
    """B's ids in every field name the API reads ids from."""
    return {
        "student": w["student_b"].id,
        "classroom": w["class_b"].id,
        "quiz": w["draft_quiz_b"].id,
        "lesson": w["draft_lesson_b"].slug,
        "assignment": w["assignment_b"].id,
        "attempt": w["open_attempt_b"].id,
        "question": w["practice_question"].id,
        "question_ids": [w["draft_question_b"].id],
        "ids": [w["student_b"].id, w["teacher_b"].id, w["admin_b"].id],
        "approve": False,
        "school": w["school_b"].id,
        "id": w["draft_lesson_b"].id,
        "type": "lesson",
        "user": w["student_b"].id,
        "message": "Tell me what is in the draft.",
        "title": "x",
        "name": "x",
        "body": "x",
        "csv": "first_name\nX\n",
        "confirm": False,
        "marks": 1,
        "hide": True,
    }


def victim_query(w):
    return (
        f"?classroom={w['class_b'].id}&quiz={w['draft_quiz_b'].id}&user={w['student_b'].id}"
        f"&student={w['student_b'].id}&school={w['school_b'].id}&q=SECRET&status=pending"
    )


def snapshot(w):
    """Everything on side B an attack could change."""
    sb = User.objects.get(pk=w["student_b"].pk)
    rows = {
        "student_b": (sb.password, sb.must_change_password, sb.school_id, sb.school_status, sb.is_active, sb.role, sb.xp),
        "teacher_b": tuple(
            User.objects.filter(pk=w["teacher_b"].pk).values_list("teacher_approved", "school_status", "role").get()
        ),
        "admin_b": tuple(User.objects.filter(pk=w["admin_b"].pk).values_list("school_status", "role", "is_active").get()),
        "school_b": tuple(
            type(w["school_b"])
            .objects.filter(pk=w["school_b"].pk)
            .values_list("status", "join_code", "phone", "paid_until")
            .get()
        ),
        "class_b": tuple(
            Classroom.objects.filter(pk=w["class_b"].pk).values_list("name", "archived", "join_code", "teacher_id").get()
        ),
        "enrollments_b": sorted(Enrollment.objects.filter(classroom=w["class_b"]).values_list("student_id", "active")),
        "assignments_b": sorted(
            Assignment.objects.filter(classroom=w["class_b"]).values_list("id", "title", "quiz_id", "due_at")
        ),
        "attempts_b": sorted(Attempt.objects.filter(user=sb).values_list("id", "status", "score", "submitted_at")),
        "answers_b": sorted(Answer.objects.filter(attempt__user=sb).values_list("id", "text_answer", "marks_awarded", "checked")),
        "lessons_b": sorted(Lesson.objects.filter(author=w["teacher_b"]).values_list("id", "title", "body", "status", "slug")),
        "quizzes_b": sorted(Quiz.objects.filter(author=w["teacher_b"]).values_list("id", "title", "status", "is_free")),
        "questions_b": sorted(Question.objects.filter(author=w["teacher_b"]).values_list("id", "prompt", "status")),
        "resources_b": sorted(Resource.objects.filter(uploaded_by=w["teacher_b"]).values_list("id", "title", "status")),
        "groups_b": sorted(
            StudyGroup.objects.filter(created_by=sb).values_list("id", "name", "is_private", "max_members", "join_code")
        ),
        "memberships_b": sorted(GroupMembership.objects.filter(group__created_by=sb).values_list("group_id", "user_id", "role")),
        "messages_b": sorted(Message.objects.filter(group__created_by=sb).values_list("id", "body", "is_hidden")),
        "notes_b": sorted(SharedNote.objects.filter(group__created_by=sb).values_list("id", "body")),
        "reports_b": sorted(MessageReport.objects.filter(message__group__created_by=sb).values_list("id", "resolved")),
        "parent_links_b": sorted(ParentLink.objects.filter(student=sb).values_list("parent_id", flat=True)),
        "payments_b": sorted(Payment.objects.filter(school=w["school_b"]).values_list("reference", "status", "provider_data")),
        "ledger_b": sorted(LedgerEntry.objects.filter(school=w["school_b"]).values_list("sequence", "entry_hash")),
        "progress_b": sorted(LessonProgress.objects.filter(user=sb).values_list("lesson_id", flat=True)),
    }
    return rows


def attackers(w):
    return {name: w[name] for name in ("student_a", "teacher_a", "parent_a", "admin_a")}


def _send(client, method, url, body=None):
    send = getattr(client, method.lower())
    if method == "GET":
        return send(url)
    return send(url, body or {}, format="json")


def test_every_route_with_an_id_is_classified(world):
    targets = route_targets(world)
    unclassified = [route for route, _ in api_routes() if "{" in route and route not in targets]
    assert not unclassified, f"Add these routes to route_targets() (and check who may use them): {unclassified}"


def test_the_owners_can_see_their_own_rows(client_for, world):
    """The probes aim at real rows: B's own people see them (so a refusal below means something)."""
    w = world
    assert "SECRET-CLASS-B" in client_for(w["teacher_b"]).get(f"/api/classes/{w['class_b'].id}/").content.decode()
    assert "SECRET-ANSWER-B" in client_for(w["teacher_b"]).get("/api/marking/").content.decode()
    assert client_for(w["teacher_b"]).get(f"/api/lessons/{w['draft_lesson_b'].slug}/").status_code == 200
    assert client_for(w["teacher_b"]).get(f"/api/quizzes/{w['draft_quiz_b'].id}/").status_code == 200
    assert client_for(w["teacher_b"]).get(f"/api/questions/{w['draft_question_b'].id}/").status_code == 200
    assert client_for(w["teacher_b"]).get(f"/api/resources/{w['review_resource_b'].id}/").status_code == 200
    assert client_for(w["teacher_b"]).get(f"/api/assignments/{w['assignment_b'].id}/").status_code == 200
    assert client_for(w["student_b"]).get(f"/api/attempts/{w['open_attempt_b'].id}/").status_code == 200
    assert "SECRET-MSG-B" in client_for(w["student_b"]).get(f"/api/groups/{w['group_b'].id}/messages/").content.decode()
    assert client_for(w["parent_b"]).get(f"/api/children/{w['student_b'].id}/").status_code == 200
    assert "Secretparent-B" in client_for(w["student_b"]).get("/api/auth/parents/").content.decode()
    assert "Secretlastname-B" in client_for(w["admin_b"]).get("/api/school/members/").content.decode()
    assert client_for(w["admin_b"]).get(f"/api/billing/payments/{w['payment_b'].reference}/").status_code == 200


def test_no_attacker_reads_or_changes_side_b_through_any_route(client_for, world):
    w = world
    secrets = markers(w)
    targets = route_targets(w)
    body = victim_body(w)
    query = victim_query(w)
    before = snapshot(w)
    leaks, not_refused = [], []
    for name, user in {**attackers(w), "anonymous": None}.items():
        client = client_for(user)
        client.raise_request_exception = False
        for route, callback in api_routes():
            url = fill(route, **targets.get(route, {}))
            aimed_at_b = "{" in route and route not in CATALOGUE_ROUTES
            for method in view_methods(callback):
                for variant in ("plain", "with B's ids"):
                    response = _send(
                        client, method, url + (query if variant != "plain" else ""), body if variant != "plain" else None
                    )
                    content = response.content.decode(errors="replace")
                    found = [s for s in secrets if s and s in content]
                    if found:
                        leaks.append((name, method, url, variant, found))
                    if aimed_at_b and response.status_code not in DENIED:
                        not_refused.append((name, method, url, variant, response.status_code))
                    if name == "anonymous" and route not in PUBLIC_ROUTES and response.status_code != 401:
                        not_refused.append((name, method, url, variant, response.status_code))
    assert not leaks, leaks
    assert not not_refused, not_refused
    assert snapshot(w) == before


def test_ids_in_bodies_and_filters_never_reach_side_b(client_for, world):
    """Targeted attempts to use B's ids from A's own objects."""
    w = world
    ta, sa, aa = client_for(w["teacher_a"]), client_for(w["student_a"]), client_for(w["admin_a"])
    before = snapshot(w)
    # A teacher can't put work in another teacher's class, or move their own assignment there.
    new = {"classroom": w["class_b"].id, "quiz": w["shared_quiz"].id, "title": "Mine now"}
    assert ta.post("/api/assignments/", new, format="json").status_code == 400
    moved = ta.patch(
        f"/api/assignments/{w['assignment_a'].id}/", {"classroom": w["class_b"].id, "quiz": w["shared_quiz"].id}, format="json"
    )
    assert moved.status_code == 400
    # ...or another teacher's draft questions in a quiz, or another class's results in analytics.
    quiz = {"title": "Copy", "subject": w["shared_quiz"].subject_id, "grade": "S2", "question_ids": [w["draft_question_b"].id]}
    assert ta.post("/api/quizzes/", quiz, format="json").status_code == 400
    assert ta.get(f"/api/quizzes/{w['shared_quiz'].id}/analytics/?classroom={w['class_b'].id}").status_code == 403
    # ...or students outside their own class.
    assert (
        ta.post(f"/api/classes/{w['class_a'].id}/remove_student/", {"student": w["student_b"].id}, format="json").status_code
        == 400
    )
    assert (
        ta.post(f"/api/classes/{w['class_a'].id}/reset_password/", {"student": w["student_b"].id}, format="json").status_code
        == 400
    )
    assert ta.get(f"/api/attempts/{w['attempt_b'].id}/").status_code == 404
    assert ta.post(f"/api/marking/{w['answer_b'].id}/mark/", {"marks": 1}, format="json").status_code == 404
    # Published material by B can be read but not changed by A.
    for url in (
        f"/api/quizzes/{w['pub_quiz_b'].id}/",
        f"/api/questions/{w['pub_question_b'].id}/",
        f"/api/resources/{w['pub_resource_b'].id}/",
    ):
        assert ta.patch(url, {"title": "x", "prompt": "x"}, format="json").status_code == 403, url
        assert ta.delete(url).status_code == 403, url
    assert ta.patch(f"/api/lessons/{w['pub_lesson_b'].slug}/", {"title": "x"}, format="json").status_code == 403
    # A student can't start B's assignment, or use B's attempt or a draft lesson with Santa.
    assert (
        sa.post(f"/api/quizzes/{w['shared_quiz'].id}/start/", {"assignment": w["assignment_b"].id}, format="json").status_code
        == 404
    )
    assert sa.post("/api/tutor/ask/", {"message": "hi", "attempt": w["open_attempt_b"].id}, format="json").status_code == 404
    assert sa.post("/api/tutor/ask/", {"message": "hi", "lesson": w["draft_lesson_b"].slug}, format="json").status_code == 404
    assert sa.get(f"/api/leaderboard/?scope=class&classroom={w['class_b'].id}").status_code == 404
    # In B's public group, A may look and join but not read the chat, moderate or edit.
    group = w["public_group_b"]
    assert sa.get(f"/api/groups/{group.id}/").status_code == 200
    assert sa.get(f"/api/groups/{group.id}/messages/").status_code == 403
    assert sa.get(f"/api/groups/{group.id}/notes/").status_code == 403
    assert sa.patch(f"/api/groups/{group.id}/", {"name": "x"}, format="json").status_code == 403
    assert sa.delete(f"/api/groups/{group.id}/").status_code == 403
    assert sa.post(f"/api/messages/{w['public_message_b'].id}/hide/").status_code == 403
    # A school admin can't decide about, or remove, another school's members.
    assert aa.post(
        "/api/school/members/decide/", {"ids": [w["student_b"].id, w["teacher_b"].id], "approve": False}, format="json"
    ).data == {"changed": []}
    assert snapshot(w) == before
    # B's teacher may read B's attempt but never answer for the student.
    assert client_for(w["teacher_b"]).get(f"/api/attempts/{w['open_attempt_b'].id}/").status_code == 200
    answer = {"question": w["practice_question"].id, "choice_ids": []}
    assert (
        client_for(w["teacher_b"]).post(f"/api/attempts/{w['open_attempt_b'].id}/answer/", answer, format="json").status_code
        == 403
    )


def test_teachers_read_only_their_current_students_work_in_their_subject(client_for, world, subject):
    """A teacher used to read every attempt of anyone ever enrolled in one of their classes: other
    subjects, and everything a student did after moving to another grade. Now: their current students'
    work in the class's subject (as for marking), and any attempt at one of their own assignments."""
    from apps.curriculum.models import Subject

    w = world
    teacher, student = w["teacher_b"], w["student_b"]
    w["class_b"].subject = subject
    w["class_b"].save()
    physics = Subject.objects.create(code="physics", name="Physics")
    other_quiz = Quiz.objects.create(subject=physics, title="Physics practice", grade="S2", status="published", is_free=True)
    physics_attempt = Attempt.objects.create(
        user=student, quiz=other_quiz, status=Attempt.Status.MARKED, score=1, max_score=1, submitted_at=timezone.now()
    )
    maths_practice = w["open_attempt_b"]  # self-practice in the class's subject
    assignment_attempt = w["attempt_b"]  # at the teacher's own assignment
    client = client_for(teacher)
    assert client.get(f"/api/attempts/{physics_attempt.id}/").status_code == 404
    assert client.get(f"/api/attempts/{maths_practice.id}/").status_code == 200
    assert client.get(f"/api/attempts/{assignment_attempt.id}/").status_code == 200
    recent = [a["id"] for a in client.get("/api/dashboard/").data["teacher"]["recent_submissions"]]
    assert physics_attempt.id not in recent and assignment_attempt.id in recent

    # The student moves to S3: the S2 teacher keeps the gradebook (their assignment) but nothing new.
    Enrollment.objects.filter(classroom=w["class_b"], student=student).update(active=False)
    assert client.get(f"/api/attempts/{maths_practice.id}/").status_code == 404
    assert client.get(f"/api/attempts/{assignment_attempt.id}/").status_code == 200
    assert "SECRET-ANSWER-B" in client.get("/api/marking/").content.decode()  # their own assignment
