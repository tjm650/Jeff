"""
AI Data Access Security for MCP/AI Components

This module centralizes enforcement that AI-driven code paths may only
access a whitelisted set of Django models. By default, only the
`core.Property` model (accommodation listings) is allowed.
"""

import logging
from typing import Iterable, Any

from django.conf import settings

logger = logging.getLogger(__name__)


def _get_ai_allowed_models() -> set[str]:
    """
    Return the set of fully-qualified model labels that AI code
    is allowed to access, e.g. {'core.Property'}.
    """
    default = {'core.Property'}
    try:
        configured = getattr(settings, 'AI_ALLOWED_MODELS', None)
        if not configured:
            return default
        return set(str(m).strip() for m in configured if str(m).strip())
    except Exception:
        # Fail closed to the default whitelist if settings are misconfigured
        logger.warning("Failed to read AI_ALLOWED_MODELS from settings, using default", exc_info=True)
        return default


def _model_label(obj: Any) -> str | None:
    """Return the Django app_label.ModelName label for a model instance or class."""
    try:
        meta = getattr(obj, "_meta", None)
        if not meta:
            return None
        return f"{meta.app_label}.{meta.object_name}"
    except Exception:
        return None


def validate_ai_data_access(objects: Iterable[Any], context: str = "") -> None:
    """
    Validate that the iterable of Django model instances belongs only to
    AI-allowed models. Raise PermissionError if a disallowed model is seen.

    This should be called in any code path that prepares ORM-backed data
    to be sent to external AI APIs.
    """
    allowed = _get_ai_allowed_models()
    disallowed: set[str] = set()

    for obj in objects:
        label = _model_label(obj)
        if label is None:
            # Non-model objects are ignored
            continue
        if label not in allowed:
            disallowed.add(label)

    if disallowed:
        message = (
            f"AI data access violation in {context or 'AI component'}: "
            f"attempted to expose models {sorted(disallowed)}; "
            f"allowed models are {sorted(allowed)}"
        )
        logger.error(message)
        raise PermissionError(message)


