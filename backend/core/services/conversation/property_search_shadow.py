"""Shadow comparison between Django and Supabase property matching.

This module is intentionally fail-open: it never changes the WhatsApp response and
never raises into the production property-search flow.
"""

import hashlib
import json
import logging
import os
import threading
import urllib.error
import urllib.request
from typing import Dict, Iterable, List

logger = logging.getLogger(__name__)


def _ids_from_django(conversation) -> List[str]:
    try:
        results = conversation.context_data.get("search_results", []) or []
        return [str(item.get("id")) for item in results if isinstance(item, dict) and item.get("id")]
    except Exception:
        return []


def _ids_from_supabase(payload: Dict) -> List[str]:
    results = payload.get("results", []) if isinstance(payload, dict) else []
    ids: List[str] = []
    for item in results or []:
        if not isinstance(item, dict):
            continue
        prop = item.get("property")
        if isinstance(prop, dict) and prop.get("id") is not None:
            ids.append(str(prop["id"]))
        elif item.get("id") is not None:
            ids.append(str(item["id"]))
    return ids


def _compare(django_ids: Iterable[str], supabase_ids: Iterable[str]) -> Dict:
    django = list(django_ids)
    supabase = list(supabase_ids)
    dset, sset = set(django), set(supabase)
    overlap = len(dset & sset)
    union = len(dset | sset)
    return {
        "django_count": len(django),
        "supabase_count": len(supabase),
        "overlap_count": overlap,
        "overlap_ratio": round(overlap / max(len(dset), 1), 3),
        "exact_order_match": django == supabase,
        "django_only": sorted(dset - sset),
        "supabase_only": sorted(sset - dset),
        "django_ids": django,
        "supabase_ids": supabase,
        "union_count": union,
    }


def _call_supabase(requirements: Dict) -> Dict:
    base_url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not base_url or not key:
        raise RuntimeError("Supabase shadow comparison is not configured")

    url = f"{base_url}/functions/v1/property-search"
    body = json.dumps({"requirements": requirements}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "apikey": key,
        },
    )
    with urllib.request.urlopen(request, timeout=4) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _run_shadow(conversation, requirements: Dict) -> None:
    try:
        validated = requirements.get("validated_requirements", requirements)
        django_ids = _ids_from_django(conversation)
        payload = _call_supabase(validated)
        supabase_ids = _ids_from_supabase(payload)
        comparison = _compare(django_ids, supabase_ids)
        phone_hash = hashlib.sha256(str(getattr(conversation, "cell_number", "")).encode()).hexdigest()[:12]
        logger.info(
            "PROPERTY_SHADOW_COMPARISON phone_hash=%s comparison=%s",
            phone_hash,
            json.dumps(comparison, separators=(",", ":")),
        )
    except Exception as exc:
        logger.warning("PROPERTY_SHADOW_COMPARISON_FAILED error=%s", exc)


def install_property_search_shadow(property_search_handler) -> None:
    """Wrap the existing handler while preserving its exact user-facing behavior."""
    original = property_search_handler.proceed_to_property_search
    if getattr(original, "_jeff_shadow_wrapped", False):
        return

    def wrapped(conversation, requirements):
        result = original(conversation, requirements)
        try:
            thread = threading.Thread(
                target=_run_shadow,
                args=(conversation, requirements),
                name="property-search-shadow",
                daemon=True,
            )
            thread.start()
        except Exception as exc:
            logger.warning("PROPERTY_SHADOW_THREAD_FAILED error=%s", exc)
        return result

    wrapped._jeff_shadow_wrapped = True
    property_search_handler.proceed_to_property_search = wrapped
