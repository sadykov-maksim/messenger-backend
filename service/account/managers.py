from django.contrib.auth.models import BaseUserManager
import re

class AccountManager(BaseUserManager):

    def _create_user(self, password=None, skip_validation=False, **extra_fields):
        Model = self.model

        if not skip_validation:
            if not extra_fields.get("email"):
                raise ValueError("Необходимо указать email.")

            if not extra_fields.get("first_name"):
                raise ValueError("Необходимо указать имя.")

            if not extra_fields.get("last_name"):
                raise ValueError("Необходимо указать фамилию.")

            if not extra_fields.get("consent_accepted") is True:
                raise ValueError("Пользователь должен дать согласие на обработку персональных данных.")

            if not extra_fields.get("region") and not extra_fields.get("region_id"):
                raise ValueError("Необходимо указать регион.")

            if not extra_fields.get("language") and not extra_fields.get("language_id"):
                raise ValueError("Необходимо указать язык.")

            if not extra_fields.get("timezone") and not extra_fields.get("timezone_id"):
                raise ValueError("Необходимо указать часовой пояс.")

            role = extra_fields.get("role", Model.Role.USER)
            if role not in Model.Role.values:
                raise ValueError(f"Недопустимая роль: {role}")

            phone = extra_fields.get("phone_number")
            if phone and not re.match(r'^\+?\d{9,15}$', phone):
                raise ValueError("Некорректный формат номера телефона.")

        user = self.model(**extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_user(self, email, password, **extra_fields):
        """Создание обычного пользователя"""

        if not email:
            raise ValueError("Необходимо указать email.")
        email = self.normalize_email(email)

        extra_fields.setdefault("email", email)
        extra_fields.setdefault("role", self.model.Role.USER)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(password=password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Создание супер-пользователя"""

        if not email:
            raise ValueError("Необходимо указать email.")

        email = self.normalize_email(email)

        extra_fields.setdefault("email", email)
        extra_fields.setdefault("role", self.model.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("consent_accepted", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser должен иметь is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser должен иметь is_superuser=True.")

        return self._create_user(password=password, skip_validation=True, **extra_fields)

    def create_from_telegram(self, telegram_user, **extra_fields):
        """Создание аккаунта на основе TelegramUser."""

        extra_fields.setdefault("role", self.model.Role.USER)
        extra_fields.setdefault("first_name", telegram_user.first_name)
        extra_fields.setdefault("last_name", telegram_user.last_name)
        extra_fields.setdefault("username", telegram_user.username)
        extra_fields["telegram"] = telegram_user
        return self._create_user(**extra_fields)

    def get_by_telegram_id(self, telegram_id):
        return self.get(telegram__telegram_id=telegram_id)

    def admins(self):
        return self.filter(role=self.model.Role.ADMIN)

    def managers(self):
        return self.filter(role=self.model.Role.MANAGER)

    def supports(self):
        return self.filter(role=self.model.Role.SUPPORT)