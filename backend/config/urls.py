from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts import parents
from apps.assessments.views import AttemptViewSet, ExamPaperViewSet, MarkingViewSet, QuestionViewSet, QuizViewSet
from apps.classroom.views import AssignmentViewSet, ClassroomViewSet
from apps.community.views import MessageViewSet, ModerationViewSet, StudyGroupViewSet
from apps.core import admin_login
from apps.core import views as core_views
from apps.curriculum.views import LessonViewSet, ResourceViewSet, SubjectViewSet, UnitViewSet
from apps.gamification import views as gamification_views
from apps.schools.downloads import PaperDownloadView
from apps.simulations.views import SimulationViewSet

router = DefaultRouter()
# The browsable list of every endpoint at /api/ is for development only.
router.include_root_view = settings.DEBUG
router.register("subjects", SubjectViewSet, basename="subject")
router.register("units", UnitViewSet, basename="unit")
router.register("lessons", LessonViewSet, basename="lesson")
router.register("resources", ResourceViewSet, basename="resource")
router.register("simulations", SimulationViewSet, basename="simulation")
router.register("questions", QuestionViewSet, basename="question")
router.register("quizzes", QuizViewSet, basename="quiz")
router.register("exam-papers", ExamPaperViewSet, basename="exam-paper")
router.register("attempts", AttemptViewSet, basename="attempt")
router.register("marking", MarkingViewSet, basename="marking")
router.register("classes", ClassroomViewSet, basename="classroom")
router.register("assignments", AssignmentViewSet, basename="assignment")
router.register("groups", StudyGroupViewSet, basename="group")
router.register("messages", MessageViewSet, basename="message")
router.register("admin/users", core_views.AdminUserViewSet, basename="admin-user")
router.register("admin/review", core_views.ReviewViewSet, basename="admin-review")
router.register("admin/moderation", ModerationViewSet, basename="admin-moderation")

api = [
    path("auth/", include("apps.accounts.urls")),
    path("tutor/", include("apps.tutor.urls")),
    path("code/", include("apps.coderun.urls")),
    path("children/", parents.ChildrenView.as_view(), name="children"),
    path("children/<id:student_id>/", parents.ChildDetailView.as_view(), name="child-detail"),
    path("health/", core_views.health, name="health"),
    path("meta/", core_views.meta, name="meta"),
    path("dashboard/", core_views.dashboard, name="dashboard"),
    path("search/", core_views.search, name="search"),
    path("leaderboard/", gamification_views.leaderboard, name="leaderboard"),
    path("badges/", gamification_views.badges, name="badges"),
    path("admin/stats/", core_views.admin_stats, name="admin-stats"),
    path("admin/audit/", core_views.admin_audit, name="admin-audit"),
    path("files/papers/<str:token>/", PaperDownloadView.as_view(), name="paper-download"),
    path("", include("apps.schools.urls")),
    path("", include(router.urls)),
]

admin.site.site_header = f"{settings.APP_NAME} administration"
admin.site.site_title = settings.APP_NAME

urlpatterns = [path("api/", include(api))]

# Requests refused before a view runs (a body over the size limits, ...) get a JSON answer.
handler400 = "apps.core.errors.bad_request"

# Off unless enabled, and in production only at its secret path (see apps/core/admin_login.py).
ADMIN_URL_PREFIX = admin_login.admin_url_prefix()
if ADMIN_URL_PREFIX:
    admin_login.install()
    urlpatterns.append(path(ADMIN_URL_PREFIX, admin.site.urls))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
