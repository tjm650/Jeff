"""
Token management handlers

This module handles token-specific operations including:
- Token validation and retrieval
- Token status checking
- Token usage tracking
- Token expiration handling
"""

import logging
from typing import Optional, Dict
from django.db.models import F
from django.utils import timezone

from core.models import Token

logger = logging.getLogger(__name__)


class TokenHandler:
    """Token management functionality"""

    def get_valid_token(self, student_phone: str) -> Optional[Token]:
        """Get valid token for user if exists"""
        try:
            # Find active tokens that haven't expired and have remaining uses
            valid_tokens = Token.objects.filter(
                cell_number=student_phone,
                is_active=True,
                expires_at__gt=timezone.now(),
                used_count__lt=F('total_uses')
            )

            return valid_tokens.first() if valid_tokens.exists() else None

        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return None

    def validate_token_usage(self, token: Token) -> bool:
        """Validate if token can be used"""
        try:
            return (
                token.is_active and
                token.expires_at > timezone.now() and
                token.used_count < token.total_uses
            )
        except Exception as e:
            logger.error(f"Token usage validation error: {str(e)}")
            return False

    def get_token_status(self, token: Token) -> Dict:
        """Get detailed token status information"""
        try:
            return {
                'token_number': token.token_number,
                'is_active': token.is_active,
                'expires_at': token.expires_at.isoformat(),
                'total_uses': token.total_uses,
                'used_count': token.used_count,
                'remaining_uses': token.remaining_uses(),
                'is_expired': token.expires_at <= timezone.now(),
                'can_use': self.validate_token_usage(token)
            }
        except Exception as e:
            logger.error(f"Token status error: {str(e)}")
            return {
                'error': 'Unable to retrieve token status'
            }


# Global instance
token_handler = TokenHandler()