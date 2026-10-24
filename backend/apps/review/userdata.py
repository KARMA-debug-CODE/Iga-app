"""Personal-data export and erase for the review deck (the shared account-data convention).

export_for(user) returns only this user's own rows; erase_for(user) deletes them. No money is involved
here, so erase simply removes the rows."""

from .models import ReviewItem


def export_for(user):
    items = ReviewItem.objects.filter(user=user).select_related("question")
    return {
        "review_items": [
            {
                "question_id": item.question_id,
                "question": item.question.prompt,
                "box": item.box + 1,
                "due_on": item.due_on.isoformat(),
                "times_seen": item.times_seen,
                "times_correct": item.times_correct,
                "added_at": item.added_at.isoformat(),
                "last_reviewed_at": item.last_reviewed_at.isoformat() if item.last_reviewed_at else None,
                "retired": item.retired_at is not None,
            }
            for item in items
        ]
    }


def erase_for(user):
    ReviewItem.objects.filter(user=user).delete()
