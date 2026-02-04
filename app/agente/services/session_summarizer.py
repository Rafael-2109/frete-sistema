"""
P0-2: Sumarização Estruturada de Sessões.

Gera resumos estruturados das sessões do agente usando Haiku.
Focado no domínio logístico: pedidos, decisões, tarefas, alertas.

Custo estimado: ~$0.001 por chamada Haiku (~2K tokens input, ~500 output).

Uso:
    Este módulo é chamado automaticamente por _save_messages_to_db() em routes.py
    quando USE_SESSION_SUMMARY=true e a sessão precisa de (re)sumarização.

    A sumarização é best-effort: falhas são logadas mas não propagadas.
    Nunca bloqueia o salvamento de mensagens nem o stream SSE.
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import anthropic

logger = logging.getLogger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"

# Limite de caracteres das mensagens para enviar ao Haiku
MAX_MESSAGES_CHARS = 8000

SUMMARY_PROMPT = """Voce eh um assistente de sumarizacao para um sistema de logistica (Nacom Goya).
Analise a conversa abaixo e gere um resumo ESTRUTURADO em JSON.

CONTEXTO DO SISTEMA:
- Gestao de pedidos de venda, estoque, separacoes e fretes
- Clientes como Atacadao, Assai, Carrefour, Sam's Club
- Produtos: palmito, azeitona, conservas, molhos
- Operacoes: roteirizacao, expedicao, faturamento, NF-e

<conversa>
{messages}
</conversa>

GERE UM JSON com esta estrutura exata:

{{
  "resumo_geral": "frase curta (max 100 chars) descrevendo o que foi feito na sessao",
  "pedidos_mencionados": [
    {{
      "cliente": "nome do cliente",
      "pedido": "numero do pedido (se mencionado)",
      "status": "o que foi discutido/decidido sobre este pedido",
      "acao_pendente": "proxima acao necessaria (se houver)"
    }}
  ],
  "decisoes_tomadas": [
    "decisao 1 - descricao clara e concisa"
  ],
  "tarefas_pendentes": [
    "tarefa 1 - o que ainda precisa ser feito"
  ],
  "alertas": [
    "alerta 1 - problemas, atrasos, erros identificados"
  ],
  "ferramentas_usadas": ["consultar_sql", "save_memory"],
  "topicos_abordados": ["separacao", "estoque", "frete"]
}}

REGRAS:
- Arrays vazios se nao houver itens: []
- "pedidos_mencionados" so inclui SE pedidos/clientes foram discutidos
- "decisoes_tomadas" so decisoes CONCRETAS (nao sugestoes)
- "tarefas_pendentes" so itens que o usuario precisa agir
- "alertas" so problemas reais identificados
- "ferramentas_usadas" baseado nos tool_calls da conversa
- "topicos_abordados" tags curtas dos assuntos

RESPONDA APENAS JSON VALIDO, sem markdown, sem comentarios."""


def _get_anthropic_client() -> anthropic.Anthropic:
    """Obtém cliente Anthropic para Haiku."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")
    return anthropic.Anthropic(api_key=api_key)


def _format_messages_for_summary(messages: List[Dict[str, Any]]) -> str:
    """
    Formata mensagens da sessão para enviar ao Haiku.

    Inclui role, content e tools_used. Trunca para MAX_MESSAGES_CHARS.

    Args:
        messages: Lista de mensagens da sessão (de session.get_messages())

    Returns:
        String formatada das mensagens
    """
    lines = []
    total_chars = 0

    for msg in messages:
        role = msg.get('role', 'unknown').upper()
        content = msg.get('content', '')
        tools = msg.get('tools_used', [])

        # Trunca conteúdo individual de mensagens longas
        if len(content) > 1500:
            content = content[:1500] + '... [truncado]'

        line = f"[{role}]: {content}"
        if tools:
            line += f"\n  (tools: {', '.join(tools)})"

        # Controle de tamanho total
        if total_chars + len(line) > MAX_MESSAGES_CHARS:
            lines.append("[... mensagens anteriores omitidas por limite ...]")
            break

        lines.append(line)
        total_chars += len(line)

    return "\n\n".join(lines)


def summarize_session(
    messages: List[Dict[str, Any]],
    session_id: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Gera resumo estruturado de uma sessão via Haiku.

    Args:
        messages: Lista de mensagens da sessão
        session_id: ID da sessão (para logging)

    Returns:
        Dict com resumo estruturado, ou None em caso de erro

    Note:
        Esta função é best-effort: falhas são logadas mas não propagadas.
        O custo é ~$0.001 por chamada.
    """
    if not messages or len(messages) < 2:
        logger.debug(
            f"[SUMMARIZER] Sessão {session_id[:8]}... "
            f"sem mensagens suficientes ({len(messages) if messages else 0})"
        )
        return None

    try:
        client = _get_anthropic_client()
        formatted = _format_messages_for_summary(messages)

        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": SUMMARY_PROMPT.format(messages=formatted)
            }]
        )

        result_text = response.content[0].text.strip()

        # Parse JSON
        summary = _parse_json_response(result_text, session_id)
        if not summary:
            return None

        # Adiciona metadata
        summary['_meta'] = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'model': HAIKU_MODEL,
            'input_tokens': response.usage.input_tokens,
            'output_tokens': response.usage.output_tokens,
            'message_count': len(messages),
        }

        logger.info(
            f"[SUMMARIZER] Resumo gerado para sessão {session_id[:8]}... "
            f"({response.usage.input_tokens}+{response.usage.output_tokens} tokens)"
        )

        return summary

    except Exception as e:
        logger.warning(
            f"[SUMMARIZER] Erro ao sumarizar sessão {session_id[:8]}...: {e}"
        )
        return None


def _parse_json_response(
    result_text: str,
    session_id: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Parse seguro da resposta JSON do Haiku.

    Tenta parse direto, depois fallback com regex para extrair JSON do texto.

    Args:
        result_text: Texto de resposta do Haiku
        session_id: ID da sessão (para logging)

    Returns:
        Dict parsed ou None se inválido
    """
    # Tentativa 1: parse direto
    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        pass

    # Tentativa 2: extrair JSON com regex (Haiku pode adicionar texto extra)
    try:
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, AttributeError):
        pass

    logger.warning(
        f"[SUMMARIZER] Resposta inválida do Haiku para {session_id[:8]}...: "
        f"{result_text[:200]}"
    )
    return None


