"""
P1-3: Aprendizado de Padrões entre Sessões (RAG de Comportamento).

Analisa sessões históricas e correções do usuário para gerar patterns PRESCRITIVOS:
- error_patterns: erros recorrentes que o agent cometeu (threshold 3x)
- anti_patterns: coisas que o agent fez e user corrigiu
- entity_defaults: defaults de desambiguação (quando "palmito" = VD 15x300g)

Salva padrões em /memories/learned/patterns.xml para uso proativo pelo agente.

Custo estimado: ~$0.006 por análise (~4K tokens input, ~800 output Sonnet).
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

SONNET_MODEL = "claude-sonnet-4-6"

# Limite de caracteres totais das sessões para enviar ao Sonnet
MAX_SESSIONS_CHARS = 24000

# Máximo de sessões recentes a analisar
MAX_SESSIONS_TO_ANALYZE = 25

# System prompt estático — separado para habilitar prompt caching (cache_control ephemeral)
PATTERN_SYSTEM_PROMPT = """Voce eh um analista de comportamento para um agente de IA em sistema de logistica (Nacom Goya).
Sua tarefa eh gerar INSTRUCOES PRESCRITIVAS que mudem o comportamento do agente — NAO descricoes do que o usuario faz.

CONTEXTO DO SISTEMA:
- Gestao de pedidos de venda, estoque, separacoes e fretes
- Clientes: Atacadao, Assai, Carrefour, Sam's Club, outros
- Produtos: palmito, azeitona, conservas, molhos
- Operacoes: roteirizacao, expedicao, faturamento, NF-e, embarques

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
  "user_profile": {{
    "resumo": "Quem eh este usuario baseado nas sessoes analisadas. Ex: Opera lancamento de pedidos em massa para grandes varejistas (Atacadao 80%, Assai 15%). Tambem monitora entregas e cancela itens pontualmente.",
    "atividades_frequentes": [
      {{"atividade": "descricao da atividade", "frequencia": "alta|media|baixa"}}
    ],
    "clientes_principais": [
      {{"nome": "cliente", "contexto": "por que aparece — lancamento, consulta, etc."}}
    ],
    "insights": [
      "Insight comportamental derivado das sessoes. Ex: Nao apenas lanca pedidos — monitora entregas, sugerindo papel end-to-end."
    ],
    "contextualizacao_para_agente": "Instrucao direta: quando este usuario mencionar X, provavelmente quer Y."
  }},
  "confianca": "alta|media|baixa"
}}

REGRAS CRITICAS:
- PRESCRITIVO, nao descritivo: cada item em error_patterns/anti_patterns deve ser uma INSTRUCAO que mude comportamento
- error_patterns: so inclua erros que ocorreram 3+ vezes (padrao confirmado)
- anti_patterns: so inclua se o usuario CORRIGIU o agente (veja secao <correcoes> se presente)
- entity_defaults: so inclua defaults que o usuario usa CONSISTENTEMENTE (3+ vezes)
- user_profile: sintetize QUEM eh este usuario baseado em TODAS as sessoes. Inclua atividades com frequencia, clientes principais com contexto de uso, e insights comportamentais. Se houver acoes_usuario nos summaries, use como fonte primaria. Se nao houver evidencia suficiente, objeto vazio {{}}
- Arrays vazios se nao houver evidencia suficiente — NUNCA invente patterns
- "confianca" = "alta" se padroes claros com 5+ evidencias, "media" se 3-4, "baixa" se < 3
- NAO inclua patterns genericos tipo "verificar dados antes de responder" — so patterns ESPECIFICOS

RESPONDA APENAS JSON VALIDO, sem markdown, sem comentarios."""


def _get_anthropic_client() -> anthropic.Anthropic:
    """Obtém cliente Anthropic."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")
    return anthropic.Anthropic(api_key=api_key)


