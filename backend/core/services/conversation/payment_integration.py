"""Free-use compatibility handlers.

Payment processing has been intentionally removed from Jeff for now. The
conversation workflow keeps this small compatibility object so old imports and
message classifications do not break while users can search and book for free.
"""

import logging

logger = logging.getLogger(__name__)


class PaymentIntegrationHandler:
    """Compatibility handler with payment functionality disabled."""

    def handle_payment_request(self, conversation, message: str) -> str:
        return (
            "Jeff is currently free to use. No payment is required.\n\n"
            "Send your accommodation requirements (location, budget, number of "
            "people, amenities, etc.) and I'll search for available properties."
        )

    def handle_payment_confirmation_step(self, conversation, message: str) -> str:
        # Legacy conversations that happen to be in this state are safely
        # returned to the normal free accommodation workflow.
        try:
            conversation.current_step = "inquiry"
            conversation.context_data = {}
            conversation.save()
        except Exception as exc:
            logger.warning("Could not reset legacy payment state: %s", exc)
        return (
            "Payments are disabled and no payment is required.\n\n"
            "Please send your accommodation requirements to start a free search."
        )

    def handle_payment_webhook(self, payment_data):
        return {
            "success": False,
            "disabled": True,
            "message": "Payment processing is disabled while Jeff is free to use.",
        }


payment_integration_handler = PaymentIntegrationHandler()
