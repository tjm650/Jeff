"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from core.views import whatsapp_webhook

def health_check(request):
    return JsonResponse({
        'status': 'ok',
    })

def api_info(request):
    return JsonResponse({
        'name': 'jeff.endpoint',
        'version': '1.0.0',
    })

urlpatterns = [
    path('', api_info, name='api_info'),
    path('jeffadminstration/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),
    path('api/payment/', include('payment.urls')),
    path('api/matching/', include('matching.urls')),
    path('api/providers/', include('providers.urls')),
    path('webhook/whatsapp/', whatsapp_webhook, name='webhook_whatsapp_root'),
    # path('webhook/whatsapp', whatsapp_webhook, name='webhook_whatsapp_root_no_slash'),
    path('webhook/', include('core.urls')),
    # path('privacy/', include('core.urls')),  # Include core URLs for privacy documentation downloads

]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)