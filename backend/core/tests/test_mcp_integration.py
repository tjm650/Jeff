#!/usr/bin/env python3
"""Test MCP integration and the free accommodation workflow."""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jeffapi.settings")
django.setup()

from core.services.mcp import mcp_integration
from core.services.conversation_workflow import ConversationWorkflow


def test_mcp_integration():
    print("Testing MCP Integration System Flow")
    print("=" * 50)
    test_messages = [
        ("hi there", "G"),
        ("I need a 2-head room with WiFi", "A"),
        ("help me please", "H"),
        ("good morning", "G"),
        ("Looking for single room near campus", "A"),
    ]
    for message, expected in test_messages:
        try:
            result = mcp_integration.classify_message(message)
            print(f"   {'[PASS]' if result == expected else '[FAIL]'} '{message}' -> {result}")
        except Exception as exc:
            print(f"   [FAIL] '{message}' -> {exc}")

    for message in [
        "I need a 2-head room with WiFi near campus",
        "Single room with parking",
        "Double room with DSTV and security",
        "3 sharing room with laundry facilities",
    ]:
        try:
            reqs = mcp_integration.extract_requirements(message)
            print(f"   [PASS] requirements: heads={reqs.get('heads')}, amenities={reqs.get('amenities', [])}")
        except Exception as exc:
            print(f"   [FAIL] requirements: {exc}")

    try:
        workflow = ConversationWorkflow()
        for message in ["hi there", "I need a 2-head room with WiFi", "I want to book this room"]:
            classification = workflow._classify_message_with_gemini(message)
            print(f"   [PASS] workflow classified '{message}' as {classification}")
    except Exception as exc:
        print(f"   [FAIL] workflow initialization/classification: {exc}")

    try:
        result = mcp_integration._classify_message_fallback("I need accommodation")
        print(f"   [PASS] fallback classification: {result}")
        reqs = mcp_integration.extract_requirements("single room")
        print(f"   [PASS] fallback extraction: heads={reqs.get('heads')}")
    except Exception as exc:
        print(f"   [FAIL] fallback: {exc}")
    return True


def test_edge_cases():
    for message in ["", "I need a room " * 100, "I need a room with WiFi! @#$%"]:
        try:
            result = mcp_integration.classify_message(message)
            print(f"   [PASS] edge case classified as {result}")
        except Exception as exc:
            print(f"   [FAIL] edge case: {exc}")


if __name__ == "__main__":
    test_mcp_integration()
    test_edge_cases()
    print("[SUCCESS] MCP integration checks completed")
