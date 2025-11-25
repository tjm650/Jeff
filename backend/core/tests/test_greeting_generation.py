#!/usr/bin/env python3
"""
Test script to demonstrate greeting message generation from NLP processor
Shows which AI service (OpenAI or Gemini) generates the greeting response
"""

import os
import sys
import django
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jeffapi.settings')
django.setup()

from matching.nlp_processor import nlp_processor

def test_greeting_generation():
    """Test greeting generation and show which AI service was used"""

    print("[TEST] Testing Greeting Message Generation")
    print("=" * 50)

    # Test messages
    test_messages = [
        "hi",
        "hello",
        "good morning",
        "hey there",
        "greetings",
        "how are you",
        "start",
        "help"
    ]

    for message in test_messages:
        print(f"\n[INPUT] Testing: '{message}'")
        print("-" * 30)

        try:
            # Extract requirements to trigger greeting detection
            requirements = nlp_processor.extract_requirements(message)

            print(f"[DETECT] Is greeting: {nlp_processor.is_greeting_message(message)}")
            print(f"[RESPONSE] Is greeting response: {nlp_processor.is_greeting_response(requirements)}")

            if requirements and requirements.get('is_greeting'):
                # Get the greeting response
                response = nlp_processor.get_greeting_response(requirements)
                print(f"[OUTPUT] Response: {response}")

                # Try to determine which AI service was used
                service_used = determine_ai_service_used(nlp_processor, message)
                print(f"[AI] Service: {service_used}")

            else:
                print("[SKIP] Not detected as greeting")

        except Exception as e:
            print(f"[ERROR] Error: {str(e)}")

def determine_ai_service_used(nlp_processor, message):
    """Determine which AI service was used for greeting generation"""

    # Check API key availability
    has_openai = nlp_processor.openai_api_key is not None and len(nlp_processor.openai_api_key) > 0
    has_gemini = nlp_processor.gemini_api_key is not None and len(nlp_processor.gemini_api_key) > 0

    print(f"[KEY] OpenAI API: {'[OK] Available' if has_openai else '[NO] Not available'}")
    print(f"[KEY] Gemini API: {'[OK] Available' if has_gemini else '[NO] Not available'}")

    if not has_openai and not has_gemini:
        return "[NO AI] No AI services available - using fallback"

    # Try to generate response directly to see which service works
    try:
        # Try Gemini first (primary)
        if has_gemini:
            try:
                direct_response = nlp_processor._generate_greeting_response(message)
                if direct_response:
                    return "[OK] Gemini (Primary)"
            except Exception as e:
                print(f"[WARN] Gemini failed: {str(e)}")

        # Try OpenAI as fallback
        if has_openai:
            try:
                direct_response = nlp_processor._generate_greeting_response(message)
                if direct_response:
                    return "[OK] OpenAI (Fallback)"
            except Exception as e:
                print(f"[WARN] OpenAI failed: {str(e)}")

        # If both failed, check fallback
        fallback_response = nlp_processor._get_fallback_greeting_response()
        return f"[FALLBACK] Both AI services failed - using fallback: {fallback_response[:50]}..."

    except Exception as e:
        return f"[ERROR] Error determining service: {str(e)}"

def test_fallback_behavior():
    """Test fallback behavior when AI services are unavailable"""

    print("\n[TEST] Testing Fallback Behavior")
    print("=" * 50)

    # Temporarily disable API keys to test fallback
    original_openai = nlp_processor.openai_api_key
    original_gemini = nlp_processor.gemini_api_key

    # Disable both API keys
    nlp_processor.openai_api_key = None
    nlp_processor.gemini_api_key = None

    try:
        test_message = "hello"
        print(f"[INPUT] Testing with disabled AI services: '{test_message}'")

        requirements = nlp_processor.extract_requirements(test_message)
        if requirements and requirements.get('is_greeting'):
            response = nlp_processor.get_greeting_response(requirements)
            print(f"[OUTPUT] Fallback Response: {response}")
        else:
            print("[SKIP] Not detected as greeting")

    finally:
        # Restore original API keys
        nlp_processor.openai_api_key = original_openai
        nlp_processor.gemini_api_key = original_gemini

if __name__ == "__main__":
    print(f"[START] Starting greeting generation test at {datetime.now()}")
    print(f"[INFO] NLP Processor: {nlp_processor.__class__.__name__}")

    # Test normal greeting generation
    test_greeting_generation()

    # Test fallback behavior
    test_fallback_behavior()

    print("\n[SUCCESS] Greeting generation test completed!")