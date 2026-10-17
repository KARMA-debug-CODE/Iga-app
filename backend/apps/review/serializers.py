import random

from rest_framework import serializers

from apps.assessments.models import Question
from apps.core.text import CleanCharField
from apps.core.utils import serializer_language

_rng = random.SystemRandom()


def question_payload(question):
    """A review question for the student: prompt, type and options, but never the answer key."""
    choices = []
    if question.type in Question.CHOICE_TYPES:
        choices = [{"id": c.id, "text": c.text} for c in question.choices.all()]
        if question.type != Question.Type.TRUE_FALSE:
            _rng.shuffle(choices)
    return {"id": question.id, "type": question.type, "prompt": question.prompt, "choices": choices}


class ReviewItemSerializer(serializers.Serializer):
    """A due item in a review session. `question` carries no solution."""

    id = serializers.IntegerField(read_only=True)
    box = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    question = serializers.SerializerMethodField()

    def get_box(self, item):
        return item.box + 1  # people count boxes from 1

    def get_subject(self, item):
        subject = item.question.subject
        return {"name": subject.localized_name(serializer_language(self)), "icon": subject.icon}

    def get_question(self, item):
        return question_payload(item.question)


class ReviewAnswerSerializer(serializers.Serializer):
    """What the student sends to answer one review item (no question id: it is in the URL)."""

    # A question has a handful of options; a longer list is a forged request.
    choice_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list, max_length=50)
    text = CleanCharField(multiline=True, required=False, allow_blank=True, default="", max_length=10000)
    numeric = serializers.FloatField(required=False, allow_null=True, default=None)
