"""Supabase-backed property search helpers used during the Django-to-Supabase migration."""
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _supabase_url() -> str:
    return (os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")


def _supabase_key() -> str:
    return os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or ""


def _post_json(url: str, payload: Dict, timeout: float = 8.0) -> Dict:
    key = _supabase_key()
    if not url or not key:
        raise RuntimeError("Supabase URL/key is not configured")
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "apikey": key,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _rest(method: str, table: str, payload: Optional[Dict] = None, query: str = "") -> Dict:
    base = _supabase_url()
    key = _supabase_key()
    if not base or not key:
        raise RuntimeError("Supabase URL/key is not configured")
    url = f"{base}/rest/v1/{table}{query}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "apikey": key,
            "Prefer": "return=representation",
        },
        method=method,
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


class SupabasePropertySearch:
    """Small compatibility layer with no Django ORM/model dependency."""

    def search(self, requirements: Dict, limit: int = 5) -> List[Dict]:
        result = _post_json(
            f"{_supabase_url()}/functions/v1/property-search",
            {"requirements": requirements, "limit": limit},
        )
        return result.get("results", []) if isinstance(result, dict) else []

    def save_search_state(self, phone_number: str, requirements: Dict, properties: List[Dict]) -> Optional[Dict]:
        if not phone_number:
            return None
        rows = _rest(
            "GET",
            "conversations",
            query=(
                "?select=id,current_step,context_data,selected_properties"
                f"&phone_number=eq.{urllib.parse.quote(phone_number, safe='')}"
                "&status=eq.active&order=updated_at.desc&limit=1"
            ),
        )
        conversation = rows[0] if isinstance(rows, list) and rows else None
        if not conversation:
            created = _rest(
                "POST",
                "conversations",
                {"phone_number": phone_number, "current_step": "property_listings", "context_data": {}, "selected_properties": []},
            )
            conversation = created[0] if isinstance(created, list) and created else None
        if not conversation:
            return None

        context = conversation.get("context_data") or {}
        context.update({
            "search_results": [item.get("property", {}) for item in properties],
            "search_matches": properties,
            "search_metadata": {"search_timestamp": datetime.now(timezone.utc).isoformat()},
            "search_requirements": requirements,
            "current_property_page": 0,
            "total_matches": len(properties),
        })
        return _rest(
            "PATCH",
            "conversations",
            {"context_data": context, "current_step": "property_listings", "last_message_at": datetime.now(timezone.utc).isoformat()},
            f"?id=eq.{conversation['id']}",
        )


supabase_property_search = SupabasePropertySearch()
