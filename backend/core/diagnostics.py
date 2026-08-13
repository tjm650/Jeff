import hashlib
import time
import uuid
from contextvars import ContextVar

from .diagnostic_models import WhatsAppDiagnosticEvent

_current_correlation_id = ContextVar("whatsapp_correlation_id", default="")
_current_phone_number = ContextVar("whatsapp_phone_number", default="")


def new_correlation_id(prefix="wa"):
    return f"{prefix}-{uuid.uuid4().hex[:20]}"


def set_context(correlation_id, phone_number=""):
    _current_correlation_id.set(correlation_id or "")
    _current_phone_number.set(phone_number or "")


def get_context():
    return _current_correlation_id.get(), _current_phone_number.get()


def _phone_last4(phone_number):
    digits = "".join(ch for ch in str(phone_number or "") if ch.isdigit())
    return digits[-4:] if digits else ""


def record_event(*, correlation_id=None, direction, event_type, stage, status="ok",
                 phone_number="", external_id="", duration_ms=None,
                 error_message="", metadata=None):
    """Persist one diagnostic event without allowing diagnostics to break WhatsApp."""
    context_id, context_phone = get_context()
    correlation_id = correlation_id or context_id or new_correlation_id("system")
    phone_number = phone_number or context_phone
    try:
        return WhatsAppDiagnosticEvent.objects.create(
            event_id=uuid.uuid4().hex,
            correlation_id=correlation_id,
            direction=direction,
            event_type=event_type,
            stage=stage,
            status=status,
            phone_last4=_phone_last4(phone_number),
            external_id=str(external_id or "")[:200],
            duration_ms=duration_ms,
            error_message=str(error_message or "")[:4000],
            metadata=metadata or {},
        )
    except Exception:
        return None


def timed_event(**kwargs):
    started = time.monotonic()

    class _Timer:
        def finish(self, status="ok", error_message="", **extra):
            return record_event(
                **kwargs,
                status=status,
                duration_ms=int((time.monotonic() - started) * 1000),
                error_message=error_message,
                **extra,
            )

    return _Timer()


def stable_payload_id(raw_body):
    return "payload-" + hashlib.sha256(raw_body or b"").hexdigest()[:24]
