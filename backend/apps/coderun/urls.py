from django.urls import path

from . import views

urlpatterns = [
    path("status/", views.CodeStatusView.as_view(), name="code-status"),
    path("run/", views.CodeRunView.as_view(), name="code-run"),
    path("input/", views.CodeInputView.as_view(), name="code-input"),
    path("stop/", views.CodeStopView.as_view(), name="code-stop"),
]
