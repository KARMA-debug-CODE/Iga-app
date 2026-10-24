from django.urls import path

from . import views

urlpatterns = [
    path("site/", views.SiteInfoView.as_view(), name="site-info"),
    path("contact/", views.ContactView.as_view(), name="contact"),
]
