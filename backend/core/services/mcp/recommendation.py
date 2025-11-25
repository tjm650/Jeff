"""
Recommendation Service for MCP Integration

This module handles generating recommendation summaries when no properties match user requirements.
It uses MCP AI services to analyze available listings and provide tailored recommendations.
"""

import logging
from typing import Dict, List, Optional
from django.db.models import Q
from core.models import Property

logger = logging.getLogger(__name__)


class RecommendationService:
    """Handles property recommendation generation using MCP AI"""

    def __init__(self):
        # Don't store reference to avoid None issues
        # Will get fresh instance when needed
        pass

    def generate_recommendation_summary(self, user_requirements: Dict, limit: int = 10) -> str:
        """
        Generate a recommendation summary when no exact matches are found.

        Args:
            user_requirements (Dict): User's search requirements
            limit (int): Number of available properties to analyze

        Returns:
            str: Recommendation summary message
        """
        try:
            # Fetch available properties
            available_properties = self._get_available_properties(limit)
            if not available_properties:
                return self._get_fallback_message(user_requirements)

            # Generate summary using MCP AI
            summary = self._generate_ai_summary(user_requirements, available_properties)
            if summary:
                return summary

            # Fallback to rule-based summary
            return self._generate_rule_based_summary(user_requirements, available_properties)

        except Exception as e:
            logger.error(f"Error generating recommendation summary: {str(e)}")
            return self._get_fallback_message(user_requirements)

    def _get_available_properties(self, limit: int) -> List[Property]:
        """Fetch available properties for analysis"""
        try:
            properties = Property.objects.filter(
                is_active=True,
                available_rooms__gt=0
            ).select_related('provider')[:limit]

            return list(properties)
        except Exception as e:
            logger.error(f"Error fetching available properties: {str(e)}")
            return []

    def _generate_ai_summary(self, user_requirements: Dict, properties: List[Property]) -> Optional[str]:
        """Generate summary using MCP AI services"""
        # Import locally to avoid circular import
        from .integration import get_mcp_integration
        mcp = get_mcp_integration()

        if not mcp or not mcp.is_configured():
            logger.warning("MCP not configured, skipping mcp summary")
            return None

        # Prepare data for AI
        properties_data = self._format_properties_for_ai(properties)
        requirements_summary = self._format_requirements_for_ai(user_requirements)

        prompt = f"""
        Analyze the user's accommodation requirements and available properties to provide a helpful recommendation summary.

        User Requirements:
        {requirements_summary}

        Available Properties (top {len(properties)}):
        {properties_data}

        As the accommodation agent, Generate a concise recommendation summary that:
        1. Explains why no exact matches were found
        2. Suggests the closest available options based on requirements
        3. Provides alternative suggestions (adjust budget, location, or amenities)
        4. Encourages the user to refine their search or contact support
        5. Do not answer with "Here's a summary" or similar phrases.

        FORMATTING RULES:
        - Use simple bullet points with single dashes for listings (•)
        - Do NOT use nested asterisks (*   *)
        - Keep formatting clean and readable for WhatsApp
        - Consider not breaking lines too much for better readability
        - Use plain text only, no markdown except for simple bullets (•)
        - Example format: • Property Name: $price/month, heads heads, distance km from campus
        - Do not use italic, or any markdown symbols except simple (•) for lists

        Keep the response professional, helpful, and under 200 words. Do not use emojis. Do not greet the user.
        """
        # - Use plain text for all property details

        # Try Gemini first
        logger.info(f"Trying Gemini - handler: {mcp.gemini_handler is not None}, model: {mcp.gemini_handler.model if mcp.gemini_handler else 'No handler'}")
        if mcp.gemini_handler and mcp.gemini_handler.model:
            # Test connection first
            if mcp.test_gemini_connection():
                logger.info("Gemini connection test passed")
                response = mcp.gemini_handler.call_api(prompt, max_tokens=150, temperature=0.3)
                logger.info(f"Gemini response: {response[:100] if response else 'None'}")
                if response and len(response.strip()) > 10:
                    return response.strip()
            else:
                logger.warning("Gemini connection test failed")

        # Fallback to Anthropic
        logger.info(f"Trying Anthropic - handler: {mcp.anthropic_handler}, client: {mcp.anthropic_handler.client if mcp.anthropic_handler else 'No handler'}")
        if mcp.anthropic_handler and mcp.anthropic_handler.client:
            response = mcp.anthropic_handler.call_api(prompt, max_tokens=150, temperature=0.3)
            logger.info(f"Anthropic response: {response[:100] if response else 'None'}")
            if response and len(response.strip()) > 10:
                return response.strip()

        return None

    def _generate_rule_based_summary(self, user_requirements: Dict, properties: List[Property]) -> str:
        """Generate summary using rule-based logic"""
        try:
            message = "No properties found matching your exact requirements.\n\n"

            # Analyze available properties
            if properties:
                # Calculate averages
                prices = [p.price_per_month for p in properties if p.price_per_month]
                distances = [p.distance_from_campus for p in properties if p.distance_from_campus]

                avg_price = sum(prices) / len(prices) if prices else 0
                avg_distance = sum(distances) / len(distances) if distances else 0

                message += "Available options summary:\n"
                message += f"- Average price: ${avg_price:.0f}/month\n"
                message += f"- Average distance from campus: {avg_distance:.1f}km\n"
                message += f"- Total available properties: {len(properties)}\n\n"

                # Suggest adjustments based on requirements
                suggestions = self._get_suggestions(user_requirements, avg_price, avg_distance)
                if suggestions:
                    message += "Suggestions:\n"
                    for suggestion in suggestions:
                        message += f"- {suggestion}\n"
                    message += "\n"

            message += "Please refine your requirements or contact support for assistance."

            return message

        except Exception as e:
            logger.error(f"Error in rule-based summary: {str(e)}")
            return self._get_fallback_message(user_requirements)

    def _get_suggestions(self, user_requirements: Dict, avg_price: float, avg_distance: float) -> List[str]:
        """Generate suggestions based on requirements"""
        suggestions = []

        if user_requirements.get('budget_max') and user_requirements['budget_max'] < avg_price:
            suggestions.append(f"Consider increasing budget to ${float(avg_price) * 1.2:.0f} for more options")

        if user_requirements.get('distance_preference') == 'near' and avg_distance > 2:
            suggestions.append("Expand location search beyond 2km from campus")

        if user_requirements.get('heads') and user_requirements['heads'] > 1:
            suggestions.append("Consider shared rooms to reduce costs")

        if not suggestions:
            suggestions.append("Try removing some amenity requirements")
            suggestions.append("Consider different campus locations")

        return suggestions[:3]  # Limit to 3 suggestions

    def _format_properties_for_ai(self, properties: List[Property]) -> str:
        """Format properties data for AI prompt"""
        formatted = ""
        for i, prop in enumerate(properties[:5], 1):  # Limit to top 5 for prompt
            formatted += f"{i}. {prop.name}: ${prop.price_per_month}/month, {prop.distance_from_campus}km from campus, amenities: {', '.join(prop.amenities[:3]) if prop.amenities else 'basic'}\n"
        return formatted

    def _format_requirements_for_ai(self, user_requirements: Dict) -> str:
        """Format user requirements for AI prompt"""
        parts = []
        if user_requirements.get('heads'):
            parts.append(f"Heads: {user_requirements['heads']}")
        if user_requirements.get('budget_max'):
            parts.append(f"Budget: up to ${user_requirements['budget_max']}")
        if user_requirements.get('amenities'):
            parts.append(f"Amenities: {', '.join(user_requirements['amenities'])}")
        if user_requirements.get('location_context'):
            parts.append(f"Location: {user_requirements['location_context']}")
        if user_requirements.get('gender_preference'):
            parts.append(f"Gender: {user_requirements['gender_preference']}")

        return " | ".join(parts) if parts else "No specific requirements"

    def _get_fallback_message(self, user_requirements: Dict) -> str:
        """Fallback message when no data is available"""
        return ("No properties found matching your requirements. "
                "Please try adjusting your criteria such as budget, location, or amenities. "
                "Contact support for personalized assistance.")


# Global instance - lazy initialization to avoid circular import
_recommendation_service = None

def get_recommendation_service():
    """Get or create the global recommendation service instance"""
    global _recommendation_service
    if _recommendation_service is None:
        _recommendation_service = RecommendationService()
    return _recommendation_service

# Backward compatibility alias
recommendation_service = None  # Will be set after integration is available