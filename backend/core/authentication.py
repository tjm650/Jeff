"""
API Key Authentication for Django REST Framework
"""

import logging
from django.utils import timezone
from rest_framework import authentication, exceptions

from .models import APIKey

logger = logging.getLogger(__name__)


class APIKeyAuthentication(authentication.BaseAuthentication):
    """API Key authentication for DRF"""

    def authenticate(self, request):
        """Authenticate request using API key"""
        api_key = self.get_api_key(request)

        if not api_key:
            return None

        # Primary path: look up by hashed key value. This avoids relying on any
        # stored plaintext key material.
        candidate_hash = APIKey.hash_key(api_key)

        try:
            try:
                key_obj = APIKey.objects.get(key_hash=candidate_hash, is_active=True)
            except APIKey.DoesNotExist:
                # Backwards‑compatibility: fall back to matching the legacy `key`
                # field directly. This allows existing keys to keep working
                # while you migrate them to hashed storage.
                key_obj = APIKey.objects.get(key=api_key, is_active=True)

            if not key_obj.is_valid():
                raise exceptions.AuthenticationFailed('API key expired or inactive')

            # Return anonymous user with API key for permission checking
            return (None, key_obj)

        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API key')

    def get_api_key(self, request):
        """Extract API key from request headers"""
        # Check Authorization header
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if auth.startswith('Bearer '):
            return auth[7:]  # Remove 'Bearer ' prefix

        # Check X-API-Key header
        api_key = request.META.get('HTTP_X_API_KEY')
        if api_key:
            return api_key

        # Check query parameter (less secure, but for compatibility)
        api_key = request.GET.get('api_key')
        if api_key:
            logger.warning('API key passed as query parameter - consider using headers')
            return api_key

        return None

    def authenticate_header(self, request):
        """Return authentication scheme for 401 responses"""
        return 'Bearer'