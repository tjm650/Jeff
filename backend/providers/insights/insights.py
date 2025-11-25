"""Insights handler for provider-submitted periodic insights.

This module exposes a small helper that accepts partial insights payloads
from a provider and updates the matching Property instance owned by that
provider. Only properties that belong to the submitting provider can be
updated.

The submit_insights function is tolerant of partial payloads: providers
may send only some fields and only those will be updated.
"""
from decimal import Decimal, InvalidOperation
from typing import Dict, Any
from django.core.exceptions import ObjectDoesNotExist
from core.models import Property, AccommodationProvider


class InsightsHandler:
    @staticmethod
    def submit_insights(*, provider_phone: str = None, provider_id: str = None, property_no: str, insights: Dict[str, Any]):
        """Accepts insights from a provider and updates the matching Property.

        Parameters
        - provider_phone: phone number of provider (preferred)
        - provider_id: uuid of provider (optional alternative)
        - property_no: the property number (e.g. AB-1234) to update
        - insights: dictionary with any of the keys:
            gender_preference, total_rooms, available_rooms,
            available_slots (dict: '1h/room', '2h/room', '3h/room', '4h/room'),
            amenities (list or comma-separated string),
            pricing (dict: 'price/term', 'price/month', 'price/week', 'price/day')

        Returns dict with keys: success (bool), message (str), updated_fields (list)
        """
        # Resolve provider
        provider = None
        try:
            if provider_phone:
                provider = AccommodationProvider.objects.get(phone_number=provider_phone)
            elif provider_id:
                provider = AccommodationProvider.objects.get(id=provider_id)
            else:
                return {"success": False, "message": "provider_phone or provider_id is required", "updated_fields": []}
        except ObjectDoesNotExist:
            return {"success": False, "message": "Provider not found", "updated_fields": []}

        # Find property owned by provider using property_no
        # Normalize property_no to ensure hyphen format (AB-1234)
        normalized_prop_no = property_no.upper()
        if len(normalized_prop_no) == 6 and '-' not in normalized_prop_no:
            # Convert AB1234 to AB-1234 format
            normalized_prop_no = f"{normalized_prop_no[:2]}-{normalized_prop_no[2:]}"
        prop = Property.objects.filter(provider=provider, property_no=normalized_prop_no).first()
        if not prop:
            return {"success": False, "message": f"Property {normalized_prop_no} not found. Contact Support team for assistance", "updated_fields": []}

        updated = []

        # Basic scalar fields
        if "gender_preference" in insights:
            gp = insights.get("gender_preference")
            if gp:
                prop.gender_preference = gp
                updated.append("gender_preference")

        if "total_rooms" in insights:
            try:
                val = int(insights.get("total_rooms") or 0)
                prop.total_rooms = val
                updated.append("total_rooms")
            except (TypeError, ValueError):
                pass

        if "available_rooms" in insights:
            try:
                val = int(insights.get("available_rooms") or 0)
                prop.available_rooms = val
                updated.append("available_rooms")
            except (TypeError, ValueError):
                pass

        # Available slots mapping
        slots = insights.get("available_slots") or {}
        if isinstance(slots, dict):
            mapping = {
                "1h/room": "available_1h_rooms",
                "2h/room": "available_2h_rooms",
                "3h/room": "available_3h_rooms",
                "4h/room": "available_4h_rooms",
            }
            for k, v in slots.items():
                field = mapping.get(k)
                if field and v is not None:
                    try:
                        setattr(prop, field, int(v))
                        updated.append(field)
                    except (TypeError, ValueError):
                        # skip invalid values
                        continue

        # Amenities: accept list or comma-separated string
        if "amenities" in insights:
            am = insights.get("amenities")
            if isinstance(am, str):
                items = [a.strip() for a in am.split(",") if a.strip()]
            elif isinstance(am, (list, tuple)):
                items = [str(a).strip() for a in am if str(a).strip()]
            else:
                items = []

            if items:
                # merge unique while preserving existing
                existing = list(prop.amenities or [])
                for it in items:
                    if it not in existing:
                        existing.append(it)
                prop.amenities = existing
                updated.append("amenities")

        # Pricing mapping
        pricing = insights.get("pricing") or {}
        if isinstance(pricing, dict):
            price_map = {
                "price/term": "price_per_semester",
                "price/month": "price_per_month",
                "price/week": "price_per_week",
                "price/day": "price_per_day",
            }
            for k, v in pricing.items():
                field = price_map.get(k)
                if field and v is not None:
                    try:
                        prop_val = Decimal(str(v))
                        setattr(prop, field, prop_val)
                        updated.append(field)
                    except (InvalidOperation, TypeError, ValueError):
                        continue

        # Save if anything changed
        if updated:
            prop.save()
            return {"success": True, "message": "Property updated", "updated_fields": list(dict.fromkeys(updated))}

        return {"success": False, "message": "No valid fields to update", "updated_fields": []}


__all__ = ["InsightsHandler"]
