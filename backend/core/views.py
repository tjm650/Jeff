from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
import json
import logging
from typing import Dict, List
from datetime import timedelta

from .models import Property, Booking, ConversationState, Conversation
from .analytics import analytics
from payment.payment_handler import payment_handler

logger = logging.getLogger(__name__)

def _is_rate_limited(phone_number: str, max_requests: int = 10, window_minutes: int = 5) -> bool:
    """Check if phone number is rate limited"""
    cache_key = f"rate_limit_{phone_number}"
    current_requests = cache.get(cache_key, 0)
    
    if current_requests >= max_requests:
        return True
    
    # Increment counter
    cache.set(cache_key, current_requests + 1, window_minutes * 60)
    return False

@csrf_exempt
@require_http_methods(["POST"])
def whatsapp_webhook(request):
    """
    Main webhook endpoint for WhatsApp messages using Twilio
    """
    start_time = timezone.now()

    # Debug logging for webhook issues
    logger.warning(f"Webhook called with path: {request.path}")
    logger.warning(f"Webhook called with full path: {request.get_full_path()}")
    logger.warning(f"Request method: {request.method}")
    logger.warning(f"Request content type: {request.content_type}")
    logger.warning(f"Request headers: {dict(request.headers)}")
    logger.warning(f"Request POST keys: {list(request.POST.keys())}")

    # Handle duplicated webhook URL pattern
    if 'webhook/whatsapp/webhook' in request.path:
        logger.error(f"DUPLICATED WEBHOOK URL DETECTED: {request.path}")
        logger.error("This suggests an external configuration issue with Twilio webhook URL")

        # # Extract the correct path from the duplicated URL
        # correct_path = '/webhook/whatsapp/'
        # if request.path.endswith('/webhook/whatsapp/'):
        #     # Redirect to correct URL by returning 404 and letting client retry with correct URL
        #     logger.info(f"Request should be made to: {correct_path}")
        #     return JsonResponse({
        #         'error': 'Incorrect webhook URL',
        #         'correct_url': correct_path,
        #         'message': 'Please update your Twilio webhook URL configuration'
        #     }, status=404)

    try:
        # Check if this is a message status update
        message_status = request.POST.get('MessageStatus')
        if message_status:
            logger.info(f"Received message status update: {message_status}")
            return JsonResponse({'status': 'ok'})

        # Extract message data from Twilio webhook
        from_number = request.POST.get('From', '').replace('whatsapp:', '')
        message_body = request.POST.get('Body', '')
        media_url = request.POST.get('MediaUrl0')  # For proof of payment images

        # Enhanced input validation
        if not from_number or len(from_number) < 10:
            logger.warning(f"Invalid phone number in webhook: {from_number}")
            return JsonResponse({'error': 'Invalid phone number'}, status=400)

        # Region availability check - only allow Zimbabwe numbers (+263)
        try:
            from ..whatsapp.utils.whatsapp_service import whatsapp_service
            if not whatsapp_service.validate_zimbabwe_number(from_number):
                logger.info(f"Blocked non-ZW number {from_number} - service not available in region")
                whatsapp_service.send_text_message(
                    from_number,
                    "Sorry, this service is not available in your region."
                )
                return JsonResponse({'error': 'Service not available in your region'}, status=403)
        except Exception as e:
            logger.error(f"Region check failed for {from_number}: {str(e)}")

        # Handle empty requests more gracefully
        if not message_body and not media_url:
            logger.warning(f"Empty message body and no media from {from_number}")
            logger.warning(f"Request POST data: {dict(request.POST)}")
            logger.warning(f"Request body: {request.body}")

            # Send a helpful message to the user if we have their number
            if from_number and len(from_number) >= 10:
                try:
                    from whatsapp.utils.whatsapp_service import whatsapp_service
                    welcome_message = """Hi! I'm Jeff👋, I help students at NUST find accommodation near campus."""

                    whatsapp_service.send_text_message(from_number, welcome_message)
                    logger.info(f"Welcome message sent to {from_number} for empty webhook request")
                except Exception as e:
                    logger.error(f"Failed to send welcome message: {str(e)}")

            return JsonResponse({
                'error': 'No message content',
                'message': 'Empty request received - welcome message sent to user'
            }, status=400)

        # Rate limiting check (basic implementation)
        if _is_rate_limited(from_number):
            logger.warning(f"Rate limit exceeded for {from_number}")
            return JsonResponse({'error': 'Rate limit exceeded'}, status=429)

        # Create or update conversation tracking for security
        conversation, created = Conversation.objects.get_or_create(
            cell_number=from_number,
            defaults={
                'agent_id': 'jeff_bot',
                'time_of_active_of_the_agent': timezone.now()
            }
        )
        conversation.message_count += 1
        conversation.last_message_at = timezone.now()
        conversation.save()

        # Handle media (proof of payment) - delegate to conversation workflow
        if media_url:
            logger.info(f"Processing media message from {from_number}")
            # Media handling should be done in conversation workflow
            response = process_text_message(from_number, "Media received: " + (message_body or "Payment proof"))

        # Process text message
        logger.info(f"Processing text message from {from_number}: {message_body[:50]}...")
        response = process_text_message(from_number, message_body)

        # Send response back to WhatsApp using Twilio
        try:
            from ..whatsapp.utils.whatsapp_service import whatsapp_service
            # Only send response if it's not empty and not too long
            if response and len(response.strip()) > 0 and len(response) < 4000:
                whatsapp_service.send_text_message(from_number, response)
                logger.info(f"WhatsApp response sent to {from_number}")
            else:
                logger.warning(f"Skipping empty or too long response for {from_number}")
        except Exception as e:
            logger.error(f"Failed to send WhatsApp response to {from_number}: {str(e)}")

        # Log processing time
        processing_time = (timezone.now() - start_time).total_seconds()
        logger.info(f"Webhook processed in {processing_time:.2f}s for {from_number}")

        return JsonResponse({
            'status': 'processed',
            'from': from_number,
            'response_length': len(response),
            'processing_time': processing_time
        })

    except Exception as e:
        logger.error(f'Webhook error for {from_number}: {str(e)}', exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)