def _format_sessions_for_analysis(sessions_data: List[Dict[str, Any]]) -> str:
    """
    Formata sessões do usuário para enviar ao Sonnet.

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

            # Ações do usuário (novo campo M1)
            acoes = summary.get('acoes_usuario', [])
            if acoes:
                session_line += f"\nAções do usuário: {'; '.join(acoes)}"

            # Sinais de perfil (novo campo M1)
            perfil = summary.get('perfil_signals', {})
            if perfil and isinstance(perfil, dict):
                dominio = perfil.get('dominio_provavel', '')
                tipos = ', '.join(perfil.get('tipo_atividade', []))
                clientes = ', '.join(perfil.get('clientes_envolvidos', []))
                volume = perfil.get('volume', '')
                if dominio:
                    session_line += f"\nDomínio: {dominio}"
                if tipos:
                    session_line += f"\nTipo atividade: {tipos}"
                if clientes:
                    session_line += f"\nClientes: {clientes}"
                if volume:
                    session_line += f"\nVolume: {volume}"

            # Pedidos mencionados
            for p in summary.get('pedidos_mencionados', [])[:5]:
                session_line += f"\nPedido: {p.get('cliente', '')} - {p.get('pedido', '')} ({p.get('status', '')})"

        else:
            # Fallback: extrair mensagens do usuário
            messages = sess.get('messages', [])
            user_msgs = [m for m in messages if m.get('role') == 'user']
            tools_used = set()

            for msg in messages:
                for tool in msg.get('tools_used', []):
                    tools_used.add(tool)

            for msg in user_msgs[:10]:  # Máximo 10 mensagens por sessão
                content = msg.get('content', '')[:500]
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
    Formata memórias com correções para incluir no prompt.

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
    existing_profile: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Analisa sessões históricas e correções para gerar patterns prescritivos via Sonnet.

    Args:
        sessions_data: Lista de sessões com messages e summaries
        user_id: ID do usuário (para logging)
        corrections: Lista de memórias com correction_count > 0 (opcional)
        existing_profile: Conteúdo XML do user.xml existente (para evolução incremental)

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

        # Preparar bloco de correções (input adicional para Sonnet)
        corrections_block = _format_corrections_for_analysis(corrections or [])
        if not corrections_block:
            corrections_block = '(Nenhuma correcao registrada ainda)'

        # Bloco de perfil existente (para evolução incremental)
        existing_profile_block = ''
        if existing_profile:
            existing_profile_block = (
                f"\n\n<perfil_atual>\n"
                f"Este eh o perfil existente do usuario. EVOLUA-o com novas evidencias das sessoes — "
                f"nao reconstrua do zero. Mantenha insights validos, atualize frequencias, "
                f"adicione novos clientes/atividades se houver evidencia.\n"
                f"{existing_profile}\n"
                f"</perfil_atual>"
            )

        user_content = (
            f"<sessoes>\n{formatted}\n</sessoes>\n\n"
            f"{corrections_block}"
            f"{existing_profile_block}"
        )

        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=3000,
            system=[{
                "type": "text",
                "text": PATTERN_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": user_content,
            }],
        )

        result_text = response.content[0].text.strip()
        patterns = _parse_json_response(result_text, user_id)

        if not patterns:
            return None

        # Adiciona metadata
        patterns['_meta'] = {
            'generated_at': agora_utc_naive().isoformat(),
            'model': SONNET_MODEL,
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
    """Parse seguro da resposta JSON do LLM."""
    # Tentativa 1: parse direto
    try:
        result = json.loads(result_text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Tentativa 2: extrair JSON com regex
    try:
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            if isinstance(result, dict):
                return result
    except (json.JSONDecodeError, AttributeError):
        pass

    logger.warning(
        f"[PATTERNS] Resposta inválida para usuário {user_id}: "
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

            # Analisar padrões via Sonnet
            patterns = analyze_patterns(sessions_data, user_id, corrections=corrections)
            if not patterns:
                return False

            # Salvar em /memories/learned/patterns.xml
            _save_patterns_to_memory(user_id, patterns)

            # Piggyback: salvar user_profile como user.xml (Tier 1)
            # Evita Sonnet call duplicado quando patterns E profile trigam juntos
            from ..config.feature_flags import USE_BEHAVIORAL_PROFILE
            if USE_BEHAVIORAL_PROFILE:
                user_profile = patterns.get('user_profile', {})
                if user_profile and user_profile.get('resumo'):
                    _save_profile_as_user_xml(
                        user_id, user_profile,
                        sessions_analyzed=len(sessions),
                        confianca=patterns.get('confianca', 'baixa'),
                    )
                    logger.info(f"[PATTERNS] user.xml salvo via piggyback para usuário {user_id}")

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
        patterns: Padrões identificados pelo Sonnet (formato prescritivo)
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

    # Formatar user_profile (novo campo M2)
    profile_xml = ""
    profile = patterns.get('user_profile', {})
    if profile and isinstance(profile, dict):
        resumo = _xml_escape(profile.get('resumo', ''))
        contextualizacao = _xml_escape(profile.get('contextualizacao_para_agente', ''))

        atividades_xml = ""
        for a in profile.get('atividades_frequentes', []):
            ativ = _xml_escape(a.get('atividade', ''))
            freq = _xml_escape(a.get('frequencia', ''))
            atividades_xml += f'\n      <atividade frequencia="{freq}">{ativ}</atividade>'

        clientes_xml = ""
        for c in profile.get('clientes_principais', []):
            nome = _xml_escape(c.get('nome', ''))
            ctx = _xml_escape(c.get('contexto', ''))
            clientes_xml += f'\n      <cliente contexto="{ctx}">{nome}</cliente>'

        insights_xml = ""
        for ins in profile.get('insights', []):
            insights_xml += f'\n      <insight>{_xml_escape(ins)}</insight>'

        profile_xml = f"""
  <user_profile>
    <resumo>{resumo}</resumo>
    <atividades_frequentes>{atividades_xml}
    </atividades_frequentes>
    <clientes_principais>{clientes_xml}
    </clientes_principais>
    <insights>{insights_xml}
    </insights>
    <contextualizacao>{contextualizacao}</contextualizacao>
  </user_profile>"""

    content = f"""<operational_patterns updated_at="{timestamp}" confianca="{confianca}" sessoes="{sessions_analyzed}">
  <error_patterns>{errors_xml}
  </error_patterns>
  <anti_patterns>{anti_xml}
  </anti_patterns>
  <entity_defaults>{defaults_xml}
  </entity_defaults>{profile_xml}
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

    # Salvar user_profile TAMBÉM como /memories/user.xml (Tier 1 — SEMPRE injetado)
    profile = patterns.get('user_profile', {})
    if profile and isinstance(profile, dict) and profile.get('resumo'):
        try:
            _save_profile_as_user_xml(user_id, profile, sessions_analyzed, confianca)
        except Exception as e:
            logger.warning(f"[PATTERNS] Erro ao salvar user.xml: {e}")


def _save_profile_as_user_xml(
    user_id: int,
    profile: Dict[str, Any],
    sessions_analyzed: int,
    confianca: str,
) -> None:
    """
    Salva o user_profile como /memories/user.xml (Tier 1 — SEMPRE injetado).

    Formato conciso (~600 chars) para injeção eficiente no system prompt.
    importance_score=0.9, category='permanent' (sem decay).

    Args:
        user_id: ID do usuário
        profile: Dict com resumo, atividades_frequentes, clientes_principais, etc.
        sessions_analyzed: Número de sessões analisadas
        confianca: Nível de confiança (alta/media/baixa)
    """
    from ..models import AgentMemory

    path = "/memories/user.xml"
    timestamp = agora_utc_naive().strftime('%d/%m/%Y')
    confianca = _xml_escape(confianca)

    # Formatar atividades
    atividades_xml = ""
    for a in profile.get('atividades_frequentes', []):
        ativ = _xml_escape(a.get('atividade', ''))
        freq = _xml_escape(a.get('frequencia', ''))
        if ativ:
            atividades_xml += f'\n    <atividade frequencia="{freq}">{ativ}</atividade>'

    # Formatar clientes
    clientes_xml = ""
    for c in profile.get('clientes_principais', []):
        nome = _xml_escape(c.get('nome', ''))
        ctx = _xml_escape(c.get('contexto', ''))
        if nome:
            clientes_xml += f'\n    <cliente contexto="{ctx}">{nome}</cliente>'

    # Formatar insights
    insights_xml = ""
    for ins in profile.get('insights', []):
        if ins:
            insights_xml += f'\n    <insight>{_xml_escape(ins)}</insight>'

    resumo = _xml_escape(profile.get('resumo', ''))
    contextualizacao = _xml_escape(profile.get('contextualizacao_para_agente', ''))

    content = f"""<user_profile updated_at="{timestamp}" confidence="{confianca}" sessions="{sessions_analyzed}">
  <resumo>{resumo}</resumo>
  <atividades>{atividades_xml}
  </atividades>
  <clientes>{clientes_xml}
  </clientes>
  <insights>{insights_xml}
  </insights>
  <contextualizacao>{contextualizacao}</contextualizacao>
</user_profile>"""

    try:
        existing = AgentMemory.get_by_path(user_id, path)
        if existing:
            existing.content = content
            existing.updated_at = agora_utc_naive()
            existing.importance_score = 0.9
            existing.category = 'permanent'
        else:
            mem = AgentMemory.create_file(user_id, path, content)
            mem.importance_score = 0.9
            mem.category = 'permanent'

        logger.info(f"[PROFILE] user.xml salvo para usuário {user_id} (confiança={confianca})")
    except Exception as e:
        logger.warning(f"[PROFILE] Erro ao salvar user.xml: {e}")
        return

    # Embedding best-effort
    try:
        from app.embeddings.config import MEMORY_SEMANTIC_SEARCH
        if MEMORY_SEMANTIC_SEARCH:
            from ..tools.memory_mcp_tool import _embed_memory_best_effort
            _embed_memory_best_effort(user_id, path, content)
    except Exception as e:
        logger.debug(f"[PROFILE] Embedding user.xml falhou (ignorado): {e}")


