# etapa: monitor
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""SCRIPT 1: Baixa estoques ATUAIS do Odoo (stock.quant) para companies FB/CD/LF.

Output: <cache>/estoques.csv
Colunas: filial, company_id, cod, product_name, lote, lot_id, location_id,
         location_name, qtd, valor, custo_unit

Uso:
    python 1_baixar_estoques.py [--cache-dir <path>]
"""
import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import (
    COMPANIES, COMPANY_NAME, ODOO_BATCH_SIZE,
    norm_cod, norm_lote, m2o_id, m2o_name,
    garantir_cache_dir, salvar_snapshot_meta,
)


def baixar_estoques(odoo):
    """Busca stock.quant internas em [1,4,5]. Retorna DataFrame por (filial, cod, lote, location)."""
    print(f'Buscando stock.quant em companies {COMPANIES} (location internal)...')
    domain = [('company_id', 'in', COMPANIES), ('location_id.usage', '=', 'internal')]
    qids = odoo.search('stock.quant', domain)
    print(f'  {len(qids)} quants encontrados')

    rows = []
    t0 = time.time()
    fields = ['id', 'company_id', 'product_id', 'lot_id',
              'location_id', 'quantity', 'value']
    for i in range(0, len(qids), ODOO_BATCH_SIZE):
        batch = qids[i:i + ODOO_BATCH_SIZE]
        data = odoo.read('stock.quant', batch, fields)
        rows.extend(data)
        print(f'  {i + len(batch)}/{len(qids)} ({time.time() - t0:.0f}s)', end='\r')
    print()

    df = pd.DataFrame(rows)
    df['company_id_n'] = df['company_id'].apply(m2o_id)
    df['filial'] = df['company_id_n'].map(COMPANY_NAME).fillna('?')
    df['product_id_n'] = df['product_id'].apply(m2o_id)
    df['product_name'] = df['product_id'].apply(m2o_name)
    df['lot_id_n'] = df['lot_id'].apply(m2o_id)
    df['lot_name'] = df['lot_id'].apply(m2o_name)
    df['lote'] = df['lot_name'].apply(norm_lote)
    df['location_id_n'] = df['location_id'].apply(m2o_id)
    df['location_name'] = df['location_id'].apply(m2o_name)
    df['qtd'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
    df['valor'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)

    # buscar default_code dos produtos
    pids = df['product_id_n'].dropna().unique().tolist()
    print(f'Buscando default_code de {len(pids)} produtos...')
    pmap = {}
    for i in range(0, len(pids), ODOO_BATCH_SIZE):
        b = pids[i:i + ODOO_BATCH_SIZE]
        d = odoo.read('product.product', list(b), ['default_code'])
        for p in d:
            pmap[p['id']] = p.get('default_code') or ''
    df['cod'] = df['product_id_n'].map(lambda x: pmap.get(x, ''))
    df['cod'] = df['cod'].apply(norm_cod)

    # filtrar cods nao-digito (paletes sem cod, ajustes virtuais sem produto)
    df = df[df['cod'].str.isdigit()].copy()

    # agregar por (filial, cod, lote)
    out = df.groupby(['filial', 'company_id_n', 'cod', 'lote'], as_index=False).agg(
        qtd=('qtd', 'sum'),
        valor=('valor', 'sum'),
        n_quants=('id', 'count'),
        nome_produto=('product_name', 'first'),
    )
    out['custo_unit'] = np.where(out['qtd'] > 0, out['valor'] / out['qtd'], 0)
    return out


def main():
    ap = argparse.ArgumentParser(description='Baixa estoques atuais do Odoo')
    ap.add_argument('--cache-dir', default=None,
                    help='Diretorio para salvar estoques.csv (default: /tmp/inventario_monitor)')
    args = ap.parse_args()

    cache_dir = garantir_cache_dir(args.cache_dir) if args.cache_dir else garantir_cache_dir()

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.odoo.utils.connection import get_odoo_connection
        from app.utils.timezone import agora_utc
        odoo = get_odoo_connection()
        # Horario UTC do snapshot (capturado JUSTO ANTES da extracao). O script 2
        # usa como teto para descartar movs posteriores -> evita descasamento.
        snapshot_utc = agora_utc().strftime('%Y-%m-%d %H:%M:%S')
        df = baixar_estoques(odoo)

    out_path = os.path.join(cache_dir, 'estoques.csv')
    df.to_csv(out_path, index=False)
    salvar_snapshot_meta(cache_dir, snapshot_utc)
    print(f'\nOK. {len(df)} linhas salvas em {out_path}')
    print(f'Snapshot UTC (teto p/ movimentacoes): {snapshot_utc}')

    # resumo por filial
    print('\n=== Resumo ===')
    print(df.groupby('filial', as_index=False).agg(
        n=('cod', 'count'),
        qtd_total=('qtd', 'sum'),
        valor_total=('valor', 'sum')
    ).to_string(index=False, float_format=lambda x: f'{x:>14,.2f}'))


if __name__ == '__main__':
    main()
