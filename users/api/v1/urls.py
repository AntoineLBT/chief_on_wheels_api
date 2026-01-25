from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LoginViewSet, UserViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"auth", LoginViewSet, basename="auth")

urlpatterns = [
    path("", include(router.urls)),
]
