# consumers_online.py — отдельный consumer только для онлайн-статуса

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
import json


class OnlineStatusConsumer(AsyncWebsocketConsumer):
    """
    Отдельный WS-consumer исключительно для онлайн-статуса.
    Не привязан к комнатам — работает глобально.

    Подключение: ws/online/?token=...
    """

    GLOBAL_GROUP = "online_status"

    async def connect(self):
        self.user = self.scope["user"]
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        # Вступаем в глобальную группу онлайн-статусов
        await self.channel_layer.group_add(self.GLOBAL_GROUP, self.channel_name)

        # Помечаем онлайн
        await self.set_online(True)

        # Рассылаем всем: этот пользователь онлайн
        await self.broadcast(True)

        await self.accept()

        # Отправляем новому клиенту список всех онлайн-пользователей
        online_list = await self.get_online_users()
        await self.send(text_data=json.dumps({
            "type": "online_list",
            "users": online_list,
        }))

    async def disconnect(self, code):
        await self.set_online(False)
        await self.broadcast(False)
        await self.channel_layer.group_discard(self.GLOBAL_GROUP, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass

    async def broadcast(self, is_online: bool):
        last_seen = await self.get_last_seen()
        await self.channel_layer.group_send(
            self.GLOBAL_GROUP,
            {
                "type": "status_event",
                "user_id": self.user.id,
                "username": self.user.username,
                "is_online": is_online,
                "last_seen": last_seen,
            }
        )

    async def status_event(self, event: dict):
        """Получаем групповое событие и пересылаем клиенту."""
        await self.send(text_data=json.dumps({
            "type": "online_status",
            "user_id": event["user_id"],
            "username": event["username"],
            "is_online": event["is_online"],
            "last_seen": event["last_seen"],
        }))

    @database_sync_to_async
    def set_online(self, is_online: bool):
        from account.models import Account
        fields = {"is_online": is_online}
        if not is_online:
            fields["last_seen"] = timezone.now()
        Account.objects.filter(pk=self.user.id).update(**fields)

    @database_sync_to_async
    def get_last_seen(self) -> str | None:
        from account.models import Account
        acc = Account.objects.filter(pk=self.user.id).values(
            "last_seen", "hide_last_seen"
        ).first()
        if not acc or acc["hide_last_seen"]:
            return None
        return acc["last_seen"].isoformat() if acc["last_seen"] else None

    @database_sync_to_async
    def get_online_users(self) -> list:
        from account.models import Account
        users = Account.objects.filter(is_online=True).values(
            "id", "username", "last_seen", "hide_last_seen"
        )
        return [
            {
                "user_id": u["id"],
                "username": u["username"],
                "is_online": True,
                "last_seen": None,
            }
            for u in users
        ]