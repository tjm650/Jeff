"""
Core payment processing handlers

This module handles the main payment processing logic including:
- Transaction creation and management
- Token generation and validation
- Payment completion workflows
- Subscription handling
"""

import logging
import uuid
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Optional
from django.utils import timezone
from django.db.models import F
from django.db import transaction, DatabaseError, IntegrityError
import os

from core.models import Transaction, Token

logger = logging.getLogger(__name__)


class PaymentCoreHandler:
    """Core payment processing functionality"""

    def __init__(self):
        """Initialize payment core handler"""
        # Legacy EcoCash config (keeping for backward compatibility)
        self.ecocash_integration_id = os.getenv('ECOCASH_INTEGRATION_ID')
        self.ecocash_integration_key = os.getenv('ECOCASH_INTEGRATION_KEY')
        self.ecocash_return_url = os.getenv('ECOCASH_RETURN_URL')
        self.ecocash_result_url = os.getenv('ECOCASH_RESULT_URL')

        # New Paynow configuration
        self.paynow_integration_id = os.getenv('PAYNOW_INTEGRATION_ID')
        self.paynow_integration_key = os.getenv('PAYNOW_INTEGRATION_KEY')
        self.paynow_return_url = os.getenv('PAYNOW_RETURN_URL')
        self.paynow_result_url = os.getenv('PAYNOW_RESULT_URL')

        # Twilio WhatsApp configuration
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER')

        self.token_price = float(os.getenv('TOKEN_PRICE', 1.00))

    def _create_transaction(self, transaction_details: Dict, cell_number: str) -> Transaction:
        """Create new transaction record"""
        # Create transaction for direct payment processing
        transaction = Transaction.objects.create(
            cell_number=cell_number,
            transaction_number=transaction_details['transaction_number'],
            amount=transaction_details['amount'],
            payment_method=transaction_details['payment_method'],
            status='verified',
            pop_verified=True,
            verified_at=timezone.now()
        )

        logger.info(f"Created transaction: {transaction.transaction_number}")
        return transaction

    def _generate_token(self, transaction: Transaction) -> Token:
        """Generate token for successful real-time transaction"""
        # Generate unique token number with timestamp for real-time payment
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        # Generate 2 random uppercase letters for enhanced security
        random_prefix = ''.join(random.choices(string.ascii_uppercase, k=2))
        token_number = f"{random_prefix}-{transaction.id:04d}-{timestamp}"

        # Create token with enhanced details for real-time payment
        expires_at = timezone.now() + timedelta(days=30)

        token = Token.objects.create(
            cell_number=transaction.cell_number,
            token_number=token_number,
            total_uses=2,
            used_count=0,
            is_active=True,
            purchased_at=timezone.now(),
            expires_at=expires_at,
            transaction=transaction
        )

        # Log token generation with more details
        logger.info(f"Generated real-time token: {token.token_number} for transaction: {transaction.transaction_number}")
        return token

    def _get_valid_token(self, student_phone: str) -> Optional[Token]:
        """Get valid token for user if exists"""
        from .token import token_handler
        return token_handler.get_valid_token(student_phone)

    def _validate_pin(self, pin: str) -> bool:
        """Validate user's PIN (mock implementation)"""
        # In real implementation, this would validate PIN with payment gateway
        # For now, accept any 4-digit PIN
        import re
        return bool(re.match(r'^\d{4}$', pin))

    def _process_payment_gateway(self, student_phone: str, pin: str, reference: str) -> Dict:
        """Process payment through Paynow gateway"""
        from ..utils.paynow_service import paynow_service

        try:
            # Check payment status using Paynow
            status_result = paynow_service.check_payment_status(reference)

            if status_result['success']:
                if status_result['paid']:
                    return {
                        'success': True,
                        'transaction_id': reference,
                        'amount': status_result.get('amount', self.token_price),
                        'status': 'completed'
                    }
                else:
                    return {
                        'success': False,
                        'message': f'Payment not completed yet. Current status: {status_result.get("status", "unknown")}'
                    }
            else:
                return {
                    'success': False,
                    'message': status_result.get('message', 'Unable to verify payment status')
                }

        except Exception as e:
            logger.error(f"Payment gateway error: {str(e)}")
            return {
                'success': False,
                'message': 'Payment processing failed. Please try again.'
            }

    def _send_payment_confirmation(self, student_phone: str, transaction: Transaction, token: Token) -> str:
        """Send payment confirmation with token details via WhatsApp"""
        try:
            from  whatsapp.utils.whatsapp_service import whatsapp_service 

            # Generate confirmation details
            confirmation_details = f""" *Payment Confirmed & Token Generated*

 *Token Number:* {token.token_number[:3]}...
 *Amount:* ${transaction.amount}
 *Expires:* {token.expires_at.strftime('%Y-%m-%d')}
 *Uses:* {token.total_uses} searches

Your token is now active

You can start searching for accommodation right away.

 *Need help?* Just describe what you're looking for"""

            # Send via WhatsApp
            if whatsapp_service.send_text_message(student_phone, confirmation_details):
                logger.info(f"Payment confirmation sent to {student_phone} via WhatsApp")
                return "Payment confirmation and token details sent to your WhatsApp."
            else:
                logger.error(f"Failed to send confirmation via WhatsApp to {student_phone}")
                return "Payment confirmed but WhatsApp sending failed."

        except Exception as e:
            logger.error(f"Payment confirmation sending error: {str(e)}")
            return "Payment confirmed but confirmation sending failed."

    def _handle_duplicate_transaction(self, existing_transaction: Transaction, student_phone: str) -> Dict:
        """Handle duplicate transaction submission"""
        # Find existing token for this transaction
        existing_token = Token.objects.filter(transaction=existing_transaction).first()

        if existing_token:
            return {
                'success': True,
                'transaction': existing_transaction,
                'token': existing_token,
                'receipt_url': f"static/receipts/receipt_{existing_transaction.transaction_number}.pdf",
                'message': f'⚠️ Duplicate payment detected\n\nYour existing token: {existing_token.token_number[:3]}...\nRemaining uses: {existing_token.remaining_uses()}\n\nThis token is still valid for accommodation searches.'
            }
        else:
            return {
                'success': False,
                'message': 'Duplicate transaction found but no token generated. Please contact support.'
            }

    def complete_transaction(self, student_phone: str, pin: str, reference: str) -> Dict:
        """
        Complete the transaction after user enters PIN with proper error handling and rollbacks

        Args:
            student_phone (str): Student's phone number
            pin (str): User's PIN for payment
            reference (str): Payment reference number

        Returns:
            Dict: Transaction completion result
        """
        logger.info(f"Starting transaction completion for {student_phone} with reference {reference}")

        try:
            # Verify PIN (in real implementation, this would validate with payment gateway)
            logger.debug(f"Validating PIN for {student_phone}")
            if not self._validate_pin(pin):
                logger.warning(f"Invalid PIN provided for {student_phone}")
                return {
                    'success': False,
                    'message': ' Invalid PIN. Please try again.'
                }

            # Process the payment through payment gateway
            logger.debug(f"Processing payment gateway for {student_phone}")
            payment_result = self._process_payment_gateway(student_phone, pin, reference)

            if not payment_result['success']:
                logger.error(f"Payment gateway failed for {student_phone}: {payment_result.get('message')}")
                return payment_result

            # Use database transaction for atomicity
            with transaction.atomic():
                try:
                    logger.debug(f"Creating transaction record for {student_phone}")
                    # Create transaction record
                    transaction_details = {
                        'transaction_number': reference,
                        'amount': self.token_price,
                        'payment_method': 'ecocash',
                        'date': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                    }

                    transaction_obj = self._create_transaction(transaction_details, student_phone)

                    # Generate token
                    logger.debug(f"Generating token for transaction {reference}")
                    token = self._generate_token(transaction_obj)

                    # Generate receipt
                    logger.debug(f"Generating receipt for transaction {reference}")
                    receipt_url = self._generate_receipt(transaction_obj, token)

                    # Commit the transaction before external operations
                    transaction_obj.save()
                    token.save()

                    logger.info(f"Transaction {reference} committed successfully for {student_phone}")

                except (DatabaseError, IntegrityError) as db_error:
                    logger.error(f"Database error during transaction {reference}: {str(db_error)}")
                    raise  # This will trigger rollback

                except Exception as trans_error:
                    logger.error(f"Transaction creation error for {reference}: {str(trans_error)}")
                    raise  # This will trigger rollback

            # External operations (WhatsApp) - these happen after successful DB commit
            # Send payment confirmation via WhatsApp
            logger.debug(f"Sending payment confirmation to {student_phone}")
            confirmation_message = self._send_payment_confirmation(student_phone, transaction_obj, token)

            # Send WhatsApp confirmation with token details
            from  whatsapp.utils.whatsapp_service import whatsapp_service 
            logger.debug(f"Sending WhatsApp confirmation to {student_phone}")
            whatsapp_sent = whatsapp_service.send_payment_confirmation(
                student_phone,
                {
                    'transaction': transaction_obj,
                    'token': token
                }
            )

            # Send PDF receipt via WhatsApp if available
            if receipt_url:
                logger.debug(f"Sending PDF receipt to {student_phone}")
                whatsapp_service.send_receipt_via_whatsapp(
                    student_phone,
                    receipt_url,
                    {'transaction': transaction_obj, 'token': token}
                )

            logger.info(f"Transaction {reference} completed successfully for {student_phone}")

            return {
                'success': True,
                'transaction': transaction_obj,
                'token': token,
                'receipt_url': receipt_url,
                'message': f' Payment completed successfully\n\nToken: {token.token_number[:3]}...\n\n{confirmation_message}\n\nWhatsApp notifications sent.',
                'status': 'completed',
                'whatsapp_sent': whatsapp_sent
            }

        except (DatabaseError, IntegrityError) as db_error:
            logger.error(f"Database transaction failed for {student_phone}: {str(db_error)}")
            return {
                'success': False,
                'message': ' Database error occurred. Please try again or contact support.',
                'error_type': 'database_error'
            }

        except Exception as e:
            logger.error(f"Transaction completion error for {student_phone}: {str(e)}", exc_info=True)

            # Send error notification via WhatsApp
            try:
                from  whatsapp.utils.whatsapp_service import whatsapp_service 
                whatsapp_service.send_error_message(
                    student_phone,
                    "We encountered an error completing your transaction. Please try again or contact support if the issue persists."
                )
                logger.debug(f"Error notification sent to {student_phone}")
            except Exception as whatsapp_error:
                logger.error(f"Failed to send WhatsApp error notification: {str(whatsapp_error)}")

            return {
                'success': False,
                'message': 'failed completing transaction. Please try again or contact support.',
                'error_type': 'system_error'
            }

    def handle_subscribe_button(self, student_phone: str) -> Dict:
        """
        Handle user pressing the Subscribe button

        Args:
            student_phone (str): Student's phone number

        Returns:
            Dict: Response with payment initiation details
        """
        try:
            # Check if user already has a valid token
            existing_token = self._get_valid_token(student_phone)
            if existing_token:
                # Send instructions on how to use existing token
                instructions_message = f""" *Active Token Found - JEFF Platform*

 *Your Token:* {existing_token.token_number[:3]}...
 *Remaining Uses:* {existing_token.remaining_uses()}
 *Expires:* {existing_token.expires_at.strftime('%Y-%m-%d')}

 *Ready to search?* Use your token to find accommodation now

 *Need another token?* Send 'USD PAY your_number' when you're ready for more searches.

Happy house hunting """

                from  whatsapp.utils.whatsapp_service import whatsapp_service 
                whatsapp_service.send_text_message(student_phone, instructions_message)

                return {
                    'success': True,
                    'message': f' You already have an active token: {existing_token.token_number[:3]}...\n\nRemaining uses: {existing_token.remaining_uses()}\n\nYou can proceed with your accommodation search.',
                    'token': existing_token,
                    'status': 'existing_token'
                }

            # Initiate payment process
            from .gateway import gateway_handler
            payment_result = gateway_handler.initiate_ecocash_payment(student_phone, self.token_price)

            if payment_result['success']:
                return {
                    'success': True,
                    'message': f'💳 Subscription initiated for ${self.token_price}\n\n{payment_result["message"]}\n\nPlease complete the payment by entering your PIN.',
                    'payment_url': payment_result.get('payment_url'),
                    'reference': payment_result.get('reference'),
                    'status': 'payment_initiated'
                }
            else:
                return payment_result

        except Exception as e:
            logger.error(f"Subscribe button error: {str(e)}")

            # Send error notification via WhatsApp if possible
            try:
                from  whatsapp.utils.whatsapp_service import whatsapp_service 
                whatsapp_service.send_error_message(
                    student_phone,
                    "We encountered an error processing your subscription request. Please try again or contact support."
                )
            except Exception as whatsapp_error:
                logger.error(f"Failed to send WhatsApp error notification: {str(whatsapp_error)}")

            return {
                'success': False,
                'message': 'failed processing subscription request. Please try again.'
            }

    def _generate_receipt(self, transaction: Transaction, token: Token) -> str:
        """Generate PDF receipt for transaction"""
        from .receipt import receipt_handler
        return receipt_handler.generate_receipt(transaction, token)


# Global instance
payment_core = PaymentCoreHandler()