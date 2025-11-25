"""
Payment gateway integration handlers

This module handles payment gateway integration including:
- Paynow payment initiation
- Payment status checking
- Webhook processing
- Gateway communication
"""

import logging
from typing import Dict
import os


logger = logging.getLogger(__name__)


class PaymentGatewayHandler:
    """Payment gateway integration functionality"""

    def __init__(self):
        """Initialize payment gateway handler"""
    # EcoCash config removed

        # New Paynow configuration
        self.paynow_integration_id = os.getenv('PAYNOW_INTEGRATION_ID')
        self.paynow_integration_key = os.getenv('PAYNOW_INTEGRATION_KEY')
        self.paynow_return_url = os.getenv('PAYNOW_RETURN_URL')
        self.paynow_result_url = os.getenv('PAYNOW_RESULT_URL')

        self.token_price = float(os.getenv('TOKEN_PRICE', 1.00))



    def check_payment_status(self, reference: str) -> Dict:
        """
        Check the status of a payment

        Args:
            reference (str): Payment reference number

        Returns:
            Dict: Payment status information
        """
        from ..utils.paynow_service import paynow_service

        try:
            return paynow_service.check_payment_status(reference)
        except Exception as e:
            logger.error(f"Payment status check error: {str(e)}")
            return {
                'success': False,
                'message': 'failed checking payment status. Please try again.'
            }

    def handle_payment_webhook(self, webhook_data: Dict) -> Dict:
        """
        Handle payment webhook from Paynow

        Args:
            webhook_data (dict): Webhook data from payment gateway

        Returns:
            Dict: Webhook processing result
        """
        from ..utils.paynow_service import paynow_service

        try:
            return paynow_service.process_webhook(webhook_data)
        except Exception as e:
            logger.error(f"Payment webhook processing error: {str(e)}")
            return {
                'success': False,
                'message': 'failed processing payment webhook.'
            }


# Global instance
gateway_handler = PaymentGatewayHandler()