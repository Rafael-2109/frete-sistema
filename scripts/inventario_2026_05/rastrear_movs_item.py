"""Rastreia movimentacoes (stock.move.line) de UM produto no Odoo desde uma data.

Mostra cronologia completa (todos os states: done/cancel/draft/etc.) por filial,
com origem -> destino, lote, picking, usuario. Tambem mostra o estoque ATUAL
(stock.quant internal) do item por filial/lote/location.

Fonte: Odoo XML-RPC (CIEL IT). Read-only.

Uso:
    python rastrear_movs_item.py --cod 205130298 [--data-inicio 2026-05-15]
"""
import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from scripts.inventario_2026_05.monitor._comum import (  # noqa: E402
    COMPANIES, COMPANY_NAME, ODOO_BATCH_SIZE,
    norm_cod, m2o_id, m2o_name,
)


def abrev_loc(name):
    """Encurta nome de location para leitura (mantem filial/ + ultimo segmento)."""
    if not name:
        return '?'
    return name


def resolver_produtos(odoo, cod):
    """Retorna lista de product.product ids com default_code == cod (+ nomes)."""
    pids = odoo.search('product.product', [('default_code', '=', cod)])
    if not pids:
        # fallback: as vezes o default_code esta so no template
        tids = odoo.search('product.template', [('default_code', '=', cod)])
        if tids:
            pids = odoo.search('product.product', [('product_tmpl_id', 'in', tids)])
    nomes = {}
    if pids:
        for p in odoo.read('product.product', pids, ['display_name', 'default_code']):
            nomes[p['id']] = (p.get('display_name') or '', p.get('default_code') or '')
    return pids, nomes


def baixar_movs(odoo, product_ids, data_inicio):
    domain = [('product_id', 'in', product_ids),
              ('date', '>=', data_inicio),
              ('company_id', 'in', COMPANIES)]
    mids = odoo.search('stock.move.line', domain)
    print(f'  {len(mids)} stock.move.line (todos os states) desde {data_inicio}')
    if not mids:
        return pd.DataFrame()
    fields = ['id', 'date', 'company_id', 'product_id', 'qty_done',
              'lot_id', 'location_id', 'location_dest_id', 'picking_id',
              'reference', 'origin', 'create_uid', 'state']
    rows = []
    for i in range(0, len(mids), ODOO_BATCH_SIZE):
        rows.extend(odoo.read('stock.move.line', mids[i:i + ODOO_BATCH_SIZE], fields))
    df = pd.DataFrame(rows)
    df['filial'] = df['company_id'].apply(m2o_id).map(COMPANY_NAME).fillna('?')
    df['lote'] = df['lot_id'].apply(m2o_name)
    df['src'] = df['location_id'].apply(m2o_name)
    df['dst'] = df['location_dest_id'].apply(m2o_name)
    df['picking'] = df['picking_id'].apply(m2o_name)
    df['usuario'] = df['create_uid'].apply(m2o_name)
    df['qty'] = pd.to_numeric(df['qty_done'], errors='coerce').fillna(0)
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date').reset_index(drop=True)


