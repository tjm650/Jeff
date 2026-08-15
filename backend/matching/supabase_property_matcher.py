"""Supabase-backed property matcher used by the WhatsApp conversation flow."""

from __future__ import annotations

import json
import logging
import os
from types import SimpleNamespace
from typing import Any, Dict, List
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)


def _namespace(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _namespace(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_namespace(v) for v in value]
    return value


class SupabasePropertyMatcher:
    """Calls the authoritative Supabase property-search Edge Function."""

    def match_properties(self, requirements: Dict, limit: int = 5) -> List[Dict]:
        base_url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not base_url or not service_key:
            logger.error("Supabase property matcher is not configured")
            return []

        endpoint = f"{base_url}/functions/v1/property-search"
        payload = json.dumps({"requirements": requirements, "limit": limit}).encode("utf-8")
        request = Request(
            endpoint,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
            },
        )

        try:
            with urlopen(request, timeout=8) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            logger.error("Supabase property-search request failed: %s", exc)
            return []

        if not body.get("success"):
            logger.error("Supabase property-search returned failure: %s", body.get("message"))
            return []

        matches: List[Dict] = []
        for item in body.get("results", []):
            property_data = item.get("property")
            if not isinstance(property_data, dict) or not property_data.get("id"):
                continue

            property_obj = _namespace(property_data)
            provider = getattr(property_obj, "providers", None)
            if provider is not None and not hasattr(property_obj, "provider"):
                property_obj.provider = provider
            if not hasattr(property_obj, "rating"):
                property_obj.rating = getattr(provider, "rating", 0.0) if provider else 0.0

            matches.append({
                "property": property_obj,
                "score": item.get("score", 0),
                "match_reasons": item.get("match_reasons", []),
            })

        return matches


property_matcher = SupabasePropertyMatcher()
