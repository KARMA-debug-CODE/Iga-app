"""Members of a subscribed school get everything; everyone else gets the free part only."""

from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.assessments import services
from apps.assessments.models import Attempt, ExamPaper, Question
from apps.curriculum.models import Lesson
from apps.schools.access import content_access

from . import samples
from .conftest import add_mcq, make_quiz, make_school, make_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def apade_student(db):
    """A student at a verified school that hasn't paid."""
    return make_user("samuel", school=make_school("APADE", "Kicukiro"))


@pytest.fixture
def premium_lesson(unit):
    return Lesson.objects.create(
        unit=unit, slug="premium", title="Premium", summary="Teaser", body="SECRET BODY", status="published"
    )


@pytest.fixture
def free_lesson(unit):
    return Lesson.objects.create(
        unit=unit, slug="free", title="Free", body="Open body", status="published", is_free=True, order=0
    )


# --- The access rule --------------------------------------------------------------


@pytest.mark.parametrize(
    ("setup", "premium", "reason"),
    [
        ("subscribed", True, ""),
        ("no_school", False, "no_school"),
        ("not_paid", False, "not_subscribed"),
        ("expired", False, "expired"),
        ("grace", True, ""),
        ("pending", False, "pending_approval"),
        ("unverified", False, "school_not_verified"),
        ("suspended", False, "school_suspended"),
        ("parent", False, "not_eligible"),
    ],
)
def test_access_rule(setup, premium, reason, settings):
    settings.SUBSCRIPTION_GRACE_DAYS = 3
    now = timezone.now()
    if setup == "subscribed":
        user = make_user("u")
    elif setup == "no_school":
        user = make_user("u", school=None)
    elif setup == "not_paid":
        user = make_user("u", school=make_school())
    elif setup == "expired":
        user = make_user("u", school=make_school(paid_until=now - timedelta(days=4)))
    elif setup == "grace":
        user = make_user("u", school=make_school(paid_until=now - timedelta(days=1)))
    elif setup == "pending":
        user = make_user("u", school=make_school(paid_until=now + timedelta(days=30)))
        user.school_status = "pending"
        user.save()
    elif setup == "unverified":
        user = make_user("u", school=make_school(paid_until=now + timedelta(days=30), status="pending"))
    elif setup == "suspended":
        user = make_user("u", school=make_school(paid_until=now + timedelta(days=30), status="suspended"))
    else:
        user = make_user("u", role="parent")
    result = content_access(user)
    assert (result.premium, result.reason) == (premium, reason)


def test_platform_admins_always_have_access(admin_user):
    assert content_access(admin_user).premium


# --- Lessons ----------------------------------------------------------------------


def test_locked_lesson_shows_teaser_without_body(client_for, apade_student, premium_lesson, free_lesson):
    client = client_for(apade_student)
    data = client.get(f"/api/lessons/{premium_lesson.slug}/").data
    assert data["locked"] and data["body"] == "" and data["summary"] == "Teaser"
    assert data["access_reason"] == "not_subscribed"
    assert client.get(f"/api/lessons/{free_lesson.slug}/").data["body"] == "Open body"
    units = client.get("/api/subjects/mathematics/?grade=S2").data["units"]
    flags = {les["slug"]: les["locked"] for les in units[0]["lessons"]}
    assert flags == {"premium": True, "free": False}


def test_subscribed_student_reads_everything(client_for, student, premium_lesson):
    data = client_for(student).get(f"/api/lessons/{premium_lesson.slug}/").data
    assert not data["locked"] and data["body"] == "SECRET BODY"


def test_locked_lessons_cannot_be_completed_for_xp(client_for, apade_student, premium_lesson):
    response = client_for(apade_student).post(f"/api/lessons/{premium_lesson.slug}/complete/")
    assert response.status_code == 403
    assert response.data["detail"].code == "subscription_required"


def test_locked_translation_is_withheld_too(client_for, apade_student, premium_lesson):
    from apps.curriculum.models import LessonTranslation

    LessonTranslation.objects.create(lesson=premium_lesson, language="fr", title="Premium FR", body="CORPS SECRET")
    data = client_for(apade_student).get(f"/api/lessons/{premium_lesson.slug}/?lang=fr").data
    assert data["body"] == "" and data["title"] == "Premium FR"


