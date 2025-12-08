"""
UX Formatter Module

WhatsApp-optimized message formatting utilities following UX style guide:
- Message length limits (300 chars, max 2 sentences per bubble)
- Emoji mapping and usage rules (1-2 per message max)
- Property preview formatting
- Error message templates (friendly, non-technical)
- Quick reply formatting utility
- Message splitting for long content
- Memory/reference formatting (gentle reminders of previous choices)
"""

import logging
import re
from typing import List, Dict, Optional
from core.models import Property, ConversationState

logger = logging.getLogger(__name__)


class UXFormatter:
    """WhatsApp-optimized message formatting utilities"""
    
    # Tone rules
    TONE_RULES = {
        'friendly': True,
        'simple_english': True,
        'student_friendly': True,
        'local_context_aware': True
    }
    
    # Message length limits
    MAX_MESSAGE_LENGTH = 300  # characters
    MAX_SENTENCES_PER_MESSAGE = 2
    
    # Emoji mapping
    EMOJI_MAP = {
        'location': '📍',
        'money': '💵',
        'viewing': '📅',
        'confirmation': '✔',
        'alert': '⚠',
        'room': '🏠',
        'wifi': '📶',
        'safe': '🛡',
        'phone': '📱',
        'search': '🔍',
        'token': '💰',
        'student': '🎓',
        'help': '❓',
        'back': '🔙',
        'save': '⭐',
        'yes': '✔',
        'no': '❌',
        'cancel': '🙅'
    }
    
    def format_property_preview(self, property: Property, index: int) -> str:
        """
        Format property preview following UX guidelines
        
        Args:
            property: Property model instance
            index: Property index number for VIEW command
            
        Returns:
            Formatted preview message
        """
        try:
            # Extract location (first part of address)
            location = property.address.split(',')[0] if property.address else "Unknown"
            
            # Format room type
            room_type = self._format_room_type(property)
            
            # Get top 2 amenities
            amenities = property.amenities[:2] if property.amenities else []
            amenities_str = ', '.join(amenities) if amenities else 'Basic'
            
            # Key info first
            message = f"{self.EMOJI_MAP['location']} {location} ({property.distance_from_campus}km from {property.campus_name})\n\n"
            
            # Short description
            message += f"{self.EMOJI_MAP['money']} ${property.price_per_month} / month\n\n"
            message += f"{self.EMOJI_MAP['room']} {room_type}, {amenities_str}\n\n"
            
            # Clear next action
            message += f"Reply VIEW {index} to unlock details."
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting property preview: {str(e)}")
            return f"Property {index}: {property.name if property else 'Unknown'}"
    
    def format_full_property_details(self, property: Property, score: float = None, reasons: List[str] = None) -> str:
        """
        Format full property details after token consumption
        
        Args:
            property: Property model instance
            score: Match score (optional)
            reasons: Match reasons (optional)
            
        Returns:
            Formatted full details message
        """
        try:
            message = f"{self.EMOJI_MAP['room']} {property.name}\n\n"
            message += f"{self.EMOJI_MAP['money']} ${property.price_per_month} / month\n\n"
            message += f"{self.EMOJI_MAP['location']} {property.distance_from_campus}km from {property.campus_name}\n"
            message += f"{property.address}\n\n"
            
            # Amenities
            if property.amenities:
                amenities_str = ', '.join(property.amenities[:5])
                message += f"{self.EMOJI_MAP['wifi']} {amenities_str}\n\n"
            
            # Availability
            message += f"Available rooms: {property.available_rooms}/{property.total_rooms}\n\n"
            
            # Match score if provided
            if score:
                message += f"Match score: {score}/50\n"
            
            # Match reasons if provided
            if reasons:
                message += f"Why it matches: {' | '.join(reasons[:2])}\n\n"
            
            # CTA
            message += "Would you like me to contact the landlord for you?"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting full property details: {str(e)}")
            return f"Property: {property.name if property else 'Unknown'}"
    
    def format_error_message(self, error_type: str) -> str:
        """
        Format friendly error messages
        
        Args:
            error_type: Type of error (invalid_input, no_properties, payment_failed, etc.)
            
        Returns:
            Friendly error message
        """
        errors = {
            'invalid_input': "Oops 😅 I didn't get that. Try choosing one of the options below.",
            'no_properties': "Sorry, I couldn't find any rooms matching your requirements. Try adjusting your budget or location.",
            'payment_failed': "Payment didn't go through. Please try again or contact support if the problem continues.",
            'token_expired': "Your token has expired. Please buy a new token to continue searching.",
            'no_token': "You need a token to view full property details. Would you like to buy one?",
            'database_error': "Try again shortly, we're fixing something.",
            'provider_timeout': "The landlord hasn't responded yet. I'll notify you when they do.",
            'generic': "Something went wrong. Please try again."
        }
        return errors.get(error_type, errors['generic'])
    
    def split_long_message(self, message: str) -> List[str]:
        """
        Split long messages into multiple bubbles
        
        Args:
            message: Message to split
            
        Returns:
            List of message chunks (each under MAX_MESSAGE_LENGTH)
        """
        if len(message) <= self.MAX_MESSAGE_LENGTH:
            return [message]
        
        # Split by sentences
        sentences = re.split(r'([.!?]\s+)', message)
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else '')
            
            if len(current_chunk) + len(sentence) + 2 <= self.MAX_MESSAGE_LENGTH:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def format_with_quick_replies(self, message: str, quick_replies: List[str]) -> str:
        """
        Format message with quick reply suggestions
        
        Args:
            message: Base message
            quick_replies: List of quick reply options
            
        Returns:
            Formatted message with quick replies
        """
        formatted = message
        if quick_replies:
            formatted += "\n\nQUICK REPLIES:\n"
            for reply in quick_replies:
                formatted += f"• {reply}\n"
        return formatted.strip()
    
    def add_emoji(self, text: str, emoji_type: str) -> str:
        """
        Add emoji following guidelines (1-2 per message max)
        
        Args:
            text: Text to add emoji to
            emoji_type: Type of emoji from EMOJI_MAP
            
        Returns:
            Text with emoji prefix
        """
        emoji = self.EMOJI_MAP.get(emoji_type, '')
        if emoji:
            return f"{emoji} {text}"
        return text
    
    def format_with_memory(self, message: str, conversation: ConversationState) -> str:
        """
        Format message with gentle reference to previous choices
        
        Args:
            message: Base message
            conversation: Conversation state with context data
            
        Returns:
            Message with memory references if applicable
        """
        try:
            context = conversation.context_data or {}
            last_location = context.get('location')
            last_budget = context.get('budget_max')
            
            # Add memory reference if message contains "similar" and we have location
            if last_location and 'similar' in message.lower():
                return f"You liked {last_location} earlier — want to see similar rooms?"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting with memory: {str(e)}")
            return message
    
    def _format_room_type(self, property: Property) -> str:
        """Format room type based on available rooms"""
        try:
            if property.available_1h_rooms > 0:
                return "Single room"
            elif property.available_2h_rooms > 0:
                return "Double room"
            elif property.available_3h_rooms > 0:
                return "Triple room"
            elif property.available_4h_rooms > 0:
                return "Quad room"
            else:
                return "Room"
        except Exception:
            return "Room"
    
    def format_welcome_message(self) -> str:
        """Format welcome message with quick replies"""
        message = f"{self.EMOJI_MAP['help']} Hi there! Welcome to Bulawayo Rooms Finder\n\n"
        message += f"I help you find safe, affordable rooms — especially near NUST {self.EMOJI_MAP['student']}.\n\n"
        message += "What would you like to do today?"
        
        quick_replies = [
            f"{self.EMOJI_MAP['search']} Search rooms",
            f"{self.EMOJI_MAP['token']} Buy token",
            f"{self.EMOJI_MAP['student']} Student rooms near NUST",
            f"{self.EMOJI_MAP['room']} General Bulawayo rooms",
            f"{self.EMOJI_MAP['help']} Help"
        ]
        
        return self.format_with_quick_replies(message, quick_replies)
    
    def format_location_question(self, locations: List[str] = None) -> str:
        """Format location selection question"""
        if locations is None:
            locations = ['NUST', 'Riverside', 'Selborne Park', 'Southwold', 'CBD']
        
        message = f"Great! Let me know the area you're interested in {self.EMOJI_MAP['location']}\n\n"
        message += f"(Example: {', '.join(locations[:3])}, etc.)"
        
        return message
    
    def format_budget_question(self) -> str:
        """Format budget selection with quick replies"""
        message = "Got it! What's your budget?"
        
        quick_replies = [
            "Below $40",
            "$40–$60",
            "$60–$100",
            "Above $100"
        ]
        
        return self.format_with_quick_replies(message, quick_replies)
    
    def format_payment_instructions(self) -> str:
        """Format payment instructions with quick replies"""
        message = "To view full details + contact the landlord, you'll need 1 view token.\n\n"
        message += "Would you like to buy a token now?\n\n"
        message += "(Paynow — EcoCash, USD, ZWL supported)"
        
        quick_replies = [
            f"{self.EMOJI_MAP['yes']} Buy token",
            f"{self.EMOJI_MAP['no']} Not now"
        ]
        
        return self.format_with_quick_replies(message, quick_replies)
    
    def format_contact_landlord_prompt(self) -> str:
        """Format contact landlord prompt with quick replies"""
        message = "Would you like me to contact the landlord for you?"
        
        quick_replies = [
            f"{self.EMOJI_MAP['phone']} Yes, contact landlord",
            f"{self.EMOJI_MAP['back']} Back",
            f"{self.EMOJI_MAP['save']} Save for later"
        ]
        
        return self.format_with_quick_replies(message, quick_replies)
    
    def format_recovery_message(self, conversation: ConversationState) -> str:
        """Format recovery message for returning users"""
        context = conversation.context_data or {}
        last_location = context.get('location', 'your area')
        
        message = f"{self.EMOJI_MAP['help']} Welcome back!\n\n"
        message += f"You were checking rooms near {last_location}.\n\n"
        message += "Would you like to continue?"
        
        quick_replies = [
            "Yes",
            "Show new listings",
            "Start over"
        ]
        
        return self.format_with_quick_replies(message, quick_replies)


# Global instance
ux_formatter = UXFormatter()

