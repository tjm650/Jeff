"""
WSGI config for backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import logging

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

application = get_wsgi_application()

# Log deployment info when WSGI app is initialized
logger = logging.getLogger('whatsapp.apps')
logger.info("\n" + "=" * 80)
logger.info("[DEPLOYED] WSGI Application Deployed")
logger.info("=" * 80)
logger.info(f"Environment: {os.getenv('RENDER', 'Local Development')}")
logger.info(f"DEBUG mode: {os.getenv('DEBUG', 'False')}")
logger.info("WhatsApp webhooks are now active and ready to receive Meta Cloud API events")
logger.info("=" * 80 + "\n")
