import os
import time
import logging
import json
from typing import Dict, Optional
from collections import defaultdict

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

logger = logging.getLogger(__name__)

class AIEnhancer:
    def __init__(self):
        # Initialize API handlers from centralized module
        from core.services.mcp.api_handlers import GeminiHandler, AnthropicHandler, OpenAIHandler
        
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

        # Initialize handlers
        self.openai_handler = OpenAIHandler(self.openai_api_key) if self.openai_api_key else None
        self.gemini_handler = GeminiHandler(self.gemini_api_key) if self.gemini_api_key else None
        self.anthropic_handler = AnthropicHandler(self.anthropic_api_key) if self.anthropic_api_key else None

        logger.info("AI Enhancer initialized with available handlers")

    def _check_rate_limit(self, api_name: str) -> bool:
        current_time = time.time()
        call_times = self.api_call_times[api_name]

        call_times[:] = [t for t in call_times if current_time - t < 60]

        if len(call_times) >= self.max_calls_per_minute:
            logger.warning(f"Rate limit exceeded for {api_name}")
            return False

        call_times.append(current_time)
        return True

    def _is_api_disabled(self, api_name: str) -> bool:
        current_time = time.time()
        if api_name == 'gemini':
            return current_time < self.gemini_disabled_until
        elif api_name == 'openai':
            return current_time < self.openai_disabled_until
        return False

    def _disable_api_temporarily(self, api_name: str, minutes: int = 5):
        if api_name == 'gemini':
            self.gemini_disabled_until = time.time() + (minutes * 60)
            logger.warning(f"Gemini API disabled for {minutes} minutes due to quota issues")
        elif api_name == 'openai':
            self.openai_disabled_until = time.time() + (minutes * 60)
            logger.warning(f"OpenAI API disabled for {minutes} minutes due to quota issues")

    def _enhance_with_gemini(self, message: str, requirements: Dict) -> Dict:
        if not self.gemini_handler:
            logger.warning("Gemini handler not available")
            return requirements

        try:
            # Add time-based greeting to prompt
            from matching.greeting_handler import GreetingHandler
            greeting = GreetingHandler().get_time_based_greeting()
            prompt = f"""
            {greeting}! Extract accommodation requirements from this WhatsApp message. Return only JSON:

            Message: "{message}"

            Extract:
            - Number of people/heads needed
            - Required amenities (wifi, parking, etc.)
            - Maximum budget
            - Location preferences
            - Gender preference (male/female/any)
            - Urgency level

            Return valid JSON with these keys: heads, amenities, budget_max, distance_preference, location_context, gender_preference, urgency
            """

            ai_text = self.gemini_handler.call_api(
                prompt=prompt,
                max_tokens=300,
                temperature=0.3
            )

            if not ai_text:
                logger.warning("No response from Gemini handler")
                ai_text = "{}"

            try:
                ai_requirements = json.loads(ai_text)
                for key, value in ai_requirements.items():
                    if requirements.get(key) is None and value is not None:
                        requirements[key] = value
            except json.JSONDecodeError:
                logger.warning("Invalid JSON response from Gemini, using original requirements")

        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "rate limit" in error_str or "429" in error_str:
                logger.warning(f"Gemini quota/rate limit issue: {e}")
                self._disable_api_temporarily('gemini', 10)
            else:
                logger.error(f"Gemini enhancement failed: {e}")

        return requirements

    def _enhance_with_openai(self, message: str, requirements: Dict) -> Dict:
        if not self.openai_handler:
            logger.warning("OpenAI handler not available")
            return requirements

        try:
            prompt = f"""
            Extract accommodation requirements from this WhatsApp message. Return only JSON:

            Message: "{message}"

            Extract:
            - Number of people/heads needed
            - Required amenities (wifi, parking, etc.)
            - Maximum budget
            - Location preferences
            - Gender preference (male/female/any)
            - Urgency level

            Return valid JSON with these keys: heads, amenities, budget_max, distance_preference, location_context, gender_preference, urgency
            """

            response = self.openai_handler.call_api(
                prompt=prompt,
                system_message="You are a helpful agent that extracts accommodation requirements from messages. Return only valid JSON.",
                model="gpt-3.5-turbo",
                max_tokens=300,
                temperature=0.3
            )

            ai_text = response.choices[0].message.content.strip()

            try:
                ai_requirements = json.loads(ai_text)
                for key, value in ai_requirements.items():
                    if requirements.get(key) is None and value is not None:
                        requirements[key] = value
            except json.JSONDecodeError:
                logger.warning("Invalid JSON response from OpenAI, using original requirements")

        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "rate limit" in error_str or "insufficient_quota" in error_str:
                logger.warning(f"OpenAI quota/rate limit issue: {e}")
                self._disable_api_temporarily('openai', 10)
            else:
                logger.error(f"OpenAI enhancement failed: {e}")

        return requirements