import logging
import uuid
from typing import Dict, Optional, Any
from datetime import datetime
from django.utils import timezone
from paynow import Paynow
import os


logger = logging.getLogger(__name__)

class PaynowService:
    """Paynow payment service for handling payment"""

    def __init__(self):
        """Initialize Paynow service"""
        self.integration_id = os.getenv('PAYNOW_INTEGRATION_ID')
        self.integration_key = os.getenv('PAYNOW_INTEGRATION_KEY')
        self.return_url = os.getenv('PAYNOW_RETURN_URL')
        self.result_url = os.getenv('PAYNOW_RESULT_URL')

        if not all([self.integration_id, self.integration_key]):
            logger.warning("Paynow credentials not fully configured")

        try:
            self.paynow = Paynow(
                integration_id=self.integration_id,
                integration_key=self.integration_key,
                return_url=self.return_url,
                result_url=self.result_url
            ) if self.integration_id and self.integration_key else None
        except Exception as e:
            logger.error(f"Failed to initialize Paynow client: {str(e)}")
            self.paynow = None

    def is_configured(self) -> bool:
        """Check if Paynow service is properly configured"""
        return all([
            self.integration_id,
            self.integration_key,
            self.return_url,
            self.result_url,
            self.paynow is not None
        ])

    def create_payment(self, phone_number: str, amount: float, reference: str = None) -> Dict[str, Any]:
        """
        Create a new payment request

        Args:
            phone_number (str): Customer's phone number
            amount (float): Payment amount
            reference (str, optional): Payment reference

        Returns:
            dict: Payment creation result with status and details
        """
        if not self.is_configured():
            return {
                'success': False,
                'message': 'Paynow service not configured'
            }

        try:
            # Generate reference if not provided
            if not reference:
                reference = f"JEFF_{timezone.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"

            # Create payment
            payment = self.paynow.create_payment(reference, 'JEFF')

            # Add customer details (amount used by gateway should be the numeric amount passed)
            payment.add('Accommodation Token', amount)

            # Send payment request for mobile money (Paynow only)
            response = self.paynow.send_mobile(payment, phone_number, 'paynow')

            if response.success:
                # Use configured amounts for display if available
                from django.conf import settings as dj_settings
                jeff = getattr(dj_settings, 'JEFF_SETTINGS', {})
                amount_usd = jeff.get('TOKEN_PRICE_USD', float(amount))
                amount_zwg = jeff.get('TOKEN_PRICE_ZWG', None)

                # Build user-facing message (no PDFs, no emojis)
                details = []
                details.append('Payment initiated!')
                details.append('')
                details.append('• Check your phone for the Paynow prompt')
                details.append('• Enter your PIN to complete payment')
                details.append('')
                details.append(f'Payment Number: {phone_number}')
                if amount_zwg is not None:
                    details.append(f'Amount ZWG: {float(amount_zwg):.2f} ZWG')
                details.append(f'Amount USD: ${float(amount_usd):.2f}')
                details.append(f'Reference: {reference}')
                details.append('')
                details.append("Send 'status' to check payment status")

                return {
                    'success': True,
                    'payment_reference': reference,
                    'poll_url': response.poll_url,
                    'instructions': '\n'.join(details),
                    'message': '\n'.join(details),
                    'amount_usd': float(amount_usd),
                    'amount_zwg': float(amount_zwg) if amount_zwg is not None else None
                }
            else:
                logger.error(f"Paynow payment creation failed: {getattr(response, 'error', response)}")
                err = getattr(response, 'error', None) or getattr(response, 'message', None) or str(response)
                return {
                    'success': False,
                    'message': f'Payment initiation failed: {err}'
                }

        except Exception as e:
            logger.error(f"Error creating Paynow payment: {str(e)}")
            return {
                'success': False,
                'message': 'failed creating payment. Please try again.'
            }

    def check_payment_status(self, reference: str) -> Dict[str, Any]:
        """
        Check the status of a payment

        Args:
            reference (str): Payment reference

        Returns:
            dict: Payment status information
        """
        if not self.is_configured():
            return {
                'success': False,
                'message': 'Paynow service not configured'
            }

        try:
            # Check payment status
            response = self.paynow.check_payment(reference)

            if response.success:
                status = response.status
                return {
                    'success': True,
                    'status': status,
                    'paid': status == 'paid',
                    'amount': getattr(response, 'amount', 0),
                    'reference': reference
                }
            else:
                return {
                    'success': False,
                    'message': f'failed  to check payment status: {response.error}'
                }

        except Exception as e:
            logger.error(f"Error checking payment status: {str(e)}")
            return {
                'success': False,
                'message': 'failed checking payment status. Please try again.'
            }

    def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Paynow webhook data

        Args:
            webhook_data (dict): Webhook data from Paynow

        Returns:
            dict: Processed webhook result
        """
        try:
            reference = webhook_data.get('reference')
            amount = webhook_data.get('amount')
            status = webhook_data.get('status')
            paynow_reference = webhook_data.get('paynow_reference')

            if not reference:
                return {
                    'success': False,
                    'message': 'Missing payment reference in webhook data'
                }

            # Here you would typically update your database with the payment status
            # For now, we'll just log and return the status

            logger.info(f"Webhook received - Reference: {reference}, Status: {status}, Amount: {amount}")

            return {
                'success': True,
                'reference': reference,
                'status': status,
                'amount': amount,
                'paynow_reference': paynow_reference,
                'processed_at': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return {
                'success': False,
                'message': 'failed processing webhook data'
            }

# Global instance
paynow_service = PaynowService()