"""Compatibility adapter exposing the Supabase property matcher to Django callers.

The WhatsApp conversation layer still imports ``property_matcher`` from this module,
but property matching itself is now executed by the Supabase Edge Function. This
module deliberately contains no Django ORM queries.
"""

from __future__ import annotations

from typing import Dict, List

from .supabase_property_matcher import SupabasePropertyMatcher


class SupabaseBackedPropertyMatcher:
    """Drop-in matcher interface backed exclusively by Supabase."""

    def __init__(self) -> None:
        self._matcher = SupabasePropertyMatcher()

    def match_properties(self, requirements: Dict, limit: int = 5) -> List[Dict]:
        return self._matcher.match_properties(requirements, limit=limit)

    def format_property_for_whatsapp(self, property, score: float, reasons: List[str]) -> str:
        amenities = getattr(property, "amenities", None) or []
        return (
            f" {property.name}\n"
            f"Price: ${getattr(property, 'price_per_month', 0)}/month\n"
            f"Available rooms: {getattr(property, 'available_1h_rooms', 0)} single, "
            f"{getattr(property, 'available_2h_rooms', 0)} double, "
            f"{getattr(property, 'available_3h_rooms', 0)} triple, "
            f"{getattr(property, 'available_4h_rooms', 0)} quad\n"
            f"Distance: {getattr(property, 'distance_from_campus', 0)}km from "
            f"{getattr(property, 'campus_name', 'campus')}\n"
            f"🏘️ {getattr(property, 'address', '')}\n\n"
            f" Amenities: {', '.join(amenities[:3]) if amenities else 'Basic'}\n"
            f" Available rooms: {getattr(property, 'available_rooms', 0)}/{getattr(property, 'total_rooms', 0)}\n\n"
            f"Match score: {score}/50"
            + (f"\n Why it matches: {' | '.join(reasons[:2])}" if reasons else "")
        )

    def get_property_summary_stats(self, properties) -> Dict:
        if not properties:
            return {}
        prices = [float(getattr(p, "price_per_month", 0) or 0) for p in properties]
        distances = [float(getattr(p, "distance_from_campus", 0) or 0) for p in properties]
        ratings = [
            float(getattr(getattr(p, "provider", None), "rating", 0) or 0)
            for p in properties
            if float(getattr(getattr(p, "provider", None), "rating", 0) or 0) > 0
        ]
        return {
            "count": len(properties),
            "avg_price": round(sum(prices) / len(prices), 2),
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_distance": round(sum(distances) / len(distances), 2),
            "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
        }


property_matcher = SupabaseBackedPropertyMatcher()
DjangoPropertyMatcher = SupabaseBackedPropertyMatcher
