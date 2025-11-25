from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Jeff Platform Core'

    def ready(self):
        # Import signals or perform app initialization
        pass 