def should_generate_profile(user_id: int, threshold: int = 5) -> bool:
    """
    Verifica se é hora de gerar/atualizar o perfil comportamental (user.xml).

    Threshold menor que patterns (5 vs 10) para perfil mais rápido.

    Critérios:
    1. user.xml NÃO existe E user tem >= 3 sessões → True
    2. user.xml existe: sessões desde updated_at >= threshold → True
    3. Fallback: total de sessões é múltiplo de threshold → True

    Args:
        user_id: ID do usuário
        threshold: A cada N sessões, regenera perfil

    Returns:
        True se deve gerar/atualizar perfil
    """
    try:
        from ..models import AgentSession, AgentMemory

        total_sessions = AgentSession.query.filter_by(user_id=user_id).count()
        if total_sessions < 3:
            return False

        user_xml = AgentMemory.get_by_path(user_id, "/memories/user.xml")

        # Se user.xml não existe e tem sessões suficientes → gerar
        if not user_xml:
            logger.info(
                f"[PROFILE] Usuário {user_id}: user.xml não existe, "
                f"{total_sessions} sessões → trigger"
            )
            return True

        # Se existe: contar sessões desde a última atualização
        if user_xml.updated_at:
            sessions_since = AgentSession.query.filter(
                AgentSession.user_id == user_id,
                AgentSession.updated_at > user_xml.updated_at,
            ).count()

            if sessions_since >= threshold:
                logger.info(
                    f"[PROFILE] Usuário {user_id}: {sessions_since} sessões "
                    f"desde última atualização → trigger"
                )
                return True

        # Fallback: múltiplo de threshold
        if total_sessions % threshold == 0:
            return True

        return False

    except Exception as e:
        logger.warning(f"[PROFILE] Erro ao verificar threshold: {e}")
        return False


def generate_and_save_profile(app, user_id: int) -> bool:
    """
    Gera perfil comportamental e salva como /memories/user.xml.

    Quando patterns E profile trigam juntos, analyze_and_save() faz o
    piggyback de user.xml — esta função NÃO é chamada nesse cenário.
    Esta função é para quando SÓ o profile triga (sem patterns).

    Args:
        app: Flask app
        user_id: ID do usuário

    Returns:
        True se perfil foi salvo, False caso contrário
    """
    try:
        from ..models import AgentSession, AgentMemory
        from app import db

        with app.app_context():
            # Carregar sessões (mesma query de analyze_and_save)
            sessions = AgentSession.query.filter_by(
                user_id=user_id
            ).order_by(
                AgentSession.updated_at.desc()
            ).limit(MAX_SESSIONS_TO_ANALYZE).all()

            if len(sessions) < 3:
                return False

            sessions_data = []
            for sess in sessions:
                sessions_data.append({
                    'session_id': sess.session_id,
                    'created_at': sess.created_at.strftime('%d/%m/%Y') if sess.created_at else '',
                    'messages': sess.get_messages(),
                    'summary': sess.get_summary(),
                    'message_count': sess.message_count,
                })

            # Carregar correções
            corrections = []
            try:
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
            except Exception:
                pass

            # Carregar perfil existente para evolução incremental
            existing_user_xml = AgentMemory.get_by_path(user_id, '/memories/user.xml')
            existing_profile_text = existing_user_xml.content if existing_user_xml else None

            # Chamar analyze_patterns() — retorna dict com user_profile
            patterns = analyze_patterns(
                sessions_data, user_id,
                corrections=corrections,
                existing_profile=existing_profile_text,
            )
            if not patterns:
                return False

            # Extrair user_profile e salvar como user.xml
            profile = patterns.get('user_profile', {})
            if not profile or not profile.get('resumo'):
                logger.debug(f"[PROFILE] Sonnet não gerou user_profile para usuário {user_id}")
                return False

            sessions_analyzed = len(sessions_data)
            confianca = patterns.get('confianca', 'baixa')

            _save_profile_as_user_xml(user_id, profile, sessions_analyzed, confianca)

            db.session.commit()
            logger.info(
                f"[PROFILE] Perfil gerado para usuário {user_id} "
                f"({sessions_analyzed} sessões analisadas)"
            )
            return True

    except Exception as e:
        logger.warning(f"[PROFILE] Erro ao gerar perfil: {e}")
        try:
            with app.app_context():
                from app import db
                db.session.rollback()
        except Exception:
            pass
        return False


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


# =====================================================================
# EXTRACAO POS-SESSAO DE CONHECIMENTO ORGANIZACIONAL
# =====================================================================
#
# Taxonomia de 5 niveis + 4 criterios formais (12/03/2026):
# - 3 tipos operacionais: protocolo, armadilha, heuristica
# - Niveis 1-2 (lookup/composicao) = NAO memorizar
# - Niveis 3-5 (diagnostico/armadilha/heuristica) = memorizar
# - 4 criterios: bifurca? perdeu tempo? implicito? transferivel?
# - Briefing da empresa injetado via empresa_briefing.md
# - Titulos existentes injetados para reutilizacao/enriquecimento
# - Busca semantica pre-save via _find_similar_empresa_memory()
#
# Paths hierarquicos: /memories/empresa/{tipo}/{dominio}/{slug-do-titulo}.xml
# Salva como memorias empresa (user_id=0, escopo='empresa').
# Rede de seguranca: captura o que o agente NAO salvou via save_memory.
# Roda em daemon thread (background) a cada exchange, sem bloquear UX.
# =====================================================================

