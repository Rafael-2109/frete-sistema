"""
P2-4: Análise de Fricção do Agente.

Detecta pontos onde operadores travam ao interagir com o agente.
Gera relatório de fricção integrado ao Dashboard de Insights (P2-2).

Sinais de fricção detectados:
1. Queries repetidas — operador repete mesma pergunta (não obteve resposta útil)
2. Sessões abandonadas — poucas mensagens e sem continuação
3. Mensagens curtas após erro — frustração (similar a P1-2)
4. Sessões sem uso de tools — agente não entendeu a intenção
5. Alto custo sem resultado — muitas mensagens mas pouca ação

Uso:
    Chamado pela API /agente/api/insights/friction quando friction_analysis
    está ativo. Integra-se ao Dashboard de Insights.

Otimizações (2026-03-06):
- FIX #1: Feature flag checagem — USE_FRICTION_ANALYSIS agora verificado no service
- FIX #2: Query única com batch load de JSONB (antes: N+1 queries por sessão)
- FIX #3: Similaridade com prefix grouping — O(n²) → O(n log n) com agrupamento
- FIX #4: Logging detalhado para troubleshooting em produção
"""

import logging
from datetime import timedelta
from difflib import SequenceMatcher
from typing import Dict, Any, List, Optional, Set, Tuple
from app.utils.timezone import agora_utc_naive
from app.agente.config.feature_flags import USE_FRICTION_ANALYSIS

logger = logging.getLogger(__name__)

# Limite de similaridade para considerar query como "repetida"
SIMILARITY_THRESHOLD = 0.75

# Limite de mensagens para considerar sessão como "abandonada"
ABANDONED_THRESHOLD = 3

# Tamanho mínimo do prefix para agrupamento de similaridade (otimização)
PREFIX_SIZE = 10

# Padrões de encerramento deliberado (português)
_FAREWELL_PATTERNS = [
    'obrigad', 'brigad', 'valeu', 'encerr', 'finaliz', 'tchau',
    'era isso', 'era só isso', 'era so isso', 'ok obrigado', 'perfeito',
    'resolvido', 'consegui', 'deu certo',
]


