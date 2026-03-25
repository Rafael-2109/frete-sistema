#!/usr/bin/env python3
"""
Eval de Roteamento — Métricas de saúde do routing do agente web.

Custo: $0 (queries PostgreSQL puras, zero chamadas LLM).

Produz relatório com:
  1. Baseline mensal (sessões, mensagens, tools)
  2. Distribuição de skills por mês
  3. Taxa de ambiguidade (AskUserQuestion / total)
  4. Sessões "struggling" (muitas msgs, poucos tools = routing perdido)
  5. Correções e memórias mais corrigidas
  6. Dataset de regressão para tracking futuro

Uso:
  source .venv/bin/activate
  python scripts/eval_roteamento.py [--json] [--meses 3]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db


def _query(sql, params=None):
    """Executa query read-only e retorna lista de dicts."""
    result = db.session.execute(db.text(sql), params or {})
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]


def baseline_mensal(meses=3):
    """Sessões, mensagens e tools por mês."""
    return _query("""
        SELECT
            TO_CHAR(created_at, 'YYYY-MM') as mes,
            COUNT(*) as sessoes,
            COUNT(*) FILTER (WHERE summary IS NOT NULL) as com_summary,
            COUNT(DISTINCT user_id) as usuarios_unicos,
            ROUND(AVG(message_count)) as avg_msgs,
            SUM(message_count) as total_msgs
        FROM agent_sessions
        WHERE created_at >= NOW() - INTERVAL ':meses months'
        GROUP BY mes
        ORDER BY mes DESC
    """.replace(':meses', str(int(meses))))


def distribuicao_skills(meses=3):
    """Quais skills/tools são usados e com que frequência."""
    return _query("""
        SELECT
            tool_name,
            COUNT(*) as vezes_usado,
            COUNT(DISTINCT s.id) as sessoes_distintas
        FROM (
            SELECT id, jsonb_array_elements_text(summary->'ferramentas_usadas') as tool_name
            FROM agent_sessions
            WHERE summary IS NOT NULL
            AND summary->'ferramentas_usadas' IS NOT NULL
            AND created_at >= NOW() - INTERVAL ':meses months'
        ) sub
        JOIN agent_sessions s ON s.id = sub.id
        GROUP BY tool_name
        ORDER BY vezes_usado DESC
    """.replace(':meses', str(int(meses))))


def taxa_ambiguidade(meses=3):
    """Sessões onde AskUserQuestion foi usado (= incerteza de routing)."""
    rows = _query("""
        SELECT
            TO_CHAR(created_at, 'YYYY-MM') as mes,
            COUNT(*) as total_sessoes,
            COUNT(*) FILTER (
                WHERE summary IS NOT NULL
                AND summary->'ferramentas_usadas' @> '"AskUserQuestion"'
            ) as sessoes_com_askuser,
            COUNT(*) FILTER (
                WHERE summary IS NOT NULL
                AND summary->'ferramentas_usadas' @> '"Skill"'
            ) as sessoes_com_skill
        FROM agent_sessions
        WHERE created_at >= NOW() - INTERVAL ':meses months'
        GROUP BY mes
        ORDER BY mes DESC
    """.replace(':meses', str(int(meses))))

    for r in rows:
        total = r['total_sessoes'] or 1
        r['taxa_askuser_pct'] = round(100 * (r['sessoes_com_askuser'] or 0) / total, 1)
        r['taxa_skill_pct'] = round(100 * (r['sessoes_com_skill'] or 0) / total, 1)
    return rows


def sessoes_struggling(meses=3, threshold_msgs=15, threshold_tools=2):
    """
    Sessões com muitas mensagens mas poucos tools distintos.
    Proxy para "routing perdido" — usuário insiste, agente não encontra skill.
    """
    return _query("""
        SELECT
            s.id,
            s.user_id,
            s.message_count,
            s.created_at::date as data,
            LEFT(s.data->'messages'->0->>'content', 120) as primeira_msg,
            jsonb_array_length(COALESCE(s.summary->'ferramentas_usadas', '[]'::jsonb)) as n_tools,
            s.summary->'ferramentas_usadas' as tools
        FROM agent_sessions s
        WHERE s.message_count >= :threshold_msgs
        AND s.summary IS NOT NULL
        AND jsonb_array_length(COALESCE(s.summary->'ferramentas_usadas', '[]'::jsonb)) <= :threshold_tools
        AND s.created_at >= NOW() - INTERVAL ':meses months'
        ORDER BY s.message_count DESC
        LIMIT 20
    """.replace(':meses', str(int(meses))), {
        'threshold_msgs': threshold_msgs,
        'threshold_tools': threshold_tools,
    })


def correcoes_e_memorias():
    """Correções criadas e memórias mais corrigidas."""
    correcoes = _query("""
        SELECT id, path, LEFT(content, 200) as preview, created_at
        FROM agent_memories
        WHERE path LIKE '/memories/corrections/%'
        ORDER BY created_at DESC
    """)

    top_corrigidas = _query("""
        SELECT id, user_id, path, correction_count, usage_count, effective_count,
               importance_score, category
        FROM agent_memories
        WHERE correction_count > 0
        ORDER BY correction_count DESC
        LIMIT 10
    """)

    resolves_to = _query("""
        SELECT
            src.entity_name as termo_ambiguo,
            tgt.entity_name as resolucao,
            r.weight,
            r.created_at
        FROM agent_memory_entity_relations r
        JOIN agent_memory_entities src ON src.id = r.source_entity_id
        JOIN agent_memory_entities tgt ON tgt.id = r.target_entity_id
        WHERE r.relation_type = 'resolves_to'
        ORDER BY r.created_at DESC
        LIMIT 20
    """)

    return {
        'correcoes_admin': correcoes,
        'memorias_mais_corrigidas': top_corrigidas,
        'resolves_to': resolves_to,
        'total_correcoes': len(correcoes),
        'total_com_correction_count': len(top_corrigidas),
        'total_resolves_to': len(resolves_to),
    }


def topicos_demanda(meses=3):
    """Tópicos mais demandados — proxy para quais domínios de routing são mais usados."""
    return _query("""
        SELECT
            topic,
            COUNT(*) as frequencia
        FROM (
            SELECT jsonb_array_elements_text(summary->'topicos_abordados') as topic
            FROM agent_sessions
            WHERE summary IS NOT NULL
            AND summary->'topicos_abordados' IS NOT NULL
            AND created_at >= NOW() - INTERVAL ':meses months'
        ) sub
        GROUP BY topic
        ORDER BY frequencia DESC
        LIMIT 20
    """.replace(':meses', str(int(meses))))


def instrumentacao_status():
    """Verifica se os campos de tracking estão sendo preenchidos."""
    checks = {}

    rows = _query("SELECT COUNT(*) as n FROM agent_memories WHERE correction_count > 0")
    checks['correction_count_ativo'] = rows[0]['n'] > 0

    rows = _query("SELECT COUNT(*) as n FROM agent_memory_entity_relations WHERE relation_type = 'resolves_to'")
    checks['resolves_to_ativo'] = rows[0]['n'] > 0

    rows = _query("""
        SELECT COUNT(*) as n FROM agent_sessions
        WHERE data::text LIKE '%"feedbacks"%' AND data::text LIKE '%"negative"%'
    """)
    checks['feedback_negativo_ativo'] = rows[0]['n'] > 0

    rows = _query("SELECT COUNT(*) as n FROM agent_memories WHERE effective_count > 0")
    checks['effective_count_ativo'] = rows[0]['n'] > 0

    rows = _query("SELECT COUNT(*) as n FROM agent_memories WHERE usage_count > 0")
    checks['usage_count_ativo'] = rows[0]['n'] > 0

    return checks


def gerar_relatorio(meses=3):
    """Gera relatório completo de saúde do roteamento."""
    report = {
        'gerado_em': datetime.now(timezone.utc).isoformat(),
        'periodo_meses': meses,
        'baseline_mensal': baseline_mensal(meses),
        'distribuicao_skills': distribuicao_skills(meses),
        'taxa_ambiguidade': taxa_ambiguidade(meses),
        'sessoes_struggling': sessoes_struggling(meses),
        'correcoes': correcoes_e_memorias(),
        'topicos_demanda': topicos_demanda(meses),
        'instrumentacao': instrumentacao_status(),
    }

    # Calcular health score simples
    instrumentacao = report['instrumentacao']
    campos_ativos = sum(1 for v in instrumentacao.values() if v)
    campos_total = len(instrumentacao)

    ambiguidade = report['taxa_ambiguidade']
    taxa_askuser_media = (
        sum(r['taxa_askuser_pct'] for r in ambiguidade) / len(ambiguidade)
        if ambiguidade else 0
    )

    n_struggling = len(report['sessoes_struggling'])

    report['health_score'] = {
        'instrumentacao_pct': round(100 * campos_ativos / campos_total, 0),
        'campos_ativos': campos_ativos,
        'campos_total': campos_total,
        'taxa_askuser_media_pct': taxa_askuser_media,
        'sessoes_struggling': n_struggling,
        'total_correcoes_admin': report['correcoes']['total_correcoes'],
        'nota': _calcular_nota(campos_ativos, campos_total, taxa_askuser_media, n_struggling),
    }

    return report


def _calcular_nota(campos_ativos, campos_total, taxa_askuser, n_struggling):
    """Nota simplificada de 0-100 para saúde do routing."""
    # Instrumentação: 40 pontos (campo ativo = 8 pts cada)
    score_inst = min(40, (campos_ativos / campos_total) * 40)

    # AskUser baixo = bom (< 5% = 30pts, < 15% = 20pts, < 30% = 10pts)
    if taxa_askuser < 5:
        score_amb = 30
    elif taxa_askuser < 15:
        score_amb = 20
    elif taxa_askuser < 30:
        score_amb = 10
    else:
        score_amb = 0

    # Struggling baixo = bom (0 = 30pts, <3 = 20pts, <10 = 10pts)
    if n_struggling == 0:
        score_str = 30
    elif n_struggling < 3:
        score_str = 20
    elif n_struggling < 10:
        score_str = 10
    else:
        score_str = 0

    return round(score_inst + score_amb + score_str)


def imprimir_relatorio(report):
    """Imprime relatório formatado no terminal."""
    print("=" * 70)
    print("  EVAL DE ROTEAMENTO — Relatório de Saúde")
    print(f"  Gerado: {report['gerado_em'][:19]}  |  Período: {report['periodo_meses']} meses")
    print("=" * 70)

    hs = report['health_score']
    print(f"\n  NOTA: {hs['nota']}/100")
    print(f"  Instrumentação: {hs['instrumentacao_pct']}% ({hs['campos_ativos']}/{hs['campos_total']} campos ativos)")
    print(f"  Taxa AskUser média: {hs['taxa_askuser_media_pct']:.1f}%")
    print(f"  Sessões struggling: {hs['sessoes_struggling']}")
    print(f"  Correções admin: {hs['total_correcoes_admin']}")

    # Instrumentação
    print("\n--- INSTRUMENTAÇÃO ---")
    for campo, ativo in report['instrumentacao'].items():
        status = "OK" if ativo else "MORTO"
        print(f"  {'[OK]' if ativo else '[!!]'} {campo}: {status}")

    # Baseline mensal
    print("\n--- BASELINE MENSAL ---")
    print(f"  {'Mês':<10} {'Sessões':>8} {'Sumários':>9} {'Usuários':>9} {'Avg Msgs':>9}")
    for r in report['baseline_mensal']:
        print(f"  {r['mes']:<10} {r['sessoes']:>8} {r['com_summary']:>9} {r['usuarios_unicos']:>9} {r['avg_msgs']:>9}")

    # Taxa de ambiguidade
    print("\n--- TAXA DE AMBIGUIDADE ---")
    print(f"  {'Mês':<10} {'Total':>8} {'AskUser':>8} {'%AskUser':>9} {'Skill':>8} {'%Skill':>9}")
    for r in report['taxa_ambiguidade']:
        print(f"  {r['mes']:<10} {r['total_sessoes']:>8} {r['sessoes_com_askuser']:>8} {r['taxa_askuser_pct']:>8.1f}% {r['sessoes_com_skill']:>8} {r['taxa_skill_pct']:>8.1f}%")

    # Top skills
    print("\n--- TOP 15 SKILLS/TOOLS ---")
    for r in report['distribuicao_skills'][:15]:
        bar = "#" * min(40, r['vezes_usado'])
        print(f"  {r['tool_name']:<40} {r['vezes_usado']:>4}x  {bar}")

    # Top tópicos
    print("\n--- TOP 15 TÓPICOS ---")
    for r in report['topicos_demanda'][:15]:
        bar = "#" * min(40, r['frequencia'])
        print(f"  {r['topic']:<30} {r['frequencia']:>4}x  {bar}")

    # Struggling
    if report['sessoes_struggling']:
        print(f"\n--- SESSÕES STRUGGLING ({len(report['sessoes_struggling'])}) ---")
        for r in report['sessoes_struggling']:
            print(f"  [{r['data']}] user={r['user_id']} msgs={r['message_count']} tools={r['n_tools']}")
            print(f"    {r['primeira_msg']}")
    else:
        print("\n--- SESSÕES STRUGGLING: nenhuma ---")

    # Correções
    if report['correcoes']['correcoes_admin']:
        print(f"\n--- CORREÇÕES ADMIN ({report['correcoes']['total_correcoes']}) ---")
        for r in report['correcoes']['correcoes_admin']:
            print(f"  [{str(r['created_at'])[:10]}] {r['path']}")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description='Eval de Roteamento — Métricas zero-cost')
    parser.add_argument('--json', action='store_true', help='Output em JSON')
    parser.add_argument('--meses', type=int, default=3, help='Período em meses (default: 3)')
    parser.add_argument('--salvar', type=str, help='Salvar JSON em arquivo')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        report = gerar_relatorio(args.meses)

        if args.json:
            # Converter datetimes para string
            print(json.dumps(report, indent=2, default=str, ensure_ascii=False))
        else:
            imprimir_relatorio(report)

        if args.salvar:
            with open(args.salvar, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str, ensure_ascii=False)
            print(f"\nRelatório salvo em: {args.salvar}")


if __name__ == '__main__':
    main()
