"""
🤖 CLAUDE CLIENT
Cliente unificado para Claude 4 Sonnet
"""

from typing import Dict, List, Optional
import anthropic
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ClaudeClient:
    """Cliente único e otimizado para Claude 4 Sonnet"""
    
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
        self.max_tokens = 8192
        self.temperature = 0.7
        
    def send_message(self, messages: List[Dict], system_prompt: str = "") -> str:
        """Envia mensagem para Claude e retorna resposta"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=messages
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Erro ao comunicar com Claude: {e}")
            raise
    
    def validate_connection(self) -> bool:
        """Valida conexão com Claude API"""
        try:
            test_response = self.send_message([
                {"role": "user", "content": "Hi"}
            ])
            return len(test_response) > 0
        except:
            return False
