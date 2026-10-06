from django.urls import path

from . import views

urlpatterns = [
    path("status/", views.CodeStatusView.as_view(), name="code-status"),
    path("run/", views.CodeRunView.as_view(), name="code-run"),
]
