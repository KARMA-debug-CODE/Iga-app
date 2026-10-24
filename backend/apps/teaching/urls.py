from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import ClassUnitsView, PackViewSet

router = SimpleRouter()
router.register("packs", PackViewSet, basename="teaching-pack")

urlpatterns = [path("classes/<int:pk>/units/", ClassUnitsView.as_view(), name="teaching-class-units"), *router.urls]
