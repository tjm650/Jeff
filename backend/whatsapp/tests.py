import json
from unittest.mock import patch, MagicMock

from django.test import Client, RequestFactory, TestCase

from whatsapp import whatsapp_handler


class MetaWebhookTests(TestCase):
    databases = {'default'}

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

    def test_cloud_api_webhook_inbound_text_message_routing(self):
        """Test that inbound text messages are routed to conversation workflow."""
        payload = {
            'object': 'whatsapp_business_account',
            'entry': [{
                'id': 'ENTRY_ID',
                'changes': [{
                    'field': 'messages',
                    'value': {
                        'messaging_product': 'whatsapp',
                        'metadata': {
                            'display_phone_number': '15556772726',
                            'phone_number_id': '1237257249471336',
                        },
                        'messages': [{
                            'from': '263771234567',
                            'id': 'wamid.test.1',
                            'timestamp': '1700000000',
                            'text': {'body': 'hello, I need accommodation'},
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
             patch('core.services.conversation_workflow.ConversationWorkflow.process_message', return_value='Found 3 properties') as process_mock, \
             patch('whatsapp.utils.whatsapp_service.whatsapp_service.send_text_message', return_value=True) as send_mock, \
             patch('core.services.conversation_workflow.ConversationWorkflow.__init__', return_value=None):
            response = whatsapp_handler.whatsapp_webhook(request)

        self.assertEqual(response.status_code, 200)
        process_mock.assert_called_once_with('+263771234567', 'hello, I need accommodation')
        send_mock.assert_called_once_with('+263771234567', 'Found 3 properties')

    def test_cloud_api_webhook_payment_request_routing(self):
        """Test that 'USD PAY <number>' messages are routed to payment handler."""
        payload = {
            'object': 'whatsapp_business_account',
            'entry': [{
                'changes': [{
                    'field': 'messages',
                    'value': {
                        'messaging_product': 'whatsapp',
                        'metadata': {'display_phone_number': '15556772726'},
                        'messages': [{
                            'from': '263771234567',
                            'text': {'body': 'USD PAY 5.00'},
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
             patch('payment.payment_handler.payment_handler.initiate_payment') as payment_mock, \
             patch('payment.payment_handler.payment_handler._get_valid_token', return_value=None):
            payment_mock.return_value = {'success': True, 'reference': 'PAY-123'}

            response = whatsapp_handler.whatsapp_webhook(request)

        self.assertEqual(response.status_code, 200)
        payment_mock.assert_called_once_with('+263771234567')

    def test_cloud_api_webhook_status_request(self):
        """Test that 'status' messages check latest payment status."""
        payload = {
            'object': 'whatsapp_business_account',
            'entry': [{
                'changes': [{
                    'field': 'messages',
                    'value': {
                        'messaging_product': 'whatsapp',
                        'metadata': {'display_phone_number': '15556772726'},
                        'messages': [{
                            'from': '263771234567',
                            'text': {'body': 'status'},
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
             patch('payment.handlers.gateway.gateway_handler.check_payment_status', return_value={'status': 'completed'}) as status_mock, \
             patch('whatsapp.utils.whatsapp_service.whatsapp_service.send_text_message', return_value=True) as send_mock:
            response = whatsapp_handler.whatsapp_webhook(request)

        self.assertEqual(response.status_code, 200)
        send_mock.assert_called_once()

    def test_cloud_api_signature_verification_fails_on_invalid_signature(self):
        """Test that webhook rejects invalid Meta signatures."""
        payload = {
            'object': 'whatsapp_business_account',
            'entry': [{
                'changes': [{
                    'field': 'messages',
                    'value': {
                        'messages': [{
                            'from': '263771234567',
                            'text': {'body': 'test'},
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

        with patch('whatsapp.whatsapp_handler._verify_meta_signature', return_value=False):
            response = whatsapp_handler.whatsapp_webhook(request)

        self.assertEqual(response.status_code, 403)
        response_data = json.loads(response.content)
        self.assertEqual(response_data.get('status'), 'error')
