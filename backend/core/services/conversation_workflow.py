import logging
from typing import Dict, List

from whatsapp.utils.whatsapp_service import whatsapp_service
from core.models import ConversationState, AccommodationProvider
from .conversation.message_classifier import message_classifier
from .conversation.property_search import property_search_handler
from .conversation.help_utils import help_utils_handler
from .conversation.nlp_processor import nlp_processor_handler
from .conversation.utils import conversation_utils
from .conversation.step_handlers import step_handlers

logger = logging.getLogger(__name__)


class ConversationWorkflow:
    """Free accommodation search and booking workflow.

    Payment is intentionally not part of Jeff's current product flow.
    """

    STEPS = [
        'inquiry',
        'property_listings',
        'name_collection',
        'booking_request',
        'provider_response',
        'info_request',
        'booking_confirmation',
        'cleanup',
    ]

    def __init__(self):
        self.whatsapp_service = whatsapp_service
        self.message_classifier = message_classifier
        self.property_search = property_search_handler
        self.help_utils = help_utils_handler
        self.nlp_processor = nlp_processor_handler
        self.utils = conversation_utils
        self.step_handlers = step_handlers

    def _is_provider(self, cell_number: str) -> bool:
        try:
            return AccommodationProvider.objects.filter(phone_number=cell_number).exists()
        except Exception:
            return False

    def process_message(self, cell_number: str, message: str, media_url: str = None) -> str:
        try:
            conversation = self.utils.get_conversation_state(cell_number)
            if not conversation:
                return "_Sure, I've reset our conversation. You can start fresh_"

            if self._is_provider(cell_number):
                return self.handle_provider_message(cell_number, message)

            if media_url:
                return self.help_utils.handle_media_message(cell_number, media_url, message)

            classification = self.message_classifier.classify_message_with_gemini(message)

            if classification == 'H':
                return self.help_utils.get_comprehensive_help_message()
            if classification == 'G':
                return self.message_classifier.handle_greeting_classification(cell_number, message)
            if classification == 'J':
                return self.step_handlers._generate_jeff_about_message()
            if classification == 'X':
                conversation.current_step = 'inquiry'
                conversation.context_data = {}
                conversation.save()
                return "_Sure, I've reset our conversation. You can start fresh_"

            # Legacy payment states are treated as a normal free inquiry so old
            # conversation records cannot lock a user behind payment.
            if conversation.current_step in ('token_check', 'payment_confirmation'):
                conversation.current_step = 'inquiry'
                conversation.save()

            current_step = conversation.current_step
            if current_step == 'inquiry':
                return self.step_handlers._handle_inquiry_step(conversation, message)
            if current_step == 'property_listings':
                return self.step_handlers._handle_property_listings_step(conversation, message)
            if current_step == 'name_collection':
                return self.step_handlers._handle_name_collection_step(conversation, message)
            if current_step == 'booking_request':
                return self.step_handlers._handle_booking_request_step(conversation, message)
            if current_step == 'provider_response':
                return self.step_handlers._handle_provider_response_step(conversation, message)
            if current_step == 'info_request':
                return self.step_handlers._handle_info_request_step(conversation, message)
            if current_step == 'booking_confirmation':
                return self.step_handlers._handle_booking_confirmation_step(conversation, message)
            if current_step == 'cleanup':
                return self.step_handlers._handle_cleanup_step(conversation, message)

            conversation.current_step = 'inquiry'
            conversation.save()
            return self.step_handlers._handle_inquiry_step(conversation, message)
        except Exception as e:
            logger.error("Error processing message for %s: %s", cell_number, e, exc_info=True)
            return "Sorry, I encountered an error. Please try again or send 'help' for assistance."

    def handle_provider_message(self, cell_number: str, message: str) -> str:
        try:
            from providers.services.workflow import provider_workflow
            result = provider_workflow.handle_provider_response(cell_number, message)
            return result.get('message', 'Error processing provider message.')
        except Exception as e:
            logger.error("Error handling provider message: %s", e)
            return "Error processing provider message. Please try again."

    def _get_conversation_state(self, cell_number: str) -> ConversationState:
        return self.utils.get_conversation_state(cell_number)

    def _handle_inquiry_step(self, conversation, message):
        return self.step_handlers._handle_inquiry_step(conversation, message)

    def _handle_name_collection_step(self, conversation, message):
        return self.step_handlers._handle_name_collection_step(conversation, message)

    def _handle_property_listings_step(self, conversation, message):
        return self.step_handlers._handle_property_listings_step(conversation, message)

    def _handle_provider_response_step(self, conversation, message):
        return self.step_handlers._handle_provider_response_step(conversation, message)

    def _handle_info_request_step(self, conversation, message):
        return self.step_handlers._handle_info_request_step(conversation, message)

    def _handle_booking_confirmation_step(self, conversation, message):
        return self.step_handlers._handle_booking_confirmation_step(conversation, message)

    def _handle_cleanup_step(self, conversation, message):
        return self.step_handlers._handle_cleanup_step(conversation, message)

    def _format_property_listing(self, properties: List[Dict]) -> str:
        return self.property_search._format_property_listing(properties)

    def _format_enhanced_property_listing(self, properties: List[Dict], requirements: Dict) -> str:
        return self.property_search._format_enhanced_property_listing(properties, requirements)
