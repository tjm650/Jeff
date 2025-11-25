from typing import List, Dict, Tuple
from django.db.models import Q, Avg
from django.core.cache import cache
from django.conf import settings
from core.models import Property
from .nlp_processor import nlp_processor
import math
import logging
import hashlib

logger = logging.getLogger(__name__)

class DjangoPropertyMatcher:
    """Django ORM-based property matching algorithm"""

    def __init__(self):
        # Scoring weights for different criteria
        self.weights = {
            'heads_match': 10.0,
            'amenity_match': 5.0,
            'budget_fit': 8.0,
            'distance_score': 7.0,
            'availability': 5.0,
            'rating_score': 3.0,
            'gender_preference': 2.0
        }

    def match_properties(self, requirements: Dict, limit: int = 5) -> List[Dict]:
        """
        Find and score properties based on student requirements

        Args:
            requirements (Dict): Extracted student requirements
            limit (int): Maximum number of properties to return

        Returns:
            List[Dict]: Sorted list of matched properties with scores
        """
        try:
            # Generate cache key based on requirements
            cache_key = self._generate_cache_key(requirements, limit)
            
            # Try to get from cache first
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for property matching: {cache_key}")
                return cached_result

            # Build query based on requirements
            queryset = self._build_property_query(requirements)

            # Get properties with related data - optimized query
            properties = queryset.select_related('provider').prefetch_related(
                'reviews', 'bookings'
            ).only(
                'id', 'name', 'address', 'total_rooms', 
                'available_rooms', 'amenities', 'price_per_month', 'price_per_week', 'price_per_day',
                'available_1h_rooms', 'available_2h_rooms', 'available_3h_rooms', 'available_4h_rooms',
                'distance_from_campus', 'campus_name', 'gender_preference',
                'is_active', 'provider__rating', 'provider__total_reviews'
            )[:limit * 2]  # Get more for scoring

            scored_properties = []

            for property in properties:
                score = self._calculate_property_score(property, requirements)
                if score > 0:  # Only include properties with positive scores
                    scored_properties.append({
                        'property': property,
                        'score': score,
                        'match_reasons': self._get_match_reasons(property, requirements, score)
                    })

            # Sort by score (descending) and return top matches
            scored_properties.sort(key=lambda x: x['score'], reverse=True)
            result = scored_properties[:limit]

            # Cache the result for 5 minutes
            cache.set(cache_key, result, 300)
            logger.debug(f"Cached property matching result: {cache_key}")

            return result

        except Exception as e:
            logger.error(f"Error in property matching: {str(e)}")
            return []

    def _build_property_query(self, requirements: Dict):
        """Build Django query based on requirements"""
        queryset = Property.objects.filter(is_active=True)

        # Filter by heads/room size based on available rooms
        if requirements.get('heads'):
            heads = requirements['heads']
            # Check available rooms for each head configuration
            if heads == 1:
                queryset = queryset.filter(available_1h_rooms__gt=0)
            elif heads == 2:
                queryset = queryset.filter(available_2h_rooms__gt=0)
            elif heads == 3:
                queryset = queryset.filter(available_3h_rooms__gt=0)
            elif heads == 4:
                queryset = queryset.filter(available_4h_rooms__gt=0)

        # Filter by budget, respecting a requested rental period (day/week/month)
        if requirements.get('budget_max'):
            budget_max = requirements['budget_max']
            # Determine which price field to use
            period = requirements.get('rental_period') or requirements.get('budget_unit')
            if period == 'day':
                queryset = queryset.filter(price_per_day__lte=budget_max)
            elif period == 'week':
                queryset = queryset.filter(price_per_week__lte=budget_max)
            else:
                # Default to monthly comparison
                queryset = queryset.filter(price_per_month__lte=budget_max)

        # Filter by amenities (if specified)
        if requirements.get('amenities'):
            amenities = requirements['amenities']
            # Properties must have all required amenities
            try:
                for amenity in amenities:
                    queryset = queryset.filter(amenities__contains=[amenity])
            except Exception as e:
                # Some DB backends (SQLite without JSON support) do not support contains lookup
                # Skip DB-level amenities filtering and rely on Python-side scoring to match amenities
                logger.warning(f"Amenities DB filter not supported, will apply amenities filtering in Python: {e}")

        # Filter by gender preference
        if requirements.get('gender_preference') and requirements['gender_preference'] == 'any':
            gender_pref = requirements['gender_preference']
            queryset = queryset.filter(gender_preference__in=[gender_pref, 'any'])

        # Filter by distance preference
        if requirements.get('distance_preference'):
            distance_pref = requirements['distance_preference']
            if distance_pref == 'near':
                queryset = queryset.filter(distance_from_campus__lte=2.0)
            elif distance_pref == 'far':
                queryset = queryset.filter(distance_from_campus__gte=3.0)

        # Filter by location context (campus name)
        if requirements.get('location_context'):
            location_context = requirements['location_context']
            queryset = queryset.filter(campus_name__icontains=location_context)

        # If keyword tokens / expanded keywords exist, broaden results by matching text fields
        # We'll OR name/address/campus_name/description against any of the keywords to get relevant candidates.
        keywords = []
        if requirements.get('expanded_keywords') and isinstance(requirements.get('expanded_keywords'), list):
            keywords = [k for k in requirements.get('expanded_keywords') if k]
        elif requirements.get('keyword_tokens') and isinstance(requirements.get('keyword_tokens'), list):
            keywords = [k for k in requirements.get('keyword_tokens') if k]

        if keywords:
            try:
                from django.db.models import Q
                q_any = None
                for kw in keywords:
                    kw = kw.strip()
                    if not kw:
                        continue
                    # Build OR across several text fields
                    q_part = Q(name__icontains=kw) | Q(address__icontains=kw) | Q(campus_name__icontains=kw)
                    # description may not be present on all models; guard against attribute absence
                    try:
                        q_part = q_part | Q(description__icontains=kw)
                    except Exception:
                        pass

                    if q_any is None:
                        q_any = q_part
                    else:
                        q_any = q_any | q_part

                if q_any is not None:
                    queryset = queryset.filter(q_any)
            except Exception as e:
                logger.warning(f"Keyword text filtering failed, continuing without text filters: {e}")

        return queryset

    def _generate_cache_key(self, requirements: Dict, limit: int) -> str:
        """Generate a cache key based on requirements and limit"""
        try:
            # Prefer a compact, stable key: include known scalar fields and expanded keywords
            keys = []
            for k in ['heads', 'budget_max', 'rental_period', 'location_context', 'distance_preference', 'gender_preference']:
                v = requirements.get(k)
                keys.append(f"{k}={v}")

            # Include sorted keywords if present
            keywords = []
            if isinstance(requirements.get('expanded_keywords'), list):
                keywords = sorted([str(x) for x in requirements.get('expanded_keywords') if x])
            elif isinstance(requirements.get('keyword_tokens'), list):
                keywords = sorted([str(x) for x in requirements.get('keyword_tokens') if x])

            keys.append(f"keywords={'|'.join(keywords)}")
            keys.append(f"limit={limit}")
            cache_data = "property_match_" + "::".join(keys)
            return hashlib.md5(cache_data.encode()).hexdigest()
        except Exception:
            # Fallback to safer stringify
            requirements_str = str(sorted([(str(k), str(v)) for k, v in requirements.items()]))
            cache_data = f"property_match_{requirements_str}_{limit}"
            return hashlib.md5(cache_data.encode()).hexdigest()

    def _calculate_property_score(self, property: Property, requirements: Dict) -> float:
        """Calculate total score for a property against requirements"""
        total_score = 0.0

        # 1. Heads/room size match (most important)
        heads_score = self._score_heads_match(property, requirements)
        total_score += heads_score

        # 2. Amenities match
        amenity_score = self._score_amenities_match(property, requirements)
        total_score += amenity_score

        # 3. Budget compatibility
        budget_score = self._score_budget_fit(property, requirements)
        total_score += budget_score

        # 4. Distance preference
        distance_score = self._score_distance(property, requirements)
        total_score += distance_score

        # 5. Availability
        availability_score = self._score_availability(property)
        total_score += availability_score

        # 6. Property rating
        rating_score = self._score_rating(property)
        total_score += rating_score

        # 7. Gender preference
        gender_score = self._score_gender_preference(property, requirements)
        total_score += gender_score

        return round(total_score, 2)

    def _score_heads_match(self, property: Property, requirements: Dict) -> float:
        """Score based on heads/room size match"""
        required_heads = requirements.get('heads')
        if not required_heads:
            return self.weights['heads_match'] * 0.5  # Neutral score if no preference

        # Check available rooms for the required head configuration
        if required_heads == 1 and property.available_1h_rooms > 0:
            return self.weights['heads_match']  # Perfect match
        elif required_heads == 2 and property.available_2h_rooms > 0:
            return self.weights['heads_match']  # Perfect match
        elif required_heads == 3 and property.available_3h_rooms > 0:
            return self.weights['heads_match']  # Perfect match
        elif required_heads == 4 and property.available_4h_rooms > 0:
            return self.weights['heads_match']  # Perfect match
            
        # No matching rooms available
        return 0.0

    def _score_amenities_match(self, property: Property, requirements: Dict) -> float:
        """Score based on amenities match"""
        required_amenities = requirements.get('amenities', [])
        if not required_amenities:
            return self.weights['amenity_match'] * 0.5  # Neutral if no requirements

        property_amenities = property.amenities or []
        if not property_amenities:
            return 0.0

        # Calculate percentage of required amenities available
        matched_amenities = 0
        for amenity in required_amenities:
            if amenity.lower() in [a.lower() for a in property_amenities]:
                matched_amenities += 1

        match_percentage = matched_amenities / len(required_amenities)
        return self.weights['amenity_match'] * match_percentage

    def _score_budget_fit(self, property: Property, requirements: Dict) -> float:
        """Score based on budget compatibility"""
        budget_max = requirements.get('budget_max')
        if not budget_max:
            return self.weights['budget_fit'] * 0.5  # Neutral if no budget specified

        # Select the appropriate price field based on requested rental period
        period = requirements.get('rental_period') or requirements.get('budget_unit')
        try:
            if period == 'day':
                # Prefer explicit day price; if missing, approximate from monthly
                property_price = float(property.price_per_day) if property.price_per_day else (float(property.price_per_month) / 30.0 if property.price_per_month else 0.0)
            elif period == 'week':
                property_price = float(property.price_per_week) if property.price_per_week else (float(property.price_per_month) / 4.0 if property.price_per_month else 0.0)
            else:
                property_price = float(property.price_per_month)
        except Exception:
            property_price = float(property.price_per_month)

        if property_price <= 0:
            return 0.0

        if property_price <= budget_max:
            # Within budget - score based on how much under budget
            budget_ratio = property_price / budget_max
            if budget_ratio >= 0.8:  # Within 20% of budget
                return self.weights['budget_fit']
            else:  # Much cheaper - still good
                return self.weights['budget_fit'] * 0.9
        else:
            # Over budget - score based on how much over
            over_ratio = property_price / budget_max
            if over_ratio <= 1.2:  # Within 20% over budget
                return self.weights['budget_fit'] * 0.3
            else:
                return 0.0  # Too expensive

    def _score_distance(self, property: Property, requirements: Dict) -> float:
        """Score based on distance preference"""
        distance_preference = requirements.get('distance_preference')
        if not distance_preference:
            return self.weights['distance_score'] * 0.5  # Neutral if no preference

        property_distance = property.distance_from_campus

        if distance_preference == 'near':
            if property_distance <= 1.0:  # Within 1km
                return self.weights['distance_score']
            elif property_distance <= 2.0:  # Within 2km
                return self.weights['distance_score'] * 0.7
            elif property_distance <= 5.0:  # Within 5km
                return self.weights['distance_score'] * 0.4
            else:
                return 0.0
        elif distance_preference == 'far':
            if property_distance >= 3.0:  # Far from campus
                return self.weights['distance_score']
            else:
                return self.weights['distance_score'] * 0.3

        return self.weights['distance_score'] * 0.5

    def _score_availability(self, property: Property) -> float:
        """Score based on room availability"""
        if property.available_rooms > 0:
            # Bonus for high availability
            availability_ratio = property.available_rooms / property.total_rooms
            if availability_ratio >= 0.5:  # 50% or more available
                return self.weights['availability']
            else:
                return self.weights['availability'] * 0.7
        else:
            return 0.0  # No rooms available

    def _score_rating(self, property: Property) -> float:
        """Score based on property rating"""
        if property.provider.rating:
            # Convert rating to 0-1 scale and multiply by weight
            rating_ratio = property.provider.rating / 5.0
            return self.weights['rating_score'] * rating_ratio
        return self.weights['rating_score'] * 0.5  # Neutral if no rating

    def _score_gender_preference(self, property: Property, requirements: Dict) -> float:
        """Score based on gender preference match"""
        gender_preference = requirements.get('gender_preference')
        if not gender_preference or gender_preference == 'any':
            return self.weights['gender_preference'] * 0.5  # Neutral

        property_gender_pref = property.gender_preference

        if property_gender_pref == 'any':
            return self.weights['gender_preference'] * 0.8  # Flexible property
        elif property_gender_pref == gender_preference:
            return self.weights['gender_preference']  # Perfect match
        else:
            return 0.0  # Gender preference mismatch

    def _get_match_reasons(self, property: Property, requirements: Dict, score: float) -> List[str]:
        """Generate human-readable reasons for the match"""
        reasons = []

        # Check each scoring factor
        if self._score_heads_match(property, requirements) > 0:
            required_heads = requirements.get('heads')
            if required_heads == 1 and property.available_1h_rooms > 0:
                reasons.append(f" {property.available_1h_rooms} single rooms")
            elif required_heads == 2 and property.available_2h_rooms > 0:
                reasons.append(f" {property.available_2h_rooms} double rooms")
            elif required_heads == 3 and property.available_3h_rooms > 0:
                reasons.append(f" {property.available_3h_rooms} triple rooms")
            elif required_heads == 4 and property.available_4h_rooms > 0:
                reasons.append(f" {property.available_4h_rooms} quad rooms")

        if self._score_amenities_match(property, requirements) > 0:
            matched_amenities = requirements.get('amenities', [])
            property_amenities = property.amenities or []
            matched = [a for a in matched_amenities if a.lower() in [pa.lower() for pa in property_amenities]]
            if matched:
                reasons.append(f" {', '.join(matched[:2])}")

        if self._score_budget_fit(property, requirements) > 0:
            reasons.append(f" ${property.price_per_month}/month")

        if self._score_distance(property, requirements) > 0:
            reasons.append(f" {property.distance_from_campus}km from campus")

        if self._score_availability(property) > 0:
            reasons.append(f" {property.available_rooms} rooms available")

        return reasons

    def format_property_for_whatsapp(self, property: Property, score: float, reasons: List[str]) -> str:
        """Format property information for WhatsApp display"""
        # Basic property info
        message = f""" {property.name}
Price: ${property.price_per_month}/month
Available rooms: {property.available_1h_rooms} single, {property.available_2h_rooms} double, {property.available_3h_rooms} triple, {property.available_4h_rooms} quad
Distance: {property.distance_from_campus}km from {property.campus_name}
🏘️ {property.address}

 Amenities: {', '.join(property.amenities[:3]) if property.amenities else 'Basic'}
 Available rooms: {property.available_rooms}/{property.total_rooms}

Match score: {score}/50"""

        if reasons:
            message += f"\n Why it matches: {' | '.join(reasons[:2])}"

        return message

    def get_property_summary_stats(self, properties) -> Dict:
        """Get summary statistics for a list of properties"""
        if not properties:
            return {}

        prices = [float(p.price_per_month) for p in properties]
        distances = [p.distance_from_campus for p in properties]
        ratings = [p.provider.rating for p in properties if p.provider.rating]

        return {
            'count': len(properties),
            'avg_price': round(sum(prices) / len(prices), 2),
            'min_price': min(prices),
            'max_price': max(prices),
            'avg_distance': round(sum(distances) / len(distances), 2),
            'avg_rating': round(sum(ratings) / len(ratings), 2) if ratings else 0
        }

# Global instance
property_matcher = DjangoPropertyMatcher()