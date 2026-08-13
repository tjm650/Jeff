import hashlib
import time
import uuid

from .diagnostic_models import WhatsAppDiagnosticEvent


def new_correlation_id(prefix="wa"):
    return f"{prefix}-{uuid.uuid4().hex[:20]}"


def _phone_last4(phone_number):
    digits = "".join(ch for ch in str(phone_number or "") if ch.isdigit())
    return digits[-4:] if digits else ""


def record_event(*, correlation_id, direction, event_type, stage, status="ok",
                 phone_number="", external_id="", duration_ms=None,
                 error_message="", metadata=None):
    """Persist one diagnostic event without allowing diagnostics to break WhatsApp."""
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
    """Return a context manager-like helper for recording a stage duration."""
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
    """Create a safe correlation fallback when Meta does not provide a message id."""
    return "payload-" + hashlib.sha256(raw_body or b"").hexdigest()[:24]
