"""
Payment Handler for Jeff Platform

This module provides a unified interface for payment processing using modular components
in the handlers/ subfolder for better organization and maintainability.

Key Features:
- Modular architecture with separate handlers for different payment aspects
- Core payment processing and transaction management
- Token management and validation
- Payment gateway integration (Paynow/EcoCash)
- Receipt generation and notifications
- Transaction cleanup and timeout handling
- Payment history and utilities
"""

import logging
from typing import Dict, List, Optional

from core.models import Transaction, Token

# Import specialized payment components
from .handlers.core import payment_core
from .handlers.token import token_handler
from .handlers.gateway import gateway_handler
from .handlers.receipt import receipt_handler
from .handlers.cleanup import cleanup_handler
from .handlers.history import history_handler

logger = logging.getLogger(__name__)


class DjangoPaymentHandler:
    """Django-compatible payment processing handler using modular components"""

    def __init__(self):
        """Initialize payment handler with modular components"""
        # Initialize specialized components
        self.core = payment_core
        self.tokens = token_handler
        self.gateway = gateway_handler
        self.receipts = receipt_handler
        self.cleanup = cleanup_handler
        self.history = history_handler




    def _create_transaction(self, transaction_details: Dict, cell_number: str) -> Transaction:
        """Create new transaction record"""
        return self.core._create_transaction(transaction_details, cell_number)

    def _generate_token(self, transaction: Transaction) -> Token:
        """Generate token for successful real-time transaction"""
        return self.core._generate_token(transaction)

    def _get_valid_token(self, student_phone: str) -> Optional[Token]:
        """Get valid token for user if exists"""
        return self.core._get_valid_token(student_phone)

    def _validate_pin(self, pin: str) -> bool:
        """Validate user's PIN (mock implementation)"""
        return self.core._validate_pin(pin)

    def _process_payment_gateway(self, student_phone: str, pin: str, reference: str) -> Dict:
        """Process payment through Paynow gateway"""
        return self.core._process_payment_gateway(student_phone, pin, reference)

    def _send_payment_confirmation(self, student_phone: str, transaction: Transaction, token: Token) -> str:
        """Send payment confirmation with token details via WhatsApp"""
        return self.core._send_payment_confirmation(student_phone, transaction, token)

    def _handle_duplicate_transaction(self, existing_transaction: Transaction, student_phone: str) -> Dict:
        """Handle duplicate transaction submission"""
        return self.core._handle_duplicate_transaction(existing_transaction, student_phone)

    def handle_subscribe_button(self, student_phone: str) -> Dict:
        """
        Handle user pressing the Subscribe button

        Args:
            student_phone (str): Student's phone number

        Returns:
            Dict: Response with payment initiation details
        """
        return self.core.handle_subscribe_button(student_phone)

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
        return self.core.complete_transaction(student_phone, pin, reference)

    def initiate_payment(self, student_phone: str, amount: float = None, payment_number: str = None) -> Dict:
        """Initiate mobile money payment using Paynow"""
        from .utils.paynow_service import paynow_service
        from .utils.whatsapp_service import whatsapp_service

        # Use payment_number if provided, otherwise use student_phone
        payment_number = payment_number or student_phone

        try:
            # Get configured prices from settings
            from django.conf import settings
            jeff_settings = getattr(settings, 'JEFF_SETTINGS', {})
            amount = amount or float(jeff_settings.get('TOKEN_PRICE_USD', 1.00))

            # Create payment using Paynow service
            payment_result = paynow_service.create_payment(
                phone_number=payment_number,
                amount=amount,
                reference=None
            )

            if payment_result.get('success'):
                # Send WhatsApp notification about payment initiation
                whatsapp_service.send_payment_initiation(
                    student_phone,
                    payment_result.get('amount_usd', amount),
                    payment_result.get('amount_zwg'),
                    payment_result.get('payment_reference'),
                    payment_number
                )

                return {
                    'success': True,
                    'payment_url': payment_result.get('poll_url'),
                    'reference': payment_result['payment_reference'],
                    'message': payment_result.get('message'),
                    'payment_method': 'paynow'
                }
            else:
                return {
                    'success': False,
                    'message': payment_result.get('message', 'Payment initiation failed')
                }

        except Exception as e:
            logger.exception(f"Paynow initiation error: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to initiate payment. Please try again.'
            }

    def get_student_payment_history(self, cell_number: str) -> List[Dict]:
        """Get payment history for a user"""
        return self.history.get_student_payment_history(cell_number)

    def check_payment_status(self, reference: str) -> Dict:
        """
        Check the status of a payment

        Args:
            reference (str): Payment reference number

        Returns:
            Dict: Payment status information
        """
        return self.gateway.check_payment_status(reference)

    def send_payment_instructions(self, student_phone: str) -> Dict:
        """
        Send initial payment instructions to user

        Args:
            student_phone (str): Student's phone number

        Returns:
            Dict: Response with instructions sent status
        """
        return self.history.send_payment_instructions(student_phone)

    def handle_payment_webhook(self, webhook_data: Dict) -> Dict:
        """
        Handle payment webhook from Paynow

        Args:
            webhook_data (dict): Webhook data from payment gateway

        Returns:
            Dict: Webhook processing result
        """
        return self.gateway.handle_payment_webhook(webhook_data)



# Global instance
payment_handler = DjangoPaymentHandler()