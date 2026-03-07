from django.urls import re_path

from account.consumers import OnlineStatusConsumer
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/room/$', consumers.RoomConsumer.as_asgi()),
    re_path(r"ws/chat/(?P<pk>\d+)/$", consumers.RoomConsumer.as_asgi()),
    re_path(r"ws/online/$", OnlineStatusConsumer.as_asgi()),  # ← новый
]

