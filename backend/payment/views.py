from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings as dj_settings
from .models import Payment
from .services import PaynowService
import logging
import json
import re
import hashlib
import hmac
from typing import Mapping, Any

logger = logging.getLogger(__name__)


def _verify_paynow_signature(params: Mapping[str, Any]) -> bool:
    """
    Verify Paynow webhook signature using a shared secret.

    Paynow typically sends a `hash` value which is calculated from the other
    fields in the payload and the integration key. We recompute that value
    here and compare using a constant‑time comparison.

    NOTE: If your Paynow account uses a different hashing scheme, update this
    function accordingly to match their documentation.
    """
    secret = dj_settings.JEFF_SETTINGS.get("PAYNOW_WEBHOOK_SECRET") or ""
    provided_hash = (params.get("hash") or params.get("HASH") or "").strip()

    if not secret:
        # Fail closed if the webhook secret is not configured – this prevents
        # anyone from spoofing webhook calls in production environments.
        logger.error(
            "PAYNOW_WEBHOOK_SECRET is not configured; rejecting Paynow webhook. "
            "Set PAYNOW_WEBHOOK_SECRET (or PAYNOW_INTEGRATION_KEY) in JEFF_SETTINGS."
        )
        return False

    if not provided_hash:
        logger.warning("Paynow webhook missing hash; rejecting")
        return False

    # Build the data string Paynow signs: concat all values except the hash,
    # in key‑sorted order, separated by '&'. This matches common Paynow examples.
    items = []
    for key in sorted(params.keys()):
        if key.lower() == "hash":
            continue
        value = params.get(key)
        if value is None:
            value = ""
        items.append(str(value))

    data_string = "&".join(items)

    computed_hash = hashlib.sha512(f"{secret}{data_string}".encode("utf-8")).hexdigest()

    if not hmac.compare_digest(computed_hash.lower(), provided_hash.lower()):
        logger.warning("Invalid Paynow webhook hash; rejecting webhook")
        return False

    return True

def parse_get_token_message(message):
    """
    Parse '{CURRENCY} PAY {payment_number}' message

    Returns: payment_number or None
    """
    # Match pattern: USD PAY 0771234567
    pattern = r'(USD|ZWL)\s+PAY\s+([0-9]+)'

    match = re.search(pattern, message, re.IGNORECASE)

    if match:
        return match.group(2)  # Return the payment number

    return None

