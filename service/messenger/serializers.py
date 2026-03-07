from account.models import Account
from api.serializers import UserSerializer
from telegram.models import TelegramUser
from .models import Room, Message, Attachment
from rest_framework import serializers


class AccountSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(use_url=True, required=False, allow_null=True)
    last_seen = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = ['id', 'username', 'avatar', 'first_name', 'last_name', 'role',  "is_online", "last_seen", "hide_last_seen"]  # Adjust based on your TelegramUser model fields
    def get_is_online(self, obj):
        # Если скрыл — не показываем онлайн
        if obj.hide_last_seen:
            return None
        return obj.is_online

    def get_last_seen(self, obj):
        if obj.hide_last_seen:
            return None
        return obj.last_seen

class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ['id', 'type', 'url', 'name', 'size']

    def get_url(self, obj) -> str:
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class MessageSerializer(serializers.ModelSerializer):
    user = AccountSerializer(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'room', 'user', 'type', 'text',
            'attachments', 'iv',
            'reply_to', 'is_edited', 'created_at', 'updated_at'
        ]

class RoomSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    messages = MessageSerializer(many=True, read_only=True)
    current_users = AccountSerializer(many=True, read_only=True)
    members = serializers.SerializerMethodField()  # ← добавить

    class Meta:
        model = Room
        fields = ["pk", "name", "messages", "current_users", "last_message", "members"]  # ← добавить
        read_only_fields = ["messages", "last_message"]
        depth = 0

    def get_last_message(self, obj: Room):
        last = obj.messages.order_by("-created_at").first()
        if not last:
            return None
        return MessageSerializer(last, context=self.context).data

    def get_members(self, obj: Room):
        users = [m.user for m in obj.members.select_related("user").all()]
        return AccountSerializer(users, many=True).data