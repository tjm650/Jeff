"""
Context Manager for MCP Integration

This module handles MCP context management, conversation history,
and session state for the MCP integration.
"""

import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages MCP context and conversation history"""

    def __init__(self):
        self.mcp_context = {
            'session_id': None,
            'conversation_history': [],
            'user_preferences': {},
            'last_interaction': None,
            'context_window': 2  # Number of recent exchanges to maintain
        }

    def update_context(self, user_message: str, assistant_response: str = None):
        """Update MCP context with conversation history"""
        current_time = datetime.now().isoformat()

        # Add user message to context
        self.mcp_context['conversation_history'].append({
            'role': 'user',
            'content': user_message,
            'timestamp': current_time
        })

        # Add agent response if provided
        if assistant_response:
            self.mcp_context['conversation_history'].append({
                'role': 'assistant',
                'content': assistant_response,
                'timestamp': current_time
            })

        # Maintain context window (2 exchanges = 4 messages: user-assistant-user-assistant)
        if len(self.mcp_context['conversation_history']) > self.mcp_context['context_window'] * 2:
            self.mcp_context['conversation_history'] = self.mcp_context['conversation_history'][-self.mcp_context['context_window'] * 2:]

        self.mcp_context['last_interaction'] = current_time

    def build_anthropic_prompt(self, system_prompt: str, user_message: str) -> str:
        """Build enhanced prompt with MCP context for Anthropic"""
        # Start with system prompt
        prompt = system_prompt + "\n\n"

        # Add conversation context if available
        if self.mcp_context['conversation_history']:
            prompt += "Conversation Context:\n"
            for msg in self.mcp_context['conversation_history'][-4:]:  # Last 2 exchanges (4 messages)
                role = "Human" if msg['role'] == 'user' else "Assistant"
                prompt += f"{role}: {msg['content']}\n"
            prompt += "\n"

        # Add current user message
        prompt += f"Current Message: {user_message}"

        return prompt

    def get_conversation_context(self) -> List[Dict]:
        """Get current conversation context"""
        return self.mcp_context['conversation_history']

    def clear_context(self):
        """Clear conversation context"""
        self.mcp_context['conversation_history'] = []
        self.mcp_context['last_interaction'] = None
        logger.info("MCP context cleared")

    def get_context_summary(self) -> Dict:
        """Get summary of current context state"""
        return {
            'session_id': self.mcp_context['session_id'],
            'message_count': len(self.mcp_context['conversation_history']),
            'last_interaction': self.mcp_context['last_interaction'],
            'context_window': self.mcp_context['context_window']
        }