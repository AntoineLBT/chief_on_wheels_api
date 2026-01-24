from django.contrib.auth import authenticate
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User

from .serializers import UserSerializer


class UserViewSet(viewsets.ModelViewSet):

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        """
        Allow unauthenticated access to signup and login.
        Require authentication for other actions.
        """
        if self.action in ["create", "login", "refresh"]:
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=["post"])
    def login(self, request):
        """
        User login endpoint.
        Expects username and password in request body.
        Returns access and refresh tokens.
        """

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
                "user": UserSerializer(user).data,
            }
        )

    @action(detail=False, methods=["post"])
    def refresh(self, request):
        """
        Refresh token endpoint.
        Expects refresh token in request body.
        Returns new access token.
        """

        refresh_token = request.data.get("refresh")

        try:
            refresh = RefreshToken(refresh_token)
            return Response({"access": str(refresh.access_token)})
        except Exception as e:
            return Response({"detail": str(e)}, status=401)
