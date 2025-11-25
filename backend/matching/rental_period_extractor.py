"""
This module handles rental period extraction from accommodation requirement messages.
"""

import re
from typing import Optional


class RentalPeriodExtractor:
    """Extracts rental period preferences from accommodation requirement messages"""

    def __init__(self):
        # Common patterns for rental period identification
        self.day_patterns = [
            r'\b(?:per\s+)?day\b',
            r'\bdaily\b',
            r'\b\d+\s*(?:day|days)\b',
            r'\brent(?:ing)?\s+(?:for\s+)?\d+\s*(?:day|days)\b'
        ]
        
        self.week_patterns = [
            r'\b(?:per\s+)?week\b',
            r'\bweekly\b',
            r'\b\d+\s*(?:week|weeks)\b',
            r'\brent(?:ing)?\s+(?:for\s+)?\d+\s*(?:week|weeks)\b'
        ]
        
        self.month_patterns = [
            r'\b(?:per\s+)?month\b',
            r'\bmonthly\b',
            r'\b\d+\s*(?:month|months)\b',
            r'\brent(?:ing)?\s+(?:for\s+)?\d+\s*(?:month|months)\b'
        ]

    def extract_rental_period(self, message: str) -> Optional[str]:
        """
        Extract rental period from message.

        Args:
            message (str): User's accommodation requirement message

        Returns:
            str: 'day', 'week', 'month', or None if not specified
        """
        if not message:
            return None

        message = message.lower()

        # Check for daily rental patterns
        for pattern in self.day_patterns:
            if re.search(pattern, message):
                return 'day'

        # Check for weekly rental patterns
        for pattern in self.week_patterns:
            if re.search(pattern, message):
                return 'week'

        # Check for monthly rental patterns
        for pattern in self.month_patterns:
            if re.search(pattern, message):
                return 'month'

        # Default to None if no rental period specified
        return None

    def suggest_rental_period(self, rental_period: Optional[str] = None) -> str:
        """
        Generate a message asking user to clarify rental period.

        Args:
            rental_period (str, optional): Previously extracted rental period, if any

        Returns:
            str: Message asking user to specify rental period preference
        """
        if rental_period:
            return f"I see you're interested in {rental_period}ly rental. Would you like to see rates for other periods as well?"

        return ("Please specify your preferred rental period:\n"
                "• Daily rental (short stays)\n"
                "• Weekly rental (medium stays)\n"
                "• Monthly rental (long-term stays)\n\n"
                "_Example: 'Looking for accommodation for the whole semester for $100 a month'_")


# Global instance
rental_period_extractor = RentalPeriodExtractor()