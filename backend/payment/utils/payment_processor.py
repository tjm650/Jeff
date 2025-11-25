"""
Payment Processor for handling successful payment and notifications
"""

import logging
import os
from datetime import datetime
from django.utils import timezone
from core.models import Transaction, Token
from payment.models import Payment
from whatsapp.utils.whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)


class PaymentProcessor:
    """Handles post-payment processing including token generation and notifications"""

    def process_successful_payment(self, payment: Payment) -> dict:
        """
        Process a successful PayNow payment

        Args:
            payment: Payment model instance

        Returns:
            dict: Processing result with success status and details
        """
        try:
            logger.info(f"Processing successful payment: {payment.transaction_id}")

            # Create transaction record
            transaction = self._create_transaction_record(payment)

            # Generate token
            token = self._generate_payment_token(transaction)

            # Send Twilio notification
            notification_result = self._send_payment_notification(payment, transaction, token)

            logger.info(f"Payment processing completed for: {payment.transaction_id}")

            return {
                'success': True,
                'transaction': transaction,
                'token': token,
                'notification_sent': notification_result,
                'message': 'Payment processed successfully'
            }

        except Exception as e:
            logger.error(f"Error processing successful payment {payment.transaction_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to process payment'
            }

    def _create_transaction_record(self, payment: Payment) -> Transaction:
        """Create transaction record for successful payment"""
        transaction = Transaction.objects.create(
            cell_number=payment.whatsapp_number,
            transaction_number=payment.paynow_reference or payment.reference,
            amount=payment.amount,
            payment_method='paynow',
            status='verified',
            pop_verified=True,
            verified_at=timezone.now()
        )

        logger.info(f"Created transaction record: {transaction.transaction_number}")
        return transaction

    def _generate_payment_token(self, transaction: Transaction) -> Token:
        """Generate token for successful payment"""
        # Generate unique token number
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_prefix = ''.join(random.choices(string.ascii_uppercase, k=2))
        # Use a simple counter based on existing tokens
        token_count = Token.objects.count() + 1
        token_number = f"{random_prefix}-{token_count:04d}-{timestamp}"

        # Create token with 30-day validity and 1 use (+1 token as requested)
        expires_at = timezone.now() + timedelta(days=30)

        token = Token.objects.create(
            cell_number=transaction.cell_number,
            token_number=token_number,
            total_uses=1,
            used_count=0,
            is_active=True,
            purchased_at=timezone.now(),
            expires_at=expires_at,
            transaction=transaction
        )

        logger.info(f"Generated token: {token.token_number} for transaction: {transaction.transaction_number}")
        return token

    def _send_payment_notification(self, payment: Payment, transaction: Transaction, token: Token) -> bool:
        """Send payment confirmation via Twilio WhatsApp Content Template"""
        try:
            # Try to send using content template first
            content_sid = os.getenv('TWILIO_CONTENT_TEMPLATE_SID_STUDENT_PAYMENT_CONFIRMATION')
            if content_sid:
                # Prepare template variables from the created records
                content_variables = {
                    "1": transaction.transaction_number,  # Transaction number from record
                    "2": transaction.created_at.strftime('%Y-%m-%d'),  # Date from transaction record
                    "3": transaction.created_at.strftime('%H:%M'),  # Time from transaction record
                    "4": f"${transaction.amount}",  # Price from transaction record
                    "5": str(token.total_uses),  # Token count from token record
                    "6": token.expires_at.strftime('%Y-%m-%d')  # Expiry Date from token record
                }

                success = whatsapp_service.send_template_message(
                    payment.whatsapp_number,
                    content_sid,
                    content_variables
                )

                if success:
                    logger.info(f"Payment confirmation template sent to {payment.whatsapp_number}")
                    return True

            # Fallback to plain text message if template fails or is not configured
            logger.warning("Content template not available or failed, falling back to plain text message")
            message = self._format_confirmation_message(payment, transaction, token)
            success = whatsapp_service.send_text_message(payment.whatsapp_number, message)

            if success:
                logger.info(f"Payment confirmation (fallback) sent to {payment.whatsapp_number}")
            else:
                logger.error(f"Failed to send payment confirmation to {payment.whatsapp_number}")

            return success

        except Exception as e:
            logger.error(f"Error sending payment notification: {str(e)}")
            return False

    def _format_confirmation_message(self, payment: Payment, transaction: Transaction, token: Token) -> str:
        """Format the payment confirmation message according to specifications"""
        # Mask phone numbers (show last 4 digits)
        chat_number_masked = f"****{payment.whatsapp_number[-4:]}"
        payment_number_masked = f"****{payment.payment_number[-4:]}"

        message = f"""*PAYMENT CONFIRMED*
Date: {timezone.now().strftime('%Y-%m-%d')}
Time: {timezone.now().strftime('%H:%M')}
Chat Number: {chat_number_masked}
Payment Number: {payment_number_masked}
Amount Paid: ${transaction.amount}
Transaction Number: {transaction.transaction_number}

YOUR ACCESS TOKEN:
Token: {token.token_number}
Uses Remaining: {token.remaining_uses()}
Expires: {token.expires_at.strftime('%Y-%m-%d')}

Your token is now active! You can start searching for accommodation.

Need help? send a help mesage."""

        return message


# Import here to avoid circular imports
import random
import string
from datetime import timedelta

# Global instance
payment_processor = PaymentProcessor()


def send_payment_confirmation(whatsapp_number: str, transaction: Transaction, token: Token) -> bool:
    """
    Utility function to send payment confirmation (for backward compatibility)

    Args:
        whatsapp_number: Recipient's WhatsApp number
        transaction: Transaction model instance
        token: Token model instance

    Returns:
        bool: True if sent successfully
    """
    try:
        # Create a temporary payment object for formatting
        class TempPayment:
            def __init__(self, whatsapp_number, payment_number):
                self.whatsapp_number = whatsapp_number
                self.payment_number = payment_number

        temp_payment = TempPayment(whatsapp_number, whatsapp_number)  # Use whatsapp_number as payment_number for simplicity
        message = payment_processor._format_confirmation_message(temp_payment, transaction, token)

        return whatsapp_service.send_text_message(whatsapp_number, message)

    except Exception as e:
        logger.error(f"Error in send_payment_confirmation: {str(e)}")
        return False