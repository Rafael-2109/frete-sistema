"""
Gerador de Respostas do Claude AI Lite.

Responsabilidade única: elaborar respostas naturais
baseadas no contexto de dados e memória.

Limite: 80 linhas
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Gera respostas elaboradas usando Claude API."""

    def __init__(self, claude_client):
        """
        Args:
            claude_client: Instância do ClaudeClient
        """
        self._client = claude_client

    def gerar_resposta(
        self,
        pergunta: str,
        contexto_dados: str,
        dominio: str = "logistica",
        contexto_memoria: str = None
    ) -> str:
        """
        Gera resposta elaborada usando contexto de dados.

        Args:
            pergunta: Pergunta original do usuário
            contexto_dados: Dados formatados da capacidade
            dominio: Domínio da consulta
            contexto_memoria: Histórico + aprendizados

        Returns:
            Resposta elaborada em linguagem natural
        """
        from ..prompts.system_base import get_system_prompt_with_memory

        # Monta prompt com memória integrada
        system_prompt = get_system_prompt_with_memory(contexto_memoria)

        # Adiciona contexto dos dados
        system_prompt += f"""

CONTEXTO DOS DADOS:
{contexto_dados}

Responda de forma clara, profissional e sempre oferecendo ajuda adicional."""

        return self._client.completar(pergunta, system_prompt, use_cache=False)

    def gerar_resposta_follow_up(
        self,
        pergunta: str,
        dados_reais: str,
        contexto_memoria: str = None
    ) -> str:
        """
        Gera resposta para perguntas de follow-up.

        Args:
            pergunta: Pergunta de follow-up
            dados_reais: Dados do último resultado
            contexto_memoria: Histórico da conversa

        Returns:
            Resposta com base nos dados anteriores
        """
        system_prompt = f"""Você é um assistente de logística respondendo uma pergunta de FOLLOW-UP.

REGRA CRÍTICA: Use APENAS os dados fornecidos. NÃO INVENTE informações!

{dados_reais}

CONTEXTO DA CONVERSA:
{contexto_memoria or 'Sem histórico'}

INSTRUÇÕES:
1. Use SOMENTE os dados fornecidos
2. NUNCA invente informações
3. Se não tiver a informação, sugira ao usuário fazer consulta específica"""

        return self._client.completar(pergunta, system_prompt, use_cache=False)


def get_responder() -> ResponseGenerator:
    """Factory para obter instância do responder."""
    from ..claude_client import get_claude_client
    return ResponseGenerator(get_claude_client())