def test_search_does_not_reveal_locked_lesson_text(client_for, apade_student, student, premium_lesson):
    assert client_for(apade_student).get("/api/search/", {"q": "SECRET"}).data["lessons"] == []
    found = client_for(student).get("/api/search/", {"q": "SECRET"}).data["lessons"]
    assert [les["slug"] for les in found] == ["premium"]
    # Titles still match, flagged as locked.
    titles = client_for(apade_student).get("/api/search/", {"q": "Premium"}).data["lessons"]
    assert titles[0]["locked"] is True


def test_continue_learning_suggests_open_lessons(client_for, apade_student, premium_lesson, free_lesson):
    data = client_for(apade_student).get("/api/dashboard/").data
    assert data["continue_learning"]["slug"] == "free"


# --- Quizzes, attempts and past papers -------------------------------------------------


def test_premium_quiz_cannot_be_started(client_for, apade_student, quiz_factory):
    quiz = quiz_factory()
    client = client_for(apade_student)
    listed = client.get("/api/quizzes/").data["results"]
    assert listed[0]["locked"] is True
    response = client.post(f"/api/quizzes/{quiz.id}/start/")
    assert response.status_code == 403 and response.data["detail"].code == "subscription_required"
    free = quiz_factory(title="Free quiz", is_free=True)
    assert client.post(f"/api/quizzes/{free.id}/start/").status_code == 201


def test_an_assignment_does_not_grant_access(client_for, teacher, apade_student, quiz_factory):
    from apps.classroom.models import Assignment, Classroom, Enrollment

    quiz = quiz_factory()
    classroom = Classroom.objects.create(name="C", grade="S2", teacher=teacher)
    Enrollment.objects.create(classroom=classroom, student=apade_student)
    assignment = Assignment.objects.create(classroom=classroom, quiz=quiz, title="HW", created_by=teacher)
    client = client_for(apade_student)
    assert client.get("/api/assignments/").data["results"][0]["locked"] is True
    response = client.post(f"/api/quizzes/{quiz.id}/start/", {"assignment": assignment.id}, format="json")
    assert response.status_code == 403


def test_lapsed_access_closes_open_attempts(client_for, quiz_factory):
    school = make_school("Lapsing", "Huye", paid_until=timezone.now() + timedelta(days=10))
    pupil = make_user("pupil", school=school)
    quiz = quiz_factory()
    attempt = services.start_attempt(pupil, quiz)
    question = Question.objects.get(pk=attempt.question_order[0])
    services.save_answer(attempt, question.id, choice_ids=[question.choices.get(is_correct=True).id])
    school.paid_until = timezone.now() - timedelta(days=30)
    school.save()

    client = client_for(type(pupil).objects.get(pk=pupil.pk))
    check = client.post(f"/api/attempts/{attempt.id}/check/", {"question": question.id}, format="json")
    assert check.status_code == 400  # the attempt was closed instead of revealing the answer
    data = client.get(f"/api/attempts/{attempt.id}/").data
    assert data["status"] != "in_progress"
    assert data["quiz"]["locked"] is True
    assert all(q["solution"]["explanation"] == "" for q in data["questions"] if q["solution"])
    assert Attempt.objects.get(pk=attempt.id).score is not None  # their work still counts


