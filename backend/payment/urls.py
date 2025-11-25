from django.urls import path
from . import views
from whatsapp import whatsapp_handler

app_name = 'payment'

urlpatterns = [
    # Agent payment endpoints
    path(
        'agent/initiate/',
        views.initiate_agent_payment,
        name='initiate_agent_payment'
    ),
    # React frontend API endpoint
    path(
        'v1/initiate_paynow/',
        views.initiate_paynow,
        name='initiate_paynow'
    ),
    # WhatsApp webhook (for incoming messages from Twilio)
    path(
        'webhook/whatsapp/',
        whatsapp_handler.whatsapp_webhook,
        name='whatsapp_webhook'
    ),
    # PayNow webhook (for payment status updates)
    path(
        'webhook/paynow/',
        views.paynow_webhook,
        name='paynow_webhook'
    ),
    path(
        'status/<str:transaction_id>/',
        views.check_payment_status,
        name='check_payment_status'
    ),
    path(
        'user/<str:whatsapp_number>/',
        views.check_user_status,
        name='check_user_status'
    ),
]