_EMPRESA_BRIEFING_CACHE: str | None = None


def _load_empresa_briefing() -> str:
    """Carrega briefing da empresa de empresa_briefing.md (cache module-level)."""
    global _EMPRESA_BRIEFING_CACHE
    if _EMPRESA_BRIEFING_CACHE is not None:
        return _EMPRESA_BRIEFING_CACHE

    briefing_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'config', 'empresa_briefing.md',
    )
    try:
        with open(briefing_path, 'r', encoding='utf-8') as f:
            _EMPRESA_BRIEFING_CACHE = f.read()
    except FileNotFoundError:
        logger.warning("[KNOWLEDGE_EXTRACTION] empresa_briefing.md nao encontrado")
        _EMPRESA_BRIEFING_CACHE = ""
    return _EMPRESA_BRIEFING_CACHE


def _build_extraction_prompt() -> str:
    """Constroi o prompt de extracao com briefing + taxonomia de 5 niveis + 4 criterios.

    Briefing carregado de empresa_briefing.md (cache module-level).
    Taxonomia embutida no prompt — Sonnet decide o que memorizar com criterios formais.
    Resultado eh constante durante o lifecycle da aplicacao (cache via module-level).
    """
    briefing = _load_empresa_briefing()

    parts = [
        "Voce eh um extrator de CONHECIMENTO ORGANIZACIONAL para a Nacom Goya.\n"
        "Extraia CONHECIMENTO TACITO (protocolos, armadilhas, heuristicas), NAO FATOS ou LOOKUPS.\n",
    ]

    if briefing:
        parts.append(f"\nCONTEXTO DA EMPRESA:\n{briefing}\n\n---\n")

    parts.append("""

TAXONOMIA DE PROBLEMAS — O que memorizar e o que NAO memorizar:

Nivel 1 — Lookup (NUNCA memorizar)
  Caminho deterministico: input -> query -> output. Sempre igual.
  "Qual embarque da NF X?" -> JOIN faturamento/embarque. Fim.
  Skills e codigo ja resolvem. Memorizar seria duplicar codigo em prosa.

Nivel 2 — Composicao (NUNCA memorizar)
  Combina 2-3 lookups em sequencia previsivel.
  "Pedidos do Atacadao com falta" = resolver entidade + verificar disponibilidade.
  O routing de skills ja cobre. A sequencia eh fixa.

  --- LINHA DE CORTE: abaixo = infraestrutura, acima = conhecimento tacito ---

Nivel 3 — Diagnostico diferencial (MEMORIZAR a arvore de investigacao)
  Multiplas causas possiveis, caminho varia conforme o que encontra.
  "NF nao apareceu no Odoo" -> pode ser: DFe nao importado, match falhou por CNPJ,
  empresa errada, fornecedor sem de-para, timeout do job.
  Memorizar: NAO o caso ("NF 12345 era CNPJ errado"), mas a ARVORE — quais causas
  verificar, em que ordem, como distinguir uma da outra.

Nivel 4 — Resolucao com armadilhas (MEMORIZAR caminho + dead ends)
  Requer acoes que podem dar errado. A sequencia importa.
  "Reativar embarque cancelado" -> verificar NF emitida, separacao existente, reverter status.
  "UPDATE no valor de frete" -> NAO dispara recalculo de margem — precisa chamar o service.
  Memorizar: sequencia correta, o que NAO funciona e por que, pre-condicoes.

Nivel 5 — Heuristica emergente (MEMORIZAR como regra)
  Problema que parece unico mas revela padrao recorrente.
  "3 NFs do mesmo fornecedor falharam no match" -> fornecedor tem CNPJ secundario.
  Memorizar: a HEURISTICA — "se fornecedor X falha no match repetidamente,
  verificar CNPJ secundario". Transforma caso em regra.

RESUMO: Memorize PROTOCOLOS DE INVESTIGACAO e ARMADILHAS CONHECIDAS.
NAO memorize solucoes pontuais ("NF 12345 estava na empresa 3") — morrem no primeiro uso.

CRITERIO FORMAL — pelo menos 2 devem ser verdadeiros:
1. Bifurca? Multiplas causas, investigacao muda.
2. Perdeu tempo? Caminho errado custou tempo real.
3. Implicito? Nao esta no codigo nem nos schemas.
4. Transferivel? Aplica-se a casos futuros.
Se nenhum → Nivel 1-2 → NAO extraia.

Retorne JSON VALIDO com esta estrutura (array vazio se nao encontrar nada):

{
  "conhecimentos": [
    {
      "titulo": "4-10 palavras, manchete do conhecimento",
      "tipo": "protocolo|armadilha|heuristica",
      "nivel": 3,
      "dominio": "texto livre (ex: recebimento, financeiro, comercial, logistica, carvia, producao, integracao)",
      "criterios_atendidos": [1, 3],
      "descricao": "Descricao clara do conhecimento",
      "prescricao": "Quando [situacao], o agente deve [acao] porque [razao]"
    }
  ]
}

TITULO (campo titulo):
O titulo eh o nome do conhecimento — como uma manchete de jornal.
- 4 a 10 palavras que capturam o conceito central
- Substantivo-frase, nao sentenca completa
- Especifico o suficiente para distinguir de outros conhecimentos
- Se na lista de titulos existentes (enviada na mensagem) houver um titulo EQUIVALENTE,
  REUTILIZE exatamente esse titulo (o sistema enriquecera a memoria existente)

Exemplos:
  OK "Diagnostico de NF ausente no Odoo"
  OK "Atacadao nao aceita pedido parcial"
  OK "UPDATE frete nao recalcula margem"
  RUIM "Verificacao" (generico)
  RUIM "Procedimento completo para realizar a verificacao..." (sentenca, nao titulo)

TIPOS (campo tipo):
  - "protocolo": Arvore de investigacao com multiplas causas possiveis (Nivel 3+)
  - "armadilha": Caminho que parece correto mas falha, com dead ends documentados (Nivel 4+)
  - "heuristica": Padrao recorrente que transforma caso em regra generalizavel (Nivel 5)

IGNORE: meta-AI (memoria, embedding, SDK, prompt, agente, Claude, Sonnet, Haiku, KG, RAG, dedup, PRD, daemon thread), resultados pontuais, status temporarios, dados do sistema.
Se conversa INTEIRAMENTE sobre dev/debug do proprio sistema → array vazio.
Prefira POUCOS itens de ALTA qualidade a muitos de baixa qualidade.

FILTRO ANTI-RUIDO (aplicar ANTES de incluir qualquer item):
1. Definicoes triviais: Se um LLM treinado SABERIA a definicao sem contexto Nacom, NAO extraia.
   Exemplos de termos que NUNCA devem ser extraidos: "cross-docking", "D+2", "lote",
   "pedido de venda", "data de expedicao", "separacao", "carteira", "janela de descarga".
   Estes sao conceitos de logistica generica, nao conhecimento tacito.
2. Fatos pontuais: "NF 12345 era da empresa 3" ou "endereco do pedido VCD267 era Guarulhos"
   sao especificos de UM caso. NAO extraia — morrem no primeiro uso.
3. Perfis de usuario minimos: "Rafael eh administrador" ou "Edson eh analista comercial"
   sao informacoes de Nivel 1 (lookup na tabela usuarios). NAO extraia.
4. Termos do sistema: nomes de tabelas, campos, modelos ORM. Estao no codigo. NAO extraia.

RACIOCINIO PRE-EXTRACAO (aplique antes de incluir cada item):
Antes de decidir se um item merece extracao, raciocine brevemente:
- MATERIAL: Que dados/eventos concretos aconteceram? (fatos da sessao)
- FORMAL: Qual padrao de conhecimento isto representa? (protocolo/armadilha/heuristica)
- EFICIENTE: Que mecanismo CAUSOU esta situacao? (por que aconteceu)
- FINAL: Que comportamento futuro esta memoria MUDARIA? (prescricao)
Se FINAL estiver vazio (a memoria nao mudaria nenhum comportamento), NAO extraia.
Inclua o raciocinio brevemente no campo "descricao" — ele enriquece a prescricao.

RESPONDA APENAS JSON VALIDO, sem markdown.""")

    return "".join(parts)


