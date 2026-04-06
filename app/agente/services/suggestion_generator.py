"""
P1-1: Gerador de Sugestões de Prompt.

Gera 2-3 sugestões contextuais de follow-up após cada resposta do agente.
Usa Sonnet para sugestões relevantes ao domínio logístico.

Custo estimado: ~$0.003 por chamada (~500 tokens input, ~200 output).

Uso:
    Este módulo é chamado por async_stream() em routes.py
    quando USE_PROMPT_SUGGESTIONS=true, após o evento 'done'.

    A geração é best-effort: falhas são logadas mas não propagadas.
    Nunca bloqueia o stream SSE principal (done já foi emitido).
"""

import logging
import os
from typing import List, Optional

import anthropic

logger = logging.getLogger(__name__)

SONNET_MODEL = "claude-sonnet-4-6"

# Limite de caracteres da resposta do assistente para enviar ao Sonnet
MAX_RESPONSE_CHARS = 5000

# System prompt estático — separado para habilitar prompt caching (cache_control ephemeral)
SUGGESTION_SYSTEM_PROMPT = """Voce eh um gerador de sugestoes para um sistema de logistica (Nacom Goya).
Com base na ultima mensagem do usuario e resposta do assistente, gere 2-3 sugestoes de follow-up.

CONTEXTO DO SISTEMA:
- Gestao de pedidos de venda, estoque, separacoes e fretes
- Clientes: Atacadao, Assai, outros
- Produtos: palmito, azeitona, conservas, molhos
- Operacoes: roteirizacao, expedicao, faturamento, NF-e, embarques

GERE um JSON array com 2-3 strings. Cada string eh uma sugestao de follow-up.

RACIOCINIO PRE-SUGESTAO:
Antes de gerar sugestoes, identifique internamente:
- Qual era o OBJETIVO do usuario? (o que ele tentava realizar)
- O que ficou INCOMPLETO ou nao resolvido na resposta?
- Qual seria o proximo passo NATURAL para alguem com esse objetivo?
Baseie suas sugestoes nesta analise, nao em templates genericos.

REGRAS:
- Cada sugestao tem NO MAXIMO 60 caracteres
- Sugestoes devem ser DIFERENTES entre si
- Sugestoes devem ser RELEVANTES ao contexto da conversa
- Sugestoes devem ser PRATICAS e ACIONAVEIS (perguntas ou comandos)
- NAO repita o que o usuario ja perguntou
- NAO use sugestoes genericas como "Me conte mais" ou "O que mais posso fazer?"
- Prefira sugestoes especificas do dominio logistico

EXEMPLOS DE BOAS SUGESTOES:
- Apos consulta de pedido: ["Ver detalhes da separacao", "Verificar estoque disponivel", "Criar separacao parcial"]
- Apos consulta de estoque: ["Quais pedidos usam este produto?", "Ver lead time de producao"]
- Apos criar separacao: ["Ver status do embarque", "Consultar outros pedidos do cliente"]
- Apos consulta SQL: ["Exportar para Excel", "Filtrar por outro periodo"]

RESPONDA APENAS um JSON array valido, sem markdown, sem comentarios.
Exemplo: ["Sugestao 1", "Sugestao 2", "Sugestao 3"]"""


def _get_anthropic_client() -> anthropic.Anthropic:
    """Obtém cliente Anthropic."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")
    return anthropic.Anthropic(api_key=api_key)


def generate_suggestions(
    user_message: str,
    assistant_response: str,
    tools_used: Optional[List[str]] = None,
) -> List[str]:
    """
    Gera 2-3 sugestões contextuais de follow-up via Sonnet.

    Args:
        user_message: Última mensagem do usuário
        assistant_response: Resposta completa do assistente
        tools_used: Lista de tools/skills usadas na resposta

    Returns:
        Lista de 2-3 strings com sugestões, ou [] em caso de erro

    Note:
        Esta função é best-effort: falhas são logadas mas não propagadas.
        O custo é ~$0.003 por chamada.
    """
    if not user_message or not assistant_response:
        logger.debug("[SUGGESTIONS] Mensagem ou resposta vazia — sem sugestões")
        return []

    # Trunca resposta longa
    truncated_response = assistant_response
    if len(truncated_response) > MAX_RESPONSE_CHARS:
        truncated_response = truncated_response[:MAX_RESPONSE_CHARS] + '... [truncado]'

    # Formata tools
    tools_str = ", ".join(tools_used) if tools_used else "nenhuma"

    try:
        client = _get_anthropic_client()

        user_content = (
            f"<mensagem_usuario>\n{user_message[:1000]}\n</mensagem_usuario>\n\n"
            f"<resposta_assistente>\n{truncated_response}\n</resposta_assistente>\n\n"
            f"<ferramentas_usadas>\n{tools_str}\n</ferramentas_usadas>"
        )

        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=400,
            system=[{
                "type": "text",
                "text": SUGGESTION_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": user_content,
            }],
        )

        result_text = response.content[0].text.strip()

        suggestions = _parse_suggestions(result_text)

        if suggestions:
            logger.info(
                f"[SUGGESTIONS] {len(suggestions)} sugestões geradas "
                f"({response.usage.input_tokens}+{response.usage.output_tokens} tokens)"
            )

        return suggestions

    except Exception as e:
        logger.warning(f"[SUGGESTIONS] Erro ao gerar sugestões: {e}")
        return []


def _parse_suggestions(result_text: str) -> List[str]:
    """Parse seguro da resposta JSON do LLM. Wrapper para parse_llm_json_response."""
    from ._utils import parse_llm_json_response
    parsed = parse_llm_json_response(result_text, list, "SUGGESTIONS")
    return _validate_suggestions(parsed) if parsed else []


def _validate_suggestions(suggestions: list) -> List[str]:
    """
    Valida e limpa sugestões.

    - Remove non-strings
    - Trunca para max 60 chars
    - Limita a 3 sugestões
    - Requer pelo menos 2

    Args:
        suggestions: Lista raw do parse JSON

    Returns:
        Lista validada de strings ou []
    """
    valid = []
    for s in suggestions:
        if isinstance(s, str) and len(s.strip()) > 5:
            text = s.strip()
            if len(text) > 60:
                text = text[:57] + '...'
            valid.append(text)

    # Limita a 3 sugestões
    valid = valid[:3]

    # Requer pelo menos 2
    if len(valid) < 2:
        return []

    return valid
