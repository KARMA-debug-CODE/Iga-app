"""The spaced-repetition review deck: wrong answers go in, the Leitner schedule moves them along."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.assessments.models import Attempt, Question
from apps.gamification.models import XPEvent
from apps.review import services, userdata
from apps.review.models import ReviewItem

from .conftest import add_mcq, make_quiz, make_user

pytestmark = pytest.mark.django_db


def _correct_choice(question):
    return question.choices.get(is_correct=True)


def _wrong_choice(question):
    return question.choices.filter(is_correct=False).first()


def start_and_answer(client, quiz, question, choice, check=True):
    attempt = client.post(f"/api/quizzes/{quiz.id}/start/", {}, format="json").data
    client.post(f"/api/attempts/{attempt['id']}/answer/", {"question": question.id, "choice_ids": [choice.id]}, format="json")
    if check:
        client.post(f"/api/attempts/{attempt['id']}/check/", {"question": question.id}, format="json")
    return attempt


def test_a_wrong_practice_answer_joins_the_deck_a_right_one_does_not(client_for, subject, unit):
    student = make_user("deck-student")
    q_wrong = add_mcq(subject, unit, prompt="2+2?")
    q_right = add_mcq(subject, unit, prompt="3+3?", correct="6", wrong=("5", "7"))
    quiz = make_quiz(subject, unit, [q_wrong, q_right], is_free=True)
    client = client_for(student)
    start_and_answer(client, quiz, q_wrong, _wrong_choice(q_wrong))
    start_and_answer(client, quiz, q_right, _correct_choice(q_right))

    deck = list(ReviewItem.objects.filter(user=student))
    assert [i.question_id for i in deck] == [q_wrong.id]
    assert deck[0].box == 0 and deck[0].due_on == timezone.localdate()


def test_submitting_adds_every_wrong_auto_marked_question(client_for, subject, unit):
    student = make_user("submit-student")
    q1 = add_mcq(subject, unit, prompt="Q1")
    q2 = add_mcq(subject, unit, prompt="Q2")
    quiz = make_quiz(subject, unit, [q1, q2], is_free=True, feedback_mode="after_submit")
    client = client_for(student)
    attempt = client.post(f"/api/quizzes/{quiz.id}/start/", {}, format="json").data
    client.post(
        f"/api/attempts/{attempt['id']}/answer/", {"question": q1.id, "choice_ids": [_wrong_choice(q1).id]}, format="json"
    )
    client.post(
        f"/api/attempts/{attempt['id']}/answer/", {"question": q2.id, "choice_ids": [_correct_choice(q2).id]}, format="json"
    )
    client.post(f"/api/attempts/{attempt['id']}/submit/", {}, format="json")

    assert set(ReviewItem.objects.filter(user=student).values_list("question_id", flat=True)) == {q1.id}


def test_essays_never_enter_the_deck(client_for, subject, unit):
    student = make_user("essay-student")
    essay = Question.objects.create(subject=subject, grade=unit.grade, unit=unit, type=Question.Type.ESSAY, prompt="Why?")
    quiz = make_quiz(subject, unit, [essay], is_free=True, feedback_mode="after_submit")
    client = client_for(student)
    attempt = client.post(f"/api/quizzes/{quiz.id}/start/", {}, format="json").data
    client.post(f"/api/attempts/{attempt['id']}/answer/", {"question": essay.id, "text": "Short"}, format="json")
    client.post(f"/api/attempts/{attempt['id']}/submit/", {}, format="json")
    assert ReviewItem.objects.filter(user=student).count() == 0


def test_scheduling_moves_items_up_and_retires_them():
    # Box 0..4 with intervals 1, 3, 7, 14, 30; a correct answer past the last box graduates.
    assert services.next_schedule(0, True) == (1, 3)
    assert services.next_schedule(3, True) == (4, 30)
    assert services.next_schedule(4, True) == (None, None)
    assert services.next_schedule(2, False) == (0, 1)


def test_a_correct_review_advances_the_box_and_pushes_the_due_date(client_for, subject, unit):
    student = make_user("reviewer")
    question = add_mcq(subject, unit)
    item = ReviewItem.objects.create(user=student, question=question, due_on=timezone.localdate())
    client = client_for(student)

    res = client.post(f"/api/review/{item.id}/answer/", {"choice_ids": [_correct_choice(question).id]}, format="json")
    assert res.status_code == 200 and res.data["is_correct"] is True
    item.refresh_from_db()
    assert item.box == 1 and item.due_on == timezone.localdate() + timedelta(days=3)
    assert res.data["solution"]["explanation"] == "Because."
    # Already answered today, so it is no longer due.
    assert services.due_count(student) == 0


def test_a_wrong_review_sends_the_item_back_to_box_one(client_for, subject, unit):
    student = make_user("reviewer2")
    question = add_mcq(subject, unit)
    item = ReviewItem.objects.create(user=student, question=question, box=3, due_on=timezone.localdate())
    client = client_for(student)
    res = client.post(f"/api/review/{item.id}/answer/", {"choice_ids": [_wrong_choice(question).id]}, format="json")
    assert res.data["is_correct"] is False
    item.refresh_from_db()
    assert item.box == 0 and item.due_on == timezone.localdate() + timedelta(days=1)


def test_a_correct_answer_in_the_last_box_retires_the_item(client_for, subject, unit):
    student = make_user("graduate")
    question = add_mcq(subject, unit)
    item = ReviewItem.objects.create(user=student, question=question, box=services.LAST_BOX, due_on=timezone.localdate())
    client = client_for(student)
    res = client.post(f"/api/review/{item.id}/answer/", {"choice_ids": [_correct_choice(question).id]}, format="json")
    assert res.data["retired"] is True
    item.refresh_from_db()
    assert item.retired_at is not None
    assert services.deck_count(student) == 0 and services.due_count(student) == 0


def test_a_future_item_is_not_due_and_cannot_be_graded(client_for, subject, unit):
    student = make_user("future")
    question = add_mcq(subject, unit)
    item = ReviewItem.objects.create(user=student, question=question, due_on=timezone.localdate() + timedelta(days=5))
    client = client_for(student)
    assert services.due_count(student) == 0
    assert (
        client.post(f"/api/review/{item.id}/answer/", {"choice_ids": [_correct_choice(question).id]}, format="json").status_code
        == 404
    )


def test_review_xp_is_small_and_capped_per_day(client_for, subject, unit):
    student = make_user("xp-review")
    client = client_for(student)
    for i in range(8):
        q = add_mcq(subject, unit, prompt=f"Q{i}")
        item = ReviewItem.objects.create(user=student, question=q, due_on=timezone.localdate())
        client.post(f"/api/review/{item.id}/answer/", {"choice_ids": [_correct_choice(q).id]}, format="json")
    total = sum(XPEvent.objects.filter(user=student, reason="review").values_list("amount", flat=True))
    assert total == services.REVIEW_XP_DAILY_CAP


def test_wrong_review_earns_no_xp(client_for, subject, unit):
    student = make_user("noxp")
    q = add_mcq(subject, unit)
    item = ReviewItem.objects.create(user=student, question=q, due_on=timezone.localdate())
    res = client_for(student).post(f"/api/review/{item.id}/answer/", {"choice_ids": [_wrong_choice(q).id]}, format="json")
    assert res.data["xp_gained"] == 0
    assert not XPEvent.objects.filter(user=student, reason="review").exists()


def test_the_deck_hides_library_questions_without_a_subscription(client_for, subject, unit):
    from .conftest import make_school

    unpaid = make_school("Unpaid", "Huye", paid_until=None, status="verified")
    student = make_user("no-sub", school=unpaid)
    library_q = add_mcq(subject, unit, prompt="Library")  # no author: premium library question
    ReviewItem.objects.create(user=student, question=library_q, due_on=timezone.localdate())
    assert services.due_count(student) == 0  # locked away until the subscription is active


def test_the_review_session_endpoint_returns_due_counts(client_for, subject, unit):
    student = make_user("session")
    q1, q2 = add_mcq(subject, unit, prompt="A"), add_mcq(subject, unit, prompt="B")
    ReviewItem.objects.create(user=student, question=q1, due_on=timezone.localdate())
    ReviewItem.objects.create(user=student, question=q2, due_on=timezone.localdate() + timedelta(days=2))
    data = client_for(student).get("/api/review/").data
    assert data["due_count"] == 1 and data["total"] == 2 and len(data["due"]) == 1
    # The served question never carries the answer key.
    assert "is_correct" not in str(data["due"][0]["question"]["choices"])


def test_export_and_erase_cover_the_deck(subject, unit):
    student = make_user("export-review")
    q = add_mcq(subject, unit)
    ReviewItem.objects.create(user=student, question=q, due_on=timezone.localdate())
    exported = userdata.export_for(student)
    assert len(exported["review_items"]) == 1 and exported["review_items"][0]["question_id"] == q.id
    userdata.erase_for(student)
    assert ReviewItem.objects.filter(user=student).count() == 0


def test_a_retired_item_is_revived_if_the_question_is_wrong_again(subject, unit):
    student = make_user("revive")
    q = add_mcq(subject, unit)
    item = ReviewItem.objects.create(user=student, question=q, box=4, due_on=timezone.localdate(), retired_at=timezone.now())
    # Simulate getting it wrong again in a quiz.
    quiz = make_quiz(subject, unit, [q], is_free=True)
    attempt = Attempt.objects.create(user=student, quiz=quiz, question_order=[q.id], max_score=1)
    from apps.assessments.models import Answer

    answer = Answer.objects.create(attempt=attempt, question=q, is_correct=False)
    answer.selected_choices.set([_wrong_choice(q).id])
    services.add_wrong_answers(attempt)
    item.refresh_from_db()
    assert item.retired_at is None and item.box == 0
