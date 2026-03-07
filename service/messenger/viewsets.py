from rest_framework.decorators import api_view, permission_classes
from .models import Attachment
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import RoomMember
from .serializers import AttachmentSerializer


def detect_type(file) -> str:
    mime = file.content_type or ""
    if mime.startswith("image/"):
        return Attachment.AttachmentType.IMAGE
    if mime.startswith("audio/"):
        return Attachment.AttachmentType.VOICE
    return Attachment.AttachmentType.FILE


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_attachment(request):
    file = request.FILES.get('file')
    if not file:
        return Response({'error': 'No file'}, status=400)

    attachment = Attachment.objects.create(
        message=None,
        type=detect_type(file),
        file=file,
        name=file.name,
        size=file.size,
    )
    return Response({
        'id': attachment.id,
        'url': request.build_absolute_uri(attachment.file.url),
        'name': attachment.name,
        'size': attachment.size,
        'type': attachment.type,
    })

class UploadPublicKeyView(APIView):
    """
    POST /api/account/public-key/
    Сохраняет публичный RSA ключ пользователя.
    Вызывается один раз после регистрации/логина с нового устройства.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        public_key = request.data.get("public_key")
        if not public_key:
            return Response(
                {"detail": "public_key is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.public_key = public_key
        request.user.save(update_fields=["public_key"])

        return Response({"detail": "Публичный ключ сохранён"}, status=status.HTTP_200_OK)


class DistributeRoomKeysView(APIView):
    """
    POST /api/rooms/distribute-keys/
    Клиент-создатель комнаты отправляет зашифрованные копии AES ключа
    для каждого участника. Сервер просто сохраняет — не знает содержимого.

    Body:
    {
        "room_id": 3,
        "encrypted_keys": [
            {"user_id": 1, "encrypted_key": "base64..."},
            {"user_id": 2, "encrypted_key": "base64..."}
        ]
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        room_id = request.data.get("room_id")
        encrypted_keys = request.data.get("encrypted_keys", [])

        if not room_id or not encrypted_keys:
            return Response(
                {"detail": "room_id и encrypted_keys обязательны"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем что текущий пользователь — участник этой комнаты
        is_member = RoomMember.objects.filter(
            room_id=room_id,
            user=request.user
        ).exists()

        if not is_member:
            return Response(
                {"detail": "Нет доступа к этой комнате"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Сохраняем зашифрованный ключ для каждого участника
        updated = 0
        for entry in encrypted_keys:
            user_id = entry.get("user_id")
            encrypted_key = entry.get("encrypted_key")
            if user_id and encrypted_key:
                count = RoomMember.objects.filter(
                    room_id=room_id,
                    user_id=user_id
                ).update(encrypted_room_key=encrypted_key)
                updated += count

        return Response(
            {"detail": f"Ключи сохранены для {updated} участников"},
            status=status.HTTP_200_OK
        )


class GetMembersPublicKeysView(APIView):
    """
    GET /api/rooms/<room_id>/public-keys/
    Возвращает публичные ключи всех участников комнаты.
    Нужен клиенту чтобы зашифровать AES ключ комнаты для каждого участника.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id):
        # Проверяем что текущий пользователь — участник
        is_member = RoomMember.objects.filter(
            room_id=room_id,
            user=request.user
        ).exists()

        if not is_member:
            return Response(
                {"detail": "Нет доступа к этой комнате"},
                status=status.HTTP_403_FORBIDDEN
            )

        members = RoomMember.objects.filter(
            room_id=room_id
        ).select_related("user").values(
            "user_id",
            "user__username",
            "user__public_key",
        )

        return Response([
            {
                "user_id": m["user_id"],
                "username": m["user__username"],
                "public_key": m["user__public_key"],
            }
            for m in members
        ])

class AttachmentUploadView(APIView):
    permission_classes = [IsAuthenticated]  # ← вот это

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file"}, status=400)

        mime = file.content_type or ""
        name = file.name or ""

        if mime.startswith("image/"):
            attach_type = Attachment.AttachmentType.IMAGE
        elif mime in ("audio/webm", "audio/ogg", "audio/mpeg", "audio/wav") or name.startswith("voice_"):
            attach_type = Attachment.AttachmentType.VOICE
        else:
            attach_type = Attachment.AttachmentType.FILE

        attachment = Attachment.objects.create(
            file=file,
            type=attach_type,
            name=file.name,
            size=file.size,
        )

        return Response(AttachmentSerializer(attachment).data, status=201)