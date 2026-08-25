from django.apps import AppConfig


class SettingsWebConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.settings_web'
    label = 'settings_web'
    verbose_name = 'Merchant Settings'
