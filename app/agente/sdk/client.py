"""
Cliente do Claude Agent SDK.

Wrapper que encapsula a comunicação com a API usando o SDK oficial.
Usa query() + resume para streaming (compatível com Flask thread-per-request).

Referência: https://platform.claude.com/docs/pt-BR/agent-sdk/

ARQUITETURA (v2 — query() + resume):
- Cada request HTTP roda em Thread + asyncio.run() que DESTRÓI o event loop.
- ClaudeSDKClient precisa de event loop PERSISTENTE → corrompido entre requests.
- query() é self-contained: spawna CLI process, executa, limpa automaticamente.
- resume=sdk_session_id restaura contexto da conversa anterior (CLI carrega sessão do disco).
"""

import asyncio
import logging
import time
from typing import AsyncGenerator, Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from app.utils.timezone import agora_utc_naive

# SDK Oficial
# Ref: https://platform.claude.com/docs/pt-BR/agent-sdk/
from claude_agent_sdk import (
    query as sdk_query,  # query() standalone — self-contained, sem estado persistente
    ClaudeAgentOptions,
    ResultMessage,
    AssistantMessage,
    UserMessage,       # Contém resultados de ferramentas
    SystemMessage,     # Mensagem de sistema (init com session_id)
    ToolUseBlock,
    ToolResultBlock,   # Resultado de execução de ferramenta
    TextBlock,
    ThinkingBlock,     # FEAT-002: Extended Thinking
    # SDK 0.1.31: Error classes especializadas
    CLINotFoundError,
    ProcessError,
    CLIJSONDecodeError,
    CLIConnectionError,  # SIGTERM/process death — sibling of ProcessError
)

# SDK 0.1.46+: Task messages para observabilidade de subagentes
try:
    from claude_agent_sdk import (
        TaskStartedMessage,
        TaskProgressMessage,
        TaskNotificationMessage,
    )
    _HAS_TASK_MESSAGES = True
except ImportError:
    _HAS_TASK_MESSAGES = False

# Fallback para API direta (health check)
import anthropic
from datetime import datetime
logger = logging.getLogger('sistema_fretes')


# =====================================================================
# HELPER: Auto-injeção de memórias do usuário
# =====================================================================

_op_context_cache: Dict[int, tuple] = {}  # user_id -> (context_str, timestamp)
_OP_CONTEXT_TTL = 180  # 3 minutos — dados urgentes mudam na escala de horas


def _build_operational_context(user_id: int) -> Optional[str]:
    """
    Memory v2 — Tier 0: Contexto operacional do dia.

    Queries leves para injetar estado atual do sistema:
    - Dia da semana
    - Pedidos vencendo D+2
    - Separações pendentes
    - Conflitos de memória pendentes

    Cache com TTL de 3 min — durante uma conversa típica (5-15 min),
    pedidos urgentes e separações pendentes são estáveis.

    Retorna XML compacto (~300 chars) ou None.
    """
    # Cache hit — evita 2 queries SQL por mensagem (~100ms de latência)
    cached = _op_context_cache.get(user_id)
    if cached and (time.time() - cached[1]) < _OP_CONTEXT_TTL:
        logger.debug(f"[MEMORY_INJECT] Contexto operacional: cache hit (user_id={user_id})")
        return cached[0]

    try:
        from app import db
        from sqlalchemy import text as sql_text
        from datetime import timedelta

        now = agora_utc_naive()
        dia_semana = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo'][now.weekday()]

        parts = [f'<operational_context date="{now.strftime("%d/%m/%Y")}" dia="{dia_semana}">']

        # Pedidos vencendo D+2 (inclui atrasados — sao os MAIS urgentes)
        try:
            d2 = now + timedelta(days=2)
            r_count = db.session.execute(sql_text("""
                SELECT count(*)
                FROM carteira_principal
                WHERE qtd_saldo_produto_pedido > 0
                  AND data_entrega_pedido <= :d2
            """), {"d2": d2.date()})
            count_urgentes = r_count.scalar() or 0

            if count_urgentes > 0:
                # Top 3 por valor pendente
                r_top = db.session.execute(sql_text("""
                    SELECT raz_social_red, num_pedido,
                           SUM(qtd_saldo_produto_pedido * preco_produto_pedido) as valor_pendente
                    FROM carteira_principal
                    WHERE qtd_saldo_produto_pedido > 0
                      AND data_entrega_pedido <= :d2
                    GROUP BY raz_social_red, num_pedido
                    ORDER BY valor_pendente DESC
                    LIMIT 3
                """), {"d2": d2.date()})
                top_rows = r_top.fetchall()

                top_str = ""
                if top_rows:
                    items = []
                    for row in top_rows:
                        nome = (row[0] or "?")[:20]
                        pedido = row[1] or "?"
                        valor = row[2] or 0
                        if valor >= 1000:
                            items.append(f"{nome} R${valor / 1000:.0f}K {pedido}")
                        else:
                            items.append(f"{nome} R${valor:.0f} {pedido}")
                    top_str = f' top="{", ".join(items)}"'

                parts.append(f'<pedidos_urgentes_d2 count="{count_urgentes}"{top_str}/>')
        except Exception:
            pass

        # Separações pendentes com data mais antiga
        try:
            r = db.session.execute(sql_text("""
                SELECT count(*), MIN(criado_em)::date as oldest
                FROM separacao
                WHERE sincronizado_nf = FALSE
                  AND qtd_saldo > 0
            """))
            row = r.fetchone()
            count_sep = row[0] or 0 if row else 0
            oldest = row[1] if row else None
            if count_sep > 0:
                oldest_attr = f' oldest="{oldest}"' if oldest else ''
                parts.append(f'<separacoes_pendentes count="{count_sep}"{oldest_attr}/>')
        except Exception:
            pass

        # Memórias com conflito pendente — mostrar título (primeiros 40 chars)
        try:
            from ..models import AgentMemory
            conflict_memories = AgentMemory.query.filter_by(
                user_id=user_id,
                has_potential_conflict=True,
                is_directory=False,
            ).with_entities(
                AgentMemory.path, AgentMemory.content
            ).limit(5).all()
            if conflict_memories:
                titles = []
                for m in conflict_memories:
                    if m.content:
                        title = m.content.strip()[:40].replace('"', "'")
                        titles.append(title)
                    else:
                        titles.append(m.path.split('/')[-1])
                parts.append(
                    f'<memorias_com_conflito count="{len(conflict_memories)}" '
                    f'items="{"; ".join(titles)}"/>'
                )
        except Exception:
            pass

        parts.append('</operational_context>')

        # Só retorna se tiver conteúdo útil (mais que date/dia)
        if len(parts) > 2:  # header + footer = sem conteúdo
            result = '\n'.join(parts)
            _op_context_cache[user_id] = (result, time.time())
            return result

        _op_context_cache[user_id] = (None, time.time())
        return None

    except Exception as e:
        logger.debug(f"[MEMORY_INJECT] Contexto operacional falhou (ignorado): {e}")
        return None


def _normalize_pendencia(text: str) -> str:
    """Normaliza texto de pendência para comparação: lowercase, strip, collapse whitespace."""
    import re
    return re.sub(r'\s+', ' ', text.strip().lower())


def _build_session_window(user_id: int) -> Optional[str]:
    """
    Memory v2 — Rolling Window: últimas 5 sessões do banco.

    Query direta em agent_sessions.summary (JSONB) — sem XML intermediário.
    Cada sessão formatada como ~150 chars.

    Pendências têm lifecycle:
    - TTL automático: pendências de sessões mais antigas que PENDENCIA_TTL_DAYS são ignoradas
    - Resolução manual: pendências em /memories/system/resolved_pendencias.json são filtradas

    Returns:
        XML compacto com resumos das últimas 5 sessões ou None.
    """
    try:
        from ..models import AgentSession
        from datetime import timedelta
        import os

        ttl_days = int(os.getenv('PENDENCIA_TTL_DAYS', '7'))
        cutoff = agora_utc_naive() - timedelta(days=ttl_days)

        sessions = AgentSession.query.filter(
            AgentSession.user_id == user_id,
            AgentSession.summary.isnot(None),
        ).order_by(
            AgentSession.updated_at.desc()
        ).limit(5).all()

        if not sessions:
            return None

        parts = ['<recent_sessions count="' + str(len(sessions)) + '">']
        pendencias_all = []

        for sess in sessions:
            summary = sess.get_summary() if hasattr(sess, 'get_summary') else sess.summary
            if not summary:
                continue

            # Extrair campos do summary JSONB
            if isinstance(summary, dict):
                resumo = summary.get('resumo_geral', '')
                pendencias = summary.get('tarefas_pendentes', [])
                alertas = summary.get('alertas', [])
                data = sess.updated_at.strftime('%d/%m') if sess.updated_at else '?'

                compact = f'<session date="{data}">{resumo}'
                if alertas:
                    compact += f' alertas={len(alertas)}'
                compact += '</session>'
                parts.append(compact)

                # Acumular pendências — TTL: ignorar sessões antigas
                session_expired = sess.updated_at and sess.updated_at < cutoff
                if not session_expired:
                    for p in pendencias:
                        if isinstance(p, dict):
                            pendencias_all.append(p.get('descricao', str(p)))
                        elif isinstance(p, str):
                            pendencias_all.append(p)

        # Pendências acumuladas (dedupadas + filtro de resolvidas)
        if pendencias_all:
            unique_pend = list(dict.fromkeys(pendencias_all))[:5]  # Max 5, preserva ordem

            # Filtrar pendências já resolvidas (matching normalizado)
            resolved = _load_resolved_pendencias(user_id)
            if resolved:
                unique_pend = [p for p in unique_pend if _normalize_pendencia(p) not in resolved]

            if unique_pend:
                parts.append('<pendencias_acumuladas>')
                parts.append('  <instruction>Verifique SILENCIOSAMENTE cada item contra '
                             'evidencias (commits recentes, sessoes anteriores, memorias). '
                             'Se resolvido, chame resolve_pendencia com o texto EXATO do item. '
                             'Mencione ao usuario apenas pendencias REALMENTE pendentes.</instruction>')
                for p in unique_pend:
                    parts.append(f'  <item>{p}</item>')
                parts.append('</pendencias_acumuladas>')

        parts.append('</recent_sessions>')
        return '\n'.join(parts)

    except Exception as e:
        logger.debug(f"[MEMORY_INJECT] Session window falhou (ignorado): {e}")
        return None


def _load_resolved_pendencias(user_id: int) -> set:
    """
    Carrega pendências resolvidas de /memories/system/resolved_pendencias.json.

    Returns:
        Set de strings normalizadas com pendências resolvidas.
    """
    try:
        from ..models import AgentMemory
        import json

        mem = AgentMemory.get_by_path(user_id, '/memories/system/resolved_pendencias.json')
        if not mem or not mem.content:
            return set()

        data = json.loads(mem.content)
        if isinstance(data, list):
            return {_normalize_pendencia(item) for item in data if isinstance(item, str)}
        return set()

    except Exception:
        return set()


# Decay rates por categoria (Memory v2)
# permanent: sem decay (1.0)
# structural: lento (~60d meia-vida) → 0.9995 ^ horas
# operational: médio (~30d meia-vida) → 0.999 ^ horas
# contextual: rápido (~3d meia-vida) → 0.990 ^ horas
_CATEGORY_DECAY_RATES = {
    'permanent': 1.0,       # Sem decay — sempre 1.0
    'structural': 0.9995,   # Meia-vida ~58 dias
    'operational': 0.999,   # Meia-vida ~29 dias
    'contextual': 0.990,    # Meia-vida ~2.9 dias
}


def _calculate_category_decay(category: str, hours_since: float) -> float:
    """Calcula decay baseado na categoria da memória (Memory v2)."""
    if category == 'permanent':
        return 1.0
    rate = _CATEGORY_DECAY_RATES.get(category, 0.995)
    return rate ** hours_since


# Correction penalty (S2): cada correção reduz importance em 15%, piso 10%
_CORRECTION_PENALTY_RATE = 0.15
_CORRECTION_PENALTY_FLOOR = 0.1


def _adjust_importance_for_corrections(importance: float, correction_count: int) -> float:
    """Penaliza importance_score baseado no número de correções."""
    if correction_count <= 0:
        return importance
    factor = max(_CORRECTION_PENALTY_FLOOR, 1 - _CORRECTION_PENALTY_RATE * correction_count)
    return importance * factor


