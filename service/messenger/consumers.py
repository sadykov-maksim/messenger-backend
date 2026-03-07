import os
import json
import logging

import msgpack
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db import models
from django.http import JsonResponse
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.observer import model_observer
from djangochannelsrestframework.observer.generics import (
    ObserverModelInstanceMixin,
    action,
)

from .models import (
    Attachment,
    Message,
    MessageStatus,
    Reaction,
    Room,
    RoomMember,
)
from .serializers import (
    AccountSerializer,
    MessageSerializer,
    RoomSerializer,
)
import hmac, hashlib, time



logger = logging.getLogger(__name__)

WS_TRANSPORT_KEY = bytes.fromhex("6e0ba81549b4905a42126f634848a3b2d967e7039abdbf65e8853f7fb3c79f6a")

def _derive_session_key(user_id: int, window_offset: int = 0) -> bytes:
    window = int(time.time()) // 300 + window_offset
    payload = f"{user_id}:{window}".encode()
    return hmac.new(WS_TRANSPORT_KEY, payload, hashlib.sha256).digest()


def transport_key(request):
    master_key = WS_TRANSPORT_KEY
    window = int(time.time()) // 300

    def derive(w):
        payload = f"{request.user.id}:{w}".encode()
        return hmac.new(master_key, payload, hashlib.sha256).digest().hex()

    curr = derive(window)
    prev = derive(window - 1)

    # ОТЛАДКА
    logger.warning(f"[VIEW] user_id={request.user.id} window={window}")
    logger.warning(f"[VIEW] key_curr={curr}")
    logger.warning(f"[VIEW] key_prev={prev}")

    return JsonResponse({
        "key": curr,
        "key_prev": prev,
        "expires_in": 300 - (int(time.time()) % 300)
    })

