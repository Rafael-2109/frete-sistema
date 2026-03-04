"""
P1-3: Aprendizado de Padrões entre Sessões (RAG de Comportamento).

Analisa sessões históricas e correções do usuário para gerar patterns PRESCRITIVOS:
- error_patterns: erros recorrentes que o agent cometeu (threshold 3x)
- anti_patterns: coisas que o agent fez e user corrigiu
- entity_defaults: defaults de desambiguação (quando "palmito" = VD 15x300g)

Salva padrões em /memories/learned/patterns.xml para uso proativo pelo agente.

Custo estimado: ~$0.002 por análise (~4K tokens input, ~800 output Haiku).
Trigger: a cada N sessões do usuário (configurável via PATTERN_LEARNING_THRESHOLD).

Uso:
    Chamado por _save_messages_to_db() em routes.py quando:
    - USE_PATTERN_LEARNING=true
    - total_sessions do usuário é múltiplo de PATTERN_LEARNING_THRESHOLD
"""

import json
import logging
import os
import re
from typing import Dict, Any, List, Optional

import anthropic
from app.utils.timezone import agora_utc_naive
logger = logging.getLogger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"

# Limite de caracteres totais das sessões para enviar ao Haiku
MAX_SESSIONS_CHARS = 12000

# Máximo de sessões recentes a analisar
MAX_SESSIONS_TO_ANALYZE = 15

PATTERN_PROMPT = """Voce eh um analista de comportamento para um agente de IA em sistema de logistica (Nacom Goya).
Sua tarefa eh gerar INSTRUCOES PRESCRITIVAS que mudem o comportamento do agente — NAO descricoes do que o usuario faz.

CONTEXTO DO SISTEMA:
- Gestao de pedidos de venda, estoque, separacoes e fretes
- Clientes: Atacadao, Assai, Carrefour, Sam's Club, outros
- Produtos: palmito, azeitona, conservas, molhos
- Operacoes: roteirizacao, expedicao, faturamento, NF-e, embarques

<sessoes>
{sessions}
</sessoes>

{corrections_block}

GERE um JSON com esta estrutura:

{{
  "error_patterns": [
    {{
      "instrucao": "Instrucao direta do que o agente DEVE fazer diferente. Ex: Quando usuario pede estoque de palmito, verificar TODAS as variantes (VD 15x300g, VD 24x300g, VD 12x500g) — ja errou 3x mostrando so uma.",
      "frequencia": "X ocorrencias",
      "severidade": "alta|media"
    }}
  ],
  "anti_patterns": [
    {{
      "instrucao": "O que o agente NAO deve fazer. Ex: Nao sugira consultar SQL manualmente quando a skill cotando-frete esta disponivel — usuario corrigiu 2x.",
      "frequencia": "X ocorrencias"
    }}
  ],
  "entity_defaults": [
    {{
      "termo": "Termo ambiguo que o usuario usa. Ex: palmito",
      "default": "Interpretacao padrao. Ex: VD 15x300g (cod_produto=12345)",
      "contexto": "Quando aplicar. Ex: Quando usuario diz 'palmito' sem qualificar variante"
    }}
  ],
  "confianca": "alta|media|baixa"
}}

REGRAS CRITICAS:
- PRESCRITIVO, nao descritivo: cada item deve ser uma INSTRUCAO que mude comportamento
- error_patterns: so inclua erros que ocorreram 3+ vezes (padrao confirmado)
- anti_patterns: so inclua se o usuario CORRIGIU o agente (veja secao <correcoes> se presente)
- entity_defaults: so inclua defaults que o usuario usa CONSISTENTEMENTE (3+ vezes)
- Arrays vazios se nao houver evidencia suficiente — NUNCA invente patterns
- "confianca" = "alta" se padroes claros com 5+ evidencias, "media" se 3-4, "baixa" se < 3
- NAO inclua patterns genericos tipo "verificar dados antes de responder" — so patterns ESPECIFICOS

RESPONDA APENAS JSON VALIDO, sem markdown, sem comentarios."""


