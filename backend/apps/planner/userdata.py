"""Personal-data export and erase for the study planner (the shared account-data convention)."""

from .models import ExamDate, StudyPlan


def export_for(user):
    plan = StudyPlan.objects.filter(user=user).first()
    return {
        "study_plan": {"weekly_goal_lessons": plan.weekly_goal_lessons} if plan else None,
        "exam_dates": [{"title": exam.title, "date": exam.date.isoformat()} for exam in ExamDate.objects.filter(user=user)],
    }


def erase_for(user):
    ExamDate.objects.filter(user=user).delete()
    StudyPlan.objects.filter(user=user).delete()
