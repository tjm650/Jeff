import logging
import re
import uuid
import random
import os
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from django.db import models
from datetime import timedelta

from core.models import ConversationState, Booking, Property, AccommodationProvider
from whatsapp.utils.whatsapp_service import whatsapp_service
from providers.services.workflow import provider_workflow
from .message_classifier import message_classifier
from .property_search import property_search_handler
from .payment_integration import payment_integration_handler
from .help_utils import help_utils_handler
from .nlp_processor import nlp_processor_handler
from .utils import conversation_utils

logger = logging.getLogger(__name__)


class StepHandlers:
    """Handles individual conversation steps as per PDF specification"""

    def __init__(self):
        self.message_classifier = message_classifier
        self.property_search = property_search_handler
        self.payment_integration = payment_integration_handler
        self.help_utils = help_utils_handler
        self.nlp_processor = nlp_processor_handler
        self.utils = conversation_utils

    def _handle_inquiry_step(self, conversation: ConversationState, message: str) -> str:
        """Step 1: Check if user is a provider, then handle inquiry accordingly"""
        try:
            # Check for abort command
            if message.lower().strip() in ['abort', 'restart', 'start over', 'cancel']:
                return self._reset_conversation(conversation)

            # Allow insights commands from inquiry as well
            if message.lower().strip().startswith('insights'):
                return self._handle_insights_command(conversation, message.lower().strip())

            # Check if the message is 'jeff' or 'j'
            if message.lower().strip() in ['jeff', 'j']:
                return self._generate_jeff_about_message()

            # Check if user is a provider
            from providers.models import Provider
            user_number = getattr(conversation, 'cell_number', None)
            if user_number:
                # Normalize number for matching
                normalized_number = user_number.strip()
                if normalized_number.startswith('0'):
                    normalized_number = '+263' + normalized_number[1:]
                elif normalized_number.startswith('263'):
                    normalized_number = '+' + normalized_number
                elif not normalized_number.startswith('+263'):
                    normalized_number = '+263' + normalized_number

                provider_exists = Provider.objects.filter(phone_number=normalized_number).exists()
                if provider_exists:
                    # Follow provider workflow
                    from providers.services import provider_workflow
                    return provider_workflow.handle_provider_inquiry(conversation, message)

            # If not a provider, follow normal accommodation enquiry workflow
            requirements = self.nlp_processor.extract_requirements(message)
            if requirements:
                # Store requirements in conversation state
                conversation.context_data['requirements'] = requirements
                # Check token validity before proceeding
                from payment.handlers.token import token_handler
                valid_token = token_handler.get_valid_token(conversation.cell_number)
                if not valid_token or not token_handler.validate_token_usage(valid_token):
                    return self._show_payment_instructions(conversation)
                    
                # Add invert_sort flag to sort properties with high prices at the top
                requirements['invert_sort'] = True

                # Store requirements in conversation state regardless of token status
                conversation.context_data['requirements'] = requirements

                # Determine next step based on token validity
                if not valid_token or not token_handler.validate_token_usage(valid_token):
                    conversation.current_step = 'token_check'
                    conversation.save()
                    return self._show_payment_instructions(conversation)
                
                # Check if rental period needs clarification
                if requirements.get('needs_rental_period_clarification'):
                    return requirements['rental_period_clarification_message']
                elif requirements.get('original_message') and requirements.get('rental_period'):
                    # Already have rental period, proceed to search
                    conversation.current_step = 'property_listings'
                    conversation.save()
                    return self.property_search.proceed_to_property_search(conversation, requirements)
                else:
                    # Proceed with existing flow
                    conversation.current_step = 'property_listings'
                    conversation.save()
                    return self.property_search.proceed_to_property_search(conversation, requirements)
            else:
                return "Please provide your accommodation requirements (location, budget, number of people, etc.)."
        except Exception as e:
            logger.error(f"Error in inquiry step: {str(e)}")
            return "Sorry, I couldn't process your inquiry. Please try again."

    def _generate_jeff_about_message(self) -> str:
        """Generate Jeff about message from markdown file."""
        try:
            # Correctly construct the absolute path to the markdown file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Navigate up to the project root `jeff/` from `jeff/apps/core/services/conversation/`
            project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
            file_path = os.path.join(project_root, 'privacy', 'privacy_whatsapp.md')

            with open(file_path, 'r', encoding='utf-8') as f:
                about_content = f.read()

            from django.conf import settings
            privacy_policy_url = settings.JEFF_SETTINGS.get('PRIVACY_POLICY_URL')

            # Add link to privacy policy page
            about_content += f"\n\nRead the Terms & Privacy Policy on {privacy_policy_url}"

            return about_content
        except FileNotFoundError:
            logger.error("jeff_about.md file not found.")
            return "Sorry, I couldn't retrieve the information at the moment. Contact support team"
        except Exception as e:
            logger.error(f"Error reading jeff_about.md file: {e}")
            return "Sorry, an error occurred while retrieving the information."


    def _get_insights(self) -> Dict:
        """Calculate insights for the last 4 months"""
        try:
            four_months_ago = timezone.now() - timedelta(days=120)

            # Unique users who have used Jeff Agent (from bookings)
            unique_users = Booking.objects.filter(created_at__gte=four_months_ago).values('cell_number').distinct().count()

            # Average price for property listings
            avg_listing_price = Property.objects.filter(created_at__gte=four_months_ago).aggregate(
                models.Avg('price_per_month')
            )['price_per_month__avg'] or 0

            # Average price for selected properties (from bookings)
            avg_selected_price = Booking.objects.filter(created_at__gte=four_months_ago).aggregate(
                models.Avg('property__price_per_month')
            )['property__price_per_month__avg'] or 0

            # Additional metrics
            # Total searches: approximate by counting conversation states updated in the period
            try:
                total_searches = ConversationState.objects.filter(last_message_at__gte=four_months_ago).count()
            except Exception:
                total_searches = 0

            total_bookings = Booking.objects.filter(created_at__gte=four_months_ago).count()

            conversion_rate = round((total_bookings / total_searches * 100), 2) if total_searches > 0 else 0.0

            # Average time to confirmation (hours) for bookings that have been confirmed
            confirmed_bookings = Booking.objects.filter(created_at__gte=four_months_ago, confirmed_at__isnull=False)
            avg_time_to_confirmation_hours = 0.0
            if confirmed_bookings.exists():
                diffs = [(b.confirmed_at - b.created_at).total_seconds() for b in confirmed_bookings if b.confirmed_at and b.created_at]
                if diffs:
                    avg_time_to_confirmation_hours = round((sum(diffs) / len(diffs)) / 3600.0, 2)

            # Top campuses by number of properties added in period
            campuses_qs = Property.objects.filter(created_at__gte=four_months_ago).values('campus_name').annotate(count=models.Count('id')).order_by('-count')[:3]
            top_campuses = [c['campus_name'] for c in campuses_qs if c.get('campus_name')]

            # Top amenities across listed properties in period (simple tally)
            amenity_counts = {}
            props_amenities = Property.objects.filter(created_at__gte=four_months_ago).values_list('amenities', flat=True)
            for a_list in props_amenities:
                if not a_list:
                    continue
                for a in a_list:
                    key = a.strip().lower()
                    amenity_counts[key] = amenity_counts.get(key, 0) + 1

            top_amenities = [k for k, _ in sorted(amenity_counts.items(), key=lambda x: x[1], reverse=True)][:5]

            return {
                'unique_users': unique_users,
                'avg_listing_price': round(avg_listing_price, 2),
                'avg_selected_price': round(avg_selected_price, 2),
                'total_searches': total_searches,
                'conversion_rate_percent': conversion_rate,
                'avg_time_to_confirmation_hours': avg_time_to_confirmation_hours,
                'top_campuses': top_campuses,
                'top_amenities': top_amenities
            }
        except Exception as e:
            logger.error(f"Error calculating insights: {str(e)}")
            # Return default values if insights fail
            return {
                'unique_users': 0,
                'avg_listing_price': 0.0,
                'avg_selected_price': 0.0
            }

    def _generate_unique_booking_number(self) -> str:
        """Generate a unique booking number in the format XK1-E followed by 6 digits"""
        while True:
            # Generate 6 random digits
            random_digits = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            booking_number = f"XK1-E{random_digits}"
            
            # Check if this booking number already exists
            if not Booking.objects.filter(booking_number=booking_number).exists():
                return booking_number

    def _format_interactive_insights(self, insights: Dict) -> str:
        """Format insights into an interactive, no-emoji summary with follow-up commands"""
        try:
            total_searches = insights.get('total_searches', 0)
            total_bookings = insights.get('total_bookings', 0)
            conversion = insights.get('conversion_rate_percent', 0.0)
            avg_listing = insights.get('avg_listing_price', 0.0)
            avg_selected = insights.get('avg_selected_price', 0.0)
            avg_time_hours = insights.get('avg_time_to_confirmation_hours', 0.0)
            top_campuses = insights.get('top_campuses', [])
            top_amenities = insights.get('top_amenities', [])
            unique_users = insights.get('unique_users', [])

            lines = []
            lines.append(f"*INSIGHTS FOR THE LAST 4 MONTHS*")
            # lines.append("")
            lines.append(f"• _{unique_users} used Jeff_")
            # lines.append(f"Searches (last 4 months): {total_searches}")
            # lines.append(f"Bookings (last 4 months): {total_bookings}")
            lines.append(f"• _Average search to bookings rate: {conversion/100}_")
            lines.append(f"• _Average listing price: ${avg_listing}_")
            lines.append(f"• _Average selected property price: ${avg_selected}_")
            # if avg_time_hours and avg_time_hours > 0:
            #     lines.append(f"Avg time to confirmation: {avg_time_hours} hours")
            # if top_campuses:
            #     lines.append(f"Top campuses: {', '.join(top_campuses)}")
            # if top_amenities:
            #     lines.append(f"Top amenities: {', '.join(top_amenities)}")

            # # Interactive options
            # lines.append("")
            # lines.append("To see more details, reply with one of the following commands:")
            # lines.append("- insights conversion  (conversion trend and breakdown)")
            # lines.append("- insights campuses    (details for top campuses)")
            # lines.append("- insights amenities   (top amenities breakdown)")
            # lines.append("- insights trends      (time series on searches/bookings)")
            # lines.append("- insights help        (this list)")

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error formatting insights: {str(e)}")
            return "Insights currently unavailable"

    def _handle_insights_command(self, conversation: ConversationState, message_lower: str) -> str:
        """Provide detailed insights responses for the interactive commands."""
        try:
            parts = message_lower.split()
            cmd = parts[1] if len(parts) > 1 else 'help'
            insights = self._get_insights()

            if cmd == 'help':
                return ("Available insight commands:\n"
                        "- insights conversion  (conversion rate, searches vs bookings)\n"
                        "- insights campuses    (top campuses breakdown)\n"
                        "- insights amenities   (top amenities breakdown)\n"
                        "- insights trends      (searches/bookings per month for last 4 months)\n"
                        "- insights help        (this message)")

            if cmd == 'conversion':
                total_searches = insights.get('total_searches', 0)
                total_bookings = insights.get('total_bookings', 0)
                conv = insights.get('conversion_rate_percent', 0.0)
                return (f"Conversion details (last 4 months):\n"
                        f"- Searches: {total_searches}\n"
                        f"- Bookings: {total_bookings}\n"
                        f"- Conversion rate: {conv}%")

            if cmd == 'campuses':
                top = insights.get('top_campuses', [])
                if not top:
                    return "No campus data available for the period."
                return "Top campuses (by properties added):\n- " + "\n- ".join(top)

            if cmd == 'amenities':
                top = insights.get('top_amenities', [])
                if not top:
                    return "No amenity data available for the period."
                return "Top amenities:\n- " + "\n- ".join(top)

            if cmd == 'trends':
                # Provide simple month-by-month counts for searches and bookings
                try:
                    now = timezone.now()
                    lines = ["Searches and bookings per month (last 4 months):"]
                    for i in range(3, -1, -1):
                        start = (now - timedelta(days=30 * (i + 1))).replace(day=1)
                        end = (now - timedelta(days=30 * i)).replace(day=1)
                        searches = ConversationState.objects.filter(last_message_at__gte=start, last_message_at__lt=end).count()
                        bookings = Booking.objects.filter(created_at__gte=start, created_at__lt=end).count()
                        month_label = start.strftime('%Y-%m')
                        lines.append(f"{month_label}: searches={searches}, bookings={bookings}")
                    return "\n".join(lines)
                except Exception:
                    return "Trend data unavailable at the moment."

            return "Unknown insights command. Reply 'insights help' for available options."
        except Exception as e:
            logger.error(f"Error handling insights command: {str(e)}")
            return "Error retrieving insights. Please try again later."

    def _handle_token_check_step(self, conversation: ConversationState, message: str) -> str:
        """Step 2: Check if student has valid tokens"""
        try:
            # Check for abort command
            if message.lower().strip() in ['abort', 'restart', 'start over', 'cancel']:
                return self._reset_conversation(conversation)

            # Check token validity
            from payment.handlers.token import token_handler
            valid_token = token_handler.get_valid_token(conversation.cell_number)
            if valid_token and token_handler.validate_token_usage(valid_token):
                return self._show_properties_and_payment_instructions(conversation, {})
            else:
                return self._show_payment_instructions(conversation)
        except Exception as e:
            logger.error(f"Error in token check step: {str(e)}")
            return "Error checking tokens. Please try again."

    def _handle_property_listings_step(self, conversation: ConversationState, message: str) -> str:
        """Step 3: Handle property selection"""
        try:
            message = message.lower().strip()

            # First check if user has a valid token
            from payment.handlers.token import token_handler
            valid_token = token_handler.get_valid_token(conversation.cell_number)
            if not valid_token or not token_handler.validate_token_usage(valid_token):
                return self._show_payment_instructions(conversation)
            
            # Check if user wants to see more properties
            if message == 'show-more':
                return self._handle_show_more(conversation)
                
            # Check if user is trying to send name instead of selecting property
            if self._is_name_format(message):
                return "Please select a property first by sending 'option-(number)' (e.g. 'option-1' for the first property).\nOr send 'abort' to start a new search."

            # Check if user is sending new requirements instead of selecting
            if self._looks_like_requirements(message):
                return "Please select a property first. Send 'option-(number)' for your chosen property (e.g. 'option-1').\nOr send 'abort' to start a new search."

            # Validate that we have search results to select from
            search_results = conversation.context_data.get('search_results', [])
            if not search_results:
                return "No properties available for selection. Please search for accommodation first by sending your requirements (e.g. 'I need a 2-bed room for $200')."

            # Process selection or show listings
            selection = self._extract_property_selection(message, conversation)
            if selection:
                # Calculate the actual index based on the current page
                current_page = conversation.context_data.get('current_property_page', 0)
                real_index = selection + (current_page * 5)
                if real_index <= len(search_results):
                    return self._process_property_selection(conversation, real_index)
                else:
                    return "Invalid selection. Please choose a property number from the displayed list."
            else:
                # Provide helpful error message for invalid selection
                max_selection = min(5, len(search_results) - (conversation.context_data.get('current_property_page', 0) * 5))
                return f"_Please select a valid property using 'option-(number)' format e.g. 'option-1' for the first property_.\n\n{self.property_search.show_property_listings(conversation)}"
        except Exception as e:
            logger.error(f"Error in property listings step: {str(e)}")
            return "Error processing property listings. Please try again."

    def _handle_name_collection_step(self, conversation: ConversationState, message: str) -> str:
        """Step 4: Collect user name for booking"""
        try:
            # Comprehensive validation for name collection step

            # 1. Check if user is in the correct step for name collection
            if conversation.current_step != 'name_collection':
                return "Please search for properties first and select one using 'option-(number)' before providing your name."

            # 2. Validate that user has selected a property in this session
            selected_property = conversation.context_data.get('selected_property')
            if not selected_property:
                logger.warning(f"Name collection attempted without property selection for {conversation.cell_number}")
                return "No property selected. Please search for properties first and select one using 'option-(number)' before providing your name."

            # 3. Validate that we have search results (property was selected from current search)
            search_results = conversation.context_data.get('search_results', [])
            if not search_results:
                logger.warning(f"Name collection attempted without search results for {conversation.cell_number}")
                return "No properties available. Please search for accommodation first by sending your requirements (e.g., 'I need a 2-bed room for $200')."

            # 4. Validate that the selected property index exists and matches search results
            selected_index = conversation.context_data.get('selected_property_index')
            if not selected_index or selected_index < 1 or selected_index > len(search_results):
                logger.warning(f"Invalid property selection index for {conversation.cell_number}")
                return "Invalid property selection. Please search for properties again and select one using 'option-(number)'."

            # Check if user is trying to select a different property
            if self._extract_property_selection(message, conversation):
                return "You've already selected a property. Please provide your name in the format: name-(your full name)\nExample: name-John Doe"

            # Check if user is sending new requirements
            if self._looks_like_requirements(message):
                return "Please provide your name first before sending new requirements. Format: name-(your full name)\nExample: name-John Doe"

            # Extract name from "name-(user's name)" format
            name = self._extract_name_from_message(message)
            if name:
                # First check and deduct token
                from payment.handlers.token import token_handler
                valid_token = token_handler.get_valid_token(conversation.cell_number)
                
                if not valid_token:
                    return "No valid token found. Please purchase a token before proceeding with the booking."
                    
                if not token_handler.validate_token_usage(valid_token):
                    return "Your token cannot be used. It may have expired or reached its usage limit. Please purchase a new token."

                # Deduct token usage
                try:
                    valid_token.used_count += 1
                    valid_token.save()
                    logger.info(f"Token usage deducted for {conversation.cell_number}, new count: {valid_token.used_count}")
                except Exception as e:
                    logger.error(f"Error deducting token usage: {str(e)}")
                    return "Error processing your token. Please try again or contact support."
                    
                # Create booking after successful token deduction
                booking, is_new = self._create_booking(conversation, name.strip())
                if booking:
                    if not is_new:
                        return f"Booking already exists with number {booking.booking_number}. Proceeding with the existing booking."
                    # Send message to provider
                    result = self._send_booking_to_provider(booking)
                    if result['success']:
                        conversation.context_data['student_name'] = name.strip()
                        conversation.current_step = 'booking_request'
                        conversation.save()
                        logger.info(f"Name collected: {name} for property {selected_property.get('name', 'Unknown')} for {conversation.cell_number}")
                    else:
                        logger.error(f"Failed to send booking to provider for {conversation.cell_number}: {result['message']}")
                        # Still update the step and proceed, but log the error

                    # Always send confirmation to student, regardless of provider notification
                    conversation.context_data['student_name'] = name.strip()
                    conversation.current_step = 'booking_request'
                    conversation.save()

                    # Get interactive insights summary (no emojis)
                    insights = self._get_insights()
                    # Default confirmation message
                    base_message = f"""Your booking request is being processed. I will notify you once the provider responds. Thank you!
Booking number: {booking.booking_number}"""

                    if not result['success']:
                        base_message = f"""Your booking request has been created successfully. We are attempting to notify the provider. I will notify you once the provider responds. Thank you!
Booking number: {booking.booking_number}"""

                    insights_text = self._format_interactive_insights(insights)
                    return base_message + "\n\n" + insights_text
                else:
                    return "Failed to create booking. Please try again."
            else:
                return "Please provide your name in the format: name-(your full name)\nExample: name-John Doe"
        except Exception as e:
            logger.error(f"Error in name collection step: {str(e)}")
            return "Error collecting name. Please try again."

    def _handle_booking_request_step(self, conversation: ConversationState, message: str) -> str:
        """Step 5: Handle booking request"""
        try:
            message_lower = message.lower().strip()

            # Allow insights commands during booking flow
            if message_lower.startswith('insights'):
                return self._handle_insights_command(conversation, message_lower)

            # Allow certain message types during booking processing
            if message_lower in ['hi', 'hello', 'hey', 'help']:
                # Handle greetings and help during booking processing
                if 'help' in message_lower:
                    return "Your booking request is being processed. Please wait for the provider's response. For general help, please wait until after the booking process is complete."
                else:
                    return "Your booking request is being processed. Please wait for the provider's response. Feel free to send greetings anytime!"

            # Check if user is sending new accommodation requirements (should restart process)
            if self._looks_like_requirements(message):
                # Reset to inquiry for new search
                conversation.current_step = 'inquiry'
                conversation.context_data = {}  # Clear previous context
                conversation.save()
                return "New accommodation requirements detected. Please provide your requirements and I'll search for properties again."

            # Check if user is trying to send another name after booking request
            if self._is_name_format(message):
                return "Your booking request is being processed. Please wait for the provider's response. If you need to search for another property later, send your requirements then."

            # Check if user is trying to select another property
            if self._extract_property_selection(message, conversation):
                return "Your booking request is being processed. Please wait for the provider's response. If you need to search for another property later, send your requirements then."

            # For any other message during booking processing, ask user to wait
            return "Your booking request is being processed. Please wait for the provider's response before sending other messages. If you need help, please wait until after the booking process is complete."
        except Exception as e:
            logger.error(f"Error in booking request step: {str(e)}")
            return "Error processing booking request. Please try again."

    def _handle_provider_response_step(self, conversation: ConversationState, message: str) -> str:
        """Step 6: Handle provider response"""
        try:
            message_lower = message.lower().strip()

            # Allow certain message types during provider response wait
            if message_lower in ['hi', 'hello', 'hey', 'help']:
                # Handle greetings and help during provider response wait
                if 'help' in message_lower:
                    return "We're waiting for the provider's response. Please wait for their reply. For general help, please wait until after the booking process is complete."
                else:
                    return "We're waiting for the provider's response. Please wait for their reply. Feel free to send greetings anytime!"

            # Check if user is sending new accommodation requirements (should restart process)
            if self._looks_like_requirements(message):
                # Reset to inquiry for new search
                conversation.current_step = 'inquiry'
                conversation.context_data = {}  # Clear previous context
                conversation.save()
                return "New accommodation requirements detected. Please provide your requirements and I'll search for properties again."

            # Check if user is trying to send name during provider response
            if self._is_name_format(message):
                return "We're waiting for the provider's response to your booking request. Please wait for their reply. If you need to search for another property later, send your requirements then."

            # Check if user is trying to select another property
            if self._extract_property_selection(message, conversation):
                return "We're waiting for the provider's response to your booking request. Please wait for their reply. If you need to search for another property later, send your requirements then."

            # Store provider response in conversation context
            conversation.context_data['provider_response'] = message.strip()
            conversation.context_data['provider_response_timestamp'] = str(timezone.now())

            # Fetch the booking
            selected_property_id = conversation.context_data.get('selected_property', {}).get('id')
            if not selected_property_id:
                logger.error(f"No selected property found for cell_number {conversation.cell_number}")
                return "Error: No property selected for this booking response."

            booking = Booking.objects.filter(cell_number=conversation.cell_number, property_id=selected_property_id, status='pending').first()
            if not booking:
                logger.error(f"No booking found for cell_number {conversation.cell_number} and property_id {selected_property_id}")
                return "Error: No booking found for this response."

            # Check if provider accepted or declined the booking
            if any(word in message_lower for word in ['accept', 'accepted', 'Confirm', 'confirm', 'confirmed', 'yes', 'approved']):
                status = "✅ ACCEPTED"
                conversation.context_data['booking_status'] = 'provider_accepted'
                booking.status = 'provider_accepted'
                booking.save()
                # Send confirmation template to student
                self._send_student_confirmation(booking, 'accepted')
            elif any(word in message_lower for word in ['Decline', 'decline', 'declined', 'reject', 'rejected', 'no', 'unavailable']):
                status = "❌ DECLINED"
                conversation.context_data['booking_status'] = 'provider_declined'
                booking.status = 'provider_declined'
                booking.save()
                # Send rejection template to student
                self._send_student_confirmation(booking, 'rejected')
            else:
                status = "⏳ PENDING"
                conversation.context_data['booking_status'] = 'provider_pending'
                booking.status = 'provider_pending'
                booking.save()

            conversation.save()

            # Return confirmation with status
            student_name = conversation.context_data.get('student_name', 'Student')
            property_name = conversation.context_data.get('selected_property', {}).get('name', 'Property')

            return f"""📋 *BOOKING STATUS UPDATE*

Student: {student_name}
Property: {property_name}
Provider Response: {status}

Provider Message: "{message}"

Response Time: {conversation.context_data['provider_response_timestamp']}

*Next Steps:*
• If accepted: Booking will be confirmed
• If declined: Student will be notified to select another property
• If pending: Awaiting final provider decision"""
        except Exception as e:
            logger.error(f"Error in provider response step: {str(e)}")
            return "Error processing provider response."

    def _handle_info_request_step(self, conversation: ConversationState, message: str) -> str:
        """Step 7: Handle additional info requests"""
        try:
            # Process student's response to info request
            result = provider_workflow.process_student_response_to_info_request(conversation.cell_number, message)
            if result['success']:
                conversation.current_step = 'provider_response'
                conversation.save()
                return result['message']
            else:
                return result['message']
        except Exception as e:
            logger.error(f"Error in info request step: {str(e)}")
            return "Error handling info request."

    def _handle_booking_confirmation_step(self, conversation: ConversationState, message: str) -> str:
        """Step 8: Handle booking confirmation"""
        try:
            # Check if user is trying to send another name
            if self._is_name_format(message):
                return "Your booking is already confirmed. If you need to search for another property, please send your accommodation requirements (e.g., 'I need a 2-bed room for $200')."

            # Check if user is trying to select another property
            if self._extract_property_selection(message, conversation):
                return "Your booking is already confirmed. If you need to search for another property, please send your accommodation requirements first."

            # Confirm booking
            return "Booking confirmed. Thank you!"
        except Exception as e:
            logger.error(f"Error in booking confirmation step: {str(e)}")
            return "Error confirming booking."

    def _handle_show_more(self, conversation: ConversationState) -> str:
        """Handle showing more property listings"""
        try:
            search_results = conversation.context_data.get('search_results', [])
            current_page = conversation.context_data.get('current_property_page', 0)
            
            # Calculate next page
            next_page = current_page + 1
            start_idx = next_page * 5
            
            # Check if there are more properties to show
            if start_idx >= len(search_results):
                return "No more properties to show. Please refine your search or select from the current listings."
            
            # Update page in conversation context
            conversation.context_data['current_property_page'] = next_page
            conversation.save()
            
            # Show next set of properties
            return self.property_search.show_property_listings(conversation)
        except Exception as e:
            logger.error(f"Error handling show-more: {str(e)}")
            return "Error showing more properties. Please try again."

    def _handle_cleanup_step(self, conversation: ConversationState, message: str) -> str:
        """Step 9: Cleanup and conversation reset"""
        try:
            # Check if user is trying to send name or property selection after booking
            if self._is_name_format(message):
                return "Your booking process is complete. If you need to search for another property, please send your accommodation requirements (e.g., 'I need a 2-bed room for $200')."

            if self._extract_property_selection(message, conversation):
                return "Your booking process is complete. If you need to search for another property, please send your accommodation requirements (e.g., 'I need a 2-bed room for $200')."

            return self._cleanup_conversation(conversation)
        except Exception as e:
            logger.error(f"Error in cleanup step: {str(e)}")
            return "Error during cleanup."

    def _show_properties_and_payment_instructions(self, conversation: ConversationState, requirements: Dict) -> str:
        """Show properties and payment instructions"""
        try:
            # First check if user has a valid token
            from payment.handlers.token import token_handler
            valid_token = token_handler.get_valid_token(conversation.cell_number)
            if not valid_token or not token_handler.validate_token_usage(valid_token):
                return self._show_payment_instructions(conversation)

            # If token is valid, proceed with property search
            result = self.property_search.proceed_to_property_search(conversation, requirements)
            if result:
                if isinstance(result, str):
                    logger.info(f"Property search completed with message for {conversation.cell_number}")
                else:
                    properties_count = len(conversation.context_data.get('search_results', [])) if conversation.context_data else 0
                    logger.info(f"Property search completed for {conversation.cell_number}: Found {properties_count} properties")
                return result
            else:
                # Import recommendation service from MCP integration
                from ..mcp.integration import get_mcp_integration
                mcp_integration = get_mcp_integration()
                if mcp_integration and mcp_integration.recommendation_service:
                    return mcp_integration.recommendation_service.generate_recommendation_summary(requirements)
                else:
                    # Fallback when MCP integration is not available
                    return self._get_fallback_recommendation_message(requirements)
        except Exception as e:
            logger.error(f"Error showing properties: {str(e)}")
            return "Error retrieving properties."

    def _show_payment_instructions(self, conversation: ConversationState) -> str:
        """Show payment instructions for token purchase"""
        try:
            # Get requirements from conversation context and search for properties
            requirements = conversation.context_data.get('requirements', {}) if getattr(conversation, 'context_data', None) is not None else {}
            
            # Search for properties
            properties = []
            try:
                result = self.property_search.proceed_to_property_search(conversation, requirements)
                if isinstance(result, str):
                    # If we got a string result, it's likely an error message
                    logger.info(f"Property search returned message for {conversation.cell_number}: {result}")
                else:
                    properties = conversation.context_data.get('search_results', [])
                    properties_count = len(properties)
                    logger.info(f"Property search completed for {conversation.cell_number}: Found {properties_count} properties")
                    logger.info(f"Search requirements: {requirements}")
            except Exception as e:
                logger.error(f"Error searching for properties: {str(e)}")
                properties = []

            # Create header with property count from conversation context
            properties_count = len(conversation.context_data.get('search_results', [])) if conversation.context_data else 0
            
            header = f"""*PROPERTY LISTINGS* 🏡
*Properties Found:* {properties_count}
• To view Property listing details and book accommodation, you need a token.\n
"""

            frontend_url = os.getenv('NEXT_PUBLIC_FRONTEND_URL')
            instructions = (f"""*HOW TO PURCHASE A TOKEN*
• Visit: {frontend_url}/cart

• _*Questions*? Send 'help' anytime._
• _Send 'Jeff' message for more info about the service, Terms & Privacy Policy of Jeff or visit {frontend_url+'/privacy'}._
• _After purchasing a token, send your accommodation requirements again to continue searching for properties._"""
)

            return header + instructions

        except Exception as e:
            logger.error(f"Error building payment instructions with listings: {str(e)}")
            # Even in error case, try to get property count from context
            properties_count = len(conversation.context_data.get('search_results', [])) if conversation.context_data else 0
            
            header = f"""*PROPERTY LISTINGS* 🏡
*Properties Found:* {properties_count}
• To view Property listing details and book accommodation, you need a token.\n
"""

            frontend_url = os.getenv('NEXT_PUBLIC_FRONTEND_URL')
            token_instructions = f"""*HOW TO PURCHASE A TOKEN*
• _Visit: {frontend_url}/cart._

• _*Questions?* Send 'help' anytime._
• _Send 'Jeff' message for more info about the service, Privacy Policy and Terms & Conditions of service._
• _After purchasing a token, send your accommodation requirements again to continue searching for properties._"""

            return header + token_instructions

    def _process_property_selection(self, conversation: ConversationState, selection: int) -> str:
        """Process property selection"""
        try:
            # Get the selected property from search results
            search_results = conversation.context_data.get('search_results', [])
            if not search_results or selection < 1 or selection > len(search_results):
                return "Invalid selection. Please reply with a valid property number from the listings."

            selected_property = search_results[selection - 1]

            # Store selected property in conversation context
            conversation.context_data['selected_property'] = selected_property
            conversation.context_data['selected_property_index'] = selection
            conversation.current_step = 'name_collection'
            conversation.save()

            logger.info(f"Property selected: {selected_property['name']} for {conversation.cell_number}")

            # Format pricing information (show monthly, weekly, daily explicitly)
            def _fmt_price(val):
                try:
                    v = float(val)
                    return f"${v:.2f}"
                except Exception:
                    return "N/A"

            month = selected_property.get('price_per_month', 0) or 0
            week = selected_property.get('price_per_week', 0) or 0
            day = selected_property.get('price_per_day', 0) or 0

            if isinstance(month, (int, float)) and month > 0:
                pricing_info = f"• Monthly rate: {_fmt_price(month)}/month\n"
            else:
                pricing_info = "• Monthly rate: N/A\n"

            if isinstance(week, (int, float)) and week > 0:
                pricing_info += f"• Weekly rate: {_fmt_price(week)}/week\n"
            else:
                pricing_info += "• Weekly rate: N/A\n"

            if isinstance(day, (int, float)) and day > 0:
                pricing_info += f"• Daily rate: {_fmt_price(day)}/day\n"
            else:
                pricing_info += "• Daily rate: N/A\n"

            if selected_property.get('price_per_head'):
                try:
                    pph = float(selected_property.get('price_per_head'))
                    pricing_info += f"• Price per head: ${pph:.2f}/head\n"
                except Exception:
                    pricing_info += f"• Price per head: {selected_property.get('price_per_head')}\n"

            return f"""*PROPERTY SELECTED:* {selected_property['name']} 🏡

*Property Details*
{pricing_info}
Please provide your name in the format: *name-(your full name)*. This name will be used for booking processing with the provider.
_Example: name-Jeff Agent_"""
        except Exception as e:
            logger.error(f"Error processing selection: {str(e)}")
            return "Invalid selection. Please try again."

    def _reset_conversation(self, conversation: ConversationState) -> str:
        """Reset conversation to inquiry step"""
        try:
            # Reset conversation state
            conversation.current_step = 'inquiry'
            conversation.context_data = {}
            conversation.save()
            logger.info(f"Conversation reset to inquiry for {conversation.cell_number}")
            return "_Sure, I've reset our conversation. You can start fresh_"
        except Exception as e:
            logger.error(f"Error resetting conversation: {str(e)}")
            # Try to reset without saving if save fails
            try:
                conversation.current_step = 'inquiry'
                conversation.context_data = {}
                return "_Sure, I've reset our conversation. You can start fresh_"
            except Exception as e2:
                logger.error(f"Error even creating response for reset: {str(e2)}")
                return "Conversation has been reset. Please try searching for accommodation again."

    def _cleanup_conversation(self, conversation: ConversationState) -> str:
        """Clean up conversation"""
        try:
            conversation.is_active = False
            conversation.save()
            return "Conversation ended. Thank you for using our service."
        except Exception as e:
            logger.error(f"Error cleaning up: {str(e)}")
            return "Error ending conversation."

    def _extract_selection(self, message: str) -> Optional[int]:
        """Extract selection number from message"""
        match = re.search(r'\d+', message)
        return int(match.group()) if match else None

    def _extract_property_selection(self, message: str, conversation: ConversationState) -> Optional[int]:
        """Extract and validate property selection number from 'option-(number)' format"""
        try:
            # Get available properties from conversation context
            search_results = conversation.context_data.get('search_results', [])
            if not search_results:
                logger.warning(f"No search results found for property selection")
                return None

            # Check for 'option-(number)' format
            match = re.search(r'option-(\d+)', message.strip().lower())
            if not match:
                return None

            selection = int(match.group(1))

            # Validate selection is within valid range
            if 1 <= selection <= len(search_results):
                logger.info(f"Valid property selection: {selection} for {conversation.cell_number}")
                return selection
            else:
                logger.warning(f"Invalid property selection: {selection} (valid range: 1-{len(search_results)}) for {conversation.cell_number}")
                return None

        except Exception as e:
            logger.error(f"Error extracting property selection: {str(e)}")
            return None

    def _is_name_format(self, message: str) -> bool:
        """Check if message is in name format (name-...)"""
        if not message:
            return False
        return message.lower().strip().startswith('name-')

    def _extract_name_from_message(self, message: str) -> Optional[str]:
        """Extract name from 'name-(user's name)' format"""
        if not message or not self._is_name_format(message):
            return None

        try:
            # Remove 'name-' prefix and get the actual name
            name_part = message.strip()[5:]  # Remove 'name-' prefix
            if name_part:
                return name_part.strip()
            return None
        except Exception as e:
            logger.error(f"Error extracting name from message: {str(e)}")
            return None

    def _looks_like_requirements(self, message: str) -> bool:
        """Check if message looks like accommodation requirements"""
        if not message:
            return False

        message_lower = message.lower().strip()

        # Check for requirement keywords that shouldn't appear in property selection step
        requirement_keywords = [
            'need', 'looking for', 'want', 'find', 'search', 'accommodation',
            'room', 'apartment', 'house', 'budget', 'price', 'heads', 'people',
            'single', 'double', 'triple', 'parking', 'wifi', 'water', 'electricity',
            'near campus', 'close to', 'location', 'amenities'
        ]

        # If message contains multiple requirement keywords, it's likely new requirements
        keyword_count = sum(1 for keyword in requirement_keywords if keyword in message_lower)
        return keyword_count >= 2

    def _create_booking_request(self, conversation: ConversationState, message: str) -> str:
        """Create booking request"""
        # Placeholder implementation
        return "Booking request created. Waiting for provider response."

    def _create_booking(self, conversation: ConversationState, student_name: str) -> Tuple[Optional[Booking], bool]:
        """Create a new booking or return existing one"""
        try:
            selected_property = conversation.context_data.get('selected_property')
            if not selected_property:
                return None, False

            # Find the property in the database
            property = Property.objects.get(id=selected_property['id'])

            # Check if a pending booking already exists for this user and property
            existing_booking = Booking.objects.filter(
                cell_number=conversation.cell_number,
                property=property,
                status='pending'
            ).first()

            if existing_booking:
                logger.info(f"Existing booking found: {existing_booking.booking_number} for {conversation.cell_number}")
                return existing_booking, False

            # Generate booking number
            booking_number = self._generate_unique_booking_number()

            # Get rental period from conversation context
            rental_period = conversation.context_data.get('rental_period', 'month')
            if rental_period not in ['day', 'week', 'month']:
                rental_period = 'month'  # Fallback to monthly if invalid

            # Get appropriate price based on rental period
            if rental_period == 'day':
                price = property.price_per_day or property.price_per_month / 30.0
            elif rental_period == 'week':
                price = property.price_per_week or property.price_per_month / 4.0
            else:
                price = property.price_per_month

            # Create booking
            booking = Booking.objects.create(
                cell_number=conversation.cell_number,
                student_name=student_name,
                property=property,
                booking_number=booking_number,
                status='pending',
                rental_period=rental_period,
                price_amount=price
            )

            logger.info(f"Booking created: {booking_number} for {conversation.cell_number}")
            return booking, True

        except Exception as e:
            logger.error(f"Error creating booking: {str(e)}")
            return None, False

    def _send_booking_to_provider(self, booking: Booking) -> Dict:
        """Send booking message to provider using content template with retry and text fallback."""
        import os
        import time
        try:
            content_sid = os.getenv('TWILIO_CONTENT_TEMPLATE_SID_PROVIDER_BOOKING')
            if not content_sid:
                logger.error("Provider booking template SID not configured")
                # Fall back to text immediately
                return self._send_booking_to_provider_text(booking)

            # Ensure provider phone number is in correct format
            provider_phone = booking.property.provider.phone_number
            if not provider_phone.startswith('+263'):
                if provider_phone.startswith('263'):
                    provider_phone = '+' + provider_phone
                elif provider_phone.startswith('0'):
                    provider_phone = '+263' + provider_phone[1:]
                else:
                    logger.error(f"Invalid provider phone number format: {provider_phone}")
                    return {
                        'success': False,
                        'message': 'Invalid provider phone number format. Please contact support.'
                    }

            # Get student name from booking or conversation state
            conversation = ConversationState.objects.filter(
                cell_number=booking.cell_number,
                is_active=True
            ).first()
            student_name = booking.student_name or (conversation.context_data.get('student_name') if conversation else booking.cell_number)

            # Unified 4-variable mapping
            content_variables = {
                "1": student_name,                 # Student name
                "2": booking.cell_number,          # Student phone
                "3": booking.property.name,        # Property name
                "4": booking.booking_number        # Booking reference
            }

            # Retry mechanism then fallback to text
            max_retries = 3
            for attempt in range(max_retries):
                success = whatsapp_service.send_template_message(
                    provider_phone,
                    content_sid,
                    content_variables
                )
                if success:
                    logger.info(f"Provider booking template sent to {provider_phone} on attempt {attempt + 1}")
                    return {
                        'success': True,
                        'message': 'Booking message sent to provider.',
                        'booking_number': booking.booking_number
                    }
                if attempt < max_retries - 1:
                    time.sleep(2)

            # Fallback to text if template failed
            return self._send_booking_to_provider_text(booking)
        except Exception as e:
            logger.error(f"Error sending booking template to provider: {str(e)}")
            return self._send_booking_to_provider_text(booking)

    def _send_booking_to_provider_text(self, booking: Booking) -> Dict:
        try:
            provider_phone = booking.property.provider.phone_number
            if not provider_phone.startswith('+263'):
                if provider_phone.startswith('263'):
                    provider_phone = '+' + provider_phone
                elif provider_phone.startswith('0'):
                    provider_phone = '+263' + provider_phone[1:]
                else:
                    logger.error(f"Invalid provider phone number format: {provider_phone}")
                    return {
                        'success': False,
                        'message': 'Invalid provider phone number format. Please contact support.'
                    }

            conversation = ConversationState.objects.filter(
                cell_number=booking.cell_number,
                is_active=True
            ).first()
            student_name = booking.student_name or (conversation.context_data.get('student_name') if conversation else booking.cell_number)

            message = (
                f"""Good day, sir or madam. A student is currently seeking accommodation at your residential property for students. Please confirm availability at your earliest convenience or let us know if it is not an option. If you require additional information, contact the student and confirm later. Thank you.
                \n\n"""
                f"Booking#: {booking.booking_number}\n\n"
                f"Property Name: {booking.property.name}\n"
                f"Student Name: {student_name}\n"
                f"Student Cell: {booking.cell_number}\n"
                f"Please reply with Confirm or Decline."
            )

            if whatsapp_service.send_text_message(provider_phone, message):
                logger.info(f"Booking message sent to provider via text: {provider_phone}")
                return {
                    'success': True,
                    'message': 'Booking message sent to provider via fallback.',
                    'booking_number': booking.booking_number
                }
            else:
                return {
                    'success': False,
                    'message': 'failed sending message to provider. Please try again later.'
                }
        except Exception as e:
            logger.error(f"Error sending booking message to provider via text: {str(e)}")
            return {
                'success': False,
                'message': 'failed sending booking message. Please try again later.'
            }

    def _send_student_confirmation(self, booking: Booking, status: str) -> bool:
        """Send confirmation or rejection template message to student"""
        try:
            import os
            if status == 'accepted':
                content_sid = os.getenv('TWILIO_CONTENT_TEMPLATE_SID_STUDENT_CONFIRMATION')
                if not content_sid:
                    logger.error("Student confirmation template SID not configured")
                    return False
            elif status == 'rejected':
                content_sid = os.getenv('TWILIO_CONTENT_TEMPLATE_SID_STUDENT_REJECTION')
                if not content_sid:
                    logger.error("Student rejection template SID not configured")
                    return False
            else:
                logger.error(f"Invalid status for student confirmation: {status}")
                return False

            # Ensure student phone number is in correct format
            student_phone = booking.cell_number
            if not student_phone.startswith('+263'):
                if student_phone.startswith('263'):
                    student_phone = '+' + student_phone
                elif student_phone.startswith('0'):
                    student_phone = '+263' + student_phone[1:]
                else:
                    logger.error(f"Invalid student phone number format: {student_phone}")
                    return False

            logger.info(f"Sending {status} template to student: {student_phone}, Content SID: {content_sid}")

            # Get student name from booking
            student_name = booking.student_name or booking.cell_number

            content_variables = {
                "1": booking.property.name,  # Property name
                "2": booking.property.provider.name,  # Provider name
                "3": booking.property.provider.phone_number,  # Provider contact
                "4": booking.booking_number,  # Booking reference
                "5": student_name,  # Student name
            }

                # "6": booking.cell_number  # Student contact
                
            success = whatsapp_service.send_template_message(
                student_phone,
                content_sid,
                content_variables
            )

            if success:
                logger.info(f"Student {status} message sent successfully to {student_phone}")
                return True
            else:
                logger.error(f"Failed to send student {status} message to {student_phone}")
                return False

        except Exception as e:
            logger.error(f"Error sending student confirmation: {str(e)}")
            return False

    def _get_fallback_recommendation_message(self, requirements: Dict) -> str:
        """Get fallback recommendation message when MCP integration is not available"""
        try:
            message = "• No properties found matching your exact requirements.\n\n"

            # Provide basic suggestions based on requirements
            suggestions = []

            if requirements.get('budget_max'):
                suggestions.append(f"Consider adjusting your budget (currently ${requirements['budget_max']})")

            if requirements.get('heads'):
                suggestions.append(f"Try different room sharing options for {requirements['heads']} people")

            if requirements.get('amenities'):
                suggestions.append("Consider properties with fewer amenities to increase options")

            if not suggestions:
                suggestions = [
                    "Try expanding your location search",
                    "Consider adjusting your budget range",
                    "Look for properties with different amenities"
                ]

            message += "Suggestions:\n"
            for suggestion in suggestions[:3]:
                message += f"- {suggestion}\n"

            message += "\nPlease refine your requirements or contact support for assistance."

            return message

        except Exception as e:
            logger.error(f"Error generating fallback recommendation: {str(e)}")
            return ("_No properties found matching your requirements. "
                   "Please try adjusting your criteria such as budget, location, or amenities. "
                   "Contact support for personalized assistance._")


# Global instance
step_handlers = StepHandlers()