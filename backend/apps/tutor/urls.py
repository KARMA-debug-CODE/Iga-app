from django.urls import path

from . import views

urlpatterns = [
    path("status/", views.TutorStatusView.as_view(), name="tutor-status"),
    path("ask/", views.TutorAskView.as_view(), name="tutor-ask"),
]