def _get_anthropic_client() -> anthropic.Anthropic:
    """Obtém cliente Anthropic para Haiku."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")
    return anthropic.Anthropic(api_key=api_key)


def _format_sessions_for_analysis(sessions_data: List[Dict[str, Any]]) -> str:
    """
    Formata sessões do usuário para enviar ao Haiku.

    Extrai resumo de cada sessão: mensagens do usuário e tools usadas.
    Trunca para MAX_SESSIONS_CHARS total.

    Args:
        sessions_data: Lista de dicts com {session_id, messages, created_at, summary}

    Returns:
        String formatada para o prompt
    """
    lines = []
    total_chars = 0

    for i, sess in enumerate(sessions_data):
        session_line = f"--- SESSÃO {i + 1} ({sess.get('created_at', 'data desconhecida')}) ---"

        # Se tem summary, usa ele (muito mais conciso)
        summary = sess.get('summary')
        if summary and isinstance(summary, dict):
            resumo = summary.get('resumo_geral', '')
            topicos = ', '.join(summary.get('topicos_abordados', []))
            tools = ', '.join(summary.get('ferramentas_usadas', []))
            session_line += f"\nResumo: {resumo}"
            if topicos:
                session_line += f"\nTópicos: {topicos}"
            if tools:
                session_line += f"\nFerramentas: {tools}"

            # Pedidos mencionados
            for p in summary.get('pedidos_mencionados', [])[:3]:
                session_line += f"\nPedido: {p.get('cliente', '')} - {p.get('pedido', '')} ({p.get('status', '')})"

        else:
            # Fallback: extrair mensagens do usuário
            messages = sess.get('messages', [])
            user_msgs = [m for m in messages if m.get('role') == 'user']
            tools_used = set()

            for msg in messages:
                for tool in msg.get('tools_used', []):
                    tools_used.add(tool)

            for msg in user_msgs[:5]:  # Máximo 5 mensagens por sessão
                content = msg.get('content', '')[:200]
                session_line += f"\n[USER]: {content}"

            if tools_used:
                session_line += f"\nFerramentas: {', '.join(tools_used)}"

        # Controle de tamanho total
        if total_chars + len(session_line) > MAX_SESSIONS_CHARS:
            lines.append("... [sessões anteriores omitidas por limite]")
            break

        lines.append(session_line)
        total_chars += len(session_line)

    return "\n\n".join(lines)


def _format_corrections_for_analysis(corrections: List[Dict[str, Any]]) -> str:
    """
    Formata memórias com correções para incluir no prompt do Haiku.

    Args:
        corrections: Lista de dicts com {path, content, correction_count}

    Returns:
        Bloco XML com correções ou string vazia
    """
    if not corrections:
        return ''

    lines = ['<correcoes count="' + str(len(corrections)) + '">']
    total_chars = 0

    for c in corrections:
        content = c.get('content', '')[:300]
        count = c.get('correction_count', 0)
        path = c.get('path', '')
        line = f'<correcao path="{path}" vezes="{count}">{content}</correcao>'

        if total_chars + len(line) > 3000:
            lines.append('... [correcoes adicionais omitidas por limite]')
            break

        lines.append(line)
        total_chars += len(line)

    lines.append('</correcoes>')
    return '\n'.join(lines)


def analyze_patterns(
    sessions_data: List[Dict[str, Any]],
    user_id: int,
    corrections: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Analisa sessões históricas e correções para gerar patterns prescritivos via Haiku.

    Args:
        sessions_data: Lista de sessões com messages e summaries
        user_id: ID do usuário (para logging)
        corrections: Lista de memórias com correction_count > 0 (opcional)

    Returns:
        Dict com padrões identificados ou None em caso de erro
    """
    if not sessions_data or len(sessions_data) < 3:
        logger.debug(
            f"[PATTERNS] Usuário {user_id}: poucas sessões para análise "
            f"({len(sessions_data) if sessions_data else 0})"
        )
        return None

    try:
        client = _get_anthropic_client()
        formatted = _format_sessions_for_analysis(sessions_data)

        # Preparar bloco de correções (input adicional para Haiku)
        corrections_block = _format_corrections_for_analysis(corrections or [])
        if not corrections_block:
            corrections_block = '(Nenhuma correcao registrada ainda)'

        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": PATTERN_PROMPT.format(
                    sessions=formatted,
                    corrections_block=corrections_block,
                ),
            }],
        )

        result_text = response.content[0].text.strip()
        patterns = _parse_json_response(result_text, user_id)

        if not patterns:
            return None

        # Adiciona metadata
        patterns['_meta'] = {
            'generated_at': agora_utc_naive().isoformat(),
            'model': HAIKU_MODEL,
            'input_tokens': response.usage.input_tokens,
            'output_tokens': response.usage.output_tokens,
            'sessions_analyzed': len(sessions_data),
        }

        logger.info(
            f"[PATTERNS] Padrões identificados para usuário {user_id}: "
            f"confiança={patterns.get('confianca', 'N/A')} "
            f"({response.usage.input_tokens}+{response.usage.output_tokens} tokens)"
        )

        return patterns

    except Exception as e:
        logger.warning(f"[PATTERNS] Erro ao analisar padrões para usuário {user_id}: {e}")
        return None


