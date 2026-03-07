from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Account
from .utils.avatar import generate_identicon_png


@receiver(post_save, sender=Account)
def ensure_account_avatar(sender, instance: Account, created: bool, **kwargs):
    if instance.photo:
        return
    if instance.telegram and getattr(instance.telegram, "photo", None):
        return

    seed = instance.email or (str(instance.pk) if instance.pk else None) or instance.username or "user"

    file = generate_identicon_png(seed, size=256)
    filename = f"auto_{instance.pk}.png"

    instance.photo.save(filename, file, save=False)
    Account.objects.filter(pk=instance.pk).update(photo=instance.photo.name)