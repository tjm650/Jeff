"""
Location Flow Handler Module

Implements structured location selection:
- Detect location from message (NUST, Riverside, Selborne Park, Southwold, CBD)
- Ask for location if not detected
- Format location question with area suggestions
- Ask budget with quick reply options (Below $40, $40-$60, $60-$100, Above $100)
- Store location and budget in conversation.context_data
"""

import logging
import re
from typing import Optional, Dict, Tuple
from core.models import ConversationState
from .ux_formatter import ux_formatter

logger = logging.getLogger(__name__)


class LocationFlowHandler:
    """Location and budget selection flow handler"""
    
    # Bulawayo-specific locations
    BULAWAYO_LOCATIONS = [
        'NUST', 'Riverside', 'Selborne Park', 'Southwold', 'CBD',
        'Hillside', 'Suburbs', 'City Centre', 'Belmont', 'Kumalo',
        'Matsheumhlope', 'Burnside', 'Famona', 'Morningside'
    ]
    
    # Campus names
    CAMPUS_NAMES = ['NUST', 'GZU', 'MSU', 'UZ', 'University']
    
    def detect_location_from_message(self, message: str, locations: list = None) -> Optional[str]:
        """
        Extract location from message
        
        Args:
            message: User's message
            locations: List of locations to check (defaults to BULAWAYO_LOCATIONS)
            
        Returns:
            Detected location or None
        """
        if locations is None:
            locations = self.BULAWAYO_LOCATIONS + self.CAMPUS_NAMES
        
        message_lower = message.lower()
        
        # Check for exact matches first
        for location in locations:
            if location.lower() in message_lower:
                return location
        
        # Check for "near campus" or "close to NUST" patterns
        if re.search(r'near\s+(campus|nust|university)', message_lower):
            return 'NUST'
        
        if re.search(r'close\s+to\s+(nust|university)', message_lower):
            return 'NUST'
        
        return None
    
    def format_location_question(self, locations: list = None) -> str:
        """
        Format location selection prompt
        
        Args:
            locations: List of locations to suggest (defaults to BULAWAYO_LOCATIONS)
            
        Returns:
            Formatted location question
        """
        if locations is None:
            locations = self.BULAWAYO_LOCATIONS[:5]  # Show top 5
        
        return ux_formatter.format_location_question(locations)
    
    def ask_budget_with_quick_replies(self) -> str:
        """
        Format budget selection with quick reply options
        
        Returns:
            Formatted budget question
        """
        return ux_formatter.format_budget_question()
    
    def parse_budget_quick_reply(self, message: str) -> Optional[float]:
        """
        Parse budget range from quick reply
        
        Args:
            message: User's budget selection
            
        Returns:
            Budget value (middle of range) or None
        """
        message_lower = message.lower().strip()
        
        # Parse budget ranges
        if 'below $40' in message_lower or 'under $40' in message_lower:
            return 35.0  # Middle of below $40 range
        elif '$40' in message_lower and '$60' in message_lower:
            return 50.0  # Middle of $40-$60 range
        elif '$60' in message_lower and '$100' in message_lower:
            return 80.0  # Middle of $60-$100 range
        elif 'above $100' in message_lower or 'over $100' in message_lower:
            return 120.0  # Above $100
        
        # Try to extract number from message
        numbers = re.findall(r'\$?(\d+)', message)
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                pass
        
        return None
    
    def store_location_in_context(self, conversation: ConversationState, location: str) -> None:
        """
        Store location in conversation context
        
        Args:
            conversation: Conversation state object
            location: Detected location
        """
        try:
            if not conversation.context_data:
                conversation.context_data = {}
            
            conversation.context_data['location'] = location
            conversation.context_data['last_action'] = 'location_selected'
            conversation.save()
            
        except Exception as e:
            logger.error(f"Error storing location in context: {str(e)}")
    
    def store_budget_in_context(self, conversation: ConversationState, budget: float) -> None:
        """
        Store budget in conversation context
        
        Args:
            conversation: Conversation state object
            budget: Budget value
        """
        try:
            if not conversation.context_data:
                conversation.context_data = {}
            
            conversation.context_data['budget_max'] = budget
            conversation.context_data['last_action'] = 'budget_selected'
            conversation.save()
            
        except Exception as e:
            logger.error(f"Error storing budget in context: {str(e)}")
    
    def get_stored_location(self, conversation: ConversationState) -> Optional[str]:
        """
        Get stored location from context
        
        Args:
            conversation: Conversation state object
            
        Returns:
            Stored location or None
        """
        try:
            return conversation.context_data.get('location') if conversation.context_data else None
        except Exception:
            return None
    
    def get_stored_budget(self, conversation: ConversationState) -> Optional[float]:
        """
        Get stored budget from context
        
        Args:
            conversation: Conversation state object
            
        Returns:
            Stored budget or None
        """
        try:
            budget = conversation.context_data.get('budget_max') if conversation.context_data else None
            if budget:
                return float(budget)
            return None
        except Exception:
            return None


# Global instance
location_flow_handler = LocationFlowHandler()

