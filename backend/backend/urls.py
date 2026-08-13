"""
URL configuration for backend project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from whatsapp.diagnostic_webhook import diagnostic_whatsapp_webhook


def health_check(request):
    return JsonResponse({'status': 'ok'})


def api_info(request):
    return JsonResponse({'name': 'jeff.endpoint', 'version': '1.0.0'})


urlpatterns = [
    path('', api_info, name='api_info'),
    path('jeffadminstration/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),
    path('api/payment/', include('payment.urls')),
    path('api/matching/', include('matching.urls')),
    path('api/providers/', include('providers.urls')),
    path('webhook/whatsapp/', diagnostic_whatsapp_webhook, name='webhook_whatsapp_root'),
    path('webhook/whatsapp', diagnostic_whatsapp_webhook, name='webhook_whatsapp_root_no_slash'),
    path('webhook/', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
