# etapa: monitor
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""SCRIPT 2: Baixa movimentacoes (stock.move.line) desde DATA_INICIO_INV.

Classifica cada movimentacao em 3 categorias (sem deducao):

  RAFAEL_UID42:           create_uid == 42 (Rafael) E picking NAO esta no Render
                          -> tudo que o Rafael fez localmente (ajustes + recebimento_lf local)
  RECEBIMENTO_LF_RENDER:  picking_id presente em recebimento_lf no banco do RENDER
                          -> recebimentos LF executados pelo worker Render
  NAO_RAFAEL:             create_uid != 42 (outros usuarios Odoo)
                          -> vendas, transferencias normais, etc.

Lista do Render vem via psycopg2 + env var DATABASE_URL_RENDER. Se nao configurada,
lista vem vazia (nao deduz nada).

Output: <cache>/movimentacoes.csv
"""
import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import (
    COMPANIES, COMPANY_NAME, ODOO_BATCH_SIZE, DATA_INICIO_INV, RAFAEL_ODOO_UID,
    norm_cod, norm_lote, m2o_id, m2o_name,
    garantir_cache_dir, is_location_interna, ler_snapshot_meta,
    consultar_pickings_recebimento_lf_render,
    is_loc_ajuste, is_loc_fornecedor, is_loc_cliente, buscar_partner_ids_empresas,
)


def baixar_movimentacoes(odoo, data_inicio, pickings_render, data_fim=None):
    """Busca stock.move.line desde data_inicio (e ate data_fim) e classifica.

    data_fim (UTC 'YYYY-MM-DD HH:MM:SS'): TETO = horario do snapshot de estoque.
    Exclui movs posteriores ao snapshot, que ainda nao se refletem no quant lido —
    evita diff fantasma (mov contada no teorico mas saldo nao no snapshot).
    """
    teto = f' e <= {data_fim}' if data_fim else ''
    print(f'Buscando stock.move.line >= {data_inicio}{teto} em companies {COMPANIES}...')
    domain = [('date', '>=', data_inicio),
              ('company_id', 'in', COMPANIES),
              ('state', '=', 'done')]
    if data_fim:
        domain.append(('date', '<=', data_fim))
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
    df['create_uid_id'] = df['create_uid'].apply(m2o_id)
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
    df['nome_produto'] = df['product_id'].apply(m2o_name)

    # Classificar: prioridade Render > UID42 > outros
    def cls(row):
        pid = row['picking_id_n']
        uid = row['create_uid_id']
        if pid is not None and not pd.isna(pid) and int(pid) in pickings_render:
            return 'RECEBIMENTO_LF_RENDER'
        if uid == RAFAEL_ODOO_UID:
            return 'RAFAEL_UID42'
        return 'NAO_RAFAEL'

    df['origem_classificada'] = df.apply(cls, axis=1)

    # Marcar locations internas (uteis para script 3)
    df['src_interna'] = df['loc_src_name'].apply(is_location_interna)
    df['dst_interna'] = df['loc_dst_name'].apply(is_location_interna)

    # Classificar negocio (compra/venda/ajuste) p/ as 3 colunas do script 4
    df = classificar_negocio(odoo, df)

    return df


def classificar_negocio(odoo, df):
    """Adiciona colunas `is_intercompany` e `categoria_negocio`.

    categoria_negocio (1 por mov, prioridade ajuste > fornecedor > cliente):
      COMPRA_EXT      : ponta fornecedor + partner EXTERNO (entrada=compra; saida=devolucao)
      VENDA_EXT       : ponta cliente + partner EXTERNO (saida=venda; entrada=retorno)
      INTERCOMPANY    : ponta fornecedor/cliente mas partner = empresa do grupo (NF entre empresas)
      AJUSTE_TERCEIRO : ponta de ajuste de inventario E create_uid != 42
      AJUSTE_PROPRIO  : ponta de ajuste de inventario E create_uid == 42 (Rafael/scripts)
      OUTRO           : transferencia interna, producao, industrializacao, transito, etc.

    `is_intercompany` so e resolvido (via partner do picking) para movs de
    fornecedor/cliente — as demais ficam False.
    """
    partners_empresas = buscar_partner_ids_empresas(odoo)
    print(f'Partners de empresas (inter-company): {sorted(partners_empresas)}')

    # Flags de location por ponta (origem OU destino)
    aj = df['loc_src_name'].apply(is_loc_ajuste) | df['loc_dst_name'].apply(is_loc_ajuste)
    forn = df['loc_src_name'].apply(is_loc_fornecedor) | df['loc_dst_name'].apply(is_loc_fornecedor)
    cli = df['loc_src_name'].apply(is_loc_cliente) | df['loc_dst_name'].apply(is_loc_cliente)

    # Resolver partner (commercial) dos pickings das movs de compra/venda
    cand = df[(forn | cli) & df['picking_id_n'].notna()]
    pids = sorted({int(x) for x in cand['picking_id_n'].dropna().unique()})
    picking_inter = {}
    if pids:
        print(f'Resolvendo partner de {len(pids)} pickings (compra/venda)...')
        partner_por_picking = {}
        partner_ids = set()
        for i in range(0, len(pids), ODOO_BATCH_SIZE):
            for p in odoo.read('stock.picking', pids[i:i + ODOO_BATCH_SIZE], ['partner_id']):
                pp = p['partner_id'][0] if p.get('partner_id') else None
                partner_por_picking[p['id']] = pp
                if pp:
                    partner_ids.add(pp)
        # commercial_partner_id (resolve contatos-filho -> empresa-mae)
        comm = {}
        partner_ids = sorted(partner_ids)
        for i in range(0, len(partner_ids), ODOO_BATCH_SIZE):
            for r in odoo.read('res.partner', partner_ids[i:i + ODOO_BATCH_SIZE],
                               ['commercial_partner_id']):
                comm[r['id']] = (r['commercial_partner_id'][0]
                                 if r.get('commercial_partner_id') else r['id'])
        for pk, part in partner_por_picking.items():
            picking_inter[pk] = comm.get(part, part) in partners_empresas

    def is_inter(pk):
        if pk is None or pd.isna(pk):
            return False
        return bool(picking_inter.get(int(pk), False))

    df['is_intercompany'] = df['picking_id_n'].apply(is_inter)

    # Categoria por np.select (prioridade pela ordem: ajuste > fornecedor > cliente)
    eh_proprio = df['create_uid_id'] == RAFAEL_ODOO_UID
    inter = df['is_intercompany']
    condicoes = [
        aj & ~eh_proprio,
        aj & eh_proprio,
        forn & inter,
        forn & ~inter,
        cli & inter,
        cli & ~inter,
    ]
    escolhas = ['AJUSTE_TERCEIRO', 'AJUSTE_PROPRIO', 'INTERCOMPANY', 'COMPRA_EXT',
                'INTERCOMPANY', 'VENDA_EXT']
    df['categoria_negocio'] = np.select(condicoes, escolhas, default='OUTRO')
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache-dir', default=None)
    ap.add_argument('--data-inicio', default=DATA_INICIO_INV,
                    help=f'YYYY-MM-DD ou ISO (default: {DATA_INICIO_INV})')
    ap.add_argument('--data-fim', default=None,
                    help='Teto UTC YYYY-MM-DD HH:MM:SS (default: snapshot do script 1)')
    args = ap.parse_args()

    cache_dir = garantir_cache_dir(args.cache_dir) if args.cache_dir else garantir_cache_dir()

    # Teto = horario do snapshot de estoque (script 1). Override manual via --data-fim.
    data_fim = args.data_fim or ler_snapshot_meta(cache_dir)
    if data_fim:
        print(f'TETO de movimentacoes (snapshot de estoque, UTC): {data_fim}')
    else:
        print('AVISO: sem snapshot_meta.json — rode 1_baixar_estoques.py antes '
              '(sem teto, pode haver descasamento estoque x movs)')

    # Pickings do recebimento_lf NO RENDER (producao)
    pickings_render = consultar_pickings_recebimento_lf_render(args.data_inicio[:10])
    print(f'Pickings recebimento_lf Render: {len(pickings_render)} ({sorted(pickings_render)})')

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.odoo.utils.connection import get_odoo_connection
        odoo = get_odoo_connection()
        df = baixar_movimentacoes(odoo, args.data_inicio, pickings_render, data_fim=data_fim)

    cols_out = ['id', 'date', 'filial', 'company_id_n', 'cod', 'nome_produto',
                'product_id_n', 'lot_id_n', 'lote',
                'loc_src_id', 'loc_src_name', 'loc_dst_id', 'loc_dst_name',
                'qty_done',
                'picking_id_n', 'picking_name', 'reference', 'origin',
                'create_uid_id', 'create_uid_name', 'state',
                'origem_classificada', 'src_interna', 'dst_interna',
                'is_intercompany', 'categoria_negocio']
    cols_out = [c for c in cols_out if c in df.columns]
    out_path = os.path.join(cache_dir, 'movimentacoes.csv')
    df[cols_out].to_csv(out_path, index=False)
    print(f'\nOK. {len(df)} movs salvas em {out_path}')

    print('\n=== Por classificacao ===')
    print(df.groupby(['filial', 'origem_classificada'], as_index=False).agg(
        n=('id', 'count'), qtd_total=('qty_done', 'sum')
    ).to_string(index=False, float_format=lambda x: f'{x:>12,.2f}'))

    print('\n=== Por categoria de negocio (compra/venda/ajuste) ===')
    print(df.groupby(['filial', 'categoria_negocio'], as_index=False).agg(
        n=('id', 'count'), qtd_total=('qty_done', 'sum')
    ).to_string(index=False, float_format=lambda x: f'{x:>12,.2f}'))


if __name__ == '__main__':
    main()
