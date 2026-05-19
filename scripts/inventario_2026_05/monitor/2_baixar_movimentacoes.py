"""SCRIPT 2: Baixa movimentacoes (stock.move.line) desde DATA_INICIO_INV.

Exclui APENAS os pickings do recebimento_lf no Render que NAO foram tambem
criados pelo pipeline INVENTARIO (overlap eh mantido como inventario).

Output: <cache>/movimentacoes.csv

Uso:
    python 2_baixar_movimentacoes.py [--cache-dir <path>] [--data-inicio YYYY-MM-DD]
"""
import argparse
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import (
    COMPANIES, COMPANY_NAME, ODOO_BATCH_SIZE, DATA_INICIO_INV,
    norm_cod, norm_lote, m2o_id, m2o_name,
    garantir_cache_dir, is_location_interna,
)


def coletar_pickings_excluir():
    """Pickings de recebimento_lf Render desde DATA_INICIO_INV (excluindo os do inventario).

    Retorna set de odoo_picking_id.
    """
    from app import create_app, db
    app = create_app()
    with app.app_context():
        rec = db.session.execute(db.text("""
            SELECT odoo_picking_id, odoo_transfer_out_picking_id, odoo_transfer_in_picking_id
            FROM recebimento_lf WHERE criado_em >= '2026-05-16'
        """)).fetchall()
        pickings_rec = set()
        for r in rec:
            for pid in r:
                if pid:
                    pickings_rec.add(int(pid))

        inv = db.session.execute(db.text("""
            SELECT DISTINCT picking_id_odoo FROM ajuste_estoque_inventario
            WHERE ciclo='INVENTARIO_2026_05' AND picking_id_odoo IS NOT NULL
        """)).scalars().all()
        pickings_inv = set(int(p) for p in inv if p)

    pickings_excluir = pickings_rec - pickings_inv  # overlap fica como inventario
    return pickings_excluir, pickings_inv


def baixar_movimentacoes(odoo, data_inicio, pickings_inv, pickings_excluir):
    """Busca stock.move.line desde data_inicio e classifica."""
    print(f'Buscando stock.move.line >= {data_inicio} em companies {COMPANIES}...')
    domain = [('date', '>=', data_inicio),
              ('company_id', 'in', COMPANIES),
              ('state', '=', 'done')]
    mids = odoo.search('stock.move.line', domain)
    print(f'  {len(mids)} move_lines encontradas')

    fields = ['id', 'date', 'company_id', 'product_id', 'qty_done',
              'lot_id', 'location_id', 'location_dest_id', 'picking_id',
              'reference', 'origin', 'create_uid', 'state']
    rows = []
    t0 = time.time()
    for i in range(0, len(mids), ODOO_BATCH_SIZE):
        batch = mids[i:i + ODOO_BATCH_SIZE]
        data = odoo.read('stock.move.line', batch, fields)
        rows.extend(data)
        print(f'  {i + len(batch)}/{len(mids)} ({time.time() - t0:.0f}s)', end='\r')
    print()
    df = pd.DataFrame(rows)

    # Normalizar
    df['company_id_n'] = df['company_id'].apply(m2o_id)
    df['filial'] = df['company_id_n'].map(COMPANY_NAME).fillna('?')
    df['product_id_n'] = df['product_id'].apply(m2o_id)
    df['lot_id_n'] = df['lot_id'].apply(m2o_id)
    df['lot_name'] = df['lot_id'].apply(m2o_name)
    df['lote'] = df['lot_name'].apply(norm_lote)
    df['loc_src_id'] = df['location_id'].apply(m2o_id)
    df['loc_src_name'] = df['location_id'].apply(m2o_name)
    df['loc_dst_id'] = df['location_dest_id'].apply(m2o_id)
    df['loc_dst_name'] = df['location_dest_id'].apply(m2o_name)
    df['picking_id_n'] = df['picking_id'].apply(m2o_id)
    df['picking_name'] = df['picking_id'].apply(m2o_name)
    df['create_uid_name'] = df['create_uid'].apply(m2o_name)
    df['qty_done'] = pd.to_numeric(df['qty_done'], errors='coerce').fillna(0)

    # cod_produto
    pids = df['product_id_n'].dropna().unique().tolist()
    pmap = {}
    print(f'Buscando default_code de {len(pids)} produtos...')
    for i in range(0, len(pids), ODOO_BATCH_SIZE):
        b = pids[i:i + ODOO_BATCH_SIZE]
        d = odoo.read('product.product', list(b), ['default_code'])
        for p in d:
            pmap[p['id']] = p.get('default_code') or ''
    df['cod'] = df['product_id_n'].map(lambda x: pmap.get(x, ''))
    df['cod'] = df['cod'].apply(norm_cod)

    # Classificar e filtrar
    def cls(pid):
        if pid is None or pd.isna(pid):
            return 'INVENTORY_ADJUST'
        pid = int(pid)
        if pid in pickings_inv:
            return 'INVENTARIO_PICKING'
        if pid in pickings_excluir:
            return 'RECEBIMENTO_LF_RENDER'
        return 'OUTROS_PICKING'

    df['origem_classificada'] = df['picking_id_n'].apply(cls)

    # Marcar locations internas (uteis para script 3)
    df['src_interna'] = df['loc_src_name'].apply(is_location_interna)
    df['dst_interna'] = df['loc_dst_name'].apply(is_location_interna)

    # Nao filtrar aqui — script 3 aplica apenas RECEBIMENTO_LF_RENDER (nao-ajuste).
    # Salva tudo com origem_classificada para auditoria.
    return df, df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache-dir', default=None)
    ap.add_argument('--data-inicio', default=DATA_INICIO_INV,
                    help=f'YYYY-MM-DD ou ISO (default: {DATA_INICIO_INV})')
    args = ap.parse_args()

    cache_dir = garantir_cache_dir(args.cache_dir) if args.cache_dir else garantir_cache_dir()

    pickings_excluir, pickings_inv = coletar_pickings_excluir()
    print(f'Pickings excluir (recebimento_lf puro): {sorted(pickings_excluir)}')
    print(f'Pickings inventario (mantem): {sorted(pickings_inv)}')

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.odoo.utils.connection import get_odoo_connection
        odoo = get_odoo_connection()
        df_incluido, df_total = baixar_movimentacoes(
            odoo, args.data_inicio, pickings_inv, pickings_excluir
        )

    cols_out = ['id', 'date', 'filial', 'company_id_n', 'cod',
                'product_id_n', 'lot_id_n', 'lote',
                'loc_src_id', 'loc_src_name', 'loc_dst_id', 'loc_dst_name',
                'qty_done',
                'picking_id_n', 'picking_name', 'reference', 'origin',
                'create_uid_name', 'state',
                'origem_classificada', 'src_interna', 'dst_interna']
    cols_out = [c for c in cols_out if c in df_incluido.columns]
    out_path = os.path.join(cache_dir, 'movimentacoes.csv')
    df_incluido[cols_out].to_csv(out_path, index=False)
    print(f'\nOK. {len(df_incluido)} movs salvas em {out_path} (todas, com classificacao)')

    print('\n=== Por classificacao ===')
    print(df_incluido.groupby(['filial', 'origem_classificada'], as_index=False).agg(
        n=('id', 'count'), qtd_total=('qty_done', 'sum')
    ).to_string(index=False, float_format=lambda x: f'{x:>12,.2f}'))


if __name__ == '__main__':
    main()
