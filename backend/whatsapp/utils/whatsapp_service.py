import os
import json
import logging
from typing import Dict, Any, List, Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Lightweight WhatsApp service wrapper for sending text messages via Twilio."""

    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = os.getenv('TWILIO_WHATSAPP_NUMBER')

        if not all([self.account_sid, self.auth_token, self.from_number]):
            logger.warning('Twilio WhatsApp credentials not fully configured')

        try:
            self.client = Client(self.account_sid, self.auth_token) if self.account_sid and self.auth_token else None
        except Exception:
            logger.exception('Failed to initialize Twilio client')
            self.client = None

    def is_configured(self) -> bool:
        return bool(self.client and self.from_number)

    def validate_zimbabwe_number(self, phone_number: str) -> bool:
        if not phone_number:
            return False
        if not phone_number.startswith('+'):
            return False
        return phone_number.startswith('+263')

    def _format_to_whatsapp(self, phone_number: str) -> str:
        return f'whatsapp:{phone_number}'

    def send_text_message(self, to_number: str, message: str) -> bool:
        if not self.is_configured():
            logger.error('WhatsApp service not configured')
            return False

        if to_number == '+14155238886':
            logger.info('Blocked message to Twilio sandbox number')
            return True

        if not self.validate_zimbabwe_number(to_number):
            logger.warning(f'Sending to non-ZW number: {to_number}')

        try:
            whatsapp_to = self._format_to_whatsapp(to_number)
            msg = self.client.messages.create(
                from_=self.from_number,
                to=whatsapp_to,
                body=message
            )
            logger.info('WhatsApp message sent, sid=%s', getattr(msg, 'sid', None))
            return True
        except TwilioException:
            logger.exception('Twilio error sending WhatsApp message')
            return False
        except Exception:
            logger.exception('Unexpected error sending WhatsApp message')
            return False


# Create the module-level instance
whatsapp_service = WhatsAppService()
__all__ = ['WhatsAppService', 'whatsapp_service']