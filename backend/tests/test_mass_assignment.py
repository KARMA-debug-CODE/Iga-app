"""Field tampering: no client sets a field it must not, through any create or update endpoint.

Every writable route gets a payload stuffed with privileged fields (role, school, approval, XP,
scores, prices, owners, statuses, codes, dates...) next to the fields it really takes; the stored
rows must keep server-decided values. Routes are listed from the URL resolver, so a new writable
route fails test_every_writable_route_is_covered until it is added here.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts import password_reset
from apps.accounts.models import User
from apps.assessments.models import Answer, Attempt, Question, Quiz, QuizQuestion
from apps.classroom.models import Assignment, Classroom, Enrollment
from apps.community.models import GroupMembership, Message, MessageReport, SharedNote, StudyGroup
from apps.curriculum.models import Lesson, LessonProgress, Resource
from apps.schools.models import LedgerEntry, Payment, School

from .conftest import add_mcq, make_school, make_user
from .routes import api_routes, view_methods

pytestmark = pytest.mark.django_db

FUTURE = "2099-01-01T00:00:00Z"
PAST = "2000-01-01T00:00:00Z"


def tampering(victim, other_school):
    """Fields no request may set for itself."""
    return {
        "id": 999999,
        "pk": 999999,
        "role": "admin",
        "is_staff": True,
        "is_superuser": True,
        "teacher_approved": True,
        "teacher_revoked": False,
        "teacher_approved_by_school": other_school.id,
        "school": other_school.id,
        "school_status": "approved",
        "school_approved_at": PAST,
        "school_approved_by": victim.id,
        "xp": 999999,
        "streak_days": 999,
        "badges": [{"code": "champion"}],
        "totp_enabled": True,
        "totp_secret": "JBSWY3DPEHPK3PXP",
        "must_change_password": False,
        "username": "hijacked",
        "date_joined": PAST,
        "last_login": PAST,
        "author": victim.id,
        "uploaded_by": victim.id,
        "created_by": victim.id,
        "teacher": victim.id,
        "owner": victim.id,
        "user": victim.id,
        "reporter": victim.id,
        "marked_by": victim.id,
        "hidden_by": victim.id,
        "score": "100.00",
        "max_score": "1.00",
        "marks_awarded": "99.00",
        "is_correct": True,
        "checked": True,
        "is_official": True,
        "content_id": "tampered",
        "join_code": "HACKED99",
        "paid_until": FUTURE,
        "verified_at": PAST,
        "verified_by": victim.id,
        "amount": "0.01",
        "price": "0.01",
        "provider": "manual",
        "reference": "TAMPERED-REF",
        "period_end": FUTURE,
        "created_at": PAST,
        "updated_at": PAST,
        "member_count": 999,
        "is_member": True,
        "is_hidden": False,
        "resolved": True,
        "reviewed": True,
        "deadline": FUTURE,
        "submitted_at": PAST,
        "question_order": [],
        "terms_accepted_at": PAST,
        "deletion_requested_at": PAST,
        "deletion_due_at": PAST,
        "erased_at": PAST,
        "handled_at": PAST,
        "handled_by": victim.id,
    }


@pytest.fixture
def w(subject, unit):
    school = make_school("Lycee", "Gasabo", paid_until=timezone.now() + timedelta(days=30))
    other = make_school("Elsewhere", "Huye", paid_until=timezone.now() + timedelta(days=300))
    victim = make_user("victim", role=User.Role.ADMIN)
    return {
        "school": school,
        "other": other,
        "victim": victim,
        "student": make_user("pupil", school=school),
        "teacher": make_user("tutor", role=User.Role.TEACHER, teacher_approved=True, school=school),
        "school_admin": make_user("head", role=User.Role.SCHOOL_ADMIN, school=school),
        "admin": make_user("iga", role=User.Role.ADMIN),
        "subject": subject,
        "unit": unit,
        "bad": tampering(victim, other),
    }


def _ok(response):
    assert response.status_code < 300, (response.status_code, getattr(response, "data", response.content))
    return response


def test_register_cannot_choose_privileges(client_for, w):
    payload = {**w["bad"], "username": "newbie", "password": "Str0ng-pass-123", "grade": "S2", "first_name": "N"}
    payload["accept_terms"] = True
    payload["role"] = "admin"
    assert client_for().post("/api/auth/register/", payload, format="json").status_code == 400
    payload.update(role="teacher", school=w["school"].id)
    _ok(client_for().post("/api/auth/register/", payload, format="json"))
    user = User.objects.get(username="newbie")
    assert user.role == "teacher" and not user.teacher_approved and not user.is_staff and not user.is_superuser
    assert user.school_status == "pending" and user.xp == 0 and not user.totp_enabled and not user.must_change_password


def test_accepting_the_terms_sets_only_the_current_version_and_time(client_for, w, settings):
    student = w["student"]
    before = User.objects.filter(pk=student.pk).values().get()
    _ok(client_for(student).post("/api/auth/accept-terms/", {**w["bad"], "version": settings.LEGAL_VERSION}, format="json"))
    after = User.objects.filter(pk=student.pk).values().get()
    assert {k for k in after if after[k] != before[k]} == {"terms_version", "terms_accepted_at"}
    assert after["terms_version"] == settings.LEGAL_VERSION and after["terms_accepted_at"].year != 2000


def test_asking_to_delete_an_account_cannot_choose_when(client_for, w, settings):
    student = w["student"]
    before = User.objects.filter(pk=student.pk).values().get()
    _ok(client_for(student).post("/api/auth/delete-account/", {**w["bad"], "confirm": True}, format="json"))
    after = User.objects.filter(pk=student.pk).values().get()
    assert {k for k in after if after[k] != before[k]} == {"deletion_requested_at", "deletion_due_at", "session_version"}
    grace = after["deletion_due_at"] - after["deletion_requested_at"]
    assert grace.days == settings.ACCOUNT_DELETION_GRACE_DAYS and after["erased_at"] is None


def test_a_contact_message_cannot_claim_a_sender_or_be_marked_handled(client_for, w):
    from apps.website.models import ContactMessage

    payload = {**w["bad"], "name": "Visitor", "email": "visitor@example.com", "message": "Hello, please call me back."}
    _ok(client_for().post("/api/contact/", payload, format="json"))
    message = ContactMessage.objects.get()
    assert message.user is None and message.handled_at is None and message.handled_by is None
    assert message.language == "en" and message.created_at.year != 2000
    # A platform admin marking it handled is recorded as that admin, now.
    _ok(client_for(w["admin"]).post(f"/api/admin/contact/{message.id}/handle/", {**w["bad"], "handled": True}, format="json"))
    message.refresh_from_db()
    assert message.handled_by == w["admin"] and message.handled_at.year != 2000 and message.name == "Visitor"


def test_password_reset_link_sets_only_the_password(client_for, w):
    student = w["student"]
    link = password_reset.create_link(student)
    before = User.objects.filter(pk=student.pk).values().get()
    payload = {**w["bad"], "token": link.rpartition("#")[2], "new_password": "An0ther-str0ng-pass"}
    _ok(client_for().post("/api/auth/password-reset/confirm/", payload, format="json"))
    after = User.objects.filter(pk=student.pk).values().get()
    changed = {k for k in after if after[k] != before[k]}
    assert changed <= {"password", "session_version", "temporary_password_expires_at"}, changed
    assert "password" in changed and after["role"] == "student" and not after["is_staff"]


def test_profile_edit_cannot_change_privileges(client_for, w):
    student = w["student"]
    before = User.objects.filter(pk=student.pk).values().get()
    _ok(client_for(student).patch("/api/auth/me/", {**w["bad"], "first_name": "Aline"}, format="json"))
    after = User.objects.filter(pk=student.pk).values().get()
    changed = {k for k in after if after[k] != before[k]}
    assert changed == {"first_name"}, changed


def test_admin_user_edit_only_touches_role_approval_and_profile(client_for, w):
    target = w["teacher"]
    before = User.objects.filter(pk=target.pk).values().get()
    payload = {**w["bad"], "role": "teacher", "teacher_approved": False}
    _ok(client_for(w["admin"]).patch(f"/api/admin/users/{target.id}/", payload, format="json"))
    after = User.objects.filter(pk=target.pk).values().get()
    changed = {k for k in after if after[k] != before[k]}
    assert changed <= {"teacher_approved", "teacher_revoked"}, changed
    assert not after["is_superuser"] and not after["is_staff"] and after["xp"] == 0


def test_school_edit_cannot_touch_status_code_or_subscription(client_for, w):
    school = w["school"]
    before = School.objects.filter(pk=school.pk).values().get()
    _ok(
        client_for(w["school_admin"]).patch(
            "/api/school/", {**w["bad"], "name": "Renamed", "status": "pending", "phone": "+250 1"}, format="json"
        )
    )
    after = School.objects.filter(pk=school.pk).values().get()
    assert {k for k in after if after[k] != before[k]} == {"phone"}
    # Platform admins may rename a school, but not set its code, status or paid-through date this way.
    _ok(
        client_for(w["admin"]).patch(
            f"/api/admin/schools/{school.id}/", {**w["bad"], "status": "pending", "phone": "+250 2"}, format="json"
        )
    )
    after = School.objects.filter(pk=school.pk).values().get()
    assert (after["status"], after["join_code"], after["paid_until"], after["verified_at"]) == (
        before["status"],
        before["join_code"],
        before["paid_until"],
        before["verified_at"],
    )


def test_payments_take_the_server_price(client_for, w, settings):
    settings.BILLING_DEV_MODE = True
    data = _ok(
        client_for(w["school_admin"]).post("/api/billing/checkout/", {**w["bad"], "months": 3, "currency": "USD"}, format="json")
    ).data
    payment = Payment.objects.get(reference=data["reference"])
    assert payment.amount == settings.SUBSCRIPTION_PRICES["USD"] * 3 and payment.school == w["school"]
    assert payment.provider == "dev" and payment.status == "pending" and payment.created_by == w["school_admin"]
    manual = {**w["bad"], "months": 1, "amount": "150.00", "currency": "USD", "note": "Bank transfer"}
    data = _ok(client_for(w["admin"]).post(f"/api/admin/schools/{w['school'].id}/payments/", manual, format="json")).data
    payment = Payment.objects.get(reference=data["reference"])
    assert payment.provider == "manual" and payment.status == "succeeded" and payment.reference != "TAMPERED-REF"
    assert payment.school == w["school"] and payment.created_by == w["admin"]


def test_a_ledger_correction_sets_only_its_amount_months_and_note(client_for, w):
    school = w["school"]
    before = School.objects.get(pk=school.pk).paid_until
    body = {
        **w["bad"],
        "school": w["other"].id,
        "kind": "correction",
        "currency": "USD",
        "amount": "-5.00",
        "months": 0,
        "note": "Overcharged by 5",
        "sequence": 1,
        "net_amount": "999.00",
        "entry_hash": "0" * 64,
        "prev_hash": "f" * 64,
        "actor_name": "someone-else",
        "actor_user_id": w["victim"].id,
    }
    data = _ok(client_for(w["admin"]).post(f"/api/admin/schools/{school.id}/ledger/", body, format="json")).data
    entry = LedgerEntry.objects.get(sequence=data["sequence"])
    assert entry.school == school and entry.kind == "correction" and entry.gross_amount == Decimal("-5.00")
    assert entry.net_amount == Decimal("-5.00") and entry.provider_fee == 0 and entry.months == 0
    assert entry.actor_user_id == w["admin"].id and entry.actor_name == "iga" and entry.reference == ""
    assert (
        entry.prev_hash != "f" * 64 and entry.entry_hash != "0" * 64 and entry.created_at > timezone.now() - timedelta(minutes=1)
    )
    assert School.objects.get(pk=school.pk).paid_until == before
    assert School.objects.get(pk=w["other"].pk).ledger_entries.count() == 0


def test_choosing_a_school_cannot_approve_yourself(client_for, w):
    joiner = make_user("joiner", school=None)
    _ok(client_for(joiner).post("/api/my-school/", {**w["bad"], "school": w["school"].id}, format="json"))
    joiner.refresh_from_db()
    assert joiner.school == w["school"] and joiner.school_status == "pending" and joiner.school_approved_by is None


def test_lesson_writes_keep_author_status_and_review(client_for, w):
    teacher = w["teacher"]
    payload = {
        **w["bad"],
        "unit": w["unit"].id,
        "slug": "my-lesson",
        "title": "Mine",
        "body": "x",
        "status": "published",
        "is_free": False,
        "translations": [{"language": "fr", "title": "T", "body": "B", "reviewed": True}],
    }
    _ok(client_for(teacher).post("/api/lessons/", payload, format="json"))
    lesson = Lesson.objects.get(slug="my-lesson")
    assert lesson.author == teacher and lesson.status == "review" and lesson.is_free
    assert lesson.translations.get().reviewed is False
    _ok(
        client_for(teacher).patch(
            f"/api/lessons/{lesson.slug}/", {**w["bad"], "status": "published", "title": "Edited"}, format="json"
        )
    )
    lesson.refresh_from_db()
    assert lesson.author == teacher and lesson.status == "review" and lesson.id != 999999


def test_resource_writes_keep_uploader_status_and_official_flag(client_for, w):
    payload = {
        **w["bad"],
        "subject": w["subject"].id,
        "kind": "notes",
        "title": "Notes",
        "url": "https://example.com/n",
        "status": "published",
    }
    data = _ok(client_for(w["teacher"]).post("/api/resources/", payload, format="json")).data
    resource = Resource.objects.get(pk=data["id"])
    assert (resource.uploaded_by, resource.status, resource.is_official, resource.content_id) == (
        w["teacher"],
        "review",
        False,
        "",
    )
    _ok(client_for(w["teacher"]).patch(f"/api/resources/{resource.id}/", {**w["bad"], "status": "published"}, format="json"))
    resource.refresh_from_db()
    assert (resource.uploaded_by, resource.status, resource.is_official) == (w["teacher"], "review", False)


def test_question_and_quiz_writes_keep_author_status_and_price_flag(client_for, w):
    teacher = w["teacher"]
    question = {
        **w["bad"],
        "subject": w["subject"].id,
        "grade": "S2",
        "type": "essay",
        "prompt": "Explain.",
        "status": "draft",
        "choices": [],
    }
    data = _ok(client_for(teacher).post("/api/questions/", question, format="json")).data
    q = Question.objects.get(pk=data["id"])
    assert q.author == teacher and q.source == "custom"
    library = add_mcq(w["subject"], w["unit"], prompt="Library question")  # no author: premium library
    quiz = {
        **w["bad"],
        "title": "My quiz",
        "subject": w["subject"].id,
        "grade": "S2",
        "status": "published",
        "is_free": True,
        "question_ids": [q.id, library.id],
    }
    data = _ok(client_for(teacher).post("/api/quizzes/", quiz, format="json")).data
    made = Quiz.objects.get(pk=data["id"])
    # Library questions can't be repackaged into a free quiz, and the public library needs approval.
    assert made.author == teacher and made.status == "review" and not made.is_free
    _ok(
        client_for(teacher).patch(f"/api/quizzes/{made.id}/", {**w["bad"], "is_free": True, "status": "published"}, format="json")
    )
    made.refresh_from_db()
    assert made.author == teacher and made.status == "review" and not made.is_free


def test_answers_cannot_carry_their_own_marks(client_for, w):
    question = add_mcq(w["subject"], w["unit"])
    quiz = Quiz.objects.create(subject=w["subject"], unit=w["unit"], title="Q", grade="S2", status="published", is_free=True)
    QuizQuestion.objects.create(quiz=quiz, question=question, order=0)
    client = client_for(w["student"])
    attempt_id = _ok(client.post(f"/api/quizzes/{quiz.id}/start/", w["bad"], format="json")).data["id"]
    attempt = Attempt.objects.get(pk=attempt_id)
    assert attempt.user == w["student"] and attempt.deadline is None and attempt.question_order == [question.id]
    wrong = question.choices.filter(is_correct=False).first()
    _ok(
        client.post(
            f"/api/attempts/{attempt_id}/answer/", {**w["bad"], "question": question.id, "choice_ids": [wrong.id]}, format="json"
        )
    )
    answer = Answer.objects.get(attempt=attempt)
    assert answer.marks_awarded is None and answer.is_correct is None and not answer.checked
    _ok(client.post(f"/api/attempts/{attempt_id}/submit/", w["bad"], format="json"))
    attempt.refresh_from_db()
    assert attempt.score == Decimal("0") and attempt.max_score == question.marks


def test_teacher_marks_stay_within_the_question(client_for, w):
    essay = Question.objects.create(subject=w["subject"], grade="S2", type="essay", prompt="Why?", marks=2)
    quiz = Quiz.objects.create(subject=w["subject"], title="E", grade="S2", status="published", is_free=True)
    classroom = Classroom.objects.create(name="S2", grade="S2", teacher=w["teacher"])
    Enrollment.objects.create(classroom=classroom, student=w["student"])
    attempt = Attempt.objects.create(user=w["student"], quiz=quiz, status="needs_marking", question_order=[essay.id], max_score=2)
    answer = Answer.objects.create(attempt=attempt, question=essay, text_answer="Because.")
    client = client_for(w["teacher"])
    assert client.post(f"/api/marking/{answer.id}/mark/", {**w["bad"], "marks": "5"}, format="json").status_code == 400
    _ok(client.post(f"/api/marking/{answer.id}/mark/", {**w["bad"], "marks": "1.5", "feedback": "ok"}, format="json"))
    answer.refresh_from_db()
    assert answer.marks_awarded == Decimal("1.5") and answer.marked_by == w["teacher"] and answer.attempt_id == attempt.id


def test_class_assignment_and_group_writes_keep_their_owners(client_for, w):
    teacher, student = w["teacher"], w["student"]
    data = _ok(client_for(teacher).post("/api/classes/", {**w["bad"], "name": "S2 A", "grade": "S2"}, format="json")).data
    classroom = Classroom.objects.get(pk=data["id"])
    assert classroom.teacher == teacher and classroom.join_code != "HACKED99"
    _ok(client_for(teacher).patch(f"/api/classes/{classroom.id}/", {**w["bad"], "name": "S2 B"}, format="json"))
    classroom.refresh_from_db()
    assert classroom.teacher == teacher and classroom.join_code != "HACKED99" and classroom.name == "S2 B"

    _ok(client_for(student).post("/api/classes/join/", {**w["bad"], "code": classroom.join_code}, format="json"))
    assert Enrollment.objects.get(classroom=classroom).student == student

    quiz = Quiz.objects.create(subject=w["subject"], title="Q", grade="S2", status="published", is_free=True)
    payload = {**w["bad"], "classroom": classroom.id, "quiz": quiz.id, "title": "Homework"}
    data = _ok(client_for(teacher).post("/api/assignments/", payload, format="json")).data
    assert Assignment.objects.get(pk=data["id"]).created_by == teacher

    data = _ok(client_for(student).post("/api/groups/", {**w["bad"], "name": "Squad"}, format="json")).data
    group = StudyGroup.objects.get(pk=data["id"])
    assert group.created_by == student and group.join_code != "HACKED99"
    assert list(group.memberships.values_list("user", "role")) == [(student.id, "owner")]
    _ok(
        client_for(student).post(
            f"/api/groups/{group.id}/messages/", {**w["bad"], "body": "hi", "is_hidden": True}, format="json"
        )
    )
    message = Message.objects.get(group=group)
    assert message.author == student and not message.is_hidden
    _ok(client_for(student).post(f"/api/groups/{group.id}/notes/", {**w["bad"], "title": "N", "body": "b"}, format="json"))
    assert SharedNote.objects.get(group=group).author == student
    friend = make_user("friend", school=w["school"])
    _ok(client_for(friend).post(f"/api/groups/{group.id}/join/", w["bad"], format="json"))
    assert GroupMembership.objects.get(group=group, user=friend).role == "member"
    _ok(client_for(friend).post(f"/api/messages/{message.id}/report/", {**w["bad"], "reason": "rude"}, format="json"))
    report = MessageReport.objects.get(message=message)
    assert report.reporter == friend and not report.resolved
    _ok(client_for(student).patch(f"/api/groups/{group.id}/", {**w["bad"], "name": "Squad 2"}, format="json"))
    group.refresh_from_db()
    assert group.created_by == student and group.join_code != "HACKED99"


def test_rewards_are_decided_by_the_server(client_for, w):
    lesson = Lesson.objects.create(unit=w["unit"], slug="free", title="Free", body="x", status="published", is_free=True)
    client = client_for(w["student"])
    data = _ok(client.post(f"/api/lessons/{lesson.slug}/complete/", w["bad"], format="json")).data
    assert data["xp"] < 1000 and LessonProgress.objects.filter(user=w["student"], lesson=lesson).count() == 1


def test_study_feature_writes_decide_owner_and_grading_on_the_server(client_for, w):
    from apps.notes.models import LessonBookmark, LessonNote
    from apps.planner.models import ExamDate, StudyPlan
    from apps.review.models import ReviewItem

    student = w["student"]
    lesson = Lesson.objects.create(unit=w["unit"], slug="study-lesson", title="Study", body="x", status="published", is_free=True)
    client = client_for(student)

    # Study plan: the weekly goal is stored; the owner is the requester, whatever ids are in the body.
    _ok(client.put("/api/planner/", {**w["bad"], "weekly_goal_lessons": 4}, format="json"))
    assert StudyPlan.objects.get(user=student).weekly_goal_lessons == 4
    assert not StudyPlan.objects.exclude(user=student).exists()

    # Exam date: only title and date are taken; the owner is the requester and the id is server-chosen.
    date = (timezone.localdate() + timedelta(days=100)).isoformat()
    data = _ok(client.post("/api/planner/exams/", {**w["bad"], "title": "Mock", "date": date}, format="json")).data
    exam = ExamDate.objects.get(pk=data["id"])
    assert exam.user == student and exam.id != 999999 and exam.title == "Mock"

    # Bookmark and note: the owner is the requester.
    data = _ok(client.post("/api/bookmarks/", {**w["bad"], "lesson": lesson.slug}, format="json")).data
    assert LessonBookmark.objects.get(pk=data["id"]).user == student
    data = _ok(client.post("/api/notes/", {**w["bad"], "lesson": lesson.slug, "body": "my note"}, format="json")).data
    note = LessonNote.objects.get(pk=data["id"])
    assert note.user == student and note.body == "my note"

    # A review answer: correctness and the Leitner box are decided by the server, never by the client.
    question = add_mcq(w["subject"], w["unit"])
    item = ReviewItem.objects.create(user=student, question=question, due_on=timezone.localdate())
    wrong = question.choices.filter(is_correct=False).first()
    _ok(
        client.post(
            f"/api/review/{item.id}/answer/",
            {**w["bad"], "choice_ids": [wrong.id], "is_correct": True, "box": 9},
            format="json",
        )
    )
    item.refresh_from_db()
    assert item.box == 0 and item.times_seen == 1  # a wrong answer stays in box 1 (0-based), not box 9


def test_roster_columns_cannot_create_privileged_accounts(client_for, w):
    classroom = Classroom.objects.create(name="S2", grade="S2", teacher=w["teacher"])
    csv = "first_name,last_name,role,is_staff,is_superuser,school_status\nAline,Uwase,admin,true,true,approved\n"
    _ok(
        client_for(w["teacher"]).post(f"/api/classes/{classroom.id}/import_roster/", {"csv": csv, "confirm": True}, format="json")
    )
    created = User.objects.get(first_name="Aline")
    assert created.role == "student" and not created.is_staff and not created.is_superuser and created.must_change_password


# Writable routes where no stored row takes fields from the request body (only an id, a code or a
# password, all checked), so there is nothing to tamper with.
NOTHING_TO_TAMPER = {
    "api/auth/login/",
    "api/auth/refresh/",
    "api/auth/logout/",
    "api/auth/password/",
    "api/auth/2fa/setup/",
    "api/auth/2fa/enable/",
    "api/auth/2fa/disable/",
    "api/auth/step-up/",
    "api/auth/logout-all/",
    "api/auth/password-reset/",
    "api/auth/parent-code/",
    "api/children/",
    "api/tutor/ask/",
    "api/tutor/stream/",
    "api/code/run/",
    "api/code/input/",
    "api/code/stop/",
    "api/school/members/decide/",
    "api/school/members/{user_id}/remove/",
    "api/school/new-code/",
    "api/billing/payments/{reference}/confirm/",
    "api/billing/dev/{reference}/complete/",
    "api/billing/webhooks/flutterwave/",
    "api/admin/schools/{school_id}/members/",
    "api/admin/schools/{school_id}/{action}/",
    "api/simulations/{slug}/view/",
    "api/classes/{pk}/leave/",
    "api/classes/{pk}/new_code/",
    "api/classes/{pk}/remove_student/",
    "api/classes/{pk}/reset_password/",
    "api/groups/join-by-code/",
    "api/groups/{pk}/leave/",
    "api/messages/{pk}/hide/",
    "api/attempts/{pk}/check/",
    "api/admin/review/decide/",
    "api/admin/moderation/{pk}/resolve/",
}
# Covered by the tests above.
TESTED = {
    "api/auth/register/",
    "api/auth/me/",
    "api/auth/password-reset/confirm/",
    "api/admin/users/{pk}/",
    "api/school/",
    "api/admin/schools/{school_id}/",
    "api/billing/checkout/",
    "api/admin/schools/{school_id}/payments/",
    "api/admin/schools/{school_id}/ledger/",
    "api/my-school/",
    "api/lessons/",
    "api/lessons/{slug}/",
    "api/lessons/{slug}/complete/",
    "api/resources/",
    "api/resources/{pk}/",
    "api/questions/",
    "api/questions/{pk}/",
    "api/quizzes/",
    "api/quizzes/{pk}/",
    "api/quizzes/{pk}/start/",
    "api/attempts/{pk}/answer/",
    "api/attempts/{pk}/submit/",
    "api/marking/{pk}/mark/",
    "api/classes/",
    "api/classes/{pk}/",
    "api/classes/join/",
    "api/classes/{pk}/import_roster/",
    "api/assignments/",
    "api/assignments/{pk}/",
    "api/groups/",
    "api/groups/{pk}/",
    "api/groups/{pk}/join/",
    "api/groups/{pk}/messages/",
    "api/groups/{pk}/notes/",
    "api/messages/{pk}/report/",
    "api/auth/accept-terms/",
    "api/auth/delete-account/",
    "api/contact/",
    "api/admin/contact/{pk}/handle/",
    "api/planner/",
    "api/planner/exams/",
    "api/bookmarks/",
    "api/notes/",
    "api/teaching/packs/",
    "api/teaching/packs/{pk}/",
    "api/teaching/packs/{pk}/assign/",
    "api/review/{pk}/answer/",
}


# The router maps POST here, but the view refuses it (users are created by signing up, not by admins).
REFUSED = {"api/admin/users/"}


def test_admins_cannot_create_users_directly(client_for, w):
    assert client_for(w["admin"]).post("/api/admin/users/", {**w["bad"], "username": "x"}, format="json").status_code == 405


def test_every_writable_route_is_covered():
    writable = {route for route, callback in api_routes() if set(view_methods(callback)) & {"POST", "PUT", "PATCH"}}
    missing = writable - NOTHING_TO_TAMPER - TESTED - REFUSED
    assert not missing, f"New writable routes: add a tampering test (or explain why there is nothing to tamper with): {missing}"


def test_teaching_pack_writes_keep_owner_document_and_class(client_for, w):
    from apps.classroom.models import Classroom
    from apps.teaching.models import TeachingPack

    teacher = w["teacher"]
    mine = Classroom.objects.create(name="Mine", subject=w["subject"], grade="S2", teacher=teacher)
    elsewhere = Classroom.objects.create(name="Theirs", subject=w["subject"], grade="S2", teacher=w["victim"])
    client = client_for(teacher)

    # Creating: the author is the requester, the document is built by the server, and Santa did not write it.
    payload = {**w["bad"], "classroom": mine.id, "unit": w["unit"].id, "document": {"evil": True}, "ai_used": True}
    pack = TeachingPack.objects.get(pk=_ok(client.post("/api/teaching/packs/", payload, format="json")).data["id"])
    assert pack.created_by == teacher and pack.classroom == mine and "evil" not in pack.document and not pack.ai_used

    # Editing: only the lesson plan's text changes.
    before = pack.document
    _ok(
        client.patch(
            f"/api/teaching/packs/{pack.id}/",
            {**w["bad"], "plan": {"objective": "Mine"}, "document": {"evil": True}, "classroom": elsewhere.id, "ai_used": True},
            format="json",
        )
    )
    pack.refresh_from_db()
    assert pack.document == before and pack.classroom == mine and pack.created_by == teacher and not pack.ai_used
    assert pack.plan_edits == {"objective": "Mine"}


def test_assigning_a_pack_decides_author_class_and_price_on_the_server(client_for, w):
    from apps.assessments.models import Quiz
    from apps.classroom.models import Assignment, Classroom
    from apps.teaching.models import TeachingPack

    teacher = w["teacher"]
    mine = Classroom.objects.create(name="Mine", subject=w["subject"], grade="S2", teacher=teacher)
    elsewhere = Classroom.objects.create(name="Theirs", subject=w["subject"], grade="S2", teacher=w["victim"])
    add_mcq(w["subject"], w["unit"])
    client = client_for(teacher)
    pack_id = _ok(client.post("/api/teaching/packs/", {"classroom": mine.id, "unit": w["unit"].id}, format="json")).data["id"]
    payload = {
        **w["bad"],
        "what": "quiz",
        "classroom": elsewhere.id,
        "quiz": 999999,
        "assignment": 999999,
        "is_free": True,
        "status": "draft",
        "title": "Hijacked",
    }
    data = _ok(client.post(f"/api/teaching/packs/{pack_id}/assign/", payload, format="json")).data
    quiz, assignment = Quiz.objects.get(pk=data["quiz_id"]), Assignment.objects.get(pk=data["assignment_id"])
    assert (quiz.author, quiz.is_free, quiz.status) == (teacher, False, "draft") and quiz.title != "Hijacked"
    assert (assignment.classroom, assignment.created_by) == (mine, teacher)
    assert TeachingPack.objects.get(pk=pack_id).classroom == mine
