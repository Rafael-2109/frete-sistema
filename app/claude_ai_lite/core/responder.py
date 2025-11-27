"""
Gerador de Respostas do Claude AI Lite.

Responsabilidade única: elaborar respostas naturais
baseadas no contexto de dados e memória.

v4.0: Integração com ResponseReviewer v2 (minimalista)
- Revisão sem custo extra de tokens
- Apenas verificações determinísticas
- Correção automática de totais

Atualizado: 27/11/2025 - v4.0: ResponseReviewer v2 minimalista
"""

import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURAÇÃO DE REVISÃO
# =============================================================================

# Flag para habilitar/desabilitar revisão globalmente
HABILITAR_REVISAO = True


def _deve_revisar(confianca: float = 0.5) -> bool:
    """
    Decide se deve revisar resposta baseado na confiança.

    Na v2, a revisão é barata (sem chamada Claude extra),
    então podemos revisar mais liberalmente.

    Args:
        confianca: Nível de confiança (0.0-1.0)

    Returns:
        True se deve revisar
    """
    if not HABILITAR_REVISAO:
        return False

    try:
        from ..config import deve_revisar_resposta
        return deve_revisar_resposta(confianca)
    except ImportError:
        # Fallback: revisa se confiança < 0.9
        # Como revisão v2 é barata, podemos ser mais agressivos
        return confianca < 0.9


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
        """
        Lazy loading do reviewer v2.

        Na v2, o reviewer não precisa do claude_client
        (não faz chamadas extras ao Claude).
        """
        if self._reviewer is None and HABILITAR_REVISAO:
            from .response_reviewer import ResponseReviewer
            self._reviewer = ResponseReviewer()  # Sem client na v2
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
            estado_estruturado: JSON do estado atual (v5 PONTE)
            revisar: Se deve revisar resposta (default: True)
            confianca: Nível de confiança da extração (0.0-1.0)

        Returns:
            Resposta elaborada em linguagem natural
        """
        from ..prompts.system_base import get_system_prompt_with_memory

        # Monta prompt com memória integrada
        system_prompt = get_system_prompt_with_memory(contexto_memoria)

        # Adiciona estado estruturado (v5 PONTE)
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

        # Gera resposta inicial via Claude
        resposta = self._client.completar(pergunta, system_prompt, use_cache=False)

        # Revisão v2: barata e determinística
        deve_revisar = revisar and _deve_revisar(confianca)

        if deve_revisar:
            resposta, metadados = self._revisar_resposta(
                pergunta, resposta, contexto_dados, dominio, estado_estruturado
            )

            if metadados.get('corrigido'):
                logger.info(f"[RESPONDER] Resposta revisada: {metadados.get('problemas', [])}")

            # Se dados não correspondem ao contexto, sinaliza para reprocessar
            if metadados.get('reprocessar'):
                problema = metadados.get('problema_contexto', 'Contexto inválido')
                logger.warning(f"[RESPONDER] Reprocessar: {problema}")
                # Retorna marcador para orchestrator tratar
                return f"[REPROCESSAR]{problema}[/REPROCESSAR]"

        return resposta

    def _revisar_resposta(
        self,
        pergunta: str,
        resposta: str,
        contexto_dados: str,
        dominio: str,
        estado_estruturado: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Aplica revisão v2 (minimalista) na resposta.

        A revisão v2 NÃO chama o Claude novamente.
        Apenas verifica coerência básica deterministicamente.
        """
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

        Follow-ups trabalham sobre dados JÁ CARREGADOS,
        não precisam de revisão (dados são os mesmos).

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


# =============================================================================
# FACTORY
# =============================================================================

def get_responder() -> ResponseGenerator:
    """Factory para obter instância do responder."""
    from ..claude_client import get_claude_client
    return ResponseGenerator(get_claude_client())
