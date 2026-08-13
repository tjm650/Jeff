import os
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .authentication import APIKeyAuthentication
from .diagnostic_models import WhatsAppDiagnosticEvent


def _authorized(request):
    try:
        result = APIKeyAuthentication().authenticate(request)
        return bool(result)
    except Exception:
        return False


def _serialize(event):
    return {
        "time": event.created_at.isoformat(), "event_id": event.event_id,
        "correlation_id": event.correlation_id, "direction": event.direction,
        "event_type": event.event_type, "stage": event.stage, "status": event.status,
        "phone_last4": event.phone_last4, "external_id": event.external_id,
        "duration_ms": event.duration_ms, "error": event.error_message,
        "metadata": event.metadata,
    }


def _snapshot(request):
    since = timezone.now() - timedelta(hours=24)
    qs = WhatsAppDiagnosticEvent.objects.filter(created_at__gte=since)
    correlation_id = request.GET.get("correlation_id", "").strip()
    phone_last4 = request.GET.get("phone_last4", "").strip()
    if correlation_id:
        qs = qs.filter(correlation_id=correlation_id)
    if phone_last4:
        qs = qs.filter(phone_last4=phone_last4[-4:])

    events = list(qs.order_by("-created_at")[:200])
    grouped = {}
    for event in reversed(events):
        grouped.setdefault(event.correlation_id, []).append(event)

    now = timezone.now()
    flows = []
    for correlation, flow_events in grouped.items():
        latest = flow_events[-1]
        failed = next((e for e in reversed(flow_events) if e.status == "failed"), None)
        age_seconds = (now - latest.created_at).total_seconds()
        if failed:
            health, stuck_at = "failed", failed.stage
        elif latest.status == "started" and age_seconds >= 10:
            health, stuck_at = "stuck", latest.stage
        else:
            health, stuck_at = "ok", None
        flows.append({
            "correlation_id": correlation, "health": health, "stuck_at": stuck_at,
            "age_seconds": round(age_seconds, 1), "last_event": _serialize(latest),
            "events": [_serialize(e) for e in flow_events],
        })

    return {
        "status": "ok", "generated_at": now.isoformat(), "window": "24h",
        "filters": {"correlation_id": correlation_id, "phone_last4": phone_last4[-4:] if phone_last4 else ""},
        "flows": list(reversed(flows)),
        "configuration": {
            "meta_verify_token": bool(getattr(settings, "JEFF_SETTINGS", {}).get("META_VERIFY_TOKEN")),
            "meta_app_secret": bool(getattr(settings, "JEFF_SETTINGS", {}).get("META_APP_SECRET")),
            "meta_access_token": bool(os.getenv("META_ACCESS_TOKEN") or os.getenv("WHATSAPP_ACCESS_TOKEN")),
            "meta_phone_number_id": bool(os.getenv("META_PHONE_NUMBER_ID") or os.getenv("WHATSAPP_PHONE_NUMBER_ID")),
        },
    }


@require_GET
def whatsapp_diagnostics(request):
    if not _authorized(request):
        return JsonResponse({"status": "error", "message": "Diagnostic endpoint requires a valid API key."}, status=401)
    data = _snapshot(request)
    if request.GET.get("format") == "json":
        return JsonResponse(data)

    rows = []
    for flow in data["flows"]:
        badge = {"ok": "OK", "failed": "FAILED", "stuck": "STUCK"}[flow["health"]]
        rows.append(
            f"<tr><td><code>{flow['correlation_id']}</code></td><td>{badge}</td>"
            f"<td>{flow['stuck_at'] or flow['last_event']['stage']}</td>"
            f"<td>{flow['last_event']['event_type']}</td><td>{flow['last_event']['status']}</td>"
            f"<td>{flow['last_event']['time']}</td></tr>"
        )
    html = f"""<!doctype html><html><head><meta charset='utf-8'><meta http-equiv='refresh' content='10'>
<title>Jeff WhatsApp Diagnostics</title><style>
body{{font:14px system-ui;margin:32px;background:#0b1020;color:#e8edf7}}table{{width:100%;border-collapse:collapse}}
th,td{{padding:10px;border-bottom:1px solid #29324a;text-align:left}}code{{color:#a9d5ff}}
.hint{{padding:14px;background:#151d31;border-radius:8px;margin-bottom:20px}}</style></head><body>
<h1>Jeff · WhatsApp Diagnostics</h1><div class='hint'>Auto-refreshes every 10 seconds · last 24 hours · add <code>?format=json</code> for JSON.</div>
<table><thead><tr><th>Correlation</th><th>Health</th><th>Stage</th><th>Event</th><th>Status</th><th>Time</th></tr></thead>
<tbody>{''.join(rows) or '<tr><td colspan="6">No WhatsApp diagnostic events recorded yet.</td></tr>'}</tbody></table>
<h2>Configuration</h2><pre>{data['configuration']}</pre></body></html>"""
    return HttpResponse(html)