# System prompt estatico — inicializado na primeira chamada e cacheado
_KNOWLEDGE_EXTRACTION_PROMPT_CACHE: str | None = None


def _get_extraction_prompt() -> str:
    """Retorna o prompt de extracao (lazy-init + cache)."""
    global _KNOWLEDGE_EXTRACTION_PROMPT_CACHE
    if _KNOWLEDGE_EXTRACTION_PROMPT_CACHE is None:
        _KNOWLEDGE_EXTRACTION_PROMPT_CACHE = _build_extraction_prompt()
    return _KNOWLEDGE_EXTRACTION_PROMPT_CACHE


def _format_messages_for_extraction(messages: list[dict]) -> str:
    """
    Formata TODAS as mensagens da sessao para o prompt de extracao.

    Usa contexto completo — Sonnet suporta 200K tokens.
    Per-message: trunca a 3000 chars (cobre 99.9% das mensagens reais).
    Safety cap: 40K chars total para edge cases extremos (sessoes muito longas).
    Se over-budget: primeiras 2 msgs + ultimas N que caibam.
    """
    MAX_PER_MESSAGE_CHARS = 3000
    TOTAL_SAFETY_CAP = 40_000

    lines = []
    total_chars = 0

    for msg in messages:
        role = msg.get('role', 'unknown').upper()
        content = msg.get('content', '')
        # Truncar mensagens individuais muito longas
        if len(content) > MAX_PER_MESSAGE_CHARS:
            content = content[:MAX_PER_MESSAGE_CHARS] + '...'
        line = f"[{role}]: {content}"
        lines.append(line)
        total_chars += len(line)

    # Se dentro do safety cap, retornar tudo
    if total_chars <= TOTAL_SAFETY_CAP:
        return "\n\n".join(lines)

    # Over-budget: primeiras 2 msgs + ultimas N que caibam em TOTAL_SAFETY_CAP
    header_lines = lines[:2]
    header_chars = sum(len(line) for line in header_lines)
    remaining_budget = TOTAL_SAFETY_CAP - header_chars - 50  # 50 chars para separador

    tail_lines = []
    tail_chars = 0
    for line in reversed(lines[2:]):
        if tail_chars + len(line) > remaining_budget:
            break
        tail_lines.insert(0, line)
        tail_chars += len(line)

    return "\n\n".join(
        header_lines + ["[... mensagens intermediarias omitidas ...]"] + tail_lines
    )


def _slugify(text: str, max_len: int = 60) -> str:
    """Converte texto para slug seguro para path de memoria.

    Trunca em word boundary (ultimo hifen) em vez de cortar no meio da palavra.
    """
    import unicodedata
    # Remove acentos
    nfkd = unicodedata.normalize('NFKD', text)
    ascii_text = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Converte para lowercase e substitui nao-alfanumericos por hifen
    slug = re.sub(r'[^a-z0-9]+', '-', ascii_text.lower()).strip('-')
    if len(slug) <= max_len:
        return slug
    # Truncar em word boundary
    truncated = slug[:max_len]
    last_sep = truncated.rfind('-')
    if last_sep > max_len // 2:
        return truncated[:last_sep]
    return truncated


def _build_knowledge_path(
    tipo: str,
    dominio: str,
    titulo: str = '',
    descricao: str = '',
) -> str:
    """Constroi path hierarquico para memoria.

    Formato: /memories/empresa/{tipo_subdir}/{dominio}/{slug-do-titulo}.xml

    Usa titulo (gerado pelo Sonnet) como fonte primaria do slug.
    Fallback para descricao se titulo estiver vazio.

    Exemplos:
        - /memories/empresa/protocolos/recebimento/diagnostico-nf-ausente-odoo.xml
        - /memories/empresa/armadilhas/financeiro/update-frete-nao-recalcula-margem.xml
        - /memories/empresa/heuristicas/recebimento/fornecedor-cnpj-secundario-match.xml
    """
    # 3 tipos operacionais (substitui 5 epistemologicos)
    _TIPO_TO_SUBDIR = {
        "protocolo": "protocolos",
        "armadilha": "armadilhas",
        "heuristica": "heuristicas",
        # Backward-compat: tipos legados mapeados
        "procedimental": "protocolos",
        "conceitual": "heuristicas",
        "condicional": "armadilhas",
        "causal": "armadilhas",
        "relacional": "heuristicas",
    }
    subdir = _TIPO_TO_SUBDIR.get(tipo, "protocolos")
    if dominio:
        subdir = f"{subdir}/{dominio}"

    # Titulo eh fonte primaria do slug (gerado pelo Sonnet com 4-10 palavras)
    slug_source = titulo.strip() if titulo else descricao[:80]
    slug = _slugify(slug_source)
    if not slug:
        slug = _slugify(descricao[:80])
    if not slug:
        return ""
    return f"/memories/empresa/{subdir}/{slug}.xml"


