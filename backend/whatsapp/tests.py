import json
from unittest.mock import patch

from django.test import Client, RequestFactory, SimpleTestCase

from whatsapp import whatsapp_handler


class MetaWebhookTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.client = Client()

    def test_meta_webhook_verification_challenge(self):
        request = self.factory.get(
            '/webhook/whatsapp/',
            {'hub.mode': 'subscribe', 'hub.verify_token': 'meta-secret', 'hub.challenge': 'challenge-123'}
        )

        with patch('whatsapp.whatsapp_handler.dj_settings.JEFF_SETTINGS', {'META_VERIFY_TOKEN': 'meta-secret'}):
            response = whatsapp_handler.whatsapp_webhook(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'challenge-123')

    def test_webhook_urls_are_reachable_without_redirect(self):
        with patch('whatsapp.whatsapp_handler.dj_settings.JEFF_SETTINGS', {'META_VERIFY_TOKEN': 'meta-secret'}):
            response = self.client.get(
                '/webhook/whatsapp',
                {'hub.mode': 'subscribe', 'hub.verify_token': 'meta-secret', 'hub.challenge': 'challenge-123'},
                HTTP_X_FORWARDED_PROTO='https',
                follow=False,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'challenge-123')

        with patch('whatsapp.whatsapp_handler.dj_settings.JEFF_SETTINGS', {'META_VERIFY_TOKEN': 'meta-secret'}):
            response = self.client.get(
                '/webhook/whatsapp/',
                {'hub.mode': 'subscribe', 'hub.verify_token': 'meta-secret', 'hub.challenge': 'challenge-123'},
                HTTP_X_FORWARDED_PROTO='https',
                follow=False,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'challenge-123')

    def test_inbound_whatsapp_cloud_api_payload_is_processed(self):
        payload = {
            'object': 'whatsapp_business_account',
            'entry': [{
                'id': 'entry-1',
                'changes': [{
                    'field': 'messages',
                    'value': {
                        'messaging_product': 'whatsapp',
                        'metadata': {'display_phone_number': '15551234567'},
                        'messages': [{
                            'from': '263771234567',
                            'id': 'wamid.1',
                            'timestamp': '1700000000',
                            'text': {'body': 'hello'},
                            'type': 'text',
                        }],
                    },
                }],
            }],
        }

        request = self.factory.post(
            '/webhook/whatsapp/',
            data=json.dumps(payload),
            content_type='application/json',
        )

        with patch('whatsapp.whatsapp_handler._verify_meta_signature', return_value=True), \
             patch('core.services.conversation_workflow.ConversationWorkflow.process_message', return_value='Hi there') as process_message_mock, \
             patch('whatsapp.utils.whatsapp_service.whatsapp_service.send_text_message', return_value=True) as send_text_mock:
            response = whatsapp_handler.whatsapp_webhook(request)

        self.assertEqual(response.status_code, 200)
        process_message_mock.assert_called_once_with('+263771234567', 'hello')
        send_text_mock.assert_called_once_with('+263771234567', 'Hi there')
