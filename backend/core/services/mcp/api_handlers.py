"""
API Handlers for MCP Integration

This module handles API calls to OpenAI, Gemini and Anthropic with proper error handling,
rate limiting, and fallback mechanisms.
"""

import time
import logging
from typing import Optional, Dict, List
from collections import defaultdict

# OpenAI SDK import
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Anthropic SDK import
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Google Gemini import
try:
    import google.generativeai as genai
    # Check if types module exists
    try:
        import google.generativeai.types as genai_types
        GENAI_TYPES_AVAILABLE = True
    except ImportError:
        GENAI_TYPES_AVAILABLE = False
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    GENAI_TYPES_AVAILABLE = False

logger = logging.getLogger(__name__)


class APIHandler:
    """Base API handler with common functionality"""

    def __init__(self):
        self.api_call_times = defaultdict(list)
        self.max_calls_per_minute = 10
        self.disabled_until = 0

    def _check_rate_limit(self, api_name: str) -> bool:
        """Check if API calls are within rate limits"""
        current_time = time.time()
        call_times = self.api_call_times[api_name]

        # Remove calls older than 1 minute
        call_times[:] = [t for t in call_times if current_time - t < 60]

        # Check if we're under the limit
        if len(call_times) >= self.max_calls_per_minute:
            logger.warning(f"Rate limit exceeded for {api_name}")
            return False

        # Record this call
        call_times.append(current_time)
        return True

    def _is_api_disabled(self, api_name: str) -> bool:
        """Check if API is temporarily disabled due to quota issues"""
        current_time = time.time()
        return current_time < self.disabled_until

    def _disable_api_temporarily(self, api_name: str, minutes: int = 5):
        """Temporarily disable API due to quota issues"""
        self.disabled_until = time.time() + (minutes * 60)
        logger.warning(f"{api_name} API disabled for {minutes} minutes due to quota issues")


class AnthropicHandler(APIHandler):
    """Handler for Anthropic API calls"""

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.client = None

        if ANTHROPIC_AVAILABLE and self.api_key:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info("Anthropic client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {str(e)}")
        else:
            logger.warning("Anthropic client not available")

    def call_api(self, prompt: str, max_tokens: int = 300, temperature: float = 0.3) -> Optional[str]:
        """Call Anthropic API with proper error handling"""
        if not self.client:
            return None

        # Check if API is disabled
        if self._is_api_disabled('anthropic'):
            logger.warning("Anthropic API is temporarily disabled")
            return None

        # Check rate limit
        if not self._check_rate_limit('anthropic'):
            logger.warning("Anthropic API rate limit exceeded")
            return None

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=max_tokens,
                temperature=temperature,
                system="You are Jeff, an agent helping NUST students find accommodation near campus. You provide helpful, accurate responses about accommodation options.",
                messages=[{"role": "user", "content": prompt}]
            )

            if response.content and len(response.content) > 0:
                return response.content[0].text.strip()
            else:
                logger.warning("Empty response from Anthropic API")
                return None

        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "rate limit" in error_str or "429" in error_str:
                logger.warning(f"Anthropic quota/rate limit issue: {e}")
                self._disable_api_temporarily('anthropic', 10)
            else:
                logger.error(f"Anthropic API call failed: {e}")
            return None


class OpenAIHandler(APIHandler):
    """Handler for OpenAI API calls"""

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.client = None

        if OPENAI_AVAILABLE and self.api_key:
            try:
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        else:
            logger.warning("OpenAI client not available")

    def call_api(self, 
                prompt: str, 
                system_message: str = "You are a helpful assistant.",
                model: str = "gpt-3.5-turbo",
                max_tokens: int = 300, 
                temperature: float = 0.3) -> Optional[str]:
        """Call OpenAI API with proper error handling"""
        if not self.client:
            return None

        # Check if API is disabled
        if self._is_api_disabled('openai'):
            logger.warning("OpenAI API is temporarily disabled")
            return None

        # Check rate limit
        if not self._check_rate_limit('openai'):
            logger.warning("OpenAI API rate limit exceeded")
            return None

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )

            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content.strip()
            else:
                logger.warning("Empty response from OpenAI API")
                return None

        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "rate limit" in error_str or "insufficient_quota" in error_str:
                logger.warning(f"OpenAI quota/rate limit issue: {e}")
                self._disable_api_temporarily('openai', 10)
            else:
                logger.error(f"OpenAI API call failed: {e}")
            return None

    def test_connection(self) -> bool:
        """Test if OpenAI API connection is working"""
        if not self.client:
            logger.error("OpenAI client not initialized")
            return False

        try:
            test_prompt = "Hello, just testing the connection. Please respond with 'OK'."
            response = self.call_api(
                prompt=test_prompt,
                max_tokens=10,
                temperature=0.1
            )
            return response is not None and len(response.strip()) > 0
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {e}")
            return False


class GeminiHandler(APIHandler):
    """Handler for Gemini API calls"""

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.model = None
 
        if GEMINI_AVAILABLE and self.api_key: 
            try:
                genai.configure(api_key=self.api_key) 
                # Use stable model instead of experimental
                self.model = genai.GenerativeModel('gemini-2.5-flash-lite') # 
                logger.info("Gemini client initialized successfully") 
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {str(e)}")
                # Try alternative model if first fails
                try:
                    self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                    logger.info("Gemini client initialized with fallback model")
                except Exception as e2:
                    logger.error(f"Failed to initialize Gemini client with fallback: {str(e2)}")
        else:
            logger.warning("Gemini client not available")

    def call_api(self, prompt: str, max_tokens: int = 300, temperature: float = 0.3) -> Optional[str]:
        """Call Gemini API with proper error handling"""
        if not self.model:
            return None

        # Check if API is disabled
        if self._is_api_disabled('gemini'):
            logger.warning("Gemini API is temporarily disabled")
            return None

        # Check rate limit
        if not self._check_rate_limit('gemini'):
            logger.warning("Gemini API rate limit exceeded")
            return None

        try:
            # Use simpler API call
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': temperature,
                    'max_output_tokens': max_tokens,
                }
            )

            if response and response.text:
                return response.text.strip()

            logger.warning("Empty response from Gemini API")
            return None

        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "rate limit" in error_str or "429" in error_str:
                logger.warning(f"Gemini quota/rate limit issue: {e}")
                self._disable_api_temporarily('gemini', 10)
            else:
                logger.error(f"Gemini API call failed: {e}")
            return None

    def test_connection(self) -> bool:
        """Test if Gemini API connection is working"""
        if not self.model:
            logger.error("Gemini model not initialized")
            return False

        try:
            test_prompt = "Hello, just testing the connection. Please respond with 'OK'."
            response = self.model.generate_content(
                test_prompt,
                generation_config={'temperature': 0.1, 'max_output_tokens': 10}
            )
            return response and response.text and len(response.text.strip()) > 0
        except Exception as e:
            logger.error(f"Gemini connection test failed: {e}")
            return False