#!/usr/bin/env python3
"""A0.7 - Meta-script: roda 1-6 e gera relatorio Markdown consolidado.

Output: docs/superpowers/reports/baseline_pre_sprint_a_YYYYMMDD.md
Tambem pode imprimir no stdout.

Uso:
  source .venv/bin/activate
  python scripts/carvia/baseline_pre_sprint_a/healthcheck_pre_a.py
  python scripts/carvia/baseline_pre_sprint_a/healthcheck_pre_a.py --stdout
  python scripts/carvia/baseline_pre_sprint_a/healthcheck_pre_a.py --out /tmp/baseline.md
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402

# Importar cada script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from count_cte_comp_orfaos import contar_cte_comp_orfaos  # noqa: E402
from count_nfs_sem_item_fatura import contar_nfs_faltantes_em_faturas  # noqa: E402
from count_cte_comp_sem_ctrc import contar_cte_comp_sem_ctrc  # noqa: E402
from count_operacoes_sem_xml import contar_operacoes_sem_xml  # noqa: E402
from count_cte_numero_duplicados import contar_duplicados  # noqa: E402
from baseline_valores_fatura import snapshot_valores_fatura  # noqa: E402


def formatar_markdown(dados):
    """Gera relatorio Markdown a partir dos dados coletados."""
    dt = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
    linhas = []
    linhas.append(f"# Baseline Pré Sprint A — CarVia")
    linhas.append(f"")
    linhas.append(f"**Gerado em**: {dt}")
    linhas.append(f"**Script**: `scripts/carvia/baseline_pre_sprint_a/healthcheck_pre_a.py`")
    linhas.append(f"**Objetivo**: medir esforço real dos itens A1-A4 antes de iniciar implementação.")
    linhas.append(f"")
    linhas.append(f"---")
    linhas.append(f"")

    # A0.1 — CTe Comp orfaos
    d = dados['cte_comp_orfaos']
    linhas.append(f"## A0.1 — CTe Comp órfãos (estima item A1)")
    linhas.append(f"")
    linhas.append(f"| Categoria | Qtd |")
    linhas.append(f"|-----------|-----|")
    linhas.append(f"| Total CTe Complementares | {d['total_cte_complementares']} |")
    linhas.append(f"| Vinculados a fatura (OK) | {d['vinculados_a_fatura']} |")
    linhas.append(f"| **Candidatos a retrolink (A1)** | **{d['candidatos_retrolink_a1']}** |")
    linhas.append(f"| Aguardando fatura chegar | {d['aguardando_fatura_chegar']} |")
    linhas.append(f"")
    linhas.append(f"**Impacto A1**: {d['candidatos_retrolink_a1']} registros precisam ser fechados via backfill.")
    linhas.append(f"")

    # A0.2 — NFs sem item
    d = dados['nfs_sem_item']
    linhas.append(f"## A0.2 — NFs sem item em fatura (estima item A2 - Bug #1)")
    linhas.append(f"")
    linhas.append(f"| Métrica | Qtd |")
    linhas.append(f"|---------|-----|")
    linhas.append(f"| Faturas ativas analisadas | {d['total_faturas_ativas_analisadas']} |")
    linhas.append(f"| **Faturas afetadas** | **{d['faturas_afetadas']}** |")
    linhas.append(f"| **Items suplementares faltando** | **{d['total_items_suplementares_faltando']}** |")
    linhas.append(f"")

    # A0.3 — CTe Comp sem CTRNC
    d = dados['cte_comp_sem_ctrc']
    linhas.append(f"## A0.3 — CTe Comp sem CTRNC (estima item A3 - Bug #3)")
    linhas.append(f"")
    linhas.append(f"| Bucket | Qtd |")
    linhas.append(f"|--------|-----|")
    linhas.append(f"| Total sem ctrc_numero | {d['total_cte_comp_sem_ctrc']} |")
    linhas.append(f"| <= 30 dias (urgente) | {d['ate_30_dias']} |")
    linhas.append(f"| 30-90 dias | {d['de_30_a_90_dias']} |")
    linhas.append(f"| > 90 dias (pode estar expurgado) | {d['mais_de_90_dias']} |")
    linhas.append(f"")
    eta = d['total_cte_comp_sem_ctrc'] * 90 // 60
    linhas.append(f"**Estimativa tempo backfill**: {eta} min (~{eta // 60}h) em 1 worker SSW.")
    linhas.append(f"")

    # A0.4 — Operacoes sem XML
    d = dados['operacoes_sem_xml']
    linhas.append(f"## A0.4 — Operações sem XML (bloqueio parcial A4.3)")
    linhas.append(f"")
    linhas.append(f"| tipo_entrada | Total | Com XML | Sem XML |")
    linhas.append(f"|--------------|-------|---------|---------|")
    for b in d['breakdown_por_tipo_entrada']:
        linhas.append(f"| {b['tipo_entrada']} | {b['total']} | {b['com_xml']} | {b['sem_xml']} |")
    linhas.append(f"")
    if d['importado_sem_xml_count'] > 0:
        linhas.append(f"**⚠ ANOMALIA**: {d['importado_sem_xml_count']} operações IMPORTADO sem XML. Investigar causa raiz.")
        linhas.append(f"")

    # A0.5 — Duplicados
    d = dados['duplicados']
    linhas.append(f"## A0.5 — Números sequenciais duplicados (bloqueia B2)")
    linhas.append(f"")
    total_dupes = sum(len(v) for v in d.values())
    if total_dupes == 0:
        linhas.append(f"✅ **OK**: 0 duplicatas. B2 UniqueConstraint pode ser aplicada direto.")
    else:
        linhas.append(f"⚠ **ATENÇÃO**: {total_dupes} grupos de duplicatas. B2 exige remediação antes.")
        for tab_col, lista in d.items():
            if lista:
                linhas.append(f"- `{tab_col}`: {len(lista)} duplicatas")
    linhas.append(f"")

    # A0.6 — Baseline valores
    d = dados['baseline_valores']
    linhas.append(f"## A0.6 — Baseline valor_total fatura")
    linhas.append(f"")
    linhas.append(f"Snapshot salvo para comparação pós Sprint A.")
    linhas.append(f"")
    linhas.append(f"| Métrica | Qtd |")
    linhas.append(f"|---------|-----|")
    linhas.append(f"| Faturas no snapshot | {d['total_faturas']} |")
    total_valor = sum(f['valor_total'] for f in d['faturas'])
    linhas.append(f"| Soma total R$ | {total_valor:,.2f} |")
    linhas.append(f"")
    linhas.append(f"Arquivo completo: `/tmp/baseline_valores_fatura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json` (salvar manualmente se desejado)")
    linhas.append(f"")

    # Sumario executivo
    linhas.append(f"---")
    linhas.append(f"")
    linhas.append(f"## Sumário Executivo")
    linhas.append(f"")
    impacto_a1 = dados['cte_comp_orfaos']['candidatos_retrolink_a1']
    impacto_a2 = dados['nfs_sem_item']['total_items_suplementares_faltando']
    impacto_a3 = dados['cte_comp_sem_ctrc']['total_cte_comp_sem_ctrc']
    impacto_a4 = dados['operacoes_sem_xml']['total_operacoes']

    linhas.append(f"| Item Sprint A | Impacto estimado |")
    linhas.append(f"|---------------|------------------|")
    linhas.append(f"| A1 (Bug #2) | {impacto_a1} CTe Comp órfãos a fechar vínculo |")
    linhas.append(f"| A2 (Bug #1) | {impacto_a2} items suplementares a criar |")
    linhas.append(f"| A3 (Bug #3) | {impacto_a3} CTe Comp sem CTRNC a buscar no SSW |")
    linhas.append(f"| A4 (Bug #4) | {impacto_a4} operações impactadas (novos imports autopopulados) |")
    linhas.append(f"")

    # Alertas
    alertas = []
    if impacto_a3 > 500:
        alertas.append(f"⚠ A3: {impacto_a3} jobs SSW — usar queue dedicada `ssw_low` e rate-limit")
    if impacto_a1 > 200:
        alertas.append(f"⚠ A1: {impacto_a1} candidatos — backfill em batches de 50")
    if total_dupes > 0:
        alertas.append(f"⚠ B2: {total_dupes} duplicatas bloqueiam UniqueConstraint — script de remediação obrigatório")
    if dados['operacoes_sem_xml']['importado_sem_xml_count'] > 0:
        alertas.append(f"⚠ A4: {dados['operacoes_sem_xml']['importado_sem_xml_count']} IMPORTADO sem XML — investigar antes de backfill")

    if alertas:
        linhas.append(f"### Alertas")
        linhas.append(f"")
        for a in alertas:
            linhas.append(f"- {a}")
        linhas.append(f"")
    else:
        linhas.append(f"### ✅ Sem alertas críticos.")
        linhas.append(f"")

    return '\n'.join(linhas)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', help='Arquivo de saida (default: docs/superpowers/reports/baseline_pre_sprint_a_YYYYMMDD.md)')
    parser.add_argument('--stdout', action='store_true', help='Imprime tambem no stdout')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        print("Coletando A0.1 - CTe Comp orfaos...", file=sys.stderr)
        d1 = contar_cte_comp_orfaos()
        print("Coletando A0.2 - NFs sem item...", file=sys.stderr)
        d2 = contar_nfs_faltantes_em_faturas()
        print("Coletando A0.3 - CTe Comp sem CTRNC...", file=sys.stderr)
        d3 = contar_cte_comp_sem_ctrc()
        print("Coletando A0.4 - Operacoes sem XML...", file=sys.stderr)
        d4 = contar_operacoes_sem_xml()
        print("Coletando A0.5 - Duplicados...", file=sys.stderr)
        d5 = contar_duplicados()
        print("Coletando A0.6 - Baseline valores fatura...", file=sys.stderr)
        d6 = snapshot_valores_fatura()

    dados = {
        'cte_comp_orfaos': d1,
        'nfs_sem_item': d2,
        'cte_comp_sem_ctrc': d3,
        'operacoes_sem_xml': d4,
        'duplicados': d5,
        'baseline_valores': d6,
    }

    md = formatar_markdown(dados)

    if args.out:
        out_path = Path(args.out)
    else:
        timestamp = datetime.now().strftime('%Y%m%d')
        out_dir = PROJECT_ROOT / 'docs' / 'superpowers' / 'reports'
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f'baseline_pre_sprint_a_{timestamp}.md'

    out_path.write_text(md, encoding='utf-8')
    print(f"Relatorio salvo em: {out_path}", file=sys.stderr)

    # JSON estruturado tambem
    json_path = out_path.with_suffix('.json')
    json_path.write_text(
        json.dumps(dados, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8',
    )
    print(f"Dados brutos em:    {json_path}", file=sys.stderr)

    if args.stdout:
        print(md)


if __name__ == '__main__':
    main()
