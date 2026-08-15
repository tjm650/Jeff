"""
Conversation Workflow Service for Jeff Agent

This service implements the exact 8-step conversation workflow as specified in the PDF:
Step 1: Student Inquiry
Step 2: Token Check
Step 3: Show Property Listings
Step 4: Booking Request
Step 5: Provider Response Handling
Step 6: Handle Info Request
Step 7: Booking Confirmation
Step 8: Cleanup & Close

This service now uses modular components in the conversation/ subfolder for better organization and maintainability.
"""

import logging
from typing import Dict, List, Optional

from whatsapp.utils.whatsapp_service import whatsapp_service
from core.models import ConversationState, AccommodationProvider

# Import specialized conversation components
from .conversation.message_classifier import message_classifier
from .conversation.property_search import property_search_handler
from .conversation.help_utils import help_utils_handler
from .conversation.nlp_processor import nlp_processor_handler
from .conversation.utils import conversation_utils
from .conversation.step_handlers import step_handlers

logger = logging.getLogger(__name__)


class ConversationWorkflow:
    """Main conversation workflow manager following PDF specifications using modular components"""

    # Conversation steps as per PDF specification
    STEPS = [
        'inquiry',           # Step 1: Student Inquiry
        'property_listings', # Step 3: Show Property Listings
        'name_collection',   # Step 4: Collect user name for booking
        'booking_request',   # Step 5: Booking Request
        'provider_response', # Step 6: Provider Response Handling
        'info_request',      # Step 7: Handle Info Request
        'booking_confirmation', # Step 8: Booking Confirmation
        'cleanup'            # Step 9: Cleanup & Close
    ]

    def __init__(self):
        """Initialize conversation workflow with modular components"""
        self.whatsapp_service = whatsapp_service
        # Initialize specialized components
        self.message_classifier = message_classifier
        self.property_search = property_search_handler
        self.help_utils = help_utils_handler
        self.nlp_processor = nlp_processor_handler
        self.utils = conversation_utils
        self.step_handlers = step_handlers

    def _is_provider(self, cell_number: str) -> bool:
        """Check if the user is an accommodation provider"""
        try:
            return AccommodationProvider.objects.filter(phone_number=cell_number).exists()
        except Exception as e:
            logger.error(f"Error checking if user is provider: {str(e)}")
            return False

    def process_message(self, cell_number: str, message: str, media_url: str = None) -> str:
        """
        Process incoming WhatsApp message according to PDF workflow with enhanced error handling

        Args:
            cell_number: Student's phone number
            message: Message text
            media_url: Media URL if message contains media

        Returns:
            WhatsApp response message
        """
        logger.info(f"Processing message from {cell_number}: '{message[:50]}{'...' if len(message) > 50 else ''}'")

        try:
            # Get or create conversation state FIRST
            logger.debug(f"Getting conversation state for {cell_number}")
            try:
                conversation = self.utils.get_conversation_state(cell_number)
                if not conversation:
                    logger.error(f"Failed to get conversation state for {cell_number}")
                    return "_Sure, I've reset our conversation. You can start fresh_"
            except Exception as e:
                logger.error(f"Error getting conversation state for {cell_number}: {str(e)}")
                return "_Sure, I've reset our conversation. You can start fresh_"

            # Check if user is a provider and route accordingly
            if self._is_provider(cell_number):
                logger.info(f"Routing provider {cell_number} to provider workflow")
                return self.handle_provider_message(cell_number, message)

            # Handle provider response payloads before classification (for students, but unlikely)
            message_lower = message.lower().strip()
            if message_lower in ['cn', 'xn']:
                logger.info(f"Handling provider response payload: {message} for {cell_number}")
                from core.models import Booking
                booking = Booking.objects.filter(cell_number=cell_number, status='pending').first()
                if booking:
                    provider_phone = booking.property.provider.phone_number
                    result = self.handle_provider_response(provider_phone, message)
                    return result
                else:
                    return "No pending booking found."

            # Classify message using message classifier component
            message_classification = self.message_classifier.classify_message_with_gemini(message)
            logger.info(f"Message classified as: {message_classification} for {cell_number}")

            # Route based on classification
            if message_classification == 'H':
                # Help message - provide comprehensive help
                logger.info(f"Help message detected for {cell_number}")
                return self.help_utils.get_comprehensive_help_message()

            elif message_classification == 'P':
                message_classification = 'A'

            elif message_classification == 'G':
                # Greeting message - handle with enhanced greeting flow
                logger.info(f"Greeting message detected for {cell_number}")
                return self.message_classifier.handle_greeting_classification(cell_number, message)

            elif message_classification == 'J':
                # Jeff about message - provide service information
                logger.info(f"Jeff about message detected for {cell_number}")
                return self.step_handlers._generate_jeff_about_message()

            elif message_classification == 'X':
                # Abort/Restart message - reset conversation
                logger.info(f"Abort/Restart message detected for {cell_number}")
                try:
                    # Reset the conversation state properly
                    conversation.current_step = 'inquiry'
                    conversation.context_data = {}
                    conversation.save()
                    logger.info(f"Conversation reset to inquiry for {cell_number}")

                    return "_Sure, I've reset our conversation. You can start fresh_"
                except Exception as e:
                    logger.error(f"Error resetting conversation for {cell_number}: {str(e)}")
                    return "_Sure, I've reset our conversation. You can start fresh_"

            elif message_classification == 'S':
                # Property selection message - route to step processing
                logger.info(f"Property selection message detected for {cell_number}")
                # Continue with normal workflow processing

            elif message_classification == 'N':
                # Name collection message - route to step processing
                logger.info(f"Name collection message detected for {cell_number}")
                # Continue with normal workflow processing

            elif message_classification == 'A':
                # Accommodation enquiry - proceed with normal workflow
                logger.info(f"Accommodation enquiry detected for {conversation.cell_number}")
                
                # Check if we're waiting for rental period clarification
                if conversation.context_data.get('requirements'):
                    from matching.rental_period_extractor import rental_period_extractor
                    rental_period = rental_period_extractor.extract_rental_period(message)
                    if rental_period:
                        # Update the stored requirements with the rental period
                        requirements = conversation.context_data['requirements']
                        requirements['rental_period'] = rental_period
                        # Clear the clarification flags
                        requirements.pop('needs_rental_period_clarification', None)
                        requirements.pop('rental_period_clarification_message', None)
                        # Proceed with search
                        return self.step_handlers._handle_inquiry_step(conversation, requirements.get('original_message', ''))
                
                # Continue with normal workflow processing
            else:
                # Unknown classification - default to accommodation enquiry
                logger.warning(f"Unknown classification '{message_classification}' for {cell_number}, defaulting to accommodation enquiry")

            # Handle media messages
            if media_url:
                logger.debug(f"Processing media message from {cell_number}")
                return self.help_utils.handle_media_message(cell_number, media_url, message)

            # Process text message based on current step
            current_step = conversation.current_step
            logger.debug(f"Processing step '{current_step}' for {cell_number}")

            # Additional validation for contextual messages
            if message_classification == 'S' and current_step != 'property_listings':
                # User sent option-(number) but not in property selection step
                if current_step in ['booking_confirmation', 'cleanup']:
                    return "Your booking process is complete. If you need to search for another property, please send your accommodation requirements (e.g., 'I need a 2-bed room for $200')."
                return "Please search for properties first by sending your accommodation requirements (e.g. 'I need a 2-bed room for $200')."

            if message_classification == 'N':
                # User sent name-(name) - validate context thoroughly
                if current_step != 'name_collection':
                    # User sent name but not in name collection step
                    if current_step in ['booking_confirmation', 'cleanup']:
                        return "Your booking process is complete. If you need to search for another property, please send your accommodation requirements (e.g., 'I need a 2-bed room for $200')."
                    return "Please search for properties and select one first before providing your name."

                # User is in name collection step - validate they have a selected property
                selected_property = conversation.context_data.get('selected_property')
                search_results = conversation.context_data.get('search_results', [])
                if not selected_property or not search_results:
                    logger.warning(f"Name message received in name_collection step but no valid property selection for {cell_number}")
                    return "No property selected. Please search for properties first and select one using 'option-(number)' before providing your name."

            if current_step == 'inquiry':
                return self.step_handlers._handle_inquiry_step(conversation, message)
            elif current_step == 'property_listings':
                return self.step_handlers._handle_property_listings_step(conversation, message)
            elif current_step == 'name_collection':
                return self.step_handlers._handle_name_collection_step(conversation, message)
            elif current_step == 'booking_request':
                return self.step_handlers._handle_booking_request_step(conversation, message)
            elif current_step == 'provider_response':
                return self.step_handlers._handle_provider_response_step(conversation, message)
            elif current_step == 'info_request':
                return self.step_handlers._handle_info_request_step(conversation, message)
            elif current_step == 'booking_confirmation':
                return self.step_handlers._handle_booking_confirmation_step(conversation, message)
            elif current_step == 'cleanup':
                return self.step_handlers._handle_cleanup_step(conversation, message)
            else:
                # Unknown step, reset to inquiry
                logger.warning(f"Unknown conversation step '{current_step}' for {cell_number}, resetting to inquiry")
                return self.utils.reset_to_inquiry(conversation)

        except Exception as e:
            logger.error(f"Error processing message for {cell_number}: {str(e)}", exc_info=True)
            return "Sorry, I encountered an error. Please try again or send 'help' for assistance."

    def _get_conversation_state(self, cell_number: str) -> ConversationState:
        """Get or create conversation state for user"""
        return self.utils.get_conversation_state(cell_number)

    def handle_provider_message(self, cell_number: str, message: str) -> str:
        """Handle messages from accommodation providers"""
        try:
            from providers.services.workflow import provider_workflow
            result = provider_workflow.handle_provider_response(cell_number, message)
            if result['success']:
                return result['message']
            else:
                return result['message']
        except Exception as e:
            logger.error(f"Error handling provider message: {str(e)}")
            return "Error processing provider message. Please try again."

    def _handle_inquiry_step(self, conversation: ConversationState, message: str) -> str:
        """Step 1: Handle student inquiry with comprehensive NLP processing"""
        return self.step_handlers._handle_inquiry_step(conversation, message)




    def _proceed_to_property_search(self, conversation: ConversationState, requirements: Dict) -> str:
        """Proceed with property search using enhanced NLP requirements"""
        return self.property_search.proceed_to_property_search(conversation, requirements)



    def _handle_name_collection_step(self, conversation: ConversationState, message: str) -> str:
        """Step 4: Handle user name collection for booking"""
        return self.step_handlers._handle_name_collection_step(conversation, message)

    def _handle_property_listings_step(self, conversation: ConversationState, message: str) -> str:
        """Step 3: Handle property selection with enhanced NLP processing"""
        return self.step_handlers._handle_property_listings_step(conversation, message)

    def _handle_new_requirements(self, conversation: ConversationState, message: str) -> str:
        """Handle new requirements from any step in the conversation"""
        return self.nlp_processor.handle_new_requirements(conversation, message)

    def _process_property_selection(self, conversation: ConversationState, selection: int) -> str:
        """Process property selection and ask for user name"""
        return self.step_handlers._process_property_selection(conversation, selection)

    def _handle_provider_response_step(self, conversation: ConversationState, message: str) -> str:
        """Step 5: Handle provider response"""
        return self.step_handlers._handle_provider_response_step(conversation, message)

    def _handle_info_request_step(self, conversation: ConversationState, message: str) -> str:
        """Step 6: Handle additional info requests from provider"""
        return self.step_handlers._handle_info_request_step(conversation, message)

    def _handle_booking_confirmation_step(self, conversation: ConversationState, message: str) -> str:
        """Step 7: Handle booking confirmation"""
        return self.step_handlers._handle_booking_confirmation_step(conversation, message)

    def _handle_cleanup_step(self, conversation: ConversationState, message: str) -> str:
        """Step 8: Cleanup and conversation reset"""
        return self.step_handlers._handle_cleanup_step(conversation, message)

    def _format_property_listing(self, properties: List[Dict]) -> str:
        """Format property listings according to PDF specification"""
        return self.property_search._format_property_listing(properties)

    def _format_enhanced_property_listing(self, properties: List[Dict], requirements: Dict) -> str:
        """Format enhanced property listings with NLP-derived insights"""
        return self.property_search._format_enhanced_property_listing(properties, requirements)

    def _cleanup_conversation(self, conversation: ConversationState) -> str:
        """Clean up conversation and reset state (Step 8 in PDF)"""
        return self.step_handlers._cleanup_conversation(conversation)

    def _reset_to_inquiry(self, conversation: ConversationState) -> str:
        """Reset conversation to inquiry step"""
        return self.utils.reset_to_inquiry(conversation)

    def _get_help_message(self) -> str:
        """Get enhanced help message using NLP processor capabilities"""
        return self.utils.get_help_message()

    def _get_contextual_help(self, conversation: ConversationState) -> str:
        """Get contextual help based on conversation state and NLP data"""
        return self.help_utils.get_contextual_help(conversation)

    def _provide_nlp_suggestions(self, failed_requirements: Dict) -> str:
        """Provide intelligent suggestions based on failed NLP extraction"""
        return self.help_utils.provide_nlp_suggestions(failed_requirements)

    def _handle_media_message(self, cell_number: str, media_url: str, caption: str) -> str:
        """Handle media messages (no longer used for POP)"""
        return self.help_utils.handle_media_message(cell_number, media_url, caption)

    def handle_provider_response(self, provider_phone: str, message: str) -> str:
        """Handle responses from accommodation providers using booking workflow"""
        try:
            from providers.services.workflow import provider_workflow
            result = provider_workflow.handle_provider_response(provider_phone, message)
            if result['success']:
                return f"Provider response processed: {result['message']}"
            else:
                return f"Error: {result['message']}"

        except Exception as e:
            logger.error(f"Error handling provider response: {str(e)}")
            return " Error processing provider response. Please try again."

    def handle_payment_webhook(self, payment_data: Dict) -> Dict:
        """Handle payment webhook from PayNow and update conversation workflow"""

        try:
            # Extract payment reference
            paynow_reference = payment_data.get('paynowreference') or payment_data.get('reference')
            status = payment_data.get('status', '').lower()

            if not paynow_reference:
                return {
                    'success': False,
                    'message': 'No payment reference provided'
                }

            # Find payment by PayNow reference
            payment = Payment.objects.filter(
                paynow_reference=paynow_reference
            ).first()

            if not payment:
                # Try finding by internal reference
                payment = Payment.objects.filter(
                    reference=paynow_reference
                ).first()

            if not payment:
                return {
                    'success': False,
                    'message': f'Payment not found for reference: {paynow_reference}'
                }

            # Update payment status
            if status == 'paid':
                payment.status = 'paid'
                payment.save()

                # Process successful payment
                result = payment_processor.process_successful_payment(payment)

                if result['success']:
                    return {
                        'success': True,
                        'message': 'Payment processed successfully',
                        'transaction_id': payment.transaction_id,
                        'whatsapp_number': payment.whatsapp_number
                    }
                else:
                    return {
                        'success': False,
                        'message': f'Payment marked as paid but processing failed: {result.get("error", "Unknown error")}'
                    }

            elif status in ['cancelled', 'failed']:
                payment.status = status
                payment.save()

                return {
                    'success': True,
                    'message': f'Payment {status}',
                    'transaction_id': payment.transaction_id,
                    'whatsapp_number': payment.whatsapp_number
                }
            else:
                return {
                    'success': False,
                    'message': f'Unknown payment status: {status}'
                }

        except Exception as e:
            logger.error(f"Error handling payment webhook: {str(e)}")
            return {
                'success': False,
                'message': f'Webhook processing error: {str(e)}'
            }