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
      - "USD PAY <number>" and "ZWG PAY <number>"
      - payment requests in USD/ZWL format
      - "status" to check latest payment status
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

        if body.lower() == 'status':
            logger.info("[HANDLER] Processing status request")
            return handle_status_request(message_data)

        if re.search(r'(USD|ZWL)\s+PAY\s+[0-9]+', body, re.IGNORECASE):
            logger.info("[HANDLER] Processing payment request (legacy format)")
            return handle_payment_request(message_data)

        match = re.match(r'^(usd|zwg)\s+pay\s+([0-9\+]+)$', body, re.IGNORECASE)
        if match:
            currency = match.group(1).upper()
            payment_number = match.group(2)
            logger.info(f"[HANDLER] Processing payment request ({currency}: {payment_number})")
            return handle_currency_payment_request(message_data, currency, payment_number)

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
        else:
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

        # Attempt to find the latest transaction for this number (best-effort)
        latest_tx = Transaction.objects.filter(cell_number=from_number).order_by('-created_at').first()
        if not latest_tx:
            whatsapp_service.send_text_message(from_number, 'No recent payment found. Send USD PAY <number> or ZWG PAY <number> to start a payment.')
            return JsonResponse({'status': 'success', 'message': 'no_payment'})

        # Check with gateway if possible
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

        result = payment_handler.initiate_payment(
            student_phone=from_number,
            payment_number=payment_number
        )

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
                        receipt = {
                            'transaction_id': reference,
                            'amount_usd': status_resp.get('amount') or None,
                            'amount_zwg': None,
                            'date': None,
                            'payment_method': 'paynow',
                        }
                        ws.send_payment_confirmation(cell_number, receipt)
                        return
                except Exception:
                    logger.debug('Polling error, will retry')
                time.sleep(5)

            # Timeout reached
            ws.send_text_message(cell_number, f"Payment timed out after {timeout_s} seconds. Please try again or send 'status' to check payment status.")

        t = threading.Thread(target=_poll_status_and_notify, args=(from_number, reference, timeout_seconds), daemon=True)
        t.start()

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