@csrf_exempt
@require_http_methods(["POST"])
def initiate_agent_payment(request):
    """
    API endpoint to initiate $1.00 agent payment

    Triggered when user sends: "{CURRENCY} PAY payment_number" (e.g., "USD PAY 0771234567")

    POST data:
    whatsapp_number: User's WhatsApp number
    payment_number: Mobile payment number to charge (Paynow)
        OR
        whatsapp_number: User's WhatsApp number
        message: Full message (will parse payment_number from it)

    Returns:
        JSON response with payment details
    """
    try:
        # Parse JSON or form data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        whatsapp_number = data.get('whatsapp_number')
        payment_number = data.get('payment_number')
        message = data.get('message', '')

        # If payment_number not provided, try to parse from message
        if not payment_number and message:
            payment_number = parse_get_token_message(message)

        # Validate inputs
        if not whatsapp_number:
            return JsonResponse({
                'success': False,
                'error': 'WhatsApp number is required'
            }, status=400)

        if not payment_number:
            return JsonResponse({
                'success': False,
                'error': 'Payment number is required. Use format: USD PAY payment_number'
            }, status=400)

        # Check for recent pending payment from same user
        recent_pending = Payment.objects.filter(
            whatsapp_number=whatsapp_number,
            status='pending'
        ).order_by('-created_at').first()

        if recent_pending:
            return JsonResponse({
                'success': False,
                'error': 'You have a pending payment. Please complete it first.',
                'transaction_id': recent_pending.transaction_id
            }, status=400)

        # Create payment record
        payment = Payment.objects.create(
            whatsapp_number=whatsapp_number,
            payment_number=payment_number,
            amount=PaynowService.AGENT_AMOUNT,
            transaction_id=f"TXN-{Payment.objects.count() + 1:06d}"
        )

        # Initiate PayNow transaction
        paynow_service = PaynowService()
        result = paynow_service.create_agent_payment(
            whatsapp_number=whatsapp_number,
            payment_number=payment_number
        )

        if result['success']:
            # Update payment with PayNow details (be tolerant of different keys returned)
            payment.poll_url = result.get('poll_url', '')
            # Paynow client responses may include 'paynow_reference', 'reference' or 'redirect_url'
            payment.paynow_reference = (
                result.get('paynow_reference') or result.get('paynowreference') or result.get('redirect_url') or result.get('redirect') or ''
            )
            payment.reference = result.get('reference') or result.get('internal_reference') or ''
            payment.save()

            logger.info(f"Agent payment created: {payment.transaction_id} - WA: {whatsapp_number} - Pay: {payment_number}")

            return JsonResponse({
                'success': True,
                'transaction_id': payment.transaction_id,
                'amount': str(payment.amount),
                'whatsapp_number': whatsapp_number,
                'payment_number': payment_number,
                'instructions': result.get('instructions', 'Please check your phone for the Paynow payment prompt.'),
                'message': f'Payment request sent to __{payment_number}__. Please complete the payment on Paynow.'
            })
        else:
            # Mark payment as failed
            payment.status = 'failed '
            payment.save()

            logger.error(f"Agent payment failed: {payment.transaction_id} - {result['error']}")

            return JsonResponse({
                'success': False,
                'error': result['error'],
                'transaction_id': payment.transaction_id
            }, status=400)

    except Exception as e:
        logger.exception(f"Agent payment initiation error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def initiate_paynow(request):
    """
    API endpoint for React frontend to initiate PayNow payment

    POST data:
    whatsapp_number: User's WhatsApp number
    payment_number: Mobile payment number to charge (Paynow)

    Returns:
        JSON response with payment initiation status
    """
    try:
        # Parse JSON data
        data = json.loads(request.body)

        whatsapp_number = data.get('whatsapp_number')
        payment_number = data.get('payment_number')

        # Validate inputs
        if not whatsapp_number:
            return JsonResponse({
                'success': False,
                'error': 'WhatsApp number is required'
            }, status=400)

        if not payment_number:
            return JsonResponse({
                'success': False,
                'error': 'Payment number is required'
            }, status=400)

        # Check for recent pending payment from same user
        recent_pending = Payment.objects.filter(
            whatsapp_number=whatsapp_number,
            status='pending'
        ).order_by('-created_at').first()

        if recent_pending:
            return JsonResponse({
                'success': False,
                'error': 'You have a pending payment. Please complete it first.',
                'transaction_id': recent_pending.transaction_id
            }, status=400)

        # Create payment record
        payment = Payment.objects.create(
            whatsapp_number=whatsapp_number,
            payment_number=payment_number,
            amount=PaynowService.AGENT_AMOUNT,
            transaction_id=f"TXN-{Payment.objects.count() + 1:06d}"
        )

        # Initiate PayNow transaction
        paynow_service = PaynowService()
        result = paynow_service.create_agent_payment(
            whatsapp_number=whatsapp_number,
            payment_number=payment_number
        )

        if result['success']:
            # Update payment with PayNow details
            payment.poll_url = result.get('poll_url', '')
            payment.paynow_reference = (
                result.get('paynow_reference') or result.get('paynowreference') or result.get('redirect_url') or ''
            )
            payment.reference = result.get('reference') or result.get('internal_reference') or ''
            payment.save()

            logger.info(f"PayNow payment initiated: {payment.transaction_id} - WA: {whatsapp_number} - Pay: {payment_number}")

            return JsonResponse({
                'success': True,
                'transaction_id': payment.transaction_id,
                'amount': str(payment.amount),
                'instructions': result.get('instructions', 'Please check your phone for the Paynow payment prompt.'),
                'message': f'Payment initiated successfully. Please check your phone for the PayNow prompt.'
            })
        else:
            # Mark payment as failed
            payment.status = 'failed'
            payment.save()

            logger.error(f"PayNow payment failed: {payment.transaction_id} - {result['error']}")

            return JsonResponse({
                'success': False,
                'error': result['error'] or 'Payment initiation failed'
            }, status=400)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.exception(f"PayNow initiation error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def paynow_webhook(request):
    """
    Handle PayNow webhook callback

    PayNow sends payment status updates here
    """
    try:
        # Log webhook data
        logger.info(f"Webhook received: {request.POST}")

        # Verify webhook signature before doing any processing
        if not _verify_paynow_signature(request.POST):
            return JsonResponse(
                {"status": "error", "message": "Invalid Paynow signature"},
                status=403,
            )

        # Get webhook data
        webhook_data = {
            'paynowreference': request.POST.get('paynowreference', ''),
            'reference': request.POST.get('reference', ''),
            'status': request.POST.get('status', ''),
            'amount': request.POST.get('amount', ''),
            'cell_number': request.POST.get('cell_number', '')
        }

        # Use conversation workflow to handle payment webhook
        from core.services.conversation_workflow import ConversationWorkflow
        workflow = ConversationWorkflow()
        result = workflow.handle_payment_webhook(webhook_data)

        if result['success']:
            return JsonResponse({
                'status': 'ok',
                'message': result['message'],
                'transaction_id': result.get('transaction_id'),
                'whatsapp_number': result.get('whatsapp_number')
            })
        else:
            logger.warning(f"Payment webhook failed: {result['message']}")
            return JsonResponse({
                'status': 'error',
                'message': result['message']
            }, status=400)

    except Exception as e:
        logger.exception(f"Webhook processing error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@require_http_methods(["GET", "POST"])
def check_payment_status(request, transaction_id):
    """
    Check payment status by transaction ID
    """
    try:
        payment = Payment.objects.get(transaction_id=transaction_id)

        # Check with PayNow if still pending
        if payment.status == 'pending' and payment.poll_url:
            paynow_service = PaynowService()
            new_status = paynow_service.check_transaction_status(payment.poll_url)

            # Update if status changed
            if new_status == 'error' and new_status != payment.status:
                payment.status = new_status
                payment.save()
                logger.info(f"Payment {transaction_id} status updated to {new_status}")

        return JsonResponse({
            'success': True,
            'transaction_id': payment.transaction_id,
            'status': payment.status,
            'amount': str(payment.amount),
            'whatsapp_number': payment.whatsapp_number,
            'payment_number': payment.payment_number,
            'created_at': payment.created_at.isoformat(),
            'updated_at': payment.updated_at.isoformat()
        })

    except Payment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Transaction not found'
        }, status=404)

    except Exception as e:
        logger.exception(f"Status check error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["GET"])
def check_user_status(request, whatsapp_number):
    """
    Check if user has active/pending payment
    """
    try:
        # Get user's most recent payment
        recent_payment = Payment.objects.filter(
            whatsapp_number=whatsapp_number
        ).order_by('-created_at').first()

        # Get successful payment count
        successful_count = Payment.objects.filter(
            whatsapp_number=whatsapp_number,
            status='paid'
        ).count()

        if recent_payment:
            return JsonResponse({
                'success': True,
                'whatsapp_number': whatsapp_number,
                'has_payment': True,
                'latest_transaction_id': recent_payment.transaction_id,
                'latest_status': recent_payment.status,
                'latest_payment_number': recent_payment.payment_number,
                'successful_payment': successful_count,
                'is_pending': recent_payment.status == 'pending'
            })
        else:
            return JsonResponse({
                'success': True,
                'whatsapp_number': whatsapp_number,
                'has_payment': False,
                'successful_payment': 0,
                'is_pending': False
            })

    except Exception as e:
        logger.exception(f"User status check error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)