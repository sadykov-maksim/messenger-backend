import json
from telegram.models import TelegramUser


def get_or_create_user(telegram_data):
    telegram_data = json.loads(telegram_data)

    telegram_id = int(telegram_data.get('id'))
    user = TelegramUser.objects.filter(user_id=telegram_id).first()

    if user:
        return user, False
    else:
        user = TelegramUser.objects.create(
            user_id=telegram_id,
            username=telegram_data.get('username'),
            first_name=telegram_data.get('first_name'),
            last_name=telegram_data.get('last_name'),
        )
        return user, True
