from django.urls import path

from . import views

urlpatterns = [
    path("schools/", views.SchoolDirectoryView.as_view(), name="school-directory"),
    path("schools/districts/", views.DistrictsView.as_view(), name="districts"),
    path("my-school/", views.MySchoolView.as_view(), name="my-school"),
    path("school/", views.SchoolAdminView.as_view(), name="school-admin"),
    path("school/members/", views.SchoolMembersView.as_view(), name="school-members"),
    path("school/members/decide/", views.DecideMembersView.as_view(), name="school-members-decide"),
    path("school/members/<id:user_id>/remove/", views.RemoveMemberView.as_view(), name="school-member-remove"),
    path("school/new-code/", views.NewSchoolCodeView.as_view(), name="school-new-code"),
    path("school/payments/", views.SchoolPaymentsView.as_view(), name="school-payments"),
    path("billing/checkout/", views.CheckoutView.as_view(), name="billing-checkout"),
    path("billing/payments/<str:reference>/", views.PaymentDetailView.as_view(), name="billing-payment"),
    path("billing/payments/<str:reference>/confirm/", views.ConfirmPaymentView.as_view(), name="billing-confirm"),
    path("billing/dev/<str:reference>/complete/", views.DevCompleteView.as_view(), name="billing-dev-complete"),
    path("billing/webhooks/flutterwave/", views.FlutterwaveWebhookView.as_view(), name="billing-webhook-flutterwave"),
    path("admin/schools/", views.PlatformSchoolsView.as_view(), name="admin-schools"),
    path("admin/schools/<id:school_id>/", views.PlatformSchoolDetailView.as_view(), name="admin-school"),
    path("admin/schools/<id:school_id>/payments/", views.PlatformManualPaymentView.as_view(), name="admin-school-payment"),
    path("admin/schools/<id:school_id>/members/", views.PlatformMembersView.as_view(), name="admin-school-members"),
    path(
        "admin/schools/<id:school_id>/<str:action>/",
        views.PlatformSchoolActionView.as_view(),
        name="admin-school-action",
    ),
]
