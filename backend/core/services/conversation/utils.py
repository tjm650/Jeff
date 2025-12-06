"""
Utility handlers for conversation workflow

This module handles utility functions including:
- Conversation state management
- Conversation reset operations
- Context data management
- Utility helper functions
"""

import logging
from typing import Dict

from core.models import ConversationState

logger = logging.getLogger(__name__)


class ConversationUtilsHandler:
    """Utility functionality for conversation workflow"""

    def get_conversation_state(self, cell_number: str) -> ConversationState:
        """Get or create conversation state for user"""
        try:
            # Try to get existing active conversation
            conversation = ConversationState.objects.filter(
                cell_number=cell_number,
                is_active=True
            ).first()

            if conversation:
                return conversation

            # Create new conversation state
            conversation = ConversationState.objects.create(
                cell_number=cell_number,
                current_step='inquiry',
                is_active=True,
                context_data={}
            )

            logger.info(f"Created new conversation state for {cell_number}")
            return conversation

        except Exception as e:
            logger.error(f"Error getting conversation state for {cell_number}: {str(e)}")
            # Try to create conversation state manually as fallback
            try:
                conversation = ConversationState.objects.create(
                    cell_number=cell_number,
                    current_step='inquiry',
                    is_active=True,
                    context_data={}
                )
                logger.info(f"Created fallback conversation state for {cell_number}")
                return conversation
            except Exception as e2:
                logger.error(f"Error creating fallback conversation state for {cell_number}: {str(e2)}")
                # Return None and let the workflow handle it
                return None

    def reset_to_inquiry(self, conversation) -> str:
        """Reset conversation to inquiry step"""
        try:
            conversation.current_step = 'inquiry'
            conversation.context_data = {}
            conversation.save()

            logger.info(f"Conversation reset to inquiry for {conversation.cell_number}")

            return """_Sure, I've reset our conversation. You can start fresh_"""

        except Exception as e:
            logger.error(f"Error resetting conversation: {str(e)}")
            return "Conversation has been reset. Please try again."

    def get_help_message(self) -> str:
        """Get enhanced help message using NLP processor capabilities"""
        try:
            from matching.nlp_processor import nlp_processor
            return nlp_processor._get_help_message()
        except Exception as e:
            logger.error(f"Error getting help message: {str(e)}")
            return """Hi, I'm Jeff👋

I help students at NUST find accommodation near campus.

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

    def update_conversation_context(self, conversation, context_updates: Dict) -> bool:
        """Update conversation context data safely"""
        try:
            if not isinstance(conversation.context_data, dict):
                conversation.context_data = {}

            conversation.context_data.update(context_updates)
            conversation.save()

            logger.debug(f"Updated conversation context for {conversation.cell_number}")
            return True

        except Exception as e:
            logger.error(f"Error updating conversation context: {str(e)}")
            return False

    def get_context_value(self, conversation, key: str, default=None):
        """Get a value from conversation context safely"""
        try:
            return conversation.context_data.get(key, default)
        except Exception as e:
            logger.error(f"Error getting context value '{key}': {str(e)}")
            return default

    def clear_conversation_context(self, conversation) -> bool:
        """Clear conversation context data"""
        try:
            conversation.context_data = {}
            conversation.save()

            logger.info(f"Cleared conversation context for {conversation.cell_number}")
            return True

        except Exception as e:
            logger.error(f"Error clearing conversation context: {str(e)}")
            return False


# Global instance
conversation_utils = ConversationUtilsHandler()