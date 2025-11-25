"""
NLP processing handlers for conversation workflow

This module handles NLP processing operations including:
- NLP requirements processing and enhancement
- Requirements validation
- Confidence score calculation
- Requirement summary generation
"""

import logging
from typing import Dict
from django.utils import timezone

logger = logging.getLogger(__name__)


class NLPProcessorHandler:
    """NLP processing functionality for conversation workflow"""

    def process_nlp_requirements(self, raw_requirements: Dict, nlp_processor) -> Dict:
        """Process and enhance raw requirements from NLP processor"""
        try:
            if not raw_requirements:
                return {}

            # If it's a greeting response, return as-is for greeting flow
            if nlp_processor.is_greeting_response(raw_requirements):
                return raw_requirements

            # Enhance requirements with additional context
            processed_requirements = raw_requirements.copy()

            # Add processing metadata
            processed_requirements['nlp_processing_timestamp'] = timezone.now().isoformat()
            processed_requirements['confidence_score'] = self._calculate_confidence_score(raw_requirements)

            # Get rental period if specified
            message = processed_requirements.get('original_message', '')
            if message:
                from ....matching.rental_period_extractor import rental_period_extractor
                rental_period = rental_period_extractor.extract_rental_period(message)
                if rental_period:
                    processed_requirements['rental_period'] = rental_period
                    # Update confidence score for having rental period
                    processed_requirements['confidence_score'] += 0.1

            # Add derived fields for better matching
            if processed_requirements.get('heads') and processed_requirements.get('budget_max'):
                # Calculate price per head for better matching
                processed_requirements['price_per_head'] = round(
                    processed_requirements['budget_max'] / processed_requirements['heads'], 2
                )

            # Add requirement summary for display
            processed_requirements['requirement_summary'] = self._generate_requirement_summary(processed_requirements)

            return processed_requirements

        except Exception as e:
            logger.error(f"Error processing NLP requirements: {str(e)}")
            return raw_requirements or {}

    def extract_requirements(self, message: str) -> Dict:
        """Extract and process requirements from message using MCP or fallback to NLP processor"""
        try:
            from ..mcp import mcp_integration
            if mcp_integration.is_configured():
                raw_requirements = mcp_integration.extract_requirements(message)
                # Add original message for rental period extraction
                raw_requirements['original_message'] = message
                # For backward compatibility, create a mock nlp_processor object
                class MockNLPProcessor:
                    def validate_requirements(self, reqs): return mcp_integration.validate_requirements(reqs)
                    def format_requirements_for_display(self, reqs): return mcp_integration.format_requirements_for_display(reqs)
                    def is_greeting_message(self, msg): return mcp_integration.is_greeting_message(msg)
                    def is_greeting_response(self, reqs): return mcp_integration.is_greeting_response(reqs)
                    def get_greeting_response(self, reqs): return mcp_integration.get_greeting_response(reqs)
                    def extract_requirements(self, msg): return mcp_integration.extract_requirements(msg)

                nlp_processor = MockNLPProcessor()
            else:
                from ....matching.nlp_processor import nlp_processor
                raw_requirements = nlp_processor.extract_requirements(message)
                raw_requirements['original_message'] = message

            # Process the requirements
            processed_requirements = self.process_nlp_requirements(raw_requirements, nlp_processor)

            # Check if rental period needs clarification
            if not processed_requirements.get('rental_period'):
                from ....matching.rental_period_extractor import rental_period_extractor
                clarification_msg = rental_period_extractor.suggest_rental_period()
                processed_requirements['needs_rental_period_clarification'] = True
                processed_requirements['rental_period_clarification_message'] = clarification_msg

            return processed_requirements
        except Exception as e:
            logger.error(f"Error extracting requirements: {str(e)}")
            return {}

    def has_valid_requirements(self, requirements: Dict) -> bool:
        """Check if requirements contain valid accommodation criteria"""
        if not requirements:
            return False

        # Check for core accommodation requirements
        valid_criteria = [
            requirements.get('heads'),
            requirements.get('amenities'),
            requirements.get('budget_max'),
            requirements.get('location_context'),
            requirements.get('gender_preference')
        ]

        # Must have at least one valid criterion
        return any(valid_criteria)

    def _calculate_confidence_score(self, requirements: Dict) -> float:
        """Calculate confidence score for extracted requirements"""
        try:
            score = 0.0
            factors = 0

            # Score based on requirement completeness
            if requirements.get('heads'):
                score += 0.3
                factors += 1

            if requirements.get('budget_max'):
                score += 0.25
                factors += 1

            if requirements.get('amenities'):
                score += 0.2
                factors += 1

            if requirements.get('location_context'):
                score += 0.15
                factors += 1

            if requirements.get('gender_preference'):
                score += 0.1
                factors += 1

            # Return average score or 0 if no factors
            return round(score / max(factors, 1), 2)

        except Exception as e:
            logger.error(f"Error calculating confidence score: {str(e)}")
            return 0.0

    def _generate_requirement_summary(self, requirements: Dict) -> str:
        """Generate a human-readable summary of requirements"""
        try:
            from ....matching.nlp_processor import nlp_processor
            return nlp_processor.format_requirements_for_display(requirements)
        except Exception as e:
            logger.error(f"Error generating requirement summary: {str(e)}")
            return "Requirements extracted"

    def is_greeting_message_enhanced(self, message: str, nlp_processor) -> bool:
        """Enhanced greeting detection with better pattern matching"""
        try:
            # First check using NLP processor's sophisticated greeting detection
            if nlp_processor.is_greeting_message(message):
                return True

            # Additional greeting patterns for better coverage
            message_lower = message.lower().strip()

            # Simple greetings that might be missed by restrictive patterns
            simple_greetings = [
                'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
                'greetings', 'howdy', 'welcome', 'sup', 'yo', 'start', 'begin',
                'thanks', 'thank you', 'how are you', 'how do you do',
                'nice to meet you', 'good to meet you', 'ready to start',
                'hi there', 'hello there', 'hey there'
            ]

            # Check for exact matches or word boundaries
            for greeting in simple_greetings:
                if greeting == message_lower or f' {greeting}' in f' {message_lower}':
                    return True

            return False

        except Exception as e:
            logger.error(f"Error in enhanced greeting detection: {str(e)}")
            return False

    def handle_new_requirements(self, conversation, message: str) -> str:
        """Handle new requirements from any step in the conversation"""
        try:
            # Use MCP integration for requirement extraction (Anthropic primary, Gemini fallback)
            from ..mcp import mcp_integration
            if mcp_integration.is_configured():
                raw_requirements = mcp_integration.extract_requirements(message)
                # For backward compatibility, create a mock nlp_processor object
                class MockNLPProcessor:
                    def validate_requirements(self, reqs): return mcp_integration.validate_requirements(reqs)
                    def format_requirements_for_display(self, reqs): return mcp_integration.format_requirements_for_display(reqs)
                    def is_greeting_message(self, msg): return mcp_integration.is_greeting_message(msg)
                    def is_greeting_response(self, reqs): return mcp_integration.is_greeting_response(reqs)
                    def get_greeting_response(self, reqs): return mcp_integration.get_greeting_response(reqs)
                    def extract_requirements(self, msg): return mcp_integration.extract_requirements(msg)

                nlp_processor = MockNLPProcessor()
                requirements = self.process_nlp_requirements(raw_requirements, nlp_processor)
            else:
                # Fallback to existing NLP processor
                logger.warning("MCP integration not configured, using existing NLP processor")
                from ....matching.nlp_processor import nlp_processor
                raw_requirements = nlp_processor.extract_requirements(message)
                requirements = self.process_nlp_requirements(raw_requirements, nlp_processor)

            # Check if it's a greeting
            if self.is_greeting_message_enhanced(message, nlp_processor):
                from .message_classifier import message_classifier
                return message_classifier._handle_greeting_flow(conversation, message, nlp_processor)

            # Validate new requirements
            if not requirements or not self.has_valid_requirements(requirements):
                from .help_utils import help_utils_handler
                return help_utils_handler.get_comprehensive_help_message()

            # Update conversation with new requirements
            conversation.context_data = {
                'raw_requirements': raw_requirements,
                'validated_requirements': nlp_processor.validate_requirements(requirements),
                'formatted_display': nlp_processor.format_requirements_for_display(requirements),
                'nlp_processed': True,
                'is_new_search': True
            }

            # Reset to token check for new search
            conversation.current_step = 'token_check'
            conversation.save()

            logger.info(f"New requirements processed for {conversation.cell_number}")

            # Proceed with token check for new requirements
            from .step_handlers import step_handlers
            return step_handlers._handle_token_check_step(conversation, message)

        except Exception as e:
            logger.error(f"Error handling new requirements: {str(e)}")
            return "Error processing your new requirements. Please try again."


# Global instance
nlp_processor_handler = NLPProcessorHandler()