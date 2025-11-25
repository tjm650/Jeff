#!/usr/bin/env python3
"""
Test script for Recommendation Service

Tests the recommendation step when no properties match user requirements.
"""

import os
import sys
import django
from datetime import datetime

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jeffapi.settings')
django.setup()

# Import necessary modules
from core.services.mcp.recommendation import get_recommendation_service
from core.services.mcp.integration import get_mcp_integration

def test_recommendation_service():
    """Test the recommendation service with no matching properties"""
    from core.services.mcp.integration import get_mcp_integration

    print("Testing Recommendation Service")
    print("=" * 50)

    # Test 0: Check global instances
    print("0. Checking Global Instances:")
    from core.services.mcp import mcp_integration, recommendation_service
    print(f"   mcp_integration: {mcp_integration}")
    print(f"   recommendation_service: {recommendation_service}")
    if mcp_integration:
        print(f"   mcp_integration.recommendation_service: {mcp_integration.recommendation_service}")
    print()

    # Test 1: Test with requirements that won't match any properties
    print("1. Testing with no matching requirements:")
    requirements = {
        'heads': 5,  # Assuming no 5-head rooms
        'budget_max': 50.00,  # Very low budget
        'amenities': ['swimming_pool', 'gym'],  # Unlikely amenities
        'location_context': 'very_far_from_campus'
    }

    try:
        service = get_recommendation_service()
        print(f"   Service: {service}")
        summary = service.generate_recommendation_summary(requirements)
        print(f"   Recommendation Summary:\n{summary}")
        print("   [PASS] Recommendation generated successfully")
    except Exception as e:
        print(f"   [FAIL] Error generating recommendation: {str(e)}")

    print()

    # Test 2: Check MCP integration status
    print("2. Testing MCP Integration Status:")
    mcp_instance = get_mcp_integration()
    if mcp_instance:
        print(f"   MCP Configured: {mcp_instance.is_configured()}")
        if mcp_instance.is_configured():
            print(f"   Gemini Handler: {mcp_instance.gemini_handler is not None}")
            print(f"   Anthropic Handler: {mcp_instance.anthropic_handler is not None}")
        else:
            print("   MCP not configured - using fallback")
    else:
        print("   MCP integration not available")

    print()

    # Test 3: Test fallback behavior
    print("3. Testing Fallback Behavior:")
    try:
        # Temporarily disable MCP to test fallback
        mcp_instance = get_mcp_integration()
        original_config = mcp_instance.is_configured() if mcp_instance else False
        if mcp_instance:
            mcp_instance._configured = False  # Simulate not configured

        summary_fallback = service.generate_recommendation_summary(requirements)
        print(f"   Fallback Summary:\n{summary_fallback}")
        print("   [PASS] Fallback recommendation generated")

        # Restore original config
        if mcp_instance:
            mcp_instance._configured = original_config

    except Exception as e:
        print(f"   [FAIL] Error in fallback: {str(e)}")

    print()

    # Test 4: Test with empty requirements
    print("4. Testing with empty requirements:")
    try:
        empty_requirements = {}
        summary_empty = service.generate_recommendation_summary(empty_requirements)
        print(f"   Empty Requirements Summary:\n{summary_empty}")
        print("   [PASS] Empty requirements handled")
    except Exception as e:
        print(f"   [FAIL] Error with empty requirements: {str(e)}")

    print()

    # Test 5: Test the import in step_handlers
    print("5. Testing Step Handlers Import:")
    try:
        from core.services.mcp.integration import get_mcp_integration
        imported_mcp = get_mcp_integration()
        print(f"   Imported mcp_integration: {imported_mcp}")
        if imported_mcp and imported_mcp.recommendation_service:
            print("   [PASS] Step handlers import working")
        else:
            print("   [FAIL] Step handlers import not working")
    except Exception as e:
        print(f"   [FAIL] Error in step handlers import: {str(e)}")

    print()

    # Test 6: Test property search with no matches
    print("6. Testing Property Search with No Matches:")
    try:
        from core.services.conversation.property_search import property_search_handler
        from core.models import ConversationState

        # Create a mock conversation
        conversation = ConversationState(cell_number='test123', current_step='inquiry', is_active=True)
        conversation.save()

        # Test with requirements that won't match
        requirements = {
            'heads': 10,
            'budget_max': 10.00,
            'amenities': ['nonexistent_amenity']
        }

        result = property_search_handler.proceed_to_property_search(conversation, requirements)
        print(f"   Property Search Result:\n{result}")
        print("   [PASS] Property search with no matches handled")

        # Clean up
        conversation.delete()

    except Exception as e:
        print(f"   [FAIL] Error in property search: {str(e)}")

    print()
    print("Recommendation Test Complete!")
    print("=" * 50)

if __name__ == "__main__":
    try:
        test_recommendation_service()
        print("\n[SUCCESS] All recommendation tests completed!")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n[WARNING] Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[CRASH] Test suite crashed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)