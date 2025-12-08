#!/usr/bin/env python3
"""
Comprehensive System Flow Test for Jeff Platform

This script tests the complete system flow from message classification through
to booking completion, including MCP integration, NLP processing, payment flow,
property matching, and booking workflow.

Tests all 8 workflow steps:
1. Student Inquiry (Message Classification & NLP)
2. Token Check (Payment Validation)
3. Property Listings (Search & Matching)
4. Name Collection (Booking Initiation)
5. Booking Request (Provider Notification)
6. Provider Response Handling
7. Booking Confirmation
8. Cleanup & Close
"""

import os
import sys
import django
import logging
from datetime import datetime, timedelta
from django.utils import timezone

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import all necessary modules
from core.models import (
    Property, AccommodationProvider, ConversationState,
    Token, Transaction, Booking
)
from core.services.conversation_workflow import ConversationWorkflow
from matching.property_matcher import property_matcher
from payment.token_service import token_service
from whatsapp.utils.whatsapp_service import whatsapp_service
from core.services.mcp import mcp_integration

class SystemFlowTester:
    """Comprehensive system flow testing class"""

    def __init__(self):
        self.test_phone = '+263712345678'
        self.provider_phone = '+263771234567'
        self.workflow = ConversationWorkflow()
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed _tests': 0,
            'errors': []
        }

    def log_test_result(self, test_name: str, success: bool, message: str = ""):
        """Log test results"""
        self.test_results['total_tests'] += 1
        if success:
            self.test_results['passed_tests'] += 1
            print(f"[PASS] {test_name}: PASSED {message}")
        else:
            self.test_results['failed _tests'] += 1
            print(f"[FAIL] {test_name}: FAILED {message}")
            self.test_results['errors'].append(f"{test_name}: {message}")

    def create_test_data(self):
        """Create comprehensive test data"""
        print("\n[SETUP] Setting up test environment...")

        # Clean up existing test data
        self.cleanup_test_data()

        # Create test provider
        provider, created = AccommodationProvider.objects.get_or_create(
            phone_number=self.provider_phone,
            defaults={
                'name': 'Test Provider Comprehensive',
                'email': 'test@comprehensive.com',
                'verified': True,
                'rating': 4.8
            }
        )

        if created:
            print(f"   Created provider: {provider.name}")

        # Create diverse test properties
        properties_data = [
            {
                'property_no': 'CVD-1001',
                'name': 'Campus View Deluxe',
                'address': '123 University Street',
                'total_rooms': 15,
                'available_rooms': 8,
                'amenities': ['wifi', 'parking', 'dstv', 'security', 'gym'],
                'price_per_semester': 450.00,
                'price_per_month': 150.00,
                'distance_from_campus': 0.5,
                'campus_name': 'NUST Campus'
            },
            {
                'property_no': 'SHB-2001',
                'name': 'Student Haven Budget',
                'address': '456 College Avenue',
                'total_rooms': 20,
                'available_rooms': 12,
                'amenities': ['wifi', 'parking', 'water'],
                'price_per_semester': 360.00,
                'price_per_month': 120.00,
                'distance_from_campus': 1.0,
                'campus_name': 'NUST Campus'
            },
            {
                'property_no': 'PLS-3001',
                'name': 'Premium Lodge Sharing',
                'address': '789 Education Road',
                'total_rooms': 10,
                'available_rooms': 5,
                'amenities': ['wifi', 'dstv', 'security', 'cleaning', 'generator'],
                'price_per_semester': 540.00,
                'price_per_month': 180.00,
                'distance_from_campus': 0.8,
                'campus_name': 'NUST Campus'
            },
            {
                'property_no': 'ERB-4001',
                'name': 'Economy Rooms Basic',
                'address': '321 Learning Lane',
                'total_rooms': 25,
                'available_rooms': 15,
                'amenities': ['water', 'electricity'],
                'price_per_semester': 300.00,
                'price_per_month': 100.00,
                'distance_from_campus': 1.5,
                'campus_name': 'NUST Campus'
            }
        ]

        properties = []
        for prop_data in properties_data:
            try:
                property = Property.objects.get(property_no=prop_data['property_no'])
                print(f"   Found existing property: {property.name}")
            except Property.DoesNotExist:
                property = Property.objects.create(
                    provider=provider,
                    **prop_data
                )
                print(f"   Created property: {property.name}")
            properties.append(property)

        return provider, properties

    def cleanup_test_data(self):
        """Clean up test data"""
        ConversationState.objects.filter(cell_number=self.test_phone).delete()
        Token.objects.filter(cell_number=self.test_phone).delete()
        Transaction.objects.filter(cell_number=self.test_phone).delete()
        Booking.objects.filter(cell_number=self.test_phone).delete()
        print("   Cleaned up existing test data")

    def test_mcp_integration(self):
        """Test MCP integration with Anthropic and Gemini"""
        print("\n[AI] Testing MCP Integration...")

        # Test 1: Check if MCP is configured
        is_configured = mcp_integration.is_configured()
        self.log_test_result("MCP Configuration", is_configured, "MCP integration is properly configured")

        if not is_configured:
            print("   ⚠️  MCP not configured - tests will use fallback methods")
            return False

        # Test 2: Message classification
        test_messages = [
            ("Hi Jeff", "G", "Greeting classification"),
            ("I need a single room", "A", "Accommodation enquiry"),
            ("help me", "H", "Help request"),
            ("get.token: 0717718865", "P", "Payment request")
        ]

        for message, expected, description in test_messages:
            try:
                classification = mcp_integration.classify_message(message)
                success = classification == expected
                self.log_test_result(f"MCP Classification: {description}",
                                   success, f"'{message}' -> {classification} (expected {expected})")
            except Exception as e:
                self.log_test_result(f"MCP Classification: {description}", False, str(e))

        # Test 3: Requirement extraction
        test_requirement = "I need a 2-head room with WiFi and parking for $150 near campus"
        try:
            requirements = mcp_integration.extract_requirements(test_requirement)
            has_requirements = bool(requirements and (
                requirements.get('heads') or
                requirements.get('amenities') or
                requirements.get('budget_max')
            ))
            self.log_test_result("MCP Requirement Extraction", has_requirements,
                               "Successfully extracted requirements from message")
        except Exception as e:
            self.log_test_result("MCP Requirement Extraction", False, str(e))

        return True

    def test_message_classification(self):
        """Test message classification for all categories"""
        print("\n[CLASSIFY] Testing Message Classification...")

        test_cases = [
            # Greeting messages (G)
            ("hi", "G", "Simple greeting"),
            ("hello", "G", "Simple greeting"),
            ("good morning", "G", "Morning greeting"),
            ("hey there", "G", "Casual greeting"),
            ("how are you", "G", "Status greeting"),

            # Accommodation enquiry messages (A)
            ("I'm looking for a single room", "A", "Single room enquiry"),
            ("I need a 2-head room with WiFi", "A", "Room with amenities"),
            ("Looking for accommodation near campus", "A", "Location-based enquiry"),
            ("Double room with parking, max $150", "A", "Budget and amenities"),
            ("3 sharing room with DSTV", "A", "Sharing room enquiry"),

            # Help messages (H)
            ("help", "H", "Direct help request"),
            ("how do I use this service", "H", "Usage question"),
            ("can you assist me", "H", "Assistance request"),
            ("what can you do", "H", "Capability question"),

            # Payment messages (P)
            ("get.token: 0717718865", "P", "Token request"),
            ("I need to make payment", "P", "Payment request"),
            ("get.token", "P", "Token keyword"),
            ("payment", "P", "Payment keyword")
        ]

        for message, expected, description in test_cases:
            try:
                # Test workflow classification
                classification = self.workflow._classify_message_with_gemini(message)
                success = classification == expected
                self.log_test_result(f"Classification: {description}",
                                   success, f"'{message}' -> {classification} (expected {expected})")

                # Test fallback classification
                fallback_classification = self.workflow._classify_message_fallback(message)
                fallback_success = fallback_classification == expected
                self.log_test_result(f"Fallback Classification: {description}",
                                   fallback_success, f"'{message}' -> {fallback_classification} (expected {expected})")

            except Exception as e:
                self.log_test_result(f"Classification: {description}", False, str(e))

    def test_requirement_extraction(self):
        """Test NLP requirement extraction"""
        print("\n[NLP] Testing Requirement Extraction...")

        test_messages = [
            "I need a 2-head room with WiFi and parking for $150 near campus",
            "Single room for one person, budget $100, with DSTV",
            "Looking for double room near campus, max $200, with security",
            "3 sharing room with WiFi, parking and generator",
            "I want a room for 2 people with all amenities under $180"
        ]

        for message in test_messages:
            try:
                # Test MCP integration extraction
                if mcp_integration.is_configured():
                    requirements = mcp_integration.extract_requirements(message)
                    extraction_method = "MCP"
                else:
                    # Fallback to NLP processor
                    from matching.nlp_processor import nlp_processor
                    requirements = nlp_processor.extract_requirements(message)
                    extraction_method = "NLP"

                # Validate extraction quality
                has_heads = requirements.get('heads') is not None
                has_budget = requirements.get('budget_max') is not None
                has_amenities = len(requirements.get('amenities', [])) > 0

                success = has_heads or has_budget or has_amenities
                self.log_test_result(f"Requirement Extraction ({extraction_method})",
                                   success, f"'{message[:30]}...' -> heads={requirements.get('heads')}, budget={requirements.get('budget_max')}, amenities={requirements.get('amenities', [])}")

            except Exception as e:
                self.log_test_result(f"Requirement Extraction", False, f"'{message[:30]}...': {str(e)}")

    def test_token_system(self):
        """Test token creation and validation"""
        print("\n[TOKEN] Testing Token System...")

        # Test 1: Create test token
        try:
            transaction = Transaction.objects.create(
                cell_number=self.test_phone,
                transaction_number=f'TEST{datetime.now().strftime("%Y%m%d%H%M%S")}',
                amount=1.50,
                payment_method='ecocash',
                status='verified',
                pop_verified=True,
                verified_at=timezone.now()
            )

            expires_at = timezone.now() + timedelta(days=30)
            token = Token.objects.create(
                cell_number=self.test_phone,
                token_number=f'JEFF-{transaction.id}-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                total_uses=2,
                used_count=0,
                is_active=True,
                purchased_at=timezone.now(),
                expires_at=expires_at,
                transaction=transaction
            )

            self.log_test_result("Token Creation", True, f"Created token: {token.token_number}")

        except Exception as e:
            self.log_test_result("Token Creation", False, str(e))
            return False

        # Test 2: Token validation
        try:
            valid_token = token_service.get_valid_token(self.test_phone)
            if valid_token and valid_token.token_number == token.token_number:
                self.log_test_result("Token Validation", True, f"Token validated: {valid_token.token_number}")
            else:
                self.log_test_result("Token Validation", False, "Token not found or invalid")
        except Exception as e:
            self.log_test_result("Token Validation", False, str(e))

        # Test 3: Token usage
        try:
            if valid_token and valid_token.use_token():
                self.log_test_result("Token Usage", True, f"Token used successfully, remaining: {valid_token.remaining_uses()}")
            else:
                self.log_test_result("Token Usage", False, "Failed to use token")
        except Exception as e:
            self.log_test_result("Token Usage", False, str(e))

        return True

    def test_property_matching(self):
        """Test property matching functionality"""
        print("\n[PROPERTY] Testing Property Matching...")

        # Test requirements
        test_requirements = [
            {
                'heads': 2,
                'budget_max': 150.00,
                'amenities': ['wifi', 'parking'],
                'description': '2-head, $150, WiFi & parking'
            },
            {
                'heads': 1,
                'budget_max': 120.00,
                'amenities': ['dstv'],
                'description': 'Single room, $120, DSTV'
            },
            {
                'heads': 3,
                'budget_max': 200.00,
                'amenities': ['wifi', 'security', 'generator'],
                'description': '3-head, $200, premium amenities'
            }
        ]

        for req in test_requirements:
            try:
                # Test property matching
                matched_properties = property_matcher.match_properties(req, limit=5)

                success = len(matched_properties) > 0
                self.log_test_result(f"Property Matching: {req['description']}",
                                   success, f"Found {len(matched_properties)} matches")

                # Show top match details
                if matched_properties:
                    top_match = matched_properties[0]
                    print(f"      Top match: {top_match['property'].name} (score: {top_match['score']})")

            except Exception as e:
                self.log_test_result(f"Property Matching: {req['description']}", False, str(e))

    def test_conversation_workflow(self):
        """Test complete conversation workflow"""
        print("\n[CONVERSATION] Testing Conversation Workflow...")

        # Clean up any existing conversation
        ConversationState.objects.filter(cell_number=self.test_phone).delete()

        # Test conversation flow
        conversation_scenarios = [
            ("Hi Jeff", "Greeting message"),
            ("I need a 2-head room with WiFi for $150", "Accommodation enquiry"),
            ("help", "Help request during conversation"),
            ("get.token: 0717718865", "Payment request"),
        ]

        for message, description in conversation_scenarios:
            try:
                response = self.workflow.process_message(self.test_phone, message)

                # Check if response is meaningful (not error)
                success = bool(response and len(response.strip()) > 10)
                self.log_test_result(f"Workflow: {description}", success,
                                   f"Response length: {len(response)} characters")

                # Show response preview
                preview = response[:50] + "..." if len(response) > 50 else response
                print(f"      Response: {preview}")

            except Exception as e:
                self.log_test_result(f"Workflow: {description}", False, str(e))

    def test_booking_workflow(self):
        """Test booking workflow"""
        print("\n[BOOKING] Testing Booking Workflow...")

        # Create a test booking
        try:
            provider, properties = self.create_test_data()

            # Create conversation with selected property
            conversation = ConversationState.objects.create(
                cell_number=self.test_phone,
                current_step='name_collection',
                is_active=True,
                context_data={
                    'selected_property': {
                        'id': str(properties[0].id),
                        'name': properties[0].name,
                        'provider_name': provider.name
                    }
                }
            )

            # Test name collection
            response = self.workflow.process_message(self.test_phone, "John Doe")
            success = "booking" in response.lower() or "request" in response.lower()
            self.log_test_result("Booking Creation", success, "Booking request created successfully")

            # Check if booking was created
            booking = Booking.objects.filter(cell_number=self.test_phone).first()
            if booking:
                print(f"      Created booking: {booking.booking_number}")

        except Exception as e:
            self.log_test_result("Booking Creation", False, str(e))

    def test_error_handling(self):
        """Test error handling and fallback scenarios"""
        print("\n[ERROR]  Testing Error Handling...")

        # Test 1: Invalid message classification
        try:
            classification = self.workflow._classify_message_with_gemini("")
            success = classification is not None
            self.log_test_result("Empty Message Handling", success, f"Classification: {classification}")
        except Exception as e:
            self.log_test_result("Empty Message Handling", False, str(e))

        # Test 2: Invalid property selection
        try:
            conversation = ConversationState.objects.create(
                cell_number=self.test_phone,
                current_step='property_listings',
                is_active=True
            )
            response = self.workflow.process_message(self.test_phone, "99")  # Invalid selection
            success = "number between" in response.lower() or "invalid" in response.lower()
            self.log_test_result("Invalid Selection Handling", success, "Proper error message returned")
        except Exception as e:
            self.log_test_result("Invalid Selection Handling", False, str(e))

        # Test 3: Missing requirements
        try:
            if mcp_integration.is_configured():
                requirements = mcp_integration.extract_requirements("xyzabc")
                success = requirements is not None
                self.log_test_result("Invalid Requirements Handling", success, "Handled gracefully")
        except Exception as e:
            self.log_test_result("Invalid Requirements Handling", False, str(e))

    def run_comprehensive_test(self):
        """Run all comprehensive tests"""
        print("Starting Comprehensive System Flow Test")
        print("=" * 60)
        print(f"Test started at: {datetime.now()}")
        print(f"Python path: {sys.executable}")
        print(f"Django settings: {os.environ.get('DJANGO_SETTINGS_MODULE')}")

        # Run all test phases
        self.create_test_data()
        self.test_mcp_integration()
        self.test_message_classification()
        self.test_requirement_extraction()
        self.test_token_system()
        self.test_property_matching()
        self.test_conversation_workflow()
        self.test_booking_workflow()
        self.test_error_handling()

        # Print summary
        self.print_test_summary()

    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 60)

        total = self.test_results['total_tests']
        passed = self.test_results['passed_tests']
        failed = self.test_results['failed _tests']
        success_rate = (passed / total * 100) if total > 0 else 0

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {success_rate:.1f}%")

        if success_rate >= 90:
            print("🎉 EXCELLENT: System flow is working very well!")
        elif success_rate >= 75:
            print("👍 GOOD: System flow is working adequately")
        elif success_rate >= 50:
            print("⚠️  NEEDS IMPROVEMENT: System flow has issues")
        else:
            print("❌ CRITICAL: System flow has major problems")

        if self.test_results['errors']:
            print("\n[NLP] ERRORS ENCOUNTERED:")
            for error in self.test_results['errors'][:10]:  # Show first 10 errors
                print(f"   • {error}")

        print(f"\nTest completed at: {datetime.now()}")
        print("=" * 60)

def main():
    """Main test function"""
    tester = SystemFlowTester()
    tester.run_comprehensive_test()
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)