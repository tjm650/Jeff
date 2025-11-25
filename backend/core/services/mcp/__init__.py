"""
MCP Integration Module

This module provides Model Context Protocol integration for the Jeff platform
with modular components for better maintainability and organization.
"""

import logging

from .api_handlers import APIHandler, AnthropicHandler, GeminiHandler
from .context_manager import ContextManager

logger = logging.getLogger(__name__)
from .classification import MessageClassifier
from .extraction import RequirementExtractor
from .greeting_handler import GreetingHandler
from .recommendation import RecommendationService, get_recommendation_service
from .integration import get_mcp_integration

__all__ = [
    'APIHandler',
    'AnthropicHandler',
    'GeminiHandler',
    'ContextManager',
    'MessageClassifier',
    'RequirementExtractor',
    'GreetingHandler',
    'RecommendationService',
    'mcp_integration',
    'recommendation_service'
]

# Initialize global instances after all modules are loaded to avoid circular imports
def _initialize_global_instances():
    """Initialize global instances in the correct order to avoid circular imports"""
    global mcp_integration, recommendation_service

    try:
        # Initialize MCP integration first
        mcp_integration = get_mcp_integration()
        logger.info("MCP integration initialized successfully")

        # Set up backward compatibility for recommendation service
        recommendation_service = get_recommendation_service()
        logger.info("Recommendation service initialized successfully")

    except Exception as e:
        logger.error(f"Error initializing global instances: {str(e)}")
        # Keep them as None if initialization fails
        mcp_integration = None
        recommendation_service = None

# Initialize the global instances
_initialize_global_instances()