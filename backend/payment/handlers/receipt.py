"""
Payment receipt and notification handlers

This module handles receipt generation and related notifications including:
- PDF receipt generation
- Receipt data formatting
- Receipt delivery via WhatsApp
"""

import logging
from typing import Dict

from core.models import Transaction, Token

logger = logging.getLogger(__name__)


class PaymentReceiptHandler:
    """Payment receipt generation and notification functionality"""

    def generate_receipt(self, transaction: Transaction, token: Token) -> str:
        """Prepare receipt data for sending as text (no PDF). Returns a dict."""
        try:
            receipt_data = {
                'transaction_id': transaction.transaction_number,
                'token_number': token.token_number,
                'amount_usd': float(transaction.amount),
                'payment_method': transaction.payment_method,
                'date': transaction.created_at.strftime('%Y-%m-%d %H:%M:%S') if transaction.created_at else None,
                'student_phone': transaction.cell_number,
                'expires_at': token.expires_at.strftime('%Y-%m-%d') if token.expires_at else None,
                'total_uses': token.total_uses,
                'token_info': {
                    'token_number': token.token_number,
                    'total_uses': token.total_uses,
                    'used_count': token.used_count
                }
            }

            return receipt_data

        except Exception as e:
            logger.error(f"Receipt data preparation error for transaction {transaction.transaction_number}: {str(e)}", exc_info=True)
            return None

    def send_receipt_via_whatsapp(self, student_phone: str, receipt_url: str, context: Dict) -> bool:
        """Send receipt details as a WhatsApp text message (PDF flow removed)"""
        try:
            from whatsapp.utils.whatsapp_service import whatsapp_service

            # context may include 'transaction' key
            transaction = context.get('transaction')
            if transaction:
                # Prepare receipt dict
                receipt = self.generate_receipt(transaction, context.get('token')) if context.get('token') else {
                    'transaction_id': transaction.transaction_number,
                    'amount_usd': float(getattr(transaction, 'amount', 0)),
                    'date': getattr(transaction, 'created_at', None).strftime('%Y-%m-%d %H:%M:%S') if getattr(transaction, 'created_at', None) else None,
                    'payment_method': getattr(transaction, 'payment_method', 'ecocash')
                }

                return whatsapp_service.send_payment_confirmation(student_phone, receipt)
            else:
                logger.warning(f"No transaction provided for receipt to {student_phone}")
                return False

        except Exception as e:
            logger.error(f"Error sending receipt via WhatsApp to {student_phone}: {str(e)}")
            return False


# Global instance
receipt_handler = PaymentReceiptHandler()