from django.urls import path
from .views import (
    verify_payment, health_check, system_status,
    analytics_dashboard, conversation_analytics, property_analytics, revenue_analytics,
    download_documentation
)
from .whatsapp_diagnostics_view import whatsapp_diagnostics
from whatsapp.diagnostic_webhook import diagnostic_whatsapp_webhook

app_name = 'core'

urlpatterns = [
    path('whatsapp/', diagnostic_whatsapp_webhook, name='whatsapp_webhook'),
    path('whatsapp/diagnostics/', whatsapp_diagnostics, name='whatsapp_diagnostics'),
    path('health/', health_check, name='health_check'),
    path('status/', system_status, name='status'),
    path('payment/verify/', verify_payment, name='verify_payment'),
    path('analytics/dashboard/', analytics_dashboard, name='analytics_dashboard'),
    path('analytics/conversations/', conversation_analytics, name='conversation_analytics'),
    path('analytics/properties/', property_analytics, name='property_analytics'),
    path('analytics/revenue/', revenue_analytics, name='revenue_analytics'),
]