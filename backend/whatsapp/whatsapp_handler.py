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

logger = logging.getLogger(__name__)


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
                'from_number': from_number.replace('whatsapp:', ''),
                'to_number': (value.get('metadata') or {}).get('display_phone_number', '').replace('whatsapp:', ''),
                'message_body': text_body,
                'media_url': '',
            }
            
            logger.info(f"[EXTRACT] Result: from={result['from_number']}, body='{result['message_body']}'")
            return result

    logger.warning("[EXTRACT] No message data found in payload")
    return None


@csrf_exempt
def whatsapp_webhook(request):
    """Handle incoming WhatsApp messages from Meta Cloud API.

    Supports:
      - Meta verification challenge for GET requests
      - inbound text messages for POST requests
    """
    if request.method == 'GET':
        logger.info("=" * 60)
        logger.info('[VERIFY] WhatsApp Webhook Verification Request')
        logger.info("=" * 60)
        mode = request.GET.get('hub.mode', '')
        verify_token = request.GET.get('hub.verify_token', '')
        challenge = request.GET.get('hub.challenge', '')
        expected_token = dj_settings.JEFF_SETTINGS.get('META_VERIFY_TOKEN') or dj_settings.JEFF_SETTINGS.get('WEBHOOK_SECRET') or ''

        logger.info(f"Mode: {mode}")
        logger.info(f"Token verification: {'[PASS]' if verify_token == expected_token else '[FAIL]'}")
        logger.info(f"Challenge received: {challenge[:20]}..." if challenge else "No challenge")

        if mode == 'subscribe' and verify_token and challenge and verify_token == expected_token:
            logger.info('[OK] WhatsApp webhook successfully connected and verified')
            logger.info("=" * 60 + "\n")
            return HttpResponse(challenge, content_type='text/plain')
        logger.warning('[ERROR] Webhook verification failed - Invalid credentials')
        logger.info("=" * 60 + "\n")
        return HttpResponse('Forbidden', status=403)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        logger.info("[POST] WhatsApp webhook POST request received")
        
        if not _verify_meta_signature(request):
            logger.error("[ERROR] Signature verification failed")
            return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=403)

        logger.info("[OK] Signature verified successfully")

        message_data = _extract_meta_message_data(request)
        if not message_data:
            logger.warning("[WARN] No message data extracted from payload")
            return JsonResponse({'status': 'error', 'message': 'Empty request'}, status=400)

        from_number = message_data['from_number']
        to_number = message_data['to_number']
        message_body = message_data['message_body']
        media_url = message_data['media_url']

        logger.info(f"[RECEIVED] Message from {from_number} to {to_number}")
        logger.info(f"[CONTENT] Message body: '{message_body}'")

        if not from_number:
            logger.error("[ERROR] Missing sender number")
            return JsonResponse({'status': 'error', 'message': 'Missing sender number'}, status=400)

        message_data = {
            'from_number': from_number,
            'to_number': to_number,
            'message_body': message_body,
            'media_url': media_url,
        }

        if media_url:
            logger.info("[HANDLER] Processing media message")
            return handle_media_message(message_data)

        body = message_body.strip()

        logger.info("[HANDLER] Processing as accommodation request")
        return handle_accommodation_request(message_data)

    except Exception as e:
        logger.error(f"[ERROR] Exception in webhook: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)

        # if not from_number:
        #     return JsonResponse({'status': 'error', 'message': 'Missing sender number'}, status=400)

        # # Region availability check - only allow Zimbabwe numbers (+263)
        # try:
        #     from whatsapp.utils.whatsapp_service import whatsapp_service
        #     if not whatsapp_service.validate_zimbabwe_number(from_number):
        #         logger.info(f"Blocked non-ZW number {from_number} - service not available in region (payment)")
        #         whatsapp_service.send_text_message(
        #             from_number,
        #             "Sorry, this service is not available in your region."
        #         )
        #         return JsonResponse({'status': 'error', 'message': 'Service not available in your region'}, status=403)
        # except Exception:
        #     logger.exception('Region availability check failed')

        message_data = {
            'from_number': from_number,
            'to_number': to_number,
            'message_body': message_body,
            'media_url': media_url,
        }

        # Media messages handled separately
        if media_url:
            return handle_media_message(message_data)

        body = message_body.strip()

        # Status check
        if body.lower() == 'status':
            return handle_status_request(message_data)

        # Legacy trigger
        # Check for payment request in new format (USD PAY or ZWL PAY)
        if re.search(r'(USD|ZWL)\s+PAY\s+[0-9]+', body, re.IGNORECASE):
            return handle_payment_request(message_data)

        # New trigger: <CURRENCY> PAY <number>
        match = re.match(r'^(usd|zwg)\s+pay\s+([0-9\+]+)$', body, re.IGNORECASE)
        if match:
            currency = match.group(1).upper()
            payment_number = match.group(2)
            return handle_currency_payment_request(message_data, currency, payment_number)

        # Default: treat as accommodation conversation
        return handle_accommodation_request(message_data)

    except Exception:
        logger.exception('Error processing WhatsApp webhook')
        return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)


def handle_accommodation_request(message_data):
    try:
        from core.services.conversation_workflow import ConversationWorkflow
        from whatsapp.utils.whatsapp_service import whatsapp_service

        from_number = message_data['from_number']
        message_body = message_data['message_body']

        logger.info(f"[ACCOMMODATION] Processing request from {from_number}")
        logger.info(f"[ACCOMMODATION] Message: '{message_body}'")

        # Handle empty message body
        if not message_body or not message_body.strip():
            logger.warning(f"[WARN] Empty message body from {from_number}")
            whatsapp_service.send_text_message(from_number, "Please send a valid message.")
            return JsonResponse({'status': 'success', 'action': 'accommodation_request', 'response_length': 0})

        workflow = ConversationWorkflow()
        logger.info(f"[ACCOMMODATION] Initializing ConversationWorkflow")
        
        response_message = workflow.process_message(from_number, message_body)
        logger.info(f"[ACCOMMODATION] Workflow response: '{response_message}'")
        
        whatsapp_service.send_text_message(from_number, response_message)
        logger.info(f"[ACCOMMODATION] Message sent to {from_number}")

        return JsonResponse({'status': 'success', 'action': 'accommodation_request', 'response_length': len(response_message)})

    except ImportError as e:
        logger.error(f"[ERROR] Import error in accommodation handler: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'Service import failed: {str(e)}'}, status=500)
    
    except AttributeError as e:
        logger.error(f"[ERROR] Attribute error in accommodation handler: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'Service method not found: {str(e)}'}, status=500)
    
    except Exception as e:
        logger.error(f"[ERROR] Unexpected error in accommodation handler: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'Failed to process request: {str(e)}'}, status=500)


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