def _save_empresa_memory(
    path: str,
    content: str,
    created_by: int,
) -> bool:
    """
    Salva memoria empresa (user_id=0) com escopo e auditoria.

    Returns:
        True se criou/atualizou, False se erro
    """
    try:
        from ..models import AgentMemory
        from app import db
        from app.utils.timezone import agora_utc_naive

        existing = AgentMemory.get_by_path(0, path)
        if existing:
            # Atualizar se conteudo mudou
            if existing.content != content:
                existing.content = content
                existing.updated_at = agora_utc_naive()
                existing.created_by = created_by
        else:
            # Verificar duplicata semantica ANTES de criar
            # created_by (NÃO 0) para cross-namespace dedup:
            # Checa [created_by, 0] → detecta duplicata pessoal↔empresa.
            try:
                from ..tools.memory_mcp_tool import _check_memory_duplicate
                dup_path = _check_memory_duplicate(
                    created_by or 0, content, current_path=path
                )
                if dup_path:
                    logger.info(
                        f"[KNOWLEDGE_EXTRACTION] Dedup: '{path}' similar a '{dup_path}', skipping"
                    )
                    return False
            except Exception:
                pass  # Se dedup falhar, continuar salvando

            mem = AgentMemory.create_file(0, path, content)
            mem.escopo = 'empresa'
            mem.created_by = created_by
            # Calcular importance pelo conteúdo (mesma lógica de save_memory)
            # em vez de hardcodar — threshold de imunidade é >= 0.7
            try:
                from ..tools.memory_mcp_tool import _calculate_importance_score
                mem.importance_score = _calculate_importance_score(path, content)
            except Exception:
                mem.importance_score = 0.5  # Fallback: base score (cold-eligible)
            mem.category = 'structural'  # Termos e regras mudam lentamente

        db.session.commit()

        # Best-effort: gerar embedding + KG extraction
        try:
            from app.embeddings.config import MEMORY_SEMANTIC_SEARCH, MEMORY_KNOWLEDGE_GRAPH
            haiku_entities, haiku_relations = [], []

            if MEMORY_SEMANTIC_SEARCH:
                from ..tools.memory_mcp_tool import _embed_memory_best_effort
                haiku_entities, haiku_relations = _embed_memory_best_effort(0, path, content)

            if MEMORY_KNOWLEDGE_GRAPH:
                from ..services.knowledge_graph_service import extract_and_link_entities
                mem_for_kg = existing or AgentMemory.get_by_path(0, path)
                if mem_for_kg:
                    extract_and_link_entities(
                        0, mem_for_kg.id, content,
                        haiku_entities=haiku_entities,
                        haiku_relations=haiku_relations,
                    )
        except Exception as e:
            logger.debug(f"[KNOWLEDGE_EXTRACTION] Embed/KG falhou (ignorado): {e}")

        return True

    except Exception as e:
        logger.warning(f"[KNOWLEDGE_EXTRACTION] Erro ao salvar {path}: {e}")
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
        return False


def _save_extracted_knowledge(
    knowledge: dict,
    created_by: int,
) -> dict:
    """
    Salva conhecimento extraido como memorias empresa (user_id=0).

    CAPDo v3.0: Novo formato com 6 dimensoes + filtro de valor.
    Compativel com formato legado (term_definitions, business_rules, etc.)
    para backward-compatibility durante transicao.

    Args:
        knowledge: Dict com "conhecimentos" (novo) ou campos legados
        created_by: ID do usuario que originou o conhecimento

    Returns:
        Dict com contadores {saved, filtered, enriched}
    """
    counts = {'saved': 0, 'filtered': 0, 'enriched': 0}

    # ── Novo formato CAPDo v3.0 ──
    conhecimentos = knowledge.get('conhecimentos', [])
    if conhecimentos:
        return _save_conhecimentos_v3(conhecimentos, created_by, counts)

    # ── Fallback: formato legado (backward-compatible) ──
    return _save_conhecimentos_legado(knowledge, created_by, counts)


def _save_conhecimentos_v3(
    conhecimentos: list[dict],
    created_by: int,
    counts: dict,
) -> dict:
    """Salva conhecimentos no novo formato com titulo + tipo + nivel + criterios.

    Filtro de valor:
    - "prescricao" vazia → NAO salvar
    - tipo invalido → NAO salvar
    - nivel < 3 → NAO salvar (Niveis 1-2 sao lookups)
    """
    _TIPOS_VALIDOS = {'protocolo', 'armadilha', 'heuristica'}

    for item in conhecimentos:
        titulo = item.get('titulo', '').strip()
        tipo = item.get('tipo', '').strip()
        nivel = item.get('nivel', 0)
        dominio = item.get('dominio', '').strip()
        criterios = item.get('criterios_atendidos', [])
        descricao = item.get('descricao', '').strip()
        prescricao = item.get('prescricao', '').strip()

        # ── Backward-compat: aceitar campo legado tipo_conhecimento ──
        if not tipo and item.get('tipo_conhecimento'):
            tipo = item['tipo_conhecimento'].strip()

        # ── Filtro de valor ──
        if not descricao:
            counts['filtered'] += 1
            continue

        if not prescricao or len(prescricao) < 10:
            logger.debug(
                f"[KNOWLEDGE_EXTRACTION] Filtrado (sem prescricao): {descricao[:60]}"
            )
            counts['filtered'] += 1
            continue

        if tipo not in _TIPOS_VALIDOS:
            # Tentar mapear tipos legados
            _LEGACY_MAP = {
                'procedimental': 'protocolo',
                'conceitual': 'heuristica',
                'condicional': 'armadilha',
                'causal': 'armadilha',
                'relacional': 'heuristica',
            }
            tipo = _LEGACY_MAP.get(tipo, 'protocolo')

        if isinstance(nivel, (int, float)) and nivel < 3 and nivel > 0:
            logger.debug(
                f"[KNOWLEDGE_EXTRACTION] Filtrado (nivel {nivel} < 3): {descricao[:60]}"
            )
            counts['filtered'] += 1
            continue

        if not dominio:
            dominio = "geral"

        # ── Construir path hierarquico (titulo como fonte primaria do slug) ──
        path = _build_knowledge_path(tipo, dominio, titulo=titulo, descricao=descricao)
        if not path:
            counts['filtered'] += 1
            continue

        # ── Construir XML enriquecido (novo formato) ──
        nivel_str = str(int(nivel)) if isinstance(nivel, (int, float)) and nivel >= 3 else "3"
        criterios_str = ",".join(str(c) for c in criterios) if criterios else ""
        content = (
            f'<conhecimento tipo="{_xml_escape(tipo)}" '
            f'nivel="{nivel_str}" '
            f'dominio="{_xml_escape(dominio)}">'
            f'\n  <titulo>{_xml_escape(titulo)}</titulo>'
            f'\n  <descricao>{_xml_escape(descricao)}</descricao>'
            f'\n  <prescricao>{_xml_escape(prescricao)}</prescricao>'
            f'\n  <criterios>{criterios_str}</criterios>'
            f'\n</conhecimento>'
        )

        # ── Tentar enriquecer memoria existente antes de criar nova ──
        enriched = _try_enrich_existing(path, content, created_by, descricao)
        if enriched:
            counts['enriched'] += 1
        elif _save_empresa_memory(path, content, created_by):
            counts['saved'] += 1
        # Se dedup bloqueou, nenhum contador incrementa (esperado)

    return counts


