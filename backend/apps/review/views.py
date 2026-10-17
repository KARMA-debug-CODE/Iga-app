from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.assessments.services import correct_choice_ids

from . import services
from .serializers import ReviewAnswerSerializer, ReviewItemSerializer


class ReviewViewSet(viewsets.GenericViewSet):
    """A student's spaced-repetition deck: the questions they got wrong, revised on a Leitner schedule.

    Every query is scoped to the signed-in user, so nobody reads or revises another student's deck."""

    permission_classes = [IsAuthenticated]
    serializer_class = ReviewItemSerializer

    def get_queryset(self):
        return services.visible_items(self.request.user)

    def list(self, request):
        """The review session: the items due today, newest boxes first, plus the deck's counts."""
        due = list(services.due_items(request.user).order_by("box", "id").prefetch_related("question__choices")[:50])
        return Response(
            {
                "due": ReviewItemSerializer(due, many=True, context={"request": request}).data,
                "due_count": services.due_count(request.user),
                "total": services.deck_count(request.user),
            }
        )

    @action(detail=True, methods=["post"])
    def answer(self, request, pk=None):
        """Grade one due item on the server, move it along the schedule, and reveal the solution."""
        item = get_object_or_404(services.due_items(request.user), pk=pk)
        data = ReviewAnswerSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        question = item.question
        is_correct, xp = services.grade_item(item, choice_ids=v["choice_ids"], text=v["text"], numeric=v["numeric"])
        item.refresh_from_db()
        return Response(
            {
                "is_correct": is_correct,
                "xp_gained": xp,
                "retired": item.retired_at is not None,
                "box": item.box + 1,
                "due_on": item.due_on,
                "due_count": services.due_count(request.user),
                "solution": {
                    "correct_choice_ids": correct_choice_ids(question),
                    "numeric_answer": question.numeric_answer,
                    "accepted_answers": question.accepted_answers,
                    "explanation": question.explanation,
                },
            }
        )

    @action(detail=False)
    def summary(self, request):
        """Just the counts, for the dashboard."""
        return Response({"due_count": services.due_count(request.user), "total": services.deck_count(request.user)})


# For the dashboard view, without going through the viewset.
def dashboard_summary(user):
    return {"due_count": services.due_count(user), "total": services.deck_count(user)}
