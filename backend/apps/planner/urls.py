from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import ExamDateViewSet, StudyPlanView

router = SimpleRouter()
router.register("planner/exams", ExamDateViewSet, basename="exam-date")

urlpatterns = [path("planner/", StudyPlanView.as_view(), name="study-plan"), *router.urls]