def _save_conhecimentos_legado(
    knowledge: dict,
    created_by: int,
    counts: dict,
) -> dict:
    """Fallback: converte formato legado para novo formato e salva.

    Mantido para backward-compatibility durante transicao.
    Mapeamento:
    - term_definitions → DESCARTADO (Nivel 1-2 — definicoes triviais, LLM ja sabe)
      Auditoria 15/03/2026: 15+ termos injetados centenas de vezes sem nunca serem
      efetivos. Definicoes como "cross-docking", "D+2", "lote" gastam tokens sem valor.
    - role_identifications → descartado (Nivel 1 — lookup de pessoa)
    - business_rules → armadilha, nivel 4
    - corrections → armadilha, nivel 4
    """
    conhecimentos_convertidos = []

    # term_definitions DESCARTADO — Nivel 1-2 (lookup/composicao)
    # Definicoes de termos sao informacao de treinamento do LLM, nao
    # conhecimento tacito da Nacom. A auditoria mostrou effective_count=0
    # para todos os termos, mesmo com centenas de injecoes.
    skipped_terms = len(knowledge.get('term_definitions', []))
    if skipped_terms > 0:
        logger.debug(
            f"[KNOWLEDGE_EXTRACTION] Descartando {skipped_terms} term_definitions "
            f"(Nivel 1-2, nao geram conhecimento tacito)"
        )

    # role_identifications descartado — Nivel 1 (lookup de pessoa)
    # Nao gera conhecimento tacito util.

    for item in knowledge.get('business_rules', []):
        regra = item.get('regra', '').strip()
        contexto = item.get('contexto', '').strip()
        if not regra:
            continue
        conhecimentos_convertidos.append({
            'titulo': regra[:60],
            'tipo': 'armadilha',
            'nivel': 4,
            'dominio': '',
            'criterios_atendidos': [2, 3],
            'descricao': regra,
            'prescricao': f'Quando a situacao envolver: {contexto or "contexto geral"}, '
                          f'aplicar a regra: {regra}',
        })

    for item in knowledge.get('corrections', []):
        errado = item.get('errado', '').strip()
        correto = item.get('correto', '').strip()
        contexto = item.get('contexto', '').strip()
        if not errado or not correto:
            continue
        conhecimentos_convertidos.append({
            'titulo': f'Correcao: {correto[:50]}',
            'tipo': 'armadilha',
            'nivel': 4,
            'dominio': '',
            'criterios_atendidos': [2, 4],
            'descricao': f'Errado: {errado}. Correto: {correto}',
            'prescricao': f'Quando a situacao envolver {contexto or "este tema"}, '
                          f'NUNCA usar "{errado[:40]}" — o correto eh "{correto[:40]}"',
        })

    if conhecimentos_convertidos:
        return _save_conhecimentos_v3(conhecimentos_convertidos, created_by, counts)

    return counts


def _find_similar_empresa_memory(descricao: str, current_path: str):
    """Busca memoria empresa semanticamente similar via dedup_embedding (threshold 0.80).

    Returns:
        AgentMemory ou None se nao encontrou similar.
    """
    try:
        from app.embeddings.config import MEMORY_SEMANTIC_SEARCH, EMBEDDINGS_ENABLED
        if not EMBEDDINGS_ENABLED or not MEMORY_SEMANTIC_SEARCH:
            return None

        from app.embeddings.service import EmbeddingService
        from app import db
        from sqlalchemy import text as sql_text
        from ..models import AgentMemory
        from .knowledge_graph_service import clean_for_comparison

        svc = EmbeddingService()
        clean_content = clean_for_comparison(descricao)
        if len(clean_content) < 10:
            return None

        query_embedding = svc.embed_texts([clean_content], input_type="document")[0]
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        svc._enable_iterative_scan()

        result = db.session.execute(sql_text("""
            SELECT
                ame.path,
                1 - (ame.dedup_embedding <=> CAST(:query AS vector)) AS similarity
            FROM agent_memory_embeddings ame
            JOIN agent_memories am ON am.user_id = ame.user_id AND am.path = ame.path
            WHERE ame.user_id = 0
              AND ame.dedup_embedding IS NOT NULL
              AND ame.path != :current_path
              AND am.is_directory = false
            ORDER BY ame.dedup_embedding <=> CAST(:query AS vector)
            LIMIT 1
        """), {
            "query": embedding_str,
            "current_path": current_path or '',
        })

        row = result.fetchone()
        if row and float(row.similarity) >= 0.80:
            logger.info(
                f"[KNOWLEDGE_EXTRACTION] Similar encontrado: "
                f"{row.path} (sim={float(row.similarity):.3f})"
            )
            return AgentMemory.get_by_path(0, row.path)

        return None
    except Exception as e:
        logger.debug(f"[KNOWLEDGE_EXTRACTION] Busca similar falhou: {e}")
        return None


