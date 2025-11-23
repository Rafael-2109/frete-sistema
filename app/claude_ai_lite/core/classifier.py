"""
Classificador de Intenções do Claude AI Lite.

Responsabilidade única: identificar domínio, intenção e entidades
a partir de texto em linguagem natural.

Limite: 100 linhas
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classifica intenções usando Claude API."""

    def __init__(self, claude_client):
        """
        Args:
            claude_client: Instância do ClaudeClient
        """
        self._client = claude_client

    def classificar(
        self,
        texto: str,
        contexto_conversa: str = None
    ) -> Dict[str, Any]:
        """
        Classifica a intenção do texto.

        Args:
            texto: Texto do usuário
            contexto_conversa: Histórico para entender follow-ups

        Returns:
            Dict com dominio, intencao, entidades e confianca
        """
        from ..prompts import gerar_prompt_classificacao

        # Gera prompt dinamicamente baseado nas capacidades
        system_prompt = gerar_prompt_classificacao(contexto_conversa)

        # Chama Claude para classificar
        resposta = self._client.completar(texto, system_prompt, use_cache=True)

        # Parseia resposta JSON
        return self._parse_resposta(resposta)

    def _parse_resposta(self, resposta: str) -> Dict[str, Any]:
        """Parseia a resposta JSON do Claude."""
        try:
            resposta_limpa = resposta.strip()

            # Remove blocos de código markdown
            if resposta_limpa.startswith("```"):
                linhas = resposta_limpa.split("\n")
                resposta_limpa = "\n".join(linhas[1:-1])

            return json.loads(resposta_limpa)

        except json.JSONDecodeError:
            logger.warning(f"[CLASSIFIER] Falha ao parsear JSON: {resposta[:100]}")
            return self._fallback_response()

    def _fallback_response(self) -> Dict[str, Any]:
        """Resposta padrão quando classificação falha."""
        return {
            "dominio": "geral",
            "intencao": "outro",
            "entidades": {},
            "confianca": 0.0,
            "erro": "Falha ao interpretar resposta"
        }


def get_classifier() -> IntentClassifier:
    """
    Factory para obter instância do classifier.

    Returns:
        IntentClassifier configurado
    """
    from ..claude_client import get_claude_client
    return IntentClassifier(get_claude_client())
