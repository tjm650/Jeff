#/usr/bin/env python
"""
Test script for Jeff Platform workflow - User without active token

This script tests the complete workflow for a user who does not have an active token,
simulating the accommodation enquiry flow from start to payment request.
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
from payment.token_service import token_service


def _safe_print(text):
    """Safely print text handling Unicode encoding issues"""
    try:
        return text.encode('ascii', 'ignore').decode('ascii')
    except:
        return str(text)


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


def test_user_without_token_workflow():
    """Test complete workflow for user without active token"""
    print("\n" + "="*60)
    print("TESTING USER WITHOUT ACTIVE TOKEN WORKFLOW")
    print("="*60)

    # Test phone number for user without token
    test_phone = '+263712345679'

    # Clean up any existing data for this user
    print(f"Cleaning up existing data for {test_phone}...")
    ConversationState.objects.filter(cell_number=test_phone).delete()
    Token.objects.filter(cell_number=test_phone).delete()
    Transaction.objects.filter(cell_number=test_phone).delete()
    Booking.objects.filter(cell_number=test_phone).delete()

    # Verify user has no tokens
    existing_tokens = token_service.get_student_tokens(test_phone)
    print(f"Existing tokens for {test_phone}: {len(existing_tokens)}")

    valid_token = token_service.get_valid_token(test_phone)
    print(f"Valid token check: {valid_token is not None}")

    workflow = ConversationWorkflow()

    # Test 1: Initial greeting/inquiry
    print("\n1. Testing initial inquiry...")
    response = workflow.process_message(test_phone, "Hello, I need accommodation")
    print(f"Response: {_safe_print(response)}")

    # Test 2: Accommodation requirements
    print("\n2. Testing accommodation requirements...")
    response = workflow.process_message(test_phone, "I need a 2 head room with wifi near campus for $200 per month")
    print(f"Response: {_safe_print(response)}")

    # Test 3: Token check (should show payment instructions since no token)
    print("\n3. Testing token check (should redirect to payment)...")
    response = workflow.process_message(test_phone, "Yes")
    print(f"Response: {_safe_print(response)}")

    # Test 4: Payment request
    print("\n4. Testing payment request...")
    response = workflow.process_message(test_phone, "get.token: 0771234567")
    print(f"Response: {_safe_print(response)}")

    # Test 5: Check conversation state
    conversation = ConversationState.objects.filter(cell_number=test_phone, is_active=True).first()
    if conversation:
        print(f"Final conversation step: {conversation.current_step}")
        print(f"Context data keys: {list(conversation.context_data.keys())}")

        # Check if payment is pending
        pending_payment = conversation.context_data.get('pending_payment', {})
        if pending_payment:
            print(f"Pending payment found: {pending_payment.get('transaction_id', 'N/A')}")

    return test_phone


def test_token_validation_scenarios():
    """Test various token validation scenarios"""
    print("\n" + "="*60)
    print("TESTING TOKEN VALIDATION SCENARIOS")
    print("="*60)

    workflow = ConversationWorkflow()

    # Test scenarios with different phone numbers
    test_scenarios = [
        '+263712345680',  # No token user
        '+263712345681',  # Another no token user
    ]

    for i, phone in enumerate(test_scenarios):
        print(f"\n--- Test Scenario {i+1}: {phone} ---")

        # Clean up
        ConversationState.objects.filter(cell_number=phone).delete()
        Token.objects.filter(cell_number=phone).delete()

        # Verify no token exists
        valid_token = token_service.get_valid_token(phone)
        print(f"Has valid token: {valid_token is not None}")

        # Test inquiry flow
        response = workflow.process_message(phone, "I need a place to stay")
        print(f"Inquiry response: {_safe_print(response[:100])}{"..." if len(response) > 100 else ""}")

        # Test token check (should show payment instructions)
        response = workflow.process_message(phone, "2 head room with wifi")
        print(f"Token check response: {_safe_print(response[:100])}{"..." if len(response) > 100 else ""}")


def test_payment_instruction_display():
    """Test that payment instructions are properly displayed"""
    print("\n" + "="*60)
    print("TESTING PAYMENT INSTRUCTION DISPLAY")
    print("="*60)

    test_phone = '+263712345682'
    workflow = ConversationWorkflow()

    # Clean up
    ConversationState.objects.filter(cell_number=test_phone).delete()
    Token.objects.filter(cell_number=test_phone).delete()

    # Test various inquiry messages that should lead to payment instructions
    inquiry_messages = [
        "Hello",
        "I need accommodation",
        "Looking for a 2 head room",
        "Need place near campus",
        "Hi, I want to find accommodation"
    ]

    for message in inquiry_messages:
        print(f"\n--- Testing: '{message}' ---")

        # Clean conversation for each test
        ConversationState.objects.filter(cell_number=test_phone).delete()

        response = workflow.process_message(test_phone, message)
        print(f"Response: {_safe_print(response)}")

        # Check if response contains payment instructions
        payment_keywords = ['token', 'payment', 'get.token', 'EcoCash', '$1.50']
        has_payment_info = any(keyword.lower() in response.lower() for keyword in payment_keywords)
        print(f"Contains payment instructions: {has_payment_info}")


def test_error_handling_scenarios():
    """Test error handling for invalid scenarios"""
    print("\n" + "="*60)
    print("TESTING ERROR HANDLING SCENARIOS")
    print("="*60)

    test_phone = '+263712345683'
    workflow = ConversationWorkflow()

    # Clean up
    ConversationState.objects.filter(cell_number=test_phone).delete()
    Token.objects.filter(cell_number=test_phone).delete()

    # Test invalid payment format
    print("\n1. Testing invalid payment format...")
    response = workflow.process_message(test_phone, "get.token: invalid_format")
    print(f"Response: {_safe_print(response)}")

    # Test invalid phone number format
    print("\n2. Testing invalid phone number...")
    response = workflow.process_message(test_phone, "get.token: 123")
    print(f"Response: {_safe_print(response)}")

    # Test empty payment request
    print("\n3. Testing empty payment request...")
    response = workflow.process_message(test_phone, "get.token:")
    print(f"Response: {_safe_print(response)}")


def cleanup_test_data():
    """Clean up test data"""
    print("\n" + "="*60)
    print("CLEANING UP TEST DATA")
    print("="*60)

    # Delete test data for all test phone numbers
    test_phones = [
        '+263712345679', '+263712345680', '+263712345681',
        '+263712345682', '+263712345683'
    ]

    for phone in test_phones:
        ConversationState.objects.filter(cell_number=phone).delete()
        Token.objects.filter(cell_number=phone).delete()
        Transaction.objects.filter(cell_number=phone).delete()
        Booking.objects.filter(cell_number=phone).delete()

    print("Test data cleaned up")


def main():
    """Main test function"""
    print("Starting Jeff Platform No-Token Workflow Tests...")

    try:
        # Create test data
        provider, properties = create_test_data()

        # Test main workflow for user without token
        test_phone = test_user_without_token_workflow()

        # Test token validation scenarios
        test_token_validation_scenarios()

        # Test payment instruction display
        test_payment_instruction_display()

        # Test error handling
        test_error_handling_scenarios()

        print("\n" + "="*60)
        print("ALL NO-TOKEN WORKFLOW TESTS COMPLETED SUCCESSFULLY")
        print("="*60)

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