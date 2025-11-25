"""
Payment cleanup and timeout handlers

This module handles payment cleanup operations including:
- Transaction timeout handling
- Expired transaction cleanup
- Failed transaction management
- Notification sending for cleanup operations
"""

import logging
from datetime import timedelta
from typing import Dict
from django.utils import timezone

from core.models import Transaction

logger = logging.getLogger(__name__)


class PaymentCleanupHandler:
    """Payment cleanup and timeout functionality"""

    def handle_transaction_timeout(self, reference: str) -> Dict:
        """
        Handle transaction timeout after 1 minute without response

        Args:
            reference (str): Payment reference number

        Returns:
            Dict: Timeout handling result
        """
        logger.warning(f"Handling transaction timeout for reference: {reference}")

        try:
            # Find the pending transaction
            transaction_obj = Transaction.objects.filter(
                transaction_number=reference,
                status='pending'
            ).first()

            if not transaction_obj:
                logger.info(f"No pending transaction found for reference {reference}")
                return {
                    'success': False,
                    'message': 'No pending transaction found for this reference.'
                }

            # Check if transaction is actually old enough to timeout (1 minute)
            time_diff = timezone.now() - transaction_obj.created_at
            if time_diff.total_seconds() < 60:
                logger.info(f"Transaction {reference} is not old enough for timeout (only {time_diff.total_seconds()} seconds)")
                return {
                    'success': False,
                    'message': 'Transaction is not old enough for timeout handling.'
                }

            # Mark transaction as failed
            transaction_obj.status = 'failed '
            transaction_obj.save()

            # Notify user about timeout
            try:
                from  whatsapp.utils.whatsapp_service import whatsapp_service 
                timeout_message = f"""*Payment Timeout - Jeff Platform*

Your payment session for reference {reference} has timed out after 1 minute.

 *What to do next:*
• Send 'USD PAY your_number' to start a new payment
• Make sure to complete the payment within 1 minute
• Check your mobile network connection

Need help? Contact our support team."""

                whatsapp_service.send_text_message(transaction_obj.cell_number, timeout_message)
                logger.info(f"Timeout notification sent to {transaction_obj.cell_number} for reference {reference}")

            except Exception as whatsapp_error:
                logger.error(f"Failed to send timeout notification: {str(whatsapp_error)}")

            logger.warning(f"Transaction {reference} marked as failed due to timeout")
            return {
                'success': True,
                'message': f'Transaction {reference} has been marked as failed due to timeout.',
                'transaction': transaction_obj,
                'status': 'timeout'
            }

        except Exception as e:
            logger.error(f"Error handling transaction timeout for {reference}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': 'failed handling transaction timeout. Please try again.'
            }

    def cleanup_expired_transactions(self) -> Dict:
        """
        Clean up expired transactions and send notifications

        Returns:
            Dict: Cleanup results
        """
        logger.info("Starting cleanup of expired transactions")

        try:
            # Find transactions older than 1 minute that are still pending
            expired_transactions = Transaction.objects.filter(
                status='pending',
                created_at__lt=timezone.now() - timedelta(minutes=1)
            )

            cleaned_count = 0
            failed_notifications = 0

            for transaction_obj in expired_transactions:
                try:
                    # Mark as failed
                    transaction_obj.status = 'failed '
                    transaction_obj.save()

                    # Send timeout notification
                    try:
                        from  whatsapp.utils.whatsapp_service import whatsapp_service 
                        timeout_message = f"""*Payment Session Expired*
Your payment session has expired after 1 minute of inactivity.
Reference: {transaction_obj.transaction_number}"""

                        whatsapp_service.send_text_message(transaction_obj.cell_number, timeout_message)
                        logger.debug(f"Timeout notification sent for transaction {transaction_obj.transaction_number}")

                    except Exception as notif_error:
                        logger.error(f"Failed to send timeout notification for {transaction_obj.transaction_number}: {str(notif_error)}")
                        failed_notifications += 1

                    cleaned_count += 1
                    logger.info(f"Cleaned up expired transaction: {transaction_obj.transaction_number}")

                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up transaction {transaction_obj.transaction_number}: {str(cleanup_error)}")

            logger.info(f"Transaction cleanup completed. Cleaned: {cleaned_count}, Failed notifications: {failed_notifications}")

            return {
                'success': True,
                'cleaned_count': cleaned_count,
                'failed _notifications': failed_notifications,
                'message': f'Cleaned up {cleaned_count} expired transactions.'
            }

        except Exception as e:
            logger.error(f"Error during transaction cleanup: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': 'failed during transaction cleanup.'
            }


# Global instance
cleanup_handler = PaymentCleanupHandler()