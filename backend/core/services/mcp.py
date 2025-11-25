"""
Gemini API Integration with Model Context Protocol (MCP) Support for Jeff Agent

This module provides Gemini integration as the primary LLM for the Jeff WhatsApp agent,
with fallback to Anthropic API when Gemini calls fail or encounter errors.

Key Features:
- Primary Gemini integration with MCP support
- Seamless fallback to existing Anthropic API
- Enhanced context management using MCP
- Compatible interface with existing NLP processor
- Proper error handling and rate limiting
- Environment-based configuration
- Modular components for better maintainability
"""

import os
import logging
from typing import Dict, List, Optional

# Import modular components
from .mcp.api_handlers import AnthropicHandler, GeminiHandler
from .mcp.context_manager import ContextManager
from .mcp.classification import MessageClassifier
from .mcp.extraction import RequirementExtractor
from .mcp.greeting_handler import GreetingHandler

logger = logging.getLogger(__name__)


class MCPIntegration:
    """
    Gemini API integration with Model Context Protocol support and Anthropic fallback

    This class provides the same interface as the existing DjangoNLPProcessor but uses
    Gemini as the primary LLM with enhanced MCP context management.

    Now uses modular components for better organization and maintainability.
    """

    def __init__(self):
        """Initialize MCP integration with API keys and modular components"""
        # API Keys
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')

        # Initialize modular components
        self.api_handlers = {
            'anthropic': AnthropicHandler(self.anthropic_api_key) if self.anthropic_api_key else None,
            'gemini': GeminiHandler(self.gemini_api_key) if self.gemini_api_key else None
        }

        self.context_manager = ContextManager()
        self.classifier = MessageClassifier()
        self.extractor = RequirementExtractor()
        self.greeting_handler = GreetingHandler()

        logger.info("MCP integration initialized with modular components")

    def is_configured(self) -> bool:
        """Check if at least one API provider is configured"""
        return (self.api_handlers['anthropic'] is not None or self.api_handlers['gemini'] is not None)

    def classify_message(self, message: str) -> str:
        """
        Classify message using modular components with AI and fallback methods

        Args:
            message (str): The message to classify

        Returns:
            str: Single character classification key (G, A, H, P)
        """
        logger.info(f"Classifying message with MCP: '{message[:50]}{'...' if len(message) > 50 else ''}'")

        # Update context with user message
        self.context_manager.update_context(message)

        # Use modular classifier component
        return self.classifier.classify_with_ai(
            message,
            self.api_handlers['gemini'],
            self.api_handlers['anthropic']
        )

    def extract_requirements(self, message: str) -> Dict:
        """
        Extract requirements using modular components with AI enhancement

        Args:
            message (str): The WhatsApp message

        Returns:
            Dict: Structured requirements or greeting response
        """
        logger.info(f"Extracting requirements with MCP: '{message[:50]}{'...' if len(message) > 50 else ''}'")

        # Update context with user message
        self.context_manager.update_context(message)

        # Check for greeting first using modular greeting handler
        if self.greeting_handler.is_greeting_message(message.lower()):
            greeting_response = self.greeting_handler.generate_greeting_response(
                message,
                self.api_handlers['gemini'],
                self.api_handlers['anthropic']
            )
            return {
                'is_greeting': True,
                'response': greeting_response,
                'raw_message': message
            }

        # Extract using modular extractor component
        requirements = self.extractor.extract_requirements(message)

        # Try to enhance with Gemini first
        if self.api_handlers['gemini']:
            try:
                enhanced_requirements = self.extractor.enhance_with_gemini(
                    message, requirements.copy(), self.api_handlers['gemini']
                )
                if enhanced_requirements:
                    requirements.update(enhanced_requirements)
                    logger.info("Gemini enhancement completed successfully")
            except Exception as e:
                logger.error(f"Gemini enhancement failed: {str(e)}")

        # Fallback to Anthropic if Gemini fails
        elif self.api_handlers['anthropic']:
            try:
                enhanced_requirements = self.extractor.enhance_with_anthropic(
                    message, requirements.copy(), self.api_handlers['anthropic']
                )
                if enhanced_requirements:
                    requirements.update(enhanced_requirements)
                    logger.info("Anthropic enhancement completed successfully")
            except Exception as e:
                logger.error(f"Anthropic enhancement failed: {str(e)}")

        return requirements

    def _generate_greeting_response(self, message: str) -> str:
        """Generate greeting response using modular greeting handler"""
        return self.greeting_handler.generate_greeting_response(
            message,
            self.api_handlers['gemini'],
            self.api_handlers['anthropic']
        )

    # Delegated methods using modular components
    def is_greeting_message(self, message: str) -> bool:
        """Check if message is a greeting using modular greeting handler"""
        return self.greeting_handler.is_greeting_message(message)

    def _extract_heads_count(self, message: str) -> Optional[int]:
        """Extract number of heads using modular extractor"""
        return self.extractor._extract_heads_count(message)

    def _extract_amenities(self, message: str) -> List[str]:
        """Extract amenities using modular extractor"""
        return self.extractor._extract_amenities(message)

    def _extract_budget(self, message: str) -> Optional[float]:
        """Extract budget using modular extractor"""
        return self.extractor._extract_budget(message)

    def _extract_location(self, message: str) -> tuple:
        """Extract location using modular extractor"""
        return self.extractor._extract_location(message)

    def _extract_gender_preference(self, message: str) -> Optional[str]:
        """Extract gender preference using modular extractor"""
        return self.extractor._extract_gender_preference(message)

    def _extract_urgency(self, message: str) -> Optional[str]:
        """Extract urgency using modular extractor"""
        return self.extractor._extract_urgency(message)

    def validate_requirements(self, requirements: Dict) -> Dict:
        """Validate and clean extracted requirements using modular extractor"""
        return self.extractor.validate_requirements(requirements)

    def format_requirements_for_display(self, requirements: Dict) -> str:
        """Format requirements for WhatsApp display using modular extractor"""
        return self.extractor.format_requirements_for_display(requirements)

    def is_greeting_response(self, requirements: Dict) -> bool:
        """Check if the requirements result is a greeting response using modular greeting handler"""
        return self.greeting_handler.is_greeting_response(requirements)

    def get_greeting_response(self, requirements: Dict) -> str:
        """Get the greeting response text if this is a greeting using modular greeting handler"""
        return self.greeting_handler.get_greeting_response(requirements)


# Global instance for easy import
mcp_integration = MCPIntegration()