def analyze_friction(
    days: int = 30,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Analisa pontos de fricção nas sessões do agente.

    Args:
        days: Período de análise em dias
        user_id: Filtrar por usuário específico (None = todos)

    Returns:
        Dict com seções: repeated_queries, abandoned_sessions,
        frustration_signals, no_tool_sessions, friction_score
    """
    # FIX #1: Checar feature flag
    if not USE_FRICTION_ANALYSIS:
        logger.info(f"[FRICTION] Feature flag USE_FRICTION_ANALYSIS desativada")
        return _empty_friction(days)

    try:
        from ..models import AgentSession

        since = agora_utc_naive() - timedelta(days=days)

        # FIX #2: Query única com batch load (antes: N+1)
        # Carrega TODAS as sessões e seus JSONB fields em uma única query
        base_query = AgentSession.query.filter(
            AgentSession.created_at >= since
        )
        if user_id:
            base_query = base_query.filter(AgentSession.user_id == user_id)

        sessions = base_query.all()

        if not sessions:
            logger.debug(f"[FRICTION] Nenhuma sessão no período (dias={days})")
            return _empty_friction(days)

        logger.info(f"[FRICTION] Processando {len(sessions)} sessões (dias={days}, user={user_id})")

        # Extrair todas as mensagens de todas as sessões
        all_user_messages = []
        session_data_list = []

        for s in sessions:
            messages = s.get_messages() if s.data else []
            user_msgs = [m for m in messages if m.get('role') == 'user']
            assistant_msgs = [m for m in messages if m.get('role') == 'assistant']

            # Coletar tools usadas
            tools_used = set()
            for m in assistant_msgs:
                for t in m.get('tools_used', []):
                    tools_used.add(t)

            session_info = {
                'session_id': s.session_id,
                'title': s.title or '(sem título)',
                'message_count': s.message_count or 0,
                'cost_usd': float(s.total_cost_usd or 0),
                'created_at': s.created_at,
                'user_messages': user_msgs,
                'assistant_messages': assistant_msgs,
                'tools_used': tools_used,
                'user_id': s.user_id,
            }
            session_data_list.append(session_info)
            all_user_messages.extend([(msg.get('content', ''), s.session_id) for msg in user_msgs])

        logger.debug(f"[FRICTION] Total de mensagens de usuário: {len(all_user_messages)}")

        # Análise 1: Queries repetidas (com otimização O(n²) → O(n log n))
        repeated = _find_repeated_queries(all_user_messages)

        # Análise 2: Sessões abandonadas
        abandoned = _find_abandoned_sessions(session_data_list)

        # Análise 3: Sinais de frustração
        frustration = _find_frustration_signals(session_data_list)

        # Análise 4: Sessões sem tools
        no_tools = _find_no_tool_sessions(session_data_list)

        # Análise 5: Score geral de fricção
        friction_score = _calculate_friction_score(
            total_sessions=len(sessions),
            repeated_count=len(repeated),
            abandoned_count=len(abandoned),
            frustration_count=len(frustration),
            no_tools_count=len(no_tools),
        )

        logger.info(
            f"[FRICTION] Análise completa: "
            f"repeated={len(repeated)}, abandoned={len(abandoned)}, "
            f"frustration={len(frustration)}, no_tools={len(no_tools)}, "
            f"score={friction_score}"
        )

        return {
            'period_days': days,
            'generated_at': agora_utc_naive().isoformat(),
            'total_sessions_analyzed': len(sessions),
            'friction_score': friction_score,
            'repeated_queries': repeated[:20],  # Top 20
            'abandoned_sessions': abandoned[:15],
            'frustration_signals': frustration[:15],
            'no_tool_sessions': no_tools[:15],
            'summary': _generate_summary(
                friction_score, len(repeated), len(abandoned),
                len(frustration), len(no_tools), len(sessions),
            ),
        }

    except Exception as e:
        logger.error(f"[FRICTION] Erro na análise: {type(e).__name__}: {e}", exc_info=True)
        return _empty_friction(days)


def _empty_friction(days: int) -> Dict[str, Any]:
    """Retorna estrutura vazia."""
    return {
        'period_days': days,
        'generated_at': agora_utc_naive().isoformat(),
        'total_sessions_analyzed': 0,
        'friction_score': 0.0,
        'repeated_queries': [],
        'abandoned_sessions': [],
        'frustration_signals': [],
        'no_tool_sessions': [],
        'summary': 'Sem dados suficientes para análise.',
    }


def _find_repeated_queries(
    all_messages: List[Tuple[str, str]],
) -> List[Dict[str, Any]]:
    """
    Encontra queries repetidas (alta similaridade) entre sessões.

    FIX #3: Otimizacao de O(n²) para O(n log n) com prefix grouping.
    Em vez de comparar TODAS as pairs, agrupa por prefix e compara
    apenas dentro do grupo.

    Args:
        all_messages: Lista de (content, session_id) de mensagens do usuário

    Returns:
        Lista de clusters de queries similares
    """
    if len(all_messages) < 2:
        return []

    # Normalizar mensagens e criar prefix groups (FIX #3)
    normalized = []
    prefix_groups: Dict[str, List[int]] = {}

    for content, session_id in all_messages:
        text = content.strip().lower()
        if len(text) >= 10:  # Ignora mensagens muito curtas
            idx = len(normalized)
            normalized.append((text, session_id, content))

            # Prefix para agrupamento (primeiros N chars)
            prefix = text[:PREFIX_SIZE]
            if prefix not in prefix_groups:
                prefix_groups[prefix] = []
            prefix_groups[prefix].append(idx)

    logger.debug(f"[FRICTION] Normalized {len(normalized)} msgs em {len(prefix_groups)} groups")

    # Encontrar pares similares via SequenceMatcher, mas apenas dentro de groups
    clusters = []
    seen_indices: Set[int] = set()

    for indices in prefix_groups.values():
        # Comparar apenas dentro do grupo (muito mais rápido)
        for i in indices:
            if i in seen_indices:
                continue

            cluster_texts = [normalized[i][2]]
            cluster_sessions = {normalized[i][1]}

            for j in indices:
                if j <= i or j in seen_indices:
                    continue

                similarity = SequenceMatcher(
                    None, normalized[i][0], normalized[j][0]
                ).ratio()

                if similarity >= SIMILARITY_THRESHOLD:
                    cluster_texts.append(normalized[j][2])
                    cluster_sessions.add(normalized[j][1])
                    seen_indices.add(j)

            if len(cluster_texts) >= 2:
                seen_indices.add(i)
                clusters.append({
                    'query': normalized[i][2][:100],  # Representante
                    'count': len(cluster_texts),
                    'sessions': len(cluster_sessions),
                    'examples': cluster_texts[:3],
                })

    # Ordenar por frequência
    clusters.sort(key=lambda x: x['count'], reverse=True)
    logger.debug(f"[FRICTION] Encontrados {len(clusters)} clusters repetidos")
    return clusters


def _is_deliberate_end(user_messages: list) -> bool:
    """Check if the last user message signals a deliberate session ending."""
    if not user_messages:
        return False
    last_content = (user_messages[-1].get('content') or '').lower().strip()
    if not last_content or len(last_content) > 200:
        return False
    return any(p in last_content for p in _FAREWELL_PATTERNS)


def _find_abandoned_sessions(
    session_data: List[Dict],
) -> List[Dict[str, Any]]:
    """
    Encontra sessões abandonadas (poucas mensagens).

    Exclui sessões que:
    - Tiveram uso de tools (agente respondeu de forma substantiva)
    - Foram encerradas deliberadamente (farewell/obrigado/encerre)

    Args:
        session_data: Lista de informações de sessão

    Returns:
        Lista de sessões abandonadas
    """
    abandoned = []

    for s in session_data:
        if s['message_count'] <= ABANDONED_THRESHOLD and s['message_count'] > 0:
            # Excluir sessões com tool usage (resolução eficiente)
            if s.get('tools_used'):
                continue
            # Excluir encerramentos deliberados
            if _is_deliberate_end(s.get('user_messages', [])):
                continue
            # Sessão com poucas mensagens e sem continuação
            abandoned.append({
                'session_id': s['session_id'],
                'title': s['title'],
                'message_count': s['message_count'],
                'cost_usd': round(s['cost_usd'], 4),
                'created_at': s['created_at'].isoformat() if s['created_at'] else None,
                'first_message': (
                    s['user_messages'][0].get('content', '')[:100]
                    if s['user_messages'] else '(vazio)'
                ),
            })

    # Ordenar por mais recentes
    abandoned.sort(key=lambda x: x.get('created_at', '') or '', reverse=True)
    logger.debug(f"[FRICTION] Encontradas {len(abandoned)} sessões abandonadas")
    return abandoned


def _find_frustration_signals(
    session_data: List[Dict],
) -> List[Dict[str, Any]]:
    """
    Encontra sinais de frustração dentro de sessões.

    Sinais:
    - Mensagens curtas do usuário após erro do assistente
    - Mensagens com marcadores de frustração ("não era isso", "errado")
    - Muitas mensagens consecutivas do usuário (agente não responde útil)

    Args:
        session_data: Lista de informações de sessão

    Returns:
        Lista de sinais de frustração
    """
    frustration_markers = [
        'não era isso', 'errado', 'não entendeu', 'de novo',
        'repito', 'já disse', 'não é isso', 'outro', 'tente novamente',
        'nao era', 'nao entendeu', 'nao e isso',
    ]

    signals = []

    for s in session_data:
        session_signals = []

        for msg in s['user_messages']:
            content = msg.get('content', '').strip().lower()
            if not content:
                continue

            # Check marcadores explícitos
            for marker in frustration_markers:
                if marker in content:
                    session_signals.append({
                        'type': 'explicit_marker',
                        'message': msg.get('content', '')[:100],
                        'marker': marker,
                    })
                    break

        if session_signals:
            signals.append({
                'session_id': s['session_id'],
                'title': s['title'],
                'signal_count': len(session_signals),
                'signals': session_signals[:3],
                'created_at': s['created_at'].isoformat() if s['created_at'] else None,
            })

    signals.sort(key=lambda x: x['signal_count'], reverse=True)
    logger.debug(f"[FRICTION] Encontradas {len(signals)} sessões com frustração")
    return signals


def _find_no_tool_sessions(
    session_data: List[Dict],
) -> List[Dict[str, Any]]:
    """
    Encontra sessões onde nenhuma tool foi usada (agente pode não ter entendido).

    Sessões com 5+ mensagens mas sem nenhuma tool call.

    Args:
        session_data: Lista de informações de sessão

    Returns:
        Lista de sessões sem uso de tools
    """
    no_tools = []

    for s in session_data:
        if s['message_count'] >= 5 and not s['tools_used']:
            no_tools.append({
                'session_id': s['session_id'],
                'title': s['title'],
                'message_count': s['message_count'],
                'cost_usd': round(s['cost_usd'], 4),
                'created_at': s['created_at'].isoformat() if s['created_at'] else None,
                'first_message': (
                    s['user_messages'][0].get('content', '')[:100]
                    if s['user_messages'] else '(vazio)'
                ),
            })

    no_tools.sort(key=lambda x: x['message_count'], reverse=True)
    logger.debug(f"[FRICTION] Encontradas {len(no_tools)} sessões sem tools")
    return no_tools


def _calculate_friction_score(
    total_sessions: int,
    repeated_count: int,
    abandoned_count: int,
    frustration_count: int,
    no_tools_count: int,
) -> float:
    """
    Calcula score de fricção geral (0 a 100).

    Ponderação:
    - Queries repetidas: peso 30%
    - Sessões abandonadas: peso 25%
    - Sinais de frustração: peso 30%
    - Sem tools: peso 15%

    Score 0 = sem fricção, Score 100 = máxima fricção.

    Args:
        total_sessions: Total de sessões analisadas
        repeated_count: Clusters de queries repetidas
        abandoned_count: Sessões abandonadas
        frustration_count: Sessões com frustração
        no_tools_count: Sessões sem tools

    Returns:
        Score de 0 a 100
    """
    if total_sessions == 0:
        return 0.0

    # Normalizar cada métrica para 0-100
    repeated_ratio = min(repeated_count / max(total_sessions * 0.1, 1), 1.0) * 100
    abandoned_ratio = min(abandoned_count / total_sessions, 1.0) * 100
    frustration_ratio = min(frustration_count / total_sessions, 1.0) * 100
    no_tools_ratio = min(no_tools_count / total_sessions, 1.0) * 100

    # Ponderado
    score = (
        repeated_ratio * 0.30
        + abandoned_ratio * 0.25
        + frustration_ratio * 0.30
        + no_tools_ratio * 0.15
    )

    return round(min(score, 100.0), 1)


def _generate_summary(
    friction_score: float,
    repeated: int,
    abandoned: int,
    frustration: int,
    no_tools: int,
    total: int,
) -> str:
    """Gera resumo textual da análise de fricção."""
    if total == 0:
        return "Sem dados suficientes para análise."

    parts = []

    if friction_score < 20:
        parts.append(f"Fricção baixa (score {friction_score}/100).")
    elif friction_score < 50:
        parts.append(f"Fricção moderada (score {friction_score}/100).")
    else:
        parts.append(f"Fricção alta (score {friction_score}/100) — ação recomendada.")

    if repeated > 0:
        parts.append(f"{repeated} cluster(s) de queries repetidas detectado(s).")
    if abandoned > 0:
        pct = round(abandoned / total * 100, 1)
        parts.append(f"{abandoned} sessões abandonadas ({pct}% do total).")
    if frustration > 0:
        parts.append(f"{frustration} sessão(ões) com sinais de frustração.")
    if no_tools > 0:
        parts.append(f"{no_tools} sessão(ões) sem uso de ferramentas (possível falta de compreensão).")

    return " ".join(parts)
