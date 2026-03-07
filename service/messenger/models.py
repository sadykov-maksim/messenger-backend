from django.db import models

from account.models import Account
from messenger.choices import RoomType
from telegram.models import TelegramUser
from django.utils import timezone
from encrypted_model_fields.fields import EncryptedTextField, EncryptedCharField


# Create your models here.
class Room(models.Model):
    """Диалог / Групповой чат"""

    name = models.CharField(max_length=255, null=True, blank=True)  # только для групп
    type = models.CharField(max_length=10, choices=RoomType.choices, default=RoomType.PRIVATE)
    host = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="hosted_rooms")
    current_users = models.ManyToManyField(Account, related_name="current_rooms", blank=True)
    avatar = models.ImageField(upload_to="room_avatars/", null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Room({self.name or self.type} | {self.host})"


class RoomMember(models.Model):
    """Участник чата"""

    class Role(models.TextChoices):
        MEMBER = 'member', 'Участник'
        ADMIN = 'admin', 'Администратор'

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)  # для счётчика непрочитанных
    encrypted_room_key = models.TextField(null=True, blank=True)


    class Meta:
        unique_together = ('room', 'user')

    def __str__(self):
        return f"RoomMember({self.user} in {self.room})"


class Message(models.Model):
    """Сообщение"""

    class MessageType(models.TextChoices):
        TEXT = 'text', 'Текст'
        IMAGE = 'image', 'Изображение'
        FILE = 'file', 'Файл'
        VOICE = 'voice', 'Голосовое'

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="messages")
    type = models.CharField(max_length=10, choices=MessageType.choices, default=MessageType.TEXT)
    text = EncryptedTextField(max_length=2000, null=True, blank=True)
    reply_to = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name="replies"
    )

    # для верификации целостности — вот где SHA-256 реально нужен
    content_hash = models.CharField(max_length=64, null=True, blank=True)
    # nonce/IV для AES-GCM — уникален для каждого сообщения
    iv = models.CharField(max_length=32, null=True, blank=True)

    is_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Message({self.user} -> {self.room} | {self.created_at:%Y-%m-%d %H:%M})"


class Attachment(models.Model):
    """Вложение к сообщению"""

    class AttachmentType(models.TextChoices):
        IMAGE = 'image', 'Изображение'
        FILE = 'file', 'Файл'
        VOICE = 'voice', 'Голосовое'

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE,
        related_name="attachments",
        null=True, blank=True
    )
    type = models.CharField(max_length=10, choices=AttachmentType.choices)
    file = models.FileField(upload_to="attachments/")
    name = EncryptedCharField(max_length=255)  # было CharField
    size = models.PositiveIntegerField()  # в байтах

    def __str__(self):
        return f"Attachment({self.name} | {self.message})"


class MessageStatus(models.Model):
    """Статус доставки / прочтения сообщения"""

    class Status(models.TextChoices):
        SENT = 'sent', 'Отправлено'
        DELIVERED = 'delivered', 'Доставлено'
        READ = 'read', 'Прочитано'

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="statuses")
    user = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="message_statuses")
    status = EncryptedCharField(max_length=10, choices=Status.choices, default=Status.SENT)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('message', 'user')

    def __str__(self):
        return f"MessageStatus({self.user} | {self.status})"


class Reaction(models.Model):
    """Реакция на сообщение"""

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="reactions")
    emoji = models.CharField(max_length=10)

    class Meta:
        unique_together = ('message', 'user', 'emoji')

    def __str__(self):
        return f"Reaction({self.emoji} by {self.user})"


class Draft(models.Model):
    """Черновик сообщения"""

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="drafts")
    user = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="drafts")
    text = EncryptedTextField(max_length=5000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('room', 'user')

    def __str__(self):
        return f"Draft({self.user} in {self.room})"