from django.urls import path
from . import views

urlpatterns = [
    path('provider-response/', views.provider_response_webhook, name='provider_response_webhook'),
    path('send-booking/', views.send_booking_to_provider, name='send_booking_to_provider'),
    path('twilio/webhook/', views.twilio_webhook, name='twilio_webhook'),
]