#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import logging


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Log startup info for migrations and other management commands
    if len(sys.argv) > 1 and sys.argv[1] == 'migrate':
        logger = logging.getLogger('whatsapp.apps')
        logger.info("\n" + "=" * 80)
        logger.info("🚀 Database Migration Starting")
        logger.info("=" * 80)
        logger.info("Running: python manage.py migrate")
        logger.info("This will prepare the database for WhatsApp webhook events")
        logger.info("=" * 80 + "\n")
    
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