def _load_user_memories_for_context(user_id: int, prompt: str = None, model_name: str = None) -> tuple[Optional[str], list[int]]:
    """
    Carrega memórias do usuário e formata como contexto para injeção.

    Memory System v2 — Arquitetura em 4 tiers:
    - Tier 0 (SEMPRE): Contexto operacional do dia + rolling window de sessões
    - Tier 1 (SEMPRE): user.xml e preferences.xml — garante identidade/preferências
    - Tier 2 (semântica): memórias relevantes ao prompt, excluindo Tier 1
    - Tier 2b (KG): complementar via Knowledge Graph
    - Fallback: memórias mais recentes se semântica não retornar nada

    v2 changes:
    - Tier 0: operational context + session window (1B + 1C)
    - Two-pass budget selection by composite score (1D)
    - Category-aware decay rates
    - Exclude cold memories from retrieval
    - Per-tier char logging
    - Increment usage_count on injection

    Budget adaptativo (T2-2):
    - Opus: 8000 chars (~2000 tokens)
    - Sonnet: 4000 chars (~1000 tokens)
    - Haiku: 2000 chars (~500 tokens)
    - Ajustado pelo tamanho do prompt (prompts longos = budget menor)

    Args:
        user_id: ID do usuário no banco
        prompt: Prompt do usuário (para seleção semântica)
        model_name: Nome do modelo (para budget adaptativo, ex: "claude-opus-4-6")

    Returns:
        Tupla (texto XML formatado ou None, lista de IDs de memórias injetadas)
    """
    if not user_id:
        return None, []

    try:
        # Obter Flask app context
        try:
            from flask import current_app
            _ = current_app.name
            ctx = None
        except RuntimeError:
            from app import create_app
            app = create_app()
            ctx = app.app_context()

        def _load():
            from ..models import AgentMemory
            from ..config.feature_flags import MEMORY_INJECTION_MIN_SIMILARITY

            # ── Tier 0: Contexto operacional + Rolling window (Memory v2) ──
            tier0_parts = []
            tier0_chars = 0

            op_ctx = _build_operational_context(user_id)
            if op_ctx:
                tier0_parts.append(op_ctx)
                tier0_chars += len(op_ctx)

            session_window = _build_session_window(user_id)
            if session_window:
                tier0_parts.append(session_window)
                tier0_chars += len(session_window)

            # ── Tier 0b: Briefing inter-sessão (Memory v2 — 3A) ──
            try:
                from ..config.feature_flags import USE_INTERSESSION_BRIEFING
                if USE_INTERSESSION_BRIEFING:
                    from ..services.intersession_briefing import build_intersession_briefing
                    briefing = build_intersession_briefing(user_id)
                    if briefing:
                        tier0_parts.append(briefing)
                        tier0_chars += len(briefing)
            except Exception as brief_err:
                logger.debug(f"[MEMORY_INJECT] Briefing inter-sessão falhou (ignorado): {brief_err}")

            # ── Tier 1: SEMPRE injetar memórias protegidas ──
            PROTECTED_PATHS = ["/memories/user.xml", "/memories/preferences.xml"]
            protected_memories = AgentMemory.query.filter(
                AgentMemory.user_id == user_id,
                AgentMemory.path.in_(PROTECTED_PATHS),
                AgentMemory.is_directory == False,  # noqa: E712
            ).all()

            protected_ids = {m.id for m in protected_memories}

            # ── Tier 2: Busca semântica com composite scoring (QW-1 + v2 category decay) ──
            additional_memories = []
            _pass1_scores = {}  # mem.id → composite score original (com similarity)
            semantic_count = 0
            avg_similarity = 0.0
            avg_composite = 0.0
            used_fallback = False

            try:
                from app.embeddings.config import MEMORY_SEMANTIC_SEARCH

                if MEMORY_SEMANTIC_SEARCH and prompt and user_id:
                    from app.embeddings.memory_search import buscar_memorias_semantica
                    # Over-fetch: buscar 20 candidatos para re-ranking por composite score
                    resultados = buscar_memorias_semantica(
                        prompt, user_id,
                        limite=20,
                        min_similarity=MEMORY_INJECTION_MIN_SIMILARITY,
                    )

                    if resultados:
                        # Filtrar memórias protegidas (já no Tier 1)
                        filtered = [
                            r for r in resultados
                            if r['memory_id'] not in protected_ids
                        ]
                        semantic_count = len(filtered)

                        if filtered:
                            avg_similarity = sum(
                                r.get('similarity', 0) for r in filtered
                            ) / len(filtered)

                            memory_ids = [r['memory_id'] for r in filtered]
                            mem_objects = AgentMemory.query.filter(
                                AgentMemory.id.in_(memory_ids),
                                AgentMemory.is_directory == False,  # noqa: E712
                                AgentMemory.is_cold == False,  # noqa: E712 — v2: excluir cold
                            ).all()

                            # Mapear similarity por memory_id
                            # GAP 10: Preferir rerank_score (Voyage) quando disponível
                            sim_map = {
                                r['memory_id']: r.get('rerank_score', r.get('similarity', 0))
                                for r in filtered
                            }

                            # v2: Composite score com category-aware decay
                            now = agora_utc_naive()
                            scored = []
                            for mem in mem_objects:
                                similarity = sim_map.get(mem.id, 0)
                                importance = mem.importance_score if mem.importance_score is not None else 0.5
                                importance = _adjust_importance_for_corrections(importance, mem.correction_count or 0)  # S2

                                # v2: Decay por categoria
                                last_access = mem.last_accessed_at or mem.updated_at or mem.created_at
                                if last_access:
                                    hours_since = max(0, (now - last_access).total_seconds() / 3600)
                                    category = getattr(mem, 'category', 'operational') or 'operational'
                                    decay = _calculate_category_decay(category, hours_since)
                                else:
                                    decay = 0.5

                                composite = 0.3 * decay + 0.3 * importance + 0.4 * similarity
                                scored.append((mem, composite, similarity))

                            # Ordenar por composite score (desc), pegar top 10
                            scored.sort(key=lambda x: x[1], reverse=True)
                            scored = scored[:10]

                            # Preservar composite scores originais (com similarity) para PASS 2
                            _pass1_scores = {s[0].id: s[1] for s in scored}
                            additional_memories = [s[0] for s in scored]
                            if scored:
                                avg_composite = sum(s[1] for s in scored) / len(scored)

            except Exception as sem_err:
                logger.warning(
                    f"[MEMORY_INJECT] Semantic fallback to recency: {sem_err}"
                )

            # ── Tier 2b: Knowledge Graph retrieval (T3-3) ──
            graph_count = 0
            try:
                from app.embeddings.config import MEMORY_KNOWLEDGE_GRAPH
                if MEMORY_KNOWLEDGE_GRAPH and prompt and user_id:
                    from app.agente.services.knowledge_graph_service import query_graph_memories

                    # IDs já encontrados pela semântica
                    semantic_ids = {m.id for m in additional_memories} | protected_ids

                    graph_results = query_graph_memories(
                        user_id=user_id,
                        prompt=prompt,
                        exclude_memory_ids=semantic_ids,
                        limit=5,  # Complementar, não substituir
                    )

                    if graph_results:
                        graph_memory_ids = [r['memory_id'] for r in graph_results]
                        graph_sim_map = {r['memory_id']: r.get('similarity', 0.5) for r in graph_results}

                        graph_mem_objects = AgentMemory.query.filter(
                            AgentMemory.id.in_(graph_memory_ids),
                            AgentMemory.is_directory == False,  # noqa: E712
                            AgentMemory.is_cold == False,  # noqa: E712 — v2: excluir cold
                        ).all()

                        # Scoring com similarity proxy (0.5)
                        now_graph = agora_utc_naive()
                        for mem in graph_mem_objects:
                            similarity = graph_sim_map.get(mem.id, 0.5)
                            importance = mem.importance_score if mem.importance_score is not None else 0.5
                            importance = _adjust_importance_for_corrections(importance, mem.correction_count or 0)  # S2
                            last_access = mem.last_accessed_at or mem.updated_at or mem.created_at
                            if last_access:
                                hours_since = max(0, (now_graph - last_access).total_seconds() / 3600)
                                category = getattr(mem, 'category', 'operational') or 'operational'
                                decay = _calculate_category_decay(category, hours_since)
                            else:
                                decay = 0.5
                            composite = 0.3 * decay + 0.3 * importance + 0.4 * similarity
                            # Só adicionar se composite razoável
                            if composite >= 0.3:
                                _pass1_scores[mem.id] = composite
                                additional_memories.append(mem)
                                graph_count += 1

            except Exception as graph_err:
                logger.debug(f"[MEMORY_INJECT] Graph retrieval falhou (ignorado): {graph_err}")

            # ── Fallback: recência se semântica não retornou nada ──
            if not additional_memories:
                used_fallback = True
                # PRD v2.1: incluir memorias empresa (user_id=0)
                fallback_user_ids = [user_id, 0] if user_id != 0 else [0]
                fallback_query = AgentMemory.query.filter(
                    AgentMemory.user_id.in_(fallback_user_ids),
                    AgentMemory.is_directory == False,  # noqa: E712
                    AgentMemory.is_cold == False,  # noqa: E712 — v2: excluir cold
                )
                if protected_ids:
                    fallback_query = fallback_query.filter(
                        ~AgentMemory.id.in_(protected_ids)
                    )
                additional_memories = fallback_query.order_by(
                    AgentMemory.updated_at.desc()
                ).limit(15).all()

            # ── Montar resultado: Tier 0 + protegidas + relevantes ──
            all_memories = protected_memories + additional_memories

            if not all_memories and not tier0_parts:
                return None, []

            # ── QW-4 + T2-2 + v2: Budget adaptativo com two-pass selection ──
            # Budget base por modelo
            _model = (model_name or "").lower()
            if "opus" in _model:
                base_budget = 8000
            elif "haiku" in _model:
                base_budget = 2000
            else:
                base_budget = 4000  # Sonnet ou desconhecido

            # Fator de ajuste: prompts longos consomem context window, reduzir budget
            prompt_len = len(prompt) if prompt else 0
            prompt_factor = max(0.5, 1.0 - prompt_len / 10000)
            budget = int(base_budget * prompt_factor)

            # ── PASS 1: Calcular tamanhos de todos os candidatos ──
            header = (
                "<user_memories>\n"
                "<!-- Memórias persistentes do usuário — use para personalizar respostas -->\n"
            )
            footer = "</user_memories>"
            overhead = len(header) + len(footer)

            # Tier 0: sempre incluído (fora do budget de memórias)
            tier0_text = ""
            if tier0_parts:
                tier0_text = "\n".join(tier0_parts) + "\n"

            # Tier 1: protegidas sempre incluídas
            tier1_texts = []
            tier1_chars = 0
            for mem in protected_memories:
                content = (mem.content or "").strip()
                if not content:
                    continue
                mem_text = f'<memory path="{mem.path}">\n{content}\n</memory>\n'
                tier1_texts.append((mem, mem_text))
                tier1_chars += len(mem_text)

            # Budget restante para Tier 2 + 2b
            budget_remaining = budget - overhead - tier1_chars

            # Tier 2/2b: calcular tamanho de cada candidato e ordenar por composite
            tier2_candidates = []
            for mem in additional_memories:
                content = (mem.content or "").strip()
                if not content:
                    continue
                mem_text = f'<memory path="{mem.path}">\n{content}\n</memory>\n'
                # Usar composite score original do PASS 1 (inclui similarity)
                # Fallback: decay + importance (sem similarity) para memórias de fallback
                if mem.id in _pass1_scores:
                    composite = _pass1_scores[mem.id]
                else:
                    now_sel = agora_utc_naive()
                    importance = mem.importance_score if mem.importance_score is not None else 0.5
                    importance = _adjust_importance_for_corrections(importance, mem.correction_count or 0)  # S2
                    last_access = mem.last_accessed_at or mem.updated_at or mem.created_at
                    if last_access:
                        hours_since = max(0, (now_sel - last_access).total_seconds() / 3600)
                        category = getattr(mem, 'category', 'operational') or 'operational'
                        decay = _calculate_category_decay(category, hours_since)
                    else:
                        decay = 0.5
                    composite = 0.3 * decay + 0.7 * importance
                tier2_candidates.append((mem, mem_text, len(mem_text), composite))

            # ── PASS 2: Selecionar por composite score dentro do budget ──
            tier2_candidates.sort(key=lambda x: x[3], reverse=True)
            selected_tier2 = []
            tier2_chars = 0
            tier2b_chars = 0
            for mem, mem_text, mem_len, _ in tier2_candidates:
                if tier2_chars + tier2b_chars + mem_len > budget_remaining:
                    continue  # v2: SKIP em vez de BREAK — permite menor caber depois
                selected_tier2.append((mem, mem_text))
                # Distinguir tier2 vs tier2b para logging
                if mem in additional_memories[:semantic_count]:
                    tier2_chars += mem_len
                else:
                    tier2b_chars += mem_len

            # ── Montar resultado final ──
            # Memórias estáveis primeiro (maior atenção), operacional ao final
            selected_parts = [header]
            injected_mems = []

            for mem, mem_text in tier1_texts:
                selected_parts.append(mem_text)
                injected_mems.append(mem)

            for mem, mem_text in selected_tier2:
                selected_parts.append(mem_text)
                injected_mems.append(mem)

            selected_parts.append(footer)
            # Contexto operacional (tier0) APÓS memórias estáveis — menor prioridade de atenção
            if tier0_text:
                selected_parts.append(tier0_text)
            result = "".join(selected_parts)

            total_chars = len(result)
            injected_count = len(injected_mems)

            if injected_count == 0 and not tier0_text:
                return None, []  # Nenhuma memória coube no budget

            # ── v2: Atualizar last_accessed_at + usage_count para memórias injetadas ──
            injected_ids = [m.id for m in injected_mems]
            try:
                from app import db
                from sqlalchemy import text as sql_text
                if injected_ids:
                    ts = agora_utc_naive()
                    db.session.execute(sql_text("""
                        UPDATE agent_memories
                        SET last_accessed_at = :ts,
                            usage_count = usage_count + 1
                        WHERE id = ANY(:ids)
                    """), {"ids": injected_ids, "ts": ts})
                    db.session.commit()
            except Exception as e:
                logger.debug(f"[MEMORY_INJECT] last_accessed_at/usage_count update failed (ignored): {e}")

            # ── v2: Log detalhado de injeção com per-tier chars ──
            penalized_count = sum(1 for m in injected_mems if (m.correction_count or 0) > 0)  # S2
            budget_pct = round(total_chars / budget * 100) if budget > 0 else 0
            skipped_budget = len(tier2_candidates) - len(selected_tier2)
            logger.info(
                f"[MEMORY_INJECT] "
                f"user_id={user_id} | "
                f"protected={len(protected_memories)} | "
                f"semantic={semantic_count} | "
                f"graph={graph_count} | "
                f"fallback={used_fallback} | "
                f"total_injected={injected_count} | "
                f"penalized={penalized_count} | "
                f"total_chars={total_chars} | "
                f"budget={budget} | "
                f"budget_pct={budget_pct}% | "
                f"skipped_budget={skipped_budget} | "
                f"candidates_total={len(tier2_candidates)} | "
                f"model={_model or 'unknown'} | "
                f"avg_similarity={avg_similarity:.2f} | "
                f"avg_composite={avg_composite:.2f} | "
                f"tier0_chars={tier0_chars} | "
                f"tier1_chars={tier1_chars} | "
                f"tier2_chars={tier2_chars} | "
                f"tier2b_chars={tier2b_chars} | "
                f"budget_remaining={max(0, budget_remaining - tier2_chars - tier2b_chars)} | "
                f"min_similarity_threshold={MEMORY_INJECTION_MIN_SIMILARITY} | "
                f"prompt_preview={prompt[:50] if prompt else 'None'}"
            )

            return result, injected_ids

        if ctx is None:
            return _load()
        else:
            with ctx:
                return _load()

    except Exception as e:
        logger.warning(f"[MEMORY_INJECT] Erro ao carregar memórias (ignorado): {e}")
        return None, []


@dataclass
class ToolCall:
    """Representa uma chamada de ferramenta."""
    id: str
    name: str
    input: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: agora_utc_naive())


