"""
Message classification and routing handlers

This module handles message classification and routing including:
- Message classification using MCP integration (Anthropic/Gemini)
- Fallback classification when AI is unavailable
- Greeting message handling
- Payment message detection
- Help message detection
"""

import logging
import re

logger = logging.getLogger(__name__)


class MessageClassifier:
    """Message classification and routing functionality"""

    def classify_message_with_gemini(self, message: str) -> str:
        """
        Classify message using MCP integration (Anthropic primary, Gemini fallback)

        Args:
            message (str): The message to classify

        Returns:
            str: Single character classification key:
                - 'G' for Greeting message
                - 'A' for Accommodation enquiry message
                - 'H' for Help message
                - 'P' for Payment message
                - 'J' for Jeff message
        """
        try:
            # Pre-check for provider confirm/decline messages to avoid AI misclassification
            message_lower = message.lower().strip()
            if 'confirm' in message_lower or 'accept' in message_lower:
                logger.info(f"Pre-classified provider confirmation message as 'CN': {message}")
                return 'CN'
            elif 'decline' in message_lower or 'reject' in message_lower:
                logger.info(f"Pre-classified provider declining message as 'XN': {message}")
                return 'XN'

            # Try MCP integration first (Anthropic with Gemini fallback)
            from ..mcp import mcp_integration
            if mcp_integration.is_configured():
                return mcp_integration.classify_message(message, categories=['G', 'A', 'H', 'P', 'J'])
            else:
                # Fallback to existing NLP processor
                logger.warning("MCP integration not configured, using existing NLP processor")
                from ....matching.nlp_processor import nlp_processor
                return nlp_processor.classify_message(message)
        except Exception as e:
            logger.error(f"Error classifying message with MCP integration: {str(e)}")
            # Fallback to simple rule-based classification
            return self._classify_message_fallback(message)

    def _classify_message_fallback(self, message: str) -> str:
        """Fallback classification when Gemini is unavailable"""
        if not message:
            return 'A'  # Default to accommodation enquiry

        message_lower = message.lower().strip()

        if message_lower == 'jeff' or message_lower == 'j':
            return 'J'

        # Check for payment messages first (most specific)
        if re.search(r'(USD|ZWL)\s+PAY\s+[0-9]+', message_lower) or '0717718865' in message_lower or 'payment' in message_lower:
            return 'P'

        # Check for help messages
        if 'help' in message_lower or 'assist' in message_lower or 'how' in message_lower:
            return 'H'

        # Check for abort messages
        if message_lower in ['abort', 'restart', 'start over', 'cancel']:
            return 'X'  # X for Abort/Restart

        # Check for confirm messages (not abort)
        if 'Confirm' in message_lower or 'cn' in message_lower:
            return 'A'  # Default to accommodation enquiry

        # Check for property selection messages (option-1, option-2, etc.)
        if re.match(r'option-\d+$', message_lower):
            return 'S'  # S for Selection

        # Check for name collection messages (name-...)
        if message_lower.startswith('name-'):
            return 'N'  # N for Name

        # Check for greeting messages
        simple_greetings = [
            'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
            'greetings', 'howdy', 'welcome', 'sup', 'yo', 'start', 'begin',
            'thanks', 'thank you', 'how are you', 'how do you do',
            'nice to meet you', 'good to meet you', 'ready to start'
        ]

        if any(greeting in message_lower for greeting in simple_greetings):
            return 'G'

        # Default to accommodation enquiry
        return 'A'

    def handle_payment_classification(self, message: str) -> str:
        """Handle payment messages directly"""
        try:
            # For payment classification, we need to handle it differently since we don't have cell_number in this context
            # Return payment instructions that will be processed by the normal workflow
            return """*PAYMENT REQUEST*"""

        except Exception as e:
            logger.error(f"Error handling payment classification: {str(e)}")
            return """*PAYMENT REQUEST*"""

    def handle_greeting_classification(self, cell_number: str, message: str) -> str:
        """Handle greeting messages with enhanced greeting flow"""
        try:
            # Get conversation state
            from ...models import ConversationState
            conversation = ConversationState.objects.filter(
                cell_number=cell_number,
                is_active=True
            ).first()

            if not conversation:
                # Create new conversation state
                conversation = ConversationState.objects.create(
                    cell_number=cell_number,
                    current_step='inquiry',
                    is_active=True
                )

            # Use enhanced greeting flow with MCP integration
            from ..mcp import mcp_integration
            if mcp_integration.is_configured():
                # Create mock nlp_processor for backward compatibility
                class MockNLPProcessor:
                    def extract_requirements(self, msg): return mcp_integration.extract_requirements(msg)
                    def is_greeting_message(self, msg): return mcp_integration.is_greeting_message(msg)
                    def is_greeting_response(self, reqs): return mcp_integration.is_greeting_response(reqs)
                    def get_greeting_response(self, reqs): return mcp_integration.get_greeting_response(reqs)
                    def _generate_greeting_response(self, msg): return mcp_integration._generate_greeting_response(msg)
                    def _get_fallback_greeting_response(self): return mcp_integration._get_fallback_greeting_response()

                nlp_processor = MockNLPProcessor()
                return self._handle_greeting_flow(conversation, message, nlp_processor)
            else:
                # Fallback to existing NLP processor
                from ....matching.nlp_processor import nlp_processor
                return self._handle_greeting_flow(conversation, message, nlp_processor)

        except Exception as e:
            logger.error(f"Error handling greeting classification: {str(e)}")
            # Fallback to simple greeting response
            return """*Hi, I'm Jeff👋* I help students at NUST find accommodation near campus."""

    def _handle_greeting_flow(self, conversation, message: str, nlp_processor) -> str:
        """Handle greeting flow with enhanced response generation"""
        try:
            # Extract requirements to check if it's a pure greeting
            from ..mcp import mcp_integration
            if mcp_integration.is_configured():
                requirements = mcp_integration.extract_requirements(message)
            else:
                requirements = nlp_processor.extract_requirements(message)

            # Get greeting response using MCP integration or NLP processor's sophisticated response generation
            greeting_response = self._get_enhanced_greeting_response(message, nlp_processor)

            # Store greeting context for better conversation flow
            conversation.context_data = {
                'is_greeting': True,
                'original_message': message,
                'greeting_detected': True,
                'requirements_extracted': requirements if requirements else {}
            }

            # Stay in inquiry step after greeting - don't move to token check
            # Users should be able to send greetings and then continue with requirements
            conversation.current_step = 'inquiry'
            conversation.save()

            logger.info(f"Greeting flow completed for {conversation.cell_number}")
            return greeting_response

        except Exception as e:
            logger.error(f"Error in greeting flow: {str(e)}")
            # Fallback to simple help message if greeting handling fails
            return self._get_help_message()

    def _get_enhanced_greeting_response(self, message: str, nlp_processor) -> str:
        """Get enhanced greeting response with fallback handling"""
        try:
            # Try MCP integration first for greeting response
            from ..mcp import mcp_integration
            if mcp_integration.is_configured():
                requirements = mcp_integration.extract_requirements(message)
                if mcp_integration.is_greeting_response(requirements):
                    response = mcp_integration.get_greeting_response(requirements)
                    if response:
                        return response

            # Try to get response from NLP processor
            requirements = nlp_processor.extract_requirements(message)

            if nlp_processor.is_greeting_response(requirements or {}):
                response = nlp_processor.get_greeting_response(requirements)
                if response:
                    return response

            # If NLP processor fails, try direct LLM generation
            try:
                direct_response = nlp_processor._generate_greeting_response(message)
                if direct_response:
                    # logger.info(f"Greeting response: {direct_response}")
                    return direct_response
            except Exception as e:
                logger.warning(f"Direct greeting generation failed: {str(e)}")

            # Final fallback to simple greeting
            return nlp_processor._get_fallback_greeting_response()

        except Exception as e:
            logger.error(f"Error getting enhanced greeting response: {str(e)}")
            # Use the same fallback responses as the NLP processor for consistency
            fallback_responses = [
               """*Hi, I'm Jeff👋*, I help students at NUST find accommodation near campus. Tell me what you're looking for, like:
• _"I need a 2-head room with WiFi for $200 near campus"_ """
            ]

            import random
            return random.choice(fallback_responses)

    def _get_help_message(self) -> str:
        """Get enhanced help message using NLP processor capabilities"""
        try:
            from ....matching.nlp_processor import nlp_processor
            return nlp_processor._get_help_message()
        except Exception as e:
            logger.error(f"Error getting help message: {str(e)}")
            return "Hi, I'm Jeff👋. I help students at NUST find accommodation near campus. Send 'help' for more information."

    def is_payment_request(self, message: str) -> bool:
        """Check if message is a payment request"""
        if not message:
            return False

        message_lower = message.lower().strip()
        return bool(re.search(r'(USD|ZWL)\s+PAY\s+[0-9]+', message_lower)) or '0717718865' in message_lower

    def is_help_message(self, message: str) -> bool:
        """Check if message is a help request"""
        if not message:
            return False

        message_lower = message.lower().strip()

        # Direct help keywords
        help_keywords = [
            'help', 'help me', 'i need help', 'assist', 'assistance',
            'how to', 'what can you do', 'guide', 'instructions',
            'support', 'info', 'information'
        ]

        return any(keyword in message_lower for keyword in help_keywords)


# Global instance
message_classifier = MessageClassifier()