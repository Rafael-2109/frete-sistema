"""
Pipeline de injeção de memórias para o AgentClient.

Auto-injeção de memórias do usuário, session window, routing context,
e scoring de memórias no hook UserPromptSubmit.

Todas as funções são module-level (sem dependência de instância).
Extraído de client.py em 2026-04-04.

Fase 5 (2026-04-21): cache por sessao + invalidacao em mutacao.
Reduz consultas redundantes em sessoes de multi-turno repetitivas
(ex: Gabriella 13 consultas de memoria em 28 msgs — pattern observado).
"""

import logging
import os
import threading
import time as _time_module
from typing import Optional
from app.utils.timezone import agora_utc_naive
from ._sanitization import xml_escape, sanitize_memory_content

logger = logging.getLogger('sistema_fretes')


# ======================================================================
# F4 PAD-CTX (2026-06-09): orcamento por bloco do hook dinamico
# ======================================================================
# Tabela canonica: ARQUITETURA_CONTEXTO_AGENTE.md secao "Hook dinamico —
# layout, orcamento e ordem". Enforcement no _load_user_memories_for_context
# (cap por memoria/bloco no Tier 2 + ordem de corte no overflow via
# _fit_hook_budget). Motivacao: fallback de recencia injetava ~63KB/turno
# com budget=unlimited no Opus (backlog do plano 2026-06-09).
HOOK_CONTEXT_TARGET_CHARS = 15_000  # teto total main+tail (<=15KB/turno)
TIER2_MEMORY_CHAR_CAP = 300         # teto por memoria Tier 2 (destilado + ponteiro)
TIER2_MAX_MEMORIES = 4              # bloco Tier 2 = 4 x ~300c (tabela PAD-CTX item 6)

# F5.5 PAD-CTX: few-shot episodico condicional. Threshold calibrado na
# distribuicao REAL do voyage-4-lite query->doc (PROD 2026-06-09: 0.24-0.55;
# o cosine 0.75 do plano nunca dispararia). 0.55 = match excepcional.
FEWSHOT_MIN_SIMILARITY = float(
    os.getenv('AGENT_FEWSHOT_MIN_SIMILARITY', '0.55')
)
FEWSHOT_CONTENT_CAP = 1_200         # exemplo entra (quase) completo, com teto


# ======================================================================
# Fase 5 (2026-04-21): Cache de injecao de memoria por sessao
# ======================================================================
# Estrutura: {session_id: (main_context, tail_context, mem_ids, timestamp, user_id)}
# (F4.4: payload dividido em main [blocos 3-9] + tail [recent_sessions+pendencias])
# TTL: 30 minutos OU invalidacao manual via mutacao de memoria.
# Memoria Invalidacao: _INVALIDATED_USERS set — consumido e limpo na proxima
# consulta do user. Permite invalidacao cross-session sem iterar cache inteiro.
_SESSION_INJECTION_CACHE: dict[str, tuple[Optional[str], Optional[str], list[int], float, int]] = {}
_INVALIDATED_USERS: set[int] = set()
_INJECTION_CACHE_TTL_SEC = 1800  # 30 minutos
_INJECTION_CACHE_LOCK = threading.Lock()
_INJECTION_CACHE_MAX_SIZE = 500  # Evita leak se sessoes nao forem limpas


def invalidate_injection_cache_for_user(user_id: int) -> None:
    """
    Remove TODAS as entries de cache do user_id atomicamente.

    Fix pos-review (2026-04-21): antes usava flag `_INVALIDATED_USERS` consumida
    pela primeira session a fazer `_cache_get` — race entre sessoes concorrentes
    (Web + Teams, ou 2 tabs) deixava algumas servindo contexto stale. Agora
    evictamos TODAS as entries do user na hora da invalidacao.

    Chamado por memory_mcp_tool em save_memory / update_memory / delete_memory.
    """
    if not user_id:
        return
    with _INJECTION_CACHE_LOCK:
        sids_to_evict = [
            sid for sid, entry in _SESSION_INJECTION_CACHE.items()
            if entry[4] == user_id  # entry = (main, tail, ids, ts, cached_uid)
        ]
        for sid in sids_to_evict:
            del _SESSION_INJECTION_CACHE[sid]
        # Remover flag se ainda presente (legado — nao mais necessario)
        _INVALIDATED_USERS.discard(user_id)
    logger.debug(
        f"[memory_injection] cache invalidated for user={user_id} "
        f"evicted={len(sids_to_evict)} sessions"
    )


def _cache_get(
    session_id: str, user_id: int
) -> Optional[tuple[Optional[str], Optional[str], list[int]]]:
    """
    Retorna (main_context, tail_context, mem_ids) do cache se valido, ou None.

    Valido = TTL nao expirou AND user_id do cache bate com o atual.
    Invalidacao por mutacao e tratada em `invalidate_injection_cache_for_user`
    (evicta todas entries do user ao inves de usar flag consumivel).
    """
    if not session_id or not user_id:
        return None
    with _INJECTION_CACHE_LOCK:
        entry = _SESSION_INJECTION_CACHE.get(session_id)
        if entry is None:
            return None
        main, tail, ids, ts, cached_uid = entry
        if cached_uid != user_id:
            # Session trocou de user (edge case) — invalidar
            del _SESSION_INJECTION_CACHE[session_id]
            return None
        if _time_module.time() - ts > _INJECTION_CACHE_TTL_SEC:
            del _SESSION_INJECTION_CACHE[session_id]
            return None
        return main, tail, list(ids)


def _cache_put(
    session_id: str,
    user_id: int,
    main: Optional[str],
    tail: Optional[str],
    mem_ids: list[int],
) -> None:
    """Armazena context no cache. Evicta entries mais antigas se overflow."""
    if not session_id or not user_id:
        return
    with _INJECTION_CACHE_LOCK:
        # Evict oldest se tamanho excedeu (simple LRU by timestamp)
        if len(_SESSION_INJECTION_CACHE) >= _INJECTION_CACHE_MAX_SIZE:
            oldest_sid = min(
                _SESSION_INJECTION_CACHE.keys(),
                key=lambda k: _SESSION_INJECTION_CACHE[k][3],
            )
            del _SESSION_INJECTION_CACHE[oldest_sid]
        _SESSION_INJECTION_CACHE[session_id] = (
            main,
            tail,
            list(mem_ids),
            _time_module.time(),
            user_id,
        )


# =====================================================================
# HELPER: Auto-injeção de memórias do usuário
# =====================================================================



def _normalize_pendencia(text: str) -> str:
    """Normaliza texto de pendência para comparação: lowercase, strip, collapse whitespace."""
    import re
    return re.sub(r'\s+', ' ', text.strip().lower())


def _is_nivel_5(content_lower: str) -> bool:
    """
    Detecta se conteudo de memoria representa heuristica nivel 5-9 (alto valor).

    Fonte unica para `_build_operational_directives` (Tier 0) e `Tier 1.6`.
    Aceita: 'nivel=5', 'nivel: 5', 'nivel "5"', 'nivel  5', '<nivel>5</nivel>', etc.

    NAO alterar sem atualizar ambos os callers — ver memory_injection.py:362 e :685.
    """
    import re
    return bool(re.search(r'nivel\s*[=:"\s>]+[5-9]', content_lower))


