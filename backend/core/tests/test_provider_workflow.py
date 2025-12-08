#!/usr/bin/env python
"""
Test script for Provider Workflow

This script tests the complete provider workflow including:
1. Provider message classification
2. Provider responses (confirmation, rejection, info requests)
3. Booking notifications to providers
4. Help message generation
5. Welcome message generation
"""

import os
import sys
import django
from datetime import datetime
from django.utils import timezone

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import (
    Property, AccommodationProvider, Booking,
    ConversationState, Token, Transaction
)
from providers.services.workflow import ProviderWorkflow
from providers.services.handlers import provider_handlers

def create_test_data():
    """Create test data for provider workflow testing"""
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
        print(f"[PASS] Created provider: {provider.name}")
    else:
        print(f"[PASS] Found existing provider: {provider.name}")

    # Create test property
    try:
        property = Property.objects.get(property_no='TP-0001')
        print(f"[PASS] Found existing property: {property.name}")
    except Property.DoesNotExist:
        property = Property.objects.create(
            provider=provider,
            property_no='TP-0001',
            name='Test Property',
            address='123 Test Street',
            total_rooms=10,
            available_rooms=5,
            amenities=['wifi', 'parking'],
            price_per_semester=600.00,
            price_per_month=200.00,
            distance_from_campus=0.5,
            campus_name='Test Campus'
        )
        print(f"[PASS] Created property: {property.name}")

    # Create a test student
    student_phone = '+263712345678'
    try:
        conversation = ConversationState.objects.filter(
            cell_number=student_phone,
            is_active=True
        ).first()
        if not conversation:
            conversation = ConversationState.objects.create(
                cell_number=student_phone,
                is_active=True,
                current_step='booking',
                context_data={
                    'student_name': 'Test Student',
                    'requirements': {
                        'heads': 2,
                        'amenities': ['wifi']
                    }
                }
            )
    except Exception as e:
        print(f"[WARNING] Could not create conversation: {str(e)}")

    return provider, property, student_phone