def process_text_message(cell_number: str, message: str) -> str:
    """Process text message using the new conversation workflow"""
    try:
        # Import the conversation workflow service
        from .services.conversation_workflow import ConversationWorkflow

        # Create workflow instance and process message
        workflow = ConversationWorkflow()
        response = workflow.process_message(cell_number, message)

        return response

    except Exception as e:
        logger.error(f"Error processing text message for {cell_number}: {str(e)}", exc_info=True)
        return " Sorry, I encountered an some problems. Please try again or send help for assistance."


@require_http_methods(["POST"])
def verify_payment(request):
    """Payment verification endpoint"""
    try:
        # TODO: Implement payment verification logic
        return JsonResponse({'status': 'not_implemented'})

    except Exception as e:
        logger.error(f'Payment verification error: {str(e)}')
        return JsonResponse({'error': 'Internal server error'}, status=500)

@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint"""
    return JsonResponse({
        'status': 'ok',
        'service': 'Jeff Platform API (Django)',
        'version': '1.0.0',
        'timestamp': timezone.now().isoformat()
    })

@require_http_methods(["GET"])
def system_status(request):
    """Comprehensive system status endpoint"""
    try:
        from django.db import connection
        from django.core.cache import cache
        
        # Check database connectivity
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check cache connectivity
    try:
        cache.set('health_check', 'ok', 10)
        cache_status = "healthy" if cache.get('health_check') == 'ok' else "error"
    except Exception as e:
        cache_status = f"error: {str(e)}"
    
    # Get system statistics
    try:
        from .models import Property, Token, Transaction, Conversation
        stats = {
            'total_properties': Property.objects.filter(is_active=True).count(),
            'active_tokens': Token.objects.filter(is_active=True).count(),
            'total_transactions': Transaction.objects.count(),
            'active_conversations': Conversation.objects.filter(
                last_message_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
        }
    except Exception as e:
        stats = {'error': str(e)}
    
    return JsonResponse({
        'status': 'ok',
        'service': 'Jeff Platform API (Django)',
        'version': '1.0',
        'timestamp': timezone.now().isoformat(),
        'database': db_status,
        'cache': cache_status,
        'statistics': stats
    })

@require_http_methods(["GET"])
def analytics_dashboard(request):
    """Analytics dashboard endpoint"""
    try:
        days = int(request.GET.get('days', 7))
        metrics = analytics.get_dashboard_metrics()
        
        return JsonResponse({
            'status': 'ok',
            'metrics': metrics,
            'period_days': days,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Analytics dashboard error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'failed generating analytics dashboard'
        }, status=500)

@require_http_methods(["GET"])
def conversation_analytics(request):
    """Conversation analytics endpoint"""
    try:
        days = int(request.GET.get('days', 7))
        data = analytics.get_conversation_analytics(days)
        
        return JsonResponse({
            'status': 'ok',
            'analytics': data,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Conversation analytics error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'failed generating conversation analytics'
        }, status=500)

@require_http_methods(["GET"])
def property_analytics(request):
    """Property analytics endpoint"""
    try:
        data = analytics.get_property_analytics()
        
        return JsonResponse({
            'status': 'ok',
            'analytics': data,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Property analytics error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'failed generating property analytics'
        }, status=500)

@require_http_methods(["GET"])
def revenue_analytics(request):
    """Revenue analytics endpoint"""
    try:
        days = int(request.GET.get('days', 30))
        data = analytics.get_revenue_analytics(days)
        
        return JsonResponse({
            'status': 'ok',
            'analytics': data,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Revenue analytics error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'failed generating revenue analytics'
        }, status=500)


@require_http_methods(["GET"])
def download_documentation(request, filename):
    """Serve documentation files for download"""
    try:
        import os
        from django.conf import settings
        from django.http import HttpResponse, Http404

        # Define allowed files and their paths
        allowed_files = {
            'Jeff.pdf': os.path.join(settings.BASE_DIR, 'privacy', 'Jeff.pdf'),
        }

        # Check if requested file is allowed
        if filename not in allowed_files:
            raise Http404("File not found")

        file_path = allowed_files[filename]

        # Check if file exists
        if not os.path.exists(file_path):
            raise Http404("File not found")

        # Read file content
        with open(file_path, 'rb') as f:
            file_data = f.read()

        # Get host from environment or request
        host = os.getenv('DOMAIN_HOST', request.get_host())
        if not host.startswith(('http://', 'https://')):
            protocol = 'https://' if not settings.DEBUG else 'http://'
            host = f"{protocol}{host}"

        # Create response with appropriate headers for download
        response = HttpResponse(file_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(file_data)

        logger.info(f"privacy file {filename}  served from {host}")
        return response

    except Http404:
        logger.warning(f"privacy file {filename} not found")
        return HttpResponse("File not found", status=404)
    except Exception as e:
        logger.error(f"Error serving documentation file {filename}: {str(e)}")
        return HttpResponse("Internal server error", status=500)
