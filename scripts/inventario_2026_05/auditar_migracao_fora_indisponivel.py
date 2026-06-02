# etapa: audit
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""Auditoria: quants com lote MIGRAÇÃO/MIGRACAO que NAO estao em {emp}/Indisponivel.

Lista todos os stock.quant cujo lot_id.name contem MIGRACAO/MIGRAÇÃO (variantes
em LOTES_MIGRACAO de monitor/_comum.py) e que NAO estao em locais
[31088, 31089, 31090, 31091] = {FB/SC/CD/LF}/Indisponivel (D011).

Output:
  - Linhas detalhadas: filial, location_name, lote, cod, produto, qtd, valor
  - Resumo por (filial, location_name): n_quants, qtd_total, valor_total

Read-only (NAO modifica nada no Odoo). Usar para validar a aplicacao da D011:
  - Antes: muitos quants em {emp}/Estoque com lote MIGRACAO (legado D005)
  - Apos: deveriam estar em {emp}/Indisponivel (D011)

Uso:
  python scripts/inventario_2026_05/auditar_migracao_fora_indisponivel.py
  python scripts/inventario_2026_05/auditar_migracao_fora_indisponivel.py --csv /tmp/migracao_fora.csv
"""
import argparse
import sys
import time
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))
# Reusa helpers do monitor (ja maduro)
sys.path.insert(0, str(_THIS.parent / 'monitor'))

import pandas as pd  # noqa: E402

from _comum import (  # type: ignore  # noqa: E402
    LOTES_MIGRACAO, ODOO_BATCH_SIZE,
    m2o_id, m2o_name, norm_cod, norm_lote,
)

from app.odoo.constants.locations import LOCAIS_INDISPONIVEL  # noqa: E402  # type: ignore

# IDs fixos D011 — LOCAIS_INDISPONIVEL importado de app.odoo.constants.locations
LOCAIS_INDISPONIVEL_IDS = list(LOCAIS_INDISPONIVEL.values())

COMPANY_NAME = {1: 'FB', 3: 'SC', 4: 'CD', 5: 'LF'}


def buscar_lotes_migracao(odoo):
    """Busca stock.lot cujo nome bate com LOTES_MIGRACAO. Retorna dict {lot_id: (name, company_id)}."""
    print(f'Buscando stock.lot com nome em {LOTES_MIGRACAO}...')
    lot_ids = odoo.search('stock.lot', [('name', 'in', list(LOTES_MIGRACAO))])
    print(f'  {len(lot_ids)} lotes encontrados')
    if not lot_ids:
        return {}
    data = odoo.read('stock.lot', lot_ids, ['id', 'name', 'company_id'])
    out = {}
    for r in data:
        out[r['id']] = (r['name'], m2o_id(r.get('company_id')))
    return out


def buscar_quants_fora_indisponivel(odoo, lot_ids):
    """Busca stock.quant com lot_id em lot_ids e location fora dos Indisponivel."""
    if not lot_ids:
        return []
    domain = [
        ('lot_id', 'in', lot_ids),
        ('location_id', 'not in', LOCAIS_INDISPONIVEL_IDS),
        ('location_id.usage', '=', 'internal'),
    ]
    print(f'Buscando stock.quant fora de {LOCAIS_INDISPONIVEL_IDS} (location internal)...')
    qids = odoo.search('stock.quant', domain)
    print(f'  {len(qids)} quants encontrados')
    if not qids:
        return []

    fields = ['id', 'company_id', 'product_id', 'lot_id',
              'location_id', 'quantity', 'reserved_quantity', 'value']
    rows = []
    t0 = time.time()
    for i in range(0, len(qids), ODOO_BATCH_SIZE):
        batch = qids[i:i + ODOO_BATCH_SIZE]
        data = odoo.read('stock.quant', batch, fields)
        rows.extend(data)
        print(f'  {i + len(batch)}/{len(qids)} ({time.time() - t0:.0f}s)', end='\r')
    print()
    return rows


def enriquecer(rows, odoo):
    """Constroi DataFrame com nomes/codigos resolvidos."""
    if not rows:
        return pd.DataFrame()
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
    df['reservado'] = pd.to_numeric(df['reserved_quantity'], errors='coerce').fillna(0)
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
    return df


def imprimir_relatorio(df, csv_path=None):
    if df.empty:
        print('\nNADA encontrado. Todos os quants do lote MIGRACAO ja estao em {emp}/Indisponivel.')
        return

    # Excluir quants com qtd zero (D011 nao se aplica a vestigios sem saldo)
    df_nz = df[df['qtd'].abs() > 1e-6].copy()
    if df_nz.empty:
        print(f'\n{len(df)} quants com lote MIGRACAO fora de Indisponivel — TODOS com qtd=0.')
        print('Nenhum saldo efetivo precisa ser movido.')
        return

    print(f'\n=== {len(df_nz)} quants com saldo nao-zero (MIGRACAO fora de Indisponivel) ===')

    # Resumo por (filial, location_name)
    resumo = df_nz.groupby(['filial', 'location_name'], as_index=False).agg(
        n_quants=('id', 'count'),
        n_produtos=('product_id_n', 'nunique'),
        qtd_total=('qtd', 'sum'),
        reservado_total=('reservado', 'sum'),
        valor_total=('valor', 'sum'),
    ).sort_values(['filial', 'qtd_total'], ascending=[True, False])
    print('\n--- Resumo por (filial, location) ---')
    print(resumo.to_string(index=False, float_format=lambda x: f'{x:>12,.2f}'))

    # Resumo por filial
    print('\n--- Resumo por filial ---')
    por_filial = df_nz.groupby('filial', as_index=False).agg(
        n_quants=('id', 'count'),
        n_produtos=('product_id_n', 'nunique'),
        qtd_total=('qtd', 'sum'),
        valor_total=('valor', 'sum'),
    )
    print(por_filial.to_string(index=False, float_format=lambda x: f'{x:>14,.2f}'))

    # Top 30 por valor
    print('\n--- Top 30 quants por valor (saldo nao-zero) ---')
    top = df_nz.sort_values('valor', ascending=False).head(30)[
        ['filial', 'location_name', 'cod', 'product_name', 'lote', 'qtd', 'reservado', 'valor']
    ]
    print(top.to_string(index=False, float_format=lambda x: f'{x:>12,.2f}'))

    if csv_path:
        cols = ['filial', 'company_id_n', 'location_id_n', 'location_name',
                'cod', 'product_id_n', 'product_name', 'lote', 'lot_id_n',
                'qtd', 'reservado', 'valor', 'id']
        # Exporta TUDO (incluindo qtd=0) para o CSV ter histórico completo
        df[cols].sort_values(['filial', 'location_name', 'cod']).to_csv(csv_path, index=False)
        print(f'\nCSV completo (com qtd=0) salvo em {csv_path}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--csv', default=None, help='Caminho para salvar CSV detalhado')
    args = ap.parse_args()

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.odoo.utils.connection import get_odoo_connection
        odoo = get_odoo_connection()

        lotes = buscar_lotes_migracao(odoo)
        if not lotes:
            print('Nenhum lote MIGRACAO encontrado no Odoo.')
            return

        # Resumo dos lotes
        print('\n--- Lotes MIGRACAO encontrados ---')
        for lid, (name, cid) in sorted(lotes.items(), key=lambda x: (x[1][1] or 0, x[0])):
            filial = COMPANY_NAME.get(cid, f'cid={cid}')
            print(f'  id={lid:>6} | {filial:>3} | name={name!r}')

        rows = buscar_quants_fora_indisponivel(odoo, list(lotes.keys()))
        df = enriquecer(rows, odoo)

    imprimir_relatorio(df, args.csv)


if __name__ == '__main__':
    main()
