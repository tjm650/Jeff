import re
from typing import Optional, List, Tuple

class RequirementExtractor:
    def __init__(self):
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

        # Bulawayo-specific locations (prioritized)
        self.bulawayo_locations = [
            'nust', 'riverside', 'selborne park', 'southwold', 'cbd',
            'hillside', 'suburbs', 'city centre', 'belmont', 'kumalo',
            'matsheumhlope', 'burnside', 'famona', 'morningside'
        ]
        
        # Campus names
        self.campus_names = ['nust', 'gzu', 'msu', 'uz', 'university']
        
        self.location_keywords = {
            'near': 'near', 'close': 'near', 'walking distance': 'near',
            'far': 'far', 'distant': 'far',
            'campus': 'campus', 'university': 'campus', 'school': 'campus',
            'town': 'town', 'city': 'town', 'center': 'town',
            'mall': 'mall', 'shopping': 'mall',
            'hospital': 'hospital', 'clinic': 'hospital'
        }
        # Rental period keywords
        self.period_keywords = {
            'day': ['per day', '/day', 'daily', 'day', 'night', 'nightly', 'per night'],
            'week': ['per week', '/week', 'weekly', 'week'],
            'month': ['per month', '/month', 'monthly', 'month']
        }

    def _extract_heads_count(self, message: str) -> Optional[int]:
        number_pattern = r'\b(\d+)\s*(?:heads?|bedrooms?|beds?|people?|person|sharing|room)\b'
        match = re.search(number_pattern, message)
        if match:
            return int(match.group(1))

        for term, count in self.heads_keywords.items():
            if term in message.lower():
                return count

        return None

    def _extract_amenities(self, message: str) -> List[str]:
        found_amenities = []

        for keyword, amenity in self.amenity_keywords.items():
            if keyword in message.lower():
                if amenity not in found_amenities:
                    found_amenities.append(amenity)

        return found_amenities

    def _extract_budget(self, message: str) -> Optional[float]:
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
        distance_preference = None
        location_context = None
        message_lower = message.lower()

        # First, check for Bulawayo-specific locations (prioritized)
        for location in self.bulawayo_locations:
            if location in message_lower:
                location_context = location.title()  # Capitalize properly
                # Check if it's near/close to this location
                if re.search(r'(near|close|walking distance)\s+' + location, message_lower):
                    distance_preference = 'near'
                break

        # Check for campus names
        if not location_context:
            for campus in self.campus_names:
                if campus in message_lower:
                    location_context = campus.upper() if campus != 'university' else 'campus'
                    # Check for "near campus" patterns
                    if re.search(r'(near|close|walking distance)\s+(campus|' + campus + ')', message_lower):
                        distance_preference = 'near'
                    break

        # Fallback to generic location keywords
        if not location_context:
            for keyword, preference in self.location_keywords.items():
                if keyword in message_lower:
                    if preference in ['near', 'far']:
                        distance_preference = preference
                    else:
                        location_context = preference
                    break

        # Extract location from patterns (if not already found)
        if not location_context:
            location_patterns = [
                r'near\s+([a-z\s]+)', r'close\s+to\s+([a-z\s]+)',
                r'walking\s+distance\s+to\s+([a-z\s]+)', r'by\s+([a-z\s]+)'
            ]

            for pattern in location_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    extracted = match.group(1).strip()
                    # Check if extracted location is a known Bulawayo location
                    for location in self.bulawayo_locations:
                        if location in extracted:
                            location_context = location.title()
                            break
                    if not location_context:
                        location_context = extracted
                    break

        return distance_preference, location_context

    def _extract_gender_preference(self, message: str) -> Optional[str]:
        message_lower = message.lower()
        if any(word in message_lower for word in ['male', 'boys', 'guys', 'mens']):
            return 'male'
        elif any(word in message_lower for word in ['female', 'girls', 'ladies', 'womens']):
            return 'female'
        elif 'mixed' in message_lower or 'any' in message_lower or 'no preference' in message_lower:
            return 'any'

        return None

    def _extract_urgency(self, message: str) -> Optional[str]:
        message_lower = message.lower()
        urgent_words = ['urgent', 'asap', 'immediately', 'quickly', 'soon']
        moderate_words = ['within', 'before', 'by']

        if any(word in message_lower for word in urgent_words):
            return 'high'
        elif any(word in message_lower for word in moderate_words):
            return 'medium'

        return None

    def _extract_rental_period(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        """Detect requested rental period (day/week/month) and budget unit if present

        Returns:
            (rental_period, budget_unit) where rental_period and budget_unit are one of
            'day', 'week', 'month' or None when not detected. budget_unit mirrors rental_period
        """
        message_lower = message.lower()
        detected_period = None
        for period, keywords in self.period_keywords.items():
            for kw in keywords:
                if kw in message_lower:
                    detected_period = period
                    break
            if detected_period:
                break

        # If user mentions numbers like '7 days' or '3 weeks' prefer that for detection
        if not detected_period:
            if re.search(r'\b\d+\s*(?:days|day|nights)\b', message_lower):
                detected_period = 'day'
            elif re.search(r'\b\d+\s*(?:weeks|week)\b', message_lower):
                detected_period = 'week'

        # Determine budget unit: if message contains explicit 'per X' use that, otherwise None
        budget_unit = None
        if re.search(r'per\s*day|/day|per\s*night|nightly', message_lower):
            budget_unit = 'day'
        elif re.search(r'per\s*week|/week|weekly', message_lower):
            budget_unit = 'week'
        elif re.search(r'per\s*month|/month|monthly', message_lower):
            budget_unit = 'month'

        return detected_period, budget_unit

    def extract_requirements(self, message: str) -> dict:
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
            'rental_period': None,  # 'day'|'week'|'month'
            'budget_unit': None,    # if budget stated as per-day/per-week
            'raw_message': message
        }

        # Extract using rule-based methods
        requirements['heads'] = self._extract_heads_count(message)
        requirements['amenities'] = self._extract_amenities(message)
        requirements['budget_max'] = self._extract_budget(message)
        requirements['distance_preference'], requirements['location_context'] = self._extract_location(message)
        requirements['gender_preference'] = self._extract_gender_preference(message)
        requirements['urgency'] = self._extract_urgency(message)
        # Extract rental period / budget unit (per day/week/month)
        rental_period, budget_unit = self._extract_rental_period(message)
        if rental_period:
            requirements['rental_period'] = rental_period
        if budget_unit:
            requirements['budget_unit'] = budget_unit

        return requirements

    def validate_requirements(self, requirements: dict) -> dict:
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

    def format_requirements_for_display(self, requirements: dict) -> str:
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