@dataclass
class StreamEvent:
    """Evento do stream de resposta."""
    type: str  # 'text', 'tool_call', 'tool_result', 'action_pending', 'done', 'error', 'init'
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Resposta completa do agente."""
    text: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    pending_action: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


@dataclass
class _StreamParseState:
    """Estado mutável compartilhado durante parsing de mensagens do SDK.

    Usado por _parse_sdk_message() para manter estado entre mensagens
    do stream. Reutilizável por ambos os paths (query() e ClaudeSDKClient).

    INVARIANTE: Todos os campos são inicializados no construtor.
    Nenhum campo depende de estado externo.
    """
    full_text: str = ""
    had_tool_between_texts: bool = False
    tool_calls: List[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    last_message_id: Optional[str] = None
    done_emitted: bool = False
    result_session_id: Optional[str] = None

    # Diagnóstico de tempo
    stream_start_time: float = field(default_factory=time.time)
    last_message_time: float = field(default_factory=time.time)
    current_tool_start_time: Optional[float] = None
    current_tool_name: Optional[str] = None
    first_message_logged: bool = False

    # Evento para sinalizar fim do stream ao prompt generator.
    # Usado APENAS no path query() (_make_streaming_prompt).
    # No path ClaudeSDKClient, é None (não necessário).
    streaming_done_event: Optional[asyncio.Event] = None


class AgentClient:
    """
    Cliente do Claude Agent SDK oficial.

    ARQUITETURA (v2 — query() + resume):
    - Usa query() standalone (self-contained, sem estado persistente)
    - Resume via sdk_session_id para manter contexto entre turnos
    - Sem SessionPool, sem locks, sem connect/disconnect
    - Skills para funcionalidades (.claude/skills/)
    - Custom Tools MCP in-process para text-to-sql
    - Callback canUseTool para permissões
    - Rastreamento de custos

    Referências:
    - https://platform.claude.com/docs/pt-BR/agent-sdk/skills
    - https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
    - https://platform.claude.com/docs/pt-BR/agent-sdk/permissions

    Uso:
        client = AgentClient()

        # Streaming com query() + resume
        async for event in client.stream_response("Sua pergunta", sdk_session_id="..."):
            if event.type == 'text':
                print(event.content, end='')
    """

    def __init__(self):
        from ..config import get_settings

        self.settings = get_settings()

        # Carrega system prompt
        self.system_prompt = self._load_system_prompt()

        # Carrega preset operacional (para USE_CUSTOM_SYSTEM_PROMPT)
        self.operational_preset = self._load_preset_operacional()

        # Cliente para health check (API direta)
        self._anthropic_client = anthropic.Anthropic(api_key=self.settings.api_key)

        # IDs de memórias injetadas no último turno (para effectiveness tracking)
        self._last_injected_memory_ids: list[int] = []

        logger.info(
            f"[AGENT_CLIENT] Inicializado | "
            f"Modelo: {self.settings.model} | "
            f"SDK: claude-agent-sdk"
        )

    def _load_system_prompt(self) -> str:
        """Carrega system prompt do arquivo."""
        try:
            with open(self.settings.system_prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(
                f"[AGENT_CLIENT] System prompt não encontrado: "
                f"{self.settings.system_prompt_path}"
            )
            return self._get_default_system_prompt()

    def _load_preset_operacional(self) -> str:
        """Carrega preset operacional do arquivo.

        Substitui o preset claude_code quando USE_CUSTOM_SYSTEM_PROMPT=true.
        Contém apenas: tool instructions, safety, environment, persistent systems.
        NÃO contém identidade dev, git, CSS, migrations.
        """
        preset_path = self.settings.operational_preset_path
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(
                    f"[AGENT_CLIENT] Preset operacional carregado: "
                    f"{preset_path} ({len(content)} chars)"
                )
                return content
        except FileNotFoundError:
            logger.warning(
                f"[AGENT_CLIENT] preset_operacional.md nao encontrado: {preset_path}"
            )
            return ""

    def _build_full_system_prompt(self, custom_instructions: str) -> str:
        """Concatena preset operacional + system_prompt formatado.

        Retorna string única que SUBSTITUI o preset claude_code.
        Economia estimada: ~3-4K tokens input por request.

        Args:
            custom_instructions: System prompt formatado (_format_system_prompt output)

        Returns:
            String completa para system_prompt (sem preset)
        """
        preset = self.operational_preset
        if not preset:
            logger.warning(
                "[AGENT_CLIENT] Preset operacional vazio — usando apenas system_prompt.md"
            )
            return custom_instructions

        return f"{preset}\n\n{custom_instructions}"

    def _get_default_system_prompt(self) -> str:
        """Retorna system prompt padrão."""
        return """Você é um assistente logístico especializado.
