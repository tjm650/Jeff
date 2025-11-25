"""
Message Classification for MCP Integration

This module handles message classification into G/A/H/P categories
with fallback mechanisms and rule-based classification.
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MessageClassifier:
    """Handles message classification with AI and fallback methods"""

    def __init__(self):
        # Greeting patterns (restrictive to avoid requirement-like content)
        self.greeting_patterns = [
            r'^(hi|hello|hey|good\s+(morning|afternoon|evening)|greetings|howdy|welcome|sup|yo)\b',
            r'^(hi|hello|hey)\s+(there|jeff|bot|agent)',
            r'^jeff\s+(hi|hello|hey)',
            r'^(good|nice|great|pleased)\s+to\s+meet\s+you',
            r'^(good|nice|hello|hi|hey)\s+(morning|afternoon|evening)',
            r'^how\s+(are\s+you|do\s+you\s+do|is\s+it\s+going)',
            r'^(thanks|thank\s+you)\s+(for\s+)?help',
            r'^(can\s+you\s+)?assist\s+me$',
            r'^start|begin|get\s+started$',
        ]

        # Simple greetings for fallback
        self.simple_greetings = [
            'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
            'greetings', 'howdy', 'welcome', 'sup', 'yo', 'start', 'begin',
            'thanks', 'thank you', 'how are you', 'how do you do',
            'nice to meet you', 'good to meet you', 'ready to start'
        ]

    def classify_with_fallback(self, message: str) -> str:
        """Fallback rule-based classification"""
        if not message:
            return 'A'

        message_lower = message.lower().strip()

        # Check for payment messages first
        if re.search(r'(USD|ZWL)\s+PAY\s+[0-9]+', message_lower) or '0717718865' in message_lower or 'payment' in message_lower:
            return 'P'

        # Check for help messages
        if 'help' in message_lower or 'assist' in message_lower or 'how' in message_lower:
            return 'H'

        # Check for abort messages
        if message_lower in ['abort', 'restart', 'start over', 'cancel', 'x']:
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

        # Check for accommodation enquiry (requirement-like content)
        if self._has_requirement_content(message_lower):
            return 'A'

        # Check for greeting messages
        if self.is_greeting_message(message_lower):
            return 'G'

        return 'A'  # Default to accommodation enquiry

    def is_greeting_message(self, message: str) -> bool:
        """Check if message is a greeting"""
        message_lower = message.lower().strip()

        # First check if message contains requirement-like content
        if self._has_requirement_content(message_lower):
            return False

        # Check against greeting patterns
        for pattern in self.greeting_patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return True

        # Simple greetings
        return any(greeting in message_lower for greeting in self.simple_greetings)

    def _has_requirement_content(self, message: str) -> bool:
        """Check if message contains accommodation requirement content"""
        # Check for specific numbers (likely head count or budget)
        number_patterns = [
            r'\b\d+\s*(?:heads?|bedrooms?|beds?|people?|person|sharing|room)\b',
            r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?',
            r'\b\d+\s*(?:km|miles?|minutes?)\s+(?:from|to|away)',
            r'\b\d+\s*(?:dollars?|usd|us)\b'
        ]

        for pattern in number_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True

        # Check for location-specific terms with context
        location_with_context = [
            'near campus', 'close to campus', 'walking distance to campus',
            'less than', 'within', 'under', 'for $'
        ]

        for term in location_with_context:
            if term in message:
                return True

        return False

    def classify_with_ai(self, message: str, gemini_handler, anthropic_handler, categories: List[str] = ['G', 'A', 'H', 'P', 'S', 'N', 'X', 'J']) -> str:
        """
        Classify message using AI with fallback to rule-based classification

        Args:
            message (str): The message to classify
            gemini_handler: Gemini API handler instance
            anthropic_handler: Anthropic API handler instance
            categories (List[str]): List of possible classification categories

        Returns:
            str: Single character classification key
        """
        logger.info(f"Classifying message with AI: '{message[:50]}{'...' if len(message) > 50 else ''}'")

        # First try rule-based classification for obvious cases
        fallback_classification = self.classify_with_fallback(message)
        if fallback_classification in categories and fallback_classification != 'A':  # If not default accommodation enquiry
            return fallback_classification

        category_map = {
            'G': 'Greeting message - Simple greetings like "hi", "hello", "good morning", introductions',
            'A': 'Accommodation enquiry message - Messages asking about accommodation, rooms, housing',
            'H': 'Help message - Messages asking for help, assistance, or information',
            'P': 'Payment message - Messages like "USD PAY number" or "ZWL PAY number"',
            'X': 'Cancel message - Messages like "x", "abort", "restart", "start over", "cancel" (universal cancel command)',
            'S': 'Property selection message - Messages selecting a property like "option-1", "option-2"',
            'N': 'Name collection message - Messages providing name like "name-John", "name-Mary"',
            'J': 'Jeff message - Messages that are exactly "Jeff" or "j"'
        }

        prompt_categories = "\n".join([f"{i+1}. {category_map[cat]}" for i, cat in enumerate(categories)])
        prompt_return_chars = ", ".join(categories)

        # Try Gemini first for complex classification
        if gemini_handler and gemini_handler.model:
            prompt = f"""
            Classify this WhatsApp message into exactly ONE category:

            Categories:
            {prompt_categories}

            Message: "{message}"

            Note: Messages containing 'confirm' or 'cn' are not abort messages.
            Messages containing 'x' are ALWAYS cancel messages (X), just like "G", "H", etc.

            Note: Messages containing 'x' are ALWAYS cancel messages (X), just like "G", "H", etc.

            Return ONLY a single character from: {prompt_return_chars}

            Choose the BEST matching category.
            """

            gemini_response = gemini_handler.call_api(prompt, max_tokens=10, temperature=0.1)
            if gemini_response:
                classification = gemini_response.strip().upper()
                if classification in categories:
                    logger.info(f"Gemini classified message as: {classification}")
                    return classification

        # Fallback to Anthropic
        if anthropic_handler and anthropic_handler.client:
            prompt = f"""
            Classify this WhatsApp message into exactly ONE category:

            Categories:
            {prompt_categories}

            Message: "{message}"

            Note: Messages containing 'confirm' or 'cn' are not abort messages.

            Return ONLY a single character from: {prompt_return_chars}

            Choose the BEST matching category.
            """

            anthropic_response = anthropic_handler.call_api(prompt, max_tokens=10, temperature=0.1)
            if anthropic_response:
                classification = anthropic_response.strip().upper()
                if classification in categories:
                    logger.info(f"Anthropic (fallback) classified message as: {classification}")
                    return classification

        # Final fallback to rule-based classification
        logger.warning("Both APIs failed, using rule-based classification")
        return self.classify_with_fallback(message)