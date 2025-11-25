import os
import json
import logging
from typing import Dict, Any, List, Optional
from twilio.rest import Client #type: ignore
from twilio.base.exceptions import TwilioException  # type: ignore

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Lightweight WhatsApp service wrapper for sending text messages via Twilio."""

    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = os.getenv('TWILIO_WHATSAPP_NUMBER')  # e.g. 'whatsapp:+1234567890'

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
            # Expect international format
            return False
        return phone_number.startswith('+263')

    def _format_to_whatsapp(self, phone_number: str) -> str:
        return f'whatsapp:{phone_number}'

    def send_text_message(self, to_number: str, message: str) -> bool:
        """Send a plain text WhatsApp message. Returns True on success."""
        if not self.is_configured():
            logger.error('WhatsApp service not configured')
            return False

        # Block sending to Twilio sandbox number to prevent "same To and From" errors
        if to_number == '+14155238886':
            logger.info('Blocked message to Twilio sandbox number')
            return True

        # Best-effort: allow sending to non-ZW numbers but warn and attempt once
        if not self.validate_zimbabwe_number(to_number):
            logger.warning(f'Sending to non-ZW number: {to_number}')

        try:
            whatsapp_to = self._format_to_whatsapp(to_number)
            msg = self.client.messages.create(from_=self.from_number, to=whatsapp_to, body=message)
            logger.info('WhatsApp message sent, sid=%s', getattr(msg, 'sid', None))
            return True
        except TwilioException:
            logger.exception('Twilio error sending WhatsApp message')
            return False
        except Exception:
            logger.exception('Unexpected error sending WhatsApp message')
            return False

    def send_template_message(self, to_number: str, content_sid: str, content_variables: Dict[str, Any]) -> bool:
        """Send a WhatsApp Content Template message via Twilio. Returns True on success.

        Expects Twilio Content Template SID and a dict of variables keyed as strings ("1", "2", ...).
        The content_variables dict will be converted to a JSON string as required by Twilio API.
        """
        if not self.is_configured():
            logger.error('WhatsApp service not configured')
            return False

        if not content_sid:
            logger.error('Missing content_sid for template message')
            return False

        # Best-effort: allow sending to non-ZW numbers but warn and attempt once
        if not self.validate_zimbabwe_number(to_number):
            logger.warning(f'Sending to non-ZW number: {to_number}')

        try:
            whatsapp_to = self._format_to_whatsapp(to_number)
            # Convert content_variables dict to JSON string as required by Twilio API
            content_variables_json = json.dumps(content_variables)
            
            # Twilio Messages API supports content_sid and content_variables (as JSON string)
            msg = self.client.messages.create(
                from_=self.from_number,
                to=whatsapp_to,
                content_sid=content_sid,
                content_variables=content_variables_json
            )
            logger.info('WhatsApp template message sent, sid=%s', getattr(msg, 'sid', None))
            return True
        except TwilioException:
            logger.exception('Twilio error sending WhatsApp template message')
            return False
        except Exception:
            logger.exception('Unexpected error sending WhatsApp template message')
            return False

    def send_payment_initiation(self, to_number: str, amount_usd: Optional[float], amount_zwg: Optional[float], reference: str, payment_number: str) -> bool:
        # Get configured prices from settings
        from django.conf import settings
        jeff_settings = getattr(settings, 'JEFF_SETTINGS', {})
        token_price_usd = jeff_settings.get('TOKEN_PRICE_USD', 1.00)
        token_price_zwg = jeff_settings.get('TOKEN_PRICE_ZWG', None)
        
        lines: List[str] = []
        if amount_zwg is not None or token_price_zwg is not None:
            display_amount_zwg = float(amount_zwg if amount_zwg is not None else token_price_zwg)
            lines.append(f'Amount ZWG: {display_amount_zwg:.2f} ZWG')
        if amount_usd is not None or token_price_usd is not None:
            display_amount_usd = float(amount_usd if amount_usd is not None else token_price_usd)
            lines.append(f'Amount USD: ${display_amount_usd:.2f}')
        lines.extend([f'Reference: {reference}', '', "Send 'status' to check payment status"])
        return self.send_text_message(to_number, '\n'.join(lines))

    def send_payment_confirmation(self, to_number: str, receipt: Dict[str, Any]) -> bool:
        lines: List[str] = ['Payment successful', '']
        if receipt.get('transaction_id'):
            lines.append('Transaction Details:')
            lines.append(f"Transaction ID: {receipt.get('transaction_id')}")
        if receipt.get('amount_zwg') is not None:
            lines.append(f"Amount ZWG: {float(receipt.get('amount_zwg')):.2f} ZWG")
        if receipt.get('amount_usd') is not None:
            lines.append(f"Amount USD: ${float(receipt.get('amount_usd')):.2f}")
        if receipt.get('date'):
            lines.append(f"Date: {receipt.get('date')}")
        if receipt.get('payment_method'):
            lines.append(f"Payment Method: {str(receipt.get('payment_method')).upper()}")
        if receipt.get('token_info'):
            token = receipt.get('token_info')
            lines.extend(['', f"Token: {token.get('token_number')}", f"Uses: {token.get('total_uses')} (used {token.get('used_count')})"])

        lines.append('')
        lines.append('Thank you for using JEFF')
        return self.send_text_message(to_number, '\n'.join(lines))

    def send_error_message(self, to_number: str, error_message: str) -> bool:
        message = (
            f"Payment Error - JEFF\n\n{error_message}\n\n"
        )
        return self.send_text_message(to_number, message)

    def send_payment_instructions(self, to_number: str) -> bool:
        """Send comprehensive payment instructions including current token prices."""
        # Get configured prices from settings
        from django.conf import settings
        jeff_settings = getattr(settings, 'JEFF_SETTINGS', {})
        token_price_usd = jeff_settings.get('TOKEN_PRICE_USD', 1.00)
        token_price_zwg = jeff_settings.get('TOKEN_PRICE_ZWG', None)
        token_uses = jeff_settings.get('TOKEN_USES', 2)
        frontend_url = os.getenv('NEXT_PUBLIC_FRONTEND_URL', 'https://jeff-platform.com')

        lines: List[str] = [
            '*JEFF Payment Instructions*',
            '',
            'To use our accommodation service, you need to purchase a token:',
            '',
            f'• Token Price: ${token_price_usd:.2f} USD',
        ]

        if token_price_zwg is not None:
            lines.append(f'• Or: {token_price_zwg:.2f} ZWG')

        lines.extend([
            f'• Each token allows {token_uses} property viewings',
            '',
            '*Payment Options:*',
            '',
            '*Option 1: Web Payment (Recommended)*',
            f'• Visit: {frontend_url}/cart',
            '• Enter your Chat Number and Payment Number',
            '• Complete payment securely online',
            '',
            '*Option 2: WhatsApp Payment*',
            '• Send "USD PAY <your-number>" for USD payment',
            '• Send "ZWG PAY <your-number>" for ZWL payment',
            '• Example: USD PAY 0771234567',
            '',
            '*Need Help?*',
            '• Send "help" for customer support',
            '• Send "status" to check payment status'
        ])

        return self.send_text_message(to_number, '\n'.join(lines))


# Create the module-level instance and manually add it to the module's __all__
whatsapp_service = WhatsAppService()
__all__ = ['WhatsAppService', 'whatsapp_service']