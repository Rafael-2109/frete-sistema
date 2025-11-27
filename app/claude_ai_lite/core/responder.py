"""
Gerador de Respostas do Claude AI Lite.

Responsabilidade única: elaborar respostas naturais
baseadas no contexto de dados e memória.

NOVO v3.4: Self-Consistency Check
- Revisa resposta antes de enviar
- Detecta alucinações
- Valida coerência com dados

Atualizado: 26/11/2025 - Revisão condicional baseada em confiança (config.py)
"""

import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURAÇÃO DINÂMICA DE REVISÃO
# =============================================================================

def _deve_revisar(confianca: float = 0.5) -> bool:
    """
    Decide se deve revisar resposta baseado na confiança.

    Se config.resposta.revisao_condicional = True:
        Só revisa se confiança < limiar
    Senão:
        Sempre revisa
    """
    try:
        from ..config import deve_revisar_resposta
        return deve_revisar_resposta(confianca)
    except ImportError:
        return True  # Fallback: sempre revisa


# Flag de fallback (mantida para compatibilidade)
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
        estado_estruturado: str = None,
        revisar: bool = True,
        confianca: float = 0.5
    ) -> str:
        """
        Gera resposta elaborada usando contexto de dados.

        Args:
            pergunta: Pergunta original do usuário
            contexto_dados: Dados formatados da capacidade
            dominio: Domínio da consulta
            contexto_memoria: Histórico de conversas
            estado_estruturado: NOVO v3.5.2 - JSON do estado atual (PILAR 3)
            revisar: Se deve revisar resposta antes de enviar (default: True)
            confianca: Nível de confiança da extração (0.0-1.0) - usado para revisão condicional

        Returns:
            Resposta elaborada em linguagem natural (revisada se habilitado)
        """
        from ..prompts.system_base import get_system_prompt_with_memory

        # Monta prompt com memória integrada
        system_prompt = get_system_prompt_with_memory(contexto_memoria)

        # NOVO v3.5.2: Adiciona estado estruturado (PILAR 3)
        if estado_estruturado:
            system_prompt += f"""

=== ESTADO ATUAL DA CONVERSA (JSON) ===
{estado_estruturado}
=== FIM DO ESTADO ===

Use o JSON acima para entender o contexto exato:
- REFERENCIA: "esse pedido", "esse cliente" se refere ao que está no JSON
- SEPARACAO: Se há rascunho ativo, mencione-o na resposta
- ENTIDADES: Dados já confirmados pelo usuário
"""

        # Adiciona contexto dos dados
        system_prompt += f"""

CONTEXTO DOS DADOS:
{contexto_dados}

Responda de forma clara, profissional e sempre oferecendo ajuda adicional."""

        # Gera resposta inicial
        resposta = self._client.completar(pergunta, system_prompt, use_cache=False)

        # Self-Consistency Check: revisa resposta antes de enviar
        # Usa decisão dinâmica baseada na confiança
        deve_revisar = revisar and _deve_revisar(confianca)

        if deve_revisar:
            resposta, metadados = self._revisar_resposta(
                pergunta, resposta, contexto_dados, dominio, estado_estruturado
            )
            if metadados.get('corrigido'):
                logger.info(f"[RESPONDER] Resposta revisada. Problemas: {metadados.get('problemas', [])}")

            # NOVO: Se dados não correspondem ao contexto, sinaliza para reprocessar
            if metadados.get('reprocessar'):
                logger.warning(f"[RESPONDER] Contexto inválido: {metadados.get('problema_contexto')}")
                # Retorna resposta com marcador para o orchestrator tratar
                return f"[REPROCESSAR]{metadados.get('problema_contexto')}[/REPROCESSAR]"

        return resposta

    def _revisar_resposta(
        self,
        pergunta: str,
        resposta: str,
        contexto_dados: str,
        dominio: str,
        estado_estruturado: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Aplica Self-Consistency Check na resposta."""
        try:
            reviewer = self._get_reviewer()
            if reviewer:
                return reviewer.revisar_resposta(
                    pergunta, resposta, contexto_dados, dominio, estado_estruturado
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
