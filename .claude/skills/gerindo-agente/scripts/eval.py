#!/usr/bin/env python3
"""
eval.py — historico de evals + calibracao do judge (Agente Web, Onda 3).

Custo $0 de tokens (so leitura/escrita pontual no banco — NAO dispara avaliacao).
Subcomandos:

  scores   Serie agregada por agente (agent_eval_scores): score atual + delta vs
           o run anterior (baseline) + modo (report_only|enforce). HISTORICO:
           a escrita foi aposentada com o eval_runner/A3 (estrategia R2, 2026-06-12).
  cases    Casos (agent_eval_case): score/status por caso + veredito humano
           (human_verdict) + taxa de concordancia judge-vs-humano (calibracao).
           Fonte VIVA: calibration_sampler (online judge, GATE-1).
  review   [WRITE dev-only] marca human_verdict de um caso (calibracao), atras
           de --confirm.

O subcomando `run` (enfileirava o eval_runner A3 na RQ 'agent_eval') foi REMOVIDO
na estrategia R2 (2026-06-12): A3 aposentado, fila e flag AGENT_EVAL_GATE removidas.
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
    # ── WRITE (fase 3b, DEV-ONLY) — dry-run e o DEFAULT; so escreve com --confirm ──
    'review': {
        'help': '[WRITE] Marca human_verdict de UM agent_eval_case (calibracao). dry-run sem --confirm',
        'args': [
            {'name': '--case-id', 'type': int, 'required': True, 'help': 'ID do agent_eval_case'},
            {'name': '--verdict', 'type': str, 'required': True, 'help': 'agree|disagree (concorda/discorda do judge)'},
            {'name': '--note', 'type': str, 'default': None, 'help': 'Nota livre opcional'},
            {'name': '--confirm', 'action': 'store_true', 'help': 'Efetiva o veredito (sem isso = preview)'},
        ],
    },
    # 'run' REMOVIDO (estrategia R2, 2026-06-12): enfileirava o eval_runner/A3
    # (aposentado) na RQ 'agent_eval' (removida).
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
        print("  (Sem scores registrados — escrita aposentada com o A3; tabela e so historico.)")
    for w in warnings:
        print(f"  [!] {w}")


def handle_cases(args):
    """Casos (agent_eval_case) + concordancia humana (calibracao do judge).

    human_verdict NULL = nao revisado. concordance_rate = agree/reviewed
    (literatura: ~85% judge-vs-humano e o esperado). Fonte viva: calibration_sampler
    (online judge, GATE-1) — degrada para lista vazia sem erro.
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
        print("  (Sem casos — calibration_sampler (AGENT_CALIBRATION_SAMPLER) ainda nao populou.)")
    for w in warnings:
        print(f"  [!] {w}")


def _emit_write_error(command, data, msg, json_mode):
    """Emite erro de WRITE de forma uniforme (envelope ok=False + texto)."""
    success_output(command, data, json_mode=json_mode, errors=[msg])
    if not json_mode:
        print(f"ERRO: {msg}")


def handle_review(args):
    """[WRITE] Marca human_verdict de UM agent_eval_case. Fecha o gap do UPDATE manual.

    dry-run: mostra o caso + verdict atual. --confirm: human_verdict/human_note/reviewed_by/
    reviewed_at + commit. verdict deve ser agree|disagree (calibracao judge-vs-humano).
    """
    from app import db
    from app.agente.models import AgentEvalCase
    from app.utils.timezone import agora_utc_naive

    verdict = (getattr(args, 'verdict', '') or '').strip().lower()
    if verdict not in ('agree', 'disagree'):
        _emit_write_error('review', {'case_id': args.case_id, 'applied': False},
                          f"verdict invalido '{verdict}' (use agree|disagree)", args.json_mode)
        return
    case = AgentEvalCase.query.get(args.case_id)
    if case is None:
        _emit_write_error('review', {'case_id': args.case_id, 'applied': False},
                          f"agent_eval_case id={args.case_id} nao encontrado", args.json_mode)
        return

    preview = {
        'id': case.id, 'agent_name': case.agent_name, 'case_id': case.case_id,
        'case_score': round(float(case.case_score), 4), 'status': case.status,
        'human_verdict_atual': case.human_verdict, 'novo_verdict': verdict,
    }
    warnings = []
    if case.human_verdict:
        warnings.append(f"ATENCAO: sobrescrevendo verdict existente ('{case.human_verdict}' -> '{verdict}').")

    if not args.confirm:
        data = {'dry_run': True, 'applied': False, 'preview': preview}
        if args.json_mode:
            success_output('review', data, json_mode=True, warnings=warnings)
            return
        print(f"[DRY-RUN] review case_id={case.id} ({case.agent_name}/{case.case_id}):")
        print(f"  score={preview['case_score']} status={case.status} | "
              f"verdict atual={case.human_verdict or '-'} -> {verdict}")
        for w in warnings:
            print(f"  [!] {w}")
        print("\n  Rode com --confirm para gravar o veredito.")
        return

    case.human_verdict = verdict
    case.human_note = getattr(args, 'note', None)
    case.reviewed_by = args.user_id
    case.reviewed_at = agora_utc_naive()
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        _emit_write_error('review', {'case_id': args.case_id, 'applied': False}, f"commit falhou: {e}", args.json_mode)
        return
    data = {'dry_run': False, 'applied': True, 'preview': preview}
    if args.json_mode:
        success_output('review', data, json_mode=True, warnings=warnings)
        return
    print(f"OK: case_id={case.id} human_verdict='{verdict}' (reviewed_by={args.user_id}).")
    for w in warnings:
        print(f"  [!] {w}")


HANDLERS = {
    'scores': handle_scores,
    'cases': handle_cases,
    'review': handle_review,
}


def main():
    run_handler('Historico de evals + calibracao do judge (READ + review dev-only)', SUBCOMMANDS, HANDLERS)


if __name__ == '__main__':
    main()
