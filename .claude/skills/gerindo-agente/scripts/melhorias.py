#!/usr/bin/env python3
"""
melhorias.py — dialogo de melhoria (D8) + intelligence report (D7) do Agente Web
(READ, Onda 3 / fase 3a). Custo $0 de tokens (so leitura). Subcomandos:

  list-open            Sugestoes abertas (proposed/responded, v1) por categoria/severidade
                       — fonte AgentImprovementDialogue.get_open_by_category (models.py:1307).
  show --key K         Historico completo (v1/v2/v3) de uma suggestion_key.
  intelligence-report  Relatorio D7 mais recente + serie por report_date + top recs
                       — fonte AgentIntelligenceReport.get_latest (models.py:1108).

ESCRITA (respond accept/reject sobre agent_improvement_dialogue) NAO mora aqui:
fase 3b, dev-only atras de --confirm. Backing da resposta = upsert_response
(models.py:1334) / rota PUT /<id>/respond — NAO improvement_suggester. Ver
docs/superpowers/plans/2026-06-03-evolucao-gerindo-agente.md (Onda 3).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from common import (
    format_table, run_handler, success_output, truncate,
)


SUBCOMMANDS = {
    'list-open': {
        'help': 'Sugestoes de melhoria abertas (proposed/responded) — custo $0',
        'args': [
            {'name': '--category', 'type': str, 'default': None,
             'help': 'Filtra por categoria (skill_suggestion|instruction_request|...)'},
        ],
    },
    'show': {
        'help': 'Historico v1/v2/v3 de uma suggestion_key — custo $0',
        'args': [
            {'name': '--key', 'type': str, 'required': True, 'help': 'suggestion_key (ex: IMP-2026-06-03-001)'},
        ],
    },
    'intelligence-report': {
        'help': 'Relatorio D7 mais recente + serie + top recomendacoes — custo $0',
        'args': [],
    },
}

# Ordem de severidade para apresentacao (menor = mais grave).
_SEV_ORDER = {'critical': 0, 'warning': 1, 'info': 2}


def _sev_key(item):
    return (_SEV_ORDER.get((item.get('severity') or '').lower(), 9), item.get('created_at') or '')


def handle_list_open(args):
    """Sugestoes abertas (status in proposed/responded, version=1), ordenadas por severidade.

    Reusa AgentImprovementDialogue.get_open_by_category (models.py:1307) — mesma fonte
    usada para deduplicacao no batch. Filtro --category e cap --limit aplicados aqui.
    """
    from app import db
    from app.agente.models import AgentImprovementDialogue

    category_filter = getattr(args, 'category', None)
    warnings = []
    items = []
    total_open = 0
    by_status = {'proposed': 0, 'responded': 0}
    try:
        rows = AgentImprovementDialogue.get_open_by_category()
        total_open = len(rows)
        for r in rows:
            # get_open_by_category retorna so proposed/responded (models.py:1307);
            # so contamos esses dois -> by_status com schema FIXO (snapshot-safe).
            if r.status in by_status:
                by_status[r.status] += 1
        filtered = [r for r in rows if (not category_filter or r.category == category_filter)]
        for r in filtered:
            items.append({
                'id': r.id,
                'suggestion_key': r.suggestion_key,
                'version': r.version,
                'category': r.category,
                'severity': r.severity,
                'status': r.status,
                'title': truncate(r.title or '', 90),
                'created_at': r.created_at.isoformat() if r.created_at else None,
            })
        items.sort(key=_sev_key)
        items = items[:args.limit]
    except Exception as e:
        db.session.rollback()
        warnings.append(f"consulta de sugestoes indisponivel: {e}")

    data = {
        'category_filter': category_filter,
        'total_abertas': total_open,
        'by_status': by_status,
        'listadas': len(items),
        'suggestions': items,
    }

    if args.json_mode:
        success_output('list-open', data, json_mode=True, warnings=warnings)
        return

    print("Sugestoes de melhoria abertas (D8):\n")
    print(f"  Total abertas: {total_open} | proposed={by_status.get('proposed', 0)} | "
          f"responded={by_status.get('responded', 0)}")
    if items:
        rows = [[
            s['suggestion_key'],
            str(s['severity']).upper(),
            truncate(str(s['category'] or '-'), 20),
            s['status'],
            s['title'],
        ] for s in items]
        print(format_table(['Chave', 'Sever', 'Categoria', 'Status', 'Titulo'], rows))
    else:
        print("  (Nenhuma sugestao aberta para o filtro.)")
    for w in warnings:
        print(f"  [!] {w}")


def handle_show(args):
    """Historico completo (v1/v2/v3) de uma suggestion_key. Shape estavel (found + versions[])."""
    from app import db
    from app.agente.models import AgentImprovementDialogue

    key = args.key
    warnings = []
    versions = []
    try:
        rows = AgentImprovementDialogue.query.filter_by(
            suggestion_key=key
        ).order_by(AgentImprovementDialogue.version.asc()).all()
        for r in rows:
            versions.append({
                'version': r.version,
                'author': r.author,
                'status': r.status,
                'category': r.category,
                'severity': r.severity,
                'title': r.title,
                'description': r.description,
                'affected_files': list(r.affected_files) if r.affected_files else [],
                'implementation_notes': r.implementation_notes,
                'auto_implemented': bool(r.auto_implemented),
                'created_at': r.created_at.isoformat() if r.created_at else None,
                'updated_at': r.updated_at.isoformat() if r.updated_at else None,
            })
    except Exception as e:
        db.session.rollback()
        warnings.append(f"consulta indisponivel: {e}")

    data = {
        'suggestion_key': key,
        'found': len(versions) > 0,
        'versions': versions,
    }

    if args.json_mode:
        success_output('show', data, json_mode=True, warnings=warnings)
        return

    if not versions:
        print(f"suggestion_key '{key}': nao encontrada.")
        for w in warnings:
            print(f"  [!] {w}")
        return
    print(f"Historico de {key} ({len(versions)} versao(oes)):\n")
    for v in versions:
        print(f"  v{v['version']} [{v['author']}] status={v['status']} severidade={v['severity']}")
        print(f"    {truncate(v['title'] or '', 100)}")
        if v['affected_files']:
            print(f"    arquivos: {', '.join(v['affected_files'][:5])}")
        if v['implementation_notes']:
            print(f"    notas: {truncate(v['implementation_notes'], 120)}")
    for w in warnings:
        print(f"  [!] {w}")


def handle_intelligence_report(args):
    """Relatorio D7 mais recente + serie por report_date + top recomendacoes.

    AgentIntelligenceReport nao tem get_series (models.py): a serie e montada por
    query order_by(report_date desc).limit(N). As recomendacoes vem de
    report_json['recommendations'] do mais recente.
    """
    from app import db
    from app.agente.models import AgentIntelligenceReport

    warnings = []
    # 'latest' e SEMPRE um dict de schema FIXO (escalares null quando nao ha report)
    # para o shape ser estavel com/sem dados (banco local vazio vs PROD com 5 reports).
    latest = {
        'report_date': None, 'health_score': None, 'friction_score': None,
        'recommendation_count': None, 'sessions_analyzed': None,
    }
    has_report = False
    series = []
    top_recommendations = []
    try:
        rep = AgentIntelligenceReport.get_latest()
        if rep is not None:
            has_report = True
            latest = {
                'report_date': rep.report_date.isoformat() if rep.report_date else None,
                'health_score': float(rep.health_score) if rep.health_score is not None else None,
                'friction_score': float(rep.friction_score) if rep.friction_score is not None else None,
                'recommendation_count': rep.recommendation_count,
                'sessions_analyzed': rep.sessions_analyzed,
            }
            rj = rep.report_json or {}
            recs = rj.get('recommendations', []) if isinstance(rj, dict) else []
            for r in (recs or [])[:5]:
                if isinstance(r, dict):
                    top_recommendations.append({
                        'severity': r.get('severity'),
                        'title': r.get('title'),
                    })
        rows = AgentIntelligenceReport.query.order_by(
            AgentIntelligenceReport.report_date.desc()
        ).limit(args.limit).all()
        for r in rows:
            series.append({
                'report_date': r.report_date.isoformat() if r.report_date else None,
                'health_score': float(r.health_score) if r.health_score is not None else None,
                'friction_score': float(r.friction_score) if r.friction_score is not None else None,
                'recommendation_count': r.recommendation_count,
                'sessions_analyzed': r.sessions_analyzed,
            })
    except Exception as e:
        db.session.rollback()
        warnings.append(f"consulta de intelligence report indisponivel: {e}")

    data = {
        'has_report': has_report,
        'latest': latest,
        'series_count': len(series),
        'series': series,
        'top_recommendations': top_recommendations,
    }

    if args.json_mode:
        success_output('intelligence-report', data, json_mode=True, warnings=warnings)
        return

    print("Intelligence Report (D7):\n")
    if not has_report:
        print("  (Nenhum relatorio gerado ainda — cron D7 nao rodou.)")
    else:
        print(f"  Mais recente: {latest['report_date']} | saude {latest['health_score']} | "
              f"friccao {latest['friction_score']} | {latest['recommendation_count']} recs | "
              f"{latest['sessions_analyzed']} sessoes")
        if top_recommendations:
            print("\n  Top recomendacoes:")
            for r in top_recommendations:
                print(f"    [{str(r.get('severity', '?')).upper()}] {r.get('title', '')}")
        if len(series) > 1:
            print(f"\n  Serie ({len(series)} relatorios):")
            rows = [[
                s['report_date'],
                str(s['health_score']),
                str(s['friction_score']),
                str(s['recommendation_count']),
            ] for s in series]
            print(format_table(['Data', 'Saude', 'Friccao', 'Recs'], rows))
    for w in warnings:
        print(f"  [!] {w}")


HANDLERS = {
    'list-open': handle_list_open,
    'show': handle_show,
    'intelligence-report': handle_intelligence_report,
}


def main():
    run_handler('Dialogo de melhoria (D8) + intelligence report (D7) do Agente Web (READ)',
                SUBCOMMANDS, HANDLERS)


if __name__ == '__main__':
    main()
