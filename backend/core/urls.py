from django.urls import path
from .views import (
    whatsapp_webhook, verify_payment, health_check, system_status,
    analytics_dashboard, conversation_analytics, property_analytics, revenue_analytics,
    download_documentation
)

app_name = 'core'

urlpatterns = [
    path('whatsapp/', whatsapp_webhook, name='whatsapp_webhook'),
    path('health/', health_check, name='health_check'),
    path('status/', system_status, name='status'),
    path('analytics/dashboard/', analytics_dashboard, name='analytics_dashboard'),
    path('analytics/properties/', property_analytics, name='property_analytics'),
]

>>>>>>> origin/main
