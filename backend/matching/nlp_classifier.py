import logging
import re

logger = logging.getLogger(__name__)

class NLPClassifier:
    def classify_message(self, message: str) -> str:
        if not message:
            return 'A'

        message_lower = message.lower().strip()
        # Check for payment message formats (USD PAY or ZWL PAY)
        if re.search(r'(usd|zwl)\s+pay\s+[0-9]+', message_lower) or '0717718865' in message_lower or 'payment' in message_lower:
            return 'P'

        if 'help' in message_lower or 'assist' in message_lower or 'how' in message_lower:
            return 'H'

        simple_greetings = [
            'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
            'greetings', 'howdy', 'welcome', 'sup', 'yo', 'start', 'begin',
            'thanks', 'thank you', 'how are you', 'how do you do',
            'nice to meet you', 'good to meet you', 'ready to start'
        ]

        if any(greeting in message_lower for greeting in simple_greetings):
            return 'G'

        return 'A'

    def _classify_message_fallback(self, message: str) -> str:
        return self.classify_message(message)