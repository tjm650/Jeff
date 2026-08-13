"""Message classification and routing handlers for Jeff's free accommodation workflow."""

import logging
import re

logger = logging.getLogger(__name__)


class MessageClassifier:
    """Classify messages for accommodation search, help, greetings and booking."""

    def classify_message_with_gemini(self, message: str) -> str:
        try:
            message_lower = message.lower().strip()
            if 'confirm' in message_lower or 'accept' in message_lower:
                return 'CN'
            if 'decline' in message_lower or 'reject' in message_lower:
                return 'XN'

            from ..mcp import mcp_integration
            if mcp_integration.is_configured():
                return mcp_integration.classify_message(message, categories=['G', 'A', 'H', 'J'])

            from matching.nlp_processor import nlp_processor
            return nlp_processor.classify_message(message)
        except Exception as exc:
            logger.error("Error classifying message: %s", exc)
            return self._classify_message_fallback(message)

    def _classify_message_fallback(self, message: str) -> str:
        if not message:
            return 'A'

        message_lower = message.lower().strip()
        if message_lower in ('jeff', 'j'):
            return 'J'
        if any(word in message_lower for word in ('help', 'assist', 'how')):
            return 'H'
        if message_lower in ('abort', 'restart', 'start over', 'cancel'):
            return 'X'
        if re.match(r'option-\d+$', message_lower):
            return 'S'
        if message_lower.startswith('name-'):
            return 'N'

        greetings = [
            'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
            'greetings', 'howdy', 'welcome', 'sup', 'yo', 'start', 'begin',
            'thanks', 'thank you', 'how are you', 'how do you do',
            'nice to meet you', 'good to meet you', 'ready to start'
        ]
        if any(greeting in message_lower for greeting in greetings):
            return 'G'
        return 'A'

    def handle_greeting_classification(self, cell_number: str, message: str) -> str:
        try:
            from core.models import ConversationState
            conversation = ConversationState.objects.filter(cell_number=cell_number, is_active=True).first()
            if not conversation:
                conversation = ConversationState.objects.create(
                    cell_number=cell_number,
                    current_step='inquiry',
                    is_active=True,
                )

            from ..mcp import mcp_integration
            if mcp_integration.is_configured():
                class MockNLPProcessor:
                    def extract_requirements(self, msg): return mcp_integration.extract_requirements(msg)
                    def is_greeting_message(self, msg): return mcp_integration.is_greeting_message(msg)
                    def is_greeting_response(self, reqs): return mcp_integration.is_greeting_response(reqs)
                    def get_greeting_response(self, reqs): return mcp_integration.get_greeting_response(reqs)
                    def _generate_greeting_response(self, msg): return mcp_integration._generate_greeting_response(msg)
                    def _get_fallback_greeting_response(self): return mcp_integration._get_fallback_greeting_response()
                nlp_processor = MockNLPProcessor()
            else:
                from matching.nlp_processor import nlp_processor
            return self._handle_greeting_flow(conversation, message, nlp_processor)
        except Exception as exc:
            logger.error("Error handling greeting classification: %s", exc)
            return "*Hi, I'm Jeff👋* I help students find accommodation. Tell me what you're looking for."

    def _handle_greeting_flow(self, conversation, message: str, nlp_processor) -> str:
        try:
            from ..mcp import mcp_integration
            requirements = mcp_integration.extract_requirements(message) if mcp_integration.is_configured() else nlp_processor.extract_requirements(message)
            greeting_response = self._get_enhanced_greeting_response(message, nlp_processor)
            conversation.context_data = {
                'is_greeting': True,
                'original_message': message,
                'greeting_detected': True,
                'requirements_extracted': requirements if requirements else {},
            }
            conversation.current_step = 'inquiry'
            conversation.save()
            return greeting_response
        except Exception as exc:
            logger.error("Error in greeting flow: %s", exc)
            return self._get_help_message()

    def _get_enhanced_greeting_response(self, message: str, nlp_processor) -> str:
        try:
            from ..mcp import mcp_integration
            if mcp_integration.is_configured():
                requirements = mcp_integration.extract_requirements(message)
                if mcp_integration.is_greeting_response(requirements):
                    response = mcp_integration.get_greeting_response(requirements)
                    if response:
                        return response

            requirements = nlp_processor.extract_requirements(message)
            if nlp_processor.is_greeting_response(requirements or {}):
                response = nlp_processor.get_greeting_response(requirements)
                if response:
                    return response
            try:
                response = nlp_processor._generate_greeting_response(message)
                if response:
                    return response
            except Exception as exc:
                logger.warning("Direct greeting generation failed: %s", exc)
            return nlp_processor._get_fallback_greeting_response()
        except Exception as exc:
            logger.error("Error getting greeting response: %s", exc)
            return "*Hi, I'm Jeff👋* I help students find accommodation. Tell me what you're looking for."

    def _get_help_message(self) -> str:
        try:
            from matching.nlp_processor import nlp_processor
            return nlp_processor._get_help_message()
        except Exception as exc:
            logger.error("Error getting help message: %s", exc)
            return "Hi, I'm Jeff👋. I help students find accommodation. Send 'help' for more information."

    def is_help_message(self, message: str) -> bool:
        if not message:
            return False
        message_lower = message.lower().strip()
        help_keywords = ['help', 'help me', 'i need help', 'assist', 'assistance', 'how to', 'what can you do', 'guide', 'instructions', 'support', 'info', 'information']
        return any(keyword in message_lower for keyword in help_keywords)


message_classifier = MessageClassifier()
