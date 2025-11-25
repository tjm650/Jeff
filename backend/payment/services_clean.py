from paynow import Paynow
from django.conf import settings
import logging
import uuid
import os
from decimal import Decimal

logger = logging.getLogger(__name__)


class PaynowService:
    """Service class to handle PayNow/mobile payment operations for WhatsApp agent.

    Notes:
    - This service uses the Paynow library to create and poll mobile payment.
    - Historically this referenced EcoCash; we now standardise on 'paynow' as the
      mobile payment provider name used with the Paynow client.
    """

    # Fixed amount for agent service - read from environment
    AGENT_AMOUNT = Decimal(str(os.getenv('TOKEN_PRICE', '1.00')))

    def __init__(self):
        # Get PayNow settings from Django settings (nested under JEFF_SETTINGS)
        jeff_settings = getattr(settings, 'JEFF_SETTINGS', {})
        integration_id = jeff_settings.get('PAYNOW_INTEGRATION_ID')
        integration_key = jeff_settings.get('PAYNOW_INTEGRATION_KEY')
        return_url = jeff_settings.get('PAYNOW_RETURN_URL')
        result_url = jeff_settings.get('PAYNOW_RESULT_URL')

        # Check if required settings are available
        if not all([integration_id, integration_key, return_url, result_url]):
            logger.warning("PayNow credentials not configured. Please set environment variables.")
            self.paynow = None
            return

        self.paynow = Paynow(integration_id, integration_key, return_url, result_url)

    def create_agent_payment(self, whatsapp_number, payment_number, reference=None):
        """
        Create a fixed-amount Paynow/mobile payment for WhatsApp agent service.

        Args:
            whatsapp_number (str): User's WhatsApp number
            payment_number (str): mobile payment number to charge (used by Paynow)
            reference (str): Optional internal reference

        Returns:
            dict: Payment response with success status, poll_url, etc.
        """
        try:
            if not self.paynow:
                return {'success': False, 'error': 'Paynow not configured'}

            # Format payment number and whatsapp number
            payment_number = payment_number.strip().replace(' ', '')
            whatsapp_number = whatsapp_number.strip().replace(' ', '')

            # PayNow requires email; use payment_number as placeholder
            email = f"{payment_number}@whatsapp.agent"

            # Generate unique reference if not provided
            if not reference:
                reference = f"WA-{whatsapp_number[-6:]}-{uuid.uuid4().hex[:8]}"

            # Create payment with fixed amount
            amount = float(self.AGENT_AMOUNT)
            payment = self.paynow.create_payment(reference, email)
            payment.add('WhatsApp Agent Service', amount)

            # Initiate mobile payment with Paynow provider name
            logger.info(f"Initiating agent payment: WA: {whatsapp_number}, Pay: {payment_number}, Amount: ${amount}")
            response = self.paynow.send_mobile(payment, payment_number, 'paynow')

            if getattr(response, 'success', False):
                logger.info(f"Payment initiated successfully: {getattr(response, 'poll_url', '')}")

                return {
                    'success': True,
                    'poll_url': getattr(response, 'poll_url', ''),
                    'redirect_url': getattr(response, 'redirect_url', ''),
                    'paynow_reference': getattr(response, 'reference', '') or getattr(response, 'paynow_reference', ''),
                    'instructions': getattr(response, 'instructions', 'Check your phone for the mobile payment prompt'),
                    'reference': reference,
                    'amount': self.AGENT_AMOUNT
                }
            else:
                # Debug: log details
                logger.error(f"Payment initiation failed. Response type: {type(response)}")
                logger.error(f"Response attributes: {dir(response)}")

                # Extract an error message if available
                error_message = None
                for attr in ('error', 'errors', 'message'):
                    if hasattr(response, attr) and getattr(response, attr):
                        error_message = getattr(response, attr)
                        break

                if not error_message:
                    error_message = f"Payment failed: {response}"

                logger.error(f"Payment initiation failed: {error_message}")
                return {'success': False, 'error': str(error_message), 'reference': reference}

        except Exception as e:
            logger.exception(f"Payment creation error: {str(e)}")
            return {'success': False, 'error': f'Payment creation failed: {str(e)}'}

    def check_transaction_status(self, poll_url):
        """
        Check payment transaction status

        Args:
            poll_url (str): Poll URL from payment initiation

        Returns:
            str: Payment status (paid, cancelled, failed, pending)
        """
        try:
            if not self.paynow:
                logger.error("Paynow client not configured for status check")
                return 'error'

            status = self.paynow.check_transaction_status(poll_url)

            if getattr(status, 'paid', False):
                logger.info(f"Transaction paid: {poll_url}")
                return 'paid'
            if getattr(status, 'cancelled', False):
                logger.info(f"Transaction cancelled: {poll_url}")
                return 'cancelled'
            if getattr(status, 'failed', False):
                logger.error(f"Transaction failed: {poll_url}")
                return 'failed '
            return 'pending'

        except Exception as e:
            logger.exception(f"Status check error: {str(e)}")
            return 'error'
