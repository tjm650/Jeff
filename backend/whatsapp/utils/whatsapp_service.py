import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Meta WhatsApp Cloud API client.

    Meta Cloud API is the only supported WhatsApp transport. Twilio credentials,
    Content SIDs, and WhatsApp address prefixes are intentionally unsupported.
    """

    def __init__(self):
        self.access_token = os.getenv("META_ACCESS_TOKEN") or os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("META_PHONE_NUMBER_ID") or os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.api_version = os.getenv("META_API_VERSION", "v26.0")
        self.base_url = (
            f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
            if self.phone_number_id
            else None
        )

        if not self.is_configured():
            logger.warning("Meta WhatsApp credentials are not fully configured")

    def is_configured(self) -> bool:
        return bool(self.access_token and self.phone_number_id and self.base_url)

    def validate_zimbabwe_number(self, phone_number: str) -> bool:
        return bool(phone_number and phone_number.startswith("+263"))

    def _normalize_to_number(self, phone_number: str) -> str:
        value = (phone_number or "").strip()
        if not value:
            return ""
        if value.startswith("+"):
            return value
        return f"+{value}"

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _send_payload(self, to_number: str, payload: Dict[str, Any]) -> bool:
        if not self.is_configured():
            logger.error("Meta WhatsApp service is not configured")
            return False

        normalized_to = self._normalize_to_number(to_number)
        if not normalized_to:
            logger.error("No recipient number provided for WhatsApp message")
            return False

        if not self.validate_zimbabwe_number(normalized_to):
            logger.warning("Sending WhatsApp message to non-ZW number: %s", normalized_to)

        try:
            response = requests.post(
                self.base_url,
                headers=self._build_headers(),
                json={**payload, "to": normalized_to},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            meta_message_id = ((data.get("messages") or [{}])[0]).get("id")
            logger.info(
                "Meta WhatsApp message accepted: recipient=%s meta_message_id=%s",
                normalized_to,
                meta_message_id,
            )
            return True
        except requests.RequestException:
            logger.exception("Meta Cloud API error sending WhatsApp message")
            return False
        except (ValueError, TypeError, KeyError):
            logger.exception("Meta Cloud API returned an unexpected response")
            return False
        except Exception:
            logger.exception("Unexpected error sending WhatsApp message")
            return False

    def send_text_message(self, to_number: str, message: str) -> bool:
        return self._send_payload(
            to_number,
            {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "type": "text",
                "text": {"body": message},
            },
        )

    def send_template_message(
        self,
        to_number: str,
        template_name: str,
        template_variables: Optional[Dict[str, Any]] = None,
    ) -> bool:
        payload: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": os.getenv("META_TEMPLATE_LANGUAGE", "en_US")},
                "components": [],
            },
        }
        if template_variables:
            payload["template"]["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(value)}
                        for value in template_variables.values()
                    ],
                }
            ]
        return self._send_payload(to_number, payload)

    def send_error_message(self, to_number: str, message: str) -> bool:
        return self.send_text_message(to_number, message)

    def send_payment_confirmation(
        self, to_number: str, receipt: Optional[Dict[str, Any]] = None
    ) -> bool:
        details = receipt or {}
        body = (
            "Payment confirmed."
            f" Reference: {details.get('transaction_id', 'N/A')}"
            f" Amount: {details.get('amount_usd') or details.get('amount_zwg') or 'N/A'}"
        )
        return self.send_text_message(to_number, body)

    def send_payment_initiation(
        self, to_number: str, payment_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        details = payment_details or {}
        return self.send_text_message(
            to_number,
            "Please complete your payment to continue. "
            f"Reference: {details.get('reference', 'N/A')}",
        )

    def send_payment_instructions(self, to_number: str) -> bool:
        return self.send_text_message(
            to_number,
            "Please send your payment details and we will help you continue.",
        )


whatsapp_service = WhatsAppService()
__all__ = ["WhatsAppService", "whatsapp_service"]