def _make_msgpack_safe(obj):
    """Рекурсивно конвертирует объект в msgpack-совместимый формат."""
    if isinstance(obj, dict):
        return {k: _make_msgpack_safe(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_msgpack_safe(i) for i in obj]
    elif hasattr(obj, 'isoformat'):  # datetime, date
        return obj.isoformat()
    elif obj is None or isinstance(obj, (bool, int, float, str, bytes)):
        return obj
    else:
        return str(obj)


class RoomConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    lookup_field = "pk"

    async def connect(self):
        self.user = self.scope["user"]
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        window = int(time.time()) // 300
        self.transport_keys = [
            _derive_session_key(self.user.id, 0),
            _derive_session_key(self.user.id, -1),
        ]
        self.transport_key = self.transport_keys[0]

        # ОТЛАДКА
        logger.warning(f"[CONNECT] user_id={self.user.id} window={window}")
        logger.warning(f"[CONNECT] key_curr={self.transport_keys[0].hex()}")
        logger.warning(f"[CONNECT] key_prev={self.transport_keys[1].hex()}")

        await super().connect()

    async def send_json(self, content, close=False):
        """Переопределяем: отправляем msgpack-бинарный фрейм вместо JSON."""
        logger.warning(f"[SEND_JSON] to={self.user.username} type={content.get('type')} action={content.get('action')}")

        safe = _make_msgpack_safe(content)
        packed = msgpack.packb(safe, use_bin_type=True)

        # Refresh keys in case the time window rotated
        self.transport_keys = [
            _derive_session_key(self.user.id, 0),
            _derive_session_key(self.user.id, -1),
        ]
        self.transport_key = self.transport_keys[0]

        aesgcm = AESGCM(self.transport_key)
        iv = os.urandom(12)
        packed = iv + aesgcm.encrypt(iv, packed, None)

        await self.send(bytes_data=packed)

    async def receive(self, text_data=None, bytes_data=None):
        """Принимаем как бинарные (msgpack), так и текстовые (JSON) фреймы."""
        if bytes_data:
            decrypted = None
            for key in self.transport_keys:
                try:
                    iv = bytes_data[:12]
                    ciphertext = bytes_data[12:]
                    aesgcm = AESGCM(key)
                    decrypted = aesgcm.decrypt(iv, ciphertext, None)
                    break
                except Exception:
                    continue

            if decrypted is None:
                try:
                    data = msgpack.unpackb(bytes_data, raw=False)
                except Exception as e:
                    logger.error(f"msgpack/decrypt error: {e}")
                    await self.send_json({"type": "error", "message": "Decrypt failed"})
                    return
            else:
                try:
                    data = msgpack.unpackb(decrypted, raw=False)
                except Exception as e:
                    logger.error(f"msgpack decode error after decrypt: {e}")
                    await self.send_json({"type": "error", "message": "Bad binary format"})
                    return

            text_data = json.dumps(data)
        elif text_data:
            pass
        else:
            return

        await super().receive(text_data=text_data)



    async def disconnect(self, code):
        room_id = getattr(self, "room_subscribe", None)
        if room_id:
            await self.channel_layer.group_discard(f"room__{int(room_id)}", self.channel_name)

        if hasattr(self, "room_subscribe"):
            await self.remove_user_from_room(self.room_subscribe)
            await self.notify_users()
        await super().disconnect(code)

    @action()
    async def join_room(self, pk, **kwargs):
        self.room_subscribe = int(pk)
        group_name = f"room__{self.room_subscribe}"

        # ЯВНО добавляем сокет в группу комнаты (для typing, users, и т.п.)
        await self.channel_layer.group_add(group_name, self.channel_name)
        logger.warning(f"[GROUP_ADD] user={self.user.username} channel={self.channel_name} group={group_name}")

        await self.add_user_to_room(self.room_subscribe)
        await self.message_activity.subscribe(room=self.room_subscribe)

        await self.notify_users()

        messages = await self.get_last_messages(self.room_subscribe)
        encrypted_room_key = await self.get_encrypted_room_key(self.room_subscribe)

        await self.send_json({
            "type": "message_history",
            "data": messages,
            "encrypted_room_key": encrypted_room_key,
        })

    @action()
    async def get_my_rooms(self, **kwargs):
        """Получить все диалоги пользователя"""

        rooms = await self.fetch_user_rooms()
        await self.send_json({"type": "my_rooms", "data": rooms})

    @action()
    async def leave_room(self, pk, **kwargs):
        pk = int(pk)
        group_name = f"room__{pk}"

        await self.channel_layer.group_discard(group_name, self.channel_name)
        logger.warning(f"[GROUP_DISCARD] user={self.user.username} channel={self.channel_name} group={group_name}")

        await self.remove_user_from_room(pk)
        await self.notify_users()

    @action()
    async def create_message(self, message="", attachment_ids=None, iv=None, **kwargs):
        if not message and not attachment_ids:
            await self.send_json({"type": "error", "message": "Нет контента"})
            return

        room = await self.get_room(pk=self.room_subscribe)
        await self.save_message(room, message, attachment_ids or [], iv=iv)

    @action()
    async def edit_message(self, message_id, text, **kwargs):
        """Редактировать своё сообщение"""

        edited = await self.update_message(message_id, text)
        if not edited:
            await self.send_json({"type": "error", "message": "Сообщение не найдено или нет прав"})

    @action()
    async def delete_message(self, message_id=None, **kwargs):
        if message_id is None:
            await self.send_json({"type": "error", "message": "message_id is required"})
            return

        deleted = await self.destroy_message(int(message_id))
        if not deleted:
            await self.send_json({"type": "error", "message": "Сообщение не найдено или нет прав"})
            return

        await self.send_json({"type": "message_deleted_ack", "pk": int(message_id)})

    @action()
    async def reply_to_message(self, message_id, text, **kwargs):
        """Ответить на сообщение"""
        room = await self.get_room(pk=self.room_subscribe)
        parent = await self.get_message(message_id)
        if parent:
            await database_sync_to_async(Message.objects.create)(
                room=room,
                user=self.user,
                text=text,
                reply_to=parent
            )

    @action()
    async def mark_as_read(self, message_id, **kwargs):
        """Отметить сообщение как прочитанное"""

        await self.set_message_status(message_id, MessageStatus.Status.READ)
        await self.update_last_read(self.room_subscribe)

    @action()
    async def add_reaction(self, message_id, emoji, **kwargs):
        """Добавить реакцию на сообщение"""
        await self.create_reaction(message_id, emoji)

    @action()
    async def remove_reaction(self, message_id, emoji, **kwargs):
        """Убрать реакцию"""
        await self.destroy_reaction(message_id, emoji)

    @action()
    async def subscribe_to_messages_in_room(self, pk, **kwargs):
        await self.message_activity.subscribe(room=pk)

    @action()
    async def search_entities(self, query: str, **kwargs):
        """Поиск чатов по названию и пользователей по username"""
        if not query:
            return

        result = await self.fetch_entities_by_query(query)
        await self.send_json({
            "type": "search_result",
            "data": result,
            "query": query
        })

    @action()
    async def upload_room_keys(self, room_id: int, encrypted_keys: list, **kwargs):
        """
        Сохраняет зашифрованные копии AES-ключа комнаты для каждого участника.
        Сервер хранит непрозрачный base64-blob — содержимого не знает.
        """
        await self.save_encrypted_keys(room_id, encrypted_keys)
        await self.send_json({"type": "keys_uploaded", "room_id": room_id})

    @action()
    async def start_direct_dialog(self, user_id: int, **kwargs):
        """Создает или находит существующий диалог с пользователем"""
        room_id, is_new = await self.get_or_create_room_with_user(user_id)
        await self.join_room(pk=room_id)
        await self.send_json({
            "type": "direct_room_ready",
            "room_id": room_id,
            "needs_key_upload": is_new,  # ← client only generates+uploads keys when True
        })

    @action()
    async def typing(self, is_typing: bool = True, **kwargs):
        room_id = getattr(self, "room_subscribe", None)
        if not room_id:
            return

        group_name = f"room__{int(room_id)}"
        logger.warning(f"[TYPING] user={self.user.username} groups={self.groups} target={group_name}")
        if not room_id:
            return

        await self.channel_layer.group_send(
            group_name,
            {
                "type": "typing_status",
                "user_id": self.user.id,
                "username": self.user.username,
                "is_typing": is_typing,
            }
        )

    async def typing_status(self, event: dict):
        logger.warning(f"[TYPING_STATUS] to={self.user.username} from={event['username']}")
        if event["user_id"] == self.user.id:
            return

        await self.send_json({
            "type": "typing",
            "user_id": event["user_id"],
            "username": event["username"],
            "is_typing": event["is_typing"],
        })

    @model_observer(Message)
    async def message_activity(self, message, observer=None, **kwargs):
        await self.send_json(message)

    @message_activity.groups_for_signal
    def message_activity(self, instance: Message, **kwargs):
        yield f'room__{instance.room_id}'
        yield f'pk__{instance.pk}'

    @message_activity.groups_for_consumer
    def message_activity(self, room=None, **kwargs):
        if room is not None:
            yield f'room__{room}'

    @message_activity.serializer
    def message_activity(self, instance: Message, action, **kwargs):
        action_value = action.value if hasattr(action, "value") else str(action)

        if action_value == "delete":
            return _make_msgpack_safe({  # ← добавить
                "type": "message",
                "action": action_value,
                "pk": instance.pk,
                "data": {
                    "id": instance.pk,
                    "room": instance.room_id,
                    "deleted": True,
                },
            })

        instance = (
            Message.objects
            .select_related("user")
            .prefetch_related("attachments")
            .get(pk=instance.pk)
        )
        return _make_msgpack_safe({  # ← добавить
            "type": "message",
            "data": MessageSerializer(instance).data,
            "action": action_value,
            "pk": instance.pk,
        })

    async def notify_users(self):
        room = await self.get_room(self.room_subscribe)
        users = await self.current_users(room)

        safe_users = _make_msgpack_safe(users)  # <-- важно

        await self.channel_layer.group_send(
            f"room__{int(self.room_subscribe)}",
            {"type": "update_users", "users": safe_users}
        )

    async def update_users(self, event: dict):
        await self.send_json({"type": "online_users", "users": event["users"]})

    @database_sync_to_async
    def fetch_entities_by_query(self, query: str) -> dict:
        user = self.user

        rooms = Room.objects.filter(
            models.Q(host=user) | models.Q(members__user=user)
        ).filter(
            models.Q(name__icontains=query)
        ).distinct()

        User = get_user_model()
        users = User.objects.filter(
            username__icontains=query
        ).exclude(pk=user.pk)[:10]

        return {
            "rooms": RoomSerializer(rooms, many=True).data,
            "users": AccountSerializer(users, many=True).data
        }

    @database_sync_to_async
    def get_or_create_room_with_user(self, target_user_id: int):
        User = get_user_model()
        target_user = User.objects.get(pk=target_user_id)

        existing_room = (
            Room.objects
            .filter(members__user=self.user)
            .filter(members__user=target_user)
            .distinct()
            .first()
        )
        if existing_room:
            return existing_room.pk, False  # ← existing, no key upload needed

        new_room = Room.objects.create(
            name=f"{target_user.username}",
            host=self.user
        )
        RoomMember.objects.create(room=new_room, user=self.user)
        RoomMember.objects.create(room=new_room, user=target_user)
        return new_room.pk, True  # ← new, client must upload keys

    @database_sync_to_async
    def get_encrypted_room_key(self, room_id: int):
        member = RoomMember.objects.filter(
            room_id=room_id,
            user=self.user
        ).first()
        return member.encrypted_room_key if member else None

    @database_sync_to_async
    def save_encrypted_keys(self, room_id: int, encrypted_keys: list):
        for entry in encrypted_keys:
            RoomMember.objects.filter(
                room_id=room_id,
                user_id=entry["user_id"]
            ).update(encrypted_room_key=entry["encrypted_key"])

    @database_sync_to_async
    def save_message(self, room, text: str, attachment_ids: list, iv: str = None):
        if attachment_ids and not text:
            first = Attachment.objects.filter(pk__in=attachment_ids).first()

            # Автоопределение типа сообщения по вложению
            if first:
                if first.type == Attachment.AttachmentType.VOICE:
                    msg_type = Message.MessageType.VOICE
                elif first.type == Attachment.AttachmentType.IMAGE:
                    msg_type = Message.MessageType.IMAGE
                else:
                    msg_type = Message.MessageType.FILE
            else:
                msg_type = Message.MessageType.FILE
        else:
            msg_type = Message.MessageType.TEXT

        msg = Message.objects.create(
            room=room,
            user=self.user,
            text=text or None,
            type=msg_type,
            iv=iv,
        )

        if attachment_ids:
            Attachment.objects.filter(
                pk__in=attachment_ids,
                message=None
            ).update(message=msg)
            msg.save()

        return msg

    @database_sync_to_async
    def fetch_user_rooms(self) -> list:
        user = self.user
        rooms = Room.objects.filter(
            models.Q(host=user) | models.Q(members__user=user)
        ).distinct().prefetch_related("members", "current_users")
        return RoomSerializer(rooms, many=True).data

    @database_sync_to_async
    def fetch_rooms_by_query(self, query: str) -> list:
        user = self.user
        rooms = Room.objects.filter(
            models.Q(host=user) | models.Q(members__user=user)
        ).filter(
            models.Q(name__icontains=query)
        ).distinct().prefetch_related("members", "current_users")
        return RoomSerializer(rooms, many=True).data

    @database_sync_to_async
    def get_room(self, pk: int) -> Room:
        return Room.objects.get(pk=pk)

    @database_sync_to_async
    def get_message(self, message_id: int):
        try:
            return Message.objects.get(pk=message_id)
        except Message.DoesNotExist:
            return None

    @database_sync_to_async
    def get_last_messages(self, room_id: int, limit: int = 50) -> list:
        messages = (
            Message.objects
            .filter(room_id=room_id)
            .select_related("user")
            .prefetch_related("attachments")
            .order_by("-created_at")[:limit]
        )
        return MessageSerializer(reversed(list(messages)), many=True).data

    @database_sync_to_async
    def current_users(self, room: Room) -> list:
        return [AccountSerializer(user).data for user in room.current_users.all()]

    @database_sync_to_async
    def add_user_to_room(self, pk: int):
        user = self.user
        room = Room.objects.get(pk=pk)
        if not user.current_rooms.filter(pk=pk).exists():
            user.current_rooms.add(room)
        RoomMember.objects.get_or_create(room=room, user=user)

    @database_sync_to_async
    def remove_user_from_room(self, pk: int):
        self.user.current_rooms.remove(pk)

    @database_sync_to_async
    def update_message(self, message_id: int, text: str) -> bool:
        try:
            msg = Message.objects.get(pk=message_id, user=self.user)
            msg.text = text
            msg.is_edited = True
            msg.save()
            return True
        except Message.DoesNotExist:
            return False

    @database_sync_to_async
    def destroy_message(self, message_id: int) -> bool:
        room_id = getattr(self, "room_subscribe", None)
        if not room_id:
            return False

        deleted_count, _ = Message.objects.filter(
            pk=message_id,
            user_id=self.user.id,
            room_id=room_id,
        ).delete()

        return deleted_count > 0

    @database_sync_to_async
    def set_message_status(self, message_id: int, status: str):
        try:
            msg = Message.objects.get(pk=message_id)
            MessageStatus.objects.update_or_create(
                message=msg,
                user=self.user,
                defaults={"status": status}
            )
        except Message.DoesNotExist:
            pass

    @database_sync_to_async
    def update_last_read(self, room_id: int):
        from django.utils import timezone
        RoomMember.objects.filter(
            room_id=room_id,
            user=self.user
        ).update(last_read_at=timezone.now())

    @database_sync_to_async
    def create_reaction(self, message_id: int, emoji: str):
        try:
            msg = Message.objects.get(pk=message_id)
            Reaction.objects.get_or_create(
                message=msg,
                user=self.user,
                emoji=emoji
            )
        except Message.DoesNotExist:
            pass

    @database_sync_to_async
    def destroy_reaction(self, message_id: int, emoji: str):
        Reaction.objects.filter(
            message_id=message_id,
            user=self.user,
            emoji=emoji
        ).delete()