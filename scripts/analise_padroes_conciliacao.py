# -*- coding: utf-8 -*-
"""
Analise de Padroes de Conciliacao CarVia
=========================================

Script standalone para analisar as conciliacoes existentes e calibrar
thresholds do motor de sugestao.

Executar:
    source .venv/bin/activate
    python scripts/analise_padroes_conciliacao.py

Resultados da analise (2026-04-03, 71 registros):
    - razao_social SEMPRE null -> usar descricao/memo para name matching
    - ~50% matches 1:1 (valor exato), ~30% split (1 linha -> N docs)
    - Nomes: match bom p/ pagador direto, falha p/ terceiros (securitizadoras)
    - Datas: 0-32 dias, +-7d ~40%, +-15d ~60%, +-30d ~85%

Thresholds calibrados:
    VALOR: peso 0.50, exato=1.0, <1%=0.95, <5%=0.80, <15%=0.50
    DATA:  peso 0.30, <=3d=1.0, <=7d=0.80, <=15d=0.60, <=30d=0.40
    NOME:  peso 0.20, jaccard tokens normalizados
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from app import create_app, db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        sql = text("""
            SELECT
                c.id as conc_id,
                c.tipo_documento,
                el.razao_social as extrato_razao,
                el.descricao as extrato_desc,
                ABS(el.valor) as extrato_valor_abs,
                c.valor_alocado,
                el.data as extrato_data,
                CASE c.tipo_documento
                    WHEN 'fatura_cliente' THEN fc.valor_total
                    WHEN 'despesa' THEN d.valor
                    WHEN 'receita' THEN r.valor
                    WHEN 'fatura_transportadora' THEN ft.valor_total
                END as doc_valor,
                CASE c.tipo_documento
                    WHEN 'fatura_cliente' THEN fc.nome_cliente
                    WHEN 'despesa' THEN d.tipo_despesa
                    WHEN 'receita' THEN r.tipo_receita
                    WHEN 'fatura_transportadora' THEN ''
                END as doc_nome,
                CASE c.tipo_documento
                    WHEN 'fatura_cliente' THEN fc.vencimento
                    WHEN 'despesa' THEN d.data_vencimento
                    WHEN 'receita' THEN r.data_vencimento
                    WHEN 'fatura_transportadora' THEN ft.vencimento
                END as doc_vencimento
            FROM carvia_conciliacoes c
            JOIN carvia_extrato_linhas el ON c.extrato_linha_id = el.id
            LEFT JOIN carvia_faturas_cliente fc
                ON c.tipo_documento = 'fatura_cliente' AND c.documento_id = fc.id
            LEFT JOIN carvia_despesas d
                ON c.tipo_documento = 'despesa' AND c.documento_id = d.id
            LEFT JOIN carvia_receitas r
                ON c.tipo_documento = 'receita' AND c.documento_id = r.id
            LEFT JOIN carvia_faturas_transportadora ft
                ON c.tipo_documento = 'fatura_transportadora' AND c.documento_id = ft.id
            ORDER BY c.id
        """)

        rows = db.session.execute(sql).mappings().all()
        print(f"\nTotal conciliacoes: {len(rows)}")

        # Distribuicao por tipo
        tipos = {}
        for r in rows:
            t = r['tipo_documento']
            tipos[t] = tipos.get(t, 0) + 1
        print("\nDistribuicao por tipo:")
        for t, n in sorted(tipos.items(), key=lambda x: -x[1]):
            print(f"  {t}: {n}")

        # razao_social preenchida?
        com_razao = sum(1 for r in rows if r['extrato_razao'])
        print(f"\nrazao_social preenchida: {com_razao}/{len(rows)}")

        # Analise valor: alocado vs doc_valor (1:1 proxy)
        diffs_valor = []
        diffs_dias = []
        for r in rows:
            doc_v = float(r['doc_valor'] or 0)
            ext_v = float(r['extrato_valor_abs'] or 0)
            if ext_v > 0 and doc_v > 0:
                diff = abs(ext_v - doc_v) / max(ext_v, doc_v)
                diffs_valor.append(diff)

            if r['extrato_data'] and r['doc_vencimento']:
                dias = abs((r['extrato_data'] - r['doc_vencimento']).days)
                diffs_dias.append(dias)

        diffs_valor.sort()
        diffs_dias.sort()

        def percentis(arr, label):
            if not arr:
                print(f"\n{label}: sem dados")
                return
            n = len(arr)
            print(f"\n{label} (n={n}):")
            for p in [25, 50, 75, 90, 95]:
                idx = min(int(n * p / 100), n - 1)
                print(f"  p{p}: {arr[idx]:.4f}" if isinstance(arr[0], float) else f"  p{p}: {arr[idx]}")

        percentis(diffs_valor, "VALOR diff_pct (extrato vs doc)")
        percentis(diffs_dias, "DATA dias_diferenca (extrato vs vencimento)")


if __name__ == '__main__':
    main()
