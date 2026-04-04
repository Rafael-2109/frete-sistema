"""
Pipeline de injeção de memórias para o AgentClient.

Auto-injeção de memórias do usuário, session window, routing context,
e scoring de memórias no hook UserPromptSubmit.

Todas as funções são module-level (sem dependência de instância).
Extraído de client.py em 2026-04-04.
"""

import logging
import time
from typing import Dict, Optional
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger('sistema_fretes')


# =====================================================================
# HELPER: Auto-injeção de memórias do usuário
# =====================================================================

_op_context_cache: Dict[int, tuple] = {}  # user_id -> (context_str, timestamp)
_OP_CONTEXT_TTL = 180  # 3 minutos — dados urgentes mudam na escala de horas


def _build_operational_context(user_id: int) -> Optional[str]: # type: ignore
    """
    DEPRECATED (P9): Desconectada do pipeline de injeção desde 2026-03.
    Mantida para possível reativação futura como skill.

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

        ttl_days = int(os.getenv('PENDENCIA_TTL_DAYS', '2'))
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
                parts.append('  <instruction>Para cada item: '
                             '1) Verifique se ja foi resolvido (consulte dados, verifique status). '
                             '2) Se resolvido: chame resolve_pendencia com o texto EXATO do item. '
                             '3) Se pode resolver agora: resolva e chame resolve_pendencia. '
                             '4) Se nao pode resolver: pergunte ao usuario como proceder.</instruction>')
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


# =====================================================================
# ROUTING CONTEXT — Contexto de despacho para decisão de roteamento
# =====================================================================

# Mapeamento domínio → keywords para detecção em session summaries
_DOMAIN_KEYWORDS = {
    'expedicao': ['separação', 'separacao', 'embarque', 'carreta', 'pallet', 'expedição',
                  'agrupamento de rota', 'casamento de rota', 'carga direta'],
    'odoo_compras': ['pedido de compra', 'vinculação', 'vinculacao', 'conciliação', 'conciliacao',
                     'validação nf', 'validacao nf', 'DFe', 'recebimento'],
    'odoo_financeiro': ['pagamento', 'extrato', 'reconciliação', 'reconciliacao', 'título', 'titulo',
                        'razão geral', 'razao geral', 'lançamento', 'lancamento'],
    'frete': ['frete', 'cotação', 'cotacao', 'transportadora', 'custo frete', 'lead time'],
    'ssw': ['ssw', 'romaneio', 'carvia', 'ctrc', 'mdf-e', 'ct-e'],
    'admin': ['diagnóstico', 'diagnostico', 'auditoria', 'memórias', 'memorias', 'sessões',
              'sessoes', 'health score', 'bug', 'investigar'],
}

# Mapeamento domínio → skills/subagentes relevantes
_DOMAIN_SKILLS = {
    'expedicao': ['gerindo-expedicao', 'cotando-frete', 'analista-carteira'],
    'odoo_compras': ['validacao-nf-po', 'conciliando-odoo-po', 'recebimento-fisico-odoo', 'especialista-odoo'],
    'odoo_financeiro': ['executando-odoo-financeiro', 'rastreando-odoo', 'razao-geral-odoo'],
    'frete': ['cotando-frete', 'gerindo-carvia'],
    'ssw': ['acessando-ssw', 'operando-ssw', 'gestor-ssw'],
    'admin': ['gerindo-agente', 'diagnosticando-banco', 'consultando-sentry'],
}

# Mapeamento domínio → segmentos de path reais usados pelo pattern_analyzer
# (pattern_analyzer usa domínio livre via Sonnet, ex: "financeiro", "recebimento")
_DOMAIN_PATH_SEGMENTS = {
    'expedicao': ['expedicao', 'logistica', 'agente'],
    'odoo_compras': ['recebimento', 'compras', 'odoo', 'integracao'],
    'odoo_financeiro': ['financeiro'],
    'frete': ['frete', 'carvia'],
    'ssw': ['ssw'],
    'admin': ['geral', 'sistema', 'agente'],
}


def _compute_user_domain(user_id: int) -> Optional[str]:
    """
    Computa domínio predominante do usuário a partir das últimas sessões.
    Zero-LLM: usa keyword matching nos summaries JSONB.

    Returns:
        Nome do domínio predominante ou None se insuficiente.
    """
    try:
        from ..models import AgentSession
        sessions = AgentSession.query.filter(
            AgentSession.user_id == user_id,
            AgentSession.summary.isnot(None),
        ).order_by(AgentSession.created_at.desc()).limit(10).all()

        if not sessions:
            return None

        domain_scores: dict = {}
        for session in sessions:
            summary = session.summary
            if not summary or not isinstance(summary, dict):
                continue
            # Combinar resumo_geral + alertas para texto de análise
            text_parts = []
            if summary.get('resumo_geral'):
                text_parts.append(summary['resumo_geral'])
            for alerta in (summary.get('alertas') or []):
                text_parts.append(str(alerta))
            text = ' '.join(text_parts).lower()

            for domain, keywords in _DOMAIN_KEYWORDS.items():
                hits = sum(1 for kw in keywords if kw.lower() in text)
                if hits > 0:
                    domain_scores[domain] = domain_scores.get(domain, 0) + hits

        if not domain_scores:
            return None

        # Domínio com mais hits
        return max(domain_scores, key=domain_scores.get)

    except Exception as e:
        logger.debug(f"[ROUTING_CONTEXT] Domain computation failed: {e}")
        return None


def _build_routing_context(user_id: int) -> Optional[str]:
    """
    Constrói contexto de despacho para routing do agente principal.
    Zero-LLM: SQL queries apenas. Max ~500 chars.

    Conteúdo:
    - Domínio predominante do usuário
    - Top 3 armadilhas ativas do domínio (ou gerais se domínio indeterminado)
    - Skills sugeridas para o domínio

    Returns:
        String XML para injeção ou None se vazio.
    """
    try:
        from ..models import AgentMemory
        import re

        domain = _compute_user_domain(user_id)

        parts = ['<routing_context>']

        # Domínio predominante
        if domain:
            domain_display = domain.replace('_', '/').title()
            skills = _DOMAIN_SKILLS.get(domain, [])
            parts.append(f'  <user_domain>{domain_display}</user_domain>')
            if skills:
                parts.append(f'  <preferred_skills>{", ".join(skills[:3])}</preferred_skills>')

        # Armadilhas ativas (filtradas por domínio se disponível)
        armadilha_filter = AgentMemory.query.filter(
            AgentMemory.user_id == 0,
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.is_cold == False,  # noqa: E712
        )
        if domain:
            # Buscar armadilhas dos path segments reais do domínio
            path_segments = _DOMAIN_PATH_SEGMENTS.get(domain, [domain])
            from sqlalchemy import or_ as sql_or
            armadilha_filter = armadilha_filter.filter(
                sql_or(*[
                    AgentMemory.path.like(f'/memories/empresa/armadilhas/{seg}%')
                    for seg in path_segments
                ])
            )
        else:
            armadilha_filter = armadilha_filter.filter(
                AgentMemory.path.like('/memories/empresa/armadilhas/%')
            )

        armadilhas = armadilha_filter.order_by(
            AgentMemory.effective_count.desc()
        ).limit(3).all()

        if armadilhas:
            parts.append('  <active_traps>')
            for arm in armadilhas:
                content = arm.content or ''
                # Suporta formato XML legado (<titulo>/<prescricao>) e novo (WHEN/DO)
                title_match = re.search(r'<titulo>(.*?)</titulo>', content, re.DOTALL)
                if title_match:
                    # Formato XML legado
                    title = title_match.group(1).strip()
                    presc_match = re.search(r'<prescricao>(.*?)</prescricao>', content, re.DOTALL)
                    prescricao = presc_match.group(1).strip() if presc_match else ''
                else:
                    # Formato compacto WHEN/DO
                    lines = content.strip().split('\n')
                    title = lines[0].strip() if lines else arm.path.split('/')[-1].replace('.xml', '')
                    # Extrair DO: line
                    prescricao = ''
                    for line in lines:
                        if line.strip().startswith('DO:'):
                            prescricao = line.strip()[3:].strip()
                            break

                if len(title) > 80:
                    title = title[:77] + '...'
                if prescricao:
                    if len(prescricao) > 200:
                        prescricao = prescricao[:197] + '...'
                    parts.append(f'    - {title}\n      DO: {prescricao}')
                else:
                    parts.append(f'    - {title}')
            parts.append('  </active_traps>')

        parts.append('</routing_context>')

        # Só retornar se tem conteúdo útil (mais que tags vazias)
        if len(parts) <= 2:  # Só tem abertura e fechamento
            return None

        result = '\n'.join(parts)
        logger.debug(f"[ROUTING_CONTEXT] user_id={user_id} domain={domain} chars={len(result)}")
        return result

    except Exception as e:
        logger.debug(f"[ROUTING_CONTEXT] Build failed: {e}")
        return None


def _load_user_memories_for_context(user_id: int, prompt: str = None, model_name: str = None) -> tuple[Optional[str], list[int]]:
    """
    Carrega memórias do usuário e formata como contexto para injeção.

    Memory System v2 — Arquitetura em 4 tiers:
    - Tier 0 (SEMPRE): Rolling window de sessões + briefing inter-sessão + routing context
    - Tier 1 (SEMPRE): user.xml e preferences.xml — garante identidade/preferências
    - Tier 1.5 (SEMPRE): Perfil empresa do usuário — contexto de routing
    - Tier 2 (semântica): memórias relevantes ao prompt, excluindo Tier 1
    - Tier 2b (KG): complementar via Knowledge Graph
    - Fallback: memórias mais recentes se semântica não retornar nada

    v2 changes:
    - Tier 0: session window + routing context (operational context removido — P9)
    - Two-pass budget selection by composite score (1D)
    - Category-aware decay rates
    - Exclude cold memories from retrieval
    - Per-tier char logging
    - Increment usage_count on injection

    Budget adaptativo (T2-2):
    - Opus: sem limite (1M context) — injetar todas as memórias retornadas
    - Sonnet: 6000 chars (~1500 tokens)
    - Haiku: 3000 chars (~750 tokens)
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

            # ── Tier 0: Rolling window de sessões (Memory v2) ──
            # Nota: _build_operational_context() removido (P9 — desconectado, só ruído).
            # Mantida como função para uso futuro como skill, mas não injetada no contexto.
            tier0_parts = []
            tier0_chars = 0

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

            # ── Tier 0c: Routing context (domínio + armadilhas) ──
            try:
                routing_ctx = _build_routing_context(user_id)
                if routing_ctx:
                    tier0_parts.append(routing_ctx)
                    tier0_chars += len(routing_ctx)
            except Exception as route_err:
                logger.debug(f"[MEMORY_INJECT] Routing context falhou (ignorado): {route_err}")

            # ── Tier 1: SEMPRE injetar memórias protegidas ──
            PROTECTED_PATHS = ["/memories/user.xml", "/memories/preferences.xml"]
            protected_memories = AgentMemory.query.filter(
                AgentMemory.user_id == user_id,
                AgentMemory.path.in_(PROTECTED_PATHS),
                AgentMemory.is_directory == False,  # noqa: E712
            ).all()

            protected_ids = {m.id for m in protected_memories}

            # ── Tier 1.5: Perfil empresa do usuário (always-inject para routing) ──
            # Se existe um perfil empresa para este user_id, injetá-lo
            # (ex: /memories/empresa/usuarios/elaine.xml para user_id=67)
            tier15_memories = []
            try:
                tier15_query = AgentMemory.query.filter(
                    AgentMemory.user_id == 0,  # empresa
                    AgentMemory.is_directory == False,  # noqa: E712
                    AgentMemory.is_cold == False,  # noqa: E712
                    AgentMemory.path.like('/memories/empresa/usuarios/%'),
                ).all()
                # Filtrar: injetar apenas se o perfil menciona o user_id atual
                # ou se é perfil genérico útil para routing
                for mem in tier15_query:
                    content_lower = (mem.content or '').lower()
                    user_id_str = str(user_id)
                    # Injetar se o perfil contém o user_id do usuário atual
                    if f'<user_id>{user_id_str}</user_id>' in content_lower or \
                       f'user_id={user_id_str}' in content_lower or \
                       f"user_id>{user_id_str}<" in content_lower:
                        tier15_memories.append(mem)
                        protected_ids.add(mem.id)
            except Exception as t15_err:
                logger.debug(f"[MEMORY_INJECT] Tier 1.5 falhou (ignorado): {t15_err}")

            # ── Tier 1.6: Heuristicas empresa nivel 5 (SEMPRE injetadas, como user.xml) ──
            # Armadilhas nivel 5 sao heuristicas emergentes de alto valor (~3-5 por empresa).
            # Deveriam estar SEMPRE no contexto para prevencao proativa de erros.
            tier16_memories = []
            try:
                tier16_query = AgentMemory.query.filter(
                    AgentMemory.user_id == 0,  # empresa
                    AgentMemory.is_directory == False,  # noqa: E712
                    AgentMemory.is_cold == False,  # noqa: E712
                    AgentMemory.path.like('/memories/empresa/heuristicas/%'),
                ).all()
                # Filtrar: apenas memorias com nivel >= 5 no conteudo
                for mem in tier16_query:
                    content_lower = (mem.content or '').lower()
                    # Checar nivel 5+ (heuristicas emergentes)
                    if any(f'nivel={n}' in content_lower for n in range(5, 10)) and mem.id not in protected_ids:
                        tier16_memories.append(mem)
                        protected_ids.add(mem.id)
                if tier16_memories:
                    logger.info(
                        f"[MEMORY_INJECT] Tier 1.6: {len(tier16_memories)} heuristicas nivel 5 injetadas"
                    )
            except Exception as t16_err:
                logger.debug(f"[MEMORY_INJECT] Tier 1.6 falhou (ignorado): {t16_err}")

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
            # Opus: sem limite (1M context) — injetar todas as memórias retornadas
            # Sonnet/Haiku: budget para manter conciso
            _model = (model_name or "").lower()
            if "opus" in _model:
                base_budget = None  # sem limite — 1M context
            elif "haiku" in _model:
                base_budget = 3000
            else:
                base_budget = 6000  # Sonnet ou desconhecido

            # Fator de ajuste: prompts longos consomem context window, reduzir budget
            prompt_len = len(prompt) if prompt else 0
            if base_budget is not None:
                prompt_factor = max(0.5, 1.0 - prompt_len / 10000)
                budget = int(base_budget * prompt_factor)
            else:
                budget = None  # Opus: sem budget

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

            # Tier 1.5: perfis empresa (routing context, sempre incluídos)
            tier15_texts = []
            tier15_chars = 0
            for mem in tier15_memories:
                content = (mem.content or "").strip()
                if not content:
                    continue
                # Truncar perfis longos a 400 chars para não sobrecarregar
                if len(content) > 400:
                    content = content[:400] + "..."
                mem_text = f'<memory path="{mem.path}" tier="routing">\n{content}\n</memory>\n'
                tier15_texts.append((mem, mem_text))
                tier15_chars += len(mem_text)

            # Tier 1.6: heuristicas empresa nivel 5 (sempre incluídas)
            tier16_texts = []
            tier16_chars = 0
            for mem in tier16_memories:
                content = (mem.content or "").strip()
                if not content:
                    continue
                mem_text = f'<memory path="{mem.path}" tier="heuristica">\n{content}\n</memory>\n'
                tier16_texts.append((mem, mem_text))
                tier16_chars += len(mem_text)

            # Budget restante para Tier 2 + 2b (None = sem limite para Opus)
            budget_remaining = (budget - overhead - tier1_chars - tier15_chars - tier16_chars) if budget is not None else None

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
                # Opus (budget_remaining=None): incluir todas as memórias sem corte
                if budget_remaining is not None and tier2_chars + tier2b_chars + mem_len > budget_remaining:
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

            for mem, mem_text in tier15_texts:
                selected_parts.append(mem_text)
                injected_mems.append(mem)

            for mem, mem_text in tier16_texts:
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
            budget_pct = round(total_chars / budget * 100) if budget and budget > 0 else 0
            skipped_budget = len(tier2_candidates) - len(selected_tier2)

            # ── Observabilidade: paths de memorias injetadas por tier ──
            tier1_paths = [m.path for m in protected_memories if m.content]
            tier15_paths = [m.path for m, _ in tier15_texts]
            tier16_paths = [m.path for m, _ in tier16_texts]
            tier2_paths = [m.path for m, _ in selected_tier2]
            all_injected_paths = tier1_paths + tier15_paths + tier16_paths + tier2_paths

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
                f"budget={budget or 'unlimited'} | "
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
                f"budget_remaining={max(0, budget_remaining - tier2_chars - tier2b_chars) if budget_remaining is not None else 'unlimited'} | "
                f"min_similarity_threshold={MEMORY_INJECTION_MIN_SIMILARITY} | "
                f"prompt_preview={prompt[:50] if prompt else 'None'}"
            )
            # Log complementar com paths individuais para auditoria/debug
            if all_injected_paths:
                logger.info(
                    f"[MEMORY_INJECT_PATHS] user_id={user_id} | "
                    f"tier1={tier1_paths} | "
                    f"tier1.5={tier15_paths} | "
                    f"tier1.6={tier16_paths} | "
                    f"tier2={tier2_paths}"
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