Ajude o usuário com consultas sobre pedidos, estoque e separações.
Use as ferramentas disponíveis para buscar dados reais do sistema.
Nunca invente informações."""

    def _extract_tool_description(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """
        FEAT-024: Extrai descrição amigável do tool_call.

        Em vez de mostrar "Read" ou "Bash", mostra uma descrição
        do que a ferramenta está fazendo, similar ao Claude Code.

        Args:
            tool_name: Nome da ferramenta (Read, Bash, Skill, etc.)
            tool_input: Input da ferramenta

        Returns:
            Descrição amigável da ação
        """
        if not tool_input:
            return tool_name

        # Mapeamento de ferramentas para descrições
        if tool_name == 'Read':
            file_path = tool_input.get('file_path', '')
            if file_path:
                # Extrai apenas o nome do arquivo
                file_name = file_path.split('/')[-1] if '/' in file_path else file_path
                return f"Lendo {file_name}"
            return "Lendo arquivo"

        elif tool_name == 'Bash':
            # Bash tem campo description explícito
            description = tool_input.get('description', '')
            if description:
                return description
            command = tool_input.get('command', '')
            if command:
                # Extrai comando principal
                cmd_parts = command.split()
                if cmd_parts:
                    main_cmd = cmd_parts[0]
                    if main_cmd == 'python':
                        return "Executando script Python"
                    elif main_cmd in ('pip', 'npm', 'yarn'):
                        return f"Instalando dependências ({main_cmd})"
                    elif main_cmd == 'git':
                        return f"Git: {' '.join(cmd_parts[1:3])}"
                    else:
                        return f"Executando {main_cmd}"
            return "Executando comando"

        elif tool_name == 'Skill':
            skill_name = tool_input.get('skill', '')
            if skill_name:
                return f"Usando skill: {skill_name}"
            return "Invocando skill"

        elif tool_name == 'Glob':
            pattern = tool_input.get('pattern', '')
            if pattern:
                return f"Buscando arquivos: {pattern}"
            return "Buscando arquivos"

        elif tool_name == 'Grep':
            pattern = tool_input.get('pattern', '')
            if pattern:
                return f"Buscando: {pattern[:30]}..."
            return "Buscando no código"

        elif tool_name == 'Write':
            file_path = tool_input.get('file_path', '')
            if file_path:
                file_name = file_path.split('/')[-1] if '/' in file_path else file_path
                return f"Escrevendo {file_name}"
            return "Escrevendo arquivo"

        elif tool_name == 'Edit':
            file_path = tool_input.get('file_path', '')
            if file_path:
                file_name = file_path.split('/')[-1] if '/' in file_path else file_path
                return f"Editando {file_name}"
            return "Editando arquivo"

        elif tool_name == 'TodoWrite':
            todos = tool_input.get('todos', [])
            if todos:
                # Conta tarefas por status
                in_progress = sum(1 for t in todos if t.get('status') == 'in_progress')
                if in_progress > 0:
                    current = next((t for t in todos if t.get('status') == 'in_progress'), None)
                    if current:
                        return current.get('activeForm', 'Atualizando tarefas')
                return f"Gerenciando {len(todos)} tarefas"
            return "Atualizando tarefas"

        # Default: usa o nome da ferramenta
        return tool_name

    def _format_system_prompt(
        self,
        user_name: str = "Usuário",
        user_id: int = None
    ) -> str:
        """
        Formata system prompt com variáveis.

        Args:
            user_name: Nome do usuário
            user_id: ID do usuário (para Memory Tool)

        Returns:
            System prompt formatado
        """
        prompt = self.system_prompt.replace(
            "{data_atual}",
            agora_utc_naive().strftime("%d/%m/%Y %H:%M")
        )
        prompt = prompt.replace("{usuario_nome}", user_name)

        # Memory Tool: passa user_id para os scripts
        if user_id:
            prompt = prompt.replace("{user_id}", str(user_id))
        else:
            prompt = prompt.replace("{user_id}", "NAO_DISPONIVEL")

        # Módulo Pessoal + SQL Admin: restrição default seguro (texto inline no prompt)
        # Se import falhar, restrição permanece (seguro por default)
        restricao_pessoal = ", acessar ou mencionar tabelas pessoal_* (financas pessoais — dados privados, acesso restrito)"
        try:
            from app.pessoal import USUARIOS_PESSOAL, USUARIOS_SQL_ADMIN
            if user_id and (user_id in USUARIOS_SQL_ADMIN or user_id in USUARIOS_PESSOAL):
                prompt = prompt.replace(restricao_pessoal, "")
        except ImportError:
            pass  # restrição já está no prompt — seguro por default

        return prompt

    @staticmethod
    async def _self_correct_response(full_text: str) -> Optional[str]:
        """
        D6: Self-Correction — valida coerência aritmética em respostas tabulares.

        Reescrito para Sonnet 4.6 com escopo reduzido (vs Haiku que gerava falsos positivos):
        - Valida APENAS respostas com tabelas contendo dados numéricos
        - Critérios: inconsistências aritméticas (soma não bate, % diverge de absolutos)
        - Threshold: 500 chars (ignora respostas curtas/conversacionais)

        Args:
            full_text: Texto completo da resposta do agente

        Returns:
            None se a resposta está OK ou não precisa de validação
            String com observação de correção se detectar problema aritmético
        """
        from ..config.feature_flags import USE_SELF_CORRECTION

        if not USE_SELF_CORRECTION:
            return None

        # Threshold alto — só validar respostas substanciais
        if not full_text or len(full_text.strip()) < 500:
            return None

        # Só validar respostas que contenham tabelas com dados numéricos
        # Indicadores: linhas com pipe (tabela markdown) + dígitos
        import re
        has_table = bool(re.search(r'\|.*\d.*\|', full_text))
        if not has_table:
            return None

        try:
            client = anthropic.Anthropic()

            validation = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": (
                        "Verifique APENAS inconsistências ARITMÉTICAS nesta resposta:\n"
                        "- Soma de itens não bate com total declarado\n"
                        "- Percentual diverge dos valores absolutos\n"
                        "- Contagem de linhas contradiz quantidade mencionada\n\n"
                        "NÃO avalie: qualidade da escrita, completude, formatação ou "
                        "informações que não envolvem cálculos.\n\n"
                        "Se não há erro aritmético, responda EXATAMENTE: OK\n"
                        "Se encontrar, descreva em UMA frase curta (ex: 'Total diz 5 itens mas tabela tem 8').\n\n"
                        f"Resposta:\n{full_text[:3000]}"
                    )
                }]
            )

            result = validation.content[0].text.strip()

            if result.upper() == "OK" or len(result) < 5:
                logger.debug("[SELF-CORRECTION] Validação aritmética: OK")
                return None

            logger.warning(f"[SELF-CORRECTION] Inconsistência aritmética detectada: {result}")
            return result

        except Exception as e:
            # Self-correction é best-effort — falha silenciosa
            logger.debug(f"[SELF-CORRECTION] Erro na validação (ignorado): {e}")
            return None

    async def _parse_sdk_message(
        self,
        message: Any,
        state: '_StreamParseState',
    ) -> List[StreamEvent]:
        """Parse de uma mensagem SDK em StreamEvents.

        Método reutilizável por ambos os paths (query() e ClaudeSDKClient).
        Modifica `state` in-place (full_text, tokens, tool_calls, etc.).
        Retorna lista de StreamEvents a emitir (pode ser vazia).

        INVARIANTE: O comportamento é IDÊNTICO ao código inline que existia
        em _stream_response() linhas 1960-2262 antes da extração.

        Args:
            message: Mensagem do SDK (SystemMessage, AssistantMessage, etc.)
            state: Estado mutável do stream (compartilhado entre mensagens)

        Returns:
            Lista de StreamEvent (pode ser vazia para mensagens sem output)
        """
        events: List[StreamEvent] = []

        # ─── Diagnóstico de tempo ───
        current_time = time.time()
        elapsed_total = current_time - state.stream_start_time
        elapsed_since_last = current_time - state.last_message_time
        state.last_message_time = current_time

        if not state.first_message_logged:
            state.first_message_logged = True
            logger.info(
                f"[AGENT_SDK] Primeira mensagem recebida: {type(message).__name__} | "
                f"{elapsed_total:.1f}s apos inicio"
            )
        else:
            logger.debug(
                f"[AGENT_SDK] msg={type(message).__name__} | "
                f"total={elapsed_total:.1f}s | "
                f"delta={elapsed_since_last:.1f}s"
            )

        # ─── SystemMessage (init do SDK) ───
        if isinstance(message, SystemMessage):
            sdk_sid = message.data.get('session_id') if hasattr(message, 'data') else None
            if sdk_sid:
                state.result_session_id = sdk_sid
                logger.info(f"[AGENT_SDK] SDK session_id from init: {sdk_sid[:12]}...")
            return events

        # ─── SDK 0.1.46+: Task messages (subagentes) ───
        if _HAS_TASK_MESSAGES:
            if isinstance(message, TaskStartedMessage):
                task_desc = getattr(message, 'description', '') or ''
                task_id = getattr(message, 'task_id', '') or ''
                task_type = getattr(message, 'task_type', '') or ''
                logger.info(
                    f"[AGENT_SDK] TaskStarted: {task_desc[:80]} | "
                    f"task_id={task_id[:12]} | task_type={task_type}"
                )
                events.append(StreamEvent(
                    type='task_started',
                    content=task_desc,
                    metadata={
                        'task_id': task_id,
                        'task_type': task_type,
                    }
                ))
                return events

            if isinstance(message, TaskProgressMessage):
                task_desc = getattr(message, 'description', '') or ''
                task_id = getattr(message, 'task_id', '') or ''
                last_tool = getattr(message, 'last_tool_name', '') or ''
                logger.debug(
                    f"[AGENT_SDK] TaskProgress: {task_desc[:80]} | "
                    f"task_id={task_id[:12]} | last_tool={last_tool}"
                )
                events.append(StreamEvent(
                    type='task_progress',
                    content=task_desc,
                    metadata={
                        'task_id': task_id,
                        'last_tool_name': last_tool,
                    }
                ))
                return events

            if isinstance(message, TaskNotificationMessage):
                summary = getattr(message, 'summary', '') or ''
                status = getattr(message, 'status', '') or ''
                task_id = getattr(message, 'task_id', '') or ''
                usage = getattr(message, 'usage', None)
                logger.info(
                    f"[AGENT_SDK] TaskNotification: {summary[:80]} | "
                    f"status={status} | task_id={task_id[:12]} | "
                    f"usage={usage}"
                )
                events.append(StreamEvent(
                    type='task_notification',
                    content=summary,
                    metadata={
                        'task_id': task_id,
                        'status': status,
                        'usage': usage if isinstance(usage, dict) else None,
                    }
                ))
                return events

        # ─── AssistantMessage ───
        if isinstance(message, AssistantMessage):
            # Captura usage
            if hasattr(message, 'usage') and message.usage:
                usage = message.usage
                if isinstance(usage, dict):
                    state.input_tokens = usage.get('input_tokens', 0)
                    state.output_tokens = usage.get('output_tokens', 0)
                else:
                    state.input_tokens = getattr(usage, 'input_tokens', 0) or 0
                    state.output_tokens = getattr(usage, 'output_tokens', 0) or 0

            # C3: Detectar erros da API
            if hasattr(message, 'error') and message.error:
                error_info = message.error
                error_str = str(error_info).lower()
                error_type_str = error_info.get('type', 'unknown') if isinstance(error_info, dict) else type(error_info).__name__

                logger.warning(
                    f"[AGENT_SDK] API error: type={error_type_str}, error={error_info}"
                )

                if 'rate_limit' in error_str:
                    events.append(StreamEvent(
                        type='error',
                        content="Limite de requisições excedido. Aguardando...",
                        metadata={'error_type': 'rate_limit', 'retryable': True}
                    ))
                elif 'too long' in error_str or 'context' in error_str:
                    events.append(StreamEvent(
                        type='error',
                        content="Conversa muito longa. Tente iniciar uma nova sessão.",
                        metadata={'error_type': 'context_overflow', 'retryable': False}
                    ))
                else:
                    events.append(StreamEvent(
                        type='error',
                        content=f"Erro da API: {error_info}",
                        metadata={'error_type': error_type_str, 'raw_error': str(error_info)[:500]}
                    ))

            # Message ID para deduplicacao
            if hasattr(message, 'id') and message.id:
                state.last_message_id = message.id

            if message.content:
                for block in message.content:
                    # Extended Thinking
                    if isinstance(block, ThinkingBlock):
                        thinking_content = getattr(block, 'thinking', '')
                        if thinking_content:
                            events.append(StreamEvent(
                                type='thinking',
                                content=thinking_content
                            ))
                        continue

                    # Texto
                    if isinstance(block, TextBlock):
                        text_chunk = block.text
                        # Adiciona separador entre segmentos de texto (após tool calls)
                        if state.full_text and state.had_tool_between_texts:
                            text_chunk = '\n\n' + text_chunk
                        state.full_text += text_chunk
                        state.had_tool_between_texts = False
                        events.append(StreamEvent(
                            type='text',
                            content=text_chunk
                        ))

                    # Tool call
                    elif isinstance(block, ToolUseBlock):
                        state.had_tool_between_texts = True
                        tool_call = ToolCall(
                            id=block.id,
                            name=block.name,
                            input=block.input
                        )
                        state.tool_calls.append(tool_call)

                        state.current_tool_start_time = time.time()
                        state.current_tool_name = block.name
                        logger.info(f"[AGENT_SDK] Tool START: {block.name}")

                        tool_description = self._extract_tool_description(
                            block.name, block.input
                        )

                        events.append(StreamEvent(
                            type='tool_call',
                            content=block.name,
                            metadata={
                                'tool_id': block.id,
                                'input': block.input,
                                'description': tool_description
                            }
                        ))

                        # TodoWrite emit
                        if block.name == 'TodoWrite' and block.input:
                            todos = block.input.get('todos', [])
                            if todos:
                                events.append(StreamEvent(
                                    type='todos',
                                    content={'todos': todos},
                                    metadata={'tool_id': block.id}
                                ))
            return events

        # ─── UserMessage (tool results) ───
        if isinstance(message, UserMessage):
            tool_duration_ms = 0
            if state.current_tool_start_time:
                tool_duration_ms = int((time.time() - state.current_tool_start_time) * 1000)
                logger.info(
                    f"[AGENT_SDK] Tool DONE: {state.current_tool_name} {tool_duration_ms}ms"
                )
                state.current_tool_start_time = None

            content = getattr(message, 'content', None)
            if content and isinstance(content, list):
                for block in content:
                    if isinstance(block, ToolResultBlock):
                        result_content = block.content
                        is_error = getattr(block, 'is_error', False) or False
                        tool_use_id = getattr(block, 'tool_use_id', '')

                        if isinstance(result_content, list):
                            result_content = str(result_content)[:500]
                        elif result_content:
                            result_content = str(result_content)[:500]
                        else:
                            result_content = "(sem resultado)"

                        tool_name = next(
                            (tc.name for tc in state.tool_calls if tc.id == tool_use_id),
                            'ferramenta'
                        )

                        if is_error:
                            expected_errors = ['does not exist', 'not found', 'no such file']
                            is_expected = any(err in result_content.lower() for err in expected_errors)
                            if is_expected:
                                logger.debug(f"[AGENT_SDK] Tool '{tool_name}' (esperado): {result_content[:100]}")
                            else:
                                logger.warning(f"[AGENT_SDK] Tool '{tool_name}' erro: {result_content[:200]}")

                        events.append(StreamEvent(
                            type='tool_result',
                            content=result_content,
                            metadata={
                                'tool_use_id': tool_use_id,
                                'tool_name': tool_name,
                                'is_error': is_error,
                                'duration_ms': tool_duration_ms,
                            }
                        ))
            return events

        # ─── ResultMessage (fim) ───
        if isinstance(message, ResultMessage):
            # CRÍTICO: Capturar session_id REAL do SDK para resume
            state.result_session_id = message.session_id

            # SDK 0.1.46+: stop_reason indica motivo do encerramento
            stop_reason = getattr(message, 'stop_reason', '') or ''

            if message.result:
                state.full_text = message.result

            # Capturar usage do ResultMessage (única fonte confiável)
            if message.usage:
                usage = message.usage
                if isinstance(usage, dict):
                    state.input_tokens = usage.get('input_tokens', state.input_tokens)
                    state.output_tokens = usage.get('output_tokens', state.output_tokens)
                else:
                    state.input_tokens = getattr(usage, 'input_tokens', state.input_tokens) or state.input_tokens
                    state.output_tokens = getattr(usage, 'output_tokens', state.output_tokens) or state.output_tokens

            logger.info(
                f"[AGENT_SDK] ResultMessage | "
                f"stop_reason={stop_reason} | "
                f"cost={message.total_cost_usd} | "
                f"usage={message.usage} | turns={message.num_turns} | "
                f"duration={message.duration_ms}ms | "
                f"tokens_captured=({state.input_tokens},{state.output_tokens})"
            )

            # Detectar interrupt
            is_interrupted = (
                getattr(message, 'subtype', '') in ('interrupted', 'canceled', 'cancelled')
                or (message.is_error and 'interrupt' in str(message.result or '').lower())
            )

            if is_interrupted and not state.done_emitted:
                logger.info(
                    f"[AGENT_SDK] Interrupt detectado | "
                    f"subtype={getattr(message, 'subtype', 'N/A')} | "
                    f"text_so_far={len(state.full_text)} chars"
                )
                events.append(StreamEvent(
                    type='interrupt_ack',
                    content='Operação interrompida pelo usuário',
                ))

            if not state.done_emitted:
                # D6: Self-Correction (skip se interrupt)
                correction = None
                if not is_interrupted:
                    correction = await self._self_correct_response(state.full_text)
                    if correction:
                        events.append(StreamEvent(
                            type='text',
                            content=f"\n\n⚠️ **Observação de validação**: {correction}",
                            metadata={'self_correction': True}
                        ))

                # SDK nativo: structured_output (quando output_format configurado)
                structured_output = getattr(message, 'structured_output', None)
                if structured_output is not None:
                    logger.info(
                        f"[AGENT_SDK] Structured output recebido: "
                        f"type={type(structured_output).__name__} | "
                        f"keys={list(structured_output.keys()) if isinstance(structured_output, dict) else 'N/A'}"
                    )

                state.done_emitted = True
                events.append(StreamEvent(
                    type='done',
                    content={
                        'text': state.full_text,
                        'input_tokens': state.input_tokens,
                        'output_tokens': state.output_tokens,
                        'total_cost_usd': getattr(message, 'total_cost_usd', 0) or 0,
                        'session_id': state.result_session_id,
                        'tool_calls': len(state.tool_calls),
                        'self_corrected': correction is not None if correction else False,
                        'interrupted': is_interrupted,
                        'stop_reason': stop_reason,
                        'structured_output': structured_output,
                    },
                    metadata={'message_id': state.last_message_id or ''}
                ))

            # Sinalizar prompt generator para terminar (path query() apenas)
            if state.streaming_done_event:
                state.streaming_done_event.set()

            return events

        # Mensagem desconhecida — ignorar silenciosamente
        logger.debug(f"[AGENT_SDK] Mensagem ignorada: {type(message).__name__}")
        return events

    async def stream_response(
        self,
        prompt: str,
        user_name: str = "Usuário",
        model: Optional[str] = None,
        effort_level: str = "off",
        plan_mode: bool = False,
        user_id: int = None,
        image_files: Optional[List[dict]] = None,
        sdk_session_id: Optional[str] = None,
        can_use_tool: Optional[Callable] = None,
        our_session_id: Optional[str] = None,
        output_format: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Gera resposta em streaming.

        Dispatch baseado em feature flag USE_PERSISTENT_SDK_CLIENT:
        - flag=false (default): path query() + resume (v2 — self-contained)
        - flag=true: path ClaudeSDKClient persistente (v3 — daemon thread pool)

        Args:
            prompt: Mensagem do usuário
            user_name: Nome do usuário
            model: Modelo a usar
            effort_level: Nível de esforço do thinking ("off"|"low"|"medium"|"high"|"max")
            plan_mode: Ativar modo somente-leitura
            user_id: ID do usuário (para Memory Tool)
            image_files: Lista de imagens em formato Vision API
            sdk_session_id: Session ID do SDK para resume (do DB)
            can_use_tool: Callback de permissão
            our_session_id: Nosso UUID de sessão (usado pelo path persistente como pool key)
            output_format: JSON Schema para structured output (SDK nativo)

        Yields:
            StreamEvent com tipo e conteúdo
        """
        from ..config.feature_flags import USE_PERSISTENT_SDK_CLIENT

        if USE_PERSISTENT_SDK_CLIENT:
            # Path v3: ClaudeSDKClient persistente (daemon thread pool)
            async for event in self._stream_response_persistent(
                prompt=prompt,
                user_name=user_name,
                model=model,
                effort_level=effort_level,
                plan_mode=plan_mode,
                user_id=user_id,
                image_files=image_files,
                sdk_session_id=sdk_session_id,
                can_use_tool=can_use_tool,
                our_session_id=our_session_id,
                output_format=output_format,
            ):
                yield event
        else:
            # Path v2: query() + resume (self-contained)
            async for event in self._stream_response(
                prompt=prompt,
                user_name=user_name,
                model=model,
                effort_level=effort_level,
                plan_mode=plan_mode,
                user_id=user_id,
                image_files=image_files,
                sdk_session_id=sdk_session_id,
                can_use_tool=can_use_tool,
                output_format=output_format,
            ):
                yield event

    def _build_options(
        self,
        user_name: str = "Usuário",
        can_use_tool: Optional[Callable] = None,
        max_turns: int = 30,
        model: Optional[str] = None,
        effort_level: str = "off",
        plan_mode: bool = False,
        user_id: int = None,
        output_format: Optional[Dict[str, Any]] = None,
    ) -> 'ClaudeAgentOptions':
        """
        Constrói ClaudeAgentOptions para ClaudeSDKClient.

        Configura: model, system_prompt, cwd, allowed_tools (de settings),
        hooks, betas, permission_mode, disallowed_tools, fallback_model.

        Args:
            user_name: Nome do usuário
            can_use_tool: Callback de permissão
            max_turns: Máximo de turnos
            model: Modelo a usar (sobrescreve settings.model)
            effort_level: Nível de esforço do thinking ("off"|"low"|"medium"|"high"|"max")
            plan_mode: Ativar modo somente-leitura
            user_id: ID do usuário (para Memory Tool)
            output_format: JSON Schema para structured output (SDK nativo)

        Returns:
            ClaudeAgentOptions configurado
        """
        import os

        # System prompt customizado (com user_id para Memory Tool)
        custom_instructions = self._format_system_prompt(user_name, user_id)

        # Diretório do projeto para carregar Skills
        project_cwd = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
            )
        )  # Raiz do projeto: /home/.../frete_sistema

        # Modo de permissão
        # Em ambiente headless (servidor), usar "acceptEdits" para evitar prompts interativos.
        # "default" faz o CLI tentar prompts no stdin (que não existe em servidor)
        # → timeout → "Stream closed" → "Claude Code has been suspended".
        # "acceptEdits" auto-aprova edições; can_use_tool callback controla permissões reais.
        # "bypassPermissions" seria alternativa mas remove TODAS as barreiras de segurança.
        permission_mode = "plan" if plan_mode else "acceptEdits"

        options_dict = {
            # Modelo
            "model": model if model else self.settings.model,

            # Máximo de turnos
            "max_turns": max_turns,

            # Buffer size para JSON messages do subprocess CLI.
            # Default do SDK: 1MB (1_048_576 bytes) — insuficiente para
            # tool results grandes (screenshots base64, HTML pesado).
            # Um screenshot PNG full-page (1280x720) em base64 gera ~1.3-2.6MB.
            # 10MB acomoda screenshots + margem para JSON envelope.
            # FONTE: claude_agent_sdk/_internal/subprocess_cli.py:29
            "max_buffer_size": 10_000_000,  # 10MB

            # System Prompt: depende de USE_CUSTOM_SYSTEM_PROMPT (configurado abaixo)
            # Placeholder — preenchido pelo guard de feature flag
            "system_prompt": None,

            # CWD: Diretório de trabalho para Skills
            "cwd": project_cwd,

            # Setting Sources: Em headless (servidor), carregar apenas "project" para
            # habilitar descoberta de skills (.claude/skills/*/SKILL.md), CLAUDE.md,
            # hooks e permissions do projeto. NÃO carregar "user" para evitar que
            # enabledPlugins pessoais (pyright-lsp, etc.) causem hang no servidor.
            # Ref: https://platform.claude.com/docs/en/agent-sdk/skills
            "setting_sources": ["project"] if permission_mode == "acceptEdits" else ["user", "project"],

            # Tools permitidas — lê de settings.py (fonte única de verdade)
            "allowed_tools": list(self.settings.tools_enabled),

            # Modo de permissão
            "permission_mode": permission_mode,

            # SDK 0.1.26+: Fallback model para resiliência
            "fallback_model": "sonnet",

            # SDK 0.1.26+: Barreira real de segurança
            "disallowed_tools": [
                "NotebookEdit",   # Não há Jupyter notebooks no sistema
            ],

            # Env vars passadas ao subprocess CLI do SDK
            # CLAUDE_CODE_STREAM_CLOSE_TIMEOUT: timeout para hooks/MCP (default 60s).
            # Em ambiente cloud (Render), MCP tools podem demorar mais (API calls, DB queries).
            # Skills complexas (cotação, SQL analítico, Odoo) podem levar até 4 min.
            # FONTE: claude_agent_sdk/_internal/query.py:116
            "env": {
                "CLAUDE_CODE_STREAM_CLOSE_TIMEOUT": "240000",  # 240s (4 min) em ms
            },
        }

        # =================================================================
        # System Prompt: preset claude_code vs preset operacional
        # Flag: USE_CUSTOM_SYSTEM_PROMPT (default false para rollback seguro)
        # =================================================================
        from ..config.feature_flags import USE_CUSTOM_SYSTEM_PROMPT

        if USE_CUSTOM_SYSTEM_PROMPT:
            # Prompt Architecture v2: string pura (preset_operacional + system_prompt)
            # Elimina ~3-4K tokens do preset claude_code (git, CSS, dev identity)
            options_dict["system_prompt"] = self._build_full_system_prompt(custom_instructions)
            logger.info(
                "[AGENT_CLIENT] System prompt: custom (preset_operacional.md + system_prompt.md)"
            )
        else:
            # Original: preset claude_code + append system_prompt.md
            options_dict["system_prompt"] = {
                "type": "preset",
                "preset": "claude_code",
                "append": custom_instructions
            }
            logger.info("[AGENT_CLIENT] System prompt: preset claude_code + append")

        # =================================================================
        # Agents customizados (.claude/agents/*.md)
        # Permite que sub-agents definidos localmente funcionem via SDK web.
        # Sem isso, Task(subagent_type="raio-x-pedido") falha com
        # "Agent type not found" porque setting_sources=[] impede
        # o CLI de descobrir agents por conta propria.
        # =================================================================
        try:
            from ..config.agent_loader import load_agent_definitions

            agents_dir = os.path.join(project_cwd, ".claude", "agents")
            if os.path.isdir(agents_dir):
                agent_definitions = load_agent_definitions(agents_dir)
                if agent_definitions:
                    options_dict["agents"] = agent_definitions
                    logger.info(
                        f"[AGENT_CLIENT] {len(agent_definitions)} agents carregados: "
                        f"{list(agent_definitions.keys())}"
                    )
        except ImportError:
            logger.debug("[AGENT_CLIENT] agent_loader nao disponivel — agents ignorados")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro ao carregar agents customizados: {e}")

        # Adaptive Thinking via campo nativo `effort` do ClaudeAgentOptions
        # SDK 0.1.36+: `effort` é campo typed no dataclass (Literal["low"|"medium"|"high"|"max"])
        # Substitui o workaround anterior via extra_args["effort"] → --effort CLI flag.
        # Opus 4.6: suporta todos os níveis (low/medium/high/max)
        # Sonnet 4.6/Haiku: suportam low/medium/high (max → fallback para high no CLI)
        if effort_level and effort_level != "off":
            options_dict["effort"] = effort_level
            logger.info(f"[AGENT_CLIENT] Effort level: {effort_level}")

        # Callback de permissão
        if can_use_tool:
            options_dict["can_use_tool"] = can_use_tool

        # Structured Output (SDK nativo)
        # Força a resposta final do agente a seguir um JSON Schema.
        # Útil para fluxos programáticos (API, dashboard, automação).
        # ResultMessage.structured_output conterá o JSON parseado.
        if output_format:
            options_dict["output_format"] = output_format
            logger.info(f"[AGENT_CLIENT] Structured output ativo: {output_format.get('type', 'unknown')}")

        # =================================================================
        # FEATURE FLAGS: Quick Wins (ativados via env vars)
        # =================================================================
        from ..config.feature_flags import (
            USE_BUDGET_CONTROL, MAX_BUDGET_USD,
            USE_EXTENDED_CONTEXT,
            USE_CONTEXT_CLEARING,
            USE_PROMPT_CACHING,
        )

        # Budget Control nativo
        if USE_BUDGET_CONTROL:
            options_dict["max_budget_usd"] = MAX_BUDGET_USD
            logger.info(f"[AGENT_CLIENT] Budget control nativo: max ${MAX_BUDGET_USD}/request")

        # Extended Context (1M tokens)
        # Opus 4.6 e Sonnet 4.6: 1M tokens NATIVO — sem beta header necessário.
        # Flag mantida apenas para log/documentação. Modelos atuais usam 1M automaticamente.
        if USE_EXTENDED_CONTEXT:
            current_model = str(options_dict.get("model", self.settings.model)).lower()
            logger.info(
                f"[AGENT_CLIENT] Extended Context: modelo '{current_model}' — "
                f"1M tokens nativo (Opus 4.6/Sonnet 4.6), sem beta header"
            )

        # Context Clearing automático
        # NOTA: clear-thinking e clear-tool-uses foram promovidos a GA.
        # Não precisam mais de beta header (removidos em 2026-02).
        if USE_CONTEXT_CLEARING:
            logger.info("[AGENT_CLIENT] Context Clearing habilitado (GA — sem beta header)")

        # Prompt Caching
        # NOTA: prompt-caching foi promovido a GA.
        # Não precisa mais de beta header (removido em 2026-02).
        if USE_PROMPT_CACHING:
            logger.info("[AGENT_CLIENT] Prompt Caching habilitado (GA — sem beta header)")

        # =================================================================
        # Hooks SDK formais para auditoria
        # =================================================================
        try:
            from claude_agent_sdk import (
                HookMatcher, PreToolUseHookInput, PostToolUseHookInput,
                PostToolUseFailureHookInput,
                PreCompactHookInput, StopHookInput, UserPromptSubmitHookInput,
                HookContext,
            )

            # SDK 0.1.48+: Subagent lifecycle hooks
            _has_subagent_hooks = False
            try:
                from claude_agent_sdk import SubagentStartHookInput, SubagentStopHookInput  # noqa: F811
                _has_subagent_hooks = True
            except ImportError:
                pass

            async def _keep_stream_open(hook_input: PreToolUseHookInput, signal, context: HookContext):
                """Hook OBRIGATÓRIO: mantém stream aberto para can_use_tool funcionar.

                FONTE: https://platform.claude.com/docs/en/agent-sdk/user-input
                'In Python, can_use_tool requires streaming mode and a PreToolUse hook
                that returns {"continue_": True} to keep the stream open. Without this
                hook, the stream closes before the permission callback can be invoked.'

                Sem este hook, AskUserQuestion e ExitPlanMode falham com 'stream closed'.

                SDK 0.1.29+: PreToolUseHookInput agora inclui tool_use_id e suporta
                additionalContext no output para injetar contexto antes da execução.
                """
                # Contexto adicional pré-execução para tools de consulta
                tool_name = hook_input.get('tool_name', '')
                additional = None

                # Injetar lembrete de campos corretos antes de queries SQL
                if tool_name == 'mcp__sql__consultar_sql':
                    additional = (
                        "LEMBRETE: carteira_principal NÃO tem codigo_ibge (usar nome_cidade+cod_uf). "
                        "faturamento_produto usa cnpj_cliente/nome_cliente (NÃO cnpj_cpf/razao_social). "
                        "separacao tem cnpj_cpf, raz_social_red, cidade_normalizada, uf_normalizada, codigo_ibge."
                    )

                if additional:
                    return {
                        "continue_": True,
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "additionalContext": additional,
                        },
                    }

                return {"continue_": True}

            async def _audit_post_tool_use(hook_input: PostToolUseHookInput, signal, context: HookContext):
                """Registra execução de tools para auditoria.

                SDK 0.1.29+: PostToolUseHookInput agora inclui tool_use_id
                para correlação precisa tool_call → tool_result.
                SDK 0.1.46+: agent_id e agent_type para distinguir subagentes.
                """
                try:
                    tool_name = hook_input.get('tool_name', 'unknown')
                    tool_use_id = hook_input.get('tool_use_id', '')
                    tool_input_str = str(hook_input.get('tool_input', ''))[:200]
                    # SDK 0.1.46+: identificar qual agente executou a tool
                    agent_id = hook_input.get('agent_id', '')
                    agent_type = hook_input.get('agent_type', '')
                    logger.info(
                        f"[AUDIT] PostToolUse: {tool_name} "
                        f"| id={tool_use_id[:12] if tool_use_id else 'N/A'} "
                        f"| agent={agent_type or 'main'}:{agent_id[:12] if agent_id else 'N/A'} "
                        f"| input: {tool_input_str}"
                    )
                    return {}
                except Exception as e:
                    logger.debug(f"[HOOK:PostToolUse] Suppressed (stream likely closed): {e}")
                    return {}

            async def _post_tool_use_failure(
                hook_input: PostToolUseFailureHookInput, signal, context: HookContext
            ):
                """Hook de falha de tool: loga erro e fornece contexto corretivo ao modelo.

                Dispara quando qualquer tool falha. Categoriza o erro e opcionalmente
                retorna additionalContext para guiar o modelo na recuperação.

                Sempre ativo (não depende de feature flag) — custo zero, benefício
                de logging estruturado + contexto corretivo.
                """
                try:
                    tool_name = hook_input.get('tool_name', 'unknown')
                    tool_input_data = hook_input.get('tool_input', {})
                    error_msg = hook_input.get('error', 'unknown error')
                    is_interrupt = hook_input.get('is_interrupt', False)

                    # Interrupt do usuário — não é erro real
                    log_prefix = "[HOOK:PostToolUseFailure]"
                    if is_interrupt:
                        logger.info(f"{log_prefix} INTERRUPT: {tool_name}")
                        return {}

                    logger.warning(
                        f"{log_prefix} {tool_name} falhou | "
                        f"error={error_msg[:300]} | "
                        f"input={str(tool_input_data)[:200]}"
                    )

                    # Contexto corretivo por categoria de tool
                    additional = None

                    if 'sql' in tool_name.lower() or 'consultar' in tool_name.lower():
                        if 'timeout' in error_msg.lower():
                            additional = (
                                "A consulta SQL excedeu o timeout. Simplifique: "
                                "use LIMIT, reduza JOINs, ou filtre por período menor."
                            )
                        elif 'permission' in error_msg.lower() or 'read only' in error_msg.lower():
                            additional = "Apenas consultas SELECT são permitidas no banco de dados."

                    elif tool_name == 'Bash':
                        if 'permission denied' in error_msg.lower():
                            additional = "Comando sem permissão. Verifique o caminho e permissões."
                        elif 'not found' in error_msg.lower():
                            additional = "Comando ou arquivo não encontrado. Verifique se existe."

                    if additional:
                        return {
                            "hookSpecificOutput": {
                                "hookEventName": "PostToolUseFailure",
                                "additionalContext": additional,
                            }
                        }

                    return {}
                except Exception as e:
                    logger.debug(f"[HOOK:PostToolUseFailure] Suppressed (stream likely closed): {e}")
                    return {}

            async def _pre_compact_hook(hook_input: PreCompactHookInput, signal, context: HookContext):
                """Antes de compactação, instrui modelo a salvar contexto logístico estruturado.

                P0-1: Melhoria do Pre-Compaction Hook.
                Com USE_STRUCTURED_COMPACTION=true (default), instrui o modelo a salvar
                pedidos, decisões, tarefas e contexto em formato XML estruturado.
                Sem a flag, mantém comportamento genérico original como fallback.
                """
                try:
                    from ..config.feature_flags import USE_STRUCTURED_COMPACTION

                    # B3: Log enriquecido de compactação
                    sdk_session = hook_input.get('session_id', 'unknown')
                    logger.info(
                        f"[COMPACTION] session={sdk_session[:12] if sdk_session != 'unknown' else 'unknown'} | "
                        f"reason=context_window_full | "
                        f"structured={USE_STRUCTURED_COMPACTION}"
                    )

                    if not USE_STRUCTURED_COMPACTION:
                        return {
                            "custom_instructions": (
                                "O contexto será compactado agora. ANTES de continuar, "
                                "salve informações críticas usando mcp__memory__save_memory "
                                "em /memories/context/session_notes.xml. "
                                "Após compactação, consulte suas memórias para recuperar estado."
                            )
                        }

                    return {
                        "custom_instructions": (
                            "⚠️ COMPACTAÇÃO IMINENTE — O contexto será reduzido agora.\n\n"
                            "ANTES de continuar, salve o estado da conversa usando "
                            "mcp__memory__save_memory no path /memories/context/session_notes.xml.\n\n"
                            "Use EXATAMENTE este formato XML:\n"
                            "```xml\n"
                            "<session_context>\n"
                            "  <pedidos_em_discussao>\n"
                            "    <!-- Liste TODOS os pedidos mencionados com código VCD/VFB, cliente e valor -->\n"
                            "    <pedido codigo=\"VCDxxx\" cliente=\"Nome\" valor=\"R$ X.XXX,XX\" status=\"pendente|parcial|concluido\" />\n"
                            "  </pedidos_em_discussao>\n"
                            "  <decisoes_tomadas>\n"
                            "    <!-- Decisões já confirmadas pelo usuário -->\n"
                            "    <decisao>Descrição da decisão</decisao>\n"
                            "  </decisoes_tomadas>\n"
                            "  <tarefas_pendentes>\n"
                            "    <!-- O que falta fazer nesta conversa -->\n"
                            "    <tarefa>Descrição</tarefa>\n"
                            "  </tarefas_pendentes>\n"
                            "  <dados_consultados>\n"
                            "    <!-- Últimas consultas SQL ou resultados relevantes -->\n"
                            "    <consulta tipo=\"sql|estoque|separacao\">Resumo do resultado</consulta>\n"
                            "  </dados_consultados>\n"
                            "  <contexto_usuario>\n"
                            "    <!-- Preferências e contexto mencionados -->\n"
                            "    <nota>Informação relevante sobre o usuário</nota>\n"
                            "  </contexto_usuario>\n"
                            "</session_context>\n"
                            "```\n\n"
                            "APÓS salvar, consulte /memories/context/session_notes.xml para "
                            "recuperar o estado e continue a conversa normalmente."
                        )
                    }
                except Exception as e:
                    logger.debug(f"[HOOK:PreCompact] Suppressed (stream likely closed): {e}")
                    return {}

            # ─── P3-2: Stop Hook — loga métricas finais da sessão ───
            async def _stop_hook(hook_input: StopHookInput, signal, context: HookContext):
                """Hook de encerramento: loga métricas finais da sessão.

                P3-2: Expanded Hooks.
                Executado pelo SDK quando a sessão termina (após ResultMessage).
                Loga: session_id, duração, indicador de stop_hook_active.
                CLI 2.1.47+: inclui last_assistant_message para audit trail.

                Quando USE_EXPANDED_HOOKS=false, retorna {} silenciosamente (noop).
                """
                try:
                    from ..config.feature_flags import USE_EXPANDED_HOOKS

                    if not USE_EXPANDED_HOOKS:
                        return {}

                    sdk_sid = hook_input.get('session_id', 'unknown')
                    stop_active = hook_input.get('stop_hook_active', False)

                    # CLI 2.1.47+: last_assistant_message disponível em runtime
                    # (não tipado no SDK 0.1.39, mas enviado pelo CLI como campo extra)
                    last_msg = hook_input.get('last_assistant_message', None)
                    last_msg_preview = ""
                    if last_msg and isinstance(last_msg, str):
                        last_msg_preview = f" | last_msg={last_msg[:80]}..."

                    logger.info(
                        f"[HOOK:Stop] Sessão encerrada: "
                        f"session={sdk_sid[:12]}... | "
                        f"stop_hook_active={stop_active}"
                        f"{last_msg_preview}"
                    )

                    # B4: Log de stats da sessão para análise futura
                    # Nota: session_id (nosso UUID) não está no escopo de _build_options.
                    # Stats são logados via [MEMORY_INJECT] a cada turno e podem ser
                    # agregados via parsing de logs.
                    logger.info(
                        f"[HOOK:Stop] user_id={user_id or 'None'} | "
                        f"sdk_session={sdk_sid[:12] if sdk_sid != 'unknown' else 'unknown'}"
                    )

                    return {}
                except Exception as e:
                    logger.debug(f"[HOOK:Stop] Suppressed (stream likely closed): {e}")
                    return {}

            # ─── SubagentStart Hook — notificacao instantanea ao frontend ───
            async def _subagent_start_hook(hook_input, signal, context: HookContext):
                """Hook de inicio de subagente: emite SSE event ANTES do subagente processar.

                SDK 0.1.48+: SubagentStart dispara INSTANTANEAMENTE no spawn,
                antes mesmo do TaskStartedMessage (que e async e pode demorar).
                Permite ao frontend mostrar 'Delegando para analista-carteira...'
                imediatamente.
                """
                try:
                    agent_id = hook_input.get('agent_id', '')
                    agent_type = hook_input.get('agent_type', '')

                    logger.info(
                        f"[HOOK:SubagentStart] "
                        f"agent_type={agent_type} | "
                        f"agent_id={agent_id[:12] if agent_id else 'N/A'} | "
                        f"user_id={user_id or 'None'}"
                    )

                    # Contexto para o modelo: saber que subagente foi acionado
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": "SubagentStart",
                            "additionalContext": (
                                f"Subagente '{agent_type}' iniciado (id={agent_id[:12] if agent_id else 'N/A'}). "
                                f"Aguarde resultado antes de responder ao usuario."
                            ),
                        }
                    }
                except Exception as e:
                    logger.debug(f"[HOOK:SubagentStart] Suppressed: {e}")
                    return {}

            # ─── SubagentStop Hook — metricas de subagente ao finalizar ───
            async def _subagent_stop_hook(hook_input, signal, context: HookContext):
                """Hook de fim de subagente: extrai custo e duracao do transcript.

                SDK 0.1.48+: SubagentStop dispara APOS o subagente terminar.
                Recebe agent_transcript_path — JSONL com todas as mensagens do
                subagente, incluindo ResultMessage com cost/usage.
                """
                try:
                    agent_id = hook_input.get('agent_id', '')
                    agent_type = hook_input.get('agent_type', '')
                    transcript_path = hook_input.get('agent_transcript_path', '')

                    # Extrair custo do transcript (ultima linha ResultMessage)
                    cost_usd = None
                    duration_ms = None
                    num_turns = None
                    stop_reason = ''

                    if transcript_path:
                        try:
                            import json as _json
                            with open(transcript_path, 'r') as f:
                                last_result = None
                                for line in f:
                                    line = line.strip()
                                    if not line:
                                        continue
                                    try:
                                        msg = _json.loads(line)
                                        if msg.get('type') == 'result':
                                            last_result = msg
                                    except _json.JSONDecodeError:
                                        continue

                                if last_result:
                                    cost_usd = last_result.get('total_cost_usd')
                                    duration_ms = last_result.get('duration_ms')
                                    num_turns = last_result.get('num_turns')
                                    stop_reason = last_result.get('stop_reason', '')
                        except (OSError, IOError) as file_err:
                            logger.debug(
                                f"[HOOK:SubagentStop] Transcript inacessivel: {file_err}"
                            )

                    logger.info(
                        f"[HOOK:SubagentStop] "
                        f"agent_type={agent_type} | "
                        f"agent_id={agent_id[:12] if agent_id else 'N/A'} | "
                        f"cost=${cost_usd or 0:.4f} | "
                        f"duration={duration_ms or 0}ms | "
                        f"turns={num_turns or 'N/A'} | "
                        f"stop_reason={stop_reason or 'end_turn'} | "
                        f"user_id={user_id or 'None'}"
                    )

                    # Registrar custo no cost_tracker
                    if cost_usd and cost_usd > 0:
                        try:
                            from .cost_tracker import cost_tracker
                            cost_tracker.record_cost(
                                message_id=f"subagent_{agent_id[:12] if agent_id else 'unknown'}",
                                input_tokens=0,  # Detalhes no log, aqui o total
                                output_tokens=0,
                                session_id=hook_input.get('session_id', ''),
                                user_id=user_id or 0,
                                tool_name=f"subagent:{agent_type}",
                            )
                            logger.debug(
                                f"[HOOK:SubagentStop] Custo registrado no cost_tracker: "
                                f"${cost_usd:.4f} ({agent_type})"
                            )
                        except Exception as cost_err:
                            logger.debug(f"[HOOK:SubagentStop] cost_tracker falhou: {cost_err}")

                    return {}
                except Exception as e:
                    logger.debug(f"[HOOK:SubagentStop] Suppressed: {e}")
                    return {}

            # ─── UserPromptSubmit Hook — injeta memórias + logging ───
            async def _user_prompt_submit_hook(
                hook_input: UserPromptSubmitHookInput, signal, context: HookContext
            ):
                """Hook de submissão: injeta memórias do usuário como contexto adicional.

                SEMPRE ATIVO: A injeção de memória é independente de USE_EXPANDED_HOOKS.
                USE_EXPANDED_HOOKS controla apenas o logging extra.

                Fluxo:
                1. Carrega memórias do usuário do banco via _load_user_memories_for_context
                2. Formata como XML estruturado
                3. Retorna via hookSpecificOutput.additionalContext
                4. SDK injeta automaticamente no contexto da conversa

                Ref: https://platform.claude.com/docs/en/agent-sdk/hooks
                """
                try:
                    from ..config.feature_flags import USE_EXPANDED_HOOKS, USE_AUTO_MEMORY_INJECTION

                    prompt = hook_input.get('prompt', '')

                    if USE_EXPANDED_HOOKS:
                        logger.info(
                            f"[HOOK:UserPromptSubmit] Prompt recebido: "
                            f"prompt_len={len(prompt)} chars"
                        )

                    # ============================================================
                    # Injeção automática de memórias (independente de EXPANDED_HOOKS)
                    # ============================================================
                    # Log de diagnóstico — confirma propagação de user_id (Teams + Web)
                    logger.info(
                        f"[HOOK:UserPromptSubmit] user_id={user_id or 'None'} | "
                        f"auto_memory={'ON' if USE_AUTO_MEMORY_INJECTION else 'OFF'} | "
                        f"prompt_len={len(prompt)} chars"
                    )

                    additional_context = None
                    if USE_AUTO_MEMORY_INJECTION and user_id:
                        try:
                            # Fix DC-3: Ler model de self.settings (sempre atual)
                            # em vez de options_dict (closure capturada no connect,
                            # fica stale após set_model() no path persistente).
                            additional_context, injected_mem_ids = _load_user_memories_for_context(
                                user_id, prompt=prompt,
                                model_name=str(self.settings.model),
                            )
                            # Salvar IDs injetados para effectiveness tracking posterior
                            self._last_injected_memory_ids = injected_mem_ids
                        except Exception as mem_err:
                            logger.warning(
                                f"[HOOK:UserPromptSubmit] Erro ao carregar memórias "
                                f"(ignorado): {mem_err}"
                            )

                    # T2-1: Detecção de correção — lembrete para Reflection Bank
                    correction_hint = ""
                    if prompt and len(prompt) > 10:
                        import re as _re
                        _correction_patterns = [
                            _re.compile(r'(?i)\b(n[aã]o|errado|incorreto),?\s*(o\s+correct?o|na\s+verdade|deveria)'),
                            _re.compile(r'(?i)^(na verdade|errado|incorreto|n[aã]o[,.]?\s+(é|e)\s+(assim|isso))'),
                            _re.compile(r'(?i)\b(voc[eê]\s+errou|est[aá]\s+errado|isso\s+(est[aá]|tá)\s+errado)'),
                            _re.compile(r'(?i)\b(correct?o\s+[eé]|certo\s+[eé]|deveria\s+ser)'),
                        ]
                        if any(p.search(prompt) for p in _correction_patterns):
                            correction_hint = (
                                "\n<system_hint>"
                                "O usuário parece estar CORRIGINDO algo. "
                                "Siga o protocolo reflection_bank (R0): identifique o erro, "
                                "reconheça, salve em /memories/corrections/ e aprenda."
                                "</system_hint>"
                            )
                            logger.info(
                                f"[REFLECTION] Correção detectada user_id={user_id} "
                                f"prompt_preview={prompt[:60]}"
                            )

                    # ============================================================
                    # Debug Mode Context Injection (Camada 2)
                    # ============================================================
                    debug_context = ""
                    try:
                        from ..config.permissions import get_debug_mode
                        if get_debug_mode():
                            debug_context = (
                                "\n<debug_mode_context>"
                                "MODO DEBUG ATIVO. Capacidades extras disponiveis:\n"
                                "- Memory tools: use target_user_id=N para acessar memorias de outro usuario\n"
                                "- Session tools: use target_user_id=N + channel='teams'|'web' para buscar sessoes de outro usuario\n"
                                "- list_session_users: lista usuarios com sessoes (para descobrir target_user_id)\n"
                                "- SQL tool: tabelas internas desbloqueadas (agent_sessions, agent_memories, usuarios)\n"
                                "- Para encontrar user_id: list_session_users ou SQL 'SELECT id, nome, email FROM usuarios'\n"
                                "- Todo acesso cross-user e logado para auditoria.\n"
                                "Fluxo recomendado: list_session_users → search_sessions(target_user_id=N) → apresentar."
                                "</debug_mode_context>"
                            )
                            logger.info(
                                f"[HOOK:UserPromptSubmit] Debug mode context injected "
                                f"for user_id={user_id}"
                            )
                    except Exception as debug_err:
                        logger.debug(f"[HOOK:UserPromptSubmit] Debug mode check failed: {debug_err}")

                    # ============================================================
                    # SQL Admin Context Injection (Camada 3)
                    # ============================================================
                    sql_admin_context = ""
                    try:
                        from app.pessoal import USUARIOS_SQL_ADMIN as _SQL_ADMIN
                        if user_id and user_id in _SQL_ADMIN:
                            sql_admin_context = (
                                "\n<sql_admin_context>"
                                "MODO SQL ADMIN: voce tem acesso TOTAL ao banco via mcp__sql__consultar_sql.\n"
                                "- Todas as tabelas desbloqueadas (incluindo agent_sessions, pessoal_*, bi_*)\n"
                                "- INSERT, UPDATE, DELETE permitidos\n"
                                "- CUIDADO: operacoes de escrita afetam producao. Confirme com o usuario ANTES de executar.\n"
                                "- Para escrita, gere o SQL e mostre ao usuario antes de executar."
                                "</sql_admin_context>"
                            )
                            logger.info(
                                f"[HOOK:UserPromptSubmit] SQL admin context injected "
                                f"for user_id={user_id}"
                            )
                    except Exception as admin_err:
                        logger.debug(f"[HOOK:UserPromptSubmit] SQL admin check failed: {admin_err}")

                    if additional_context or correction_hint or debug_context or sql_admin_context:
                        additional_context = (additional_context or "") + correction_hint + debug_context + sql_admin_context
                        # B2: Log de context budget por categoria
                        memory_tokens_est = len(additional_context) // 4
                        logger.info(
                            f"[CONTEXT_BUDGET] "
                            f"user_id={user_id or 'None'} | "
                            f"memory_chars={len(additional_context)} | "
                            f"memory_tokens_est={memory_tokens_est} | "
                            f"prompt_len={len(prompt)}"
                        )
                        return {
                            "hookSpecificOutput": {
                                "hookEventName": "UserPromptSubmit",
                                "additionalContext": additional_context,
                            }
                        }

                    return {}
                except Exception as e:
                    logger.debug(f"[HOOK:UserPromptSubmit] Suppressed (stream likely closed): {e}")
                    return {}

            # ─── Registrar TODOS os hooks ───
            options_dict["hooks"] = {
                "PreToolUse": [
                    HookMatcher(
                        matcher=None,  # Aplica a TODAS as tools
                        hooks=[_keep_stream_open],
                    ),
                ],
                "PostToolUse": [
                    HookMatcher(
                        matcher="Bash|Skill",
                        hooks=[_audit_post_tool_use],
                    ),
                ],
                "PostToolUseFailure": [
                    HookMatcher(
                        matcher=None,  # Todas as tools
                        hooks=[_post_tool_use_failure],
                    ),
                ],
                "PreCompact": [
                    HookMatcher(
                        hooks=[_pre_compact_hook],
                    ),
                ],
                "Stop": [
                    HookMatcher(
                        hooks=[_stop_hook],
                    ),
                ],
                "UserPromptSubmit": [
                    HookMatcher(
                        hooks=[_user_prompt_submit_hook],
                    ),
                ],
            }

            # SDK 0.1.48+: Subagent lifecycle hooks
            if _has_subagent_hooks:
                options_dict["hooks"]["SubagentStart"] = [
                    HookMatcher(hooks=[_subagent_start_hook]),
                ]
                options_dict["hooks"]["SubagentStop"] = [
                    HookMatcher(hooks=[_subagent_stop_hook]),
                ]

            hooks_list = list(options_dict["hooks"].keys())
            logger.debug(
                f"[AGENT_CLIENT] Hooks SDK configurados: {', '.join(hooks_list)}"
            )
        except (ImportError, Exception) as e:
            logger.warning(f"[AGENT_CLIENT] Hooks SDK não disponíveis: {e}")

        # =================================================================
        # MCP Servers (Custom Tools in-process)
        # Helper + glob patterns — CLI resolve "mcp__name__*" automaticamente
        # =================================================================
        def _register_mcp(name: str, server, user_id_setter=None) -> bool:
            """Registra MCP server com glob pattern em allowed_tools."""
            if server is None:
                logger.debug(f"[AGENT_CLIENT] {name}_server é None — módulo não disponível")
                return False
            if user_id and user_id_setter:
                user_id_setter(user_id)
            options_dict.setdefault("mcp_servers", {})[name] = server
            options_dict.setdefault("allowed_tools", []).append(f"mcp__{name}__*")
            return True

        # SQL (Text-to-SQL com bloqueio condicional de tabelas pessoal_*)
        try:
            from ..tools.text_to_sql_tool import sql_server, set_current_user_id as set_sql_user_id
            if _register_mcp("sql", sql_server, set_sql_user_id):
                logger.info("[AGENT_CLIENT] MCP 'sql' registrada")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP sql não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP sql: {e}")

        # Memory (memória persistente — 11 operações)
        try:
            from ..tools.memory_mcp_tool import memory_server, set_current_user_id
            if _register_mcp("memory", memory_server, set_current_user_id):
                logger.info("[AGENT_CLIENT] MCP 'memory' registrada (11 operações)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP memory não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP memory: {e}")

        # Schema (descoberta de schema — 2 operações)
        try:
            from ..tools.schema_mcp_tool import schema_server
            if _register_mcp("schema", schema_server):
                logger.info("[AGENT_CLIENT] MCP 'schema' registrada (2 operações)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP schema não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP schema: {e}")

        # Sessions (busca em sessões anteriores — 4 operações)
        try:
            from ..tools.session_search_tool import sessions_server
            from ..tools.session_search_tool import set_current_user_id as set_session_search_user_id
            if _register_mcp("sessions", sessions_server, set_session_search_user_id):
                logger.info("[AGENT_CLIENT] MCP 'sessions' registrada (4 operações)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP sessions não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP sessions: {e}")

        # Render (logs e métricas — 3 operações)
        try:
            from ..tools.render_logs_tool import render_server
            if _register_mcp("render", render_server):
                logger.info("[AGENT_CLIENT] MCP 'render' registrada (3 operações)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP render não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP render: {e}")

        # Browser (Playwright headless — SSW + Atacadão, 12 operações)
        try:
            from ..tools.playwright_mcp_tool import browser_server
            if _register_mcp("browser", browser_server):
                logger.info("[AGENT_CLIENT] MCP 'browser' registrada (12 operações)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP browser não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP browser: {e}")

        # Routes (busca semântica de rotas — 1 operação)
        try:
            from ..tools.routes_search_tool import routes_server
            if _register_mcp("routes", routes_server):
                logger.info("[AGENT_CLIENT] MCP 'routes' registrada (1 operação)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP routes não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP routes: {e}")

        # Log de diagnóstico — útil para validar configuração em produção
        logger.info(
            f"[AGENT_CLIENT] Options: model={options_dict.get('model')}, "
            f"permission_mode={permission_mode}, "
            f"mcp_servers={list(options_dict.get('mcp_servers', {}).keys())}, "
            f"allowed_tools_count={len(options_dict.get('allowed_tools', []))}"
        )

        return ClaudeAgentOptions(**options_dict)

    async def _stream_response_persistent(
        self,
        prompt: str,
        user_name: str = "Usuário",
        model: Optional[str] = None,
        effort_level: str = "off",
        plan_mode: bool = False,
        user_id: int = None,
        image_files: Optional[List[dict]] = None,
        sdk_session_id: Optional[str] = None,
        can_use_tool: Optional[Callable] = None,
        our_session_id: Optional[str] = None,
        output_format: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Gera resposta em streaming usando ClaudeSDKClient persistente.

        ARQUITETURA v3 (flag USE_PERSISTENT_SDK_CLIENT=true):
        - ClaudeSDKClient mantido vivo entre turnos (daemon thread pool)
        - get_or_create_client() obtém ou cria client para a sessão
        - client.query() envia prompt, receive_response() recebe mensagens
        - ~2x menor latência vs query() (sem overhead spawn/destroy CLI)
        - streaming_done_event NÃO é necessário (sem _make_streaming_prompt)

        INVARIANTE: Emite os MESMOS StreamEvents na MESMA ordem que _stream_response().

        Args:
            prompt: Mensagem do usuário
            user_name: Nome do usuário
            model: Modelo a usar
            effort_level: Nível de esforço do thinking ("off"|"low"|"medium"|"high"|"max")
            plan_mode: Ativar modo somente-leitura
            user_id: ID do usuário (para Memory Tool)
            image_files: Lista de imagens em formato Vision API
            sdk_session_id: SDK session ID para resume (na primeira conexão)
            can_use_tool: Callback de permissão
            our_session_id: Nosso UUID de sessão (chave do pool)

        Yields:
            StreamEvent com tipo e conteúdo
        """
        from .client_pool import get_or_create_client, get_pooled_client

        # ─── Estado de parsing (sem streaming_done_event — DC-5) ───
        state = _StreamParseState()
        # Path persistente: streaming_done_event NÃO necessário.
        # Com ClaudeSDKClient, query()+receive_response() termina naturalmente
        # quando ResultMessage é recebido. Sem _make_streaming_prompt().
        state.streaming_done_event = None

        # ─── Construir options ───
        options = self._build_options(
            user_name=user_name,
            user_id=user_id,
            model=model,
            effort_level=effort_level,
            plan_mode=plan_mode,
            can_use_tool=can_use_tool,
            output_format=output_format,
        )

        # ─── RESUME: só na primeira conexão ───
        # Se o client já existe no pool (reutilização), o CLI subprocess
        # já tem o contexto da conversa. Resume só é necessário quando
        # criamos um novo client (primeiro turno ou após idle cleanup).
        pool_key = our_session_id or ''
        existing = get_pooled_client(pool_key)
        if not existing and sdk_session_id:
            options = self._with_resume(options, sdk_session_id)
            logger.info(f"[AGENT_SDK_PERSISTENT] Resuming session: {sdk_session_id[:12]}...")

        # ─── Emitir init sintético ───
        state.result_session_id = sdk_session_id
        yield StreamEvent(
            type='init',
            content={'session_id': sdk_session_id or 'pending'},
            metadata={
                'timestamp': agora_utc_naive().isoformat(),
                'resume': bool(sdk_session_id),
                'persistent': True,
            }
        )

        try:
            # ─── Obter ou criar client do pool ───
            pooled = await get_or_create_client(
                session_id=pool_key,
                options=options,
                user_id=user_id or 0,
            )

            # ─── Ajustar model/permission se client já existia ───
            current_model = model or self.settings.model
            if existing and existing.connected:
                # Client reutilizado — aplicar mudanças de configuração
                try:
                    await pooled.client.set_model(current_model)
                except Exception as model_err:
                    logger.warning(
                        f"[AGENT_SDK_PERSISTENT] set_model ignorado: {model_err}"
                    )
                permission_mode = "plan" if plan_mode else "acceptEdits"
                try:
                    await pooled.client.set_permission_mode(permission_mode)
                except Exception as perm_err:
                    logger.warning(
                        f"[AGENT_SDK_PERSISTENT] set_permission_mode ignorado: {perm_err}"
                    )

            # ─── Preparar prompt para query() ───
            if image_files:
                # Imagens requerem AsyncIterable (Vision API)
                async def _image_prompt():
                    content_blocks = list(image_files) + [{"type": "text", "text": prompt}]
                    yield {"type": "user", "message": {"role": "user", "content": content_blocks}}
                query_prompt = _image_prompt()
            else:
                # Texto puro: string é suficiente
                query_prompt = prompt

            # ─── STREAMING: query() + receive_response() ───
            # asyncio.Lock serializa chamadas no mesmo client (DC-1, R08)
            async with pooled.lock:
                pooled.last_used = time.time()

                logger.info(
                    f"[AGENT_SDK_PERSISTENT] query() | "
                    f"session={pool_key[:8]}... | "
                    f"model={current_model} | "
                    f"reuse={'yes' if (existing and existing.connected) else 'new'} | "
                    f"images={len(image_files) if image_files else 0}"
                )

                # Enviar prompt
                await pooled.client.query(query_prompt)

                # Receber resposta (termina após ResultMessage)
                async for message in pooled.client.receive_response():
                    for event in await self._parse_sdk_message(message, state):
                        yield event

            # ─── Fallback done (sem ResultMessage) ───
            if not state.done_emitted:
                correction = await self._self_correct_response(state.full_text)
                if correction:
                    yield StreamEvent(
                        type='text',
                        content=f"\n\n⚠️ **Observação de validação**: {correction}",
                        metadata={'self_correction': True}
                    )

                yield StreamEvent(
                    type='done',
                    content={
                        'text': state.full_text,
                        'input_tokens': state.input_tokens,
                        'output_tokens': state.output_tokens,
                        'total_cost_usd': 0,
                        'session_id': state.result_session_id,
                        'tool_calls': len(state.tool_calls),
                        'self_corrected': correction is not None if correction else False,
                    }
                )

        except ProcessError as e:
            elapsed_total = time.time() - state.stream_start_time
            exit_code = getattr(e, 'exit_code', None)
            stderr = getattr(e, 'stderr', '') or ''
            logger.error(
                f"[AGENT_SDK_PERSISTENT] ProcessError {elapsed_total:.1f}s | "
                f"exit={exit_code} | stderr={stderr[:500]} | msg={e}"
            )
            yield StreamEvent(
                type='error',
                content=f"Erro de processo (código {exit_code}). Tente novamente." if exit_code else str(e),
                metadata={'error_type': 'process_error', 'exit_code': exit_code,
                          'elapsed_seconds': elapsed_total, 'last_tool': state.current_tool_name}
            )
            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': state.full_text, 'input_tokens': state.input_tokens,
                             'output_tokens': state.output_tokens, 'total_cost_usd': 0,
                             'session_id': state.result_session_id,
                             'tool_calls': len(state.tool_calls), 'error_recovery': True},
                    metadata={'error_type': 'process_error'}
                )
            # Nota: streaming_done_event é None no path persistente (DC-5)

        except CLINotFoundError as e:
            # CLINotFoundError é subclasse de CLIConnectionError — DEVE vir antes
            elapsed_total = time.time() - state.stream_start_time
            logger.critical(f"[AGENT_SDK_PERSISTENT] CLI não encontrada {elapsed_total:.1f}s: {e}")
            yield StreamEvent(
                type='error',
                content="Erro crítico: CLI do agente não encontrada.",
                metadata={'error_type': 'cli_not_found', 'elapsed_seconds': elapsed_total}
            )
            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': state.full_text, 'input_tokens': state.input_tokens,
                             'output_tokens': state.output_tokens, 'total_cost_usd': 0,
                             'session_id': state.result_session_id,
                             'error_recovery': True},
                    metadata={'error_type': 'cli_not_found'}
                )
            # Nota: streaming_done_event é None no path persistente (DC-5)

        except CLIConnectionError as e:
            # Fix PYTHON-FLASK-J/H: CLI subprocess killed by SIGTERM (gunicorn worker
            # recycling). Catch explicitly to: (1) log as warning not error since it's
            # expected during deploys, (2) evict dead client from pool, (3) emit clean
            # error+done so Teams stream terminates immediately instead of timing out
            # (fixes PYTHON-FLASK-G cascade).
            elapsed_total = time.time() - state.stream_start_time
            logger.warning(
                f"[AGENT_SDK_PERSISTENT] CLIConnectionError {elapsed_total:.1f}s | "
                f"msg={e} | pool_key={pool_key[:8]}... | "
                f"Provável reciclagem de worker (SIGTERM)"
            )

            # Evict dead client from pool to force fresh connection on retry.
            # Subprocess already dead — just remove registry entry (no disconnect needed).
            try:
                from .client_pool import _registry, _registry_lock
                with _registry_lock:
                    evicted = _registry.pop(pool_key, None)
                if evicted:
                    evicted.connected = False
                    logger.info(f"[AGENT_SDK_PERSISTENT] Dead client evicted from pool: {pool_key[:8]}...")
            except Exception as evict_err:
                logger.debug(f"[AGENT_SDK_PERSISTENT] Pool eviction ignored: {evict_err}")

            # Return partial text if any was collected before the crash
            user_msg = state.full_text if state.full_text else (
                "O processo do agente foi interrompido (reciclagem do servidor). "
                "Tente novamente."
            )
            yield StreamEvent(
                type='error',
                content=user_msg if not state.full_text else (
                    "O processo do agente foi interrompido. Resposta parcial acima."
                ),
                metadata={
                    'error_type': 'cli_connection_error',
                    'elapsed_seconds': elapsed_total,
                    'last_tool': state.current_tool_name,
                    'partial_text_len': len(state.full_text),
                }
            )
            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={
                        'text': state.full_text,
                        'input_tokens': state.input_tokens,
                        'output_tokens': state.output_tokens,
                        'total_cost_usd': 0,
                        'session_id': state.result_session_id,
                        'tool_calls': len(state.tool_calls),
                        'error_recovery': True,
                    },
                    metadata={'error_type': 'cli_connection_error'}
                )
            # Nota: streaming_done_event é None no path persistente (DC-5)

        except CLIJSONDecodeError as e:
            elapsed_total = time.time() - state.stream_start_time
            logger.error(f"[AGENT_SDK_PERSISTENT] JSON decode error {elapsed_total:.1f}s: {e}")
            yield StreamEvent(
                type='error',
                content="Erro ao processar resposta do agente. Tente novamente.",
                metadata={'error_type': 'json_decode_error', 'elapsed_seconds': elapsed_total}
            )
            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': state.full_text, 'input_tokens': state.input_tokens,
                             'output_tokens': state.output_tokens, 'total_cost_usd': 0,
                             'session_id': state.result_session_id,
                             'error_recovery': True},
                    metadata={'error_type': 'json_decode_error'}
                )

        except BaseExceptionGroup as eg:
            elapsed_total = time.time() - state.stream_start_time
            sub_exceptions = list(eg.exceptions)
            sub_messages = [f"{type(se).__name__}: {se}" for se in sub_exceptions]

            logger.error(
                f"[AGENT_SDK_PERSISTENT] ExceptionGroup {elapsed_total:.1f}s | "
                f"{len(sub_exceptions)} sub-exceptions: {'; '.join(sub_messages[:3])}",
                exc_info=True
            )

            first_error = sub_exceptions[0] if sub_exceptions else eg
            error_msg = str(first_error)

            user_message = "Erro temporário ao executar ferramentas. Tente novamente."
            if 'timeout' in error_msg.lower():
                user_message = "Tempo limite excedido. Tente uma consulta mais simples."
            elif 'connection' in error_msg.lower():
                user_message = "Erro de conexão com a API. Tente novamente em alguns segundos."

            yield StreamEvent(
                type='error',
                content=user_message,
                metadata={
                    'error_type': 'exception_group',
                    'sub_exception_count': len(sub_exceptions),
                    'original_error': error_msg[:500],
                    'elapsed_seconds': elapsed_total,
                    'last_tool': state.current_tool_name,
                }
            )

            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={
                        'text': state.full_text,
                        'input_tokens': state.input_tokens,
                        'output_tokens': state.output_tokens,
                        'total_cost_usd': 0,
                        'session_id': state.result_session_id,
                        'tool_calls': len(state.tool_calls),
                        'error_recovery': True,
                    },
                    metadata={'error_type': 'exception_group'}
                )

        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            elapsed_total = time.time() - state.stream_start_time
            logger.error(
                f"[AGENT_SDK_PERSISTENT] {error_type} {elapsed_total:.1f}s: {error_msg}",
                exc_info=True
            )

            user_message = error_msg
            if 'timeout' in error_msg.lower():
                user_message = "Tempo limite excedido. Tente uma consulta mais simples."
            elif 'connection' in error_msg.lower():
                user_message = "Erro de conexão com a API. Tente novamente em alguns segundos."

            yield StreamEvent(
                type='error',
                content=user_message,
                metadata={
                    'error_type': error_type,
                    'original_error': error_msg[:500],
                    'elapsed_seconds': elapsed_total,
                    'last_tool': state.current_tool_name,
                }
            )

            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={
                        'text': state.full_text,
                        'input_tokens': state.input_tokens,
                        'output_tokens': state.output_tokens,
                        'total_cost_usd': 0,
                        'session_id': state.result_session_id,
                        'tool_calls': len(state.tool_calls),
                        'error_recovery': True,
                    },
                    metadata={'error_type': error_type}
                )

    async def _stream_response(
        self,
        prompt: str,
        user_name: str = "Usuário",
        model: Optional[str] = None,
        effort_level: str = "off",
        plan_mode: bool = False,
        user_id: int = None,
        image_files: Optional[List[dict]] = None,
        sdk_session_id: Optional[str] = None,
        can_use_tool: Optional[Callable] = None,
        output_format: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Gera resposta em streaming usando query() + resume.

        ARQUITETURA v2:
        - Cada chamada usa query() standalone (sem ClaudeSDKClient)
        - query() spawna CLI process, executa, limpa automaticamente
        - resume=sdk_session_id restaura contexto da conversa anterior
        - Sem pool, sem locks, sem connect/disconnect

        Args:
            prompt: Mensagem do usuário
            user_name: Nome do usuário
            model: Modelo a usar
            effort_level: Nível de esforço do thinking ("off"|"low"|"medium"|"high"|"max")
            plan_mode: Ativar modo somente-leitura
            user_id: ID do usuário (para Memory Tool)
            image_files: Lista de imagens em formato Vision API
            sdk_session_id: Session ID do SDK para resume (do DB)
            can_use_tool: Callback de permissão

        Yields:
            StreamEvent com tipo e conteúdo
        """
        # ─── Estado de parsing (compartilhado via _StreamParseState) ───
        state = _StreamParseState()

        # ─── Construir options ───
        options = self._build_options(
            user_name=user_name,
            user_id=user_id,
            model=model,
            effort_level=effort_level,
            plan_mode=plan_mode,
            can_use_tool=can_use_tool,
            output_format=output_format,
        )

        # ─── RESUME: Continuar conversa anterior ───
        if sdk_session_id:
            options = self._with_resume(options, sdk_session_id)
            logger.info(f"[AGENT_SDK] Resuming session: {sdk_session_id[:12]}...")

        # ─── Construir prompt como AsyncIterable ───
        # CRÍTICO: can_use_tool EXIGE streaming mode (AsyncIterable, não string)
        # FONTE: _internal/client.py:53-58
        # Portanto SEMPRE usamos AsyncIterable wrapper.
        # FIX-9: Event para sinalizar prompt generator após ResultMessage
        state.streaming_done_event = asyncio.Event()
        query_prompt = AgentClient._make_streaming_prompt(prompt, image_files, done_event=state.streaming_done_event)

        # ─── Emitir init sintético ───
        state.result_session_id = sdk_session_id  # Será sobrescrito pelo SDK se houver novo
        yield StreamEvent(
            type='init',
            content={'session_id': sdk_session_id or 'pending'},
            metadata={
                'timestamp': agora_utc_naive().isoformat(),
                'resume': bool(sdk_session_id),
            }
        )

        try:
            # ─── STREAMING via query() ───
            # query() é self-contained: spawna CLI process, executa, limpa.
            # Sem background tasks, sem estado persistente.
            # Quando o async for termina, o CLI process é limpo automaticamente.
            logger.info(
                f"[AGENT_SDK] Iniciando sdk_query() | "
                f"model={getattr(options, 'model', '?')} | "
                f"resume={bool(sdk_session_id)} | "
                f"setting_sources={getattr(options, 'setting_sources', '?')} | "
                f"mcp_servers={list(getattr(options, 'mcp_servers', {}).keys()) if hasattr(options, 'mcp_servers') and options.mcp_servers else '[]'}"
            )
            async for message in sdk_query(
                prompt=query_prompt,
                options=options,
            ):
                for event in await self._parse_sdk_message(message, state):
                    yield event

            # ─── Fallback done (sem ResultMessage) ───
            if not state.done_emitted:
                correction = await self._self_correct_response(state.full_text)
                if correction:
                    yield StreamEvent(
                        type='text',
                        content=f"\n\n⚠️ **Observação de validação**: {correction}",
                        metadata={'self_correction': True}
                    )

                yield StreamEvent(
                    type='done',
                    content={
                        'text': state.full_text,
                        'input_tokens': state.input_tokens,
                        'output_tokens': state.output_tokens,
                        'total_cost_usd': 0,
                        'session_id': state.result_session_id,
                        'tool_calls': len(state.tool_calls),
                        'self_corrected': correction is not None if correction else False,
                    }
                )

            # ─── NÃO PRECISA DESTRUIR NADA ───
            # query() limpa o CLI process automaticamente quando o
            # async for termina. Sem pool, sem disconnect, sem leak.

        except ProcessError as e:
            elapsed_total = time.time() - state.stream_start_time
            exit_code = getattr(e, 'exit_code', None)
            stderr = getattr(e, 'stderr', '') or ''
            logger.error(
                f"[AGENT_SDK] ProcessError {elapsed_total:.1f}s | "
                f"exit={exit_code} | stderr={stderr[:500]} | msg={e}"
            )
            yield StreamEvent(
                type='error',
                content=f"Erro de processo (código {exit_code}). Tente novamente." if exit_code else str(e),
                metadata={'error_type': 'process_error', 'exit_code': exit_code,
                          'elapsed_seconds': elapsed_total, 'last_tool': state.current_tool_name}
            )
            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': state.full_text, 'input_tokens': state.input_tokens,
                             'output_tokens': state.output_tokens, 'total_cost_usd': 0,
                             'session_id': state.result_session_id,
                             'tool_calls': len(state.tool_calls), 'error_recovery': True},
                    metadata={'error_type': 'process_error'}
                )
            # FIX: Liberar prompt generator para evitar zombie de 10min.
            # Ref: CLAUDE.md R5 (streaming_done_event)
            if state.streaming_done_event:
                state.streaming_done_event.set()

        except CLINotFoundError as e:
            # CLINotFoundError é subclasse de CLIConnectionError — DEVE vir antes
            elapsed_total = time.time() - state.stream_start_time
            logger.critical(f"[AGENT_SDK] CLI não encontrada {elapsed_total:.1f}s: {e}")
            yield StreamEvent(
                type='error',
                content="Erro crítico: CLI do agente não encontrada.",
                metadata={'error_type': 'cli_not_found', 'elapsed_seconds': elapsed_total}
            )
            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': state.full_text, 'input_tokens': state.input_tokens,
                             'output_tokens': state.output_tokens, 'total_cost_usd': 0,
                             'session_id': state.result_session_id,
                             'error_recovery': True},
                    metadata={'error_type': 'cli_not_found'}
                )
            if state.streaming_done_event:
                state.streaming_done_event.set()

        except CLIConnectionError as e:
            # Fix PYTHON-FLASK-J/H: CLI subprocess killed by SIGTERM (gunicorn worker
            # recycling). Same fix as persistent path — emit error+done immediately
            # so stream terminates cleanly instead of hanging until timeout.
            elapsed_total = time.time() - state.stream_start_time
            logger.warning(
                f"[AGENT_SDK] CLIConnectionError {elapsed_total:.1f}s | "
                f"msg={e} | Provável reciclagem de worker (SIGTERM)"
            )
            user_msg = state.full_text if state.full_text else (
                "O processo do agente foi interrompido (reciclagem do servidor). "
                "Tente novamente."
            )
            yield StreamEvent(
                type='error',
                content=user_msg if not state.full_text else (
                    "O processo do agente foi interrompido. Resposta parcial acima."
                ),
                metadata={
                    'error_type': 'cli_connection_error',
                    'elapsed_seconds': elapsed_total,
                    'last_tool': state.current_tool_name,
                    'partial_text_len': len(state.full_text),
                }
            )
            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={
                        'text': state.full_text,
                        'input_tokens': state.input_tokens,
                        'output_tokens': state.output_tokens,
                        'total_cost_usd': 0,
                        'session_id': state.result_session_id,
                        'tool_calls': len(state.tool_calls),
                        'error_recovery': True,
                    },
                    metadata={'error_type': 'cli_connection_error'}
                )
            if state.streaming_done_event:
                state.streaming_done_event.set()

        except CLIJSONDecodeError as e:
            elapsed_total = time.time() - state.stream_start_time
            logger.error(f"[AGENT_SDK] JSON decode error {elapsed_total:.1f}s: {e}")
            yield StreamEvent(
                type='error',
                content="Erro ao processar resposta do agente. Tente novamente.",
                metadata={'error_type': 'json_decode_error', 'elapsed_seconds': elapsed_total}
            )
            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': state.full_text, 'input_tokens': state.input_tokens,
                             'output_tokens': state.output_tokens, 'total_cost_usd': 0,
                             'session_id': state.result_session_id,
                             'error_recovery': True},
                    metadata={'error_type': 'json_decode_error'}
                )
            if state.streaming_done_event:
                state.streaming_done_event.set()

        except BaseExceptionGroup as eg:
            # Python 3.11+: asyncio.TaskGroup envolve erros de tools paralelas
            # em BaseExceptionGroup, que herda de BaseException (NÃO Exception).
            # Sem este handler, o erro propaga sem ser capturado.
            elapsed_total = time.time() - state.stream_start_time
            sub_exceptions = list(eg.exceptions)
            sub_messages = [f"{type(se).__name__}: {se}" for se in sub_exceptions]

            logger.error(
                f"[AGENT_SDK] ExceptionGroup {elapsed_total:.1f}s | "
                f"{len(sub_exceptions)} sub-exceptions: {'; '.join(sub_messages[:3])}",
                exc_info=True
            )

            # Mensagem amigável baseada na primeira sub-exception
            first_error = sub_exceptions[0] if sub_exceptions else eg
            error_msg = str(first_error)

            user_message = "Erro temporário ao executar ferramentas. Tente novamente."
            if 'timeout' in error_msg.lower():
                user_message = "Tempo limite excedido. Tente uma consulta mais simples."
            elif 'connection' in error_msg.lower():
                user_message = "Erro de conexão com a API. Tente novamente em alguns segundos."

            yield StreamEvent(
                type='error',
                content=user_message,
                metadata={
                    'error_type': 'exception_group',
                    'sub_exception_count': len(sub_exceptions),
                    'original_error': error_msg[:500],
                    'elapsed_seconds': elapsed_total,
                    'last_tool': state.current_tool_name,
                }
            )

            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={
                        'text': state.full_text,
                        'input_tokens': state.input_tokens,
                        'output_tokens': state.output_tokens,
                        'total_cost_usd': 0,
                        'session_id': state.result_session_id,
                        'tool_calls': len(state.tool_calls),
                        'error_recovery': True,
                    },
                    metadata={'error_type': 'exception_group'}
                )

            if state.streaming_done_event:
                state.streaming_done_event.set()

        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            elapsed_total = time.time() - state.stream_start_time
            logger.error(
                f"[AGENT_SDK] {error_type} {elapsed_total:.1f}s: {error_msg}",
                exc_info=True
            )

            user_message = error_msg
            if 'timeout' in error_msg.lower():
                user_message = "Tempo limite excedido. Tente uma consulta mais simples."
            elif 'connection' in error_msg.lower():
                user_message = "Erro de conexão com a API. Tente novamente em alguns segundos."

            yield StreamEvent(
                type='error',
                content=user_message,
                metadata={
                    'error_type': error_type,
                    'original_error': error_msg[:500],
                    'elapsed_seconds': elapsed_total,
                    'last_tool': state.current_tool_name,
                }
            )

            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={
                        'text': state.full_text,
                        'input_tokens': state.input_tokens,
                        'output_tokens': state.output_tokens,
                        'total_cost_usd': 0,
                        'session_id': state.result_session_id,
                        'tool_calls': len(state.tool_calls),
                        'error_recovery': True,
                    },
                    metadata={'error_type': error_type}
                )

            if state.streaming_done_event:
                state.streaming_done_event.set()

        finally:
            # CRITICAL: Sempre liberar prompt generator.
            # Cobre CancelledError, KeyboardInterrupt, SystemExit e qualquer
            # BaseException que bypasse os except handlers acima.
            # asyncio.CancelledError é BaseException (não Exception) desde Python 3.9.
            # Sem isto, _make_streaming_prompt bloqueia em done_event.wait(600)
            # mantendo subprocess CLI vivo por até 10 minutos (zombie).
            # Ref: DC-8 (CancelledError bypass)
            if state.streaming_done_event and not state.streaming_done_event.is_set():
                state.streaming_done_event.set()
                logger.warning(
                    "[AGENT_SDK] streaming_done_event released via finally "
                    f"(elapsed={time.time() - state.stream_start_time:.1f}s)"
                )

    @staticmethod
    async def _make_streaming_prompt(
        text: str,
        image_files: Optional[List[dict]] = None,
        done_event: Optional[asyncio.Event] = None,
    ):
        """
        Converte prompt string em AsyncIterable para compatibilidade com can_use_tool.

        CRÍTICO: can_use_tool exige streaming mode (AsyncIterable, não string).
        FONTE: _internal/client.py:53-58

        Args:
            text: Texto do prompt
            image_files: Lista de imagens em formato Vision API
            done_event: Event sinalizado quando ResultMessage é recebido.
                        Permite terminar o generator gracefully sem GeneratorExit.

        Yields:
            Dict no formato esperado pelo SDK streaming mode
        """
        if image_files:
            content_blocks = list(image_files) + [{"type": "text", "text": text}]
        else:
            content_blocks = text

        yield {
            "type": "user",
            "message": {"role": "user", "content": content_blocks}
        }

        # CRITICAL: Manter stream aberto para evitar race condition em stream_input().
        # Sem isso, stream_input() chama end_input() que fecha stdin do CLI.
        # Se houver _handle_control_request pendente (can_use_tool, hook, MCP),
        # o write falha com CLIConnectionError: ProcessTransport is not ready for writing.
        #
        # FIX-9: Usar done_event para terminar gracefully após ResultMessage.
        # Cadeia: done_event.set() → generator termina → stream_input() detecta fim
        # → chama end_input() → stdin fecha → CLI sai → receive_messages() termina
        # → process_query() retorna → async for sai naturalmente. Zero GeneratorExit.
        if done_event:
            try:
                await asyncio.wait_for(done_event.wait(), timeout=600)
            except asyncio.TimeoutError:
                logger.warning("[AGENT_SDK] _make_streaming_prompt timeout de segurança (10 min)")
        else:
            await asyncio.Event().wait()  # Fallback: comportamento antigo

    @staticmethod
    def _with_resume(options: 'ClaudeAgentOptions', sdk_session_id: str) -> 'ClaudeAgentOptions':
        """
        Retorna cópia do options com resume configurado.

        Usa dataclasses.replace() para criar cópia imutável.

        Args:
            options: ClaudeAgentOptions original
            sdk_session_id: Session ID do SDK para resume

        Returns:
            Novo ClaudeAgentOptions com resume=sdk_session_id
        """
        from dataclasses import replace
        return replace(options, resume=sdk_session_id)

    async def get_response(
        self,
        prompt: str,
        user_name: str = "Usuário",
        model: Optional[str] = None,
        sdk_session_id: Optional[str] = None,
        can_use_tool: Optional[Callable] = None,
        user_id: Optional[int] = None,
        our_session_id: Optional[str] = None,
        # LEGADO: aceitar pooled_client para compatibilidade (ignorado)
        pooled_client: Any = None,
    ) -> AgentResponse:
        """
        Obtém resposta completa (não streaming).

        Args:
            prompt: Mensagem do usuário
            user_name: Nome do usuário
            model: Modelo a usar
            sdk_session_id: Session ID do SDK para resume
            can_use_tool: Callback de permissão
            user_id: ID do usuário (para Memory Tool e hooks)
            our_session_id: Nosso UUID de sessão (chave do pool para path persistente)
            pooled_client: LEGADO — ignorado

        Returns:
            AgentResponse completa
        """
        full_text = ""
        tool_calls = []
        input_tokens = 0
        output_tokens = 0
        stop_reason = ""
        result_session_id = sdk_session_id
        errors = []  # Fix 2c: Capturar error events

        async for event in self.stream_response(
            prompt=prompt,
            user_name=user_name,
            model=model,
            sdk_session_id=sdk_session_id,
            can_use_tool=can_use_tool,
            user_id=user_id,
            our_session_id=our_session_id,
        ):
            if event.type == 'init':
                result_session_id = event.content.get('session_id')
            elif event.type == 'text':
                full_text += event.content
            elif event.type == 'error':
                # Fix 2c: Capturar mensagens de erro para montar texto sintetico
                error_content = event.content if isinstance(event.content, str) else str(event.content)
                errors.append(error_content)
                logger.warning(f"[AGENT_CLIENT] Error event em get_response: {error_content[:200]}")
            elif event.type == 'tool_call':
                tool_calls.append(ToolCall(
                    id=event.metadata.get('tool_id', ''),
                    name=event.content,
                    input=event.metadata.get('input', {})
                ))
            elif event.type == 'done':
                input_tokens = event.content.get('input_tokens', 0)
                output_tokens = event.content.get('output_tokens', 0)
                stop_reason = event.content.get('stop_reason', '')
                # Captura session_id real do done
                done_session_id = event.content.get('session_id')
                if done_session_id:
                    result_session_id = done_session_id

        # Fix 2c: Se full_text vazio mas houve errors, montar texto sintetico
        # Evita retornar AgentResponse(text="") que vira repr() no Teams
        if not full_text and errors:
            full_text = "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente."
            logger.warning(
                f"[AGENT_CLIENT] get_response: text vazio com {len(errors)} errors. "
                f"Usando texto sintetico. Errors: {'; '.join(errors[:3])}"
            )

        return AgentResponse(
            text=full_text,
            tool_calls=tool_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            stop_reason=stop_reason,
            session_id=result_session_id,
        )

    def health_check(self) -> Dict[str, Any]:
        """
        Verifica saúde da conexão com API.

        Usa models.retrieve() (zero tokens, ~200ms) em vez de
        messages.create() (~2s, gasta tokens).

        Returns:
            Dict com status da conexão
        """
        try:
            model_info = self._anthropic_client.models.retrieve(
                model_id=self.settings.model
            )

            return {
                'status': 'healthy',
                'model': model_info.id,
                'api_connected': True,
                'sdk': 'claude-agent-sdk',
            }

        except anthropic.AuthenticationError:
            return {
                'status': 'unhealthy',
                'error': 'API key inválida',
                'api_connected': False,
            }

        except anthropic.APIError as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'api_connected': False,
            }


# Singleton do cliente
_client: Optional[AgentClient] = None


def get_client() -> AgentClient:
    """
    Obtém instância do cliente (singleton).

    Returns:
        Instância de AgentClient
    """
    global _client
    if _client is None:
        _client = AgentClient()
    return _client


def reset_client() -> None:
    """Reseta o singleton do cliente."""
    global _client
    _client = None
