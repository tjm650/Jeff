"""Re-export key models from core for backward compatibility.

Some parts of the codebase import `Provider` from `providers.models`.
The canonical model is named `AccommodationProvider` in `core.models`.
Provide a `Provider` alias here to avoid ImportError and preserve older imports.
"""

# Import the canonical models
from core.models import AccommodationProvider, Property, Booking

# Backwards-compatible alias: some modules expect `Provider` to be available
Provider = AccommodationProvider

__all__ = [
	'Provider',
	'AccommodationProvider',
	'Property',
	'Booking',
]