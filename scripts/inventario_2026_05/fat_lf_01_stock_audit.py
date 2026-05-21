"""fat_lf_01_stock_audit.py — Auditoria de viabilidade do faturamento LF.

READ-ONLY. Para CADA produto do Excel, compara o estoque REAL (locations
INTERNAL, exclui virtual=inventory/production/transit) com a QTD pedida:

- INDUSTRIALIZACAO (FB->LF): executor puxa de FB/Estoque(8). Stock real FB suficiente?
- PERDA/DEV (LF->FB): executor puxa de LF/Estoque(42). Stock real LF suficiente?
                       Tambem reporta total LF internal (Estoque+Pre+Pos Producao).

Escreve resumo LIMPO em /tmp/stock_audit_summary.txt (evita ruido de log do app).

Uso: python scripts/inventario_2026_05/fat_lf_01_stock_audit.py
"""
import os
import sys
import warnings

warnings.simplefilter('ignore')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pandas as pd  # noqa: E402
from collections import defaultdict  # noqa: E402

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

XLSX = '/mnt/c/Users/rafael.nascimento/Downloads/RELACAO FATURAMENTO LF.xlsx'
OUT = '/tmp/stock_audit_summary.txt'
LF_ESTOQUE = 42
FB_ESTOQUE = 8