def _build_session_window(user_id: int) -> tuple[Optional[str], Optional[str]]:
    """
    Memory v2 — Rolling Window: últimas 5 sessões do banco.

    Query direta em agent_sessions.summary (JSONB) — sem XML intermediário.
    Cada sessão formatada como ~150 chars.

    F4.4a PAD-CTX (item D3): pendencias_acumuladas saem como bloco SEPARADO —
    o caller as posiciona por ULTIMO no payload (coladas a mensagem do usuario,
    mitigando lost-in-the-middle).

    Pendências têm lifecycle:
    - TTL automático: pendências de sessões mais antigas que PENDENCIA_TTL_DAYS são ignoradas
    - Resolução manual: pendências em /memories/system/resolved_pendencias.json são filtradas

    Returns:
        Tupla (sessions_block, pendencias_block) — cada um XML compacto ou None.
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
            return None, None

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

                # G4: resumo e texto simples do summary JSONB — xml_escape
                compact = f'<session date="{data}">{xml_escape(resumo)}'
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

        parts.append('</recent_sessions>')
        sessions_block = '\n'.join(parts)

        # Pendências acumuladas (dedupadas + filtro de resolvidas) — bloco separado
        pendencias_block = None
        if pendencias_all:
            unique_pend = list(dict.fromkeys(pendencias_all))[:5]  # Max 5, preserva ordem

            # Filtrar pendências já resolvidas (matching normalizado)
            resolved = _load_resolved_pendencias(user_id)
            if resolved:
                unique_pend = [p for p in unique_pend if _normalize_pendencia(p) not in resolved]

            if unique_pend:
                pend_parts = ['<pendencias_acumuladas>']
                pend_parts.append('  <instruction>Para cada item: '
                                  '1) Verifique se ja foi resolvido (consulte dados, verifique status). '
                                  '2) Se resolvido: chame resolve_pendencia com o texto EXATO do item. '
                                  '3) Se pode resolver agora: resolva e chame resolve_pendencia. '
                                  '4) Se nao pode resolver: pergunte ao usuario como proceder.</instruction>')
                for p in unique_pend:
                    # G4: p e texto simples de summary JSONB — xml_escape
                    pend_parts.append(f'  <item>{xml_escape(p)}</item>')
                pend_parts.append('</pendencias_acumuladas>')
                pendencias_block = '\n'.join(pend_parts)

        return sessions_block, pendencias_block

    except Exception as e:
        logger.debug(f"[MEMORY_INJECT] Session window falhou (ignorado): {e}")
        return None, None


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


def _memory_open_tag(mem, tier: str = None) -> str:
    """Tag de abertura <memory> enriquecida com atributos do meta canonico
    (kind/dominio/nivel) quando disponivel — apresentacao XML estruturada para o
    Claude. getattr: robusto a objetos sem coluna meta (legado / mock de teste).

    F5.3 PAD-CTX (proveniencia cross-user-safe — ARQUITETURA_CONTEXTO_AGENTE.md
    §Memorias): memoria PESSOAL expoe session= (navegavel via search_sessions) +
    date=; memoria EMPRESA (user_id=0) expoe APENAS created_by= + date= — o UUID
    de sessao alheia NUNCA vaza (search_sessions e per-user; cross-user e gated
    por debug_mode).
    """
    attrs = [f'path="{xml_escape(mem.path)}"']
    if tier:
        attrs.append(f'tier="{tier}"')
    meta = getattr(mem, 'meta', None)
    if isinstance(meta, dict):
        if meta.get('kind'):
            attrs.append(f'kind="{xml_escape(str(meta["kind"]))}"')
        if meta.get('dominio'):
            attrs.append(f'dominio="{xml_escape(str(meta["dominio"]))}"')
        if meta.get('nivel') is not None:
            attrs.append(f'nivel="{xml_escape(str(meta["nivel"]))}"')
    updated = getattr(mem, 'updated_at', None)
    if updated is not None:
        try:
            attrs.append(f'date="{updated.strftime("%d/%m/%Y")}"')
        except (AttributeError, ValueError):
            pass
    if getattr(mem, 'user_id', None) == 0:
        created_by = getattr(mem, 'created_by', None)
        if created_by:
            attrs.append(f'created_by="{xml_escape(str(created_by))}"')
    else:
        source_sid = getattr(mem, 'source_session_id', None)
        if source_sid:
            attrs.append(f'session="{xml_escape(str(source_sid))}"')
    return '<memory ' + ' '.join(attrs) + '>'


def _is_episodic_memory(mem) -> bool:
    """F5.5 PAD-CTX: memoria EPISODICA = caso/correcao concreta (candidata a
    few-shot). Criterio: kind canonico 'correcao' OU path em /corrections/ ou
    /casos/."""
    meta = getattr(mem, 'meta', None)
    if isinstance(meta, dict) and meta.get('kind') == 'correcao':
        return True
    path = getattr(mem, 'path', '') or ''
    return '/corrections/' in path or '/casos/' in path


def _render_tier2_candidate(mem, content: str, similarity: float = 0.0) -> str:
    """F5.5 PAD-CTX: renderiza candidato Tier 2 — destilado 300c por padrao,
    OU exemplo few-shot (quase) completo quando o match e EXCEPCIONAL
    (similarity >= FEWSHOT_MIN_SIMILARITY) com memoria EPISODICA.

    Threshold calibrado na distribuicao REAL do voyage-4-lite query->doc
    (PROD 2026-06-09: scores vivem em 0.24-0.55; o 0.75 planejado nunca
    dispararia). Exemplo tem cap proprio (FEWSHOT_CONTENT_CAP) — exemplo
    trabalhado > resumo, mas nao sem teto.
    """
    if similarity >= FEWSHOT_MIN_SIMILARITY and _is_episodic_memory(mem):
        if len(content) > FEWSHOT_CONTENT_CAP:
            pointer = f'\n[integra] view_memories("{xml_escape(mem.path)}")'
            content = content[:FEWSHOT_CONTENT_CAP].rstrip() + '…' + pointer
        return f'{_memory_open_tag(mem, "exemplo")}\n{content}\n</memory>\n'
    content = _distill_tier2_content(mem, content)
    return f'{_memory_open_tag(mem)}\n{content}\n</memory>\n'


def _distill_tier2_content(mem, content: str) -> str:
    """F4.3 PAD-CTX: teto ~300c por memoria Tier 2.

    Memoria curta (<= TIER2_MEMORY_CHAR_CAP) entra integral, sem ponteiro.
    Memoria longa e DESTILADA: preferir meta canonico (titulo + WHEN/DO —
    2026-06-08) sobre o content bruto; truncar ao cap e anexar ponteiro
    `view_memories(path)` para a integra. Memoria de 27 linhas nao entra
    inteira no boot (PAD-CTX secao Memorias).

    Args:
        mem: AgentMemory (ou objeto com .path e .meta opcional)
        content: conteudo JA sanitizado (sanitize_memory_content no caller)
    """
    if len(content) <= TIER2_MEMORY_CHAR_CAP:
        return content

    distilled = None
    meta = getattr(mem, 'meta', None)
    if isinstance(meta, dict) and ((meta.get('when') or meta.get('do'))):
        bits = []
        if (meta.get('titulo') or '').strip():
            bits.append(str(meta['titulo']).strip())
        if (meta.get('when') or '').strip():
            bits.append('WHEN: ' + str(meta['when']).strip())
        if (meta.get('do') or '').strip():
            bits.append('DO: ' + str(meta['do']).strip())
        if bits:
            # meta vem do JSONB (fora do caminho sanitizado do content)
            distilled = sanitize_memory_content(
                '\n'.join(bits), source=f"mem_id={getattr(mem, 'id', '?')} meta-distill"
            )

    if not distilled:
        distilled = content

    if len(distilled) > TIER2_MEMORY_CHAR_CAP:
        distilled = distilled[:TIER2_MEMORY_CHAR_CAP - 3] + '...'

    pointer = f'\n[integra] view_memories("{xml_escape(mem.path)}")'
    return distilled + pointer


def _fit_hook_budget(
    parts: dict, target: int = HOOK_CONTEXT_TARGET_CHARS
) -> tuple[dict, list[str]]:
    """F4.3 PAD-CTX: ordem de corte no overflow do hook dinamico.

    Corta na ordem: Tier 2 RAG -> directives ORGANICAS (constitucional fica) ->
    routing_context. NUNCA corta os blocos fixos (user_rules, tier1/1.5/1.6,
    briefing, recent_sessions, pendencias) — representados por 'fixed_chars'.
    Se apos os 3 cortes ainda estourar, retorna assim mesmo (nao ha mais o
    que cortar sem violar os intocaveis).

    Args:
        parts: {'fixed_chars': int, 'tier2': str, 'directives_full': str,
                'directives_const': str, 'routing': str}
        target: teto em chars (default HOOK_CONTEXT_TARGET_CHARS)

    Returns:
        ({'tier2': str, 'directives': str, 'routing': str}, lista de cortes)
    """
    fixed = int(parts.get('fixed_chars') or 0)
    resolved = {
        'tier2': parts.get('tier2') or '',
        'directives': parts.get('directives_full') or '',
        'routing': parts.get('routing') or '',
    }
    cortes: list[str] = []

    def _total() -> int:
        return fixed + len(resolved['tier2']) + len(resolved['directives']) + len(resolved['routing'])

    if _total() <= target:
        return resolved, cortes

    resolved['tier2'] = ''
    cortes.append('tier2')
    if _total() <= target:
        return resolved, cortes

    resolved['directives'] = parts.get('directives_const') or ''
    cortes.append('directives_organicas')
    if _total() <= target:
        return resolved, cortes

    resolved['routing'] = ''
    cortes.append('routing')
    return resolved, cortes


# =====================================================================
# USER.XML POINTER — Camada 2 da Mudanca 4 (v2.2, 2026-04-12)
# =====================================================================
# Quando user.xml excede threshold e budget Sonnet/Haiku e finito,
# injetar versao parcial contendo apenas <resumo> + <contextualizacao>
# + ponteiro instruindo o agente a chamar view_memories para detalhes.
# Preserva informacao sem truncate destrutivo e sem parser XML complexo.
# Camada 1 (guidance no gerador) e a solucao de causa raiz — esta
# camada 2 cobre o periodo de transicao ate re-geracao natural.


def _build_user_profile_pointer(content: str) -> str:
    """
    Constroi versao parcial de user.xml com ponteiro para a versao completa.

    Extrai apenas <resumo> e <contextualizacao> (blocos prescritivos).
    Se regex nao encontrar NENHUM dos dois, retorna content original
    (fallback seguro — nao degrada o estado atual).

    Args:
        content: Conteudo completo do user.xml

    Returns:
        String XML parcial com ponteiro, ou content original se fallback.
    """
    import re
    resumo = re.search(r'<resumo>.*?</resumo>', content, re.DOTALL)
    contexto = re.search(
        r'<contextualizacao.*?</contextualizacao>',
        content,
        re.DOTALL,
    )
    if not resumo and not contexto:
        return content  # Fallback: regex falhou, preserva original

    parts = ['<user_profile_partial reason="tamanho_excede_budget">']
    if resumo:
        parts.append(f'  {resumo.group(0)}')
    if contexto:
        parts.append(f'  {contexto.group(0)}')
    parts.append(
        '  <pointer>Perfil completo (atividades, clientes, insights) em '
        '/memories/user.xml. Use view_memories("/memories/user.xml") '
        'se precisar de detalhes operacionais.</pointer>'
    )
    parts.append('</user_profile_partial>')
    return '\n'.join(parts)


# =====================================================================
# ROUTING CONTEXT — Contexto de despacho para decisão de roteamento
# =====================================================================
# Nota (v2.2, 2026-04-12): removido _adjust_importance_for_corrections e
# constantes _CORRECTION_PENALTY_* — era dead code. correction_count = 0
# em 197/197 memórias (nada incrementa o contador). A função legacy
# sempre retornava importance inalterado. Coluna correction_count
# permanece em models.py para backwards-compat do dashboard insights.

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
    # F0.3 PAD-CTX (2026-06-09): entry 'admin' REMOVIDA — mapeava 3 skills dev-only
    # (gerindo-agente, diagnosticando-banco, consultando-sentry) com 0-2 usos em 90d
    # (finding A5), todas fora do listing do principal a partir da F2. Dominio 'admin'
    # segue valido para deteccao de armadilhas (_DOMAIN_PATH_SEGMENTS), apenas sem
    # preferred_skills. Derivacao por uso real: F7.5 do plano (backlog).
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


# ---------------------------------------------------------------------------
# Diretiva(s) constitucional(is) — pinadas no bloco <operational_directives>.
# Sempre injetadas (independem de effective_count/cap das heuristicas organicas);
# promovidas por decisao EXPLICITA do usuario, nao pelo flywheel A4.
#
# registro-melhorias (2026-06-06, sessao da fatura 161-9): afrouxa o gatilho de
# register_improvement para incluir CASOS SUTIS (suspeita de atrito que impacta o
# agente, sem reproducao/evidencia/fix) com prioridade IGUAL ao concreto, e fixa o
# principio de que auto-capacitar-se e o proposito do sistema — nao overhead.
# Espelha a R9 do system_prompt.md (defense-in-depth: corpo do prompt + R0d).
# ---------------------------------------------------------------------------
_CONSTITUTIONAL_DIRECTIVES = [
    {
        'id': 'registro-melhorias',
        'titulo': 'Registrar melhorias proativamente — inclusive casos sutis',
        'when': (
            'Suspeitar de bug em skill/service, gotcha do ambiente, lacuna de '
            'instrucao/prompt, OU qualquer atrito que afete a SUA propria capacidade '
            'de operar — mesmo sem reproducao, evidencia completa ou fix em maos.'
        ),
        'do': (
            'Registrar via register_improvement no momento da descoberta OU da '
            'suspeita (nao esperar o batch D8). Caso sutil = prioridade IGUAL ao '
            'concreto. Sem fix em maos? Registrar hipotese + sintoma e deixar o '
            'Claude Code (dev) completar o diagnostico. Auto-capacitar-se e o '
            'proposito do sistema, nao overhead a justificar.'
        ),
    },
]


def _render_operational_directives(directives: list[str]) -> Optional[str]:
    """Envelopa itens <directive> ja renderizados no bloco <operational_directives>.

    F4.3 PAD-CTX: separado do builder para a politica de overflow poder
    re-renderizar o bloco SO com a(s) constitucional(is) sem re-query.
    """
    if not directives:
        return None
    parts = [
        '<operational_directives priority="critical">',
        '  <!-- Diretivas obrigatorias de operacao. Verifique WHEN antes de responder -->',
        '  <!-- e aplique DO silenciosamente se aplicavel. Violar = erro grave. -->',
    ]
    parts.extend(directives)
    parts.append('</operational_directives>')
    return '\n'.join(parts)


def _build_operational_directives(user_id: int) -> Optional[str]:
    """
    Constroi bloco <operational_directives> com heuristicas empresa nivel 5
    de alta confianca (importance >= 0.7). Estas sao promovidas de "contexto
    passivo" para "diretriz operacional obrigatoria" — o system_prompt.md
    instrui o agente a tratar este bloco como regra, nao como referencia.

    Wrapper de compatibilidade sobre _build_operational_directives_parts
    (F4.3 separa constitucional/organicas p/ a politica de overflow).
    """
    const_items, org_items = _build_operational_directives_parts(user_id)
    result = _render_operational_directives(const_items + org_items)
    if result:
        logger.info(
            f"[OPERATIONAL_DIRECTIVES] user_id={user_id} "
            f"directives={len(const_items) + len(org_items)} chars={len(result)}"
        )
    return result


def _build_operational_directives_parts(user_id: int) -> tuple[list[str], list[str]]:
    """
    Itens <directive> renderizados, separados em (constitucionais, organicas).

    Constitucionais: pinadas em _CONSTITUTIONAL_DIRECTIVES (promovidas por
    decisao explicita do usuario; NUNCA cortadas pela politica de overflow).
    Organicas: heuristicas/protocolos empresa nivel 5 top effective_count
    (cap MANDATORY_MAX_COUNT; cortaveis no overflow — F4.3 PAD-CTX).

    Inspirado na arquitetura do Claude Code: CLAUDE.md e carregado no
    system_prompt como instrucao de alta prioridade, nao como user memory.
    Nao da para colocar memorias dinamicas no system_prompt sem invalidar
    cache, entao imitamos o efeito via framing explicito + instrucao no
    system_prompt ensinando o agente a obedecer.

    Zero LLM. Zero schema change. Deterministico.

    v2.2 (2026-04-12) — substitui proposta de judge LLM da v1 do plano.

    Args:
        user_id: ID do usuario (nao usado na query, mas mantido para
            interface consistente com _build_routing_context)

    Returns:
        Tupla (constitucionais, organicas) — listas de strings XML (vazias
        se flag off ou erro).
    """
    try:
        from ..models import AgentMemory
        from ..config.feature_flags import (
            USE_OPERATIONAL_DIRECTIVES,
            MANDATORY_IMPORTANCE_THRESHOLD,
            MANDATORY_MAX_COUNT,
        )
        import re as _re

        if not USE_OPERATIONAL_DIRECTIVES:
            return [], []

        # Buscar heuristicas empresa de alta importancia (nivel 5)
        # Ordenar por effective_count desc (mais aplicadas primeiro)
        # Aceita tanto /heuristicas/ (confianca estabelecida) quanto /protocolos/
        # (regras operacionais explicitas, ex: baseline, formatos travados).
        # Ref: docs/superpowers/plans/2026-04-16-memory-system-redesign.md Task 5
        from sqlalchemy import or_ as sql_or
        candidates = AgentMemory.query.filter(
            AgentMemory.user_id == 0,
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.is_cold == False,  # noqa: E712
            sql_or(
                AgentMemory.path.like('/memories/empresa/heuristicas/%'),
                AgentMemory.path.like('/memories/empresa/protocolos/%'),
            ),
            AgentMemory.importance_score >= MANDATORY_IMPORTANCE_THRESHOLD,
            # A4: injeta só legado (NULL) OU ativa. Exclui shadow/candidata/despromovida.
            sql_or(
                AgentMemory.directive_status.is_(None),
                AgentMemory.directive_status == 'ativa',
            ),
        ).order_by(
            AgentMemory.effective_count.desc()
        ).limit(MANDATORY_MAX_COUNT * 3).all()

        # Filtrar por nivel 5 no conteudo (mesmo pattern usado em Tier 1.6)
        const_items: list[str] = []
        org_items: list[str] = []

        # Diretivas constitucionais pinadas: sempre primeiro, independem de
        # effective_count/cap das organicas (promovidas por decisao do usuario).
        for _cd in _CONSTITUTIONAL_DIRECTIVES:
            const_items.append('\n'.join([
                f'  <directive id="{_cd["id"]}">',
                f'    <titulo>{xml_escape(_cd["titulo"])}</titulo>',
                f'    <when>{xml_escape(_cd["when"])}</when>',
                f'    <do>{xml_escape(_cd["do"])}</do>',
                '  </directive>',
            ]))

        # As organicas (top effective_count) preenchem ate MANDATORY_MAX_COUNT —
        # a(s) constitucional(is) sao EXTRA, nao consomem slot das organicas.
        organicas = 0
        for mem in candidates:
            if organicas >= MANDATORY_MAX_COUNT:
                break

            # Formato canonico (2026-06-08): preferir meta estruturado (queryavel,
            # sem regex fragil). Fallback para parse do content nos formatos legados.
            # getattr: robusto a objetos sem coluna meta (mocks de teste / legado).
            meta = getattr(mem, 'meta', None)
            meta = meta if isinstance(meta, dict) else None
            if meta and (meta.get('do') or '').strip() and meta.get('nivel') is not None:
                if meta['nivel'] < 5:
                    continue
                titulo = (meta.get('titulo') or '').strip()
                when_text = (meta.get('when') or '').strip()
                presc = (meta.get('do') or '').strip()
            else:
                content_lower = (mem.content or '').lower()
                # Detecta nivel 5-9 — formato unificado via _is_nivel_5() para
                # garantir consistencia com Tier 1.6 (memory_injection.py:685)
                if not _is_nivel_5(content_lower):
                    continue

                content = mem.content or ''

                # Extrair titulo, when, prescricao — suporta 2 formatos
                titulo_match = _re.search(r'<titulo>(.*?)</titulo>', content, _re.DOTALL)
                presc_match = _re.search(r'<prescricao>(.*?)</prescricao>', content, _re.DOTALL)
                when_match = _re.search(r'<when>(.*?)</when>', content, _re.DOTALL)

                titulo = titulo_match.group(1).strip() if titulo_match else ''
                presc = presc_match.group(1).strip() if presc_match else ''
                when_text = when_match.group(1).strip() if when_match else ''

                # Fallback: formato compacto WHEN:/DO: em texto
                if not presc:
                    lines = content.strip().split('\n')
                    if not titulo and lines:
                        # Primeira linha significativa como titulo
                        for line in lines:
                            stripped = line.strip()
                            if stripped and not stripped.startswith(('```', '[', '<')):
                                titulo = stripped
                                break
                    for line in lines:
                        stripped = line.strip()
                        if stripped.startswith('WHEN:') and not when_text:
                            when_text = stripped[5:].strip()
                        elif stripped.startswith('DO:') and not presc:
                            presc = stripped[3:].strip()

                # Precisa de prescricao para ser uma diretiva acionavel
                if not presc:
                    continue

            # Truncar para caber dentro do budget
            if len(titulo) > 100:
                titulo = titulo[:97] + '...'
            if len(when_text) > 250:
                when_text = when_text[:247] + '...'
            if len(presc) > 350:
                presc = presc[:347] + '...'

            # G4: campos extraidos de memorias podem vir com tags/entities
            # no conteudo — escapar antes de interpolar no wrapper XML.
            d_parts = [f'  <directive id="{mem.id}">']
            if titulo:
                d_parts.append(f'    <titulo>{xml_escape(titulo)}</titulo>')
            if when_text:
                d_parts.append(f'    <when>{xml_escape(when_text)}</when>')
            d_parts.append(f'    <do>{xml_escape(presc)}</do>')
            d_parts.append('  </directive>')
            org_items.append('\n'.join(d_parts))
            organicas += 1

        return const_items, org_items

    except Exception as e:
        logger.debug(f"[OPERATIONAL_DIRECTIVES] Build failed: {e}")
        return [], []


def _build_routing_context(user_id: int) -> Optional[str]:
    """
    Constrói contexto de despacho para routing do agente principal.
    Zero-LLM: SQL queries apenas. Max ~500 chars.

    F4.4 PAD-CTX: operational_directives NAO vem mais embutido aqui — o caller
    (_load_user_memories_for_context) monta directives (item 7) e routing
    (item 9) como blocos separados na ordem-alvo, com o briefing entre eles.

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

        parts = ['<routing_context priority="advisory">']

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
                # Formato canonico (2026-06-08): preferir meta estruturado;
                # fallback para parse do content nos formatos legados.
                a_meta = getattr(arm, 'meta', None)
                a_meta = a_meta if isinstance(a_meta, dict) else None
                if a_meta and (a_meta.get('titulo') or a_meta.get('do')):
                    title = (a_meta.get('titulo') or '').strip() or arm.path.split('/')[-1].replace('.xml', '')
                    prescricao = (a_meta.get('do') or '').strip()
                else:
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
                # G4: title/prescricao extraidos de AgentMemory.content —
                # escapar antes de interpolar no XML de active_traps.
                if prescricao:
                    if len(prescricao) > 200:
                        prescricao = prescricao[:197] + '...'
                    parts.append(
                        f'    - {xml_escape(title)}'
                        f'\n      DO: {xml_escape(prescricao)}'
                    )
                else:
                    parts.append(f'    - {xml_escape(title)}')
            parts.append('  </active_traps>')

        parts.append('</routing_context>')

        # routing_context so entra se tem conteudo util (> tags vazias)
        if len(parts) <= 2:
            return None

        result = '\n'.join(parts)
        logger.debug(
            f"[ROUTING_CONTEXT] user_id={user_id} domain={domain} "
            f"chars={len(result)}"
        )
        return result

    except Exception as e:
        logger.debug(f"[ROUTING_CONTEXT] Build failed: {e}")
        return None


