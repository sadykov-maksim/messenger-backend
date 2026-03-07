"""
ASGI config for backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

django_asgi_app = get_asgi_application()

from messenger.middleware import QueryStringSimpleJWTAuthTokenMiddleware, SimpleJWTAuthTokenMiddleware
from messenger.routing import websocket_urlpatterns
from video_call.routing import call_urlpatterns

websocket_urlpatterns += call_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": SimpleJWTAuthTokenMiddleware(
            QueryStringSimpleJWTAuthTokenMiddleware(URLRouter(websocket_urlpatterns))),
    }
)