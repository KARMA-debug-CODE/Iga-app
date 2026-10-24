from django.urls import path

from . import parents, stepup, views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("refresh/", views.RefreshView.as_view(), name="refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("logout-all/", views.LogoutEverywhereView.as_view(), name="logout-all"),
    path("me/", views.MeView.as_view(), name="me"),
    path("password/", views.ChangePasswordView.as_view(), name="change-password"),
    path("password-reset/", views.PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset/confirm/", views.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("2fa/setup/", views.TwoFactorSetupView.as_view(), name="2fa-setup"),
    path("2fa/enable/", views.TwoFactorEnableView.as_view(), name="2fa-enable"),
    path("2fa/disable/", views.TwoFactorDisableView.as_view(), name="2fa-disable"),
    path("step-up/", stepup.StepUpView.as_view(), name="step-up"),
    path("accept-terms/", views.AcceptTermsView.as_view(), name="accept-terms"),
    path("my-data/", views.MyDataView.as_view(), name="my-data"),
    path("delete-account/", views.DeleteAccountView.as_view(), name="delete-account"),
    path("parent-code/", parents.ParentCodeView.as_view(), name="parent-code"),
    path("parents/", parents.MyParentsView.as_view(), name="my-parents"),
    path("parents/<id:parent_id>/", parents.MyParentsView.as_view(), name="my-parent"),
]
