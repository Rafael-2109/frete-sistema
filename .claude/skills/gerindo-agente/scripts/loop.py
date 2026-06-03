#!/usr/bin/env python3
"""
loop.py — flywheel de diretrizes operacionais do Agente Web (READ, Onda 3 / fase 3a).

Expoe a camada A4 (Distill -> Deploy) do blueprint para INSPECAO. Custo $0 de tokens
(SQL puro). Subcomandos:

  directives    Diretrizes-empresa (user_id=0): funil shadow/ativa/legado/candidata
                — espelha o filtro de _build_operational_directives (memory_injection.py)
                para mostrar o que ESTA sendo injetado vs o que aguarda revisao.
  corrections   Correcoes (/memories/corrections/) candidatas a regra dura (mandatory)
                — fonte de promover_correcoes_recorrentes (directive_promotion_service.py).
  loop-health   Saude do flywheel: PlanState (gargalo B1) + funil de diretrizes +
                prontidao de promocao + estado das flags relevantes.

ESCRITA (approve shadow->ativa, reject, promote-batch) NAO mora aqui: fase 3b,
dev-only atras de --confirm (approve muta o prompt PROD em tempo real). Ver
docs/superpowers/plans/2026-06-03-evolucao-gerindo-agente.md (Onda 3).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

import re as _re

from common import (
    format_table, run_handler, success_output, truncate,
)


SUBCOMMANDS = {
    'directives': {
        'help': 'Diretrizes-empresa (funil shadow/ativa/legado) — custo $0',
        'args': [
            {'name': '--status', 'type': str, 'default': 'all',
             'help': "Filtra por status: shadow|ativa|legado|candidata|despromovida|all (default: all)"},
        ],
    },
    'corrections': {
        'help': 'Correcoes candidatas a regra dura (mandatory) — custo $0',
        'args': [
            {'name': '--days', 'type': int, 'default': 30, 'help': 'Janela por created_at em dias (default: 30)'},
            {'name': '--all', 'action': 'store_true', 'dest': 'all_users', 'help': 'Sistema inteiro (todos os usuarios)'},
        ],
    },
    'loop-health': {
        'help': 'Saude do flywheel: PlanState (gargalo B1) + funil + promocao — custo $0',
        'args': [
            {'name': '--days', 'type': int, 'default': 30, 'help': 'Janela por created_at em dias (default: 30)'},
            {'name': '--all', 'action': 'store_true', 'dest': 'all_users', 'help': 'Sistema inteiro (todos os usuarios)'},
        ],
    },
    # ── WRITE (fase 3b, DEV-ONLY) — dry-run e o DEFAULT; so escreve com --confirm ──
    'approve': {
        'help': '[WRITE] Promove diretriz shadow -> ativa (MUTA O PROMPT VIVO). dry-run sem --confirm',
        'args': [
            {'name': '--id', 'type': int, 'required': True, 'help': 'ID da AgentMemory (diretriz shadow)'},
            {'name': '--confirm', 'action': 'store_true', 'help': 'Efetiva o flip shadow->ativa (sem isso = preview)'},
        ],
    },
    'reject': {
        'help': '[WRITE] Rejeita diretriz shadow/candidata -> despromovida. dry-run sem --confirm',
        'args': [
            {'name': '--id', 'type': int, 'required': True, 'help': 'ID da AgentMemory (diretriz)'},
            {'name': '--confirm', 'action': 'store_true', 'help': 'Efetiva o rebaixamento (sem isso = preview)'},
        ],
    },
    'promote-batch': {
        'help': '[WRITE] Roda o batch A4 (cria shadows + promove correcoes a mandatory). dry-run sem --confirm',
        'args': [
            {'name': '--lookback-hours', 'type': int, 'default': 24, 'help': 'Janela do batch em horas (default: 24)'},
            {'name': '--confirm', 'action': 'store_true', 'help': 'Executa o batch (sem isso = preview do estado)'},
        ],
    },
}

# Status possiveis de uma diretriz-empresa. NULL no banco = diretriz legada (pre-A4),
# que continua sendo injetada (filtro IN (NULL,'ativa') em _build_operational_directives).
_DIRECTIVE_STATUSES = ('shadow', 'ativa', 'legado', 'candidata', 'despromovida')

_DIRECTIVE_PATHS = ('/memories/empresa/heuristicas/%', '/memories/empresa/protocolos/%')


def _scope_uid(args):
    """Resolve escopo: None (sistema inteiro) se --all, senao o --user-id."""
    return None if getattr(args, 'all_users', False) else args.user_id


def _scope_label(args):
    return 'TODOS os usuarios' if _scope_uid(args) is None else f'user_id={args.user_id}'


def _threshold():
    """AGENT_CORRECTION_PROMOTION_THRESHOLD (default 2), tolerante a valor invalido.

    Nunca levanta — o contrato READ-first e degradacao graciosa (review Onda 3).
    """
    try:
        from app.agente.config.feature_flags import AGENT_CORRECTION_PROMOTION_THRESHOLD as t
        return int(t)
    except Exception:
        try:
            return int(os.environ.get('AGENT_CORRECTION_PROMOTION_THRESHOLD', '2'))
        except (ValueError, TypeError):
            return 2


def _content_nivel_5(content):
    """Espelha memory_injection._is_nivel_5:139 (regex `nivel\\s*[=:"\\s>]+[5-9]`).

    Replicado (nao importado) para nao puxar o modulo pesado memory_injection.
    Se mudar la, mudar aqui (o predicado decide se a diretriz e injetada).
    """
    return bool(_re.search(r'nivel\s*[=:"\s>]+[5-9]', (content or '').lower()))


def _has_prescricao(content):
    """True se ha <prescricao> OU linha `DO:` — espelha o filtro `if not presc: continue`
    de _build_operational_directives (memory_injection.py:494-522). Diferente de _extrai_do
    (display, que tem fallback de conteudo livre): aqui SEM fallback (precisa ser acionavel)."""
    content = content or ''
    if _re.search(r'<prescricao>(.*?)</prescricao>', content, _re.DOTALL):
        return True
    return any(line.strip().startswith('DO:') for line in content.splitlines())


def _injection_params():
    """(USE_OPERATIONAL_DIRECTIVES, MANDATORY_IMPORTANCE_THRESHOLD) — tolerante a import falho.

    Le as flags REAIS que governam a injecao (memory_injection.py:446-453, :470) em vez de
    hardcodar 0.7 / assumir a flag ON (review fase 3b).
    """
    try:
        from app.agente.config.feature_flags import (
            USE_OPERATIONAL_DIRECTIVES, MANDATORY_IMPORTANCE_THRESHOLD,
        )
        return bool(USE_OPERATIONAL_DIRECTIVES), float(MANDATORY_IMPORTANCE_THRESHOLD)
    except Exception:
        return True, 0.7


def _will_inject(mem):
    """True se a diretriz (apos ativa) REALMENTE entra em <operational_directives>.

    Espelha FIELMENTE _build_operational_directives (memory_injection.py:446-522):
    flag USE_OPERATIONAL_DIRECTIVES ON + is_cold=False + importance>=threshold +
    conteudo nivel-5 + ha <prescricao>/DO: (acionavel). (status ja sera 'ativa'.)
    """
    flag_on, threshold = _injection_params()
    return (
        flag_on
        and not mem.is_cold
        and (mem.importance_score or 0) >= threshold
        and _content_nivel_5(mem.content)
        and _has_prescricao(mem.content)
    )


def _load_directive(mem_id):
    """Carrega uma diretriz-empresa por id, validando que e do escopo certo.

    Retorna (mem, erro_str). erro_str != None => nao operar.
    """
    from app.agente.models import AgentMemory
    mem = AgentMemory.query.get(mem_id)
    if mem is None:
        return None, f"AgentMemory id={mem_id} nao encontrada"
    if mem.user_id != 0:
        return None, f"id={mem_id} nao e diretriz-empresa (user_id={mem.user_id}, esperado 0)"
    path = mem.path or ''
    if not (path.startswith('/memories/empresa/heuristicas/') or path.startswith('/memories/empresa/protocolos/')):
        return None, f"id={mem_id} nao esta em /heuristicas/ ou /protocolos/ (path={path})"
    return mem, None


def _titulo_de(content):
    """Extrai <titulo> (ou a 1a linha significativa) — mesmo padrao do builder."""
    content = content or ''
    m = _re.search(r'<titulo>(.*?)</titulo>', content, _re.DOTALL)
    if m:
        return m.group(1).strip()
    for line in content.strip().splitlines():
        s = line.strip()
        if s and not s.startswith(('```', '[', '<')):
            return s
    return ''


def handle_directives(args):
    """Funil de diretrizes-empresa (user_id=0): o que e injetado vs o que aguarda.

    A injecao no prompt (memory_injection.py:462) usa: user_id=0, path
    /heuristicas/ ou /protocolos/, importance>=0.7, is_cold=False e
    directive_status IN (NULL,'ativa') — alem de um filtro de conteudo nivel-5
    aplicado em Python (nao reproduzido aqui; por isso 'injetaveis' e um teto).
    """
    from app import db
    from app.agente.models import AgentMemory
    from sqlalchemy import func, or_ as sql_or

    status_filter = (getattr(args, 'status', 'all') or 'all').strip().lower()
    warnings = []

    path_clause = sql_or(
        AgentMemory.path.like(_DIRECTIVE_PATHS[0]),
        AgentMemory.path.like(_DIRECTIVE_PATHS[1]),
    )
    base = [
        AgentMemory.user_id == 0,
        AgentMemory.is_directory == False,  # noqa: E712
        path_clause,
    ]

    # Threshold REAL de injecao (flag, nao hardcode 0.7 — review fase 3b).
    _, _imp_threshold = _injection_params()

    # Funil completo (contagem por status — NAO limitado), schema FIXO (zeros sempre).
    por_status = {k: 0 for k in _DIRECTIVE_STATUSES}
    injetaveis = 0
    try:
        grouped = db.session.query(
            func.coalesce(AgentMemory.directive_status, 'legado'),
            func.count(AgentMemory.id),
        ).filter(*base).group_by(
            func.coalesce(AgentMemory.directive_status, 'legado')
        ).all()
        for st, n in grouped:
            por_status[st] = int(n)
        injetaveis = AgentMemory.query.filter(
            *base,
            AgentMemory.is_cold == False,  # noqa: E712
            AgentMemory.importance_score >= _imp_threshold,
            sql_or(AgentMemory.directive_status.is_(None), AgentMemory.directive_status == 'ativa'),
        ).count()
    except Exception as e:  # coluna directive_status ausente => degradar sem mascarar
        db.session.rollback()
        warnings.append(f"funil indisponivel (coluna ausente?): {e}")

    # Lista (limitada) para inspecao.
    directives = []
    try:
        q = AgentMemory.query.filter(*base)
        if status_filter != 'all':
            if status_filter == 'legado':
                q = q.filter(AgentMemory.directive_status.is_(None))
            else:
                q = q.filter(AgentMemory.directive_status == status_filter)
        rows = q.order_by(
            AgentMemory.importance_score.desc(),
            AgentMemory.effective_count.desc(),
        ).limit(args.limit).all()
        for m in rows:
            st = m.directive_status or 'legado'
            injected = (
                m.directive_status in (None, 'ativa')
                and not m.is_cold
                and (m.importance_score or 0) >= _imp_threshold
            )
            directives.append({
                'id': m.id,
                'path': m.path,
                'status': st,
                'priority': m.priority,
                'importance': round(float(m.importance_score or 0), 2),
                'effective_count': m.effective_count,
                'harmful_count': m.harmful_count,
                'helpful_count': m.helpful_count,
                'is_cold': bool(m.is_cold),
                'injected': bool(injected),
                'titulo': truncate(_titulo_de(m.content), 80),
                'created_at': m.created_at.isoformat() if m.created_at else None,
            })
    except Exception as e:
        db.session.rollback()
        warnings.append(f"listagem indisponivel: {e}")

    data = {
        'scope': 'empresa (user_id=0)',
        'status_filter': status_filter,
        'por_status': por_status,
        'injetaveis': injetaveis,
        'listados': len(directives),
        'directives': directives,
    }

    if args.json_mode:
        success_output('directives', data, json_mode=True, warnings=warnings)
        return

    print("Diretrizes-empresa (funil A4):\n")
    print(f"  Por status: shadow={por_status['shadow']} | ativa={por_status['ativa']} | "
          f"legado={por_status['legado']} | candidata={por_status['candidata']} | "
          f"despromovida={por_status['despromovida']}")
    print(f"  Injetaveis no prompt (teto, antes do filtro nivel-5): {injetaveis}")
    if directives:
        print(f"\n  Listados (filtro={status_filter}, limite={args.limit}):")
        rows = [[
            str(d['id']),
            d['status'],
            d['priority'],
            f"{d['importance']:.2f}",
            'inj' if d['injected'] else '-',
            f"h{d['harmful_count']}/u{d['helpful_count']}",
            d['titulo'],
        ] for d in directives]
        print(format_table(['ID', 'Status', 'Prio', 'Import', 'Inj', 'Harm/Help', 'Titulo'], rows))
    else:
        print(f"\n  (Sem diretrizes para o filtro '{status_filter}'.)")
    for w in warnings:
        print(f"  [!] {w}")


def handle_corrections(args):
    """Correcoes (/memories/corrections/) candidatas a regra dura (mandatory).

    'promovivel' = correction_count >= AGENT_CORRECTION_PROMOTION_THRESHOLD (default 2)
    e priority != 'mandatory' e is_cold=False. Espelha promover_correcoes_recorrentes
    (directive_promotion_service.py:660). Custo $0.
    """
    from app import db
    from app.agente.models import AgentMemory
    from app.utils.timezone import agora_utc_naive
    from datetime import timedelta

    threshold = _threshold()
    uid = _scope_uid(args)
    since = agora_utc_naive() - timedelta(days=args.days)
    warnings = []

    base = [
        AgentMemory.is_directory == False,  # noqa: E712
        AgentMemory.path.like('/memories/corrections/%'),
        AgentMemory.created_at >= since,
    ]
    if uid is not None:
        base.append(AgentMemory.user_id == uid)

    corrections = []
    total = 0
    mandatory_count = 0
    promovivel_count = 0
    try:
        total = AgentMemory.query.filter(*base).count()
        mandatory_count = AgentMemory.query.filter(
            *base, AgentMemory.priority == 'mandatory'
        ).count()
        # COUNT do CONJUNTO (NAO sobre a fatia paginada) — espelha handle_loop_health;
        # senao `promoviveis` ficava <= --limit e divergia do painel (review Onda 3).
        promovivel_count = AgentMemory.query.filter(
            *base,
            AgentMemory.correction_count >= threshold,
            AgentMemory.priority != 'mandatory',
            AgentMemory.is_cold == False,  # noqa: E712
        ).count()
        rows = AgentMemory.query.filter(*base).order_by(
            AgentMemory.correction_count.desc()
        ).limit(args.limit).all()
        for m in rows:
            promovivel = (
                (m.correction_count or 0) >= threshold
                and m.priority != 'mandatory'
                and not m.is_cold
            )
            corrections.append({
                'id': m.id,
                'user_id': m.user_id,
                'path': m.path,
                'error_signature': m.error_signature,
                'correction_count': m.correction_count,
                'priority': m.priority,
                'harmful_count': m.harmful_count,
                'helpful_count': m.helpful_count,
                'is_cold': bool(m.is_cold),
                'promovivel': bool(promovivel),
                'titulo': truncate(_titulo_de(m.content), 80),
                'created_at': m.created_at.isoformat() if m.created_at else None,
            })
    except Exception as e:
        db.session.rollback()
        warnings.append(f"consulta de correcoes indisponivel: {e}")

    data = {
        'period_days': args.days,
        'scope': _scope_label(args),
        'threshold_promocao': threshold,
        'total': total,
        'mandatory_count': mandatory_count,
        'promoviveis': promovivel_count,
        'listadas': len(corrections),
        'corrections': corrections,
    }

    if args.json_mode:
        success_output('corrections', data, json_mode=True, warnings=warnings)
        return

    print(f"Correcoes ({args.days} dias, {_scope_label(args)}):\n")
    print(f"  Total no periodo: {total} | regras duras (mandatory): {mandatory_count} | "
          f"promoviveis (>= {threshold} reincid.): {promovivel_count}")
    if corrections:
        rows = [[
            str(c['id']),
            str(c['user_id']),
            truncate(str(c['error_signature'] or '-'), 28),
            str(c['correction_count']),
            c['priority'],
            'Sim' if c['promovivel'] else '-',
            c['titulo'],
        ] for c in corrections]
        print(format_table(['ID', 'User', 'Assinatura', 'Reinc', 'Prio', 'Promov', 'Titulo'], rows))
    else:
        print("  (Sem correcoes no periodo.)")
    for w in warnings:
        print(f"  [!] {w}")


def handle_loop_health(args):
    """Saude do flywheel: PlanState (gargalo B1) + funil de diretrizes + promocao.

    PlanState: % de sessoes com data->'plan'. <5% => gargalo B1 (promocao A4 vira
    no-op porque a fonte 1 do batch depende de PlanState 100% concluido). Tambem
    expoe o estado das flags que governam o flywheel. Custo $0.
    """
    from app import db
    from app.agente.models import AgentMemory
    from app.utils.timezone import agora_utc_naive
    from datetime import timedelta
    from sqlalchemy import text, func, or_ as sql_or

    uid = _scope_uid(args)
    since = agora_utc_naive() - timedelta(days=args.days)
    warnings = []

    # 1) PlanState (mesma SQL de diagnostico._loop_health).
    plan_state = {'status': 'ok', 'sessions_total': 0, 'with_plan': 0,
                  'with_plan_pct': 0.0, 'teams_sessions': 0, 'gargalo_b1': False}
    try:
        row = db.session.execute(text("""
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE data::jsonb ? 'plan') AS with_plan,
                   count(*) FILTER (WHERE session_id LIKE 'teams_%') AS teams_sessions
            FROM agent_sessions
            WHERE created_at >= :since AND (:uid IS NULL OR user_id = :uid)
        """), {'since': since, 'uid': uid}).fetchone()
        total = (row.total or 0) if row else 0
        with_plan = (row.with_plan or 0) if row else 0
        teams = (row.teams_sessions or 0) if row else 0
        pct = round(100.0 * with_plan / total, 1) if total else 0.0
        plan_state = {
            'status': 'ok', 'sessions_total': total, 'with_plan': with_plan,
            'with_plan_pct': pct, 'teams_sessions': teams,
            'gargalo_b1': bool(total > 0 and pct < 5),
        }
        if plan_state['gargalo_b1']:
            warnings.append("[GARGALO B1] PlanState <5% -> promocao A4 (fonte PlanState) vira no-op")
    except Exception as e:
        db.session.rollback()
        plan_state = {'status': 'query_error', 'error': str(e)}
        warnings.append(f"PlanState indisponivel: {e}")

    # 2) Funil de diretrizes-empresa (schema FIXO).
    directive_funnel = {k: 0 for k in _DIRECTIVE_STATUSES}
    try:
        path_clause = sql_or(
            AgentMemory.path.like(_DIRECTIVE_PATHS[0]),
            AgentMemory.path.like(_DIRECTIVE_PATHS[1]),
        )
        grouped = db.session.query(
            func.coalesce(AgentMemory.directive_status, 'legado'),
            func.count(AgentMemory.id),
        ).filter(
            AgentMemory.user_id == 0,
            AgentMemory.is_directory == False,  # noqa: E712
            path_clause,
        ).group_by(func.coalesce(AgentMemory.directive_status, 'legado')).all()
        for st, n in grouped:
            directive_funnel[st] = int(n)
    except Exception as e:
        db.session.rollback()
        warnings.append(f"funil de diretrizes indisponivel: {e}")

    # 3) Prontidao de promocao de correcoes.
    threshold = _threshold()
    correction_promotion = {'threshold': threshold, 'promoviveis': 0, 'mandatory': 0}
    try:
        cbase = [
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.path.like('/memories/corrections/%'),
        ]
        if uid is not None:
            cbase.append(AgentMemory.user_id == uid)
        correction_promotion['mandatory'] = AgentMemory.query.filter(
            *cbase, AgentMemory.priority == 'mandatory'
        ).count()
        correction_promotion['promoviveis'] = AgentMemory.query.filter(
            *cbase,
            AgentMemory.priority != 'mandatory',
            AgentMemory.is_cold == False,  # noqa: E712
            AgentMemory.correction_count >= threshold,
        ).count()
    except Exception as e:
        db.session.rollback()
        warnings.append(f"prontidao de promocao indisponivel: {e}")

    # 4) Estado das flags que governam o flywheel (contexto p/ entender no-op).
    flags = {}
    try:
        from app.agente.config import feature_flags as ff
        flags = {
            'AGENT_DIRECTIVE_PROMOTION': bool(getattr(ff, 'AGENT_DIRECTIVE_PROMOTION', False)),
            'USE_AGENT_PLANNER': bool(getattr(ff, 'USE_AGENT_PLANNER', False)),
            'AGENT_CORRECTION_PROMOTION': bool(getattr(ff, 'AGENT_CORRECTION_PROMOTION', False)),
        }
    except Exception as e:
        warnings.append(f"flags indisponiveis: {e}")

    data = {
        'period_days': args.days,
        'scope': _scope_label(args),
        'plan_state': plan_state,
        'directive_funnel': directive_funnel,
        'correction_promotion': correction_promotion,
        'flags': flags,
    }

    if args.json_mode:
        success_output('loop-health', data, json_mode=True, warnings=warnings)
        return

    print(f"Saude do Flywheel ({args.days} dias, {_scope_label(args)}):\n")
    if plan_state.get('status') != 'query_error':
        gargalo = " [GARGALO B1]" if plan_state.get('gargalo_b1') else ""
        print(f"  PlanState: {plan_state['with_plan']}/{plan_state['sessions_total']} sessoes "
              f"c/ plano ({plan_state['with_plan_pct']}%){gargalo}")
    df = directive_funnel
    print(f"  Diretrizes: shadow={df['shadow']} | ativa={df['ativa']} | legado={df['legado']} | "
          f"candidata={df['candidata']} | despromovida={df['despromovida']}")
    cp = correction_promotion
    print(f"  Correcoes: {cp['promoviveis']} promoviveis (>= {cp['threshold']}), {cp['mandatory']} ja duras")
    if flags:
        ativos = [k for k, v in flags.items() if v]
        print(f"  Flags ON: {', '.join(ativos) if ativos else '(nenhuma)'}")
    for w in warnings:
        print(f"  [!] {w}")


def _extrai_do(content):
    """Extrai a prescricao (<prescricao>/<do>/linha DO:) — o texto que vira regra."""
    content = content or ''
    for tag in ('prescricao', 'do'):
        m = _re.search(rf'<{tag}>(.*?)</{tag}>', content, _re.DOTALL)
        if m:
            return m.group(1).strip()
    for line in content.splitlines():
        s = line.strip()
        if s.upper().startswith('DO:'):
            return s[3:].strip()
    return content.strip()


def _emit_write_error(command, data, msg, json_mode):
    """Emite erro de WRITE de forma uniforme (envelope ok=False + texto)."""
    success_output(command, data, json_mode=json_mode, errors=[msg])
    if not json_mode:
        print(f"ERRO: {msg}")


def handle_approve(args):
    """[WRITE] Promove diretriz shadow -> ativa. MUTA O PROMPT VIVO (todos os usuarios).

    dry-run (sem --confirm): mostra o <do> + se a diretriz REALMENTE sera injetada
    (filtro nivel-5/importance/cold) + funil. --confirm: directive_status='ativa' +
    reviewed_at/reviewed_by + commit. So aceita quem esta em 'shadow' (idempotencia/seguranca).
    """
    from app import db
    from app.utils.timezone import agora_utc_naive

    mem, err = _load_directive(args.id)
    if err:
        _emit_write_error('approve', {'id': args.id, 'applied': False}, err, args.json_mode)
        return
    if mem.directive_status != 'shadow':
        _emit_write_error('approve', {'id': args.id, 'status_atual': mem.directive_status, 'applied': False},
                          f"id={args.id} tem status '{mem.directive_status or 'legado'}' (so 'shadow' pode ser aprovada)",
                          args.json_mode)
        return

    will_inject = _will_inject(mem)
    flag_on, _ = _injection_params()
    warnings = []
    if not will_inject:
        if not flag_on:
            warnings.append("AGENT_OPERATIONAL_DIRECTIVES=OFF: nenhuma diretriz-empresa e injetada agora. "
                            "A diretriz vira 'ativa' mas so injeta quando a flag ligar (sem nova revisao).")
        else:
            warnings.append("approve sera NO-OP para injecao: o conteudo nao passa no filtro real "
                            "(nivel-5 / importance>=threshold / nao-cold / sem <prescricao>/DO:). "
                            "Vira 'ativa' mas NAO entra no prompt.")
    preview = {
        'id': mem.id, 'path': mem.path,
        'titulo': _titulo_de(mem.content),
        'do': truncate(_extrai_do(mem.content), 400),
        'importance': round(float(mem.importance_score or 0), 2),
        'is_cold': bool(mem.is_cold),
        'will_inject': bool(will_inject),
    }

    if not args.confirm:
        data = {'dry_run': True, 'applied': False, 'preview': preview}
        if args.json_mode:
            success_output('approve', data, json_mode=True, warnings=warnings)
            return
        print(f"[DRY-RUN] approve id={mem.id} (shadow -> ativa):\n")
        print(f"  Titulo: {preview['titulo']}")
        print(f"  DO: {preview['do']}")
        print(f"  Sera injetada no prompt? {'SIM' if will_inject else 'NAO (no-op de injecao)'}")
        for w in warnings:
            print(f"  [!] {w}")
        print("\n  Rode com --confirm para promover (ATENCAO: MUTA O PROMPT PROD VIVO).")
        return

    # TOCTOU: re-carrega COM LOCK e re-valida o status antes de mutar (review fase 3b).
    from app.agente.models import AgentMemory
    locked = AgentMemory.query.filter_by(id=args.id).with_for_update().first()
    if locked is None or locked.directive_status != 'shadow':
        db.session.rollback()
        _emit_write_error('approve', {'id': args.id, 'applied': False},
                          f"id={args.id} nao esta mais em 'shadow' (status="
                          f"{getattr(locked, 'directive_status', None)}) — concorrencia/ja operado",
                          args.json_mode)
        return
    locked.directive_status = 'ativa'
    locked.reviewed_at = agora_utc_naive()  # AgentMemory NAO tem reviewed_by — so reviewed_at (quem = log da CLI)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        _emit_write_error('approve', {'id': args.id, 'applied': False}, f"commit falhou: {e}", args.json_mode)
        return
    data = {'dry_run': False, 'applied': True, 'preview': preview}
    if args.json_mode:
        success_output('approve', data, json_mode=True, warnings=warnings)
        return
    print(f"OK: id={mem.id} promovida shadow -> ativa por user_id={args.user_id} "
          f"(injecao no prompt: {'SIM' if will_inject else 'NAO'}).")
    for w in warnings:
        print(f"  [!] {w}")


def handle_reject(args):
    """[WRITE] Rejeita diretriz shadow/candidata -> despromovida (nao e injetada)."""
    from app import db
    from app.utils.timezone import agora_utc_naive

    mem, err = _load_directive(args.id)
    if err:
        _emit_write_error('reject', {'id': args.id, 'applied': False}, err, args.json_mode)
        return
    if mem.directive_status not in ('shadow', 'candidata'):
        _emit_write_error('reject', {'id': args.id, 'status_atual': mem.directive_status, 'applied': False},
                          f"id={args.id} tem status '{mem.directive_status or 'legado'}' (so 'shadow'/'candidata' podem ser rejeitadas)",
                          args.json_mode)
        return

    preview = {'id': mem.id, 'path': mem.path, 'titulo': _titulo_de(mem.content),
               'status_atual': mem.directive_status}

    if not args.confirm:
        data = {'dry_run': True, 'applied': False, 'preview': preview}
        if args.json_mode:
            success_output('reject', data, json_mode=True)
            return
        print(f"[DRY-RUN] reject id={mem.id} ({mem.directive_status} -> despromovida):")
        print(f"  Titulo: {preview['titulo']}")
        print("\n  Rode com --confirm para rebaixar.")
        return

    # TOCTOU: re-carrega COM LOCK e re-valida antes de mutar (review fase 3b).
    from app.agente.models import AgentMemory
    locked = AgentMemory.query.filter_by(id=args.id).with_for_update().first()
    if locked is None or locked.directive_status not in ('shadow', 'candidata'):
        db.session.rollback()
        _emit_write_error('reject', {'id': args.id, 'applied': False},
                          f"id={args.id} nao esta mais em 'shadow'/'candidata' (status="
                          f"{getattr(locked, 'directive_status', None)}) — concorrencia/ja operado",
                          args.json_mode)
        return
    locked.directive_status = 'despromovida'
    locked.reviewed_at = agora_utc_naive()  # AgentMemory NAO tem reviewed_by — so reviewed_at
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        _emit_write_error('reject', {'id': args.id, 'applied': False}, f"commit falhou: {e}", args.json_mode)
        return
    data = {'dry_run': False, 'applied': True, 'preview': preview}
    if args.json_mode:
        success_output('reject', data, json_mode=True)
        return
    print(f"OK: id={mem.id} rebaixada -> despromovida por user_id={args.user_id}.")


def handle_promote_batch(args):
    """[WRITE] Roda o batch A4 (run_directive_promotion_batch).

    Cria shadows (de PlanState/judge — nao injetadas) E promove correcoes recorrentes
    a 'mandatory' (INJETADAS via <user_rules>). dry-run mostra o estado + flags; --confirm
    executa. O batch commita internamente. Custo $0 de LLM (heuristica deterministica).
    """
    from app import db
    from app.agente.models import AgentMemory
    from sqlalchemy import func, or_ as sql_or

    threshold = _threshold()
    warnings = ["O batch promove correcoes recorrentes (>= threshold) a 'mandatory' "
                "-> elas passam a ser INJETADAS via <user_rules> na PROXIMA sessao do agente.",
                "O canal <user_rules> e INDEPENDENTE de AGENT_OPERATIONAL_DIRECTIVES "
                "(controlado por USE_USER_RULES_CHANNEL): correcoes mandatory injetam mesmo com aquela flag OFF."]
    flags = {}
    try:
        from app.agente.config import feature_flags as ff
        flags = {
            'AGENT_DIRECTIVE_PROMOTION': bool(getattr(ff, 'AGENT_DIRECTIVE_PROMOTION', False)),
            'AGENT_CORRECTION_PROMOTION': bool(getattr(ff, 'AGENT_CORRECTION_PROMOTION', False)),
            'USE_USER_RULES_CHANNEL': bool(getattr(ff, 'USE_USER_RULES_CHANNEL', True)),
            'USE_AGENT_PLANNER': bool(getattr(ff, 'USE_AGENT_PLANNER', False)),
        }
    except Exception as e:
        warnings.append(f"flags indisponiveis: {e}")

    # Estado atual (preview): funil + correcoes promoviveis.
    funnel = {k: 0 for k in _DIRECTIVE_STATUSES}
    promoviveis = 0
    try:
        path_clause = sql_or(AgentMemory.path.like(_DIRECTIVE_PATHS[0]), AgentMemory.path.like(_DIRECTIVE_PATHS[1]))
        for st, n in db.session.query(
            func.coalesce(AgentMemory.directive_status, 'legado'), func.count(AgentMemory.id),
        ).filter(AgentMemory.user_id == 0, AgentMemory.is_directory == False, path_clause).group_by(  # noqa: E712
            func.coalesce(AgentMemory.directive_status, 'legado')
        ).all():
            funnel[st] = int(n)
        promoviveis = AgentMemory.query.filter(
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.path.like('/memories/corrections/%'),
            AgentMemory.priority != 'mandatory',
            AgentMemory.is_cold == False,  # noqa: E712
            AgentMemory.correction_count >= threshold,
        ).count()
    except Exception as e:
        db.session.rollback()
        warnings.append(f"estado indisponivel: {e}")

    estado = {'directive_funnel': funnel, 'correcoes_promoviveis': promoviveis, 'flags': flags}

    if not args.confirm:
        data = {'dry_run': True, 'executed': False, 'lookback_hours': args.lookback_hours,
                'limit': args.limit, 'estado': estado}
        if args.json_mode:
            success_output('promote-batch', data, json_mode=True, warnings=warnings)
            return
        print(f"[DRY-RUN] promote-batch (lookback={args.lookback_hours}h, limit={args.limit}):\n")
        print(f"  Funil atual: shadow={funnel['shadow']} ativa={funnel['ativa']} legado={funnel['legado']} "
              f"candidata={funnel['candidata']} despromovida={funnel['despromovida']}")
        print(f"  Correcoes promoviveis (-> mandatory): {promoviveis}")
        print(f"  Flags: {', '.join(k for k, v in flags.items() if v) or '(nenhuma ON)'}")
        for w in warnings:
            print(f"  [!] {w}")
        print("\n  Rode com --confirm para executar o batch A4.")
        return

    from app.agente.services.directive_promotion_service import run_directive_promotion_batch
    resultado = run_directive_promotion_batch(lookback_hours=args.lookback_hours, limit=args.limit)
    data = {'dry_run': False, 'executed': True, 'estado_antes': estado, 'resultado': resultado}
    if args.json_mode:
        success_output('promote-batch', data, json_mode=True, warnings=warnings)
        return
    print("OK: batch A4 executado. Resultado:")
    for k, v in (resultado or {}).items():
        print(f"  {k}: {v}")
    for w in warnings:
        print(f"  [!] {w}")


HANDLERS = {
    'directives': handle_directives,
    'corrections': handle_corrections,
    'loop-health': handle_loop_health,
    'approve': handle_approve,
    'reject': handle_reject,
    'promote-batch': handle_promote_batch,
}


def main():
    run_handler('Flywheel de diretrizes do Agente Web (READ + WRITE dev-only)', SUBCOMMANDS, HANDLERS)


if __name__ == '__main__':
    main()
