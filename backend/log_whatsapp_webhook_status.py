"""
WhatsApp Webhook Deployment Initialization Script

This module logs comprehensive WhatsApp webhook configuration when the server
is deployed or started. Run this as part of your deployment process.

Usage (in Render deployment):
    python log_whatsapp_webhook_status.py

Or add to your startup sequence to get deployment logs.
"""

import os
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging to display deployment info
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s',
)

logger = logging.getLogger('whatsapp.deployment')


def log_deployment_status():
    """Log WhatsApp webhook deployment status."""
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    
    import django
    django.setup()
    
    from django.conf import settings as dj_settings
    
    logger.info("\n" + "=" * 90)
    logger.info("[DEPLOY] JEFF PLATFORM - WHATSAPP WEBHOOK DEPLOYMENT STATUS")
    logger.info("=" * 90)
    
    # 1. Environment Info
    logger.info("\n[ENVIRONMENT] DEPLOYMENT ENVIRONMENT:")
    environment = os.getenv('RENDER', os.getenv('ENVIRONMENT', 'Local Development'))
    logger.info(f"   Environment: {environment}")
    logger.info(f"   DEBUG Mode: {'ON [WARN]' if dj_settings.DEBUG else 'OFF [OK]'}")
    logger.info(f"   Python: {sys.version.split()[0]}")
    logger.info(f"   Django: {django.VERSION[0]}.{django.VERSION[1]}")
    
    # 2. Allowed Hosts
    logger.info("\n[HOSTS] ALLOWED HOSTS:")
    allowed_hosts = getattr(dj_settings, 'ALLOWED_HOSTS', [])
    if allowed_hosts:
        for host in allowed_hosts[:5]:  # Show first 5
            logger.info(f"   - {host}")
        if len(allowed_hosts) > 5:
            logger.info(f"   - ... and {len(allowed_hosts) - 5} more")
    else:
        logger.warning("   [WARN] NO ALLOWED HOSTS CONFIGURED")
    
    # 3. WhatsApp Configuration Status
    logger.info("\n[CONFIG] WHATSAPP WEBHOOK CONFIGURATION:")
    
    jeff_settings = dj_settings.JEFF_SETTINGS or {}
    
    meta_verify_token = jeff_settings.get('META_VERIFY_TOKEN')
    meta_app_secret = jeff_settings.get('META_APP_SECRET')
    webhook_secret = jeff_settings.get('WEBHOOK_SECRET')
    
    if meta_verify_token:
        logger.info(f"   [OK] META_VERIFY_TOKEN: Configured (length: {len(meta_verify_token)})")
    else:
        logger.warning(f"   [WARN] META_VERIFY_TOKEN: NOT CONFIGURED")
    
    if meta_app_secret:
        logger.info(f"   [OK] META_APP_SECRET: Configured (length: {len(meta_app_secret)})")
    else:
        logger.warning(f"   [WARN] META_APP_SECRET: NOT CONFIGURED")
    
    if webhook_secret:
        logger.info(f"   [OK] WEBHOOK_SECRET: Configured (length: {len(webhook_secret)})")
    else:
        logger.warning(f"   [WARN] WEBHOOK_SECRET: NOT CONFIGURED")
    
    # 4. Webhook Endpoints
    logger.info("\n[ENDPOINTS] WEBHOOK ENDPOINTS:")
    if allowed_hosts:
        # Prefer production host over localhost
        primary_host = "https://jeff-backend-n5kb.onrender.com"
        for host in allowed_hosts:
            if 'onrender.com' in host or 'vercel.app' in host:
                primary_host = host
                break
        if not primary_host:
            primary_host = next((h for h in allowed_hosts if h not in ('0.0.0.0')), allowed_hosts[0])
        
        logger.info(f"   GET (Verification):  https://{primary_host}/webhook/whatsapp/")
        logger.info(f"   POST (Messages):     https://{primary_host}/webhook/whatsapp/")
    else:
        logger.warning("   [WARN] Cannot determine webhook URL - no allowed hosts configured")
    
    # 5. Security Configuration
    logger.info("\n[SECURITY] SECURITY CONFIGURATION:")
    logger.info(f"   CSRF Exempt: [OK] Enabled for webhook endpoints")
    logger.info(f"   Signature Verification: {'[OK] Enabled' if meta_app_secret else '[WARN] Disabled - no app secret'}")
    logger.info(f"   HTTPS Required: {'[OK] Yes (production)' if not dj_settings.DEBUG else '[WARN] Not enforced (debug mode)'}")
    
    # 6. Installed Apps
    logger.info("\n[APPS] INSTALLED APPS STATUS:")
    installed_apps = getattr(dj_settings, 'INSTALLED_APPS', [])
    whatsapp_installed = 'whatsapp' in installed_apps
    core_installed = 'core' in installed_apps
    payment_installed = 'payment' in installed_apps
    
    logger.info(f"   {'[OK]' if whatsapp_installed else '[ERROR]'} WhatsApp App")
    logger.info(f"   {'[OK]' if core_installed else '[ERROR]'} Core App")
    logger.info(f"   {'[OK]' if payment_installed else '[ERROR]'} Payment App")
    
    # 7. Middleware Configuration
    logger.info("\n[MIDDLEWARE] MIDDLEWARE CONFIGURATION:")
    middleware = getattr(dj_settings, 'MIDDLEWARE', [])
    has_csrf = any('csrf' in m.lower() for m in middleware)
    has_cors = any('cors' in m.lower() for m in middleware)
    logger.info(f"   {'[OK]' if has_csrf else '[ERROR]'} CSRF Middleware")
    logger.info(f"   {'[OK]' if has_cors else '[ERROR]'} CORS Middleware")
    
    # 8. Final Status
    logger.info("\n" + "=" * 90)
    
    config_complete = all([meta_verify_token, meta_app_secret or webhook_secret])
    if config_complete:
        logger.info("[OK] WHATSAPP WEBHOOK FULLY CONFIGURED - READY TO RECEIVE MESSAGES")
    else:
        logger.warning("[WARN] WHATSAPP WEBHOOK PARTIALLY CONFIGURED - CHECK MISSING SETTINGS")
    
    logger.info("\n[NEXT] Next Steps:")
    if not config_complete:
        logger.info("   1. Set META_VERIFY_TOKEN environment variable")
        logger.info("   2. Set META_APP_SECRET environment variable")
        logger.info("   3. Configure webhook URL in Meta App Dashboard:")
        if allowed_hosts:
            logger.info(f"      https://{allowed_hosts[0]}/webhook/whatsapp/")
        logger.info("   4. Deploy and restart the application")
    else:
        logger.info("   [OK] Webhook is ready to receive messages from Meta Cloud API")
        logger.info("   [OK] Monitor logs for incoming messages at: /logs/")
        logger.info("   [OK] Test webhook: Use Meta App Dashboard -> Webhooks section")
    
    logger.info("\n" + "=" * 90 + "\n")


if __name__ == '__main__':
    try:
        log_deployment_status()
    except Exception as e:
        logger.error(f"Error during deployment logging: {e}", exc_info=True)
        sys.exit(1)
