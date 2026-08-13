import json
import time

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.diagnostics import new_correlation_id, record_event, set_context
from core.diagnostic_models import WhatsAppDiagnosticEvent
from .whatsapp_handler import _verify_meta_signature, whatsapp_webhook as meta_whatsapp_webhook


def _first_message(payload):
    for entry in payload.get('entry', []):
        for change in entry.get('changes', []):
            value = change.get('value') or {}
            messages = value.get('messages') or []
            if messages:
                return messages[0], value
    return None, None


def _first_status(payload):
    for entry in payload.get('entry', []):
        for change in entry.get('changes', []):
            value = change.get('value') or {}
            statuses = value.get('statuses') or []
            if statuses:
                return statuses[0], value
    return None, None


@csrf_exempt
def diagnostic_whatsapp_webhook(request):
    """Instrument Meta WhatsApp webhooks and acknowledge delivery-status events."""
    if request.method == 'GET':
        return meta_whatsapp_webhook(request)

    raw_body = getattr(request, 'body', b'') or b''
    correlation_id = new_correlation_id()
    phone_number = ''
    external_id = ''
    event_type = 'webhook'
    payload = {}
    try:
        payload = json.loads(raw_body.decode('utf-8')) if raw_body else {}
    except Exception:
        payload = {}

    message, _ = _first_message(payload)
    status, _ = _first_status(payload)
    if message:
        correlation_id = message.get('id') or correlation_id
        phone_number = message.get('from') or ''
        external_id = message.get('id') or ''
        event_type = 'message_received'
    elif status:
        external_id = status.get('id') or ''
        existing = WhatsAppDiagnosticEvent.objects.filter(external_id=external_id).order_by('-created_at').first() if external_id else None
        correlation_id = existing.correlation_id if existing else new_correlation_id('status')
        phone_number = status.get('recipient_id') or ''
        event_type = 'message_status'

    set_context(correlation_id, phone_number)
    started = time.monotonic()
    record_event(correlation_id=correlation_id, direction='inbound', event_type=event_type, stage='webhook_received', status='started', phone_number=phone_number, external_id=external_id, metadata={'object': payload.get('object', ''), 'field': 'messages' if message else 'statuses' if status else 'unknown'})

    if status and not _verify_meta_signature(request):
        record_event(correlation_id=correlation_id, direction='system', event_type='message_status', stage='signature_verification', status='failed', phone_number=phone_number, external_id=external_id, error_message='Invalid or missing X-Hub-Signature-256')
        return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=403)

    if message:
        record_event(correlation_id=correlation_id, direction='inbound', event_type='message_received', stage='message_extracted', status='ok', phone_number=phone_number, external_id=external_id, metadata={'message_type': message.get('type', 'unknown')})
    elif status:
        status_name = status.get('status', 'unknown')
        record_event(correlation_id=correlation_id, direction='inbound', event_type='message_status', stage='meta_delivery', status='failed' if status_name == 'failed' else 'ok', phone_number=phone_number, external_id=external_id, metadata={'status': status_name, 'errors': status.get('errors') or []})
        record_event(correlation_id=correlation_id, direction='system', event_type='message_status', stage='webhook_response', status='ok', phone_number=phone_number, external_id=external_id, duration_ms=int((time.monotonic() - started) * 1000), metadata={'http_status': 200})
        return JsonResponse({'status': 'ok', 'event': 'message_status'})

    try:
        record_event(correlation_id=correlation_id, direction='system', event_type=event_type, stage='business_processing', status='started', phone_number=phone_number, external_id=external_id)
        response = meta_whatsapp_webhook(request)
        record_event(correlation_id=correlation_id, direction='system', event_type=event_type, stage='webhook_response', status='ok' if getattr(response, 'status_code', 500) < 400 else 'failed', phone_number=phone_number, external_id=external_id, duration_ms=int((time.monotonic() - started) * 1000), metadata={'http_status': getattr(response, 'status_code', None)})
        return response
    except Exception as exc:
        record_event(correlation_id=correlation_id, direction='system', event_type=event_type, stage='webhook_exception', status='failed', phone_number=phone_number, external_id=external_id, duration_ms=int((time.monotonic() - started) * 1000), error_message=str(exc))
        return HttpResponse('Internal server error', status=500)
