#!/usr/bin/env python3
"""
eval.py — eval-gate offline (A3) do Agente Web (READ, Onda 3 / fase 3a).

Expoe a camada A3 (golden dataset / eval_gate_service) para INSPECAO. Custo $0 de
tokens (so leitura do banco — NAO dispara avaliacao). Subcomandos:

  scores   Serie agregada por agente (agent_eval_scores): score atual + delta vs
           o run anterior (baseline) + modo (report_only|enforce).
  cases    Casos por run (agent_eval_case): score/status por caso + veredito humano
           (human_verdict) + taxa de concordancia judge-vs-humano (calibracao).

ESCRITA (review human_verdict, run -> dispara eval_runner com custo Haiku+Opus) NAO
mora aqui: fase 3b, dev-only atras de --confirm + aviso de custo. Ver
docs/superpowers/plans/2026-06-03-evolucao-gerindo-agente.md (Onda 3).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from common import (
    format_table, run_handler, success_output, truncate,
)


SUBCOMMANDS = {
    'scores': {
        'help': 'Serie de scores por agente (agent_eval_scores) + delta vs baseline — custo $0',
        'args': [
            {'name': '--agent', 'type': str, 'default': None, 'help': 'Filtra por agent_name (default: todos)'},
        ],
    },
    'cases': {
        'help': 'Casos por run (agent_eval_case) + concordancia judge-vs-humano — custo $0',
        'args': [
            {'name': '--agent', 'type': str, 'default': None, 'help': 'Filtra por agent_name (default: todos)'},
            {'name': '--status', 'type': str, 'default': None, 'help': 'Filtra por status: pass|fail|error (default: todos)'},
        ],
    },
}


def handle_scores(args):
    """Score atual por agente + delta vs o run anterior (baseline).

    1 linha por agente: o run mais recente e a diferenca para o penultimo. Espelha
    AgentEvalScore.get_baseline_score (models.py:1879), que e o 'penultimo' run.
    """
    from app import db
    from app.agente.models import AgentEvalScore

    agent_filter = getattr(args, 'agent', None)
    warnings = []
    latest = []
    total_runs = 0
    try:
        nq = db.session.query(AgentEvalScore.agent_name).distinct()
        if agent_filter:
            nq = nq.filter(AgentEvalScore.agent_name == agent_filter)
        agent_names = sorted(r[0] for r in nq.all())
        for name in agent_names:
            recent = AgentEvalScore.query.filter_by(agent_name=name).order_by(
                AgentEvalScore.recorded_at.desc(), AgentEvalScore.id.desc()
            ).limit(2).all()
            if not recent:
                continue
            cur = recent[0]
            prev = recent[1] if len(recent) > 1 else None
            runs = AgentEvalScore.query.filter_by(agent_name=name).count()
            total_runs += runs
            latest.append({
                'agent_name': name,
                'score': round(float(cur.score), 4),
                'total': cur.total,
                'passed': cur.passed,
                'mode': cur.mode,
                'git_sha': cur.git_sha,
                'runs': runs,
                'delta_vs_prev': round(float(cur.score) - float(prev.score), 4) if prev else None,
                'recorded_at': cur.recorded_at.isoformat() if cur.recorded_at else None,
            })
    except Exception as e:
        db.session.rollback()
        warnings.append(f"consulta de scores indisponivel: {e}")

    data = {
        'agent_filter': agent_filter,
        'agentes': len(latest),
        'total_runs': total_runs,
        'scores': latest,
    }

    if args.json_mode:
        success_output('scores', data, json_mode=True, warnings=warnings)
        return

    print("Eval scores (A3) — ultimo run por agente:\n")
    if latest:
        rows = []
        for s in latest:
            d = s['delta_vs_prev']
            d_str = '-' if d is None else (f"+{d:.3f}" if d >= 0 else f"{d:.3f}")
            rows.append([
                truncate(s['agent_name'], 28),
                f"{s['score']:.3f}",
                f"{s['passed']}/{s['total']}",
                d_str,
                s['mode'] or '-',
                str(s['runs']),
            ])
        print(format_table(['Agente', 'Score', 'Pass/Tot', 'Delta', 'Modo', 'Runs'], rows))
    else:
        print("  (Sem scores registrados — eval_runner ainda nao rodou.)")
    for w in warnings:
        print(f"  [!] {w}")


def handle_cases(args):
    """Casos por run (agent_eval_case) + concordancia humana (calibracao do judge).

    human_verdict NULL = nao revisado. concordance_rate (models.py:2095) = agree/reviewed
    (literatura: ~85% judge-vs-humano e o esperado). Em PROD a tabela hoje tem 0 linhas
    (USE_AGENT_EVAL_CALIBRATION OFF) — degrada para lista vazia sem erro.
    """
    from app import db
    from app.agente.models import AgentEvalCase

    agent_filter = getattr(args, 'agent', None)
    status_filter = getattr(args, 'status', None)
    warnings = []
    cases = []
    total = 0
    by_status = {'pass': 0, 'fail': 0, 'error': 0}
    concordance = {'reviewed': 0, 'agree': 0, 'disagree': 0, 'rate': None}
    try:
        base = AgentEvalCase.query
        if agent_filter:
            base = base.filter(AgentEvalCase.agent_name == agent_filter)
        if status_filter:
            base = base.filter(AgentEvalCase.status == status_filter)
        total = base.count()
        # by_status = distribuicao do CONJUNTO (COUNT sobre `base`, NAO sobre a fatia
        # paginada) — senao soma != total quando ha mais casos que --limit (review Onda 3).
        for st in ('pass', 'fail', 'error'):
            by_status[st] = base.filter(AgentEvalCase.status == st).count()
        rows = base.order_by(
            AgentEvalCase.recorded_at.desc(), AgentEvalCase.id.desc()
        ).limit(args.limit).all()
        for c in rows:
            cases.append({
                'id': c.id,
                'agent_name': c.agent_name,
                'case_id': c.case_id,
                'case_score': round(float(c.case_score), 4),
                'status': c.status,
                'n_runs': c.n_runs,
                'human_verdict': c.human_verdict,
                'reviewed_by': c.reviewed_by,
                'reviewed_at': c.reviewed_at.isoformat() if c.reviewed_at else None,
                'recorded_at': c.recorded_at.isoformat() if c.recorded_at else None,
            })
        conc = AgentEvalCase.concordance_rate(agent_name=agent_filter)
        if isinstance(conc, dict):
            concordance = {
                'reviewed': conc.get('reviewed', 0),
                'agree': conc.get('agree', 0),
                'disagree': conc.get('disagree', 0),
                'rate': conc.get('rate'),
            }
    except Exception as e:
        db.session.rollback()
        warnings.append(f"consulta de casos indisponivel: {e}")

    data = {
        'agent_filter': agent_filter,
        'status_filter': status_filter,
        'total': total,
        'listados': len(cases),
        'by_status': by_status,
        'concordance': concordance,
        'cases': cases,
    }

    if args.json_mode:
        success_output('cases', data, json_mode=True, warnings=warnings)
        return

    print("Eval cases (A3) — calibracao judge-vs-humano:\n")
    print(f"  Total: {total} | pass={by_status['pass']} fail={by_status['fail']} error={by_status['error']}")
    rate = concordance['rate']
    rate_str = '-' if rate is None else f"{rate:.1%}"
    print(f"  Concordancia humana: {concordance['agree']}/{concordance['reviewed']} ({rate_str})")
    if cases:
        rows = [[
            truncate(c['agent_name'], 22),
            c['case_id'],
            f"{c['case_score']:.3f}",
            c['status'],
            c['human_verdict'] or '-',
        ] for c in cases]
        print(format_table(['Agente', 'Caso', 'Score', 'Status', 'Veredito'], rows))
    else:
        print("  (Sem casos — USE_AGENT_EVAL_CALIBRATION OFF ou eval_runner nao populou.)")
    for w in warnings:
        print(f"  [!] {w}")


HANDLERS = {
    'scores': handle_scores,
    'cases': handle_cases,
}


def main():
    run_handler('Eval-gate offline (A3) do Agente Web (READ)', SUBCOMMANDS, HANDLERS)


if __name__ == '__main__':
    main()
