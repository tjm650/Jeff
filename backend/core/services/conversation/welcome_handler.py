"""
Welcome Handler Module

Handles welcome flow for new users:
- Detect first-time users (check last_message_at == created_at)
- Format welcome message with quick reply options
- Route quick reply keywords (🔍 Search, 💰 Buy token, 🎒 NUST rooms, 🏘 General, ❓ Help)
"""

import logging
from typing import Optional
from core.models import ConversationState
from .ux_formatter import ux_formatter

logger = logging.getLogger(__name__)


class WelcomeHandler:
    """Welcome flow handler for new users"""
    
    def check_first_time_user(self, conversation: ConversationState) -> bool:
        """
        Detect first-time users
        
        Args:
            conversation: Conversation state object
            
        Returns:
            True if first-time user, False otherwise
        """
        try:
            # Check if last_message_at is very close to created_at (within 1 minute)
            # This indicates the user just started
            time_diff = conversation.last_message_at - conversation.created_at
            return time_diff.total_seconds() < 60
            
        except Exception as e:
            logger.error(f"Error checking first-time user: {str(e)}")
            return False
    
    def format_welcome_message(self) -> str:
        """
        Format welcome message with quick replies
        
        Returns:
            Formatted welcome message
        """
        return ux_formatter.format_welcome_message()
    
    def handle_quick_reply(self, message: str) -> Optional[str]:
        """
        Route quick reply keywords to appropriate handlers
        
        Args:
            message: User's message
            
        Returns:
            Handler identifier or None if not a quick reply
        """
        message_lower = message.lower().strip()
        
        # Check for quick reply keywords
        quick_replies = {
            'search': ['🔍', 'search', 'search rooms', 'find rooms'],
            'buy_token': ['💰', 'buy token', 'token', 'pay'],
            'nust_rooms': ['🎒', 'nust', 'student rooms', 'student'],
            'general_rooms': ['🏘', 'general', 'bulawayo', 'all rooms'],
            'help': ['❓', 'help', 'assist']
        }
        
        for handler, keywords in quick_replies.items():
            if any(keyword in message_lower for keyword in keywords):
                return handler
        
        return None
    
    def should_show_welcome(self, conversation: ConversationState) -> bool:
        """
        Determine if welcome message should be shown
        
        Args:
            conversation: Conversation state object
            
        Returns:
            True if welcome should be shown
        """
        # Check if first-time user
        if self.check_first_time_user(conversation):
            return True
        
        # Check if conversation was reset
        if conversation.current_step == 'inquiry' and not conversation.context_data:
            return True
        
        return False


# Global instance
welcome_handler = WelcomeHandler()

