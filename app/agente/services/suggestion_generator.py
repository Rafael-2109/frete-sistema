"""
P1-1: Gerador de Sugestões de Prompt.

Gera 2-3 sugestões contextuais de follow-up após cada resposta do agente.
Usa Haiku para sugestões relevantes ao domínio logístico.

Custo estimado: ~$0.001 por chamada (~500 tokens input, ~200 output).

Uso:
    Este módulo é chamado por async_stream() em routes.py
    quando USE_PROMPT_SUGGESTIONS=true, após o evento 'done'.

    A geração é best-effort: falhas são logadas mas não propagadas.
    Nunca bloqueia o stream SSE principal (done já foi emitido).
"""

import json
import logging
import os
import re
from typing import List, Optional

import anthropic

logger = logging.getLogger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"

# Limite de caracteres da resposta do assistente para enviar ao Haiku
MAX_RESPONSE_CHARS = 3000

SUGGESTION_PROMPT = """Voce eh um gerador de sugestoes para um sistema de logistica (Nacom Goya).
Com base na ultima mensagem do usuario e resposta do assistente, gere 2-3 sugestoes de follow-up.

CONTEXTO DO SISTEMA:
- Gestao de pedidos de venda, estoque, separacoes e fretes
- Clientes: Atacadao, Assai, Carrefour, Sam's Club, outros
- Produtos: palmito, azeitona, conservas, molhos
- Operacoes: roteirizacao, expedicao, faturamento, NF-e, embarques

<mensagem_usuario>
{user_message}
</mensagem_usuario>

<resposta_assistente>
{assistant_response}
</resposta_assistente>

<ferramentas_usadas>
{tools_used}
</ferramentas_usadas>

GERE um JSON array com 2-3 strings. Cada string eh uma sugestao de follow-up.

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
    """Obtém cliente Anthropic para Haiku."""
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
    Gera 2-3 sugestões contextuais de follow-up via Haiku.

    Args:
        user_message: Última mensagem do usuário
        assistant_response: Resposta completa do assistente
        tools_used: Lista de tools/skills usadas na resposta

    Returns:
        Lista de 2-3 strings com sugestões, ou [] em caso de erro

    Note:
        Esta função é best-effort: falhas são logadas mas não propagadas.
        O custo é ~$0.001 por chamada.
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

        prompt_text = SUGGESTION_PROMPT.format(
            user_message=user_message[:500],  # Limita mensagem do usuário
            assistant_response=truncated_response,
            tools_used=tools_str,
        )

        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": prompt_text,
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
    """
    Parse seguro da resposta JSON do Haiku.

    Tenta parse direto, depois fallback com regex para extrair JSON array.

    Args:
        result_text: Texto de resposta do Haiku

    Returns:
        Lista de strings (2-3 sugestões) ou []
    """
    # Tentativa 1: parse direto
    try:
        parsed = json.loads(result_text)
        if isinstance(parsed, list):
            return _validate_suggestions(parsed)
    except json.JSONDecodeError:
        pass

    # Tentativa 2: extrair JSON array com regex
    try:
        json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, list):
                return _validate_suggestions(parsed)
    except (json.JSONDecodeError, AttributeError):
        pass

    logger.warning(
        f"[SUGGESTIONS] Resposta inválida do Haiku: {result_text[:200]}"
    )
    return []


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
