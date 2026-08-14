import hashlib
import hmac
import json
import logging

from django.conf import settings as dj_settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


def _normalize_phone_number(phone_number: str) -> str:
    value = (phone_number or '').strip().replace('whatsapp:', '')
    if value and not value.startswith('+'):
        value = f'+{value}'
    return value


def _verify_meta_signature(request) -> bool:
    app_secret = (
        dj_settings.JEFF_SETTINGS.get('META_APP_SECRET')
        or dj_settings.JEFF_SETTINGS.get('WEBHOOK_SECRET')
        or ''
    )
    if not app_secret:
        logger.error('META_APP_SECRET/META_WEBHOOK_SECRET is not configured')
        return False

    signature = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')
    if not signature:
        logger.warning('Missing X-Hub-Signature-256 header')
        return False

    expected_signature = 'sha256=' + hmac.new(
        app_secret.encode('utf-8'),
        request.body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


def _parse_meta_payload(request):
    body = request.body.decode('utf-8') if getattr(request, 'body', b'') else ''
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        logger.warning('WhatsApp webhook contained invalid JSON')
        return None


def _extract_events(payload):
    """Return all message and status events from a Meta webhook payload."""
    events = []
    if not payload:
        return events

    for entry in payload.get('entry', []):
        for change in entry.get('changes', []):
            value = change.get('value') or {}
            metadata = value.get('metadata') or {}

            for status in value.get('statuses', []) or []:
                events.append({
                    'type': 'status',
                    'status': status.get('status'),
                    'message_id': status.get('id'),
                    'recipient_id': status.get('recipient_id'),
                    'timestamp': status.get('timestamp'),
                    'errors': status.get('errors') or [],
                    'phone_number_id': metadata.get('phone_number_id'),
                    'display_phone_number': metadata.get('display_phone_number'),
                })

            for message in value.get('messages', []) or []:
                text_body = ''
                if message.get('text'):
                    text_body = (message.get('text', {}).get('body') or '').strip()
                elif message.get('interactive'):
                    interactive = message.get('interactive') or {}
                    button_reply = interactive.get('button_reply') or {}
                    list_reply = interactive.get('list_reply') or {}
                    text_body = (button_reply.get('title') or list_reply.get('title') or '').strip()

                events.append({
                    'type': 'message',
                    'message_id': message.get('id'),
                    'from_number': _normalize_phone_number(message.get('from', '')),
                    'to_number': _normalize_phone_number(metadata.get('display_phone_number', '')),
                    'message_body': text_body,
                    'message_type': message.get('type', ''),
                    'media_url': '',
                })

    return events


def _send_text_response(to_number: str, message: str) -> bool:
    from whatsapp.utils.whatsapp_service import whatsapp_service
    return whatsapp_service.send_text_message(to_number, message)


@csrf_exempt
def whatsapp_webhook(request):
    """Handle Meta WhatsApp verification, inbound messages, and status callbacks."""
    if request.method == 'GET':
        mode = request.GET.get('hub.mode', '')
        verify_token = request.GET.get('hub.verify_token', '')
        challenge = request.GET.get('hub.challenge', '')
        expected_token = dj_settings.JEFF_SETTINGS.get('META_VERIFY_TOKEN') or ''

        if mode == 'subscribe' and challenge and verify_token == expected_token:
            logger.info('WhatsApp webhook verification succeeded')
            return HttpResponse(challenge, content_type='text/plain')

        logger.warning('WhatsApp webhook verification failed')
        return HttpResponse('Forbidden', status=403)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        if not _verify_meta_signature(request):
            return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=403)

        payload = _parse_meta_payload(request)
        events = _extract_events(payload)

        # Meta sends status-only callbacks for outbound messages. These are valid
        # webhooks and must be acknowledged with 200, not treated as empty messages.
        if not events:
            logger.info('WhatsApp webhook acknowledged: no message/status events')
            return JsonResponse({'status': 'ok', 'action': 'acknowledged'})

        processed = []
        for event in events:
            if event['type'] == 'status':
                logger.info(
                    'WhatsApp outbound status: id=%s status=%s recipient=%s errors=%s',
                    event['message_id'], event['status'], event['recipient_id'], event['errors'],
                )
                processed.append({
                    'type': 'status',
                    'message_id': event['message_id'],
                    'status': event['status'],
                })
                continue

            from_number = event['from_number']
            message_body = event['message_body']
            logger.info(
                'WhatsApp inbound message: id=%s from=%s type=%s',
                event['message_id'], from_number, event['message_type'],
            )

            if not from_number:
                logger.warning('WhatsApp message missing sender number')
                continue

            if event['media_url']:
                processed.append({'type': 'media', 'message_id': event['message_id']})
                continue

            if not message_body:
                sent = _send_text_response(
                    from_number,
                    'Please send your accommodation requirements so I can search for you.',
                )
                processed.append({
                    'type': 'message',
                    'message_id': event['message_id'],
                    'response_sent': sent,
                })
                continue

            from core.services.conversation_workflow import ConversationWorkflow
            workflow = ConversationWorkflow()
            response_message = workflow.process_message(from_number, message_body)
            sent = _send_text_response(from_number, response_message)
            logger.info(
                'WhatsApp response: inbound_id=%s sent=%s response_length=%s',
                event['message_id'], sent, len(response_message or ''),
            )
            processed.append({
                'type': 'message',
                'message_id': event['message_id'],
                'response_sent': sent,
            })

        # Always acknowledge successfully after valid Meta payload handling.
        return JsonResponse({'status': 'ok', 'processed': processed})

    except Exception as exc:
        logger.error('[ERROR] Exception in WhatsApp webhook: %s', exc, exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)


def handle_accommodation_request(message_data):
    """Backward-compatible helper for callers that use the old interface."""
    from core.services.conversation_workflow import ConversationWorkflow

    from_number = message_data['from_number']
    message_body = message_data['message_body']
    response_message = ConversationWorkflow().process_message(from_number, message_body)
    sent = _send_text_response(from_number, response_message)
    return JsonResponse({'status': 'success', 'action': 'accommodation_request', 'response_sent': sent})


def handle_media_message(message_data):
    return JsonResponse({'status': 'success', 'action': 'media_received'})
