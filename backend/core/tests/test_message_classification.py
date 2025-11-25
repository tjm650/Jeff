#!/usr/bin/env python3
"""
Test script to demonstrate message classification using Gemini AI
Tests the new classify_message() function that returns single character keys:
- G for Greeting message
- A for Accommodation enquiry message
- H for Help message
- P for Payment message (get.token: 0717718865)
"""

import os
import sys
import django
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jeffapi.settings')
django.setup()

from matching.nlp_processor import nlp_processor

def test_message_classification():
    """Test message classification with various message types"""

    print("[TEST] Testing Message Classification with Gemini")
    print("=" * 60)

    # Test messages for each category
    test_cases = [
        # Greeting messages (G)
        ("hi", "G", "Simple greeting"),
        ("hello", "G", "Simple greeting"),
        ("good morning", "G", "Morning greeting"),
        ("hey there", "G", "Casual greeting"),
        ("how are you", "G", "Greeting with question"),
        ("nice to meet you", "G", "Introduction greeting"),

        # Accommodation enquiry messages (A)
        ("I'm looking for a single room", "A", "Single room enquiry"),
        ("I need a 2-head room with WiFi", "A", "Room with amenities"),
        ("Looking for accommodation near campus", "A", "Location-based enquiry"),
        ("Double room for $150 max", "A", "Budget specified"),
        ("I need a place to stay", "A", "General accommodation request"),
        ("Looking for a room with parking", "A", "Amenity requirement"),

        # Help messages (H)
        ("help", "H", "Direct help request"),
        ("how do I use this service", "H", "Usage question"),
        ("can you assist me", "H", "Assistance request"),
        ("what can you do", "H", "Capability question"),
        ("help me find accommodation", "H", "Help with accommodation"),

        # Payment messages (P)
        ("get.token: 0717718865", "P", "Token request"),
        ("I need to make payment", "P", "Payment request"),
        ("how do I pay", "P", "Payment question"),
        ("get.token", "P", "Token keyword"),
        ("payment token please", "P", "Payment token request"),
    ]

    correct_predictions = 0
    total_predictions = len(test_cases)

    for message, expected, description in test_cases:
        print(f"\n[INPUT] '{message}'")
        print(f"[DESC] {description}")
        print("-" * 40)

        try:
            # Classify the message
            classification = nlp_processor.classify_message(message)

            print(f"[EXPECTED] {expected}")
            print(f"[ACTUAL] {classification}")

            if classification == expected:
                print("[RESULT] CORRECT")
                correct_predictions += 1
            else:
                print("[RESULT] WRONG")

            # Show fallback classification for comparison
            fallback_classification = nlp_processor._classify_message_fallback(message)
            print(f"[FALLBACK] {fallback_classification}")

        except Exception as e:
            print(f"[ERROR] {str(e)}")
            print("[RESULT] ERROR")

    # Print summary
    print(f"\n[SUMMARY] Classification Results")
    print("=" * 60)
    print(f"Correct: {correct_predictions}/{total_predictions}")
    print(f"Accuracy: {((correct_predictions/total_predictions)*100):.1f}%")

    if correct_predictions == total_predictions:
        print("All classifications were correct!")
    elif correct_predictions >= total_predictions * 0.8:
        print("Good accuracy achieved!")
    else:
        print("Accuracy could be improved")

def test_real_world_messages():
    """Test with real-world message examples"""

    print("\n[TEST] Testing Real-World Messages")
    print("=" * 60)

    real_messages = [
        "Hi Jeff, I'm new here",
        "I need accommodation for 3 people",
        "Hello! Can you help me?",
        "get.token: 0717718865",
        "Looking for a single room near campus, max $150",
        "How does this work?",
        "Good evening",
        "I want to pay for the service",
        "Need a double room with WiFi and parking",
        "help",
    ]

    for message in real_messages:
        print(f"\n[INPUT] '{message}'")
        print("-" * 40)

        try:
            classification = nlp_processor.classify_message(message)
            fallback = nlp_processor._classify_message_fallback(message)

            print(f"[GEMINI] {classification}")
            print(f"[FALLBACK] {fallback}")

            # Show what each classification means
            classification_meanings = {
                'G': 'Greeting message',
                'A': 'Accommodation enquiry',
                'H': 'Help message',
                'P': 'Payment message'
            }

            print(f"[MEANING] {classification_meanings.get(classification, 'Unknown')}")

        except Exception as e:
            print(f"[ERROR] {str(e)}")

def test_edge_cases():
    """Test edge cases and ambiguous messages"""

    print("\n[TEST] Testing Edge Cases")
    print("=" * 60)

    edge_cases = [
        "Hi, I need help finding accommodation",
        "Hello, get.token: 0717718865",
        "I'm looking for help with payment",
        "Good morning, I need a room",
        "Can you help me get.token: 0717718865",
    ]

    for message in edge_cases:
        print(f"\n[INPUT] '{message}'")
        print("-" * 40)

        try:
            classification = nlp_processor.classify_message(message)
            fallback = nlp_processor._classify_message_fallback(message)

            print(f"[GEMINI] {classification}")
            print(f"[FALLBACK] {fallback}")

        except Exception as e:
            print(f"[ERROR] {str(e)}")

if __name__ == "__main__":
    print(f"[START] Starting message classification test at {datetime.now()}")
    print(f"[INFO] NLP Processor: {nlp_processor.__class__.__name__}")

    # Test basic classification
    test_message_classification()

    # Test real-world messages
    test_real_world_messages()

    # Test edge cases
    test_edge_cases()

    print("\n[SUCCESS] Message classification test completed!")