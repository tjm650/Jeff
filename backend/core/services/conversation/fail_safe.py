"""
Fail-Safe Handler Module

Implements fail-safe rules for robust error handling:
- Null response handlers for all API operations
- Random text input handler (show help menu)
- Payment verification delay messages
- Provider timeout handling (24-hour follow-up)
- Database error graceful degradation
"""

import logging
from typing import Optional, Dict
from django.utils import timezone
from datetime import timedelta
from core.models import Booking, Payment
from .ux_formatter import ux_formatter

logger = logging.getLogger(__name__)


class FailSafeHandler:
    """Fail-safe rules for robust conversation handling"""
    
    def handle_null_response(self, context: str) -> str:
        """
        Handle null/empty responses gracefully
        
        Args:
            context: Context of the operation (property_search, payment_verification, etc.)
            
        Returns:
            Friendly error message
        """
        messages = {
            'property_search': "I couldn't find any properties. Try adjusting your budget or location.",
            'payment_verification': "Still checking your payment... Please wait a moment.",
            'provider_response': "The landlord hasn't responded yet. I'll notify you when they do.",
            'database_error': "Try again shortly, we're fixing something.",
            'token_validation': "There was an issue checking your token. Please try again.",
            'booking_creation': "There was an issue creating your booking. Please try again.",
            'generic': "Something went wrong. Please try again."
        }
        return messages.get(context, messages['generic'])
    
    def handle_random_text(self, message: str) -> Optional[str]:
        """
        Handle random/unexpected text input
        
        Args:
            message: User's message
            
        Returns:
            Help message if input is invalid, None if it might be valid
        """
        # Check if it's a valid command (basic check)
        valid_commands = [
            'help', 'hi', 'hello', 'start', 'search', 'view', 'option-',
            'name-', 'yes', 'no', 'buy', 'token', 'pay', 'usd', 'zwg',
            'abort', 'restart', 'cancel', 'jeff', 'j', 'status', 'insights'
        ]
        
        message_lower = message.lower().strip()
        
        # Check if message starts with a valid command
        is_valid = any(
            message_lower.startswith(cmd) or cmd in message_lower
            for cmd in valid_commands
        )
        
        # Also check for numbers (could be option selection)
        if message_lower.isdigit() or message_lower.startswith('view '):
            is_valid = True
        
        if not is_valid and len(message) > 50:
            # Likely random text, show help menu
            return self._get_simple_help_menu()
        
        return None
    
    def handle_payment_delay(self, payment: Payment = None) -> str:
        """
        Handle payment verification delays
        
        Args:
            payment: Payment object (optional)
            
        Returns:
            Delay message
        """
        return "Still checking your payment... This usually takes a few seconds. I'll notify you as soon as it's confirmed."
    
    def handle_provider_timeout(self, booking: Booking) -> Optional[str]:
        """
        Handle provider not responding
        
        Args:
            booking: Booking object
            
        Returns:
            Timeout message if 24+ hours, None otherwise
        """
        try:
            time_since_booking = timezone.now() - booking.created_at
            
            if time_since_booking > timedelta(hours=24):
                message = "The landlord hasn't responded yet. Would you like to:\n\n"
                message += "• Wait longer\n"
                message += "• Try another property\n"
                message += "• Contact support"
                return message
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking provider timeout: {str(e)}")
            return None
    
    def handle_database_error(self, operation: str) -> str:
        """
        Handle database errors gracefully
        
        Args:
            operation: Operation that failed
            
        Returns:
            Friendly error message
        """
        logger.error(f"Database error in {operation}")
        return ux_formatter.format_error_message('database_error')
    
    def handle_api_error(self, service: str, error: Exception = None) -> str:
        """
        Handle API/service errors
        
        Args:
            service: Service name (paynow, twilio, etc.)
            error: Exception object (optional)
            
        Returns:
            Friendly error message
        """
        logger.error(f"API error in {service}: {str(error) if error else 'Unknown error'}")
        
        messages = {
            'paynow': "Payment service is temporarily unavailable. Please try again in a few minutes.",
            'twilio': "Messaging service is having issues. Please try again shortly.",
            'generic': "A service is temporarily unavailable. Please try again shortly."
        }
        
        return messages.get(service, messages['generic'])
    
    def handle_token_error(self, error_type: str) -> str:
        """
        Handle token-related errors
        
        Args:
            error_type: Type of token error
            
        Returns:
            Friendly error message
        """
        messages = {
            'expired': ux_formatter.format_error_message('token_expired'),
            'not_found': ux_formatter.format_error_message('no_token'),
            'invalid': "Your token is invalid. Please contact support.",
            'consumed': "You've used all your token searches. Please buy a new token."
        }
        
        return messages.get(error_type, "There was an issue with your token. Please try again.")
    
    def handle_property_error(self, error_type: str) -> str:
        """
        Handle property-related errors
        
        Args:
            error_type: Type of property error
            
        Returns:
            Friendly error message
        """
        messages = {
            'not_found': "I couldn't find that property. Please try selecting another one.",
            'unavailable': "This property is no longer available. Please try another one.",
            'invalid_selection': "Invalid selection. Please use 'VIEW {number}' or 'option-{number}'."
        }
        
        return messages.get(error_type, "There was an issue with the property. Please try again.")
    
    def _get_simple_help_menu(self) -> str:
        """Get simple help menu for invalid input"""
        return """I didn't understand that. Here's what I can help with:

• 🔍 Search rooms
• 💰 Buy token
• ❓ Help
• Start over"""
    
    def wrap_operation(self, operation_func, context: str, *args, **kwargs):
        """
        Wrap an operation with fail-safe error handling
        
        Args:
            operation_func: Function to wrap
            context: Context for error messages
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Result of operation or error message
        """
        try:
            result = operation_func(*args, **kwargs)
            
            # Check for null/empty results
            if result is None or (isinstance(result, str) and not result.strip()):
                return self.handle_null_response(context)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in {context}: {str(e)}", exc_info=True)
            
            # Check error type and return appropriate message
            if 'database' in str(e).lower() or 'connection' in str(e).lower():
                return self.handle_database_error(context)
            elif 'api' in str(e).lower() or 'http' in str(e).lower():
                return self.handle_api_error('generic', e)
            else:
                return self.handle_null_response(context)


# Global instance
fail_safe_handler = FailSafeHandler()

