from django.urls import include, path

from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenVerifyView,
)

from messenger.viewsets import upload_attachment, AttachmentUploadView
from .routers import router
from .services.phone_auth import SMSVerifyCodeView, SMSRequestCodeView
from .services.telegram_auth import TelegramAuthView
from .views import transport_key
from .viewsets import (
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
)


urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    path('auth/', include('djoser.urls')),
    path('auth/telegram/', TelegramAuthView.as_view(), name='telegram_auth'),
    path('auth/sms/request/', SMSRequestCodeView.as_view(), name='sms_request_code'),
    path('auth/sms/verify/', SMSVerifyCodeView.as_view(), name='sms_verify_code'),
    path('token/', CookieTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),

    # Messenger
    #path('attachments/upload/', upload_attachment, name='attachment-upload'),
    path("messenger/", include("messenger.urls")),
    path("transport-key/", transport_key, name='transport-key'),
    path("attachments/upload/", AttachmentUploadView.as_view(), name='attachment-upload'),
]
