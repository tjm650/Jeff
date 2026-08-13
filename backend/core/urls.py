from django.urls import path
from .views import (
    whatsapp_webhook, health_check, system_status,
    analytics_dashboard, conversation_analytics, property_analytics,
    download_documentation,
)

app_name = 'core'

urlpatterns = [
    path('whatsapp/', whatsapp_webhook, name='whatsapp_webhook'),
    path('health/', health_check, name='health_check'),
    path('status/', system_status, name='status'),
    path('analytics/dashboard/', analytics_dashboard, name='analytics_dashboard'),
    path('analytics/conversations/', conversation_analytics, name='conversation_analytics'),
    path('analytics/properties/', property_analytics, name='analytics_properties'),
    path('docs/<str:filename>/', download_documentation, name='download_documentation'),
]
