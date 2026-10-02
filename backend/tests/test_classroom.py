import pytest

from apps.classroom.models import Classroom, Enrollment
from apps.curriculum.models import LessonProgress

pytestmark = pytest.mark.django_db


@pytest.fixture
def classroom(teacher, subject):
    return Classroom.objects.create(name="S2 Maths", grade="S2", subject=subject, teacher=teacher)


def test_teacher_creates_class_with_readable_join_code(client_for, teacher):
    response = client_for(teacher).post("/api/classes/", {"name": "S3 Physics", "grade": "S3"}, format="json")
    assert response.status_code == 201
    code = response.data["join_code"]
    assert len(code) == 6 and not set(code) & set("0O1I")


def test_student_joins_with_code_and_cannot_see_code(client_for, student, classroom):
    client = client_for(student)
    response = client.post("/api/classes/join/", {"code": classroom.join_code.lower()}, format="json")
    assert response.status_code == 200
    assert response.data["join_code"] is None
    assert Enrollment.objects.filter(classroom=classroom, student=student).exists()
    detail = client.get(f"/api/classes/{classroom.id}/").data
    assert "students" not in detail  # roster is for the teacher only


def test_bad_join_code(client_for, student):
    assert client_for(student).post("/api/classes/join/", {"code": "ZZZZZZ"}, format="json").status_code == 400


def test_teachers_only_see_their_own_classes(client_for, other_teacher, classroom):
    client = client_for(other_teacher)
    assert client.get("/api/classes/").data["count"] == 0
    assert client.get(f"/api/classes/{classroom.id}/").status_code == 404
    assert client.get(f"/api/classes/{classroom.id}/report/").status_code == 404


def test_students_cannot_open_classes_they_are_not_in(client_for, student, classroom):
    assert client_for(student).get(f"/api/classes/{classroom.id}/").status_code == 404


def test_assignment_and_report(client_for, teacher, student, other_student, classroom, lesson, quiz_factory):
    Enrollment.objects.create(classroom=classroom, student=student)
    Enrollment.objects.create(classroom=classroom, student=other_student)
    quiz = quiz_factory()
    teacher_client = client_for(teacher)

    response = teacher_client.post(
        "/api/assignments/", {"classroom": classroom.id, "title": "Read", "lesson": lesson.id}, format="json"
    )
    assert response.status_code == 201
    response = teacher_client.post(
        "/api/assignments/", {"classroom": classroom.id, "title": "Quiz", "quiz": quiz.id}, format="json"
    )
    assert response.status_code == 201

    LessonProgress.objects.create(user=student, lesson=lesson)
    mine = client_for(student).get("/api/assignments/").data["results"]
    states = {a["title"]: a["my_status"]["state"] for a in mine}
    assert states == {"Read": "done", "Quiz": "todo"}

    report = teacher_client.get(f"/api/classes/{classroom.id}/report/").data
    assert len(report["rows"]) == 2
    row = next(r for r in report["rows"] if r["student"]["id"] == student.id)
    assert row["completed"] == 1


def test_assignment_needs_exactly_one_target(client_for, teacher, classroom, lesson, quiz_factory):
    response = client_for(teacher).post(
        "/api/assignments/",
        {"classroom": classroom.id, "title": "Both", "lesson": lesson.id, "quiz": quiz_factory().id},
        format="json",
    )
    assert response.status_code == 400


def test_cannot_assign_to_someone_elses_class(client_for, other_teacher, classroom, lesson):
    response = client_for(other_teacher).post(
        "/api/assignments/", {"classroom": classroom.id, "title": "Sneaky", "lesson": lesson.id}, format="json"
    )
    assert response.status_code == 400


def test_students_cannot_create_assignments(client_for, student, classroom, lesson):
    response = client_for(student).post(
        "/api/assignments/", {"classroom": classroom.id, "title": "x", "lesson": lesson.id}, format="json"
    )
    assert response.status_code == 403


def test_deleting_a_class_archives_it(client_for, teacher, student, classroom):
    Enrollment.objects.create(classroom=classroom, student=student)
    assert client_for(teacher).delete(f"/api/classes/{classroom.id}/").status_code == 204
    classroom.refresh_from_db()
    assert classroom.archived
    assert client_for(student).get("/api/classes/").data["count"] == 0
