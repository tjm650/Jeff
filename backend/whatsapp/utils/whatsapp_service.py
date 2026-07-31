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
            or os.getenv('TWILIO_AUTH_TOKEN')
        )
        self.phone_number_id = (
            os.getenv('META_PHONE_NUMBER_ID')
            or os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        )
        self.api_version = os.getenv('META_API_VERSION', 'v26.0')
        self.from_number = os.getenv('META_WHATSAPP_NUMBER') or os.getenv('TWILIO_WHATSAPP_NUMBER')

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

    def _send_payload(self, to_number: str, payload: Dict[str, Any]) -> bool:
        if not self.is_configured():
            logger.error('WhatsApp service not configured')
            return False

        normalized_to = self._normalize_to_number(to_number)
        if not normalized_to:
            logger.error('No recipient number provided for WhatsApp message')
            return False

        if not self.validate_zimbabwe_number(normalized_to):
            logger.warning('Sending to non-ZW number: %s', normalized_to)

        try:
            response = requests.post(
                self.base_url,
                headers=self._build_headers(),
                json={**payload, 'to': normalized_to},
                timeout=20,
            )
            response.raise_for_status()
            logger.info('Meta WhatsApp message sent successfully to %s', normalized_to)
            return True
        except requests.RequestException:
            logger.exception('Meta Cloud API error sending WhatsApp message')
            return False
        except Exception:
            logger.exception('Unexpected error sending WhatsApp message')
            return False

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

    def send_payment_confirmation(self, to_number: str, receipt: Optional[Dict[str, Any]] = None) -> bool:
        details = receipt or {}
        body = (
            f"Payment confirmed."
            f" Reference: {details.get('transaction_id', 'N/A')}"
            f" Amount: {details.get('amount_usd') or details.get('amount_zwg') or 'N/A'}"
        )
        return self.send_text_message(to_number, body)

    def send_payment_initiation(self, to_number: str, payment_details: Optional[Dict[str, Any]] = None) -> bool:
        details = payment_details or {}
        body = (
            'Please complete your payment to continue. '
            f"Reference: {details.get('reference', 'N/A')}"
        )
        return self.send_text_message(to_number, body)

    def send_payment_instructions(self, to_number: str) -> bool:
        return self.send_text_message(to_number, 'Please send your payment details and we will help you continue.')


# Create the module-level instance
whatsapp_service = WhatsAppService()
__all__ = ['WhatsAppService', 'whatsapp_service']