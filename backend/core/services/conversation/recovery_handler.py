"""
Recovery Handler Module

Implements recovery flow for returning users:
- Detect inactivity (2+ hours since last message)
- Check for stored search context in conversation.context_data
- Format recovery message with last location/budget
- Offer quick replies: "Yes", "Show new listings", "Start over"
"""

import logging
from typing import Optional
from django.utils import timezone
from datetime import timedelta
from core.models import ConversationState
from .ux_formatter import ux_formatter

logger = logging.getLogger(__name__)


class RecoveryHandler:
    """Recovery flow handler for returning users"""
    
    # Inactivity threshold (2 hours)
    INACTIVITY_THRESHOLD = timedelta(hours=2)
    
    def check_recovery_needed(self, conversation: ConversationState) -> bool:
        """
        Detect inactivity and check if recovery flow is needed
        
        Args:
            conversation: Conversation state object
            
        Returns:
            True if recovery flow should be shown, False otherwise
        """
        try:
            # Check time since last message
            time_since_last = timezone.now() - conversation.last_message_at
            
            if time_since_last < self.INACTIVITY_THRESHOLD:
                return False
            
            # Check if we have stored search context
            context = conversation.context_data or {}
            has_context = bool(
                context.get('location') or 
                context.get('budget_max') or 
                context.get('last_property_ids')
            )
            
            return has_context
            
        except Exception as e:
            logger.error(f"Error checking recovery needed: {str(e)}")
            return False
    
    def format_recovery_message(self, conversation: ConversationState) -> str:
        """
        Format recovery message with context
        
        Args:
            conversation: Conversation state object
            
        Returns:
            Formatted recovery message
        """
        return ux_formatter.format_recovery_message(conversation)
    
    def handle_recovery_response(self, conversation: ConversationState, message: str) -> Optional[str]:
        """
        Route recovery actions based on user response
        
        Args:
            conversation: Conversation state object
            message: User's response
            
        Returns:
            Handler action or None if not a recovery response
        """
        try:
            message_lower = message.lower().strip()
            
            # Check for recovery responses
            if message_lower in ['yes', 'continue', 'y']:
                # Continue with previous search
                context = conversation.context_data or {}
                location = context.get('location')
                budget = context.get('budget_max')
                
                if location and budget:
                    # Restore search with previous criteria
                    return f"Continuing your search for rooms near {location} with budget ${budget}..."
                elif location:
                    return f"Continuing your search for rooms near {location}..."
                else:
                    return "Continuing your previous search..."
            
            elif message_lower in ['show new listings', 'new listings', 'new']:
                # Show new listings (clear old results, keep location/budget)
                context = conversation.context_data or {}
                context.pop('search_results', None)
                context.pop('last_property_ids', None)
                conversation.context_data = context
                conversation.current_step = 'inquiry'
                conversation.save()
                return "Showing new listings for your area..."
            
            elif message_lower in ['start over', 'start', 'restart', 'new search']:
                # Start completely fresh
                conversation.context_data = {}
                conversation.current_step = 'inquiry'
                conversation.save()
                return "Starting fresh. What area are you looking for?"
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling recovery response: {str(e)}")
            return None
    
    def restore_search_context(self, conversation: ConversationState) -> dict:
        """
        Restore search context from conversation state
        
        Args:
            conversation: Conversation state object
            
        Returns:
            Restored context dictionary
        """
        try:
            context = conversation.context_data or {}
            return {
                'location': context.get('location'),
                'budget_max': context.get('budget_max'),
                'last_property_ids': context.get('last_property_ids', []),
                'cached_filters': context.get('cached_filters', {}),
                'user_preferences': context.get('user_preferences', {})
            }
        except Exception as e:
            logger.error(f"Error restoring search context: {str(e)}")
            return {}


# Global instance
recovery_handler = RecoveryHandler()

