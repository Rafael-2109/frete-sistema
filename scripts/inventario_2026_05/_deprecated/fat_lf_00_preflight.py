"""fat_lf_00_preflight.py — Pre-voo do faturamento em lote LF (RELACAO FATURAMENTO LF.xlsx).

READ-ONLY. Responde 4 perguntas decisivas antes de construir/rodar o executor:

1. COLISAO: quantos AjusteEstoqueInventario ja existem (ciclo INVENTARIO_2026_05,
   company 5, acoes onda-1) e em que status/fase? -> decide isolamento por ciclo proprio.
2. FIFO SOURCE: o estoque dos produtos PERDA esta em LF/Estoque(42)? O dos
   INDUSTRIALIZACAO esta em FB/Indisponivel? -> decide se FIFO do executor acha o saldo.
3. TIPO-6: qual e o unico produto tipo-6 (cod comeca com 6)? -> decide mapeamento.
4. G035: quantos dos produtos do Excel tem barcode invalido (cstat=225)? -> dimensiona limpeza.

Uso: python scripts/inventario_2026_05/fat_lf_00_preflight.py
"""
import os
import sys
import warnings

warnings.simplefilter('ignore')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pandas as pd  # noqa: E402
from collections import defaultdict  # noqa: E402

from app import create_app, db  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402
from app.odoo.utils.gtin_validator import find_invalid_barcodes  # noqa: E402

XLSX = '/mnt/c/Users/rafael.nascimento/Downloads/RELACAO FATURAMENTO LF.xlsx'
CICLO = 'INVENTARIO_2026_05'
ONDA1_ACOES = ['PERDA_LF_FB', 'INDUSTRIALIZACAO_FB_LF',
               'DEV_LF_FB', 'DEV_FB_LF', 'DEV_CD_LF', 'DEV_LF_CD',
               'RENOMEAR_LOTE', 'TRANSFERIR_LOTE']


def main():
    df = pd.read_excel(XLSX)
    df['cod'] = df['cod'].astype(str).str.strip()
    df['tipo'] = df['cod'].str[0]

    app = create_app()
    with app.app_context():
        print('=' * 78)
        print('  DB configurado:', str(db.engine.url).split('@')[-1])
        print('=' * 78)

        # ---- 1. COLISAO ----
        from app.odoo.models.ajuste_estoque_inventario import AjusteEstoqueInventario
        print('\n### 1. COLISAO — AjusteEstoqueInventario ciclo=%s company_id=5 ###' % CICLO)
        q = (AjusteEstoqueInventario.query
             .filter_by(ciclo=CICLO, company_id=5)
             .filter(AjusteEstoqueInventario.acao_decidida.in_(ONDA1_ACOES)))
        total = q.count()
        print(f'  TOTAL onda-1 LF existentes: {total}')
        if total:
            from sqlalchemy import func
            rows = (db.session.query(
                        AjusteEstoqueInventario.status,
                        AjusteEstoqueInventario.fase_pipeline,
                        func.count(AjusteEstoqueInventario.id))
                    .filter_by(ciclo=CICLO, company_id=5)
                    .filter(AjusteEstoqueInventario.acao_decidida.in_(ONDA1_ACOES))
                    .group_by(AjusteEstoqueInventario.status,
                              AjusteEstoqueInventario.fase_pipeline)
                    .all())
            for st, fase, n in sorted(rows, key=lambda r: (r[0] or '', r[1] or '')):
                print(f'    status={st!r:14} fase={fase!r:20} -> {n}')
        # Meu ciclo ja existe?
        meu = AjusteEstoqueInventario.query.filter_by(ciclo='FATURAMENTO_LF_2026_05_20').count()
        print(f'  Meu ciclo FATURAMENTO_LF_2026_05_20 ja tem: {meu} registros')

        odoo = get_odoo_connection()

        # ---- 3. TIPO-6 ----
        print('\n### 3. TIPO-6 (cod comeca com 6) ###')
        t6 = df[df.tipo == '6'][['cod', 'nome_produto', 'TIPO FATURAMENTO', 'QTD']]
        print(t6.to_string())

        # ---- 2. FIFO SOURCE (amostra) ----
        print('\n### 2. FIFO SOURCE — onde esta o estoque (amostra) ###')
        loc_cache = {}

        def loc_name(lid):
            if lid not in loc_cache:
                r = odoo.read('stock.location', [lid], ['complete_name'])
                loc_cache[lid] = r[0]['complete_name'] if r else f'loc{lid}'
            return loc_cache[lid]

        def amostra(label, sub, n):
            print(f'\n  --- {label} ---')
            for cod in sub['cod'].drop_duplicates().head(n):
                prods = odoo.search_read('product.product',
                                         [['default_code', '=', cod]],
                                         ['id', 'standard_price'], limit=1)
                if not prods:
                    print(f'    {cod}: SEM product_id no Odoo')
                    continue
                pid = prods[0]['id']
                quants = odoo.search_read(
                    'stock.quant',
                    [['product_id', '=', pid], ['company_id', 'in', [1, 4, 5]],
                     ['quantity', '!=', 0]],
                    ['company_id', 'location_id', 'lot_id', 'quantity', 'reserved_quantity'])
                exc = float(df[df.cod == cod]['QTD'].sum())
                if not quants:
                    print(f'    {cod} (excel QTD~{exc:.0f}): SEM quants !=0')
                    continue
                parts = []
                for qq in quants:
                    cid = qq['company_id'][0] if qq.get('company_id') else '?'
                    ln = loc_name(qq['location_id'][0]) if qq.get('location_id') else '?'
                    lot = qq['lot_id'][1] if qq.get('lot_id') else '(sem)'
                    parts.append(f'c{cid}/{ln}/{lot}={qq["quantity"]:.0f}(r{qq.get("reserved_quantity") or 0:.0f})')
                print(f'    {cod} (excel~{exc:.0f}): ' + ' | '.join(parts))

        ind = df[df['TIPO FATURAMENTO'] == 'INDUSTRIALIZAÇÃO']
        per = df[df['TIPO FATURAMENTO'] == 'PERDA']
        amostra('INDUSTRIALIZACAO (espera FB/Indisponivel)', ind, 5)
        amostra('PERDA tipo1 (espera LF)', per[per.tipo == '1'], 4)
        amostra('PERDA tipo2 (espera LF)', per[per.tipo == '2'], 4)
        amostra('PERDA tipo3 (espera LF)', per[per.tipo == '3'], 3)
        amostra('PERDA tipo4 (espera LF)', per[per.tipo == '4'], 5)
        amostra('PERDA tipo6', per[per.tipo == '6'], 1)

        # ---- 4. G035 barcode invalido ----
        print('\n### 4. G035 — barcodes invalidos (cstat=225) entre os cods do Excel ###')
        cods_all = sorted(df['cod'].unique().tolist())
        invalids = find_invalid_barcodes(odoo, cods_produto=cods_all)
        print(f'  {len(invalids)} produtos com barcode invalido (de {len(cods_all)} distintos)')
        for p in invalids[:15]:
            print(f'    id={p["id"]} cod={p["default_code"]} barcode={p["barcode"]!r}')
        if len(invalids) > 15:
            print(f'    ... +{len(invalids) - 15}')


if __name__ == '__main__':
    main()