def baixar_quant_atual(odoo, product_ids):
    domain = [('product_id', 'in', product_ids),
              ('location_id.usage', '=', 'internal'),
              ('company_id', 'in', COMPANIES)]
    qids = odoo.search('stock.quant', domain)
    if not qids:
        return pd.DataFrame()
    rows = odoo.read('stock.quant', qids,
                     ['company_id', 'lot_id', 'location_id', 'quantity', 'reserved_quantity'])
    df = pd.DataFrame(rows)
    df['filial'] = df['company_id'].apply(m2o_id).map(COMPANY_NAME).fillna('?')
    df['lote'] = df['lot_id'].apply(m2o_name)
    df['location'] = df['location_id'].apply(m2o_name)
    df['qtd'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
    df['reservado'] = pd.to_numeric(df['reserved_quantity'], errors='coerce').fillna(0)
    return df


def classificar_direcao(row):
    """ENTRADA/SAIDA/INTERNA/OUTRA conforme location src/dst x filial."""
    src_int = str(row['src']).startswith(row['filial'] + '/')
    dst_int = str(row['dst']).startswith(row['filial'] + '/')
    if dst_int and not src_int:
        return 'ENTRADA'
    if src_int and not dst_int:
        return 'SAIDA'
    if src_int and dst_int:
        return 'INTERNA'
    return 'OUTRA'


def exportar_excel(movs, quant, out_path):
    """Exporta movimentacoes detalhadas + estoque atual + resumo para Excel."""
    cols = ['id', 'date', 'filial', 'qty', 'direcao', 'src', 'dst', 'lote',
            'picking', 'reference', 'origin', 'usuario', 'state',
            'product_id', 'lot_id']
    det = movs.copy()
    det['product_id'] = det['product_id'].apply(m2o_id)
    det['lot_id'] = det['lot_id'].apply(m2o_id)
    det = det[[c for c in cols if c in det.columns]]
    with pd.ExcelWriter(out_path, engine='openpyxl') as xw:
        det.to_excel(xw, sheet_name='Movimentacoes', index=False)
        if not quant.empty:
            qg = quant.groupby(['filial', 'location', 'lote'], as_index=False).agg(
                qtd=('qtd', 'sum'), reservado=('reservado', 'sum'))
            qg.to_excel(xw, sheet_name='Estoque_Atual', index=False)
        d = movs[movs['state'] == 'done']
        if not d.empty:
            res = d.groupby(['filial', 'direcao'], as_index=False).agg(
                n=('id', 'count'), qty_total=('qty', 'sum'))
            res.to_excel(xw, sheet_name='Resumo_done', index=False)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cod', required=True, help='default_code do produto')
    ap.add_argument('--data-inicio', default='2026-05-15 00:00:00')
    ap.add_argument('--lote', default=None, help='Filtra por nome exato do lote (client-side)')
    ap.add_argument('--excel', action='store_true', help='Exporta Excel detalhado')
    args = ap.parse_args()
    cod = norm_cod(args.cod)
    data_inicio = args.data_inicio if len(args.data_inicio) > 10 else args.data_inicio + ' 00:00:00'

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.odoo.utils.connection import get_odoo_connection
        odoo = get_odoo_connection()

        pids, nomes = resolver_produtos(odoo, cod)
        print(f'\n=== Produto cod={cod} ===')
        if not pids:
            print('  NENHUM product.product encontrado com esse default_code.')
            return
        for pid in pids:
            nome, dc = nomes.get(pid, ('', ''))
            print(f'  product_id={pid} | default_code={dc} | {nome}')

        movs = baixar_movs(odoo, pids, data_inicio)
        quant = baixar_quant_atual(odoo, pids)

    # Filtro opcional por lote (client-side: evita bug do operador '=' no stock.lot)
    if args.lote:
        lote_alvo = str(args.lote).strip()
        lotes_disp = sorted(set(
            list(movs['lote'].dropna().astype(str)) if not movs.empty else []
        ) | set(
            list(quant['lote'].dropna().astype(str)) if not quant.empty else []
        ))
        if not movs.empty:
            movs = movs[movs['lote'].astype(str).str.strip() == lote_alvo].reset_index(drop=True)
        if not quant.empty:
            quant = quant[quant['lote'].astype(str).str.strip() == lote_alvo].reset_index(drop=True)
        print(f'  Filtro lote="{lote_alvo}": {len(movs)} movs, {len(quant)} quants')
        if movs.empty and quant.empty:
            print(f'  Lotes encontrados para o produto: {lotes_disp}')

    if not movs.empty:
        movs['direcao'] = movs.apply(classificar_direcao, axis=1)

    # === CRONOLOGIA ===
    print(f'\n=== CRONOLOGIA DE MOVIMENTACOES (cod {cod}) ===')
    if movs.empty:
        print('  Nenhuma movimentacao no periodo.')
    else:
        for _, r in movs.iterrows():
            flag = '' if r['state'] == 'done' else f"  [{r['state'].upper()}]"
            lote = f" lote={r['lote']}" if r['lote'] else ''
            pk = f" | {r['picking']}" if r['picking'] else ''
            org = f" | origin={r['origin']}" if r['origin'] else ''
            print(f"{r['date']:%d/%m %H:%M} [{r['filial']}] {r['qty']:>12,.2f}  "
                  f"{r['src']}  ->  {r['dst']}{lote}{pk}{org} | {r['usuario']}{flag}")

        # Resumo so dos done, por filial e direcao
        print('\n=== RESUMO (apenas state=done) ===')
        d = movs[movs['state'] == 'done'].copy()
        if not d.empty:
            print(d.groupby(['filial', 'direcao'], as_index=False).agg(
                n=('id', 'count'), qty_total=('qty', 'sum')
            ).to_string(index=False, float_format=lambda x: f'{x:,.2f}'))
        print(f"\n  Total move_lines: {len(movs)} | done: {len(d)} | "
              f"outros states: {len(movs) - len(d)}")

    # === ESTOQUE ATUAL ===
    print(f'\n=== ESTOQUE ATUAL no Odoo (stock.quant internal, cod {cod}) ===')
    if quant.empty:
        print('  Sem saldo interno atual.')
    else:
        qg = quant.groupby(['filial', 'location', 'lote'], as_index=False).agg(
            qtd=('qtd', 'sum'), reservado=('reservado', 'sum'))
        qg = qg[qg['qtd'].abs() > 0.001]
        print(qg.to_string(index=False, float_format=lambda x: f'{x:,.2f}'))
        print('\n  Total por filial:')
        print(quant.groupby('filial', as_index=False).agg(
            qtd=('qtd', 'sum')).to_string(index=False, float_format=lambda x: f'{x:,.2f}'))

    # === EXPORT EXCEL ===
    if args.excel and not movs.empty:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        ts = datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%Y-%m-%d_%H-%M')
        out_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..', 'docs', 'inventario-2026-05', '07-relatorios'))
        os.makedirs(out_dir, exist_ok=True)
        suf = f"_lote_{args.lote.replace('/', '-').replace(' ', '')}" if args.lote else ''
        out_path = os.path.join(out_dir, f'MOVS_{cod}{suf}_{ts}.xlsx')
        exportar_excel(movs, quant, out_path)
        print(f'\nExcel salvo: {out_path}')


if __name__ == '__main__':
    main()
