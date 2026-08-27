from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import SessionViewSet, TreatmentViewSet

router = DefaultRouter()
router.register("treatments", TreatmentViewSet, basename="treatment")
router.register("sessions", SessionViewSet, basename="session")

urlpatterns = [
    path("", include(router.urls)),
]
