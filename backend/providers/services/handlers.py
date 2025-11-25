import logging
import re
import os
from typing import Dict, List, Optional
from django.utils import timezone
from django.db import transaction

from core.models import Booking, Property, AccommodationProvider, ConversationState, Token
from whatsapp.utils.whatsapp_service import whatsapp_service
from core.services.booking.notifications import booking_notifications
from core.services.mcp import mcp_integration
from providers.insights.insights import InsightsHandler

logger = logging.getLogger(__name__)


class ProviderHandlers:
    def get_time_based_greeting(self) -> str:
        """Return time-based greeting based on current hour"""
        from datetime import datetime
        try:
            from django.utils import timezone
            import pytz
            cat_tz = pytz.timezone('Africa/Harare')
            now_cat = timezone.now().astimezone(cat_tz)
            hour = now_cat.hour
        except Exception:
            hour = datetime.now().hour

        if hour >= 0 and hour < 12:
            return "Good morning"
        elif hour >= 12 and hour < 18:
            return "Good afternoon"
        else:hour >= 18 and hour < 24
        return "Good evening"
    """Handles provider-related operations"""

    def __init__(self):
        self.whatsapp_service = whatsapp_service

    def _classify_provider_message_with_mcp(self, message: str) -> str:
        """Classify provider message using MCP integration"""
        try:
            if mcp_integration.is_configured():
                # Use MCP for classification with provider-specific categories
                greeting = self.get_time_based_greeting()
                prompt = f"""
                {greeting}! Classify this provider message into exactly ONE category:

                Categories:
                1. Jeff about message (J) - Messages requesting information about Jeff service, Privacy Policy, or Terms & Conditions (e.g., "jeff", "j", "about jeff", "privacy policy", "terms")
                2. Enquiry message sent to Jeff admin (E) - Messages asking questions about the system, bookings, or admin-related inquiries (e.g., "how does the system work?", "what is the status of booking?", "can you explain the process?")
                3. Greeting message (G) - Simple greetings like "hi", "hello", "good morning", "thanks" (e.g., "hi", "hello", "good morning", "thanks for the booking")
                4. Help message (H) - Messages asking for help, assistance, or information about how to use the system (e.g., "I need help", "how do I confirm?", "assist me", "what should I do?", "help me")
                5. Accommodation request confirmation (CN) - Messages confirming or accepting a booking request (e.g., "yes", "confirmed", "accept", "ok")
                6. Accommodation request declining (XN) - Messages declining or rejecting a booking request (e.g., "no", "reject", "not available", "decline")
                7. Accommodation request additional information (AX) - Messages requesting more information from the student (e.g., "what is your course?", "do you smoke?", "tell me more about the student")
                8. Property Insights Submission (IS) - Messages containing property information fields like "property name:", "gender preference:", "total rooms:", "available rooms:", "amenities:", "pricing:", etc.
                9. Property List Request (PL) - Messages requesting to view property listings (e.g., "LP", "List my Property", "list properties")
                10. Cancel Conversation (X) - Messages to cancel/reset the conversation (e.g., "x", "cancel", "abort", "restart")

                CRITICAL: 
                - Messages containing words like "help", "assist", "need help", "how do I", "what should I" are ALWAYS HELP messages (H), never greetings.
                - Messages containing 3+ property insight fields (e.g., "property name:", "total rooms:", "pricing:") are ALWAYS insights messages (IS).

                Message: "{message}"

                Return ONLY a single character: J, E, G, H, CN, XN, AX, IS, PL, or X

                Choose the BEST matching category.
                """

                # Try Gemini first
                if mcp_integration.api_handlers['gemini']:
                    gemini_response = mcp_integration.api_handlers['gemini'].call_api(prompt, max_tokens=10, temperature=0.1)
                    if gemini_response:
                        classification = gemini_response.strip().upper()
                        if classification in ['J', 'E', 'G', 'H', 'CN', 'XN', 'AX', 'IS', 'PL', 'X']:
                            logger.info(f"MCP (Gemini) classified provider message as: {classification}")
                            return classification

                # Fallback to Anthropic
                if mcp_integration.api_handlers['anthropic']:
                    anthropic_response = mcp_integration.api_handlers['anthropic'].call_api(prompt, max_tokens=10, temperature=0.1)
                    if anthropic_response:
                        classification = anthropic_response.strip().upper()
                        if classification in ['J', 'E', 'G', 'H', 'CN', 'XN', 'AX', 'IS', 'PL', 'X']:
                            logger.info(f"MCP (Anthropic) classified provider message as: {classification}")
                            return classification

            # Fallback to rule-based classification
            return self._classify_provider_message_fallback(message)

        except Exception as e:
            logger.error(f"Error classifying provider message with MCP: {str(e)}")
            return self._classify_provider_message_fallback(message)

    def _classify_provider_message_fallback(self, message: str) -> str:
        """Fallback rule-based classification for provider messages"""
        if not message:
            return 'G'  # Default to greeting

        message_lower = message.lower().strip()

        # Check for Jeff about message first
        if message_lower in ['jeff', 'j', 'about jeff', 'privacy policy', 'terms', 'terms and conditions']:
            return 'J'

        # Check if it's an insights message (contains typical insights fields)
        insights_fields = [
            'property name:',
            'gender preference:',
            'total rooms:',
            'available rooms:',
            'available slots',
            'amenities',
            'pricing',
            'price/term:',
            'price/month:',
            'price/week:',
            'price/day:'
        ]

        insights_field_count = sum(1 for field in insights_fields if field in message_lower)
        if insights_field_count >= 3:  # If message has 3+ insights fields, classify as insights
            return 'IS'

        # Confirmation keywords
        confirmation_keywords = [
            'yes', 'confirmed', 'ok', 'accepted', 'available', 'welcome',
            'approved', 'sure', 'okay', 'confirm', 'accept', 'cn'
        ]

        # Rejection keywords
        rejection_keywords = [
            'no', 'sorry', 'full', 'unavailable', 'occupied', 'booked',
            'cannot', 'rejected', 'not available', 'no space', 'decline', 'cancel', 'xn'
        ]

        # Information request keywords
        info_keywords = [
            'what', 'which', 'who', 'tell me', 'need to know', 'can you provide',
            'smoke', 'drink', 'drinking', 'program', 'year', 'references',
            'student', 'background', 'habits', 'lifestyle', 'course'
        ]

        # Help keywords
        help_keywords = [
            'help', 'assist', 'how', 'what can you do', 'guide', 'instructions',
            'support', 'info', 'information'
        ]

        # Greeting keywords
        greeting_keywords = [
            'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
            'greetings', 'howdy', 'welcome', 'sup', 'yo', 'start', 'begin',
            'thanks', 'thank you', 'how are you', 'how do you do',
            'nice to meet you', 'good to meet you', 'ready to start'
        ]

        # Property list keywords
        property_list_keywords = [
            'list my property', 'list property', 'list properties', 'show my properties',
            'view properties', 'property list', 'my properties'
        ]

        # Enquiry keywords
        enquiry_keywords = [
            'how does', 'what is', 'can you explain', 'system', 'admin', 'booking process',
            'how to', 'why', 'when', 'where', 'status', 'update', 'change'
        ]

        if any(keyword in message_lower for keyword in confirmation_keywords):
            return 'CN'
        elif any(keyword in message_lower for keyword in rejection_keywords):
            return 'XN'
        elif any(keyword in message_lower for keyword in info_keywords):
            return 'AX'
        elif any(keyword in message_lower for keyword in help_keywords):
            return 'H'
        elif any(keyword in message_lower for keyword in property_list_keywords):
            return 'PL'
        elif any(keyword in message_lower for keyword in greeting_keywords):
            return 'G'
        elif any(keyword in message_lower for keyword in enquiry_keywords):
            return 'E'
        else:
            return 'G'  # Default to greeting

    def _generate_provider_welcome_message(self) -> str:
        """Generate welcome message for providers using MCP integration"""
        try:
            greeting = self.get_time_based_greeting()
            if mcp_integration.is_configured():
                # Use MCP greeting handler for personalized welcome
                prompt = f"""You are Jeff, an agent both students & accommodation providers. Generate a greeting response for WhatsApp.

                Use this exact time-based greeting: "{greeting}"

                Response should:
                1. Start with the exact time-based greeting provided above
                2. Be friendly, formal and concise in continous form
                3. Explain that Jeff helps students reach accommodation providers like this user, fast and easily
                4. Mention user to send a 'Jeff' for more information about the service, Privacy Policy and Terms & Conditions of service
                5. Mention user to send a _'help'_ message for more information including insights and booking confirmation instructions
                Return only the greeting response text, starting with "{greeting}".
                """

                # Try Gemini first
                if mcp_integration.api_handlers['gemini']:
                    response = mcp_integration.api_handlers['gemini'].call_api(prompt, max_tokens=50, temperature=0.7)
                    if response and response.strip():
                        logger.info("Generated provider welcome message using MCP (Gemini)")
                        return response.strip()

                # Fallback to Anthropic
                if mcp_integration.api_handlers['anthropic']:
                    response = mcp_integration.api_handlers['anthropic'].call_api(prompt, max_tokens=50, temperature=0.7)
                    if response and response.strip():
                        logger.info("Generated provider welcome message using MCP (Anthropic)")
                        return response.strip()

            # Fallback to static message
            return f"""{greeting}, I'm Jeff, your accommodation agent. I connect NUST students with accommodation providers like you. My goal is to make property search simpler and more efficient for students. I'll notify you once there are new booking requests

• _Send 'help' for detailed instructions including insight sharing and managing your property listings._
• _Send 'Jeff' for more information about the service, Privacy Policy and Terms & Conditions._
"""
        except Exception:
            # Fallback single-line message in the unlikely event of an error
            return "Welcome! I'm Jeff, your accommodation agent. I'll notify you of new booking requests. Reply 'help' for instructions."

    def _generate_provider_help_message(self) -> str:
        """Return a manual provider help dashboard message.

        The project previously used an MCP-based generator for provider help messages.
        Per request, we use a static, clear help dashboard message for providers.
        """
        try:
            return (
                """
*JEFF HELP & SUPPORT*

*How Jeff Works* 📑
• I help NUST students find accommodation near campus
• Send me your property insights per period (weekly or monthly) from the comforts of your home.
• Your property insights help me to always be up to date

*What I Can Find 🏠*
• Single, double, triple rooms, BNBs
• Properties with WiFi, parking, etc
• Properties near campus
• Male/female/mixed accommodations
• Various budget ranges

*HOW TO SEND YOUR INSIGHTS📊*
*Property Insights*
• Property Number: XZ-1234 _(Replace with your Property Number)_

*Available Slots*
• 1h/room: 0
• 2h/room: 0
• 3h/room: 0
• 4h/room: 0

*Amenities*
• Wifi,
• Gas stoves,
• Study room,
• etc 

*Pricing*
• price/term: 0
• price/month: 0
• price/week: 0
• price/day: 0

• Total rooms: 0 _(Replace '0' with actual number)_
• Rooms with available slots: 0
• Gender Preference: ‘male’, ‘female’, ‘both’ _(Replace with 1 preference)_

- _*Need more help?* Contact our support team._
- _Send *List my Property* message to view all your property listings_
- _Send 'Jeff' message for more info about the service, Privacy Policy and Terms & Conditions of service._
                """
            )
        except Exception:
            # Fallback single-line message in the unlikely event of an error
            return "Reply with YES to confirm, NO to decline, or 'help' for provider instructions."

    def handle_provider_response(self, provider_phone: str, message: str) -> Dict:
        """
        Handle responses from accommodation providers with enhanced error handling

        Args:
            provider_phone: Provider's phone number
            message: Provider's response message

        Returns:
            Dict with processing result
        """
        logger.info(f"Processing provider response from {provider_phone}: '{message[:50]}{'...' if len(message) > 50 else ''}'")

        try:
            # Find provider
            logger.debug(f"Finding provider {provider_phone} in database")
            provider = AccommodationProvider.objects.get(phone_number=provider_phone)

            # Normalize message for keyword checks
            message_lower = (message or "").lower().strip()

            # Classify response type using MCP first
            logger.debug(f"Classifying message type for provider {provider_phone}")
            response_type = self._classify_provider_message_with_mcp(message)

            # Handle different message types
            if response_type == 'J':
                logger.info(f"Jeff about message detected for provider {provider_phone}")
                return self._generate_jeff_about_message_for_provider()

            elif response_type == 'PL':
                logger.info(f"Processing property list request from provider {provider_phone}")
                return self._generate_property_list_message(provider)
    
            # Check for explicit cancellation/terminate phrases from provider
            cancel_keywords = [
                'cancel conversation', 'end conversation', 'terminate conversation',
                'cancel', 'end'
            ]
            # Only act on explicit cancellation phrases to avoid accidental triggers
            if any(kw in message_lower for kw in ['cancel conversation', 'end conversation', 'terminate conversation']):
                logger.info(f"Provider {provider_phone} requested conversation cancellation")
                # Find most recent pending booking for this provider
                booking = Booking.objects.filter(
                    property__provider=provider,
                    status='pending'
                ).order_by('-created_at').first()

                if not booking:
                    logger.warning(f"No pending booking found to cancel conversation for provider {provider_phone}")
                    return {
                        'success': False,
                        'message': 'No active conversation or pending booking found to cancel.'
                    }

                # Terminate the student's conversation state
                conversation = ConversationState.objects.filter(cell_number=booking.cell_number, is_active=True).first()
                if conversation:
                    conversation.is_active = False
                    conversation.current_step = 'inquiry'
                    conversation.context_data = {}
                    conversation.save()
                    logger.info(f"Conversation terminated for student {booking.cell_number} by provider request")
                    return {
                        'success': True,
                        'message': 'Conversation terminated successfully.'
                    }
                else:
                    logger.warning(f"No active conversation state found for student {booking.cell_number}")
                    return {
                        'success': False,
                        'message': 'No active conversation found for the current booking.'
                    }

            # Classify response type using MCP first
            logger.debug(f"Classifying message type for provider {provider_phone}")
            response_type = self._classify_provider_message_with_mcp(message)

            # Handle different message types
            if response_type == 'G':
                # For greetings, check for pending bookings
                logger.debug(f"Finding pending booking for greeting from provider {provider_phone}")
                booking = Booking.objects.filter(
                    property__provider=provider,
                    status='pending'
                ).order_by('-created_at').first()

                # For greetings, we want to show the welcome message if there's no pending booking
                # or guide them about the pending booking if one exists
                if not booking:
                    logger.info(f"No pending booking found for provider {provider_phone}, sending welcome message")
                    welcome_message = self._generate_provider_welcome_message()
                    return {
                        'success': True,
                        'message': welcome_message  # This will use our comprehensive greeting with fallback
                    }
                else:
                    logger.info(f"Processing greeting for booking {booking.booking_number}")
                    greeting = self.get_time_based_greeting()
                    return {
                        'success': True,
                        'message': f"""{greeting}! You have a pending booking that needs your attention.

*Booking Details:*
• Property: {booking.property.name}
• Student: {booking.student_name or 'Not provided'}
• Booking #: {booking.booking_number}

Please reply with:
• *YES* or *Confirm* - to accept the booking
• *NO* or *Decline* - to reject the booking
• Or ask any questions about the student

Send _'help'_ for more detailed instructions."""
                    }

            elif response_type == 'H':
                # For help, send comprehensive help without checking bookings
                logger.info(f"Processing help request for provider {provider_phone}")
                help_message = self._generate_provider_help_message()
                return {
                    'success': True,
                    'message': help_message
                }

            elif response_type == 'E':
                # For enquiry, send response without checking bookings
                logger.info(f"Processing enquiry for provider {provider_phone}")
                return {
                    'success': True,
                    'message': '_Please contact support team for assistance on that.Thank you_'
                }

            elif response_type in ['CN', 'XN', 'AX']:
                # For booking-related actions, check for pending bookings
                logger.debug(f"Finding pending booking for {response_type} from provider {provider_phone}")
                booking = Booking.objects.filter(
                    property__provider=provider,
                    status='pending'
                ).order_by('-created_at').first()

                if not booking:
                    logger.warning(f"No pending booking found for {response_type} from provider {provider_phone}")
                    return {
                        'success': False,
                        'message': 'No pending booking found. Please wait for new booking requests or send "help" for assistance.'
                    }

                if response_type == 'CN':
                    logger.info(f"Processing confirmation for booking {booking.booking_number}")
                    return self._process_provider_confirmation(booking, message)
                elif response_type == 'XN':
                    logger.info(f"Processing rejection for booking {booking.booking_number}")
                    return self._process_provider_rejection(booking, message)
                elif response_type == 'AX':
                    logger.info(f"Processing info request for booking {booking.booking_number}")
                    return self._process_provider_info_request(booking, message)

            elif response_type == 'X':
                logger.info(f"Processing cancel conversation request from provider {provider_phone}")
                return self._handle_provider_cancel_conversation(provider_phone)
            elif response_type == 'PL':
                logger.info(f"Processing property list request from provider {provider_phone}")
                return self._generate_property_list_message(provider)

            elif response_type == 'IS':
                # Insights submission: require property number and parse simple labeled fields
                logger.info(f"Processing insights submission from provider {provider_phone}")

                # Try to find property number in the message (format: 2 letters + hyphen + 4 digits, e.g., AB-1234)
                prop_no = None
                m = re.search(r"\b([A-Za-z]{2}-\d{4})\b", message, re.IGNORECASE)
                if m:
                    prop_no = m.group(1).upper()
                else:
                    # Try common labeled forms like 'property number: AB-1234' or 'property no: AB-1234'
                    m2 = re.search(r"property\s*(?:number|no)[:\-\s]*([A-Za-z]{2}-\d{4})", message_lower)
                    if m2:
                        prop_no = m2.group(1).upper()

                if not prop_no:
                    logger.info(f"Insights message from {provider_phone} missing property number")
                    return {
                        'success': False,
                        'message': "Please include your Property Number (e.g. XZ-1234) in the insights message. Send 'help' for more information on insight format."
                    }

                # Parse labeled fields into insights dict. This parser is deliberately simple
                # and expects lines or segments like 'total rooms: 5' or '1h/room: 2'.
                # Handles bullet points, dashes, and various formatting.
                insights = {}
                slots = {}
                pricing = {}

                # Split by newlines or semicolons to tolerate different message formats
                parts = re.split(r"[\r\n;]+", message)
                for part in parts:
                    if ':' not in part:
                        continue
                    label, val = part.split(':', 1)
                    # Strip bullet points, dashes, and whitespace from label
                    label = re.sub(r'^[\s\-\•\*\#]+', '', label.strip()).lower()
                    val = val.strip()

                    if not val:
                        continue

                    # Match field labels (case-insensitive, flexible whitespace)
                    if label == 'gender preference' or label == 'gender':
                        insights['gender_preference'] = val
                    elif label == 'total rooms' or label == 'total':
                        insights['total_rooms'] = val
                    elif label == 'available rooms' or label == 'available':
                        insights['available_rooms'] = val
                    elif label in ('1h/room', '1h', '1h room'):
                        slots['1h/room'] = val
                    elif label in ('2h/room', '2h', '2h room'):
                        slots['2h/room'] = val
                    elif label in ('3h/room', '3h', '3h room'):
                        slots['3h/room'] = val
                    elif label in ('4h/room', '4h', '4h room'):
                        slots['4h/room'] = val
                    elif label == 'amenities' or label == 'amenity':
                        insights['amenities'] = val
                    elif label in ('price/term', 'price per term', 'price term'):
                        pricing['price/term'] = val
                    elif label in ('price/month', 'price per month', 'price month'):
                        pricing['price/month'] = val
                    elif label in ('price/week', 'price per week', 'price week'):
                        pricing['price/week'] = val
                    elif label in ('price/day', 'price per day', 'price day'):
                        pricing['price/day'] = val

                if slots:
                    insights['available_slots'] = slots
                if pricing:
                    insights['pricing'] = pricing

                # Submit insights via the dedicated handler
                try:
                    res = InsightsHandler.submit_insights(provider_phone=provider_phone, property_no=prop_no, insights=insights)
                    if res.get('success'):
                        updated_fields = res.get('updated_fields', [])
                        try:
                            property_obj = Property.objects.get(property_no=prop_no)
                            property_name = property_obj.name
                        except Property.DoesNotExist:
                            property_name = prop_no  # fallback to property number

                        if updated_fields:
                            updated_list = '\n'.join(f'{i+1}. {field.replace("_", " ")}' for i, field in enumerate(updated_fields))
                            message = f"""*INSIGHTS SUBMITTED*
• Insights submitted successfully for {property_name}

*Updated Insights*
{updated_list}"""
                        else:
                            message = f"""*INSIGHTS SUBMITTED*
- Insights submitted successfully for {property_name}"""

                        return {'success': True, 'message': message}
                    else:
                        return {'success': False, 'message': res.get('message', 'Failed to submit insights.')}
                except Exception as e:
                    logger.error(f"Error submitting insights for provider {provider_phone}: {e}")
                    return {'success': False, 'message': 'Failed to process insights. Please try again later.'}

            else:
                logger.warning(f"Unknown response type for provider {provider_phone}")
                return {
                    'success': False,
                    'message': 'Please reply with YES/NO, ask specific questions, or send "help" for assistance.'
                }

        except AccommodationProvider.DoesNotExist:
            logger.error(f"Provider {provider_phone} not found in system")
            return {
                'success': False,
                'message': 'Provider not found. Please contact support.'
            }
        except Exception as e:
            logger.error(f"Error handling provider response from {provider_phone}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': 'failed  processing provider response. Please try again.'
            }

    def _classify_provider_response(self, message: str) -> str:
        """Classify provider response type using MCP integration"""
        return self._classify_provider_message_with_mcp(message)

    def _process_provider_confirmation(self, booking: Booking, message: str) -> Dict:
        """Process provider confirmation (Step 7 in PDF)"""
        try:
            with transaction.atomic():
                # Prevent UNIQUE constraint violations: ensure there is no other
                # booking already confirmed for the same student and property.
                existing_confirmed = Booking.objects.filter(
                    cell_number=booking.cell_number,
                    property=booking.property,
                    status='confirmed'
                ).exclude(id=booking.id).first()

                if existing_confirmed:
                    logger.warning(
                        f"Attempt to confirm booking {booking.booking_number} but another confirmed "
                        f"booking exists {existing_confirmed.booking_number} for {booking.cell_number}"
                    )
                    return {
                        'success': False,
                        'message': 'Cannot confirm booking: another booking for this student and property is already confirmed.'
                    }

                # Update booking status
                booking.status = 'confirmed'
                booking.confirmed_at = timezone.now()
                booking.provider_response = message
                booking.save()

                # Update property availability
                property = booking.property
                if property.available_rooms > 0: 
                    property.available_rooms -= 1
                    if property.available_rooms == 0:
                        property.is_active = False
                    property.save()

                # Notify student using template
                content_sid = os.getenv('TWILIO_CONTENT_TEMPLATE_SID_STUDENT_CONFIRMATION')
                if not content_sid:
                    logger.error("Student confirmation template SID not configured")
                    return {
                        'success': False,
                        'message': 'Template configuration missing.'
                    }

                # Get student name from conversation context
                from core.models import ConversationState
                conversation = ConversationState.objects.filter(cell_number=booking.cell_number, is_active=True).first()
                student_name = conversation.context_data.get('student_name', booking.cell_number) if conversation else booking.cell_number

                content_variables = {
                    "1": property.name,
                    "2": property.provider.name,
                    "3": property.provider.phone_number,
                    "4": booking.booking_number,
                    "5": student_name,
                    "6": booking.cell_number
                }

                success = self.whatsapp_service.send_template_message(booking.cell_number, content_sid, content_variables)
                if not success:
                    logger.error("Failed to send confirmation message to student")
                    return {
                        'success': False,
                        'message': 'failed to send confirmation to student. Contact support team.'
                    }

                # Reset conversation state to allow new search
                logger.debug(f"Resetting conversation state for student {booking.cell_number}")
                conversation = ConversationState.objects.filter(cell_number=booking.cell_number, is_active=True).first()
                if conversation:
                    conversation.current_step = 'inquiry'
                    conversation.context_data = {}
                    conversation.save()
                    logger.info(f"Conversation state reset to inquiry for student {booking.cell_number}")

                logger.info(f"Booking {booking.booking_number} confirmed by provider")
                return {
                    'success': True,
                    'message': f'Booking confirmed successfully for {student_name} {booking.cell_number}.\n\n• Booking number: *{booking.booking_number}*',
                    'booking_number': booking.booking_number,
                    'student_notified': True,
                    'conversation_reset': True
                }

        except Exception as e:
            logger.error(f"Error processing provider confirmation: {str(e)}")
            return {
                'success': False,
                'message': 'Booking confirmed but failed to send confirmation to the student. Try contacting the student.'
            }

    def _process_provider_rejection(self, booking: Booking, message: str) -> Dict:
        """Process provider rejection with token refund"""
        try:
            with transaction.atomic():
                # Update booking status
                booking.status = 'rejected'
                booking.provider_response = message
                booking.save()

                # Refund token to student
                logger.debug(f"Refunding token for student {booking.cell_number}")
                token_refunded = self._refund_student_token(booking.cell_number)

                # Notify student using template
                content_sid = os.getenv('TWILIO_CONTENT_TEMPLATE_SID_STUDENT_REJECTION')
                if not content_sid:
                    logger.error("Student rejection template SID not configured")
                    return {
                        'success': False,
                        'message': 'Template configuration missing.'
                    }

                # Get student name from conversation context
                from core.models import ConversationState
                conversation = ConversationState.objects.filter(cell_number=booking.cell_number, is_active=True).first()
                student_name = conversation.context_data.get('student_name', booking.cell_number) if conversation else booking.cell_number

                content_variables = {
                    "1": booking.property.name,  # Property name
                    "2": booking.booking_number,  # Booking reference
                    "3": booking.property.provider.name,  # Provider name
                    "4": student_name,  # Student name
                    "5": booking.cell_number  # Student contact
                }

                success = self.whatsapp_service.send_template_message(booking.cell_number, content_sid, content_variables)
                if not success:
                    logger.error("Failed to send rejection message to student")
                    return {
                        'success': False,
                        'message': 'failed sending rejection to student.'
                    }

                # Reset conversation state to allow new search
                logger.debug(f"Resetting conversation state for student {booking.cell_number}")
                conversation = ConversationState.objects.filter(cell_number=booking.cell_number, is_active=True).first()
                if conversation:
                    conversation.current_step = 'inquiry'
                    conversation.context_data = {}
                    conversation.save()
                    logger.info(f"Conversation state reset to inquiry for student {booking.cell_number}")

                logger.info(f"Booking {booking.booking_number} rejected by provider, token refunded: {token_refunded}")
                return {
                    'success': True,
                    'message': f'Booking declined for {student_name} {booking.cell_number}.\n\n• Booking number: *{booking.booking_number}*',
                    'booking_number': booking.booking_number,
                    'student_notified': True,
                    'token_refunded': token_refunded,
                    'conversation_reset': True
                }

        except Exception as e:
            logger.error(f"Error processing provider rejection: {str(e)}")
            return {
                'success': False,
                'message': 'failed processing rejection. Please try again.'
            }

    def _refund_student_token(self, cell_number: str) -> bool:
        """Refund token to student by decrementing used_count"""
        try:
            # Find the most recent active token for the student
            token = Token.objects.filter(
                cell_number=cell_number,
                is_active=True,
                expires_at__gt=timezone.now()
            ).order_by('-purchased_at').first()

            if not token:
                logger.warning(f"No active token found for student {cell_number}")
                return False

            # Check if token has been used (used_count > 0)
            if token.used_count > 0:
                token.used_count -= 1
                token.save()
                logger.info(f"Token refunded for student {cell_number}, new used_count: {token.used_count}")
                return True
            else:
                logger.info(f"Token for student {cell_number} has not been used, no refund needed")
                return False

        except Exception as e:
            logger.error(f"Error refunding token for student {cell_number}: {str(e)}")
            return False

    def _process_provider_info_request(self, booking: Booking, message: str) -> Dict:
        """Process provider information request (Step 6 in PDF)"""
        try:
            # Extract questions from provider message
            questions = self._extract_questions_from_message(message)

            if not questions:
                return {
                    'success': False,
                    'message': 'Could not identify specific questions in your message.'
                }

            # Update booking with info request
            booking.status = 'info_requested'
            booking.additional_info_requested = {
                'questions': questions,
                'provider_message': message,
                'requested_at': timezone.now().isoformat()
            }
            booking.save()

            # Notify student with questions using plain text (template removed)
            questions_text = "\n".join(f"{i}. {q}" for i, q in enumerate(questions, 1))

            text_message = (
                f"Information requested by provider\n\n"
                f"Property: {booking.property.name}\n"
                f"Booking #: {booking.booking_number}\n\n"
                f"Please answer the questions below:\n{questions_text}"
            )

            success = self.whatsapp_service.send_text_message(booking.cell_number, text_message)
            if not success:
                logger.error("Failed to send info request message to student")
                return {
                    'success': False,
                    'message': 'failed sending info request to student.'
                }

            logger.info(f"Information request for booking {booking.booking_number}")
            return {
                'success': True,
                'message': 'Information request forwarded to student.',
                'booking_number': booking.booking_number,
                'questions_count': len(questions),
                'student_notified': True
            }

        except Exception as e:
            logger.error(f"Error processing provider info request: {str(e)}")
            return {
                'success': False,
                'message': 'failed processing information request. Please try again.'
            }

    def _extract_questions_from_message(self, message: str) -> List[str]:
        """Extract specific questions from provider message"""
        questions = []

        # Common question patterns
        question_patterns = [
            r'([A-Z][^.?]*\?)',  # Questions starting with capital letter
            r'(do you[^.?]*\?)',  # Do you... questions
            r'(does the student[^.?]*\?)',  # Does the student... questions
            r'(what[^.?]*\?)',  # What... questions
            r'(which[^.?]*\?)',  # Which... questions
            r'(tell me[^.?]*\?)',  # Tell me... questions
        ]

        for pattern in question_patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            questions.extend([match.strip() for match in matches])

        return list(set(questions))  # Remove duplicates

    def _generate_property_list_message(self, provider: AccommodationProvider) -> Dict:
        """Generate formatted property listings message for provider"""
        try:
            # Get all properties for this provider
            properties = Property.objects.filter(provider=provider).order_by('name')
            
            if not properties.exists():
                return {
                    'success': True,
                    'message': 'You have no properties listed yet. Please submit property insights to add properties.'
                }
            
            # Build the message
            message_parts = ["*YOUR PROPERTY LISTINGS*🏡"]
            
            properties_list = list(properties)
            total_properties = len(properties_list)
            
            for idx, prop in enumerate(properties_list, 1):
                # Property Name
                message_parts.append(f"{idx}. *{prop.name}*")
                
                # Pricing
                message_parts.append(f"• Monthly price: {prop.price_per_month}")
                message_parts.append(f"• Weekly price: {prop.price_per_week}")
                message_parts.append(f"• Daily price: {prop.price_per_day}")
                
                # Room availability by heads
                message_parts.append(f"• 1H/R: {prop.available_1h_rooms} available")
                message_parts.append(f"• 2H/R: {prop.available_2h_rooms} available")
                message_parts.append(f"• 3H/R: {prop.available_3h_rooms} available")
                message_parts.append(f"• 4H/R: {prop.available_4h_rooms} available")
                
                # Total Available Heads
                total_heads = (
                    prop.available_1h_rooms * 1 +
                    prop.available_2h_rooms * 2 +
                    prop.available_3h_rooms * 3 +
                    prop.available_4h_rooms * 4
                )
                total_heads_str = str(total_heads) if total_heads > 0 else "N/A"
                message_parts.append(f"Total Available Heads: {total_heads_str}")
                
                # Distance
                message_parts.append(f"Distance: *{prop.distance_from_campus}km* from campus")
                
                # Amenities
                amenities_list = prop.amenities if prop.amenities and isinstance(prop.amenities, list) else []
                if amenities_list:
                    amenities_str = ", ".join(amenities_list)
                    message_parts.append(f"Amenities: {amenities_str}")
                else:
                    message_parts.append("Amenities: ")
                
                # Add separator between properties (except for last one)
                if idx < total_properties:
                    message_parts.append("")
            
            full_message = "\n".join(message_parts)
            
            logger.info(f"Generated property list for provider {provider.phone_number}: {total_properties} properties")
            return {
                'success': True,
                'message': full_message
            }
            
        except Exception as e:
            logger.error(f"Error generating property list for provider {provider.phone_number}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': 'Failed to retrieve property listings. Please try again later.'
            }

    def send_booking_message_to_provider(self, booking: Booking) -> Dict:
        """Send booking message to provider using content template with text fallback"""
        try:
            # Get student name from conversation state
            conversation = ConversationState.objects.filter(
                cell_number=booking.cell_number,
                is_active=True
            ).first()
            student_name = conversation.context_data.get('student_name', booking.cell_number) if conversation else booking.cell_number

            # Attempt template first
            content_sid = os.getenv('TWILIO_CONTENT_TEMPLATE_SID_PROVIDER_BOOKING')
            if content_sid:
                content_variables = {
                    "1": student_name,
                    "2": booking.cell_number,
                    "3": booking.property.name,
                    "4": booking.booking_number
                }
                if self.whatsapp_service.send_template_message(
                    booking.property.provider.phone_number,
                    content_sid,
                    content_variables
                ):
                    return {
                        'success': True,
                        'message': 'Booking message sent to provider.',
                        'booking_number': booking.booking_number
                    }

            # Fallback to concise text message
            text_message = (
                f"New booking request\n\n"
                f"Property: {booking.property.name}\n"
                f"Student: {student_name} ({booking.cell_number})\n"
                f"Booking #: {booking.booking_number}\n\n"
                f"Reply YES to confirm or NO to decline."
            )

            success = self.whatsapp_service.send_text_message(
                booking.property.provider.phone_number,
                text_message
            )

            if success:
                return {
                    'success': True,
                    'message': 'Booking message sent to provider via fallback.',
                    'booking_number': booking.booking_number
                }
            else:
                return {
                    'success': False,
                    'message': 'failed sending message to provider.'
                }

        except Exception as e:
            logger.error(f"Error sending booking message: {str(e)}")
            return {
                'success': False,
                'message': 'failed sending booking message.'
            }

    def _classify_template_message_with_mcp(self, message: str) -> str:
        """Classify template message as booking request or enquiry using MCP"""
        try:
            if mcp_integration.is_configured():
                # Use MCP for classification
                prompt = f"""
                Classify this WhatsApp template message into exactly ONE category:

                Categories:
                1. Booking request (BR) - Messages requesting confirmation or action on a booking (e.g., "New booking request", "Please confirm", "Reply YES/NO")
                2. Enquiry (E) - Messages asking for information or general inquiries (e.g., "What is", "How does", "Can you explain")

                Message: "{message}"

                Return ONLY a single character: BR or E

                Choose the BEST matching category.
                """

                # Try Gemini first
                if mcp_integration.api_handlers['gemini']:
                    gemini_response = mcp_integration.api_handlers['gemini'].call_api(prompt, max_tokens=10, temperature=0.1)
                    if gemini_response:
                        classification = gemini_response.strip().upper()
                        if classification in ['BR', 'E']:
                            logger.info(f"MCP (Gemini) classified template message as: {classification}")
                            return classification

                # Fallback to Anthropic
                if mcp_integration.api_handlers['anthropic']:
                    anthropic_response = mcp_integration.api_handlers['anthropic'].call_api(prompt, max_tokens=10, temperature=0.1)
                    if anthropic_response:
                        classification = anthropic_response.strip().upper()
                        if classification in ['BR', 'E']:
                            logger.info(f"MCP (Anthropic) classified template message as: {classification}")
                            return classification

            # Fallback to rule-based classification
            return self._classify_template_message_fallback(message)

        except Exception as e:
            logger.error(f"Error classifying template message with MCP: {str(e)}")
            return self._classify_template_message_fallback(message)

    def _classify_template_message_fallback(self, message: str) -> str:
        """Fallback rule-based classification for template messages"""
        if not message:
            return 'E'  # Default to enquiry

        message_lower = message.lower().strip()

        # Booking request keywords
        booking_keywords = [
            'booking request', 'new booking', 'please confirm', 'reply yes', 'reply no',
            'confirm', 'decline', 'accept', 'reject', 'booking number', 'student name',
            'property name', 'accommodation request'
        ]

        # Enquiry keywords
        enquiry_keywords = [
            'what is', 'how does', 'can you explain', 'information', 'help', 'guide',
            'instructions', 'status', 'update', 'change'
        ]

        if any(keyword in message_lower for keyword in booking_keywords):
            return 'BR'
        elif any(keyword in message_lower for keyword in enquiry_keywords):
            return 'E'
        else:
            return 'BR'  # Default to booking request for template messages

    def _handle_provider_cancel_conversation(self, provider_phone: str) -> Dict:
        """Handle provider cancel conversation request"""
        try:
            logger.info(f"Provider {provider_phone} requested conversation cancellation")

            # Find most recent pending booking for this provider
            booking = Booking.objects.filter(
                property__provider__phone_number=provider_phone,
                status='pending'
            ).order_by('-created_at').first()

            if not booking:
                logger.warning(f"No pending booking found to cancel conversation for provider {provider_phone}")
                return {
                    'success': True,
                    'message': 'No active conversation found to cancel. You can start fresh anytime.'
                }

            # Terminate the student's conversation state
            conversation = ConversationState.objects.filter(cell_number=booking.cell_number, is_active=True).first()
            if conversation:
                conversation.is_active = False
                conversation.current_step = 'inquiry'
                conversation.context_data = {}
                conversation.save()
                logger.info(f"Conversation terminated for student {booking.cell_number} by provider request")
                return {
                    'success': True,
                    'message': 'Conversation cancelled successfully. The student can start a new search anytime.'
                }
            else:
                logger.warning(f"No active conversation state found for student {booking.cell_number}")
                return {
                    'success': True,
                    'message': 'No active conversation found to cancel.'
                }

        except Exception as e:
            logger.error(f"Error handling provider cancel conversation: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to cancel conversation. Please try again.'
            }

    def _generate_jeff_about_message_for_provider(self) -> Dict:
        """Generate Jeff about message for providers"""
        try:
            # Read the about message from the markdown file
            file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'privacy', 'privacy_whatsapp.md')

            with open(file_path, 'r', encoding='utf-8') as f:
                about_content = f.read()

            # Get PDF URL from settings
            from django.conf import settings
            privacy_policy_url = settings.JEFF_SETTINGS.get('PRIVACY_POLICY_URL')

            # Add provider-specific information
            provider_message = about_content + f"\n\nRead the Terms & full Privacy Policy on {privacy_policy_url}."

            return {
                'success': True,
                'message': provider_message
            }
        except FileNotFoundError:
            logger.error("jeff_about.md file not found for provider.")
            return {
                'success': False,
                'message': "Sorry, I couldn't retrieve the information at the moment. Contact support team"
            }
        except Exception as e:
            logger.error(f"Error reading jeff_about.md file for provider: {e}")
            return {
                'success': False,
                'message': "Sorry, an error occurred while retrieving the information."
            }

# Global instance for easy import
provider_handlers = ProviderHandlers()
