import logging
import os
import time
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Lightweight WhatsApp service wrapper for Meta Cloud API."""

    def __init__(self):
        self.access_token = os.getenv('META_ACCESS_TOKEN') or os.getenv('WHATSAPP_ACCESS_TOKEN') or os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number_id = os.getenv('META_PHONE_NUMBER_ID') or os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.api_version = os.getenv('META_API_VERSION', 'v26.0')
        self.from_number = os.getenv('META_WHATSAPP_NUMBER') or os.getenv('TWILIO_WHATSAPP_NUMBER')
        self.base_url = f'https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages' if self.phone_number_id else None
        if not self.is_configured():
            logger.warning('Meta WhatsApp credentials not fully configured')

    def is_configured(self) -> bool:
        return bool(self.access_token and self.phone_number_id)

    def validate_zimbabwe_number(self, phone_number: str) -> bool:
        return bool(phone_number and phone_number.startswith('+') and phone_number.startswith('+263'))

    def _normalize_to_number(self, phone_number: str) -> str:
        phone_number = (phone_number or '').strip()
        if not phone_number:
            return ''
        if phone_number.startswith('whatsapp:'):
            phone_number = phone_number[len('whatsapp:'):]
        return phone_number if phone_number.startswith('+') else f'+{phone_number}'

    def _build_headers(self) -> Dict[str, str]:
        return {'Authorization': f'Bearer {self.access_token}', 'Content-Type': 'application/json'}

    def _send_payload(self, to_number: str, payload: Dict[str, Any]) -> bool:
        from core.diagnostics import record_event, get_context
        correlation_id, _ = get_context()
        correlation_id = correlation_id or 'outbound-' + str(int(time.time() * 1000))
        normalized_to = self._normalize_to_number(to_number)
        record_event(correlation_id=correlation_id, direction='outbound', event_type='message_send', stage='outbound_validate', status='started', phone_number=normalized_to, metadata={'configured': self.is_configured()})

        if not self.is_configured():
            logger.error('WhatsApp service not configured')
            record_event(correlation_id=correlation_id, direction='outbound', event_type='message_send', stage='outbound_config', status='failed', phone_number=normalized_to, error_message='Meta WhatsApp credentials not fully configured')
            return False
        if not normalized_to:
            logger.error('No recipient number provided for WhatsApp message')
            record_event(correlation_id=correlation_id, direction='outbound', event_type='message_send', stage='outbound_validate', status='failed', error_message='No recipient number provided')
            return False
        if not self.validate_zimbabwe_number(normalized_to):
            logger.warning('Sending to non-ZW number: %s', normalized_to)

        started = time.monotonic()
        try:
            response = requests.post(self.base_url, headers=self._build_headers(), json={**payload, 'to': normalized_to}, timeout=20)
            response.raise_for_status()
            response_json = response.json() if response.content else {}
            messages = response_json.get('messages') or []
            external_id = messages[0].get('id', '') if messages else ''
            duration_ms = int((time.monotonic() - started) * 1000)
            record_event(correlation_id=correlation_id, direction='outbound', event_type='message_send', stage='meta_api_accepted', status='ok', phone_number=normalized_to, external_id=external_id, duration_ms=duration_ms, metadata={'http_status': response.status_code})
            logger.info('WhatsApp message successfully sent to recipient: %s', normalized_to)
            print(f' WhatsApp message successfully sent to {normalized_to}')
            return True
        except requests.RequestException as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            detail = getattr(getattr(exc, 'response', None), 'text', '')[:1000]
            record_event(correlation_id=correlation_id, direction='outbound', event_type='message_send', stage='meta_api_accepted', status='failed', phone_number=normalized_to, duration_ms=duration_ms, error_message=f'{exc}; response={detail}')
            logger.exception('Meta Cloud API error sending WhatsApp message')
            return False
        except Exception as exc:
            record_event(correlation_id=correlation_id, direction='outbound', event_type='message_send', stage='outbound_exception', status='failed', phone_number=normalized_to, error_message=str(exc))
            logger.exception('Unexpected error sending WhatsApp message')
            return False

    def send_text_message(self, to_number: str, message: str) -> bool:
        return self._send_payload(to_number, {'messaging_product': 'whatsapp', 'recipient_type': 'individual', 'type': 'text', 'text': {'body': message}})

    def send_template_message(self, to_number: str, template_name: str, template_variables: Optional[Dict[str, Any]] = None) -> bool:
        payload = {'messaging_product': 'whatsapp', 'recipient_type': 'individual', 'type': 'template', 'template': {'name': template_name, 'language': {'code': 'en_US'}, 'components': []}}
        if template_variables:
            payload['template']['components'] = [{'type': 'body', 'parameters': [{'type': 'text', 'text': str(value)} for value in template_variables.values()]}]
        return self._send_payload(to_number, payload)

    def send_error_message(self, to_number: str, message: str) -> bool:
        return self.send_text_message(to_number, message)

    def send_payment_confirmation(self, to_number: str, receipt: Optional[Dict[str, Any]] = None) -> bool:
        details = receipt or {}
        return self.send_text_message(to_number, f"Payment confirmed. Reference: {details.get('transaction_id', 'N/A')} Amount: {details.get('amount_usd') or details.get('amount_zwg') or 'N/A'}")

    def send_payment_initiation(self, to_number: str, payment_details: Optional[Dict[str, Any]] = None) -> bool:
        details = payment_details or {}
        return self.send_text_message(to_number, 'Please complete your payment to continue. ' f"Reference: {details.get('reference', 'N/A')}")

    def send_payment_instructions(self, to_number: str) -> bool:
        return self.send_text_message(to_number, 'Please send your payment details and we will help you continue.')


whatsapp_service = WhatsAppService()
__all__ = ['WhatsAppService', 'whatsapp_service']
