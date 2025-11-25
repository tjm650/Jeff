"""
MCP Integration Coordinator

This module provides a central integration point for all MCP components,
coordinating between API handlers, classification, extraction, and greeting handling.
"""

import os
import logging
from typing import Dict, List, Optional

from .api_handlers import AnthropicHandler, GeminiHandler
from .classification import MessageClassifier
from .extraction import RequirementExtractor
from .greeting_handler import GreetingHandler

logger = logging.getLogger(__name__)


class MCPIntegration:
    """Central coordinator for MCP integration components"""

    def __init__(self):
        logger.info("Initializing MCP Integration...")

        # Initialize API handlers
        self.anthropic_handler = None
        self.gemini_handler = None
        self._initialize_api_handlers()
        logger.info(f"API handlers initialized - Anthropic: {self.anthropic_handler is not None}, Gemini: {self.gemini_handler is not None}")

        # Initialize MCP components
        self.message_classifier = MessageClassifier()
        self.requirement_extractor = RequirementExtractor()
        self.greeting_handler = GreetingHandler()
        logger.info("MCP components initialized")

        # Import locally to avoid circular import
        from .recommendation import RecommendationService
        self.recommendation_service = RecommendationService()
        logger.info("Recommendation service initialized")

    @property
    def api_handlers(self):
        """Provide access to API handlers as a dictionary for backward compatibility"""
        return {
            'gemini': self.gemini_handler,
            'anthropic': self.anthropic_handler
        }

    def _initialize_api_handlers(self):
        """Initialize API handlers with keys from environment"""
        # Anthropic API key
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        logger.info(f"Anthropic API key found: {anthropic_key is not None}")
        if anthropic_key:
            self.anthropic_handler = AnthropicHandler(anthropic_key)
            logger.info("Anthropic handler initialized")
        else:
            logger.warning("ANTHROPIC_API_KEY not found")

        # Gemini API key
        gemini_key = os.getenv('GEMINI_API_KEY')
        logger.info(f"Gemini API key found: {gemini_key is not None}")
        if gemini_key:
            self.gemini_handler = GeminiHandler(gemini_key)
            logger.info("Gemini handler initialized")
        else:
            logger.warning("GEMINI_API_KEY not found")

    def is_configured(self) -> bool:
        """Check if MCP integration is properly configured"""
        return (self.anthropic_handler is not None and self.anthropic_handler.client is not None) or \
               (self.gemini_handler is not None and self.gemini_handler.model is not None)

    def classify_message(self, message: str, categories: List[str] = ['G', 'A', 'H', 'P', 'S', 'N', 'X', 'J']) -> str:
        """Classify message using AI with fallback to rule-based classification"""
        if not message:
            return 'A'  # Default to accommodation enquiry

        # Use the MCP message classifier with AI handlers
        return self.message_classifier.classify_with_ai(
            message,
            self.gemini_handler,
            self.anthropic_handler,
            categories
        )

    def extract_requirements(self, message: str) -> Dict:
        """Extract requirements from message using rule-based methods and optional AI keyword expansion

        This returns the extracted requirements dict and, when AI handlers are available,
        attempts to expand keywords and attach them under 'expanded_keywords' for downstream matching.
        """
        reqs = self.requirement_extractor.extract_requirements(message)

        # Try to expand keywords using Gemini first, then Anthropic. Merge expansions if available.
        expanded = []
        try:
            if self.gemini_handler and self.gemini_handler.model:
                gems = self.requirement_extractor.expand_keywords_with_gemini(message, self.gemini_handler)
                if gems:
                    expanded.extend(gems)
        except Exception as e:
            logger.warning(f"Gemini keyword expansion failed: {e}")

        try:
            if self.anthropic_handler and self.anthropic_handler.client:
                ants = self.requirement_extractor.expand_keywords_with_anthropic(message, self.anthropic_handler)
                if ants:
                    for k in ants:
                        if k not in expanded:
                            expanded.append(k)
        except Exception as e:
            logger.warning(f"Anthropic keyword expansion failed: {e}")

        # If no AI expansion provided anything, fall back to tokenized keywords generated earlier
        if not expanded and reqs.get('keyword_tokens'):
            expanded = reqs.get('keyword_tokens')

        if expanded:
            # Attach expanded keywords to requirements for property matcher
            reqs['expanded_keywords'] = expanded

        return reqs

    def is_greeting_message(self, message: str) -> bool:
        """Check if message is a greeting"""
        return self.greeting_handler.is_greeting_message(message)

    def _generate_greeting_response(self, message: str) -> str:
        """Generate greeting response using AI"""
        return self.greeting_handler.generate_greeting_response(
            message,
            self.gemini_handler,
            self.anthropic_handler
        )

    def _get_fallback_greeting_response(self) -> str:
        """Get fallback greeting response"""
        return self.greeting_handler._get_fallback_greeting_response()

    def is_greeting_response(self, requirements: Dict) -> bool:
        """Check if the requirements result is a greeting response"""
        return self.greeting_handler.is_greeting_response(requirements)

    def get_greeting_response(self, requirements: Dict) -> str:
        """Get the greeting response text if this is a greeting"""
        return self.greeting_handler.get_greeting_response(requirements)

    def test_gemini_connection(self) -> bool:
        """Test if Gemini API connection is working"""
        if self.gemini_handler and self.gemini_handler.model:
            return self.gemini_handler.test_connection()
        return False

    def get_mcp_status(self) -> Dict:
        """Get status of MCP integration components"""
        return {
            'gemini_configured': self.gemini_handler is not None and self.gemini_handler.model is not None,
            'anthropic_configured': self.anthropic_handler is not None and self.anthropic_handler.client is not None,
            'gemini_available': self.gemini_handler is not None,
            'anthropic_available': self.anthropic_handler is not None,
            'is_configured': self.is_configured()
        }


# Global instance - lazy initialization to avoid circular import
_mcp_integration = None

def get_mcp_integration():
    """Get or create the global MCP integration instance"""
    global _mcp_integration
    if _mcp_integration is None:
        _mcp_integration = MCPIntegration()
    return _mcp_integration

# Backward compatibility alias
mcp_integration = None  # Will be set after modules are loaded