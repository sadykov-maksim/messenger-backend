from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model

from rest_framework import viewsets
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .serializers import (
    UserSerializer,
    CookieTokenRefreshSerializer,
    MyTokenObtainPairSerializer,
)
from telegram.models import TelegramUser


class UserViewSet(viewsets.ModelViewSet):
    queryset = TelegramUser.objects.all()
    serializer_class = UserSerializer


class CookieTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    def finalize_response(self, request, response, *args, **kwargs):
        if 'user' in response.data:
            user = response.data['user']
            if user:
                response.data['user'] = {
                    "id": user['id'],
                    "username": user['username'],
                    "image": user.get('image', None),
                    "email": user['email'],
                    "role": user['role'],
                }
        response = super().finalize_response(request, response, *args, **kwargs)

        if response.data.get('refresh'):
            cookie_max_age = 3600 * 24 * 14
            domain = Site.objects.get_current().domain
            response.set_cookie('refresh', response.data['refresh'], domain=f".{domain}",
                                max_age=cookie_max_age, httponly=True,
                                samesite='Lax', secure=True)
            del response.data['refresh']
        return response


class CookieTokenRefreshView(TokenRefreshView):
    def finalize_response(self, request, response, *args, **kwargs):
        if response.data.get('refresh'):
            cookie_max_age = 3600 * 24 * 14
            domain = Site.objects.get_current().domain
            response.set_cookie('refresh', response.data['refresh'], domain=f".{domain}",
                                max_age=cookie_max_age,  httponly=True,
                                samesite='Lax', secure=True)
            del response.data['refresh']
        return super().finalize_response(request, response, *args, **kwargs)
    serializer_class = CookieTokenRefreshSerializer