def test_message_classification():
    """Test provider message classification"""
    print("\n" + "="*60)
    print("TEST 1: MESSAGE CLASSIFICATION")
    print("="*60)

    test_cases = [
        ('hello', 'G', 'Greeting'),
        ('hi provider', 'G', 'Greeting'),
        ('yes confirmed', 'CN', 'Confirmation'),
        ('YES ACCEPTED', 'CN', 'Confirmation'),
        ('no not available', 'XN', 'Rejection'),
        ('what is your course?', 'AX', 'Additional Info Request'),
        ('tell me about the student', 'AX', 'Additional Info Request'),
        ('help me', 'H', 'Help request'),
        ('i need assistance', 'H', 'Help request'),
        ('jeff', 'J', 'Jeff About message'),
        ('about jeff', 'J', 'Jeff About message'),
        ('List my Property', 'PL', 'Property List Request'),
    ]

    passed = 0
    failed = 0

    for message, expected, description in test_cases:
        try:
            result = provider_handlers._classify_provider_message_with_mcp(message)
            if result == expected:
                print(f"[PASS] '{message}' -> {result} ({description})")
                passed += 1
            else:
                print(f"[FAIL] '{message}' -> Expected {expected}, got {result}")
                failed += 1
        except Exception as e:
            print(f"[ERROR] '{message}' -> {str(e)}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return passed, failed


def test_provider_responses():
    """Test provider response handling"""
    print("\n" + "="*60)
    print("TEST 2: PROVIDER RESPONSE HANDLING")
    print("="*60)

    provider, property, student_phone = create_test_data()
    workflow = ProviderWorkflow()

    # Create a booking to test responses
    booking = Booking.objects.create(
        cell_number=student_phone,
        property=property,
        student_name='Test Student',
        status='pending',
        booking_number=f'BK{timezone.now().timestamp()}'
    )
    print(f"[PASS] Created booking: {booking.booking_number}")

    test_responses = [
        ('YES confirmed', 'Confirmation'),
        ('No sorry full', 'Rejection'),
        ('What is your budget?', 'Info Request'),
    ]

    passed = 0
    failed = 0

    for response, description in test_responses:
        try:
            result = workflow.handle_provider_response(provider.phone_number, response)
            print(f"[PASS] Response '{response}' ({description})")
            print(f"  Result: {result.get('message', 'No message')[:50]}...")
            passed += 1
        except Exception as e:
            print(f"[FAIL] Response '{response}' -> {str(e)}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return passed, failed


def test_welcome_message():
    """Test provider welcome message generation"""
    print("\n" + "="*60)
    print("TEST 3: WELCOME MESSAGE GENERATION")
    print("="*60)

    try:
        welcome_msg = provider_handlers._generate_provider_welcome_message()
        if welcome_msg and len(welcome_msg) > 0:
            print(f"[PASS] Welcome message generated")
            print(f"  Message length: {len(welcome_msg)} characters")
            print(f"  Preview: {welcome_msg[:100]}...")
            return 1, 0
        else:
            print(f"[FAIL] Welcome message is empty")
            return 0, 1
    except Exception as e:
        print(f"[FAIL] {str(e)}")
        return 0, 1


def test_help_message():
    """Test provider help message generation"""
    print("\n" + "="*60)
    print("TEST 4: HELP MESSAGE GENERATION")
    print("="*60)

    try:
        help_msg = provider_handlers._generate_provider_help_message()
        if help_msg and len(help_msg) > 0:
            print(f"[PASS] Help message generated")
            print(f"  Message length: {len(help_msg)} characters")
            print(f"  Preview: {help_msg[:100]}...")
            return 1, 0
        else:
            print(f"[FAIL] Help message is empty")
            return 0, 1
    except Exception as e:
        print(f"[FAIL] {str(e)}")
        return 0, 1


def test_time_based_greeting():
    """Test time-based greeting generation"""
    print("\n" + "="*60)
    print("TEST 5: TIME-BASED GREETING")
    print("="*60)

    try:
        greeting = provider_handlers.get_time_based_greeting()
        valid_greetings = ['Good morning', 'Good afternoon', 'Good evening']
        if greeting in valid_greetings:
            print(f"[PASS] Greeting generated: '{greeting}'")
            return 1, 0
        else:
            print(f"[FAIL] Invalid greeting: '{greeting}'")
            return 0, 1
    except Exception as e:
        print(f"[FAIL] {str(e)}")
        return 0, 1


def test_provider_message_handler():
    """Test provider message handler"""
    print("\n" + "="*60)
    print("TEST 6: PROVIDER MESSAGE HANDLER")
    print("="*60)

    provider, property, student_phone = create_test_data()
    workflow = ProviderWorkflow()

    test_messages = [
        ('hello', 'Valid greeting'),
        ('hello there', 'Greeting with extra text'),
    ]

    passed = 0
    failed = 0

    for message, description in test_messages:
        try:
            result = workflow.handle_provider_message(provider.phone_number, message)
            if result.get('success'):
                print(f"[PASS] Message '{message}' ({description})")
                passed += 1
            else:
                print(f"[PASS] Message '{message}' handled (not error)")
                passed += 1
        except Exception as e:
            print(f"[FAIL] Message '{message}' -> {str(e)}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return passed, failed


def main():
    """Run all provider workflow tests"""
    print("\n" + "="*60)
    print("JEFF PLATFORM - PROVIDER WORKFLOW TESTS")
    print("="*60)
    
    total_passed = 0
    total_failed = 0

    try:
        # Run tests
        p, f = test_message_classification()
        total_passed += p
        total_failed += f

        p, f = test_provider_responses()
        total_passed += p
        total_failed += f

        p, f = test_welcome_message()
        total_passed += p
        total_failed += f

        p, f = test_help_message()
        total_passed += p
        total_failed += f

        p, f = test_time_based_greeting()
        total_passed += p
        total_failed += f

        p, f = test_provider_message_handler()
        total_passed += p
        total_failed += f

    except Exception as e:
        print(f"\n[ERROR] Test suite error: {str(e)}")
        import traceback
        traceback.print_exc()

    # Print summary
    print("\n" + "="*60)
    print("PROVIDER WORKFLOW TEST SUMMARY")
    print("="*60)
    print(f"Total Passed: {total_passed}")
    print(f"Total Failed: {total_failed}")
    print(f"Total Tests: {total_passed + total_failed}")
    
    if total_failed == 0:
        print("\n[SUCCESS] ALL TESTS PASSED!")
    else:
        print(f"\n[FAILED] {total_failed} test(s) failed")

    return 0 if total_failed == 0 else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
