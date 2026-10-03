import pytest

from apps.assessments.models import Question
from apps.classroom.models import Classroom, Enrollment

from .conftest import add_mcq, make_quiz, make_user

pytestmark = pytest.mark.django_db


def take(client, quiz, picks):
    """Start the quiz and answer each question with the option text in `picks` (by question prompt)."""
    attempt = client.post(f"/api/quizzes/{quiz.id}/start/").data
    for q in attempt["questions"]:
        question = Question.objects.get(pk=q["id"])
        choice = question.choices.get(text=picks[question.prompt])
        client.post(f"/api/attempts/{attempt['id']}/answer/", {"question": q["id"], "choice_ids": [choice.id]}, format="json")
    return client.post(f"/api/attempts/{attempt['id']}/submit/").data


@pytest.fixture
def setup(teacher, subject, unit):
    easy = add_mcq(subject, unit, "easy", "4", ("3", "5"))
    hard = add_mcq(subject, unit, "hard", "right", ("wrong", "other"))
    quiz = make_quiz(subject, unit, [easy, hard], feedback_mode="after_submit")
    classroom = Classroom.objects.create(name="C", grade="S2", teacher=teacher)
    students = [make_user(f"s{i}") for i in range(5)]
    for s in students:
        Enrollment.objects.create(classroom=classroom, student=s)
    return quiz, classroom, students


def test_item_analysis(client_for, teacher, setup):
    quiz, classroom, students = setup
    # 2 strong students get both right; 3 get the hard one wrong (2 pick "wrong", 1 picks "other").
    for s in students[:2]:
        take(client_for(s), quiz, {"easy": "4", "hard": "right"})
    for s, pick in zip(students[2:], ["wrong", "wrong", "other"], strict=True):
        take(client_for(s), quiz, {"easy": "4", "hard": pick})
    # A retry after seeing the answers must not change the analysis.
    take(client_for(students[4]), quiz, {"easy": "4", "hard": "right"})

    data = client_for(teacher).get(f"/api/quizzes/{quiz.id}/analytics/?classroom={classroom.id}").data
    assert data["students_attempted"] == 5
    assert data["classroom"]["students"] == 5
    easy, hard = data["questions"]
    assert easy["average_pct"] == 100.0 and hard["average_pct"] == 40.0
    counts = {c["text"]: c["count"] for c in hard["choices"]}
    assert counts == {"right": 2, "wrong": 2, "other": 1}
    assert data["hardest"][0] == 2
    assert hard["discrimination"] == 1.0 and easy["discrimination"] == 0.0
    assert sum(b["count"] for b in data["histogram"]) == 5
    assert data["histogram"][5]["count"] == 3 and data["histogram"][9]["count"] == 2


def test_only_own_classes(client_for, other_teacher, student, setup):
    quiz, classroom, _ = setup
    assert client_for(other_teacher).get(f"/api/quizzes/{quiz.id}/analytics/?classroom={classroom.id}").status_code == 403
    assert client_for(student).get(f"/api/quizzes/{quiz.id}/analytics/").status_code == 403


def test_without_class_uses_all_my_students(client_for, teacher, setup):
    quiz, _, students = setup
    outsider = make_user("outsider")
    take(client_for(students[0]), quiz, {"easy": "4", "hard": "right"})
    take(client_for(outsider), quiz, {"easy": "3", "hard": "wrong"})
    data = client_for(teacher).get(f"/api/quizzes/{quiz.id}/analytics/").data
    assert data["students_attempted"] == 1
