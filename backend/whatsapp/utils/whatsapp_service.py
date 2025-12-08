import os
import logging
from typing import Optional, List
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

logger = logging.getLogger(__name__)

class WhatsAppService:
    """Lightweight WhatsApp service wrapper for sending text messages via Twilio."""

    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        
        # FIX 1: Ensure the FROM number has the correct prefix immediately upon loading
        raw_from = os.getenv('TWILIO_WHATSAPP_NUMBER')
        
        
        if raw_from and not raw_from.startswith('whatsapp:'):
            self.from_number = f'whatsapp:{raw_from}'
        else:
            self.from_number = raw_from

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
        # Ensures format is "whatsapp:+123456789"
        return f'whatsapp:{phone_number}'

    def send_text_message(self, to_number: str, message: str) -> bool:
        if not self.is_configured():
            logger.error('WhatsApp service not configured')
            return False

        # Prevent sending to the Twilio sandbox number itself to avoid loops
        if to_number == '+14155238886':
            logger.info('Blocked message to Twilio sandbox number')
            return True

        # Check if we're using Twilio sandbox
        if 'whatsapp:+14155238886' in self.from_number:
            logger.warning('Using Twilio sandbox number - messages may fail for unverified numbers')
            # FIX 2: Commented out "return True" so you can actually TEST sending.
            # If you want to block sending in Sandbox, uncomment the line below.
            # return True 

        if not self.validate_zimbabwe_number(to_number):
            logger.warning(f'Sending to non-ZW number: {to_number}')

        try:
            # Format the "To" number
            whatsapp_to = self._format_to_whatsapp(to_number)
            
            # FIX 3: Use 'whatsapp_to' directly. Removed the extra f-string that caused double prefixing.
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

    def send_formatted_message(self, to_number: str, message: str, quick_replies: Optional[List[str]] = None) -> bool:
        """
        Send formatted message with UX formatting applied
        
        Args:
            to_number: Recipient phone number
            message: Message text
            quick_replies: Optional list of quick reply suggestions (formatted as text)
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            # Import UX formatter locally to avoid circular imports
            from core.services.conversation.ux_formatter import ux_formatter
            
            # Add quick replies if provided
            if quick_replies:
                message = ux_formatter.format_with_quick_replies(message, quick_replies)
            
            # Split long messages
            message_chunks = ux_formatter.split_long_message(message)
            
            # Send each chunk
            success = True
            for chunk in message_chunks:
                if not self.send_text_message(to_number, chunk):
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending formatted message: {str(e)}")
            # Fallback to regular text message
            return self.send_text_message(to_number, message)

# Create the module-level instance
whatsapp_service = WhatsAppService()
__all__ = ['WhatsAppService', 'whatsapp_service']