def _parse_json_response(
    result_text: str,
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """Parse seguro da resposta JSON do Haiku."""
    # Tentativa 1: parse direto
    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        pass

    # Tentativa 2: extrair JSON com regex
    try:
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, AttributeError):
        pass

    logger.warning(
        f"[PATTERNS] Resposta inválida do Haiku para usuário {user_id}: "
        f"{result_text[:200]}"
    )
    return None


def analyze_and_save(
    app,
    user_id: int,
) -> bool:
    """
    Carrega sessões do usuário, analisa padrões e salva em memória.

    Função principal chamada por routes.py.

    Args:
        app: Flask app
        user_id: ID do usuário

    Returns:
        True se padrões foram salvos, False caso contrário
    """
    try:
        from ..models import AgentSession
        from app import db

        with app.app_context():
            # Carregar últimas N sessões do usuário (com mensagens)
            sessions = AgentSession.query.filter_by(
                user_id=user_id
            ).order_by(
                AgentSession.updated_at.desc()
            ).limit(MAX_SESSIONS_TO_ANALYZE).all()

            if len(sessions) < 3:
                logger.debug(
                    f"[PATTERNS] Usuário {user_id}: {len(sessions)} sessões, "
                    f"mínimo 3 para análise"
                )
                return False

            # Preparar dados das sessões
            sessions_data = []
            for sess in sessions:
                sessions_data.append({
                    'session_id': sess.session_id,
                    'created_at': sess.created_at.strftime('%d/%m/%Y') if sess.created_at else '',
                    'messages': sess.get_messages(),
                    'summary': sess.get_summary(),
                    'message_count': sess.message_count,
                })

            # Buscar memórias com correções (input adicional para patterns prescritivos)
            corrections = []
            try:
                from ..models import AgentMemory
                correction_memories = AgentMemory.query.filter(
                    AgentMemory.user_id == user_id,
                    AgentMemory.is_directory == False,  # noqa: E712
                    AgentMemory.correction_count > 0,
                ).order_by(
                    AgentMemory.correction_count.desc()
                ).limit(10).all()

                for mem in correction_memories:
                    corrections.append({
                        'path': mem.path,
                        'content': mem.content or '',
                        'correction_count': mem.correction_count,
                    })
            except Exception as e:
                logger.debug(f"[PATTERNS] Erro ao carregar correções (ignorado): {e}")

            # Analisar padrões via Haiku
            patterns = analyze_patterns(sessions_data, user_id, corrections=corrections)
            if not patterns:
                return False

            # Salvar em /memories/learned/patterns.xml
            _save_patterns_to_memory(user_id, patterns)

            db.session.commit()
            logger.info(
                f"[PATTERNS] Padrões salvos para usuário {user_id} "
                f"({len(sessions)} sessões analisadas)"
            )
            return True

    except Exception as e:
        logger.warning(f"[PATTERNS] Erro ao salvar padrões: {e}")
        try:
            with app.app_context():
                db.session.rollback()
        except Exception:
            pass
        return False


