from django.contrib.auth import authenticate
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User

from .serializers import (
    LoginResponseSerializer,
    LoginSerializer,
    TokenRefreshResponseSerializer,
    UserSerializer,
)


class UserViewSet(viewsets.ModelViewSet):

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        """
        Allow unauthenticated access to create.
        Require authentication for other actions.
        """
        if self.action in ["create"]:
            return [AllowAny()]
        return super().get_permissions()


class LoginViewSet(viewsets.ViewSet):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: OpenApiResponse(description="Unexpected field"),
            401: OpenApiResponse(description="Invalid credentials"),
        },
        tags=["Auth"],
        summary="User login",
        description="Authenticate user and return JWT tokens",
    )
    @action(detail=False, methods=["post"])
    def login(self, request):
        """
        User login endpoint.
        Expects username and password in request body.
        Returns access and refresh tokens.
        """

        for key in request.data.keys():
            if key not in ["username", "password"]:
                return Response({"detail": f"Unexpected field: {key}"}, status=400)

        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)

        if user is None:
            return Response({"detail": "Invalid credentials"}, status=401)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )

    @extend_schema(
        request=TokenRefreshSerializer,
        responses={
            200: TokenRefreshResponseSerializer,
            401: OpenApiResponse(description="Invalid refresh token"),
        },
        tags=["Auth"],
        summary="Refresh access token",
    )
    @action(detail=False, methods=["post"])
    def refresh(self, request):
        """
        Refresh token endpoint.
        Expects refresh token in request body.
        Returns new access token.
        """

        for key in request.data.keys():
            if key not in ["refresh"]:
                return Response({"detail": f"Unexpected field: {key}"}, status=400)

        refresh_token = request.data.get("refresh")

        try:
            refresh = RefreshToken(refresh_token)
            return Response({"access": str(refresh.access_token)})
        except Exception as e:
            return Response({"detail": str(e)}, status=401)
