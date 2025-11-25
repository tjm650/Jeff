import re
import logging
import random
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class GreetingHandler:
    def get_time_based_greeting(self) -> str:
        from datetime import datetime
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "Good morning"
        elif 12 <= hour < 18:
            return "Good afternoon"
        else:
            return "Good evening"
    def __init__(self):
        self.greeting_patterns = [
            r'^(hi|hello|hey|good\s+(morning|afternoon|evening)|greetings|howdy|welcome|sup|yo)\b',
            r'^(hi|hello|hey)\s+(there|jeff|bot|assistant)',
            r'^jeff\s+(hi|hello|hey)',
            r'^(good|nice|great|pleased)\s+to\s+meet\s+you',
            r'^(good|nice|hello|hi|hey)\s+(morning|afternoon|evening)',
            r'^how\s+(are\s+you|do\s+you\s+do|is\s+it\s+going)',
            r'^(thanks|thank\s+you)\s+(for\s+)?help',
            r'^(can\s+you\s+)?assist\s+me$',
            r'^start|begin|get\s+started$',
        ]

    def is_greeting_message(self, message: str) -> bool:
        message_lower = message.lower().strip()

        if self._has_requirement_content(message_lower):
            return False

        for pattern in self.greeting_patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return True

        simple_greetings = [
            'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
            'greetings', 'howdy', 'welcome', 'sup', 'yo', 'start', 'begin',
            'thanks', 'thank you', 'how are you', 'how do you do',
            'nice to meet you', 'good to meet you', 'ready to start'
        ]

        return any(greeting in message_lower for greeting in simple_greetings)

    def _has_requirement_content(self, message: str) -> bool:
        number_patterns = [
            r'\b\d+\s*(?:heads?|bedrooms?|beds?|people?|person|sharing|room)\b',
            r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?',
            r'\b\d+\s*(?:km|miles?|minutes?)\s+(?:from|to|away)',
            r'\b\d+\s*(?:dollars?|usd|us)\b'
        ]

        for pattern in number_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True

        location_with_context = [
            'near campus', 'close to campus', 'walking distance to campus',
            'less than', 'within', 'under', 'for $'
        ]

        for term in location_with_context:
            if term in message:
                return True

        return False

    def _generate_greeting_response(self, message: str) -> str:
        return self._get_fallback_greeting_response()

    def _get_fallback_greeting_response(self) -> str:
        fallback_responses = [
            """*Hi, I'm Jeff*👋.
I help students at NUST find accommodation near campus. If you see this message, I'm offline.
Please try again later or contact support for assistance."""
            ]



        return random.choice(fallback_responses)

    def is_greeting_response(self, requirements: Dict) -> bool:
        """Check if the requirements result is a greeting response"""
        return requirements.get('is_greeting', False)

    def get_greeting_response(self, requirements: Dict) -> str:
        """Get the greeting response text if this is a greeting"""
        if self.is_greeting_response(requirements):
            return requirements.get('response', self._get_fallback_greeting_response())
        return None
    
    
    
#     """I help students at NUST to find recommended places to stay near campus.

# Just tell me what you're looking for. For example:
# • _"I need a 2-head room with WiFi for $200"_
# • _"Looking for single room near campus"_
# • _"Double room with parking, max $150"_

# I can help you find accommodation based on:
# • Number of people (heads)
# • Budget per month
# • Required amenities (WiFi, parking, etc.)
# • Location preferences
# • Gender preferences

# Send me your requirements and I'll find matching properties for you!""",
#             """*Hi, I'm Jeff👋*

# I help students at NUST find accommodation near campus.

# Tell me what you're looking for, like:
# _"I need a 2-head room with WiFi for $200 near campus"_ """
