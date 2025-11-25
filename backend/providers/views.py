from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import logging

from core.models import Booking
from .services.workflow import provider_workflow

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def provider_response_webhook(request):
    """Webhook to handle provider responses via WhatsApp"""
    try:
        data = json.loads(request.body)
        provider_phone = data.get('provider_phone')
        message = data.get('message')

        if not provider_phone or not message:
            return JsonResponse({'error': 'Missing provider_phone or message'}, status=400)

        result = provider_workflow.handle_provider_response(provider_phone, message)

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Error in provider response webhook: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

@csrf_exempt
@require_POST
def send_booking_to_provider(request):
    """API to send booking to provider"""
    try:
        data = json.loads(request.body)
        booking_id = data.get('booking_id')

        if not booking_id:
            return JsonResponse({'error': 'Missing booking_id'}, status=400)

        booking = Booking.objects.get(id=booking_id)
        result = provider_workflow.send_booking_to_provider(booking)

        return JsonResponse(result)

    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)
    except Exception as e:
        logger.error(f"Error sending booking to provider: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

@csrf_exempt
@require_POST
def twilio_webhook(request):
    """Webhook to handle incoming Twilio WhatsApp messages"""
    try:
        message_body = request.POST.get('Body', '')
        from_number = request.POST.get('From', '').replace('whatsapp:', '')
        logger.info(f"Received WhatsApp message from {from_number}: {message_body}")

        # Handle message and get response
        result = provider_workflow.handle_provider_message(from_number, message_body)
        
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error in Twilio webhook: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)