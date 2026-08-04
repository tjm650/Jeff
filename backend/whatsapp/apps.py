import logging
from django.apps import AppConfig
from django.conf import settings as dj_settings

logger = logging.getLogger(__name__)


class WhatsappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'whatsapp'
    verbose_name = 'WhatsApp Integration'

    def ready(self):
        """Initialize WhatsApp webhook configuration on app startup."""
        logger.info("=" * 80)
        logger.info("[START] WhatsApp Integration Module Initialized")
        logger.info("=" * 80)
        
        # Log webhook configuration status
        meta_verify_token = dj_settings.JEFF_SETTINGS.get('META_VERIFY_TOKEN')
        meta_app_secret = dj_settings.JEFF_SETTINGS.get('META_APP_SECRET')
        webhook_secret = dj_settings.JEFF_SETTINGS.get('WEBHOOK_SECRET')
        
        logger.info("WhatsApp Webhook Configuration Status:")
        logger.info(f"   [OK] META_VERIFY_TOKEN: {'[OK] Configured' if meta_verify_token else '[WARN] NOT configured'}")
        logger.info(f"   [OK] META_APP_SECRET: {'[OK] Configured' if meta_app_secret else '[WARN] NOT configured'}")
        logger.info(f"   [OK] WEBHOOK_SECRET: {'[OK] Configured' if webhook_secret else '[WARN] NOT configured'}")
        
        # Log webhook URL info
        allowed_hosts = getattr(dj_settings, 'ALLOWED_HOSTS', [])
        if allowed_hosts:
            # Prefer production host over localhost
            primary_host = None
            for host in allowed_hosts:
                if 'onrender.com' in host or 'vercel.app' in host:
                    primary_host = host
                    break
            if not primary_host:
                primary_host = next((h for h in allowed_hosts if h not in ('localhost', '127.0.0.1', '0.0.0.0')), allowed_hosts[0])
            
            logger.info(f"\nWhatsApp Webhook Endpoints:")
            logger.info(f"   - GET:  https://{primary_host}/webhook/whatsapp/")
            logger.info(f"   - POST: https://{primary_host}/webhook/whatsapp/")
        
        # Log security settings
        logger.info(f"\nSecurity Configuration:")
        debug_mode = getattr(dj_settings, 'DEBUG', False)
        logger.info(f"   [OK] DEBUG mode: {'ON' if debug_mode else 'OFF'}")
        csrf_trusted = 'whatsapp_webhook' in str(dj_settings.MIDDLEWARE)
        logger.info(f"   [OK] CSRF exemption: {'[OK] Enabled' if csrf_trusted else '[WARN] Check middleware'}")
        
        logger.info("\n[READY] WhatsApp module ready to receive webhook events")
        logger.info("=" * 80 + "\n")