def _composite_score(decay: float, importance: float,
                     similarity: Optional[float] = None,
                     correction_count: int = 0) -> float:
    """Composite de ranking de memoria (puro/testavel).

    Fase 3.4B (flag USE_RECURRENCE_SCORE, default OFF): soma um eixo de RECORRENCIA
    (correction_count normalizado, cap 10) ao score — regras reincidentes do usuario
    sobem no ranking. OFF por padrao porque hoje correction_count e ~0 em quase todas as
    memorias (so o loop corretivo o popula); ligar antes disso apenas redistribuiria os
    pesos de decay/importance (regressao silenciosa). Com a flag OFF, retorna a formula
    historica EXATA (0.3 decay + 0.3 imp + 0.4 sim; fallback 0.3 decay + 0.7 imp).
    """
    try:
        from ..config.feature_flags import USE_RECURRENCE_SCORE
    except Exception:
        USE_RECURRENCE_SCORE = False

    if similarity is None:
        # Fallback sem similaridade (tier2b)
        if USE_RECURRENCE_SCORE:
            recurrence = min(int(correction_count or 0), 10) / 10.0
            return 0.25 * decay + 0.60 * importance + 0.15 * recurrence
        return 0.3 * decay + 0.7 * importance

    if USE_RECURRENCE_SCORE:
        recurrence = min(int(correction_count or 0), 10) / 10.0
        return 0.25 * decay + 0.25 * importance + 0.35 * similarity + 0.15 * recurrence
    return 0.3 * decay + 0.3 * importance + 0.4 * similarity


