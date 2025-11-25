"""
Requirement Extraction for MCP Integration

This module handles extraction of accommodation requirements from messages
with AI enhancement and rule-based fallback methods.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RequirementExtractor:
    """Handles extraction and enhancement of accommodation requirements"""

    def __init__(self):
        # Accommodation-specific patterns (same as existing NLP processor)
        self.heads_keywords = {
            'single': 1, 'one': 1, 'solo': 1, 'individual': 1,
            'double': 2, 'two': 2, 'twin': 2, 'couple': 2,
            'triple': 3, 'three': 3, 'quad': 4, 'four': 4,
            'sharing': 2, 'shared': 2
        }

        self.amenity_keywords = {
            'wifi': 'wifi', 'internet': 'wifi', 'wi-fi': 'wifi',
            'parking': 'parking', 'car park': 'parking',
            'dstv': 'dstv', 'cable': 'dstv', 'tv': 'dstv',
            'security': 'security', 'guard': 'security', 'secure': 'security',
            'laundry': 'laundry', 'washing': 'laundry',
            'gym': 'gym', 'fitness': 'gym',
            'pool': 'pool', 'swimming': 'pool',
            'electricity': 'electricity', 'power': 'electricity',
            'water': 'water', 'borehole': 'water',
            'cleaning': 'cleaning', 'maid': 'cleaning',
            'backup generator': 'generator', 'generator': 'generator',
            'study room': 'study_room', 'quiet': 'study_room'
        }

        self.location_keywords = {
            'near': 'near', 'close': 'near', 'walking distance': 'near',
            'far': 'far', 'distant': 'far',
            'campus': 'campus', 'university': 'campus', 'school': 'campus',
            'town': 'town', 'city': 'town', 'center': 'town',
            'mall': 'mall', 'shopping': 'mall',
            'hospital': 'hospital', 'clinic': 'hospital'
        }

    def extract_requirements(self, message: str) -> Dict:
        """
        Extract requirements using rule-based methods

        Args:
            message (str): The WhatsApp message

        Returns:
            Dict: Structured requirements
        """
        # Initialize requirements structure
        requirements = {
            'heads': None,
            'amenities': [],
            'budget_max': None,
            'distance_preference': None,
            'location_context': None,
            'gender_preference': None,
            'urgency': None,
            'raw_message': message
        }

        # Extract using rule-based methods
        requirements['heads'] = self._extract_heads_count(message)
        requirements['amenities'] = self._extract_amenities(message)
        requirements['budget_max'] = self._extract_budget(message)
        requirements['distance_preference'], requirements['location_context'] = self._extract_location(message)
        requirements['gender_preference'] = self._extract_gender_preference(message)
        requirements['urgency'] = self._extract_urgency(message)

        # Generate basic keyword tokens from the raw message. MCPIntegration may
        # later call the AI expanders to attach 'expanded_keywords'.
        requirements['keyword_tokens'] = self._generate_keyword_tokens(message)

        return requirements

    def _safe_parse_json(self, response: str):
        """Attempt to parse JSON from a possibly noisy AI response.

        Tries direct json.loads first, then attempts to extract a JSON
        array or object substring if the direct parse fails. Returns
        the parsed object or None on failure.
        """
        if not response or not isinstance(response, str):
            return None

        # Try direct parse
        try:
            return json.loads(response)
        except Exception:
            pass

        # Try to extract a JSON array substring
        try:
            first_arr = response.find('[')
            last_arr = response.rfind(']')
            if first_arr != -1 and last_arr != -1 and last_arr > first_arr:
                sub = response[first_arr:last_arr+1]
                return json.loads(sub)
        except Exception:
            pass

        # Try to extract a JSON object substring
        try:
            first_obj = response.find('{')
            last_obj = response.rfind('}')
            if first_obj != -1 and last_obj != -1 and last_obj > first_obj:
                sub = response[first_obj:last_obj+1]
                return json.loads(sub)
        except Exception:
            pass

        # Give up and return None (caller will handle logging)
        return None

    def _generate_keyword_tokens(self, message: str) -> List[str]:
        """Generate simple keyword tokens from the message for matching fallbacks

        This does light tokenization and filtering; AI expansion can add synonyms.
        """
        try:
            if not message:
                return []

            # Lowercase and remove punctuation
            text = re.sub(r"[^a-zA-Z0-9\s]", " ", message.lower())
            parts = [p.strip() for p in text.split() if len(p.strip()) > 2]

            # Remove common short stopwords
            stopwords = set(['have', 'with', 'for', 'and', 'the', 'need', 'need', 'looking', 'lookingfor', 'lookingfor'])
            tokens = [p for p in parts if p not in stopwords]

            # Deduplicate while preserving order
            seen = set()
            final = []
            for t in tokens:
                if t not in seen:
                    seen.add(t)
                    final.append(t)
            return final
        except Exception:
            return []

    def expand_keywords_with_anthropic(self, message: str, anthropic_handler) -> Optional[List[str]]:
        """Ask Anthropic to expand/normalize keywords from the message; returns list of keywords or None"""
        if not anthropic_handler or not anthropic_handler.client:
            return None

        prompt = f"""
        Extract and expand important search keywords from this message. Return a JSON array of short keywords (strings).

        Message: "{message}"

        Only return valid JSON array, e.g. ["wifi", "near campus", "2 heads"].
        """

        response = anthropic_handler.call_api(prompt, temperature=0.2)
        if not response:
            return None
        data = self._safe_parse_json(response)
        if isinstance(data, list):
            return [str(x).strip() for x in data if x]

        logger.warning("Anthropic keyword expansion returned invalid JSON")
        logger.debug(f"Anthropic keyword expansion raw response: {response}")
        return None

    def expand_keywords_with_gemini(self, message: str, gemini_handler) -> Optional[List[str]]:
        """Ask Gemini to expand/normalize keywords from the message; returns list of keywords or None"""
        if not gemini_handler or not gemini_handler.model:
            return None

        prompt = f"""
        Extract and expand important search keywords from this message. Return a JSON array of short keywords (strings).

        Message: "{message}"

        Only return valid JSON array, e.g. ["wifi", "near campus", "2 heads"].
        """

        response = gemini_handler.call_api(prompt, temperature=0.2)
        if not response:
            return None
        data = self._safe_parse_json(response)
        if isinstance(data, list):
            return [str(x).strip() for x in data if x]

        logger.warning("Gemini keyword expansion returned invalid JSON")
        logger.debug(f"Gemini keyword expansion raw response: {response}")
        return None

    def enhance_with_anthropic(self, message: str, requirements: Dict, anthropic_handler) -> Optional[Dict]:
        """Enhance requirements using Anthropic Claude"""
        if not anthropic_handler or not anthropic_handler.client:
            return None

        prompt = f"""
        Extract accommodation requirements from this WhatsApp message. Return only valid JSON:

        Message: "{message}"

        Current extraction: {json.dumps(requirements)}

        Extract and enhance:
        - Number of people/heads needed
        - Required amenities (wifi, parking, etc.)
        - Maximum budget
        - Location preferences
        - Gender preference (male/female/any)
        - Urgency level

        Return valid JSON with these keys: heads, amenities, budget_max, distance_preference, location_context, gender_preference, urgency

        Only include values that improve upon the current extraction.
        """

        response = anthropic_handler.call_api(prompt, temperature=0.3)
        if not response:
            return None

        ai_requirements = self._safe_parse_json(response)
        if not isinstance(ai_requirements, dict):
            logger.warning("Invalid JSON response from Anthropic")
            logger.debug(f"Anthropic enhancement raw response: {response}")
            return None

        # Merge with existing requirements, preferring AI results for missing fields
        for key, value in ai_requirements.items():
            if requirements.get(key) is None and value is not None:
                requirements[key] = value
        return requirements

    def enhance_with_gemini(self, message: str, requirements: Dict, gemini_handler) -> Optional[Dict]:
        """Enhance requirements using Gemini"""
        if not gemini_handler or not gemini_handler.model:
            return None

        prompt = f"""
        Extract accommodation requirements from this WhatsApp message. Return only valid JSON:

        Message: "{message}"

        Current extraction: {json.dumps(requirements)}

        Extract and enhance:
        - Number of people/heads needed
        - Required amenities (wifi, parking, etc.)
        - Maximum budget
        - Location preferences
        - Gender preference (male/female/any)
        - Urgency level

        Return valid JSON with these keys: heads, amenities, budget_max, distance_preference, location_context, gender_preference, urgency

        Only include values that improve upon the current extraction.
        """

        response = gemini_handler.call_api(prompt, temperature=0.3)
        if not response:
            return None

        ai_requirements = self._safe_parse_json(response)
        if not isinstance(ai_requirements, dict):
            logger.warning("Invalid JSON response from Gemini")
            logger.debug(f"Gemini enhancement raw response: {response}")
            return None

        # Merge with existing requirements, preferring AI results for missing fields
        for key, value in ai_requirements.items():
            if requirements.get(key) is None and value is not None:
                requirements[key] = value
        return requirements

    def _extract_heads_count(self, message: str) -> Optional[int]:
        """Extract number of heads/bedrooms from message"""
        # Look for explicit numbers
        number_pattern = r'\b(\d+)\s*(?:heads?|bedrooms?|beds?|people?|person|sharing|room)\b'
        match = re.search(number_pattern, message)
        if match:
            return int(match.group(1))

        # Look for descriptive terms
        for term, count in self.heads_keywords.items():
            if term in message.lower():
                return count

        return None

    def _extract_amenities(self, message: str) -> List[str]:
        """Extract required amenities from message"""
        found_amenities = []

        for keyword, amenity in self.amenity_keywords.items():
            if keyword in message.lower():
                if amenity not in found_amenities:
                    found_amenities.append(amenity)

        return found_amenities

    def _extract_budget(self, message: str) -> Optional[float]:
        """Extract budget information from message"""
        # Look for USD amounts
        usd_pattern = r'\$?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)|\$?(\d+)\s*(?:dollars?|usd|us)'
        matches = re.findall(usd_pattern, message)

        budgets = []
        for match in matches:
            amount = next((m for m in match if m), None)
            if amount:
                amount = float(amount.replace(',', ''))
                budgets.append(amount)

        return max(budgets) if budgets else None

    def _extract_location(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract location preferences and context"""
        distance_preference = None
        location_context = None

        # Check for distance keywords
        for keyword, preference in self.location_keywords.items():
            if keyword in message.lower():
                if preference in ['near', 'far']:
                    distance_preference = preference
                else:
                    location_context = preference
                break

        # Extract specific location mentions
        location_patterns = [
            r'near\s+([a-z\s]+)', r'close\s+to\s+([a-z\s]+)',
            r'walking\s+distance\s+to\s+([a-z\s]+)', r'by\s+([a-z\s]+)'
        ]

        for pattern in location_patterns:
            match = re.search(pattern, message.lower())
            if match:
                location_context = match.group(1).strip()
                break

        return distance_preference, location_context

    def _extract_gender_preference(self, message: str) -> Optional[str]:
        """Extract gender preference if mentioned"""
        message_lower = message.lower()
        if any(word in message_lower for word in ['male', 'boys', 'guys', 'mens']):
            return 'male'
        elif any(word in message_lower for word in ['female', 'girls', 'ladies', 'womens']):
            return 'female'
        elif 'mixed' in message_lower or 'any' in message_lower or 'no preference' in message_lower:
            return 'any'

        return None

    def _extract_urgency(self, message: str) -> Optional[str]:
        """Extract urgency level if mentioned"""
        message_lower = message.lower()
        urgent_words = ['urgent', 'asap', 'immediately', 'quickly', 'soon']
        moderate_words = ['within', 'before', 'by']

        if any(word in message_lower for word in urgent_words):
            return 'high'
        elif any(word in message_lower for word in moderate_words):
            return 'medium'

        return None

    def validate_requirements(self, requirements: Dict) -> Dict:
        """Validate and clean extracted requirements"""
        validated = requirements.copy()

        # Validate heads count
        if validated['heads'] is not None:
            if validated['heads'] < 1:
                validated['heads'] = 1
            elif validated['heads'] > 10:
                validated['heads'] = 10

        # Validate budget
        if validated['budget_max'] is not None:
            if validated['budget_max'] < 10:
                validated['budget_max'] = None
            elif validated['budget_max'] > 10000:
                validated['budget_max'] = 10000

        # Clean amenities list
        if validated['amenities']:
            validated['amenities'] = list(set(validated['amenities']))

        return validated

    def format_requirements_for_display(self, requirements: Dict) -> str:
        """Format requirements for WhatsApp display"""
        parts = []

        if requirements.get('heads'):
            parts.append(f"{requirements['heads']} heads")

        if requirements.get('amenities'):
            amenities_str = ', '.join(requirements['amenities'][:3])
            parts.append(f" {amenities_str}")

        if requirements.get('budget_max'):
            parts.append(f" Max ${requirements['budget_max']}")

        if requirements.get('distance_preference'):
            parts.append(f" {requirements['distance_preference']} to campus")

        if requirements.get('gender_preference'):
            parts.append(f" {requirements['gender_preference']} only")

        return ' | '.join(parts) if parts else "Requirements extracted"