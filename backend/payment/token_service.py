from typing import Dict, List, Optional
from django.utils import timezone
from core.models import Token, Transaction
import logging

logger = logging.getLogger(__name__)

class DjangoTokenService:
    """Django-compatible service for token management operations"""

    def get_student_tokens(self, cell_number: str) -> List[Dict]:
        """Get all tokens for a user"""
        try:
            tokens = Token.objects.filter(cell_number=cell_number)

            token_list = []
            for token in tokens:
                token_list.append({
                    'token_number': token.token_number,
                    'total_uses': token.total_uses,
                    'used_count': token.used_count,
                    'remaining_uses': token.remaining_uses(),
                    'is_active': token.is_active,
                    'is_valid': token.is_valid(),
                    'purchased_at': token.purchased_at.isoformat(),
                    'expires_at': token.expires_at.isoformat(),
                    'transaction_number': token.transaction.transaction_number if token.transaction else None
                })

            return token_list

        except Exception as e:
            logger.error(f"Error getting student tokens: {str(e)}")
            return []

    def get_valid_token(self, cell_number: str) -> Optional[Token]:
        """Get a valid token for a user"""
        try:
            # Get all active tokens for user
            tokens = Token.objects.filter(
                cell_number=cell_number,
                is_active=True
            )

            # Find first valid token
            for token in tokens:
                if token.is_valid():
                    return token

            return None

        except Exception as e:
            logger.error(f"Error getting valid token: {str(e)}")
            return None

    def use_token(self, token: Token) -> bool:
        """Use one count from a token"""
        try:
            if token.use_token():
                token.save()
                logger.info(f"Token used: {token.token_number}, remaining: {token.remaining_uses()}")
                return True
            else:
                logger.warning(f"Token use failed - no remaining uses: {token.token_number}")
                return False

        except Exception as e:
            logger.error(f"Error using token: {str(e)}")
            return False

    def refund_token_use(self, token: Token) -> bool:
        """Refund a token use"""
        try:
            if token.used_count > 0:
                token.used_count -= 1
                token.save()
                logger.info(f"Token use refunded: {token.token_number}, remaining: {token.remaining_uses()}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error refunding token: {str(e)}")
            return False

    def get_token_by_number(self, token_number: str) -> Optional[Token]:
        """Get token by token number"""
        try:
            return Token.objects.filter(token_number=token_number).first()
        except Exception as e:
            logger.error(f"Error getting token by number: {str(e)}")
            return None

    def get_token_statistics(self) -> Dict:
        """Get token usage statistics"""
        try:
            from django.db.models import Sum, Avg

            total_tokens = Token.objects.count()
            active_tokens = Token.objects.filter(is_active=True).count()
            expired_tokens = Token.objects.filter(
                expires_at__lt=timezone.now()
            ).count()

            # Calculate total uses
            total_uses_result = Token.objects.aggregate(
                total_uses=Sum('total_uses'),
                used_uses=Sum('used_count')
            )

            total_uses_allocated = total_uses_result['total_uses'] or 0
            total_uses_consumed = total_uses_result['used_uses'] or 0

            return {
                'total_tokens': total_tokens,
                'active_tokens': active_tokens,
                'expired_tokens': expired_tokens,
                'total_uses_allocated': total_uses_allocated,
                'total_uses_consumed': total_uses_consumed,
                'remaining_uses': total_uses_allocated - total_uses_consumed,
                'utilization_rate': (total_uses_consumed / total_uses_allocated * 100) if total_uses_allocated > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error getting token statistics: {str(e)}")
            return {}

    def cleanup_expired_tokens(self) -> int:
        """Deactivate expired tokens"""
        try:
            expired_tokens = Token.objects.filter(
                expires_at__lt=timezone.now(),
                is_active=True
            )

            count = expired_tokens.update(is_active=False)
            logger.info(f"Deactivated {count} expired tokens")

            return count

        except Exception as e:
            logger.error(f"Error cleaning up expired tokens: {str(e)}")
            return 0

# Global instance
token_service = DjangoTokenService()