"""Supabase-backed property search for the legacy Django compatibility layer.

This module intentionally contains no Django ORM/model imports. Production WhatsApp
traffic is handled by the Supabase jeff-conversation Edge Function; this adapter
exists only so any remaining legacy callers also use the same Supabase search and
conversation state instead of a second Django implementation.
"""

import logging
import os
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .property_search_supabase import supabase_property_search

logger = logging.getLogger(__name__)


class PropertySearchHandler:
    """Compatibility facade backed by Supabase search and conversation state."""

    def _phone(self, conversation) -> Optional[str]:
        return getattr(conversation, "cell_number", None) or getattr(conversation, "phone_number", None)

    def proceed_to_property_search(self, conversation, requirements: Dict) -> str:
        phone = self._phone(conversation)
        validated = requirements.get("validated_requirements", requirements) if isinstance(requirements, dict) else {}
        if not validated:
            return "Error: No valid requirements found. Please try again."

        criteria = ("heads", "budget_max", "amenities", "location_context", "gender_preference")
        if not any(validated.get(k) for k in criteria) and not any(
            validated.get(k) for k in ("expanded_keywords", "keyword_tokens", "raw_message")
        ):
            return "Error: No search criteria found. Please provide more details about what you're looking for."

        try:
            matches = supabase_property_search.search(validated, limit=5)
            if not matches:
                relaxed = self._relax_search_criteria(validated)
                if relaxed != validated:
                    matches = supabase_property_search.search(relaxed, limit=5)
                    if matches:
                        validated = relaxed

            properties = self._process_search_results(matches, validated)
            if phone:
                try:
                    supabase_property_search.save_search_state(phone, validated, matches)
                except Exception:
                    logger.exception("Failed to persist Supabase search state for %s", phone)

            if not properties:
                return self._get_no_properties_message(validated)

            return self._format_enhanced_property_listing(properties, validated, conversation)
        except Exception:
            logger.exception("Supabase property search failed for %s", phone)
            return "Error searching for properties. Please try again."

    def _relax_search_criteria(self, requirements: Dict) -> Dict:
        relaxed = dict(requirements or {})
        if relaxed.get("budget_max"):
            try:
                relaxed["budget_max"] = float(relaxed["budget_max"]) * 1.2
            except (TypeError, ValueError):
                pass
        if not relaxed.get("amenities"):
            relaxed["amenities"] = []
        if relaxed.get("location_context") and len(str(relaxed["location_context"])) < 3:
            relaxed["location_context"] = None
        return relaxed

    def _process_search_results(self, matches: List[Dict], requirements: Dict) -> List[Dict]:
        properties = []
        for match in matches or []:
            raw = match.get("property") or {}
            if not raw.get("id") or not raw.get("name"):
                continue
            amenities = raw.get("amenities") or []
            if not isinstance(amenities, list):
                amenities = list(amenities.keys()) if isinstance(amenities, dict) else []
            availability = {
                "available_1h_rooms": int(raw.get("available_1h_rooms") or 0),
                "available_2h_rooms": int(raw.get("available_2h_rooms") or 0),
                "available_3h_rooms": int(raw.get("available_3h_rooms") or 0),
                "available_4h_rooms": int(raw.get("available_4h_rooms") or 0),
            }
            properties.append({
                "id": str(raw["id"]),
                "name": raw["name"],
                "rating": float(raw.get("rating") or raw.get("providers", {}).get("rating") or 0),
                "price_per_month": float(raw.get("price_per_month") or 0),
                "price_per_week": float(raw.get("price_per_week") or 0),
                "price_per_day": float(raw.get("price_per_day") or 0),
                "distance_from_campus": float(raw.get("distance_from_campus") or 0),
                "amenities": amenities,
                "available_rooms": int(raw.get("available_rooms") or 0),
                **availability,
                "campus_name": raw.get("campus_name") or "Unknown Campus",
                "match_score": float(match.get("score") or 0),
                "match_reasons": list(match.get("match_reasons") or []),
                "provider_id": raw.get("provider_id"),
                "provider": raw.get("providers") or {},
            })
        return properties[:50]

    def _get_no_properties_message(self, requirements: Dict, cell_number: str = None) -> str:
        return (
            "*No Properties Found*\n\n"
            "I couldn't find accommodation matching those requirements. "
            "Try adjusting your budget, room size, location or amenities."
        )

    def _get_match_reasons(self, match: Dict, requirements: Dict) -> List[str]:
        return list(match.get("match_reasons") or [])[:3]

    def _format_enhanced_property_listing(self, properties: List[Dict], requirements: Dict, conversation=None) -> str:
        if not properties:
            return self._get_no_properties_message(requirements, self._phone(conversation) if conversation else None)

        period = requirements.get("rental_period") or requirements.get("budget_unit") or "month"
        invert = bool(requirements.get("invert_sort", False))

        def price(p):
            value = p.get("price_per_day") if period == "day" else p.get("price_per_week") if period == "week" else p.get("price_per_month")
            return float(value or 0)

        properties = sorted(properties, key=lambda p: (float(p.get("rating") or 0), price(p)), reverse=not invert)
        page = 0
        if isinstance(requirements, dict):
            try:
                page = max(0, int(requirements.get("current_property_page", 0) or 0))
            except (TypeError, ValueError):
                page = 0
        current = properties[page * 5:(page + 1) * 5]

        confidence = requirements.get("confidence_score", 0)
        message = f"*PROPERTY LISTINGS* 🏡\n*Properties Found:* {len(properties)}\n"
        if confidence:
            message += f"*Match confidence*: ({int(float(confidence) * 100)}%)\n\n"
        else:
            message += "\n"

        for index, prop in enumerate(current, 1):
            message += f"{['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣'][index-1]}. *{str(prop['name']).upper()}*\n"
            message += f"• Monthly price: ${prop['price_per_month']:.2f}\n" if prop['price_per_month'] > 0 else "• Monthly price: N/A\n"
            message += f"• Weekly price: ${prop['price_per_week']:.2f}\n" if prop['price_per_week'] > 0 else "• Weekly price: N/A\n"
            message += f"• Daily price: ${prop['price_per_day']:.2f}\n" if prop['price_per_day'] > 0 else "• Daily price: N/A\n"
            for key, label in (("available_1h_rooms", "1H/R"), ("available_2h_rooms", "2H/R"), ("available_3h_rooms", "3H/R"), ("available_4h_rooms", "4H/R")):
                value = prop.get(key, 0)
                message += f"• {label}: {int(value)} available\n" if value else f"• {label}: N/A\n"
            total_heads = sum(int(prop.get(k, 0) or 0) for k in ("available_1h_rooms", "available_2h_rooms", "available_3h_rooms", "available_4h_rooms"))
            message += f"• Total Available Heads: {total_heads}\n" if total_heads else "• Total Available Heads: N/A\n"
            message += f"• Distance: *{prop['distance_from_campus']}km* from campus\n"
            if prop.get("amenities"):
                message += f"• Amenities: {', '.join(map(str, prop['amenities'][:3]))}\n"
            if prop.get("match_reasons"):
                message += f"{prop['match_reasons'][0]}: ✅\n"
            message += "\n"

        if len(properties) > 5:
            message += f"*Showing properties {page * 5 + 1}-{min((page + 1) * 5, len(properties))} of {len(properties)}*\n"
        if (page + 1) * 5 < len(properties):
            message += "\n_3. Send 'show-more' to view more properties_\n"
        message += (
            "\n_1. Reply with 'option-(number)' to proceed for booking (e.g. 'option-1')_\n"
            "_2. Send an abort message to cancel your enquiry and start a different search._"
        )
        frontend_url = os.getenv("NEXT_PUBLIC_FRONTEND_URL")
        if frontend_url:
            message += f"\n• _Send 'Jeff' for more info or visit {frontend_url}_"
        return message

    def show_property_listings(self, conversation) -> str:
        phone = self._phone(conversation)
        if not phone:
            return "No properties available for selection. Please search for accommodation first."
        try:
            encoded = urllib.parse.quote(phone, safe="")
            rows = self._read_conversation(encoded)
            if not rows:
                return "No properties available for selection. Please search for accommodation first."
            state = rows[0]
            context = state.get("context_data") or {}
            requirements = context.get("search_requirements") or context.get("requirements") or {}
            requirements["current_property_page"] = context.get("current_property_page", 0)
            properties = context.get("search_results") or []
            if not properties:
                return self._get_no_properties_message(requirements, phone)
            matches = [{"property": p, "score": p.get("match_score", 0), "match_reasons": p.get("match_reasons", [])} for p in properties]
            return self._format_enhanced_property_listing(self._process_search_results(matches, requirements), requirements, conversation)
        except Exception:
            logger.exception("Failed to read Supabase property listings for %s", phone)
            return "Error displaying property listings. Please try again."

    def _read_conversation(self, encoded_phone: str):
        from .property_search_supabase import _rest
        return _rest("GET", "conversations", query=(
            "?select=id,current_step,context_data,selected_properties"
            f"&phone_number=eq.{encoded_phone}&status=eq.active&order=updated_at.desc&limit=1"
        ))

    def _get_fallback_recommendation_message(self, requirements: Dict) -> str:
        suggestions = []
        if requirements.get("budget_max"):
            suggestions.append(f"Consider adjusting your budget (currently ${requirements['budget_max']}).")
        if requirements.get("heads"):
            suggestions.append(f"Try a different room-sharing option for {requirements['heads']} people.")
        if requirements.get("amenities"):
            suggestions.append("Consider fewer required amenities to increase available options.")
        if not suggestions:
            suggestions = ["Expand your location search.", "Adjust your budget.", "Try different amenities."]
        return "No properties found matching your exact requirements.\n\nSuggestions:\n" + "\n".join(f"- {s}" for s in suggestions[:3])


property_search_handler = PropertySearchHandler()
