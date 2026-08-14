import logging
import os
from typing import Dict
from django.utils import timezone

from core.models import Booking, AccommodationProvider, ConversationState
from .handlers import provider_handlers

logger = logging.getLogger(__name__)


class ProviderWorkflow:
    """Provider workflow manager."""

    def __init__(self):
        self.handlers = provider_handlers

    def handle_provider_response(self, provider_phone: str, message: str) -> Dict:
        return self.handlers.handle_provider_response(provider_phone, message)

    def send_booking_to_provider(self, booking: Booking) -> Dict:
        return self.handlers.send_booking_message_to_provider(booking)

    def process_student_response_to_info_request(self, cell_number: str, message: str) -> Dict:
        """Forward a student's answer to a provider using a Meta template."""
        try:
            booking = Booking.objects.filter(
                cell_number=cell_number,
                status="info_requested",
            ).order_by("-created_at").first()

            if not booking:
                return {"success": False, "message": "No pending information request found."}

            template_name = os.getenv("META_TEMPLATE_PROVIDER_INFO_RESPONSE")
            if not template_name:
                logger.error("META_TEMPLATE_PROVIDER_INFO_RESPONSE is not configured")
                return {"success": False, "message": "WhatsApp template configuration missing."}

            conversation = ConversationState.objects.filter(
                cell_number=booking.cell_number,
                is_active=True,
            ).first()
            student_name = (
                conversation.context_data.get("student_name", booking.cell_number)
                if conversation else booking.cell_number
            )

            template_variables = {
                "1": booking.property.name,
                "2": booking.booking_number,
                "3": student_name,
                "4": booking.cell_number,
                "5": message,
            }

            success = self.handlers.whatsapp_service.send_template_message(
                booking.property.provider.phone_number,
                template_name,
                template_variables,
            )

            if not success:
                return {
                    "success": False,
                    "message": "Failed sending response to provider. Please try again.",
                }

            booking.additional_info_requested["student_response"] = message
            booking.additional_info_requested["responded_at"] = timezone.now().isoformat()
            booking.save()

            return {
                "success": True,
                "message": "Your response has been forwarded to the provider. Waiting for their decision.",
                "booking_number": booking.booking_number,
            }
        except Exception as exc:
            logger.error("Error processing student response to info request: %s", exc, exc_info=True)
            return {
                "success": False,
                "message": "Failed processing your response. Please try again.",
            }

    def handle_provider_message(self, from_number: str, message: str) -> Dict:
        try:
            message = message.strip()
            logger.info("Handling provider message from %s", from_number)

            if message.upper().startswith("USD PAY ") or message.upper().startswith("ZWG PAY "):
                return {"success": True, "message": "Starting payment process..."}

            provider = AccommodationProvider.objects.filter(phone_number=from_number).first()
            if not provider:
                return {"success": False, "message": "Unknown provider number"}

            return self.handle_provider_response(from_number, message)
        except Exception as exc:
            logger.error("Error handling provider message: %s", exc, exc_info=True)
            return {"success": False, "message": "Error processing message"}


provider_workflow = ProviderWorkflow()
