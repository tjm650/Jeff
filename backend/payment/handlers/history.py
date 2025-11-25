"""
Payment history and utility handlers

This module handles payment history operations including:
- Student payment history retrieval
- Payment instructions sending
- History formatting and utilities
"""

import logging
from typing import List, Dict
from core.models import Property, Transaction

logger = logging.getLogger(__name__)


class PaymentHistoryHandler:
    """Payment history and utility functionality"""

    def get_student_payment_history(self, cell_number: str) -> List[Dict]:
        """Get payment history for a user"""
        try:
            transactions = Transaction.objects.filter(cell_number=cell_number)

            history = []
            for transaction in transactions:
                history.append({
                    'transaction_number': transaction.transaction_number,
                    'amount': float(transaction.amount),
                    'payment_method': transaction.payment_method,
                    'status': transaction.status,
                    'created_at': transaction.created_at.isoformat(),
                    'token_number': transaction.token.token_number if hasattr(transaction, 'token') and transaction.token else None,
                    'remaining_uses': transaction.token.remaining_uses() if hasattr(transaction, 'token') and transaction.token else 0
                })

            return history

        except Exception as e:
            logger.error(f"Payment history error: {str(e)}")
            return []

    def send_payment_instructions(self, student_phone: str) -> Dict:
        """
        Send initial payment instructions to user

        Args:
            student_phone (str): Student's phone number

        Returns:
            Dict: Response with instructions sent status
        """
        try:
            from whatsapp.utils.whatsapp_service import whatsapp_service

            # Send comprehensive payment instructions
            instructions_sent = whatsapp_service.send_payment_instructions(student_phone)

            if instructions_sent:
                return {
                    'success': True,
                    'message': 'Payment instructions sent successfully via WhatsApp.'
                }
            else:
                return {
                    'success': False,
                    'message': 'failed  to send payment instructions. Please check WhatsApp configuration.'
                }

        except Exception as e:
            logger.error(f"Error sending payment instructions: {str(e)}")
            return {
                'success': False,
                'message': 'failed sending payment instructions. Please try again.'
            }


# Global instance
history_handler = PaymentHistoryHandler()