def main():
    df = pd.read_excel(XLSX)
    df['cod'] = df['cod'].astype(str).str.strip()
    df['tipo'] = df['cod'].str[0]
    # QTD pedida por (cod, tipo_faturamento)
    qtd_por_cod = df.groupby(['cod', 'TIPO FATURAMENTO'])['QTD'].sum().reset_index()

    lines = []

    def w(s=''):
        lines.append(s)

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()

        # Mapa de locations INTERNAL por company (exclui virtual)
        locs = odoo.search_read(
            'stock.location',
            [['usage', '=', 'internal'], ['company_id', 'in', [1, 5]]],
            ['id', 'complete_name', 'company_id'])
        loc_company = {l['id']: (l['company_id'][0] if l.get('company_id') else None) for l in locs}
        loc_name = {l['id']: l['complete_name'] for l in locs}
        lf_internal_ids = [lid for lid, c in loc_company.items() if c == 5]
        fb_internal_ids = [lid for lid, c in loc_company.items() if c == 1]
        w(f'LF internal locations ({len(lf_internal_ids)}): ' +
          ', '.join(f'{lid}:{loc_name[lid]}' for lid in sorted(lf_internal_ids)))
        w(f'FB internal locations ({len(fb_internal_ids)}): ' +
          ', '.join(f'{lid}:{loc_name[lid]}' for lid in sorted(fb_internal_ids)))
        w()

        # Resolver pids
        cods = sorted(df['cod'].unique().tolist())
        prod = odoo.search_read('product.product',
                                [['default_code', 'in', cods]],
                                ['id', 'default_code'])
        cod_para_pid = {p['default_code']: p['id'] for p in prod}
        pid_para_cod = {p['id']: p['default_code'] for p in prod}
        pids = list(pid_para_cod.keys())

        # Batch quants em locations internal (LF + FB) para todos os pids
        quants = odoo.search_read(
            'stock.quant',
            [['product_id', 'in', pids],
             ['location_id', 'in', lf_internal_ids + fb_internal_ids],
             ['quantity', '!=', 0]],
            ['product_id', 'location_id', 'quantity', 'reserved_quantity'])

        # Agregar por (cod, location)
        lf_estoque = defaultdict(float)   # cod -> qty livre em LF/Estoque(42)
        lf_total = defaultdict(float)     # cod -> qty livre em todas LF internal
        fb_estoque = defaultdict(float)   # cod -> qty livre em FB/Estoque(8)
        fb_total = defaultdict(float)
        lf_por_loc = defaultdict(lambda: defaultdict(float))  # cod -> {loc_name: qty}
        for q in quants:
            pid = q['product_id'][0]
            cod = pid_para_cod.get(pid)
            if not cod:
                continue
            lid = q['location_id'][0]
            livre = float(q['quantity']) - float(q.get('reserved_quantity') or 0)
            comp = loc_company.get(lid)
            if comp == 5:
                lf_total[cod] += livre
                lf_por_loc[cod][loc_name[lid]] += livre
                if lid == LF_ESTOQUE:
                    lf_estoque[cod] += livre
            elif comp == 1:
                fb_total[cod] += livre
                if lid == FB_ESTOQUE:
                    fb_estoque[cod] += livre

        # ---- INDUSTRIALIZACAO ----
        ind = qtd_por_cod[qtd_por_cod['TIPO FATURAMENTO'] == 'INDUSTRIALIZAÇÃO']
        w('=' * 70)
        w(f'INDUSTRIALIZACAO (FB->LF) — {len(ind)} produtos. Executor puxa de FB/Estoque(8).')
        w('=' * 70)
        ind_ok = ind_parcial = ind_zero = ind_sempid = 0
        ind_problemas = []
        for _, r in ind.iterrows():
            cod, q = r['cod'], float(r['QTD'])
            if cod not in cod_para_pid:
                ind_sempid += 1
                ind_problemas.append(f'  SEM_PID {cod} (QTD {q:.0f})')
                continue
            disp = fb_estoque.get(cod, 0)
            if disp >= q - 0.5:
                ind_ok += 1
            elif disp > 0:
                ind_parcial += 1
                ind_problemas.append(f'  PARCIAL {cod}: FB/Estoque={disp:.0f} < QTD={q:.0f} (fb_total={fb_total.get(cod,0):.0f})')
            else:
                ind_zero += 1
                ind_problemas.append(f'  ZERO    {cod}: FB/Estoque=0 (QTD={q:.0f}, fb_total={fb_total.get(cod,0):.0f})')
        w(f'  OK (FB/Estoque>=QTD): {ind_ok} | PARCIAL: {ind_parcial} | ZERO: {ind_zero} | SEM_PID: {ind_sempid}')
        for p in ind_problemas[:40]:
            w(p)
        w()

        # ---- PERDA/DEV ----
        per = qtd_por_cod[qtd_por_cod['TIPO FATURAMENTO'] == 'PERDA']
        w('=' * 70)
        w(f'PERDA/DEV (LF->FB) — {len(per)} produtos. Executor puxa de LF/Estoque(42).')
        w('=' * 70)
        ok42 = parc42 = okTotal_nao42 = insuf = sempid = 0
        problemas = []
        for _, r in per.iterrows():
            cod, q = r['cod'], float(r['QTD'])
            if cod not in cod_para_pid:
                sempid += 1
                problemas.append(f'  SEM_PID {cod} (QTD {q:.0f})')
                continue
            e42 = lf_estoque.get(cod, 0)
            tot = lf_total.get(cod, 0)
            if e42 >= q - 0.5:
                ok42 += 1
            elif tot >= q - 0.5:
                okTotal_nao42 += 1
                locs_str = ', '.join(f'{n}={v:.0f}' for n, v in sorted(lf_por_loc[cod].items(), key=lambda x: -x[1])[:4])
                problemas.append(f'  FORA_ESTOQUE {cod}: LF/Estoque={e42:.0f} < QTD={q:.0f} mas LF_total={tot:.0f}. [{locs_str}]')
            elif tot > 0:
                parc42 += 1
                problemas.append(f'  INSUF_PARCIAL {cod}: LF_total={tot:.0f} < QTD={q:.0f} (LF/Estoque={e42:.0f})')
            else:
                insuf += 1
                problemas.append(f'  SEM_STOCK {cod}: LF_total=0 (QTD={q:.0f})')
        w(f'  OK (LF/Estoque>=QTD): {ok42}')
        w(f'  FORA_ESTOQUE (LF_total>=QTD, mas nao em /Estoque): {okTotal_nao42}')
        w(f'  INSUF_PARCIAL (0<LF_total<QTD): {parc42}')
        w(f'  SEM_STOCK (LF_total=0): {insuf}')
        w(f'  SEM_PID: {sempid}')
        w()
        w('--- Detalhe problemas PERDA (primeiros 60) ---')
        for p in problemas[:60]:
            w(p)

    with open(OUT, 'w') as f:
        f.write('\n'.join(lines))
    print(f'Resumo escrito em {OUT} ({len(lines)} linhas)')


if __name__ == '__main__':
    main()
