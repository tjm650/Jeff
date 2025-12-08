"""
Payment integration handlers for conversation workflow

This module handles payment integration within conversation workflow including:
- Payment request handling
- Token creation after payment
- Payment webhook processing
- Payment confirmation steps
"""

import logging
import random
import string
from typing import Dict
from django.utils import timezone
from datetime import timedelta
from .ux_formatter import ux_formatter
from .fail_safe import fail_safe_handler

logger = logging.getLogger(__name__)


class PaymentIntegrationHandler:
    """Payment integration functionality for conversation workflow"""

    def handle_payment_request(self, conversation, message: str) -> str:
        """Handle payment request
        """
        try:
            import re
            from payment.models import Payment
            from payment.services import PaynowService

            cell_number = conversation.cell_number

            # Log that this payment request came from classification
            logger.info(f"Processing classified payment request for {cell_number}: {message}")

            # Extract payment number and currency from message
            pattern = r'(USD|ZWL)\s+PAY\s+([0-9]+)'
            match = re.search(pattern, message, re.IGNORECASE)

            if not match:
                return ux_formatter.format_error_message('invalid_input')

            payment_number = match.group(2).strip()  # Fix: group 2 is the payment number
            currency = match.group(1).upper()  # USD or ZWL

            # Validate payment number format (basic validation)
            if len(payment_number) < 10:
                return ux_formatter.format_error_message('invalid_input')

            # Check for recent pending payment
            recent_pending = Payment.objects.filter(
                whatsapp_number=cell_number,
                status='pending'
            ).order_by('-created_at').first()

            if recent_pending:
                # Use fail-safe for payment delay
                return fail_safe_handler.handle_payment_delay(recent_pending)

            # Create payment record
            payment = Payment.objects.create(
                whatsapp_number=cell_number,
                payment_number=payment_number,
                amount=PaynowService.AGENT_AMOUNT,
                transaction_id=f"TXN-{Payment.objects.count() + 1:06d}"
            )

            # Initiate PayNow payment
            paynow_service = PaynowService()
            result = paynow_service.create_agent_payment(
                whatsapp_number=cell_number,
                payment_number=payment_number
            )

            if result['success']:
                # Update payment with PayNow details
                payment.poll_url = result['poll_url']
                payment.paynow_reference = result.get('redirect_url', '')
                payment.reference = result.get('reference', '')
                payment.save()

                # Update conversation state
                conversation.context_data['pending_payment'] = {
                    'transaction_id': payment.transaction_id,
                    'payment_number': payment_number,
                    'poll_url': result['poll_url']
                }
                conversation.current_step = 'payment_confirmation'
                conversation.save()

                # Use UX formatter for payment initiation message
                message = f"*Payment Initiated*\n\n"
                message += f"Transaction: {payment.transaction_id}\n"
                message += f"Amount: ${payment.amount}\n"
                message += f"Payment Number: {payment_number}\n\n"
                message += f"{payment_number[:6]}... will receive a Paynow prompt on your phone.\n\n"
                message += "Approve the payment. You'll receive confirmation once payment is complete."
                
                return message

            else:
                # Mark payment as failed
                payment.status = 'failed '
                payment.save()

                return ux_formatter.format_error_message('payment_failed')

        except Exception as e:
            logger.error(f"Error handling payment request: {str(e)}")
            return fail_safe_handler.handle_null_response('payment_verification')

    def handle_payment_confirmation_step(self, conversation, message: str) -> str:
        """Handle payment confirmation step"""
        try:
            from payment.models import Payment

            cell_number = conversation.cell_number
            pending_payment = conversation.context_data.get('pending_payment', {})

            if not pending_payment:
                return self._reset_to_inquiry(conversation)

            transaction_id = pending_payment.get('transaction_id')

            # Check payment status
            payment = Payment.objects.filter(transaction_id=transaction_id).first()

            if not payment:
                return "Payment record not found. Please try again."

            if payment.status == 'paid':
                # Payment successful, create token
                return self._create_token_after_payment(conversation, payment)
            elif payment.status == 'failed ':
                return ux_formatter.format_error_message('payment_failed')
            else:
                # Still pending - use fail-safe for delay
                return fail_safe_handler.handle_payment_delay(payment)

        except Exception as e:
            logger.error(f"Error in payment confirmation step: {str(e)}")
            return fail_safe_handler.handle_null_response('payment_verification')

    def _create_token_after_payment(self, conversation, payment) -> str:
        """Create token after successful payment"""
        try:
            from payment.models import Payment
            from core.models import Transaction, Token

            cell_number = conversation.cell_number

            # Generate unique token number
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            random_prefix = ''.join(random.choices(string.ascii_uppercase, k=2))
            token_number = f"{random_prefix}-{payment.id:04d}-{timestamp}"

            # Create transaction record for existing system
            transaction = Transaction.objects.create(
                cell_number=cell_number,
                transaction_number=payment.transaction_id,
                amount=payment.amount,
                payment_method='paynow',
                status='verified',
                pop_verified=True,
                verified_at=timezone.now()
            )

            # Create token
            expires_at = timezone.now() + timedelta(days=30)
            token = Token.objects.create(
                cell_number=cell_number,
                token_number=token_number,
                total_uses=2,
                used_count=0,
                is_active=True,
                purchased_at=timezone.now(),
                expires_at=expires_at,
                transaction=transaction
            )

            # Update conversation state
            conversation.context_data = conversation.context_data.get('original_requirements', {})
            conversation.current_step = 'token_check'
            conversation.save()

            return f"""*Payment Confirmed & Token Generated *

*Token Number:* {token_number[:3]}...
*Amount:* ${payment.amount}
*Expires:* {expires_at.strftime('%Y-%m-%d')}
*Validity:* {token.total_uses} searches """

        except Exception as e:
            logger.error(f"Error creating token after payment: {str(e)}")
            return "Error creating token. Please contact support."

    def handle_payment_webhook(self, payment_data: Dict) -> Dict:
        """Handle payment webhook from PayNow and update conversation workflow"""
        try:
            from payment.models import Payment

            # Extract payment information from webhook
            # Accept multiple possible key names from Paynow payloads
            reference = payment_data.get('reference') or payment_data.get('internal_reference') or ''
            paynow_reference = (
                payment_data.get('paynowreference') or payment_data.get('paynow_reference') or payment_data.get('paynowReference') or ''
            )
            status = (payment_data.get('status') or '').lower()

            # Find payment by a set of possible matching strategies (be tolerant)
            payment = None

            tried = {
                'paynow_reference': paynow_reference,
                'reference': reference,
            }

            # 1) Exact paynow_reference match
            if paynow_reference:
                payment = Payment.objects.filter(paynow_reference__iexact=paynow_reference).first()

            # 2) Fallback: paynow_reference contains
            if not payment and paynow_reference:
                payment = Payment.objects.filter(paynow_reference__icontains=paynow_reference).first()

            # 3) Exact internal reference match
            if not payment and reference:
                payment = Payment.objects.filter(reference=reference).first()

            # 4) Try matching by transaction id if provided in webhook
            if not payment:
                tx = payment_data.get('transaction') or payment_data.get('transaction_id') or payment_data.get('transactionId')
                if tx:
                    payment = Payment.objects.filter(transaction_id=tx).first()

            if not payment:
                logger.warning(f"Webhook payment lookup failed. Tried: {tried} ; transaction keys: {payment_data.get('transaction')}")
                return {
                    'success': False,
                    'message': 'Payment not found'
                }

            # Update payment status
            old_status = payment.status

            if status == 'paid':
                payment.status = 'paid'
                success = self._create_token_after_webhook_payment(payment)
            elif status == 'cancelled':
                payment.status = 'cancelled'
                success = True
            elif status in ['failed ', 'error']:
                payment.status = 'failed '
                success = True
            else:
                success = True

            payment.save()

            logger.info(f"Payment {payment.transaction_id} updated via webhook: {old_status} -> {payment.status}")

            return {
                'success': success,
                'message': f'Payment {payment.transaction_id} updated to {payment.status}',
                'transaction_id': payment.transaction_id,
                'whatsapp_number': payment.whatsapp_number,
                'status': payment.status
            }

        except Exception as e:
            logger.error(f"Error handling payment webhook: {str(e)}")
            return {
                'success': False,
                'message': f'failed processing webhook: {str(e)}'
            }

    def _create_token_after_webhook_payment(self, payment) -> bool:
        """Create token after successful webhook payment"""
        try:
            from core.models import Transaction, Token
            from whatsapp.utils.whatsapp_service import whatsapp_service

            cell_number = payment.whatsapp_number

            # Generate unique token number
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            random_prefix = ''.join(random.choices(string.ascii_uppercase, k=2))
            token_number = f"{random_prefix}-{payment.id:04d}-{timestamp}"

            # Create transaction record for existing system
            transaction = Transaction.objects.create(
                cell_number=cell_number,
                transaction_number=payment.transaction_id,
                amount=payment.amount,
                payment_method='paynow',
                status='verified',
                pop_verified=True,
                verified_at=timezone.now()
            )

            # Create token
            expires_at = timezone.now() + timedelta(days=30)
            token = Token.objects.create(
                cell_number=cell_number,
                token_number=token_number,
                total_uses=2,
                used_count=0,
                is_active=True,
                purchased_at=timezone.now(),
                expires_at=expires_at,
                transaction=transaction
            )

            # Find and reset the conversation
            try:
                from core.models import ConversationState
                conversation = ConversationState.objects.filter(
                    cell_number=cell_number,
                    is_active=True
                ).first()

                if conversation:
                    # Reset conversation
                    conversation.current_step = 'inquiry'
                    conversation.context_data = {}
                    conversation.save()
                    logger.info(f"Conversation reset for {cell_number} after payment")

                # Send confirmation and reset notification via WhatsApp
                confirmation_message = f""" *Payment Confirmed & Token Generated*

*Token Number:* {token_number[:3]}...
*Amount:* ${payment.amount}
*Expires:* {expires_at.strftime('%Y-%m-%d')}
*Validity:* {token.total_uses} searches

Your conversation has been reset. You can now start a new property search by sending your requirements. For example:
• _"I need a 2-head room with WiFi for $200"_
• _"Looking for single room near campus"_"""

                whatsapp_service.send_text_message(cell_number, confirmation_message)
                logger.info(f"Payment confirmation sent to {cell_number}")

            except Exception as whatsapp_error:
                logger.error(f"Failed to send payment confirmation: {str(whatsapp_error)}")

            logger.info(f"Token created after webhook payment: {token_number} for {cell_number}")
            return True

        except Exception as e:
            logger.error(f"Error creating token after webhook payment: {str(e)}")
            return False

    def _reset_to_inquiry(self, conversation) -> str:
        """Reset conversation to inquiry step"""
        try:
            from .utils import conversation_utils
            return conversation_utils._reset_to_inquiry(conversation)
        except Exception as e:
            logger.error(f"Error resetting to inquiry: {str(e)}")
            return "Please try again or send 'help' for assistance."


# Global instance
payment_integration_handler = PaymentIntegrationHandler()