def summarize_and_save(
    app,
    session_id: str,
    user_id: int,
) -> bool:
    """
    Gera resumo e salva na sessão + memória.

    Função principal chamada por _save_messages_to_db() em routes.py.
    Executa dentro de app_context (passado como parâmetro).

    O commit das mensagens já foi feito antes desta chamada.
    Esta função faz seu próprio commit separado para o summary.

    Args:
        app: Flask app
        session_id: Nosso session_id (UUID)
        user_id: ID do usuário

    Returns:
        True se summary foi salvo, False caso contrário
    """
    try:
        from ..models import AgentSession
        from app import db

        with app.app_context():
            session = AgentSession.get_by_session_id(session_id)
            if not session:
                logger.warning(
                    f"[SUMMARIZER] Sessão não encontrada: {session_id[:8]}..."
                )
                return False

            messages = session.get_messages()
            summary = summarize_session(messages, session_id)

            if not summary:
                return False

            # 1. Salva no campo summary da sessão
            session.set_summary(summary)

            # 2. Salva na memória do usuário
            _save_summary_to_memory(user_id, session_id, summary)

            db.session.commit()
            logger.info(
                f"[SUMMARIZER] Summary salvo para sessão {session_id[:8]}... "
                f"(resumo: {summary.get('resumo_geral', '')[:60]})"
            )
            return True

    except Exception as e:
        logger.warning(f"[SUMMARIZER] Erro ao salvar summary: {e}")
        try:
            with app.app_context():
                db.session.rollback()
        except Exception:
            pass
        return False


def _save_summary_to_memory(
    user_id: int,
    session_id: str,
    summary: Dict[str, Any],
) -> None:
    """
    Salva resumo na memória persistente do usuário.

    Path: /memories/context/session_summary.xml
    Conteúdo: XML com resumo da última sessão ativa.

    A memória é sobrescrita a cada sumarização — sempre contém o
    resumo da sessão mais recente do usuário.

    Args:
        user_id: ID do usuário
        session_id: ID da sessão
        summary: Resumo estruturado
    """
    from ..models import AgentMemory

    path = "/memories/context/session_summary.xml"

    # Formata como XML para manter padrão das memórias
    pedidos_xml = ""
    for p in summary.get('pedidos_mencionados', []):
        cliente = _xml_escape(p.get('cliente', ''))
        numero = _xml_escape(p.get('pedido', ''))
        status = _xml_escape(p.get('status', ''))
        acao = _xml_escape(p.get('acao_pendente', ''))
        pedidos_xml += (
            f'\n    <pedido cliente="{cliente}" numero="{numero}">'
            f'\n      <status>{status}</status>'
            f'\n      <acao_pendente>{acao}</acao_pendente>'
            f'\n    </pedido>'
        )

    decisoes_xml = "\n".join(
        f"    <decisao>{_xml_escape(d)}</decisao>"
        for d in summary.get('decisoes_tomadas', [])
    )

    tarefas_xml = "\n".join(
        f"    <tarefa>{_xml_escape(t)}</tarefa>"
        for t in summary.get('tarefas_pendentes', [])
    )

    alertas_xml = "\n".join(
        f"    <alerta>{_xml_escape(a)}</alerta>"
        for a in summary.get('alertas', [])
    )

    topicos = ", ".join(summary.get('topicos_abordados', []))
    resumo = _xml_escape(summary.get('resumo_geral', ''))
    timestamp = datetime.now(timezone.utc).isoformat()

    content = f"""<session_summary session_id="{session_id}" updated_at="{timestamp}">
  <resumo>{resumo}</resumo>
  <pedidos>{pedidos_xml}
  </pedidos>
  <decisoes>
{decisoes_xml}
  </decisoes>
  <tarefas_pendentes>
{tarefas_xml}
  </tarefas_pendentes>
  <alertas>
{alertas_xml}
  </alertas>
  <topicos>{topicos}</topicos>
</session_summary>"""

    try:
        existing = AgentMemory.get_by_path(user_id, path)
        if existing:
            existing.content = content
        else:
            AgentMemory.create_file(user_id, path, content)

        logger.debug(f"[SUMMARIZER] Memory salva em {path}")
    except Exception as e:
        # Não propaga — best-effort
        logger.warning(f"[SUMMARIZER] Erro ao salvar memory: {e}")


def _xml_escape(text: str) -> str:
    """Escapa caracteres especiais para XML."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
