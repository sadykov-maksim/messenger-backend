from django.apps import AppConfig
from django.contrib.admin import AdminSite
from django.conf import settings


class TelegramConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telegram'

    def ready(self):
        site_domain = settings.SITE_DOMAIN
        project_name = settings.PROJECT_NAME

        AdminSite.site_header = f"{project_name}"
        AdminSite.site_title = f"{project_name} CMS"
        AdminSite.site_url = f"https://{site_domain}"
        AdminSite.index_title = "Система управления содержимым"
        AdminSite.enable_nav_sidebar = False

        import telegram.signals