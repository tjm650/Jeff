import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Lightweight WhatsApp service wrapper for Meta Cloud API."""

    def __init__(self):
        self.access_token = (
            os.getenv('META_ACCESS_TOKEN')
            or os.getenv('WHATSAPP_ACCESS_TOKEN')
        )
        self.phone_number_id = (
            os.getenv('META_PHONE_NUMBER_ID')
            or os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        )
        self.api_version = os.getenv('META_API_VERSION', 'v26.0')
        self.from_number = os.getenv('META_WHATSAPP_NUMBER') or None

        self.base_url = (
            f'https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages'
            if self.phone_number_id else None
        )

        if not self.is_configured():
            logger.warning('Meta WhatsApp credentials not fully configured')

    def is_configured(self) -> bool:
        return bool(self.access_token and self.phone_number_id)

    def validate_zimbabwe_number(self, phone_number: str) -> bool:
        if not phone_number:
            return False
        if not phone_number.startswith('+'):
            return False
        return phone_number.startswith('+263')

    def _normalize_to_number(self, phone_number: str) -> str:
        phone_number = (phone_number or '').strip()
        if not phone_number:
            return ''
        if phone_number.startswith('whatsapp:'):
            phone_number = phone_number[len('whatsapp:'):]
        if phone_number.startswith('+'):
            return phone_number
        return f'+{phone_number}'

    def _build_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }

    def send_text_message(self, to_number: str, message: str) -> bool:
        payload = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'type': 'text',
            'text': {'body': message},
        }
        return self._send_payload(to_number, payload)

    def send_template_message(self, to_number: str, template_name: str, template_variables: Optional[Dict[str, Any]] = None) -> bool:
        payload = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'type': 'template',
            'template': {
                'name': template_name,
                'language': {'code': 'en_US'},
                'components': [],
            },
        }
        if template_variables:
            payload['template']['components'] = [
                {'type': 'body', 'parameters': [{'type': 'text', 'text': str(value)} for value in template_variables.values()]}
            ]
        return self._send_payload(to_number, payload)

    def send_error_message(self, to_number: str, message: str) -> bool:
        return self.send_text_message(to_number, message)


    def send_payment_instructions(self, to_number: str) -> bool:
        return self.send_text_message(to_number, 'Please send your payment details and we will help you continue.')


# Create the module-level instance
whatsapp_service = WhatsAppService()
__all__ = ['WhatsAppService', 'whatsapp_service']