def _load_user_memories_for_context(
    user_id: int, prompt: str = None, model_name: str = None
) -> tuple[Optional[str], Optional[str], list[int]]:
    """
    Carrega memórias do usuário e formata como contexto para injeção.

    Memory System v2 — Arquitetura em 4 tiers:
    - Tier 1 (SEMPRE): user.xml e preferences.xml — garante identidade/preferências
    - Tier 1.5 (SEMPRE): Perfil empresa do usuário — contexto de routing
    - Tier 2 (semântica): memórias relevantes ao prompt, excluindo Tier 1
    - Tier 2b (KG): complementar via Knowledge Graph
    - Fallback: memórias mais recentes se semântica não retornar nada
    + blocos de contexto operacional: directives, briefing, routing, session window

    F4 PAD-CTX (2026-06-09) — ordem-alvo + orcamento por bloco:
    - Retorno em DUAS partes: MAIN (itens 3-9 da tabela: user_rules ->
      user_memories -> operational_directives -> briefing -> routing_context)
      e TAIL (itens 12-13: recent_sessions -> pendencias_acumuladas, que o
      hook posiciona por ULTIMO, apos debug/sql_admin).
    - Tier 2: cap TIER2_MAX_MEMORIES x ~TIER2_MEMORY_CHAR_CAP (destilado
      meta WHEN/DO + ponteiro view_memories — _distill_tier2_content).
    - Overflow: _fit_hook_budget corta tier2 -> directives organicas ->
      routing (NUNCA user_rules/pendencias/sessions/tier1).

    Budget adaptativo (T2-2) permanece como teto ADICIONAL do Tier 2:
    - Opus: sem limite por modelo (o cap de bloco F4 e quem limita)
    - Sonnet: 6000 chars | Haiku: 3000 chars (ajustado pelo tamanho do prompt)

    Args:
        user_id: ID do usuário no banco
        prompt: Prompt do usuário (para seleção semântica)
        model_name: Nome do modelo (para budget adaptativo, ex: "claude-opus-4-8")

    Returns:
        Tupla (main_context ou None, tail_context ou None, IDs injetados)
    """
    if not user_id:
        return None, None, []

    # ─── Fase 5: Cache check por sessao ────────────────────────────
    # Se estamos em uma sessao conhecida, tenta servir do cache antes de
    # fazer queries SQL + embeddings. TTL 30min ou invalidacao em mutacao.
    try:
        from ..config.permissions import get_current_session_id
        _cached_session_id = get_current_session_id()
        if _cached_session_id:
            _cache_hit = _cache_get(_cached_session_id, user_id)
            if _cache_hit is not None:
                main_c, tail_c, mem_ids = _cache_hit
                logger.info(
                    f"[memory_injection] CACHE HIT session={_cached_session_id[:12]}... "
                    f"user={user_id} chars={len(main_c or '') + len(tail_c or '')} "
                    f"ids={len(mem_ids)}"
                )
                return main_c, tail_c, mem_ids
    except Exception as _cache_err:
        logger.debug(f"[memory_injection] cache check falhou (ignorado): {_cache_err}")
        _cached_session_id = None

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

            # ── L1: User Rules (SEMPRE, priority=mandatory) — NOVO CANAL ──
            # Fase 3.4A: regras duras vao para o TOPO ABSOLUTO do contexto (antes de
            # <user_memories>). A Fase 0 (AgingBench) mostrou que a regra no topo rende
            # muito mais (P3=89% vs P1=0%). Com USE_USER_RULES_TOP=False (legado),
            # as regras vao para a CAUDA do main (apos routing_context).
            rules_block_top = None
            rules_block_tail_legacy = None
            # F1.1 PAD-CTX (bug N-1): IDs das regras L1 efetivamente injetadas —
            # unidos ao protected_ids adiante para o Tier 2 NAO re-injetar a mesma
            # memoria (dupla injecao user_rules + user_memories no mesmo payload).
            l1_rule_ids: set = set()
            try:
                from ..config.feature_flags import USE_USER_RULES_CHANNEL, USE_USER_RULES_TOP
                if USE_USER_RULES_CHANNEL:
                    from .memory_injection_rules import _build_user_rules, _get_user_rule_ids
                    rules_block = _build_user_rules(user_id)
                    if rules_block:
                        l1_rule_ids = _get_user_rule_ids(user_id)
                        if USE_USER_RULES_TOP:
                            rules_block_top = rules_block  # TOPO (maior atencao) na montagem final
                        else:
                            rules_block_tail_legacy = rules_block  # legado: cauda do main
                        logger.info(
                            f"[MEMORY_INJECT] L1 user_rules injected "
                            f"({'top' if USE_USER_RULES_TOP else 'tail'}): {len(rules_block)} chars"
                        )
            except Exception as l1_err:
                logger.debug(f"[MEMORY_INJECT] L1 rules falhou (ignorado): {l1_err}")

            # ── Itens 12-13 (TAIL): rolling window + pendencias (F4.4a) ──
            session_window, pendencias_block = _build_session_window(user_id)

            # ── Item 8: Briefing inter-sessão (Memory v2 — 3A) ──
            briefing = None
            try:
                from ..config.feature_flags import USE_INTERSESSION_BRIEFING
                if USE_INTERSESSION_BRIEFING:
                    from ..services.intersession_briefing import build_intersession_briefing
                    briefing = build_intersession_briefing(user_id)
            except Exception as brief_err:
                logger.debug(f"[MEMORY_INJECT] Briefing inter-sessão falhou (ignorado): {brief_err}")

            # ── Item 7: Operational directives (const + organicas — F4.3) ──
            directives_full = None
            directives_const = None
            try:
                const_items, org_items = _build_operational_directives_parts(user_id)
                directives_full = _render_operational_directives(const_items + org_items)
                directives_const = _render_operational_directives(const_items)
                if directives_full:
                    logger.info(
                        f"[OPERATIONAL_DIRECTIVES] user_id={user_id} "
                        f"directives={len(const_items) + len(org_items)} "
                        f"chars={len(directives_full)}"
                    )
            except Exception as dir_err:
                logger.debug(f"[MEMORY_INJECT] Directives falhou (ignorado): {dir_err}")

            # ── Item 9: Routing context (domínio + armadilhas) ──
            routing_ctx = None
            try:
                routing_ctx = _build_routing_context(user_id)
            except Exception as route_err:
                logger.debug(f"[MEMORY_INJECT] Routing context falhou (ignorado): {route_err}")

            # ── Tier 1: SEMPRE injetar memórias protegidas ──
            # user_expertise.xml (2026-05-11): consolida expertise do usuario
            # (substitui /learned/expertise_*.xml que ficavam orfaos). Mesma
            # mecanica de preferences.xml — singleton, sempre injetado.
            PROTECTED_PATHS = [
                "/memories/user.xml",
                "/memories/preferences.xml",
                "/memories/user_expertise.xml",
            ]
            protected_memories = AgentMemory.query.filter(
                AgentMemory.user_id == user_id,
                AgentMemory.path.in_(PROTECTED_PATHS),
                AgentMemory.is_directory == False,  # noqa: E712
            ).all()

            protected_ids = {m.id for m in protected_memories}
            # F1.1 PAD-CTX (bug N-1): regras ja injetadas no canal L1 <user_rules>
            # nao podem reentrar via Tier 2 semantico/fallback.
            protected_ids |= l1_rule_ids

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
            #
            # NOTA: Quando USE_OPERATIONAL_DIRECTIVES=True, estas heuristicas ja sao
            # injetadas via <operational_directives> (Tier 0, como diretiva obrigatoria).
            # Pulamos Tier 1.6 para evitar duplicacao no contexto — mesma regra em dois
            # frames (obrigatoria + contextual) confunde o modelo e dobra consumo de budget.
            tier16_memories = []
            try:
                from ..config.feature_flags import USE_OPERATIONAL_DIRECTIVES
                if USE_OPERATIONAL_DIRECTIVES:
                    logger.debug(
                        "[MEMORY_INJECT] Tier 1.6 SKIP: USE_OPERATIONAL_DIRECTIVES=True "
                        "(heuristicas nivel 5 ja vem como <operational_directives>)"
                    )
                else:
                    tier16_query = AgentMemory.query.filter(
                        AgentMemory.user_id == 0,  # empresa
                        AgentMemory.is_directory == False,  # noqa: E712
                        AgentMemory.is_cold == False,  # noqa: E712
                        AgentMemory.path.like('/memories/empresa/heuristicas/%'),
                    ).all()
                    # Filtrar: apenas memorias com nivel >= 5 no conteudo
                    # Usa helper unificado _is_nivel_5() — mesma deteccao do
                    # _build_operational_directives (memory_injection.py:362)
                    for mem in tier16_query:
                        content_lower = (mem.content or '').lower()
                        if _is_nivel_5(content_lower) and mem.id not in protected_ids:
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
            _pass1_similarity = {}  # F5.5: mem.id → similarity CRUA (gate few-shot)
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
                            from sqlalchemy import or_ as sql_or
                            mem_objects = AgentMemory.query.filter(
                                AgentMemory.id.in_(memory_ids),
                                AgentMemory.is_directory == False,  # noqa: E712
                                AgentMemory.is_cold == False,  # noqa: E712 — v2: excluir cold
                                # Nao injetar diretiva nao-promovida (shadow/candidata/
                                # despromovida) — so NULL/ativa (mesmo criterio do
                                # _build_operational_directives, linha 504-505). Filtro
                                # na FONTE preserva o slot do top-10 para memoria legitima.
                                sql_or(
                                    AgentMemory.directive_status.is_(None),
                                    AgentMemory.directive_status == 'ativa',
                                ),
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

                                # v2: Decay por categoria
                                last_access = mem.last_accessed_at or mem.updated_at or mem.created_at
                                if last_access:
                                    hours_since = max(0, (now - last_access).total_seconds() / 3600)
                                    category = getattr(mem, 'category', 'operational') or 'operational'
                                    decay = _calculate_category_decay(category, hours_since)
                                else:
                                    decay = 0.5

                                composite = _composite_score(decay, importance, similarity, mem.correction_count)
                                scored.append((mem, composite, similarity))

                            # Ordenar por composite score (desc), pegar top 10
                            scored.sort(key=lambda x: x[1], reverse=True)
                            scored = scored[:10]

                            # Preservar composite scores originais (com similarity) para PASS 2
                            _pass1_scores = {s[0].id: s[1] for s in scored}
                            # F5.5: similarity crua para o gate de few-shot episodico
                            _pass1_similarity = {s[0].id: s[2] for s in scored}
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
                            last_access = mem.last_accessed_at or mem.updated_at or mem.created_at
                            if last_access:
                                hours_since = max(0, (now_graph - last_access).total_seconds() / 3600)
                                category = getattr(mem, 'category', 'operational') or 'operational'
                                decay = _calculate_category_decay(category, hours_since)
                            else:
                                decay = 0.5
                            composite = _composite_score(decay, importance, similarity, mem.correction_count)
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

            # ── Defesa em profundidade: nunca injetar diretiva nao-promovida ──
            # Os tiers de descoberta KG (1072) e fallback (1105) materializam por id
            # SEM filtrar directive_status. 'shadow'/'candidata'/'despromovida' nao podem
            # entrar no contexto por NENHUMA via — so legado (NULL) ou 'ativa' (mesmo
            # criterio do _build_operational_directives:504-505). Guard unico = robusto
            # contra tiers futuros. protected_memories sao paths fixos de identidade
            # (Tier 0/1), fora do escopo deste filtro.
            if additional_memories:
                additional_memories = [
                    m for m in additional_memories
                    if getattr(m, 'directive_status', None) in (None, 'ativa')
                ]

            # ── Montar resultado: blocos operacionais + protegidas + relevantes ──
            all_memories = protected_memories + additional_memories

            _has_operational_blocks = bool(
                session_window or pendencias_block or briefing
                or directives_full or routing_ctx
                or rules_block_top or rules_block_tail_legacy
            )
            if not all_memories and not _has_operational_blocks:
                return None, None, []

            # ── QW-4 + T2-2 + v2: Budget adaptativo com two-pass selection ──
            # Budget base por modelo (teto ADICIONAL ao cap de bloco F4)
            # Opus: sem limite por modelo — o cap TIER2_MAX_MEMORIES x 300c limita
            # Sonnet/Haiku: budget para manter conciso
            _model = (model_name or "").lower()
            if "opus" in _model:
                base_budget = None  # sem limite por modelo — cap de bloco F4 aplica
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
                budget = None  # Opus: sem budget por modelo

            # ── PASS 1: Calcular tamanhos de todos os candidatos ──
            header = (
                "<user_memories>\n"
                "<!-- Memórias persistentes do usuário — use para personalizar respostas -->\n"
            )
            footer = "</user_memories>"
            overhead = len(header) + len(footer)

            # Tier 1: protegidas sempre incluídas
            tier1_texts = []
            tier1_chars = 0
            for mem in protected_memories:
                content = (mem.content or "").strip()
                if not content:
                    continue
                # P1-3 Camada 2: user.xml > threshold em budget finito → ponteiro
                # Evidencia: 5/12 users excedem 67% do budget Sonnet so com Tier 1.
                # Gabriella e Marcus (10K+ bytes) ficam com Tier 2 zerado sistematicamente.
                # Camada 1 (guidance no gerador) resolvera em 1-4 semanas via re-geracao.
                from ..config.feature_flags import (
                    USE_USER_XML_POINTER,
                    USER_XML_POINTER_THRESHOLD,
                )
                if (
                    USE_USER_XML_POINTER
                    and mem.path == "/memories/user.xml"
                    and budget is not None
                    and len(content) > USER_XML_POINTER_THRESHOLD
                ):
                    original_len = len(content)
                    content = _build_user_profile_pointer(content)
                    logger.debug(
                        f"[MEMORY_INJECT] user.xml pointer aplicado: "
                        f"user_id={user_id} orig={original_len} new={len(content)}"
                    )
                # G4: neutralizar tags de controle injetadas em memoria
                # (preserva XML legitimo tipo <resumo>, <contextualizacao>)
                content = sanitize_memory_content(
                    content, source=f"mem_id={mem.id} path={mem.path}"
                )
                mem_text = f'{_memory_open_tag(mem)}\n{content}\n</memory>\n'
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
                # G4: sanitizar tags de controle (perfil empresa user_id=0
                # e shared entre sessoes — vetor critico de RAG injection)
                content = sanitize_memory_content(
                    content, source=f"mem_id={mem.id} tier=routing path={mem.path}"
                )
                mem_text = (
                    f'{_memory_open_tag(mem, "routing")}\n'
                    f'{content}\n</memory>\n'
                )
                tier15_texts.append((mem, mem_text))
                tier15_chars += len(mem_text)

            # Tier 1.6: heuristicas empresa nivel 5 (sempre incluídas)
            tier16_texts = []
            tier16_chars = 0
            for mem in tier16_memories:
                content = (mem.content or "").strip()
                if not content:
                    continue
                # G4: mesma logica tier1.5 — heuristicas empresa sao shared
                content = sanitize_memory_content(
                    content, source=f"mem_id={mem.id} tier=heuristica path={mem.path}"
                )
                mem_text = (
                    f'{_memory_open_tag(mem, "heuristica")}\n'
                    f'{content}\n</memory>\n'
                )
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
                # G4: sanitizar antes de envolver em wrapper <memory>
                content = sanitize_memory_content(
                    content, source=f"mem_id={mem.id} tier=2 path={mem.path}"
                )
                # F4.3 (destilado 300c) OU F5.5 (few-shot episodico completo
                # quando match excepcional) — decisao em _render_tier2_candidate
                mem_text = _render_tier2_candidate(
                    mem, content, similarity=_pass1_similarity.get(mem.id, 0.0)
                )
                # Usar composite score original do PASS 1 (inclui similarity)
                # Fallback: decay + importance (sem similarity) para memórias de fallback
                if mem.id in _pass1_scores:
                    composite = _pass1_scores[mem.id]
                else:
                    now_sel = agora_utc_naive()
                    importance = mem.importance_score if mem.importance_score is not None else 0.5
                    last_access = mem.last_accessed_at or mem.updated_at or mem.created_at
                    if last_access:
                        hours_since = max(0, (now_sel - last_access).total_seconds() / 3600)
                        category = getattr(mem, 'category', 'operational') or 'operational'
                        decay = _calculate_category_decay(category, hours_since)
                    else:
                        decay = 0.5
                    composite = _composite_score(decay, importance, correction_count=mem.correction_count)
                tier2_candidates.append((mem, mem_text, len(mem_text), composite))

            # ── PASS 2: Selecionar por composite score dentro do budget ──
            # F4.3 PAD-CTX: cap de QUANTIDADE do bloco Tier 2 (TIER2_MAX_MEMORIES)
            # alem do budget por modelo — tabela do PAD-CTX: 4 x ~300c.
            tier2_candidates.sort(key=lambda x: x[3], reverse=True)
            selected_tier2 = []
            tier2_chars = 0
            tier2b_chars = 0
            for mem, mem_text, mem_len, _ in tier2_candidates:
                if len(selected_tier2) >= TIER2_MAX_MEMORIES:
                    break
                if budget_remaining is not None and tier2_chars + tier2b_chars + mem_len > budget_remaining:
                    continue  # v2: SKIP em vez de BREAK — permite menor caber depois
                selected_tier2.append((mem, mem_text))
                # Distinguir tier2 vs tier2b para logging
                if mem in additional_memories[:semantic_count]:
                    tier2_chars += mem_len
                else:
                    tier2b_chars += mem_len

            # ── F4.3: politica de overflow (ordem de corte da tabela PAD-CTX) ──
            # Blocos fixos (incortaveis): user_rules, tier1/1.5/1.6, briefing,
            # recent_sessions, pendencias. Cortaveis, na ordem: tier2 ->
            # directives organicas (constitucional fica) -> routing_context.
            fixed_chars = (
                len(rules_block_top or '') + len(rules_block_tail_legacy or '')
                + overhead + tier1_chars + tier15_chars + tier16_chars
                + len(briefing or '') + len(session_window or '')
                + len(pendencias_block or '')
            )
            fitted, overflow_cortes = _fit_hook_budget({
                'fixed_chars': fixed_chars,
                'tier2': ''.join(t for _, t in selected_tier2),
                'directives_full': directives_full or '',
                'directives_const': directives_const or '',
                'routing': routing_ctx or '',
            })
            if 'tier2' in overflow_cortes:
                selected_tier2 = []
                tier2_chars = 0
                tier2b_chars = 0
            directives_block = fitted['directives'] or None
            routing_block = fitted['routing'] or None
            if overflow_cortes:
                logger.info(
                    f"[MEMORY_INJECT] F4 overflow policy: cortes={overflow_cortes} "
                    f"user_id={user_id} target={HOOK_CONTEXT_TARGET_CHARS}"
                )

            # ── Montar resultado final (ordem-alvo PAD-CTX, F4.4) ──
            # MAIN: user_rules(3) -> user_memories(4-6) -> directives(7) ->
            # briefing(8) -> routing(9). TAIL: recent_sessions(12) -> pendencias(13).
            main_parts = []
            # Fase 3.4A: regras duras (<user_rules>) no TOPO ABSOLUTO — antes do <user_memories>.
            if rules_block_top:
                main_parts.append(rules_block_top + "\n")
            main_parts.append(header)
            injected_mems = []

            for mem, mem_text in tier1_texts:
                main_parts.append(mem_text)
                injected_mems.append(mem)

            for mem, mem_text in tier15_texts:
                main_parts.append(mem_text)
                injected_mems.append(mem)

            for mem, mem_text in tier16_texts:
                main_parts.append(mem_text)
                injected_mems.append(mem)

            for mem, mem_text in selected_tier2:
                main_parts.append(mem_text)
                injected_mems.append(mem)

            main_parts.append(footer + "\n")
            if directives_block:
                main_parts.append(directives_block + "\n")
            if briefing:
                main_parts.append(briefing + "\n")
            if routing_block:
                main_parts.append(routing_block + "\n")
            if rules_block_tail_legacy:
                # legado USE_USER_RULES_TOP=False: regras na cauda do main
                main_parts.append(rules_block_tail_legacy + "\n")
            main_result = "".join(main_parts)

            tail_parts = []
            if session_window:
                tail_parts.append(session_window + "\n")
            if pendencias_block:
                tail_parts.append(pendencias_block + "\n")
            tail_result = "".join(tail_parts) if tail_parts else None

            total_chars = len(main_result) + len(tail_result or '')
            injected_count = len(injected_mems)

            if injected_count == 0 and not _has_operational_blocks:
                return None, None, []  # Nenhuma memória coube no budget

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
                f"main_chars={len(main_result)} | "
                f"tail_chars={len(tail_result or '')} | "
                f"tier1_chars={tier1_chars} | "
                f"tier2_chars={tier2_chars} | "
                f"tier2b_chars={tier2b_chars} | "
                f"overflow_cortes={overflow_cortes or '[]'} | "
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

            return main_result, tail_result, injected_ids

        if ctx is None:
            result = _load()
        else:
            with ctx:
                result = _load()

        # ─── Fase 5: Cache write-back (MISS) ───────────────────────
        # Persistir resultado para proximas consultas da mesma sessao.
        # Invalidado automaticamente em save/update/delete_memory (user marcado).
        try:
            if _cached_session_id and result is not None:
                main_c, tail_c, mem_ids = result
                _cache_put(_cached_session_id, user_id, main_c, tail_c, mem_ids or [])
                logger.info(
                    f"[memory_injection] CACHE MISS -> PUT session={_cached_session_id[:12]}... "
                    f"user={user_id} chars={len(main_c or '') + len(tail_c or '')} "
                    f"ids={len(mem_ids or [])}"
                )
        except Exception as _put_err:
            logger.debug(f"[memory_injection] cache put falhou: {_put_err}")

        return result

    except Exception as e:
        logger.warning(f"[MEMORY_INJECT] Erro ao carregar memórias (ignorado): {e}")
        return None, None, []


# ======================================================================
# Task 10 (Fase 1 Skill Effectiveness): Cache de lembretes de skill
# ======================================================================
# Lembretes ativos do usuario: AgentMemory com path LIKE '/memories/lembretes_skill/%'
# e directive_status NULL ou 'ativa' (shadow NAO injeta — mesmo criterio de Tier 0c).
# Cache por session_id, TTL 30min, cap 500 entradas (anti-leak).
# Invalidado por invalidate_skill_reminders_cache() que e chamado por
# _invalidate_caches() em skill_effectiveness_service.apply_decision.

_SKILL_REMINDERS_CACHE: dict = {}           # {session_id: ({skill: conteudo}, timestamp)}
_SKILL_REMINDERS_TTL = 1800                 # 30 minutos
_SKILL_REMINDERS_LOCK = threading.Lock()


def invalidate_skill_reminders_cache() -> None:
    """Limpa cache de lembretes de skill (chamado apos criar/atualizar lembrete)."""
    with _SKILL_REMINDERS_LOCK:
        _SKILL_REMINDERS_CACHE.clear()
    logger.debug("[memory_injection] skill reminders cache cleared")


def get_skill_reminders_for_session(user_id: int, session_id: str) -> dict:
    """{skill_name: conteudo} dos lembretes ATIVOS (directive_status NULL/'ativa') do usuario.

    Cache por session_id (TTL 30min). Flag-gated por AGENT_SKILL_EVAL.
    Shadow NAO injeta (mesmo criterio do Tier 0c operational_directives).
    """
    import time as _t
    try:
        from ..config.feature_flags import AGENT_SKILL_EVAL
        if not AGENT_SKILL_EVAL:
            return {}
    except Exception:
        return {}

    now = _t.time()
    with _SKILL_REMINDERS_LOCK:
        hit = _SKILL_REMINDERS_CACHE.get(session_id)
        if hit and (now - hit[1]) < _SKILL_REMINDERS_TTL:
            return hit[0]

    out: dict = {}
    try:
        from contextlib import nullcontext
        try:
            from flask import current_app as _app_probe
            _ = _app_probe.name
            _ctx = nullcontext()
        except RuntimeError:
            from app import create_app as _ca
            _ctx = _ca().app_context()

        with _ctx:
            from app import db
            from ..models import AgentMemory
            rows = AgentMemory.query.filter(
                AgentMemory.user_id == user_id,
                AgentMemory.path.like('/memories/lembretes_skill/%'),
                db.or_(
                    AgentMemory.directive_status.is_(None),
                    AgentMemory.directive_status == 'ativa',
                ),
            ).all()
            for m in rows:
                skill = m.path.rsplit('/', 1)[-1].replace('.xml', '')
                if skill:
                    out[skill] = m.content or ""
    except Exception as e:
        logger.debug(f"[SKILL_EVAL] skill reminders load falhou (ignorado): {e}")

    with _SKILL_REMINDERS_LOCK:
        # Cap: evitar leak se muitas sessoes nao sao limpas
        if len(_SKILL_REMINDERS_CACHE) > 500:
            _SKILL_REMINDERS_CACHE.clear()
        _SKILL_REMINDERS_CACHE[session_id] = (out, now)

    return out
