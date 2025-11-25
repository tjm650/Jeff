from typing import List
from core.models import Booking, Property

class BookingNotifications:
    """Handles all booking-related notifications and message formatting"""

    def _format_confirmation_message(self, booking: Booking, property: Property) -> str:
        """Format confirmation message for student (matches PDF specification Step 7)"""
        return f""" *BOOKING CONFIRMED*

 Property: {property.name}
 Provider: {property.provider.name}
 Contact: {property.provider.phone_number}

Your accommodation at {property.name} has been confirmed
Thank you for using Jeff Agent
Type anything to start a new search, or type "help" for assistance."""

    def _format_rejection_message(self, booking: Booking) -> str:
        """Format rejection message for student"""
        return f""" *Booking Not Available*

Unfortunately, {booking.property.name} is no longer available. Your token has been refunded. You can Use it for your next booking.

*Choose your next option:*
1. Book another property from your list
2. Start a new search

__Reply with the number or describe what you're looking for.__"""

    def _format_info_request_message(self, booking: Booking, questions: List[str]) -> str:
        """Format information request message for student (Step 6 in PDF)"""
        message = f""" *Additional Information Requested*

The accommodation provider has some questions before confirming:
 Property: {booking.property.name}
 Provider: {booking.property.provider.name}

 *Questions:*
"""

        for i, question in enumerate(questions, 1):
            message += f"{i}. {question}\n"

        message += """
Please reply with your answers.
I'll forward them to the provider.

_ Replying Example:_
_1. No, I don't smoke_
_2. No, I don't drink_
_3. Computer Science, 2nd year_ """

        return message

# Global instance for easy import
booking_notifications = BookingNotifications()