#/usr/bin/env python
"""
Test script for Jeff Platform workflow

This script tests the complete workflow from inquiry to booking completion
to ensure all components work together correctly.
"""

import os
import sys
import django
from datetime import datetime
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jeffapi.settings')
django.setup()

from core.models import (
    Property, AccommodationProvider, ConversationState,
    Token, Transaction, Booking
)
from core.services.conversation_workflow import ConversationWorkflow
from core.services.booking_workflow import BookingWorkflow
from payment.token_service import token_service
from payment.payment_handler import payment_handler


def create_test_data():
    """Create test data for workflow testing"""
    print("Creating test data...")

    # Create test provider
    provider, created = AccommodationProvider.objects.get_or_create(
        phone_number='+263771234567',
        defaults={
            'name': 'Test Provider',
            'email': 'test@provider.com',
            'verified': True,
            'rating': 4.5
        }
    )

    if created:
        print(f"Created provider: {provider.name}")

    # Create test properties
    properties_data = [
        {
            'name': 'Blue Haven Lodge',
            'address': '123 Campus Street',
                # 'heads_per_room': 2,
            'total_rooms': 10,
            'available_rooms': 5,
            'amenities': ['wifi', 'parking', 'DSTV'],
            'price_per_semester': 540.00,  # 3 months * 180
            'price_per_month': 180.00,
            'distance_from_campus': 1.2,
            'campus_name': 'University of Zimbabwe'
        },
        {
            'name': 'Campus View Apartments',
            'address': '456 University Ave',
            # 'heads_per_room': 2,
            'total_rooms': 8,
            'available_rooms': 3,
            'amenities': ['wifi', 'kitchen', 'security'],
            'price_per_semester': 600.00,  # 3 months * 200
            'price_per_month': 200.00,
            'distance_from_campus': 0.8,
            'campus_name': 'University of Zimbabwe'
        }
    ]

    properties = []
    for prop_data in properties_data:
        property, created = Property.objects.get_or_create(
            name=prop_data['name'],
            provider=provider,
            defaults=prop_data
        )
        if created:
            print(f"Created property: {property.name}")
        properties.append(property)

    return provider, properties


def test_conversation_workflow():
    """Test the conversation workflow"""
    print("\n" + "="*50)
    print("TESTING CONVERSATION WORKFLOW")
    print("="*50)

    # Test phone number
    test_phone = '+263712345678'

    # Clean up any existing conversation
    ConversationState.objects.filter(cell_number=test_phone).delete()

    workflow = ConversationWorkflow()

    # Test 1: Greeting message
    print("\n1. Testing greeting message...")
    response = workflow.process_message(test_phone, "Hello")
    print(f"Response: {response.encode('ascii', 'ignore').decode('ascii')}")

    # Test 2: Accommodation inquiry
    print("\n2. Testing accommodation inquiry...")
    response = workflow.process_message(test_phone, "I need a 2 head room with wifi near campus for $200")
    print(f"Response: {response.encode('ascii', 'ignore').decode('ascii')}")

    # Test 3: Check conversation state
    conversation = ConversationState.objects.filter(cell_number=test_phone, is_active=True).first()
    if conversation:
        print(f"Conversation step: {conversation.current_step}")
        print(f"Context data keys: {list(conversation.context_data.keys())}")

    return test_phone


def test_token_and_payment_flow():
    """Test token creation and payment flow"""
    print("\n" + "="*50)
    print("TESTING TOKEN AND PAYMENT FLOW")
    print("="*50)

    test_phone = '+263712345678'

    # Create a test transaction and token
    transaction = Transaction.objects.create(
        cell_number=test_phone,
        transaction_number=f'TEST{datetime.now().strftime("%Y%m%d%H%M%S")}',
        amount=2.00,
        payment_method='ecocash',
        status='verified',
        pop_verified=True
    )

    # Create token
    token = Token.objects.create(
        cell_number=test_phone,
        token_number=f'JEFF-{transaction.id}-{datetime.now().strftime("%Y%m%d%H%M%S")}',
        total_uses=2,
        used_count=0,
        is_active=True,
        purchased_at=timezone.now(),
        expires_at=timezone.now() + timezone.timedelta(days=30),
        transaction=transaction
    )

    print(f"Created token: {token.token_number}")

    # Test token validation
    valid_token = token_service.get_valid_token(test_phone)
    if valid_token:
        print(f"Token validation successful: {valid_token.token_number}")
        print(f"Remaining uses: {valid_token.remaining_uses()}")
    else:
        print("Token validation failed")

    return token


def test_property_search_with_token():
    """Test property search with valid token"""
    print("\n" + "="*50)
    print("TESTING PROPERTY SEARCH WITH TOKEN")
    print("="*50)

    test_phone = '+263712345678'
    workflow = ConversationWorkflow()

    # Get conversation state
    conversation = ConversationState.objects.filter(cell_number=test_phone, is_active=True).first()
    if not conversation:
        print("No active conversation found")
        return

    # Set conversation to property listings step (simulating token validation)
    conversation.current_step = 'property_listings'
    conversation.context_data = {
        'search_results': [
            {
                'id': 'test-prop-1',
                'name': 'Blue Haven Lodge',
                'price_per_month': 180.00,
                # 'heads_per_room': 2,
                'distance_from_campus': 1.2,
                'amenities': ['wifi', 'parking', 'DSTV'],
                'available_rooms': 5,
                'campus_name': 'University of Zimbabwe',
                'match_score': 45
            }
        ]
    }
    conversation.save()

    # Test property selection
    response = workflow.process_message(test_phone, "1")
    print(f"Property selection response: {response.encode('ascii', 'ignore').decode('ascii')}")


def test_booking_workflow():
    """Test booking workflow"""
    print("\n" + "="*50)
    print("TESTING BOOKING WORKFLOW")
    print("="*50)

    booking_workflow = BookingWorkflow()

    # Test provider response handling
    test_responses = [
        "YES confirmed",
        "NO sorry it's full",
        "What program is the student studying?"
    ]

    for response in test_responses:
        print(f"\nTesting provider response: '{response}'")
        result = booking_workflow.handle_provider_response('+263771234567', response)
        print(f"Result: {result}")


def cleanup_test_data():
    """Clean up test data"""
    print("\n" + "="*50)
    print("CLEANING UP TEST DATA")
    print("="*50)

    # Delete test data
    test_phone = '+263712345678'
    ConversationState.objects.filter(cell_number=test_phone).delete()
    Token.objects.filter(cell_number=test_phone).delete()
    Transaction.objects.filter(cell_number=test_phone).delete()
    Booking.objects.filter(cell_number=test_phone).delete()

    print("Test data cleaned up")


def main():
    """Main test function"""
    print("Starting Jeff Platform Workflow Tests...")

    try:
        # Create test data
        provider, properties = create_test_data()

        # Test conversation workflow
        test_phone = test_conversation_workflow()

        # Test token and payment flow
        token = test_token_and_payment_flow()

        # Test property search with token
        test_property_search_with_token()

        # Test booking workflow
        test_booking_workflow()

        print("\n" + "="*50)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*50)

        # Clean up
        cleanup_test_data()

    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)