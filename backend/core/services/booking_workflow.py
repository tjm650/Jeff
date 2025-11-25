"""
Booking Workflow Service for Jeff Platform

This service handles the complete booking process using modular components
in the booking/ subfolder for better organization and maintainability.

Key Features:
- Modular architecture with separate handlers and notifications
- Provider response handling (confirmation/rejection/info requests)
- Booking confirmation and property availability updates
- Token management and refunds
- Student notifications
- Conversation cleanup
"""

import logging
from typing import Dict, List, Optional

from core.models import Booking, Property, ConversationState, Token, AccommodationProvider
from whatsapp.utils.whatsapp_service import whatsapp_service

# Import specialized booking components from providers
from providers.services.handlers import provider_handlers
from .booking.handlers import booking_handlers
from .booking.notifications import booking_notifications

logger = logging.getLogger(__name__)


class BookingWorkflow:
    """Complete booking workflow manager using modular components"""

    def __init__(self):
        self.whatsapp_service = whatsapp_service
        # Initialize specialized components
        self.handlers = booking_handlers
        self.notifications = booking_notifications

    def handle_provider_response(self, provider_phone: str, message: str) -> Dict:
        """
        Handle responses from accommodation providers with enhanced error handling

        Args:
            provider_phone: Provider's phone number
            message: Provider's response message

        Returns:
            Dict with processing result
        """
        return self.handlers.handle_provider_response(provider_phone, message)


    def process_student_response_to_info_request(self, cell_number: str, message: str) -> Dict:
        """Process student's response to provider's information request"""
        return self.handlers.process_student_response_to_info_request(cell_number, message)

    def cleanup_completed_bookings(self):
        """Clean up old completed bookings and update property availability"""
        return self.handlers.cleanup_completed_bookings()

    def update_property_availability(self, provider_phone: str, availability_count: int) -> Dict:
        """Update property availability based on provider response"""
        return self.handlers.update_property_availability(provider_phone, availability_count)