def _try_enrich_existing(
    path: str,
    new_content: str,
    created_by: int,
    descricao: str,
) -> bool:
    """Tenta enriquecer memoria existente em vez de criar duplicata.

    2 camadas de busca:
    1. Path exato (mesmo slug = mesmo assunto)
    2. Embedding semantico (threshold 0.80) — encontra memorias sobre
       o mesmo tema mesmo com titulo/path diferente

    Returns:
        True se enriqueceu memoria existente, False se nao encontrou similar.
    """
    try:
        from ..models import AgentMemory
        from app import db

        # Camada 1: path exato
        existing = AgentMemory.get_by_path(0, path)

        # Camada 2: busca semantica (se path exato nao encontrou)
        if not existing:
            existing = _find_similar_empresa_memory(descricao, path)

        if not existing:
            return False

        # Se conteudo identico, nao precisa fazer nada
        if existing.content == new_content:
            return True

        # Enriquecer: manter conteudo existente e adicionar novo contexto
        # Nao substituir — agregar informacao
        from .knowledge_graph_service import clean_for_comparison
        words_old = set(clean_for_comparison(existing.content).lower().split())
        words_new = set(clean_for_comparison(new_content).lower().split())
        min_size = min(len(words_old), len(words_new))
        overlap = len(words_old & words_new) / min_size if min_size > 0 else 0

        if overlap > 0.80:
            # Conteudo muito similar — nao vale enriquecer
            return True

        # Enriquecer com novo contexto (append, nao replace)
        enriched = (
            f"{existing.content}\n"
            f"<!-- Enriquecido em {agora_utc_naive().strftime('%Y-%m-%d')} -->\n"
            f"{new_content}"
        )

        # Limite de tamanho para nao crescer indefinidamente
        if len(enriched) > 4000:
            logger.debug(
                f"[KNOWLEDGE_EXTRACTION] Memoria {path} ja muito longa, "
                f"nao enriquecendo ({len(enriched)} chars)"
            )
            return False

        existing.content = enriched
        existing.updated_at = agora_utc_naive()
        existing.created_by = created_by
        db.session.commit()

        logger.info(f"[KNOWLEDGE_EXTRACTION] Enriquecido: {existing.path}")
        return True

    except Exception as e:
        logger.debug(f"[KNOWLEDGE_EXTRACTION] Enriquecimento falhou: {e}")
        return False


def _get_existing_titles() -> str:
    """Consulta titulos de memorias empresa existentes, agrupados por tipo/dominio.

    Retorna string formatada para injecao no prompt de extracao.
    Best-effort: retorna string vazia se falhar.
    """
    try:
        from ..models import AgentMemory

        paths = AgentMemory.query.filter(
            AgentMemory.user_id == 0,
            AgentMemory.is_directory == False,  # noqa: E712
        ).with_entities(AgentMemory.path).all()

        # Agrupar por tipo/dominio, extrair slugs como titulos legiveis
        grouped: dict[str, list[str]] = {}
        for (path,) in paths:
            if not path or '/memories/empresa/' not in path:
                continue
            # /memories/empresa/{tipo}/{dominio}/{slug}.xml
            relative = path.replace('/memories/empresa/', '')
            parts = relative.rsplit('/', 1)
            if len(parts) == 2:
                prefix, filename = parts
                slug = filename.replace('.xml', '')
                title = slug.replace('-', ' ')
                grouped.setdefault(prefix, []).append(f'"{title}"')

        if not grouped:
            return ""

        lines = [
            "TITULOS EXISTENTES (reutilize se seu conhecimento for sobre o mesmo tema):"
        ]
        for prefix in sorted(grouped.keys()):
            titles = ", ".join(sorted(grouped[prefix]))
            lines.append(f"  {prefix}: {titles}")

        return "\n".join(lines)
    except Exception as e:
        logger.debug(f"[KNOWLEDGE_EXTRACTION] Erro ao buscar titulos: {e}")
        return ""


def extrair_conhecimento_sessao(
    app,
    user_id: int,
    session_messages: list[dict],
) -> bool:
    """
    Extrai conhecimento organizacional de TODAS as mensagens de uma sessao via Sonnet.

    Funcao principal chamada por routes.py em daemon thread apos cada exchange.
    Rede de seguranca: captura o que o agente NAO salvou via save_memory.

    Fluxo:
    1. Formata mensagens da sessao
    2. Consulta titulos de memorias empresa existentes (para reutilizacao)
    3. Envia ao Sonnet com prompt contextualizado (briefing + taxonomia + criterios)
    4. Salva conhecimento extraido como memorias empresa

    Args:
        app: Flask app
        user_id: ID do usuario (sera o created_by)
        session_messages: Lista de mensagens da sessao

    Returns:
        True se extraiu e salvou algo, False caso contrario
    """
    if not session_messages or len(session_messages) < 2:
        return False

    try:
        client = _get_anthropic_client()
        formatted = _format_messages_for_extraction(session_messages)
        extraction_prompt = _get_extraction_prompt()

        # Injetar titulos existentes para reutilizacao (dynamic, nao cacheado)
        existing_titles = ""
        try:
            with app.app_context():
                existing_titles = _get_existing_titles()
        except Exception:
            pass  # Best-effort

        # Construir mensagem do usuario com titulos + conversa
        user_parts = []
        if existing_titles:
            user_parts.append(f"<titulos_existentes>\n{existing_titles}\n</titulos_existentes>\n\n")
        user_parts.append(f"<conversa>\n{formatted}\n</conversa>")
        user_content = "".join(user_parts)

        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=2000,
            system=[{
                "type": "text",
                "text": extraction_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": user_content,
            }],
        )

        result_text = response.content[0].text.strip()
        knowledge = _parse_json_response(result_text, user_id)

        if not knowledge:
            return False

        # Verificar novo formato (conhecimentos) ou legado
        total_items = len(knowledge.get('conhecimentos', []))
        if total_items == 0:
            # Fallback: verificar formato legado
            total_items = sum(
                len(knowledge.get(k, []))
                for k in ('term_definitions', 'role_identifications',
                           'business_rules', 'corrections')
            )

        if total_items == 0:
            logger.debug(
                f"[KNOWLEDGE_EXTRACTION] Nenhum conhecimento extraido para usuario {user_id} "
                f"({response.usage.input_tokens}+{response.usage.output_tokens} tokens)"
            )
            return False

        # Salvar como memorias empresa
        with app.app_context():
            counts = _save_extracted_knowledge(
                knowledge=knowledge,
                created_by=user_id,
            )

        logger.info(
            f"[KNOWLEDGE_EXTRACTION] Usuario {user_id}: "
            f"{counts} "
            f"({response.usage.input_tokens}+{response.usage.output_tokens} tokens)"
        )
        return counts.get('saved', 0) + counts.get('enriched', 0) > 0

    except Exception as e:
        logger.warning(f"[KNOWLEDGE_EXTRACTION] Erro para usuario {user_id}: {e}")
        return False


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
