from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .serializers import CustomTokenObtainPairSerializer


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RefreshView(TokenRefreshView):
    serializer_class = TokenRefreshSerializer


@extend_schema(
    request=inline_serializer(
        "RegisterRequest",
        {
            "username": drf_serializers.CharField(),
            "password": drf_serializers.CharField(write_only=True),
            "email": drf_serializers.EmailField(required=False),
        },
    ),
    responses=inline_serializer(
        "RegisterResponse",
        {
            "id": drf_serializers.IntegerField(),
            "username": drf_serializers.CharField(),
            "email": drf_serializers.CharField(),
        },
    ),
)
class RegisterView(APIView):
    """Crea el admin. Solo disponible en el primer arranque (sin usuarios)."""

    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        if User.objects.exists():
            return Response(
                {
                    "detail": (
                        "El registro está deshabilitado: ya existe un "
                        "administrador en el sistema."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email", "")

        if not username or not password:
            return Response(
                {"detail": "username y password son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {"detail": "Ya existe un usuario con ese username."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_superuser(
            username=username, email=email, password=password
        )
        return Response(
            {"id": user.id, "username": user.username, "email": user.email},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    responses=inline_serializer(
        "MeResponse",
        {
            "id": drf_serializers.IntegerField(),
            "username": drf_serializers.CharField(),
            "email": drf_serializers.CharField(),
            "first_name": drf_serializers.CharField(),
            "last_name": drf_serializers.CharField(),
            "is_staff": drf_serializers.BooleanField(),
        },
    ),
)
class MeView(APIView):
    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,
            }
        )
