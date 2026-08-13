"""Free-access compatibility layer.

Payment and paid token enforcement are disabled while Jeff is in free-use mode.
This module remains temporarily so older conversation workflow imports continue
working without introducing a payment dependency.
"""


class FreeAccess:
    """Truthy access object used by legacy token checks."""

    is_active = True
    total_uses = 0
    used_count = 0

    def remaining_uses(self):
        return 0

    def is_valid(self):
        return True

    def use_token(self):
        return True


class TokenHandler:
    """Compatibility API that always grants free access."""

    def get_valid_token(self, student_phone: str):
        return FreeAccess()

    def validate_token_usage(self, token) -> bool:
        return True

    def get_token_status(self, token):
        return {
            "free_access": True,
            "can_use": True,
            "message": "Jeff is currently free to use.",
        }


# Legacy import compatibility. No payment or token purchase is performed.
token_handler = TokenHandler()
