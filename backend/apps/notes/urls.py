from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import BookmarkViewSet, LessonNotesStateView, NoteViewSet

router = SimpleRouter()
router.register("bookmarks", BookmarkViewSet, basename="bookmark")
router.register("notes", NoteViewSet, basename="note")

urlpatterns = [
    path("my-notes/<slug:slug>/", LessonNotesStateView.as_view(), name="lesson-notes-state"),
    *router.urls,
]
