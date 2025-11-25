import logging
import os
from typing import Dict, List, Optional
from django.utils import timezone

from core.models import Booking, Property, AccommodationProvider, ConversationState
from .handlers import provider_handlers

logger = logging.getLogger(__name__)


class ProviderWorkflow:
    """Provider workflow manager"""

    def __init__(self):
        self.handlers = provider_handlers

    def handle_provider_response(self, provider_phone: str, message: str) -> Dict:
        """Handle responses from accommodation providers"""
        return self.handlers.handle_provider_response(provider_phone, message)

    def send_booking_to_provider(self, booking: Booking) -> Dict:
        """Send booking request to provider"""
        return self.handlers.send_booking_message_to_provider(booking)

    def process_student_response_to_info_request(self, cell_number: str, message: str) -> Dict:
        """Process student's response to provider's information request"""
        try:
            # Find the booking with info request
            booking = Booking.objects.filter(
                cell_number=cell_number,
                status='info_requested'
            ).order_by('-created_at').first()

            if not booking:
                return {
                    'success': False,
                    'message': 'No pending information request found.'
                }

            # Forward response to provider
            provider_message = f""" *Student's Response to your questions*

 Booking number: {booking.booking_number}
 Student: {cell_number}

 *Response:*
{message}

Please review and reply with:
• _YES/CONFIRMED to accept_
• _NO/REJECT to decline_
• _Ask additional questions if needed_"""

            content_sid = os.getenv('TWILIO_CONTENT_TEMPLATE_SID_PROVIDER_INFO_RESPONSE')
            if not content_sid:
                logger.error("Provider info response template SID not configured")
                return {
                    'success': False,
                    'message': 'Template configuration missing.'
                }

            # Get student name from conversation state
            conversation = ConversationState.objects.filter(
                cell_number=booking.cell_number,
                is_active=True
            ).first()
            student_name = conversation.context_data.get('student_name', booking.cell_number) if conversation else booking.cell_number

            content_variables = {
                "1": booking.property.name,  # Property name
                "2": booking.booking_number,  # Booking reference
                "3": student_name,  # Student name
                "4": booking.cell_number,  # Student contact
                "5": message  # Student's response
            }

            success = self.handlers.whatsapp_service.send_template_message(
                booking.property.provider.phone_number,
                content_sid,
                content_variables
            )

            if success:
                # Update booking status
                booking.additional_info_requested['student_response'] = message
                booking.additional_info_requested['responded_at'] = timezone.now().isoformat()
                booking.save()

                return {
                    'success': True,
                    'message': 'Your response has been forwarded to the provider. Waiting for their decision.',
                    'booking_number': booking.booking_number
                }
            else:
                return {
                    'success': False,
                    'message': 'failed sending response to provider. Please try again.'
                }

        except Exception as e:
            logger.error(f"Error processing student response to info request: {str(e)}")
            return {
                'success': False,
                'message': 'failed processing your response. Please try again.'
            }

    def handle_provider_message(self, from_number: str, message: str) -> Dict:
        """Handle incoming WhatsApp messages from providers"""
        try:
            message = message.strip()
            logger.info(f"Handling provider message from {from_number}: {message}")

            if message.upper().startswith('USD PAY ') or message.upper().startswith('ZWG PAY '):
                # Payment initiation message
                return {
                    'success': True,
                    'message': 'Starting payment process...'
                }
            
            # Check if this is a provider response to a booking
            provider = AccommodationProvider.objects.filter(phone_number=from_number).first()
            if not provider:
                return {
                    'success': False,
                    'message': 'Unknown provider number'
                }
            
            return self.handle_provider_response(from_number, message)

        except Exception as e:
            logger.error(f"Error handling provider message: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing message'
            }

# Global instance
provider_workflow = ProviderWorkflow()