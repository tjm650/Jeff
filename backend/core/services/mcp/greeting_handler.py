"""
Greeting Handler for MCP Integration

This module handles greeting detection and response generation
with AI-powered contextual responses.
"""

import logging
import re
from typing import Dict, Optional
from django.utils import timezone
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)


class GreetingHandler:
    """Handles greeting detection and response generation"""

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

    def generate_greeting_response(self, message: str, gemini_handler, anthropic_handler) -> str:
        """Generate greeting response using AI with fallback"""
        # Get current time of day greeting
        time_greeting = self._get_time_of_day_greeting()
        
        # Try Gemini first
        if gemini_handler and gemini_handler.model:
            prompt = f"""
            You are Jeff, an agent for accommodation. Generate a greeting response for WhatsApp.
            Current time greeting to use: {time_greeting}

            User said: "{message}"

            Response should:
            1. Be friendly, formal and concise in continous form
            2. Include time of day appropriate greeting, eg; "Good morning", "Good afternoon", "Good evening"
            3. Explain that Jeff helps find accommodation near campus
            4. Guide user to provide requirements to start search
            5. Ask what they're looking for
            6. Mention user to send a _'help'_ message for more information including payment instructions.
            7. Mention user to send a 'Jeff' for more infomation about the service, Privacy Policy and Terms & Conditions of service.
            
            

            Return only the response text, no JSON.
            """

            response = gemini_handler.call_api(prompt, max_tokens=250, temperature=0.7)
            if response:
                logger.info("Gemini greeting response generated successfully")
                return self._prepend_time_of_day_greeting(response)

        # Fallback to Anthropic
        if anthropic_handler and anthropic_handler.client:
            prompt = f"""
            You are Jeff, an agent for NUST students looking for recommended accommodation. Generate a friendly, helpful greeting response for WhatsApp based on the user's greeting message.
            Current time greeting to use: {time_greeting}

            User said: "{message}"

            Response should:
            
             1. Be friendly and formal
            2. Include time of day appropriate greeting, eg "Good morning", "Good afternoon", "Good evening"
            2. Explain that Jeff helps find accommodation near campus
            3. Mention user to send a 'Jeff' for more infomation about the service, Privacy Policy and Terms & Conditions of service.
            4. Mention user to send a _'help'_ message for more information including payment instructions.
            
            
            1. Be friendly and welcoming
            2. Explain that Jeff helps find accommodation near campus
            3. Explain how you can help find accommodation based on(no emojis):
            • Number of people (heads)
            • Budget per month or budget range or budget per day
            • Required amenities (WiFi, parking, etc.)
            • Location preferences
            • Gender preferences
            • any addistional relevant info
            4. Guide user to provide requirements to start search:
            5. Ask what they're looking for
            6. Keep it concise for WhatsApp
            7. Use markdown formatting for WhatsApp bold, bullet(•), italic and lists
            8. Mention the token is $1.00 to review accommodation listings
            9. Mention user to send a _'help'_ message for more information including payment instructions.

            Return only the response text, no JSON.
            """

            response = anthropic_handler.call_api(prompt, max_tokens=250, temperature=0.7)
            if response:
                logger.info("Anthropic greeting response generated successfully")
                return self._prepend_time_of_day_greeting(response)

        # Final fallback
        logger.warning("Both APIs failed for greeting, using static response")
        return self._prepend_time_of_day_greeting(self._get_fallback_greeting_response())

    def _get_fallback_greeting_response(self) -> str:
        """Static fallback greeting response with time-of-day greeting prepended"""
        time_greeting = self._get_time_of_day_greeting()
        response = (
            "I'm Jeff, your accommodation agent. I connect NUST students with accommodation providers and my goal is to make accommodation hunt simpler and more efficient for students. Just tell me what you're looking for. For example: _\"I need a 2-head room with WiFi for $200\"_\n\n"
            "• Send 'help' for detailed instructions including insight sharing and managing your property listings.\n"
            "• Send 'Jeff' for more information about the service, Privacy Policy and Terms & Conditions.\n"
        )
        return f"{time_greeting}, {response}"

    def is_greeting_response(self, requirements: Dict) -> bool:
        """Check if the requirements result is a greeting response"""
        return requirements.get('is_greeting', False)

    def get_greeting_response(self, requirements: Dict) -> str:
        """Get the greeting response text if this is a greeting"""
        if self.is_greeting_response(requirements):
            # Ensure time-of-day greeting is included even if upstream provided raw text
            raw = requirements.get('response', self._get_fallback_greeting_response())
            return self._prepend_time_of_day_greeting(raw)
        return None

    def _get_time_of_day_greeting(self) -> str:
        """Return a time-of-day appropriate greeting using CAT timezone (Africa/Harare)."""
        try:
            cat_tz = pytz.timezone('Africa/Harare')
            now_cat = timezone.now().astimezone(cat_tz)
            hour = now_cat.hour
        except Exception:
            # Final fallback: assume UTC and treat as-is
            hour = timezone.now().hour

        if hour >= 0 and hour < 12:
            return "Good morning"
        elif hour >= 12 and hour < 18:
            return "Good afternoon"
        else:  # hour >= 18 and hour < 24
            return "Good evening"

    def _prepend_time_of_day_greeting(self, text: str) -> str:
        """Prepend a time-of-day greeting if not already present."""
        prefix = self._get_time_of_day_greeting()
        normalized = text.lstrip()
        # Avoid duplicating if response already starts with a time-based greeting
        if normalized.lower().startswith(("good morning", "good afternoon", "good evening", "hello")):
            return text
        return f"{prefix}, {text}"