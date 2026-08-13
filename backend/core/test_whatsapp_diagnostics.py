import json
from unittest.mock import patch

from django.test import Client, TestCase

from .diagnostic_models import WhatsAppDiagnosticEvent


class WhatsAppDiagnosticsTests(TestCase):
    def test_event_model_persists_pipeline_event(self):
        event = WhatsAppDiagnosticEvent.objects.create(
            event_id='test-event-1', correlation_id='wamid.test.1',
            direction='inbound', event_type='message_received',
            stage='message_extracted', status='ok', phone_last4='4567',
            external_id='wamid.test.1', metadata={'message_type': 'text'},
        )
        self.assertEqual(event.correlation_id, 'wamid.test.1')
        self.assertEqual(WhatsAppDiagnosticEvent.objects.count(), 1)

    def test_diagnostic_endpoint_requires_api_key(self):
        response = Client().get('/webhook/whatsapp/diagnostics/')
        self.assertEqual(response.status_code, 401)

    def test_status_event_can_be_correlated_to_outbound_message(self):
        WhatsAppDiagnosticEvent.objects.create(
            event_id='outbound-1', correlation_id='wamid.inbound.1',
            direction='outbound', event_type='message_send',
            stage='meta_api_accepted', status='ok', phone_last4='4567',
            external_id='wamid.outbound.1',
        )
        payload = {
            'object': 'whatsapp_business_account',
            'entry': [{'changes': [{'value': {'statuses': [{
                'id': 'wamid.outbound.1', 'status': 'delivered', 'recipient_id': '263771234567'
            }]}}]}],
        }
        request_body = json.dumps(payload)
        with patch('whatsapp.whatsapp_handler._verify_meta_signature', return_value=True):
            from whatsapp.diagnostic_webhook import diagnostic_whatsapp_webhook
            from django.test import RequestFactory
            response = diagnostic_whatsapp_webhook(RequestFactory().post('/webhook/whatsapp/', data=request_body, content_type='application/json'))
        self.assertEqual(response.status_code, 400)
        status_event = WhatsAppDiagnosticEvent.objects.filter(event_type='message_status').latest('created_at')
        self.assertEqual(status_event.correlation_id, 'wamid.inbound.1')
        self.assertEqual(status_event.metadata['status'], 'delivered')
