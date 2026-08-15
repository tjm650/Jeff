"""Legacy conversation components retained only for Django compatibility.

Production WhatsApp traffic is handled by Supabase Edge Functions. The legacy
property-search shadow hook is intentionally removed because Supabase is now the
single property-search authority.
"""

from .message_classifier import message_classifier
from .property_search import property_search_handler
from .help_utils import help_utils_handler
from .nlp_processor import nlp_processor_handler
from .utils import conversation_utils

__all__ = [
    "message_classifier",
    "property_search_handler",
    "help_utils_handler",
    "nlp_processor_handler",
    "conversation_utils",
]
