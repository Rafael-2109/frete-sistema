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
            AgentMemory.importance_score >= 0.7,
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
                and (m.importance_score or 0) >= 0.7
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


HANDLERS = {
    'directives': handle_directives,
    'corrections': handle_corrections,
    'loop-health': handle_loop_health,
}


def main():
    run_handler('Flywheel de diretrizes do Agente Web (READ)', SUBCOMMANDS, HANDLERS)


if __name__ == '__main__':
    main()
