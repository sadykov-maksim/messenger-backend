from django.contrib.sites.models import Site
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django.conf import settings

@receiver(post_migrate)
def set_default_domain(sender, **kwargs):
    # Checking the existence
    if Site.objects.filter(id=1).exists():
        # Getting the current Site object
        current_site = Site.objects.get_current()

        # From the environment
        site_domain = getattr(settings, "SITE_DOMAIN", "localhost")
        project_name = getattr(settings, "PROJECT_NAME", "Default Project")

        # Getting the current Site object
        current_site.domain = site_domain
        current_site.name = project_name
        current_site.save()
