import pytest

from apps.curriculum.models import Lesson, LessonTranslation, Subject, Unit

pytestmark = pytest.mark.django_db


def test_subjects_for_grade_with_progress(client_for, student, subject, lesson):
    Subject.objects.create(code="economics", name="Economics", offered_o_level=False)
    client = client_for(student)
    data = client.get("/api/subjects/?grade=S2").data
    assert [s["code"] for s in data] == ["mathematics"]  # economics is A-level only
    assert data[0]["lesson_count"] == 1 and data[0]["completed_count"] == 0

    client.post(f"/api/lessons/{lesson.slug}/complete/")
    data = client.get("/api/subjects/?grade=S2").data
    assert data[0]["completed_count"] == 1


def test_subject_detail_lists_units_and_lessons(client_for, student, subject, lesson):
    data = client_for(student).get("/api/subjects/mathematics/?grade=S2").data
    assert data["units"][0]["lessons"][0]["slug"] == "linear"


def test_lesson_translation(client_for, student, lesson):
    LessonTranslation.objects.create(lesson=lesson, language="sw", title="Grafu", body="Habari")
    client = client_for(student)
    data = client.get(f"/api/lessons/{lesson.slug}/?lang=sw").data
    assert data["title"] == "Grafu" and data["language"] == "sw"
    assert data["available_languages"] == ["en", "sw"]
    assert data["subject"]["name"] == "Hisabati"
    # Falls back to English when no translation exists.
    assert client.get(f"/api/lessons/{lesson.slug}/?lang=rw").data["title"] == "Linear graphs"


def test_draft_lessons_hidden_from_students(client_for, student, unit):
    Lesson.objects.create(unit=unit, slug="secret", title="Draft", body="x", status="draft")
    assert client_for(student).get("/api/lessons/secret/").status_code == 404


def test_teacher_lessons_go_to_review_then_admin_publishes(client_for, teacher, admin_user, student, unit):
    response = client_for(teacher).post(
        "/api/lessons/",
        {"unit": unit.id, "slug": "teacher-lesson", "title": "Mine", "body": "Content", "status": "published"},
        format="json",
    )
    assert response.status_code == 201
    lesson = Lesson.objects.get(slug="teacher-lesson")
    assert lesson.status == "review" and lesson.author == teacher
    assert client_for(student).get("/api/lessons/teacher-lesson/").status_code == 404

    queue = client_for(admin_user).get("/api/admin/review/").data
    assert any(item["slug"] == "teacher-lesson" for item in queue)
    client_for(admin_user).post("/api/admin/review/decide/", {"type": "lesson", "id": lesson.id, "approve": True}, format="json")
    assert client_for(student).get("/api/lessons/teacher-lesson/").status_code == 200


def test_teachers_cannot_edit_other_teachers_lessons(client_for, teacher, other_teacher, unit):
    lesson = Lesson.objects.create(unit=unit, slug="t1", title="T1", body="x", status="published", author=teacher)
    response = client_for(other_teacher).patch(f"/api/lessons/{lesson.slug}/", {"title": "Hacked"}, format="json")
    assert response.status_code == 403


def test_teacher_edit_sends_published_lesson_back_to_review(client_for, teacher, unit):
    lesson = Lesson.objects.create(unit=unit, slug="t2", title="T2", body="x", status="published", author=teacher)
    client_for(teacher).patch(f"/api/lessons/{lesson.slug}/", {"body": "changed"}, format="json")
    lesson.refresh_from_db()
    assert lesson.status == "review"


def test_completing_a_lesson_awards_xp_once(client_for, student, lesson):
    client = client_for(student)
    first = client.post(f"/api/lessons/{lesson.slug}/complete/").data
    second = client.post(f"/api/lessons/{lesson.slug}/complete/").data
    assert first["xp_gained"] == 10 and second["xp_gained"] == 0
    student.refresh_from_db()
    assert student.xp == 10
    assert student.badges.filter(badge__code="first-lesson").exists()


def test_lesson_detail_includes_prev_next_and_quizzes(client_for, student, unit, lesson, quiz_factory):
    Lesson.objects.create(unit=unit, slug="second", order=2, title="Second", body="x", status="published")
    quiz_factory()
    data = client_for(student).get(f"/api/lessons/{lesson.slug}/").data
    assert data["previous"] is None and data["next"]["slug"] == "second"
    assert len(data["quizzes"]) == 1


def test_resources_uploaded_by_teachers_need_review(client_for, teacher, student, subject):
    response = client_for(teacher).post(
        "/api/resources/",
        {"subject": subject.id, "kind": "notes", "title": "My notes", "url": "https://example.com/n.pdf"},
        format="json",
    )
    assert response.status_code == 201 and response.data["status"] == "review"
    assert client_for(student).get("/api/resources/").data["count"] == 0


def test_unauthenticated_requests_are_rejected(client_for):
    assert client_for().get("/api/subjects/").status_code == 401


def test_units_endpoint_filters(client_for, teacher, subject):
    Unit.objects.create(subject=subject, grade="S3", number=1, title="Quadratics")
    data = client_for(teacher).get("/api/units/?subject=mathematics&grade=S3").data
    assert [u["title"] for u in data] == ["Quadratics"]


def test_subject_opens_even_when_not_offered_in_my_grade(client_for, student, subject, lesson):
    subject.offered_o_level = False
    subject.offered_a_level = True
    subject.save()
    client = client_for(student)  # an S2 student
    assert [s["code"] for s in client.get("/api/subjects/").data] == []
    detail = client.get(f"/api/subjects/{subject.code}/", {"grade": "S2"}).data
    assert detail["lesson_count"] == 1 and detail["completed_count"] == 0


def test_subject_counts_per_grade(client_for, student, subject, unit, lesson):
    from apps.curriculum.models import Lesson, LessonProgress, Unit

    other = Unit.objects.create(subject=subject, grade="S2", number=2, title="Angles")
    for i in range(3):
        Lesson.objects.create(unit=other, slug=f"angles-{i}", title="Angles", body="x", status="published")
    LessonProgress.objects.create(user=student, lesson=lesson)
    row = client_for(student).get("/api/subjects/", {"grade": "S2"}).data[0]
    assert (row["unit_count"], row["lesson_count"], row["completed_count"]) == (2, 4, 1)
