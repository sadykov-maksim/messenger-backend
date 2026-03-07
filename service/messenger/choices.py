from django.db import models

class RoomType(models.TextChoices):
    PRIVATE = 'private', 'Личный'
    GROUP = 'group', 'Групповой'