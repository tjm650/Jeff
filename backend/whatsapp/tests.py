from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from whatsapp import whatsapp_handler


class MetaWebhookTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_meta_webhook_verification_challenge(self):
        request = self.factory.get(
            '/webhook/whatsapp/',
            {'hub.mode': 'subscribe', 'hub.verify_token': 'meta-secret', 'hub.challenge': 'challenge-123'}
        )

        with patch('whatsapp.whatsapp_handler.dj_settings.JEFF_SETTINGS', {'META_VERIFY_TOKEN': 'meta-secret'}):
            response = whatsapp_handler.whatsapp_webhook(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'challenge-123')
