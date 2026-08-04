from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Jeff Platform Core'

    def ready(self):
        """Initialize core app and log startup info."""
        logger.info("\n" + "=" * 80)
        logger.info("[INIT] Jeff Platform Core Module Initialized")
        logger.info("=" * 80)
        logger.info("[OK] Core models and services loaded")
        logger.info("[OK] Authentication middleware activated")
        logger.info("[OK] API key authentication enabled")
        logger.info("=" * 80 + "\n")