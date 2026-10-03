from django.urls import path

from . import parents, views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("refresh/", views.RefreshView.as_view(), name="refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("me/", views.MeView.as_view(), name="me"),
    path("password/", views.ChangePasswordView.as_view(), name="change-password"),
    path("2fa/setup/", views.TwoFactorSetupView.as_view(), name="2fa-setup"),
    path("2fa/enable/", views.TwoFactorEnableView.as_view(), name="2fa-enable"),
    path("2fa/disable/", views.TwoFactorDisableView.as_view(), name="2fa-disable"),
    path("parent-code/", parents.ParentCodeView.as_view(), name="parent-code"),
    path("parents/", parents.MyParentsView.as_view(), name="my-parents"),
    path("parents/<int:parent_id>/", parents.MyParentsView.as_view(), name="my-parent"),
]
