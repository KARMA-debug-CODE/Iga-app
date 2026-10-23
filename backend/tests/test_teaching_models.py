"""Teaching Packs: the stored pack, its assignments, settings and the owner's personal data."""

import pytest
from django.db import IntegrityError, transaction

from apps.classroom.models import Classroom
from apps.teaching import userdata
from apps.teaching.models import PackAssignment, TeachingPack

DOCUMENT = {"version": 1, "unit": {"label": "S2 Unit 1: Linear graphs"}, "lesson": {"title": "Linear graphs"}}


@pytest.fixture
def pack(teacher, subject, unit):
    classroom = Classroom.objects.create(name="S2 A", subject=subject, grade="S2", teacher=teacher)
    return TeachingPack.objects.create(
        classroom=classroom, unit=unit, created_by=teacher, language="en", document=DOCUMENT, plan_edits={"objective": "Mine"}
    )


def test_one_assignment_per_pack_part(pack):
    PackAssignment.objects.create(pack=pack, what=PackAssignment.What.QUIZ)
    with pytest.raises(IntegrityError), transaction.atomic():
        PackAssignment.objects.create(pack=pack, what=PackAssignment.What.QUIZ)
    PackAssignment.objects.create(pack=pack, what=PackAssignment.What.WORKSHEET_CORE)
    assert pack.assignments.count() == 2


def test_deleting_the_class_deletes_its_packs(pack):
    pack.classroom.delete()
    assert TeachingPack.objects.count() == 0


def test_export_lists_the_teachers_packs(teacher, pack):
    exported = userdata.export_for(teacher)["teaching_packs"]
    assert exported == [
        {
            "unit": "S2 Unit 1: Linear graphs",
            "lesson": "Linear graphs",
            "created_at": pack.created_at.isoformat(),
            "language": "en",
            "plan_edits": {"objective": "Mine"},
        }
    ]


def test_erasure_deletes_the_teachers_packs(teacher, other_teacher, pack):
    kept = TeachingPack.objects.create(
        classroom=pack.classroom, unit=pack.unit, created_by=other_teacher, language="en", document=DOCUMENT
    )
    userdata.erase_for(teacher)
    assert list(TeachingPack.objects.all()) == [kept]


def test_teaching_settings_have_their_defaults(settings):
    assert settings.TEACHING_MIN_STUDENTS == 5 and settings.TEACHING_MISCONCEPTION_SHARE == 0.3
    assert settings.TEACHING_MASTERED_SHARE == 0.85 and settings.TEACHING_QUIZ_SIZE == 10
    assert settings.TEACHING_WORKSHEET_PER_LEVEL == 5 and settings.TEACHING_LOOKBACK_DAYS == 365
    assert settings.TEACHING_PERIOD_MINUTES == 40 and settings.TEACHING_AI_SECONDS == 20
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["teaching_pack"] == "30/hour"
