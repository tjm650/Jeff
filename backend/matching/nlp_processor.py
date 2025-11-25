import re
import openai
import google.generativeai as genai
from typing import Dict, List, Optional
from fuzzywuzzy import process, fuzz
import os
import logging
import json
import time
from collections import defaultdict
from .greeting_handler import GreetingHandler
from .requirement_extractor import RequirementExtractor
from .ai_enhancer import AIEnhancer
from .nlp_classifier import NLPClassifier

logger = logging.getLogger(__name__)

class DjangoNLPProcessor:
    """Django-compatible NLP processor for extracting accommodation requirements"""

    def __init__(self):
        """Initialize the NLP processor"""
        self.greeting_handler = GreetingHandler()
        self.extractor = RequirementExtractor()
        self.ai_enhancer = AIEnhancer()
        self.classifier = NLPClassifier()

        # Log API key status for debugging
        logger.info(f"OpenAI API Key received: {self.ai_enhancer.openai_api_key is not None and len(self.ai_enhancer.openai_api_key) > 0}")
        logger.info(f"Gemini API Key received: {self.ai_enhancer.gemini_api_key is not None and len(self.ai_enhancer.gemini_api_key) > 0}")

        # Initialize keyword dictionaries (same as original implementation)
        self.location_keywords = {
            'near': 'near', 'close': 'near', 'walking distance': 'near',
            'far': 'far', 'distant': 'far',
            'campus': 'campus', 'university': 'campus', 'school': 'campus',
            'town': 'town', 'city': 'town', 'center': 'town',
            'mall': 'mall', 'shopping': 'mall',
            'hospital': 'hospital', 'clinic': 'hospital'
        }

    def is_greeting_message(self, message: str) -> bool:
        """Check if message is a greeting or introduction"""
        return self.greeting_handler.is_greeting_message(message)


    def extract_requirements(self, message: str) -> Dict:
        """
        Extract structured requirements from natural language message

        Args:
            message (str): The WhatsApp message from student

        Returns:
            Dict: Structured requirements with keys like heads, amenities, budget_max, etc.
                  For greetings, returns a special response with 'is_greeting' flag.
        """
        message = message.lower().strip()

        if self.is_greeting_message(message):
            comprehensive_response = self._generate_greeting_response(message)
            return {
                'is_greeting': True,
                'response': comprehensive_response,
                'raw_message': message
            }

        requirements = {
            'heads': None,
            'amenities': [],
            'budget_max': None,
            'distance_preference': None,
            'location_context': None,
            'gender_preference': None,
            'urgency': None,
            'raw_message': message
        }

        requirements['heads'] = self.extractor._extract_heads_count(message)
        requirements['amenities'] = self.extractor._extract_amenities(message)
        requirements['budget_max'] = self.extractor._extract_budget(message)
        requirements['distance_preference'], requirements['location_context'] = self.extractor._extract_location(message)
        requirements['gender_preference'] = self.extractor._extract_gender_preference(message)
        requirements['urgency'] = self.extractor._extract_urgency(message)

        if self.ai_enhancer.gemini_api_key:
            try:
                requirements = self.ai_enhancer._enhance_with_gemini(message, requirements)
                logger.info("Gemini enhancement completed successfully")
            except Exception as e:
                logger.error(f"Gemini enhancement failed: {str(e)}")
        elif self.ai_enhancer.openai_api_key:
            try:
                requirements = self.ai_enhancer._enhance_with_openai(message, requirements)
                logger.info("OpenAI enhancement completed successfully")
            except Exception as e:
                logger.error(f"OpenAI enhancement failed: {str(e)}")

        return requirements




    def _extract_location(self, message: str) -> tuple:
        """Extract location preferences and context"""
        distance_preference = None
        location_context = None

        # Check for distance keywords
        for keyword, preference in self.location_keywords.items():
            if keyword in message:
                if preference in ['near', 'far']:
                    distance_preference = preference
                else:
                    location_context = preference
                break

        # Extract specific location mentions
        location_patterns = [
            r'near\s+([a-z\s]+)', r'close\s+to\s+([a-z\s]+)',
            r'walking\s+distance\s+to\s+([a-z\s]+)', r'by\s+([a-z\s]+)'
        ]

        for pattern in location_patterns:
            match = re.search(pattern, message)
            if match:
                location_context = match.group(1).strip()
                break

        return distance_preference, location_context

    def _extract_gender_preference(self, message: str) -> Optional[str]:
        """Extract gender preference if mentioned"""
        if any(word in message for word in ['male', 'boys', 'guys', 'mens']):
            return 'male'
        elif any(word in message for word in ['female', 'girls', 'ladies', 'womens']):
            return 'female'
        elif 'mixed' in message or 'any' in message or 'no preference' in message:
            return 'any'

        return None

    def _extract_urgency(self, message: str) -> Optional[str]:
        """Extract urgency level if mentioned"""
        urgent_words = ['urgent', 'asap', 'immediately', 'quickly', 'soon']
        moderate_words = ['within', 'before', 'by']

        if any(word in message for word in urgent_words):
            return 'high'
        elif any(word in message for word in moderate_words):
            return 'medium'

        return None






    def validate_requirements(self, requirements: Dict) -> Dict:
        """Validate and clean extracted requirements"""
        return self.extractor.validate_requirements(requirements)

    def format_requirements_for_display(self, requirements: Dict) -> str:
        """Format requirements for WhatsApp display"""
        return self.extractor.format_requirements_for_display(requirements)

    def is_greeting_response(self, requirements: Dict) -> bool:
        """Check if the requirements result is a greeting response"""
        return self.greeting_handler.is_greeting_response(requirements)

    def get_greeting_response(self, requirements: Dict) -> str:
        """Get the greeting response text if this is a greeting"""
        return self.greeting_handler.get_greeting_response(requirements)

    def _generate_greeting_response(self, message: str) -> str:
        """Generate greeting response"""
        return self.greeting_handler._generate_greeting_response(message)

    def classify_message(self, message: str) -> str:
        """
        Classify message into one of 4 categories

        Args:
            message (str): The message to classify

        Returns:
            str: Single character classification key
        """
        return self.classifier.classify_message(message)

    def _get_help_message(self) -> str:
        """Get help message for users"""
        return """*Help - Jeff Accommodation Assistant*

I help students find accommodation near NUST campus.

*How to use:*
• Tell me your requirements (e.g. "2 heads, WiFi, $200 max")
• I'll find matching properties for you
• Pay $1.00 token to view detailed listings

*Available commands:*
• Send requirements to search
• "help" for this message
• "USD PAY" or "ZWL PAY" for payment

*Payment:* $1.00 (or ZWL equivalent) via PayNow to view property details."""

    def _get_fallback_greeting_response(self) -> str:
        """Static fallback greeting response"""
        return """*Hi, I'm Jeff*

I help students at NUST find recommended places to stay near campus.

Just tell me what you're looking for. For example:
• _"I need a 2-head room with WiFi for $200"_
• _"Looking for single room near campus"_
• _"Double room with parking, max $150"_

I can help you find accommodation based on:
• Number of people (heads)
• Budget per month
• Required amenities (WiFi, parking, etc.)
• Location preferences
• Gender preferences

Send me your requirements and I'll find matching properties for you!"""

    def _classify_message_fallback(self, message: str) -> str:
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

        # Check for accommodation enquiry (requirement-like content)
        if self._has_requirement_content(message_lower):
            return 'A'

        # Check for greeting messages
        if self.is_greeting_message(message_lower):
            return 'G'

        return 'A'  # Default to accommodation enquiry

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


# Global instance
nlp_processor = DjangoNLPProcessor()