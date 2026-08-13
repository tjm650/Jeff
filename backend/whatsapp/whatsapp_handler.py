import hashlib
import hmac
import json
import logging

from django.conf import settings as dj_settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings as dj_settings

from core.models import Transaction, Token

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
        logger.warning('META_APP_SECRET not configured; skipping Meta signature verification')
        return True

    signature = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')
    if not signature:
        return False

    expected_signature = 'sha256=' + hmac.new(
        app_secret.encode('utf-8'),
        request.body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


def _extract_meta_message_data(request):
    body = request.body.decode('utf-8') if getattr(request, 'body', b'') else ''
    if not body:
        return None

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None

    for entry in payload.get('entry', []):
        for change in entry.get('changes', []):
            value = change.get('value', {})
            messages = value.get('messages', [])
            if not messages:
                continue

            message = messages[0]
            from_number = (message.get('from') or '').strip()
            text_body = ''
            if message.get('text'):
                text_body = (message.get('text', {}).get('body') or '').strip()
            elif message.get('interactive'):
                text_body = (
                    message.get('interactive', {})
                    .get('button_reply', {})
                    .get('title', '')
                    .strip()
                )

            return {
                'from_number': _normalize_phone_number(from_number),
                'to_number': _normalize_phone_number(
                    (value.get('metadata') or {}).get('display_phone_number', '')
                ),
                'message_body': text_body,
                'media_url': '',
            }

    return None


@csrf_exempt
def whatsapp_webhook(request):
    """Handle incoming WhatsApp messages from Meta Cloud API.

    Supports:
      - Meta verification challenge for GET requests
      - inbound text messages for POST requests
      - "USD PAY <number>" and "ZWG PAY <number>"
      - payment requests in USD/ZWL format
      - "status" to check latest payment status
    """
    if request.method == 'GET':
        mode = request.GET.get('hub.mode', '')
        verify_token = request.GET.get('hub.verify_token', '')
        challenge = request.GET.get('hub.challenge', '')
        expected_token = (
            dj_settings.JEFF_SETTINGS.get('META_VERIFY_TOKEN')
            or dj_settings.JEFF_SETTINGS.get('WEBHOOK_SECRET')
            or ''
        )
        if mode == 'subscribe' and verify_token and challenge and verify_token == expected_token:
            return HttpResponse(challenge, content_type='text/plain')
        return HttpResponse('Forbidden', status=403)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        if not _verify_meta_signature(request):
            return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=403)

        message_data = _extract_meta_message_data(request)
        if not message_data:
            return JsonResponse({'status': 'error', 'message': 'Empty request'}, status=400)

        if not message_data['from_number']:
            return JsonResponse({'status': 'error', 'message': 'Missing sender number'}, status=400)

        if message_data['media_url']:
            return handle_media_message(message_data)

        logger.info("[HANDLER] Processing as accommodation request")
        return handle_accommodation_request(message_data)

    except Exception as exc:
        logger.error('[ERROR] Exception in WhatsApp webhook: %s', exc, exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)


def handle_accommodation_request(message_data):
    """Route every user message into the free accommodation workflow."""
    from core.services.conversation_workflow import ConversationWorkflow
    from whatsapp.utils.whatsapp_service import whatsapp_service

    from_number = message_data['from_number']
    message_body = message_data['message_body']

    if not message_body or not message_body.strip():
        whatsapp_service.send_text_message(
            from_number,
            'Please send your accommodation requirements so I can search for you.'
        )
        return JsonResponse({'status': 'success', 'action': 'empty_message'})

    workflow = ConversationWorkflow()
    response_message = workflow.process_message(from_number, message_body)
    whatsapp_service.send_text_message(from_number, response_message)
    return JsonResponse({
        'status': 'success',
        'action': 'accommodation_request',
        'response_length': len(response_message),
        'mode': 'free',
    })


def handle_media_message(message_data):
    # We simply acknowledge and do not forward media to users
    try:
        from_number = message_data['from_number']
        media_url = message_data.get('media_url')
        logger.info('Media message received from %s, url=%s', from_number, media_url)
        return JsonResponse({'status': 'success', 'action': 'media_deleted', 'media_url': media_url})
    except Exception:
        logger.exception('Error handling media message')
        return JsonResponse({'status': 'error', 'message': 'failed to process media message'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def payment_status_webhook(request):
    """Webhook for external payment gateway (Paynow) to notify status."""
    try:
        webhook_data = json.loads(request.body)
        from payment.payment_handler import payment_handler

        result = payment_handler.handle_payment_webhook(webhook_data)
        if result.get('success'):
            reference = result.get('reference')
            if reference:
                _send_payment_confirmation_whatsapp(reference)
            return JsonResponse({'status': 'success', 'message': 'Payment processed'})
        return JsonResponse({'status': 'error', 'message': result.get('message')}, status=400)

    except Exception:
        logger.exception('Error processing payment status webhook')
        return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)


def _send_payment_confirmation_whatsapp(reference: str):
    try:
        transaction = Transaction.objects.get(transaction_number=reference)
        token = Token.objects.filter(transaction=transaction).first()
        if not token:
            logger.warning('No token found for transaction %s', reference)
            return

        from whatsapp.utils.whatsapp_service import whatsapp_service

        receipt = {
            'transaction_id': transaction.transaction_number,
            'amount_usd': float(transaction.amount) if transaction.amount is not None else None,
            'date': transaction.created_at.strftime('%Y-%m-%d %H:%M:%S') if transaction.created_at else None,
            'payment_method': transaction.payment_method,
            'token_info': {
                'token_number': token.token_number,
                'total_uses': token.total_uses,
                'used_count': token.used_count,
            }
        }

        whatsapp_service.send_payment_confirmation(transaction.cell_number, receipt)

    except Transaction.DoesNotExist:
        logger.error('Transaction not found for reference %s', reference)
    except Exception:
        logger.exception('Error sending payment confirmation via WhatsApp')
