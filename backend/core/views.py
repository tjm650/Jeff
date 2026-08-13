from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
import logging

from .models import Property, Conversation
from .analytics import analytics
from whatsapp.whatsapp_handler import whatsapp_webhook as meta_whatsapp_webhook

logger = logging.getLogger(__name__)


def _is_rate_limited(phone_number: str, max_requests: int = 10, window_minutes: int = 5) -> bool:
    cache_key = f"rate_limit_{phone_number}"
    current_requests = cache.get(cache_key, 0)
    if current_requests >= max_requests:
        return True
    cache.set(cache_key, current_requests + 1, window_minutes * 60)
    return False


@csrf_exempt
def whatsapp_webhook(request):
    return meta_whatsapp_webhook(request)


def process_text_message(cell_number: str, message: str) -> str:
    try:
        from .services.conversation_workflow import ConversationWorkflow
        return ConversationWorkflow().process_message(cell_number, message)
    except Exception as exc:
        logger.error("Error processing text message for %s: %s", cell_number, exc, exc_info=True)
        return "Sorry, I encountered a problem. Please try again or send help for assistance."


@require_http_methods(["GET"])
def health_check(request):
    return JsonResponse({
        'status': 'ok',
        'service': 'Jeff Platform API (Django)',
        'version': '1.0.0',
        'timestamp': timezone.now().isoformat(),
        'free_access': True,
    })


@require_http_methods(["GET"])
def system_status(request):
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_status = "healthy"
    except Exception as exc:
        db_status = f"error: {exc}"

    try:
        cache.set('health_check', 'ok', 10)
        cache_status = "healthy" if cache.get('health_check') == 'ok' else "error"
    except Exception as exc:
        cache_status = f"error: {exc}"

    try:
        stats = {
            'total_properties': Property.objects.filter(is_active=True).count(),
            'active_conversations': Conversation.objects.filter(
                last_message_at__gte=timezone.now() - timezone.timedelta(hours=24)
            ).count(),
        }
    except Exception as exc:
        stats = {'error': str(exc)}

    return JsonResponse({
        'status': 'ok',
        'service': 'Jeff Platform API (Django)',
        'version': '1.0',
        'timestamp': timezone.now().isoformat(),
        'free_access': True,
        'database': db_status,
        'cache': cache_status,
        'statistics': stats,
    })


@require_http_methods(["GET"])
def analytics_dashboard(request):
    try:
        days = int(request.GET.get('days', 7))
        return JsonResponse({'status': 'ok', 'metrics': analytics.get_dashboard_metrics(), 'period_days': days, 'timestamp': timezone.now().isoformat()})
    except Exception as exc:
        logger.error("Analytics dashboard error: %s", exc)
        return JsonResponse({'status': 'error', 'message': 'failed generating analytics dashboard'}, status=500)


@require_http_methods(["GET"])
def conversation_analytics(request):
    try:
        days = int(request.GET.get('days', 7))
        return JsonResponse({'status': 'ok', 'analytics': analytics.get_conversation_analytics(days), 'timestamp': timezone.now().isoformat()})
    except Exception as exc:
        logger.error("Conversation analytics error: %s", exc)
        return JsonResponse({'status': 'error', 'message': 'failed generating conversation analytics'}, status=500)


@require_http_methods(["GET"])
def property_analytics(request):
    try:
        return JsonResponse({'status': 'ok', 'analytics': analytics.get_property_analytics(), 'timestamp': timezone.now().isoformat()})
    except Exception as exc:
        logger.error("Property analytics error: %s", exc)
        return JsonResponse({'status': 'error', 'message': 'failed generating property analytics'}, status=500)


@require_http_methods(["GET"])
def download_documentation(request, filename):
    try:
        import os
        from django.http import Http404
        allowed_files = {'Jeff.pdf': os.path.join(settings.BASE_DIR, 'privacy', 'Jeff.pdf')}
        if filename not in allowed_files or not os.path.exists(allowed_files[filename]):
            raise Http404("File not found")
        with open(allowed_files[filename], 'rb') as file_handle:
            file_data = file_handle.read()
        response = HttpResponse(file_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(file_data)
        return response
    except Http404:
        return HttpResponse("File not found", status=404)
    except Exception as exc:
        logger.error("Error serving documentation file %s", filename, exc)
        return HttpResponse("Internal server error", status=500)