def test_past_paper_links_are_withheld_when_locked(client_for, apade_student, student, subject, unit, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    quiz = make_quiz(subject, unit, [add_mcq(subject, unit)], kind="past_paper")
    paper = ExamPaper.objects.create(subject=subject, level="O", year=2024, title="Maths 2024", quiz=quiz)
    secret = samples.pdf(samples.stream(b"/Type /XObject /Subtype /Form", b"secret paper"))
    paper.paper_file.save("paper.pdf", ContentFile(secret))
    paper.marking_guide_url = "https://example.org/guide.pdf"
    paper.save()

    locked = client_for(apade_student).get(f"/api/exam-papers/{paper.id}/").data
    assert locked["locked"] and locked["paper_link"] is None and locked["marking_guide_link"] is None

    open_ = client_for(student).get(f"/api/exam-papers/{paper.id}/").data
    assert not open_["locked"] and open_["marking_guide_link"] == "https://example.org/guide.pdf"
    link = open_["paper_link"]
    assert "/api/files/papers/" in link and "/media/" not in link
    download = client_for().get(link.replace("http://testserver", ""))
    assert download.status_code == 200 and b"".join(download.streaming_content) == secret
    assert download["Cache-Control"] == "private, no-store"


def test_download_links_are_rechecked_and_expire(client_for, student, subject, unit, settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path
    paper = ExamPaper.objects.create(subject=subject, level="O", year=2023, title="Maths 2023")
    paper.paper_file.save("p.pdf", ContentFile(samples.pdf()))
    link = client_for(student).get(f"/api/exam-papers/{paper.id}/").data["paper_link"].replace("http://testserver", "")
    # The student's school stops paying: the old link no longer works.
    school = student.school
    school.paid_until = timezone.now() - timedelta(days=30)
    school.save()
    assert client_for().get(link).status_code == 403
    assert client_for().get("/api/files/papers/forged-token/").status_code == 404

    from apps.schools import downloads

    school.paid_until = timezone.now() + timedelta(days=30)
    school.save()
    monkeypatch.setattr(downloads, "LINK_SECONDS", -1)
    assert client_for().get(link).status_code == 404  # expired


def test_protected_files_use_nginx_internal_redirect(client_for, student, subject, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.PROTECTED_MEDIA_ACCEL = True
    paper = ExamPaper.objects.create(subject=subject, level="A", year=2022, title="Paper")
    paper.paper_file.save("x.pdf", ContentFile(samples.pdf()))
    link = client_for(student).get(f"/api/exam-papers/{paper.id}/").data["paper_link"].replace("http://testserver", "")
    response = client_for().get(link)
    assert response["X-Accel-Redirect"] == f"/protected-media/{paper.paper_file.name}"


# --- Teachers --------------------------------------------------------------------------


def test_library_questions_stay_premium_for_teachers(client_for, subject, unit):
    library = add_mcq(subject, unit, "Library question?")
    teacher = make_user("unpaidteacher", role="teacher", teacher_approved=True, school=make_school("Unpaid", "Huye"))
    own = add_mcq(subject, unit, "My own question?")
    own.author = teacher
    own.status = "published"
    own.save()
    library.status = "published"
    library.save()
    client = client_for(teacher)
    prompts = {q["prompt"] for q in client.get("/api/questions/").data["results"]}
    assert prompts == {"My own question?"}
    response = client.post(
        "/api/quizzes/",
        {"title": "Repackaged", "subject": subject.id, "grade": "S2", "question_ids": [library.id]},
        format="json",
    )
    assert response.status_code == 400


def test_teacher_quizzes_are_free_only_without_library_questions(client_for, teacher, subject, unit):
    own = add_mcq(subject, unit, "Mine?")
    own.author = teacher
    own.save()
    library = add_mcq(subject, unit, "Library?")
    client = client_for(teacher)  # subscribed school: may use library questions
    mine = client.post(
        "/api/quizzes/", {"title": "Mine", "subject": subject.id, "grade": "S2", "question_ids": [own.id]}, format="json"
    )
    mixed = client.post(
        "/api/quizzes/",
        {"title": "Mixed", "subject": subject.id, "grade": "S2", "question_ids": [own.id, library.id]},
        format="json",
    )
    from apps.assessments.models import Quiz

    assert Quiz.objects.get(pk=mine.data["id"]).is_free is True
    assert Quiz.objects.get(pk=mixed.data["id"]).is_free is False
    # Teachers can't simply declare a quiz free.
    client.patch(f"/api/quizzes/{mixed.data['id']}/", {"is_free": True}, format="json")
    assert Quiz.objects.get(pk=mixed.data["id"]).is_free is False


def test_teacher_lessons_are_free(client_for, teacher, unit):
    response = client_for(teacher).post(
        "/api/lessons/", {"unit": unit.id, "slug": "mine", "title": "Mine", "body": "x", "is_free": False}, format="json"
    )
    assert response.status_code == 201
    assert Lesson.objects.get(slug="mine").is_free is True


# --- The AI tutor ------------------------------------------------------------------------


def test_tutor_needs_a_subscription(client_for, apade_student):
    client = client_for(apade_student)
    assert client.get("/api/tutor/status/").data == {
        "enabled": False,
        "reason": "subscription_required",
        "state": "",
        "exam": None,
        "allowance": None,
    }
    for path in ("/api/tutor/ask/", "/api/tutor/stream/"):
        response = client.post(path, {"message": "help"}, format="json")
        assert response.status_code == 403 and response.data["detail"].code == "subscription_required"


# --- Teachers see premium answer keys only with the subscription ---------------------------


@pytest.fixture
def unpaid_teacher(db):
    return make_user("unpaidteacher", role="teacher", teacher_approved=True, school=make_school("Unpaid", "Huye"))


def _premium_essay_attempt(client_for, student, teacher, subject, unit):
    from apps.classroom.models import Classroom, Enrollment

    essay = Question.objects.create(
        subject=subject,
        grade="S2",
        unit=unit,
        type=Question.Type.ESSAY,
        prompt="PREMIUM ESSAY",
        marks=4,
        marking_guide="PREMIUM GUIDE",
    )
    quiz = make_quiz(subject, unit, [add_mcq(subject, unit, "PREMIUM MCQ"), essay], feedback_mode="after_submit")
    classroom = Classroom.objects.create(name="Maths", grade="S2", teacher=teacher, subject=subject)
    Enrollment.objects.create(classroom=classroom, student=student)
    client = client_for(student)  # a student of a subscribed school
    attempt = client.post(f"/api/quizzes/{quiz.id}/start/").data
    essay_id = next(q["id"] for q in attempt["questions"] if q["type"] == "essay")
    client.post(f"/api/attempts/{attempt['id']}/answer/", {"question": essay_id, "text": "Because..."}, format="json")
    client.post(f"/api/attempts/{attempt['id']}/submit/")
    return quiz, attempt["id"]


def test_unsubscribed_teachers_get_no_premium_marking_guides(client_for, student, teacher, unpaid_teacher, subject, unit):
    _premium_essay_attempt(client_for, student, unpaid_teacher, subject, unit)
    item = client_for(unpaid_teacher).get("/api/marking/").data[0]
    assert item["answer_text"] == "Because..." and item["marking_guide"] == ""
    from apps.classroom.models import Classroom, Enrollment

    classroom = Classroom.objects.create(name="Paid", grade="S2", teacher=teacher, subject=subject)
    Enrollment.objects.create(classroom=classroom, student=student)
    assert client_for(teacher).get("/api/marking/").data[0]["marking_guide"] == "PREMIUM GUIDE"


def test_unsubscribed_teachers_see_only_the_score_of_premium_attempts(client_for, student, unpaid_teacher, subject, unit):
    _, attempt_id = _premium_essay_attempt(client_for, student, unpaid_teacher, subject, unit)
    seen = client_for(unpaid_teacher).get(f"/api/attempts/{attempt_id}/").data
    assert seen["questions"] == [] and seen["quiz"]["locked"] is True
    assert "PREMIUM" not in str(seen)
    own = client_for(student).get(f"/api/attempts/{attempt_id}/").data
    assert {q["prompt"] for q in own["questions"]} == {"PREMIUM MCQ", "PREMIUM ESSAY"}


def test_authors_lose_library_answer_keys_with_the_subscription(client_for, subject, unit):
    school = make_school("Lapsing", "Huye", paid_until=timezone.now() + timedelta(days=30))
    author = make_user("author", role="teacher", teacher_approved=True, school=school)
    library = add_mcq(subject, unit, "Library question?")
    library.status = "published"
    library.save()
    own = add_mcq(subject, unit, "My question?")
    own.author = author
    own.save()
    client = client_for(author)
    mixed = client.post(
        "/api/quizzes/", {"title": "Mixed", "subject": subject.id, "grade": "S2", "question_ids": [library.id]}, format="json"
    ).data
    mine = client.post(
        "/api/quizzes/", {"title": "Mine", "subject": subject.id, "grade": "S2", "question_ids": [own.id]}, format="json"
    ).data
    assert client.get(f"/api/quizzes/{mixed['id']}/analytics/").status_code == 200
    school.paid_until = timezone.now() - timedelta(days=30)
    school.save()
    from apps.accounts.models import User

    client = client_for(User.objects.get(pk=author.pk))  # a new request, without the cached access
    assert client.get(f"/api/quizzes/{mixed['id']}/analytics/").status_code == 403
    assert client.get(f"/api/quizzes/{mine['id']}/analytics/").status_code == 200  # their own free material


# --- Upgrading an existing database --------------------------------------------------------


def _migration(name):
    import importlib

    return importlib.import_module(f"apps.assessments.migrations.{name}")


def test_upgrade_keeps_repackaged_library_questions_premium(teacher, subject, unit):
    from django.apps import apps as registry

    from apps.assessments.models import Quiz

    library = add_mcq(subject, unit, "Library?")
    own = add_mcq(subject, unit, "Mine?")
    own.author = teacher
    own.save()
    repack = make_quiz(subject, unit, [own, library], title="Repack", author=teacher)
    mine = make_quiz(subject, unit, [own], title="Mine", author=teacher)
    _migration("0005_quiz_is_free").teacher_content_is_free(registry, None)
    assert Quiz.objects.get(pk=mine.pk).is_free is True
    assert Quiz.objects.get(pk=repack.pk).is_free is False
    # Databases that ran the earlier version of 0005 are corrected.
    Quiz.objects.filter(pk=repack.pk).update(is_free=True)
    _migration("0006_recheck_teacher_quizzes").lock_repackaged_library_questions(registry, None)
    assert Quiz.objects.get(pk=repack.pk).is_free is False
    assert Quiz.objects.get(pk=mine.pk).is_free is True


def test_upgrade_opens_the_starter_lessons_and_quizzes(subject, unit):
    from django.apps import apps as registry

    from apps.assessments.models import Quiz

    starter = Lesson.objects.create(unit=unit, slug="s1-maths-integers", title="Integers", body="x", status="published")
    other = Lesson.objects.create(unit=unit, slug="s1-maths-other", title="Other", body="x", status="published")
    quiz = make_quiz(subject, unit, [add_mcq(subject, unit)], title="Integers — quick practice", grade="S1")
    _migration("0007_open_starter_content").open_starter_content(registry, None)
    assert Lesson.objects.get(pk=starter.pk).is_free is True
    assert Lesson.objects.get(pk=other.pk).is_free is False
    assert Quiz.objects.get(pk=quiz.pk).is_free is True


def test_teachers_keep_their_own_marking_guides_without_the_subscription(client_for, student, subject, unit):
    from apps.classroom.models import Classroom, Enrollment

    school = make_school("Lapsing2", "Huye", paid_until=timezone.now() + timedelta(days=30))
    teacher = make_user("guideteacher", role="teacher", teacher_approved=True, school=school)
    library = add_mcq(subject, unit, "LIBRARY MCQ")
    library_essay = Question.objects.create(
        subject=subject, grade="S2", unit=unit, type=Question.Type.ESSAY, prompt="LIB ESSAY", marks=4, marking_guide="LIB GUIDE"
    )
    own_essay = Question.objects.create(
        subject=subject,
        grade="S2",
        unit=unit,
        type=Question.Type.ESSAY,
        prompt="OWN ESSAY",
        marks=4,
        marking_guide="MY OWN GUIDE",
        author=teacher,
    )
    quiz = make_quiz(subject, unit, [library, library_essay, own_essay], feedback_mode="after_submit", author=teacher)
    classroom = Classroom.objects.create(name="Maths", grade="S2", teacher=teacher, subject=subject)
    Enrollment.objects.create(classroom=classroom, student=student)
    client = client_for(student)
    attempt = client.post(f"/api/quizzes/{quiz.id}/start/").data
    for q in attempt["questions"]:
        if q["type"] == "essay":
            client.post(f"/api/attempts/{attempt['id']}/answer/", {"question": q["id"], "text": "..."}, format="json")
    client.post(f"/api/attempts/{attempt['id']}/submit/")
    school.paid_until = timezone.now() - timedelta(days=30)
    school.save()
    from apps.accounts.models import User

    guides = {
        item["question"]: item["marking_guide"] for item in client_for(User.objects.get(pk=teacher.pk)).get("/api/marking/").data
    }
    assert guides == {"LIB ESSAY": "", "OWN ESSAY": "MY OWN GUIDE"}
