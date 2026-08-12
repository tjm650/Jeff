import hashlib
import hmac
import json
import logging
import re
import threading
import time

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings as dj_settings

from core.models import Transaction, Token

logger = logging.getLogger(__name__)


def _normalize_phone_number(phone_number: str) -> str:
    """Normalize WhatsApp sender numbers to Jeff's E.164-style format."""
    value = (phone_number or '').strip().replace('whatsapp:', '')
    if value and not value.startswith('+'):
        value = f'+{value}'
    return value


def _verify_meta_signature(request) -> bool:
    """Verify Meta webhook signatures for inbound updates."""
    app_secret = dj_settings.JEFF_SETTINGS.get("META_APP_SECRET") or dj_settings.JEFF_SETTINGS.get("WEBHOOK_SECRET") or ""
    if not app_secret:
        logger.warning("META_APP_SECRET not configured; skipping Meta signature verification")
        return True

    signature = request.META.get("HTTP_X_HUB_SIGNATURE_256", "")
    if not signature:
        logger.warning("Missing X-Hub-Signature-256 header on WhatsApp webhook")
        return False

    expected_signature = "sha256=" + hmac.new(
        app_secret.encode('utf-8'),
        request.body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


def _extract_meta_message_data(request):
    """Extract inbound WhatsApp message data from a Meta webhook payload."""
    body = request.body.decode('utf-8') if getattr(request, 'body', b'') else ''
    if not body:
        logger.warning("[EXTRACT] Empty request body")
        return None

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        logger.warning(f'[EXTRACT] Invalid Meta webhook JSON payload: {str(e)}')
        return None

    logger.info(f"[EXTRACT] Payload object type: {payload.get('object', 'unknown')}")

    for entry in payload.get('entry', []):
        logger.info(f"[EXTRACT] Processing entry: {entry.get('id', 'unknown')}")
        for change in entry.get('changes', []):
            value = change.get('value', {})
            messages = value.get('messages', [])
            if not messages:
                logger.info(f"[EXTRACT] No messages in change field: {change.get('field', 'unknown')}")
                continue

            logger.info(f"[EXTRACT] Found {len(messages)} message(s)")
            message = messages[0]
            from_number = (message.get('from') or '').strip()
            text_body = ''

            if message.get('text'):
                text_body = (message.get('text', {}).get('body') or '').strip()
                logger.info(f"[EXTRACT] Text message extracted: '{text_body}'")
            elif message.get('interactive'):
                text_body = (message.get('interactive', {}).get('button_reply', {}).get('title') or '').strip()
                logger.info(f"[EXTRACT] Interactive message extracted: '{text_body}'")
            else:
                logger.info(f"[EXTRACT] Message type: {message.get('type', 'unknown')}")

            result = {
                'from_number': _normalize_phone_number(from_number),
                'to_number': _normalize_phone_number((value.get('metadata') or {}).get('display_phone_number', '')),
                'message_body': text_body,
                'media_url': '',
            }

            logger.info(f"[EXTRACT] Result: from={result['from_number']}, body='{result['message_body']}'")
            return result

    logger.warning("[EXTRACT] No message data found in payload")
    return None


@csrf_exempt
def whatsapp_webhook(request):
    """Handle incoming WhatsApp messages from Meta Cloud API."""
    if request.method == 'GET':
        mode = request.GET.get('hub.mode', '')
        verify_token = request.GET.get('hub.verify_token', '')
        challenge = request.GET.get('hub.challenge', '')
        expected_token = dj_settings.JEFF_SETTINGS.get('META_VERIFY_TOKEN') or dj_settings.JEFF_SETTINGS.get('WEBHOOK_SECRET') or ''
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

        from_number = message_data['from_number']
        to_number = message_data['to_number']
        message_body = message_data['message_body']
        media_url = message_data['media_url']

        if not from_number:
            return JsonResponse({'status': 'error', 'message': 'Missing sender number'}, status=400)

        message_data = {
            'from_number': from_number,
            'to_number': to_number,
            'message_body': message_body,
            'media_url': media_url,
        }

        if media_url:
            return handle_media_message(message_data)

        body = message_body.strip()
        if body.lower() == 'status':
            return handle_status_request(message_data)
        if re.search(r'(USD|ZWL)\s+PAY\s+[0-9]+', body, re.IGNORECASE):
            return handle_payment_request(message_data)
        match = re.match(r'^(usd|zwg)\s+pay\s+([0-9\+]+)$', body, re.IGNORECASE)
        if match:
            return handle_currency_payment_request(message_data, match.group(1).upper(), match.group(2))
        return handle_accommodation_request(message_data)

    except Exception as e:
        logger.error(f"[ERROR] Exception in webhook: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)


def handle_payment_request(message_data):
    """Legacy payment flow (no explicit payment number)."""
    try:
        from payment.payment_handler import payment_handler
        from whatsapp.utils.whatsapp_service import whatsapp_service
        from_number = message_data['from_number']
        existing_token = payment_handler._get_valid_token(from_number)
        if existing_token:
            msg = (
                f"You already have an active token\n\n"
                f"Token: {existing_token.token_number[:6]}...\n"
                f"Expires: {existing_token.expires_at.strftime('%Y-%m-%d')}\n"
                f"Remaining Uses: {existing_token.total_uses - existing_token.used_count}"
            )
            whatsapp_service.send_text_message(from_number, msg)
            return JsonResponse({'status': 'success', 'action': 'existing_token'})
        payment_result = payment_handler.initiate_payment(from_number)
        if payment_result.get('success'):
            return JsonResponse({'status': 'success', 'action': 'payment_initiated', 'reference': payment_result.get('reference')})
        whatsapp_service.send_error_message(from_number, payment_result.get('message', 'Failed to initiate payment'))
        return JsonResponse({'status': 'error', 'message': payment_result.get('message')}, status=400)
    except Exception:
        logger.exception('Error handling payment request')
        return JsonResponse({'status': 'error', 'message': 'failed to process payment request'}, status=500)


def handle_status_request(message_data):
    """Handle 'status' request - check latest payment status for the user."""
    try:
        from payment.handlers.gateway import gateway_handler
        from whatsapp.utils.whatsapp_service import whatsapp_service
        from_number = message_data['from_number']
        latest_tx = Transaction.objects.filter(cell_number=from_number).order_by('-created_at').first()
        if not latest_tx:
            whatsapp_service.send_text_message(from_number, 'No recent payment found. Send USD PAY <number> or ZWG PAY <number> to start a payment.')
            return JsonResponse({'status': 'success', 'message': 'no_payment'})
        status = gateway_handler.check_payment_status(latest_tx.transaction_number)
        whatsapp_service.send_text_message(from_number, f"Payment status: {status.get('status', 'unknown')}")
        return JsonResponse({'status': 'success', 'payment_status': status.get('status')})
    except Exception:
        logger.exception('Error handling status request')
        return JsonResponse({'status': 'error', 'message': 'failed to check status'}, status=500)


def handle_currency_payment_request(message_data, currency: str, payment_number: str):
    """Handle new payment trigger format and start a short background poller for confirmation."""
    try:
        from payment.payment_handler import payment_handler
        from whatsapp.utils.whatsapp_service import whatsapp_service
        from_number = message_data['from_number']
        result = payment_handler.initiate_payment(student_phone=from_number, payment_number=payment_number)
        if not result.get('success'):
            whatsapp_service.send_error_message(from_number, result.get('message', 'Payment initiation failed'))
            return JsonResponse({'status': 'error', 'message': result.get('message')}, status=400)
        reference = result.get('reference')
        timeout_seconds = int(dj_settings.JEFF_SETTINGS.get('PAYMENT_TIMEOUT_SECONDS', 30))

        def _poll_status_and_notify(cell_number, reference, timeout_s):
            from payment.handlers.gateway import gateway_handler as gh
            from whatsapp.utils.whatsapp_service import whatsapp_service as ws
            start = time.time()
            while time.time() - start < timeout_s:
                try:
                    status_resp = gh.check_payment_status(reference)
                    if status_resp.get('success') and status_resp.get('status') == 'paid':
                        receipt = {'transaction_id': reference, 'amount_usd': status_resp.get('amount') or None, 'amount_zwg': None, 'date': None, 'payment_method': 'paynow'}
                        ws.send_payment_confirmation(cell_number, receipt)
                        return
                except Exception:
                    logger.debug('Polling error, will retry')
                time.sleep(5)
            ws.send_text_message(cell_number, f"Payment timed out after {timeout_s} seconds. Please try again or send 'status' to check payment status.")

        threading.Thread(target=_poll_status_and_notify, args=(from_number, reference, timeout_seconds), daemon=True).start()
        return JsonResponse({'status': 'success', 'action': 'payment_initiated', 'reference': reference})
    except Exception:
        logger.exception('Error handling currency payment request')
        return JsonResponse({'status': 'error', 'message': 'failed to process payment request'}, status=500)


def handle_accommodation_request(message_data):
    try:
        from core.services.conversation_workflow import ConversationWorkflow
        from whatsapp.utils.whatsapp_service import whatsapp_service
        from_number = message_data['from_number']
        message_body = message_data['message_body']
        if not message_body or not message_body.strip():
            whatsapp_service.send_text_message(from_number, "Please send a valid message.")
            return JsonResponse({'status': 'success', 'action': 'accommodation_request', 'response_length': 0})
        workflow = ConversationWorkflow()
        response_message = workflow.process_message(from_number, message_body)
        whatsapp_service.send_text_message(from_number, response_message)
        return JsonResponse({'status': 'success', 'action': 'accommodation_request', 'response_length': len(response_message)})
    except ImportError as e:
        return JsonResponse({'status': 'error', 'message': f'Service import failed: {str(e)}'}, status=500)
    except AttributeError as e:
        return JsonResponse({'status': 'error', 'message': f'Service error: {str(e)}'}, status=500)


def handle_media_message(message_data):
    return JsonResponse({'status': 'success', 'action': 'media_received'})
