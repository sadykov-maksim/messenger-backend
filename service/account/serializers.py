import re
from djoser.serializers import UserCreateSerializer
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from rest_framework.fields import BooleanField

User = get_user_model()

class CustomUserCreateSerializer(UserCreateSerializer):
    consent_accepted = BooleanField(required=True)

    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = (
            'id', 'email', 'password',
            'first_name', 'last_name',
            'username', 'phone_number',
            'consent_accepted',
            'region', 'language', 'timezone',  # 👈
        )

    @staticmethod
    def validate_first_name(value):
        if not value:
            raise ValidationError("Необходимо указать имя.")
        return value

    @staticmethod
    def validate_last_name(value):
        if not value:
            raise ValidationError("Необходимо указать фамилию.")
        return value

    @staticmethod
    def validate_consent_accepted(value):
        if not value:
            raise ValidationError(
                "Пользователь должен дать согласие на обработку персональных данных."
            )
        return value

    @staticmethod
    def validate_phone_number(value):
        if value and not re.match(r'^\+?\d{9,15}$', value):
            raise ValidationError("Некорректный формат номера телефона.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if not attrs.get("region") and not attrs.get("region_id"):
            raise ValidationError({"region": "Необходимо указать регион."})

        if not attrs.get("language") and not attrs.get("language_id"):
            raise ValidationError({"language": "Необходимо указать язык."})

        if not attrs.get("timezone") and not attrs.get("timezone_id"):
            raise ValidationError({"timezone": "Необходимо указать часовой пояс."})

        return attrs