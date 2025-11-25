"""
Gerador de Respostas do Claude AI Lite.

Responsabilidade única: elaborar respostas naturais
baseadas no contexto de dados e memória.

NOVO v3.4: Self-Consistency Check
- Revisa resposta antes de enviar
- Detecta alucinações
- Valida coerência com dados

Limite: 120 linhas
"""

import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Flag para ativar/desativar revisão
HABILITAR_REVISAO = True


class ResponseGenerator:
    """Gera respostas elaboradas usando Claude API."""

    def __init__(self, claude_client):
        """
        Args:
            claude_client: Instância do ClaudeClient
        """
        self._client = claude_client
        self._reviewer = None

    def _get_reviewer(self):
        """Lazy loading do reviewer."""
        if self._reviewer is None and HABILITAR_REVISAO:
            from .response_reviewer import ResponseReviewer
            self._reviewer = ResponseReviewer(self._client)
        return self._reviewer

    def gerar_resposta(
        self,
        pergunta: str,
        contexto_dados: str,
        dominio: str = "logistica",
        contexto_memoria: str = None,
        revisar: bool = True
    ) -> str:
        """
        Gera resposta elaborada usando contexto de dados.

        Args:
            pergunta: Pergunta original do usuário
            contexto_dados: Dados formatados da capacidade
            dominio: Domínio da consulta
            contexto_memoria: Histórico + aprendizados
            revisar: Se deve revisar resposta antes de enviar (default: True)

        Returns:
            Resposta elaborada em linguagem natural (revisada se habilitado)
        """
        from ..prompts.system_base import get_system_prompt_with_memory

        # Monta prompt com memória integrada
        system_prompt = get_system_prompt_with_memory(contexto_memoria)

        # Adiciona contexto dos dados
        system_prompt += f"""

CONTEXTO DOS DADOS:
{contexto_dados}

Responda de forma clara, profissional e sempre oferecendo ajuda adicional."""

        # Gera resposta inicial
        resposta = self._client.completar(pergunta, system_prompt, use_cache=False)

        # Self-Consistency Check: revisa resposta antes de enviar
        if revisar and HABILITAR_REVISAO:
            resposta, metadados = self._revisar_resposta(
                pergunta, resposta, contexto_dados, dominio
            )
            if metadados.get('corrigido'):
                logger.info(f"[RESPONDER] Resposta revisada. Problemas: {metadados.get('problemas', [])}")

        return resposta

    def _revisar_resposta(
        self,
        pergunta: str,
        resposta: str,
        contexto_dados: str,
        dominio: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Aplica Self-Consistency Check na resposta."""
        try:
            reviewer = self._get_reviewer()
            if reviewer:
                return reviewer.revisar_resposta(
                    pergunta, resposta, contexto_dados, dominio
                )
        except Exception as e:
            logger.warning(f"[RESPONDER] Erro na revisão: {e}")

        return resposta, {'revisao': 'erro'}

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