def _save_patterns_to_memory(
    user_id: int,
    patterns: Dict[str, Any],
) -> None:
    """
    Salva padrões prescritivos na memória persistente do usuário.

    Path: /memories/learned/patterns.xml
    Sobrescrito a cada análise com padrões mais recentes.

    Formato prescritivo v2:
    - error_patterns: erros recorrentes que o agent cometeu
    - anti_patterns: coisas que o agent fez e user corrigiu
    - entity_defaults: defaults de desambiguação

    Args:
        user_id: ID do usuário
        patterns: Padrões identificados pelo Haiku (formato prescritivo)
    """
    from ..models import AgentMemory

    path = "/memories/learned/patterns.xml"
    timestamp = agora_utc_naive().strftime('%d/%m/%Y %H:%M')
    confianca = _xml_escape(patterns.get('confianca', 'baixa'))
    sessions_analyzed = patterns.get('_meta', {}).get('sessions_analyzed', 0)

    # Formatar error_patterns
    errors_xml = ""
    for e in patterns.get('error_patterns', []):
        instrucao = _xml_escape(e.get('instrucao', ''))
        freq = _xml_escape(e.get('frequencia', ''))
        sev = _xml_escape(e.get('severidade', 'media'))
        errors_xml += (
            f'\n    <pattern frequencia="{freq}" severidade="{sev}">'
            f'{instrucao}</pattern>'
        )

    # Formatar anti_patterns
    anti_xml = ""
    for a in patterns.get('anti_patterns', []):
        instrucao = _xml_escape(a.get('instrucao', ''))
        freq = _xml_escape(a.get('frequencia', ''))
        anti_xml += f'\n    <avoid frequencia="{freq}">{instrucao}</avoid>'

    # Formatar entity_defaults
    defaults_xml = ""
    for d in patterns.get('entity_defaults', []):
        termo = _xml_escape(d.get('termo', ''))
        default = _xml_escape(d.get('default', ''))
        ctx = _xml_escape(d.get('contexto', ''))
        defaults_xml += (
            f'\n    <default termo="{termo}" resolve_para="{default}">'
            f'{ctx}</default>'
        )

    content = f"""<operational_patterns updated_at="{timestamp}" confianca="{confianca}" sessoes="{sessions_analyzed}">
  <error_patterns>{errors_xml}
  </error_patterns>
  <anti_patterns>{anti_xml}
  </anti_patterns>
  <entity_defaults>{defaults_xml}
  </entity_defaults>
</operational_patterns>"""

    try:
        existing = AgentMemory.get_by_path(user_id, path)
        if existing:
            existing.content = content
        else:
            AgentMemory.create_file(user_id, path, content)

        logger.debug(f"[PATTERNS] Memory prescritiva salva em {path}")
    except Exception as e:
        logger.warning(f"[PATTERNS] Erro ao salvar memory: {e}")


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


def should_analyze_patterns(user_id: int, threshold: int = 10) -> bool:
    """
    Verifica se é hora de analisar padrões para o usuário.

    Memory v2: Trigger event-driven em vez de threshold fixo.
    Critérios (qualquer um dispara):
    1. >= 3 memórias novas desde a última análise de patterns
    2. Fallback legado: total de sessões é múltiplo de threshold

    Args:
        user_id: ID do usuário
        threshold: A cada N sessões, analisa (fallback legado)

    Returns:
        True se deve analisar
    """
    try:
        from ..models import AgentSession, AgentMemory

        # v2: Verificar memórias novas desde última análise
        try:
            patterns_mem = AgentMemory.get_by_path(user_id, "/memories/learned/patterns.xml")
            if patterns_mem and patterns_mem.updated_at:
                last_analysis = patterns_mem.updated_at
                new_memories_count = AgentMemory.query.filter(
                    AgentMemory.user_id == user_id,
                    AgentMemory.is_directory == False,  # noqa: E712
                    AgentMemory.created_at > last_analysis,
                    ~AgentMemory.path.like('/memories/context/%'),  # Excluir contextuais
                    ~AgentMemory.path.like('%/consolidated.xml'),   # Excluir consolidados
                ).count()

                if new_memories_count >= 3:
                    logger.info(
                        f"[PATTERNS] v2 trigger: {new_memories_count} novas memórias "
                        f"desde última análise ({last_analysis.strftime('%d/%m %H:%M')})"
                    )
                    return True
        except Exception:
            pass  # Se falhar, cair no fallback

        # Fallback legado: a cada N sessões
        total = AgentSession.query.filter_by(user_id=user_id).count()
        return total > 0 and total % threshold == 0

    except Exception as e:
        logger.warning(f"[PATTERNS] Erro ao verificar threshold: {e}")
        return False
