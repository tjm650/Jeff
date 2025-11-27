"""
Help and utility handlers for conversation workflow

This module handles help and utility functions including:
- Comprehensive help messages
- Contextual help based on conversation state
- NLP suggestions for failed extractions
- Help message formatting
"""

import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class HelpUtilsHandler:
    """Help and utility functionality for conversation workflow"""

    def get_comprehensive_help_message(self) -> str:
        """Get comprehensive help message with all available options"""
        frontend_url = os.getenv('NEXT_PUBLIC_FRONTEND_URL')
        return f"""*JEFF HELP & SUPPORT*

*How Jeff Works* 📑
• Jeff helps NUST students find accommodation near campus
• Jeff is reliable, fast, secure and easy to use, accessible on WhatsApp
• Visit {frontend_url} for more info
• Send your requirements and find matching properties
• Token cost $1.00 (USD or ZWL equivalent)

*How to Pay 💳*
• Visit: {frontend_url}/cart

*What Jeff Can Find 🏠*
• Single, double rooms and BNBs
• Properties with WiFi, parking, etc
• Properties near campus
• Male/female/mixed accommodations
• Various budget ranges

*How to Search 🔎*
• _"I need a 2-head room with WiFi for $200"_
• _"Single room near campus, max $150"_
• _"Property with parking, wifi, etc"_


_*Need more help?* Contact our support team._
_Send 'Jeff' message for more info about the service, Terms & Privacy Policy of Jeff or visit {frontend_url}._
"""

    def get_fallback_help_message(self) -> str:
        """Fallback help message in case comprehensive help fails"""
        return """Hi, I'm Jeff👋.
    I help students find accommodation near campus. If you see this message, I'm offline right now.
    Please try again later or contact support for assistance."""

    def get_contextual_help(self, conversation) -> str:
        """Get contextual help based on conversation state and NLP data"""
        try:
            context_data = conversation.context_data
            current_step = conversation.current_step

            # Provide step-specific help
            if current_step == 'inquiry':
                return self._get_inquiry_help(context_data)
            elif current_step == 'token_check':
                return self._get_token_help(context_data)
            elif current_step == 'property_listings':
                return self._get_property_selection_help(context_data)
            elif current_step == 'name_collection':
                return self._get_name_collection_help(context_data)
            else:
                return self.get_comprehensive_help_message()

        except Exception as e:
            logger.error(f"Error generating contextual help: {str(e)}")
            return self.get_comprehensive_help_message()

    def _get_inquiry_help(self, context_data: Dict) -> str:
        """Get help for inquiry step"""
        return """*Need Help with Your Search?*

Try these examples:
• "I need a single room for $100"
• "Looking for 2-head with WiFi and parking"
• "Double room near campus, max $150"

Just tell me:
• How many people? (1, 2, 3, etc.)
• Your budget per month?
• Any amenities you need?
• Location preferences?"""

    def _get_token_help(self, context_data: Dict) -> str:
        """Get help for token step"""
        frontend_url = os.getenv('NEXT_PUBLIC_FRONTEND_URL')
        return f"""*Need Help with Payment?*
To search for accommodation, you need a token.

*HOW TO PURCHASE A TOKEN*
• Visit: {frontend_url}/cart
_Questions? Send 'help' for more information._
_Send 'Jeff' message for more info about the service, Terms & Privacy Policy of Jeff or visit {frontend_url}._
"""

    def _get_property_selection_help(self, context_data: Dict) -> str:
        """Get help for property selection"""
        search_results = context_data.get('search_results', [])

        if not search_results:
            return self.get_comprehensive_help_message()

        message = """*Need Help Selecting a Property?*

Reply with the number option-(1-5) next to the property you want to book.

*Example:* Send "option-2" to book the second property.

*Want different options?*
Send new requirements like "higher budget" or "different location".

*Available options:*"""

        for i, prop in enumerate(search_results[:3], 1):  # Show first 3
            message += f"\n{i}. {prop['name']} - ${prop['price_per_month']}"

        return message

    def _get_name_collection_help(self, context_data: Dict) -> str:
        """Get help for name collection"""
        return """*Almost Done!*

Please provide your full name for the booking request.

*Examples:*
• "John Doe"
• "Sarah Smith"
• "Michael Johnson"

This helps the accommodation provider know who's requesting the booking."""

    def provide_nlp_suggestions(self, failed_requirements: Dict) -> str:
        """Provide intelligent suggestions based on failed NLP extraction"""
        try:
            from ....matching.nlp_processor import nlp_processor

            suggestions = ["*Try these formats:*"]

            # Suggest based on what's missing
            if not failed_requirements.get('heads'):
                suggestions.append("• 'I need a 2-head room'")
                suggestions.append("• 'Single room for one person'")

            if not failed_requirements.get('budget_max'):
                suggestions.append("• 'Budget is $200 per month'")
                suggestions.append("• 'Looking for something under $150'")

            if not failed_requirements.get('amenities'):
                suggestions.append("• 'Room with WiFi and parking'")
                suggestions.append("• 'Need DSTV and security'")

            suggestions.append("• '2-head room with electricity for $200'")

            return "\n".join(suggestions)

        except Exception as e:
            logger.error(f"Error providing NLP suggestions: {str(e)}")
            return "*Try:* 'I need a 2-head room with WiFi for $200'"

    def handle_media_message(self, cell_number: str, media_url: str, caption: str) -> str:
        """Handle media messages (no longer used for POP)"""
        try:
            # Media messages are no longer used for proof of payment
            # Payment is handled directly through Paynow/EcoCash APIs
            return " Media uploads are not required for payment. Please use the direct payment flow by sending 'pay' and following the mobile payment instructions."

        except Exception as e:
            logger.error(f"Error handling media message: {str(e)}")
            return " Error processing media message. Please try again."


# Global instance
help_utils_handler = HelpUtilsHandler()