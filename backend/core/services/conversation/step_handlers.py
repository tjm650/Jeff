import logging
import os
import random
import re
from typing import Dict, Optional, Tuple

from django.db import models
from django.utils import timezone

from core.models import ConversationState, Booking, Property
from providers.services.workflow import provider_workflow
from whatsapp.utils.whatsapp_service import whatsapp_service
from .nlp_processor import nlp_processor_handler
from .property_search import property_search_handler

logger = logging.getLogger(__name__)


class StepHandlers:
    """Conversation steps for free accommodation search and booking."""

    def __init__(self):
        self.property_search = property_search_handler
        self.nlp_processor = nlp_processor_handler

    def _handle_inquiry_step(self, conversation: ConversationState, message: str) -> str:
        if message.lower().strip() in {'abort', 'restart', 'start over', 'cancel'}:
            return self._reset_conversation(conversation)
        requirements = self.nlp_processor.extract_requirements(message)
        if not requirements:
            return "Please provide your accommodation requirements (location, budget, number of people, etc.)."
        requirements['invert_sort'] = True
        conversation.context_data['requirements'] = requirements
        conversation.current_step = 'property_listings'
        conversation.save()
        prefix = ''
        if requirements.get('needs_period_recommendation'):
            prefix = f"{requirements.get('period_recommendation_message', '')}\n\n"
        return prefix + self.property_search.proceed_to_property_search(conversation, requirements)

    def _handle_property_listings_step(self, conversation: ConversationState, message: str) -> str:
        text = message.lower().strip()
        if text == 'show-more':
            return self._handle_show_more(conversation)
        results = conversation.context_data.get('search_results', [])
        if not results:
            return "No properties available for selection. Please search for accommodation first."
        selection = self._extract_property_selection(text, conversation)
        if selection is None:
            return "Please select a property using 'option-(number)'.\n\n" + self.property_search.show_property_listings(conversation)
        page = conversation.context_data.get('current_property_page', 0)
        index = selection - 1 + page * 5
        return self._process_property_selection(conversation, index)

    def _handle_name_collection_step(self, conversation: ConversationState, message: str) -> str:
        name = self._extract_name_from_message(message)
        if not name:
            return "Please provide your name in the format: name-(your full name)."
        booking, is_new = self._create_booking(conversation, name)
        if not booking:
            return "Failed to create booking. Please try again."
        conversation.context_data['student_name'] = name
        conversation.current_step = 'booking_request'
        conversation.save()
        if not is_new:
            return f"Booking already exists with number {booking.booking_number}. I will continue processing it."
        result = self._send_booking_to_provider(booking)
        if result.get('success'):
            return f"Your booking request is being processed. I will notify you once the provider responds.\nBooking number: {booking.booking_number}"
        return f"Your booking request was created successfully. We are attempting to notify the provider.\nBooking number: {booking.booking_number}"

    def _handle_booking_request_step(self, conversation: ConversationState, message: str) -> str:
        if self._looks_like_requirements(message):
            conversation.current_step = 'inquiry'
            conversation.context_data = {}
            conversation.save()
            return "New accommodation requirements detected. Please provide them and I'll search again."
        return "Your booking request is being processed. Please wait for the provider's response."

    def _handle_provider_response_step(self, conversation: ConversationState, message: str) -> str:
        selected_id = conversation.context_data.get('selected_property', {}).get('id')
        if not selected_id:
            return "No property is associated with this booking."
        booking = Booking.objects.filter(cell_number=conversation.cell_number, property_id=selected_id, status='pending').first()
        if not booking:
            return "No pending booking found."
        text = message.lower().strip()
        if any(x in text for x in ('accept', 'accepted', 'confirm', 'confirmed', 'yes', 'approved')):
            booking.status = 'provider_accepted'
            status = 'ACCEPTED'
        elif any(x in text for x in ('decline', 'declined', 'reject', 'rejected', 'no', 'unavailable')):
            booking.status = 'provider_declined'
            status = 'DECLINED'
        else:
            booking.status = 'provider_pending'
            status = 'PENDING'
        booking.save()
        conversation.context_data['provider_response'] = message
        conversation.context_data['booking_status'] = status.lower()
        conversation.save()
        return f"Booking status update: {status}.\nProvider message: {message}"

    def _handle_info_request_step(self, conversation: ConversationState, message: str) -> str:
        result = provider_workflow.process_student_response_to_info_request(conversation.cell_number, message)
        if result.get('success'):
            conversation.current_step = 'provider_response'
            conversation.save()
        return result.get('message', 'Information sent.')

    def _handle_booking_confirmation_step(self, conversation: ConversationState, message: str) -> str:
        return "Booking confirmed. Thank you!"

    def _handle_cleanup_step(self, conversation: ConversationState, message: str) -> str:
        return self._cleanup_conversation(conversation)

    def _handle_show_more(self, conversation: ConversationState) -> str:
        results = conversation.context_data.get('search_results', [])
        page = conversation.context_data.get('current_property_page', 0) + 1
        if page * 5 >= len(results):
            return "No more properties to show. Please refine your search or select from the current listings."
        conversation.context_data['current_property_page'] = page
        conversation.save()
        return self.property_search.show_property_listings(conversation)

    def _process_property_selection(self, conversation: ConversationState, index: int) -> str:
        results = conversation.context_data.get('search_results', [])
        if index < 0 or index >= len(results):
            return "Invalid selection. Please choose a property from the listings."
        selected = results[index]
        conversation.context_data['selected_property'] = selected
        conversation.context_data['selected_property_index'] = index + 1
        conversation.current_step = 'name_collection'
        conversation.save()
        return f"*PROPERTY SELECTED:* {selected.get('name', 'Property')}\n\nPlease provide your name in the format: *name-(your full name)*."

    def _create_booking(self, conversation: ConversationState, student_name: str) -> Tuple[Optional[Booking], bool]:
        try:
            selected = conversation.context_data.get('selected_property')
            if not selected:
                return None, False
            property_obj = Property.objects.get(id=selected['id'])
            existing = Booking.objects.filter(cell_number=conversation.cell_number, property=property_obj, status='pending').first()
            if existing:
                return existing, False
            number = self._generate_unique_booking_number()
            period = conversation.context_data.get('rental_period', 'month')
            if period not in {'day', 'week', 'month'}:
                period = 'month'
            if period == 'day':
                price = property_obj.price_per_day or property_obj.price_per_month / 30.0
            elif period == 'week':
                price = property_obj.price_per_week or property_obj.price_per_month / 4.0
            else:
                price = property_obj.price_per_month
            return Booking.objects.create(cell_number=conversation.cell_number, student_name=student_name, property=property_obj, booking_number=number, status='pending', rental_period=period, price_amount=price), True
        except Exception as exc:
            logger.error('Error creating booking: %s', exc, exc_info=True)
            return None, False

    def _generate_unique_booking_number(self) -> str:
        while True:
            number = f"XK1-E{random.randint(0, 999999):06d}"
            if not Booking.objects.filter(booking_number=number).exists():
                return number

    def _send_booking_to_provider(self, booking: Booking) -> Dict:
        try:
            phone = booking.property.provider.phone_number
            if phone.startswith('0'):
                phone = '+263' + phone[1:]
            elif phone.startswith('263'):
                phone = '+' + phone
            message = (f"A student is requesting accommodation.\nBooking#: {booking.booking_number}\n"
                       f"Property: {booking.property.name}\nStudent: {booking.student_name}\n"
                       f"Student Cell: {booking.cell_number}\nPlease reply with Confirm or Decline.")
            ok = whatsapp_service.send_text_message(phone, message)
            return {'success': bool(ok), 'message': 'Booking sent to provider.', 'booking_number': booking.booking_number}
        except Exception as exc:
            logger.error('Error sending booking to provider: %s', exc, exc_info=True)
            return {'success': False, 'message': 'Failed sending booking to provider.'}

    def _reset_conversation(self, conversation: ConversationState) -> str:
        conversation.current_step = 'inquiry'
        conversation.context_data = {}
        conversation.save()
        return "_Sure, I've reset our conversation. You can start fresh_"

    def _cleanup_conversation(self, conversation: ConversationState) -> str:
        conversation.is_active = False
        conversation.save()
        return "Conversation ended. Thank you for using our service."

    def _extract_property_selection(self, message: str, conversation: ConversationState) -> Optional[int]:
        match = re.search(r'option-(\d+)', message)
        if not match:
            return None
        value = int(match.group(1))
        return value if 1 <= value <= len(conversation.context_data.get('search_results', [])) else None

    def _extract_name_from_message(self, message: str) -> Optional[str]:
        if not message or not message.lower().strip().startswith('name-'):
            return None
        value = message.strip()[5:].strip()
        return value or None

    def _looks_like_requirements(self, message: str) -> bool:
        text = (message or '').lower()
        keywords = ['need', 'looking for', 'want', 'find', 'search', 'accommodation', 'room', 'apartment', 'house', 'budget', 'price', 'people', 'parking', 'wifi', 'water', 'electricity', 'location', 'amenities']
        return sum(1 for keyword in keywords if keyword in text) >= 2

    def _generate_jeff_about_message(self) -> str:
        return "Jeff helps users search for accommodation and make booking requests."

    def _handle_insights_command(self, conversation: ConversationState, message_lower: str) -> str:
        return "Jeff is currently free to use. Search for accommodation, select a property, and make a booking request."


step_handlers = StepHandlers()
