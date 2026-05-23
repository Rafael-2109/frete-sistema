"""RELATORIO: Apontamentos de producao (componentes + PA) + Compras recebidas.

Escopo (FIXO neste relatorio, parametrizavel via flags):
  - Empresas: FB(1), CD(4), LF(5)  (mesmo conjunto do monitor de inventario)
  - Periodo: desde DATA_INICIO_INV (2026-05-16) — override via --data-inicio
  - Compras: SOMENTE externas. Compras inter-company (fornecedor = empresa do
    grupo) sao EXCLUIDAS do relatorio (contadas no Resumo para transparencia).

Definicoes (sem deducao — ancoradas nos vinculos Odoo, nao em locations):
  APONTAMENTO  : stock.move.line state=done cujo move tem vinculo de producao:
                   - raw_material_production_id  -> COMPONENTE (consumo)
                   - production_id               -> PA (se produto == produto da MO)
                                                    ou SUBPRODUTO (demais finished)
  COMPRA RECEB.: stock.move.line state=done com location_id.usage='supplier'
                 (entrada vinda de fornecedor). Devolucao de compra (saida p/
                 fornecedor) NAO entra. Inter-company excluida via partner do picking.

Saidas (Excel em docs/inventario-2026-05/07-relatorios/):
  Aba 'Apontamentos'      : 1 linha por move.line de producao (componente/PA/subproduto)
  Aba 'Compras_Recebidas' : 1 linha por move.line de entrada de fornecedor externo
  Aba 'Resumo'            : agregados por empresa

Uso:
    python scripts/inventario_2026_05/monitor/relatorio_apontamentos_compras.py
    python scripts/inventario_2026_05/monitor/relatorio_apontamentos_compras.py \
        --data-inicio 2026-05-01 --output-name MEU_RELATORIO.xlsx
"""
import argparse
import datetime as _dt
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import (  # noqa: E402
    COMPANIES, COMPANY_NAME, ODOO_BATCH_SIZE, DATA_INICIO_INV,
    norm_cod, norm_lote, m2o_id, m2o_name,
    garantir_relatorios_dir, buscar_partner_ids_empresas,
)

TIPO_ORDEM = {'PA': 0, 'SUBPRODUTO': 1, 'COMPONENTE': 2}


def _batches(seq, n=ODOO_BATCH_SIZE):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


# ============================================================
# PRODUTOS (name limpo + default_code)
# ============================================================
def buscar_produto_info(odoo, pids):
    """pid -> (nome, cod). nome = product.product.name (sem prefixo [###])."""
    info = {}
    pids = sorted({int(p) for p in pids if p is not None and not pd.isna(p)})
    for b in _batches(pids):
        for r in odoo.read('product.product', b, ['name', 'default_code']):
            info[r['id']] = (r.get('name') or '', norm_cod(r.get('default_code') or ''))
    return info


def buscar_lote_names(odoo, lot_ids):
    nomes = {}
    lot_ids = sorted({int(x) for x in lot_ids if x is not None and not pd.isna(x)})
    for b in _batches(lot_ids):
        for r in odoo.read('stock.lot', b, ['name']):
            nomes[r['id']] = r.get('name') or ''
    return nomes


# ============================================================
# APONTAMENTOS (mrp.production: componentes + PA)
# ============================================================
def baixar_apontamentos(odoo, data_inicio):
    """move.lines de producao no periodo, classificadas em PA/SUBPRODUTO/COMPONENTE."""
    base = [['date', '>=', data_inicio], ['company_id', 'in', COMPANIES],
            ['state', '=', 'done']]
    raw_ids = odoo.search('stock.move', base + [['raw_material_production_id', '!=', False]])
    fin_ids = odoo.search('stock.move', base + [['production_id', '!=', False]])
    print(f'  moves COMPONENTE: {len(raw_ids)} | moves PA/finished: {len(fin_ids)}')

    # move_id -> base ({'COMPONENTE','FINISHED'}) e move_id -> mo_id, numa unica leitura
    move_meta = {}     # move_id -> 'COMPONENTE' | 'FINISHED'
    move_to_mo = {}    # move_id -> mrp.production id
    mo_ids = set()
    for ids, base_tag, link_field in (
        (raw_ids, 'COMPONENTE', 'raw_material_production_id'),
        (fin_ids, 'FINISHED', 'production_id'),
    ):
        for b in _batches(list(ids)):
            for m in odoo.read('stock.move', b, [link_field]):
                moid = m2o_id(m.get(link_field))
                if moid:
                    move_meta[m['id']] = base_tag
                    move_to_mo[m['id']] = moid
                    mo_ids.add(moid)

    # mrp.production headline (PA principal + qtd produzida)
    mo_info = {}
    for b in _batches(sorted(mo_ids)):
        for mo in odoo.read('mrp.production', b,
                            ['name', 'product_id', 'qty_produced', 'product_qty',
                             'state', 'date_finished']):
            mo_info[mo['id']] = {
                'name': mo.get('name') or '',
                'pa_pid': m2o_id(mo.get('product_id')),
                'qtd_prod': float(mo.get('qty_produced') or 0),
                'state': mo.get('state') or '',
                'date_finished': mo.get('date_finished') or '',
            }

    # move.lines (granularidade lote + qty_done)
    all_move_ids = list(move_to_mo.keys())
    sml = []
    for b in _batches(all_move_ids):
        ids = odoo.search('stock.move.line',
                          [['move_id', 'in', b], ['state', '=', 'done']])
        for bb in _batches(ids):
            sml.extend(odoo.read('stock.move.line', bb,
                                 ['id', 'date', 'company_id', 'product_id', 'qty_done',
                                  'lot_id', 'move_id', 'location_id', 'location_dest_id']))
    if not sml:
        return pd.DataFrame(), mo_info
    df = pd.DataFrame(sml)
    df['move_id_n'] = df['move_id'].apply(m2o_id)
    df['mo_id'] = df['move_id_n'].map(move_to_mo)
    df = df[df['mo_id'].notna()].copy()
    df['mo_id'] = df['mo_id'].astype(int)
    df['company_id_n'] = df['company_id'].apply(m2o_id)
    df['empresa'] = df['company_id_n'].map(COMPANY_NAME).fillna('?')
    df['product_id_n'] = df['product_id'].apply(m2o_id)
    df['lot_id_n'] = df['lot_id'].apply(m2o_id)
    df['origem'] = df['location_id'].apply(m2o_name)
    df['destino'] = df['location_dest_id'].apply(m2o_name)
    df['qtd'] = pd.to_numeric(df['qty_done'], errors='coerce').fillna(0)

    def tipo(row):
        moid = row['mo_id']
        base = move_meta.get(row['move_id_n'], '')
        if base == 'COMPONENTE':
            return 'COMPONENTE'
        pa_pid = mo_info.get(moid, {}).get('pa_pid')
        return 'PA' if row['product_id_n'] == pa_pid else 'SUBPRODUTO'

    df['tipo'] = df.apply(tipo, axis=1)
    df['mo'] = df['mo_id'].map(lambda x: mo_info.get(x, {}).get('name', ''))
    df['mo_qtd_produzida'] = df['mo_id'].map(lambda x: mo_info.get(x, {}).get('qtd_prod', 0))
    df['mo_pa_pid'] = df['mo_id'].map(lambda x: mo_info.get(x, {}).get('pa_pid'))
    df['mo_state'] = df['mo_id'].map(lambda x: mo_info.get(x, {}).get('state', ''))
    return df, mo_info


# ============================================================
# COMPRAS RECEBIDAS (externas — exclui inter-company)
# ============================================================
def baixar_compras(odoo, data_inicio):
    """Entradas de fornecedor EXTERNAS (exclui inter-company).

    Fornecedor resolvido pela ORDEM DE COMPRA (autoritativo):
        move.purchase_line_id -> purchase.order.line.order_id -> purchase.order.partner_id
    Fallback ao partner do picking quando o move nao tem PO. Inter-company =
    commercial_partner_id do fornecedor resolvido pertence a uma empresa do grupo.

    NOTA: usar SO o partner do picking sub-detecta inter-company — varias entradas
    inter-filiais tem picking.partner_id vazio mas PO apontando p/ empresa do grupo.
    """
    print(f'  buscando entradas de fornecedor desde {data_inicio}...')
    ids = odoo.search('stock.move.line',
                      [['date', '>=', data_inicio], ['company_id', 'in', COMPANIES],
                       ['state', '=', 'done'], ['location_id.usage', '=', 'supplier']])
    print(f'  {len(ids)} move_lines de entrada de fornecedor (antes de excluir inter-company)')
    rows = []
    for b in _batches(ids):
        rows.extend(odoo.read('stock.move.line', b,
                              ['id', 'date', 'company_id', 'product_id', 'qty_done',
                               'lot_id', 'location_id', 'location_dest_id', 'move_id',
                               'picking_id', 'reference', 'origin']))
    if not rows:
        return pd.DataFrame(), 0
    df = pd.DataFrame(rows)
    df['company_id_n'] = df['company_id'].apply(m2o_id)
    df['empresa'] = df['company_id_n'].map(COMPANY_NAME).fillna('?')
    df['product_id_n'] = df['product_id'].apply(m2o_id)
    df['lot_id_n'] = df['lot_id'].apply(m2o_id)
    df['move_id_n'] = df['move_id'].apply(m2o_id)
    df['picking_id_n'] = df['picking_id'].apply(m2o_id)
    df['picking_name'] = df['picking_id'].apply(m2o_name)
    df['destino'] = df['location_dest_id'].apply(m2o_name)
    df['qtd'] = pd.to_numeric(df['qty_done'], errors='coerce').fillna(0)

    partners_empresas = buscar_partner_ids_empresas(odoo)

    # 1) move -> purchase_line_id -> order -> (partner_id, partner_name)
    move_ids = sorted({int(x) for x in df['move_id_n'].dropna().unique()})
    mv_to_pl = {}
    for b in _batches(move_ids):
        for m in odoo.read('stock.move', b, ['purchase_line_id']):
            mv_to_pl[m['id']] = m2o_id(m.get('purchase_line_id'))
    pl_ids = sorted({v for v in mv_to_pl.values() if v})
    pl_to_order = {}
    for b in _batches(pl_ids):
        for pl in odoo.read('purchase.order.line', b, ['order_id']):
            pl_to_order[pl['id']] = m2o_id(pl.get('order_id'))
    order_ids = sorted({v for v in pl_to_order.values() if v})
    order_partner = {}
    for b in _batches(order_ids):
        for o in odoo.read('purchase.order', b, ['partner_id']):
            order_partner[o['id']] = (m2o_id(o.get('partner_id')), m2o_name(o.get('partner_id')))

    # 2) fallback: partner do picking
    pk_ids = sorted({int(x) for x in df['picking_id_n'].dropna().unique()})
    pk_partner = {}
    for b in _batches(pk_ids):
        for p in odoo.read('stock.picking', b, ['partner_id']):
            pk_partner[p['id']] = (m2o_id(p.get('partner_id')), m2o_name(p.get('partner_id')))

    # 3) commercial_partner_id de todos (contato-filho -> empresa-mae)
    all_part = ({p for (p, _) in order_partner.values() if p}
                | {p for (p, _) in pk_partner.values() if p})
    comm = {}
    for b in _batches(sorted(all_part)):
        for r in odoo.read('res.partner', b, ['commercial_partner_id']):
            cp = r.get('commercial_partner_id')
            comm[r['id']] = cp[0] if cp else r['id']

    def resolver(row):
        """(fornecedor, is_inter, tem_po) — PO primeiro, picking como fallback."""
        mid = row['move_id_n']
        plid = mv_to_pl.get(int(mid)) if pd.notna(mid) else None
        if plid and pl_to_order.get(plid):
            pid, pname = order_partner.get(pl_to_order[plid], (None, ''))
            return pname or '(PO sem partner)', comm.get(pid, pid) in partners_empresas, True
        pk = row['picking_id_n']
        if pd.notna(pk) and pk_partner.get(int(pk), (None, ''))[0]:
            pid, pname = pk_partner[int(pk)]
            return pname or '', comm.get(pid, pid) in partners_empresas, False
        return '(indefinido)', False, False

    res = df.apply(resolver, axis=1, result_type='expand')
    df['fornecedor'] = res[0]
    df['is_intercompany'] = res[1]
    df['tem_po'] = res[2].map({True: 'Sim', False: 'Nao'})

    n_inter = int(df['is_intercompany'].sum())
    df_ext = df[~df['is_intercompany']].copy()
    print(f'  inter-company excluidas: {n_inter} | compras externas: {len(df_ext)}')
    return df_ext, n_inter


# ============================================================
# MAIN
# ============================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-inicio', default=DATA_INICIO_INV,
                    help=f'YYYY-MM-DD ou ISO (default: {DATA_INICIO_INV})')
    ap.add_argument('--output-name', default=None)
    args = ap.parse_args()

    rel_dir = garantir_relatorios_dir()

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.odoo.utils.connection import get_odoo_connection
        odoo = get_odoo_connection()

        print('=== APONTAMENTOS (mrp.production) ===')
        ap_df, mo_info = baixar_apontamentos(odoo, args.data_inicio)
        print('=== COMPRAS RECEBIDAS (externas) ===')
        co_df, n_inter = baixar_compras(odoo, args.data_inicio)

        # Enriquecer produto (nome + cod) e lote
        pids = set()
        if len(ap_df):
            pids |= set(ap_df['product_id_n'].dropna().tolist())
            pids |= {v['pa_pid'] for v in mo_info.values() if v.get('pa_pid')}
        if len(co_df):
            pids |= set(co_df['product_id_n'].dropna().tolist())
        info = buscar_produto_info(odoo, pids)

        lot_ids = set()
        if len(ap_df):
            lot_ids |= set(ap_df['lot_id_n'].dropna().tolist())
        if len(co_df):
            lot_ids |= set(co_df['lot_id_n'].dropna().tolist())
        lote_nomes = buscar_lote_names(odoo, lot_ids)

    def nome(pid):
        return info.get(int(pid), ('', ''))[0] if pd.notna(pid) else ''

    def cod_de(pid):
        return info.get(int(pid), ('', ''))[1] if pd.notna(pid) else ''

    def lote_de(lid):
        return norm_lote(lote_nomes.get(int(lid), '')) if pd.notna(lid) else ''

    # ----- Aba Apontamentos -----
    if len(ap_df):
        ap_df['cod'] = ap_df['product_id_n'].map(cod_de)
        ap_df['produto'] = ap_df['product_id_n'].map(nome)
        ap_df['lote'] = ap_df['lot_id_n'].map(lote_de)
        ap_df['mo_pa_cod'] = ap_df['mo_pa_pid'].map(cod_de)
        ap_df['mo_pa_produto'] = ap_df['mo_pa_pid'].map(nome)
        ap_df['tipo_ord'] = ap_df['tipo'].map(TIPO_ORDEM).fillna(9)
        ap_out = ap_df.sort_values(['empresa', 'mo', 'tipo_ord', 'cod'])[
            ['empresa', 'date', 'mo', 'mo_state', 'mo_pa_cod', 'mo_pa_produto',
             'mo_qtd_produzida', 'tipo', 'cod', 'produto', 'lote', 'qtd',
             'origem', 'destino']].rename(columns={'date': 'data'})
    else:
        ap_out = pd.DataFrame(columns=['empresa', 'data', 'mo', 'mo_state', 'mo_pa_cod',
                                       'mo_pa_produto', 'mo_qtd_produzida', 'tipo', 'cod',
                                       'produto', 'lote', 'qtd', 'origem', 'destino'])

    # ----- Aba Compras Recebidas -----
    if len(co_df):
        co_df['cod'] = co_df['product_id_n'].map(cod_de)
        co_df['produto'] = co_df['product_id_n'].map(nome)
        co_df['lote'] = co_df['lot_id_n'].map(lote_de)
        co_out = co_df.sort_values(['empresa', 'date'])[
            ['empresa', 'date', 'fornecedor', 'tem_po', 'cod', 'produto', 'lote', 'qtd',
             'picking_name', 'origin', 'destino']].rename(
            columns={'date': 'data', 'picking_name': 'picking', 'origin': 'origem_doc'})
    else:
        co_out = pd.DataFrame(columns=['empresa', 'data', 'fornecedor', 'tem_po', 'cod',
                                       'produto', 'lote', 'qtd', 'picking', 'origem_doc',
                                       'destino'])

    # ----- Aba Resumo (por empresa) -----
    resumo_rows = []
    for cid in COMPANIES:
        emp = COMPANY_NAME[cid]
        n_mos = ap_df[ap_df['empresa'] == emp]['mo'].nunique() if len(ap_df) else 0
        qtd_pa = ap_df[(ap_df['empresa'] == emp) & (ap_df['tipo'] == 'PA')]['qtd'].sum() if len(ap_df) else 0
        n_comp = len(ap_df[(ap_df['empresa'] == emp) & (ap_df['tipo'] == 'COMPONENTE')]) if len(ap_df) else 0
        n_compras = len(co_df[co_df['empresa'] == emp]) if len(co_df) else 0
        qtd_compra = co_df[co_df['empresa'] == emp]['qtd'].sum() if len(co_df) else 0
        resumo_rows.append({
            'empresa': emp,
            'mos_concluidas': n_mos,
            'qtd_pa_produzida': round(float(qtd_pa), 3),
            'linhas_componentes': n_comp,
            'compras_recebidas_linhas': n_compras,
            'qtd_recebida': round(float(qtd_compra), 3),
        })
    resumo = pd.DataFrame(resumo_rows)
    resumo.loc['TOTAL'] = {
        'empresa': 'TOTAL',
        'mos_concluidas': resumo['mos_concluidas'].sum(),
        'qtd_pa_produzida': round(resumo['qtd_pa_produzida'].sum(), 3),
        'linhas_componentes': resumo['linhas_componentes'].sum(),
        'compras_recebidas_linhas': resumo['compras_recebidas_linhas'].sum(),
        'qtd_recebida': round(resumo['qtd_recebida'].sum(), 3),
    }

    ts = _dt.datetime.now().strftime('%Y-%m-%d_%H-%M')
    out_name = args.output_name or f'APONTAMENTOS_COMPRAS_{ts}.xlsx'
    out_path = os.path.join(rel_dir, out_name)
    print(f'\nEscrevendo {out_path}...')
    with pd.ExcelWriter(out_path, engine='xlsxwriter') as writer:
        ap_out.to_excel(writer, sheet_name='Apontamentos', index=False)
        co_out.to_excel(writer, sheet_name='Compras_Recebidas', index=False)
        resumo.to_excel(writer, sheet_name='Resumo', index=False)
        # nota inter-company excluidas
        nota = pd.DataFrame([
            {'info': 'Periodo (date >=)', 'valor': args.data_inicio},
            {'info': 'Empresas', 'valor': ', '.join(COMPANY_NAME[c] for c in COMPANIES)},
            {'info': 'Compras inter-company EXCLUIDAS (linhas)', 'valor': n_inter},
        ])
        nota.to_excel(writer, sheet_name='Resumo', index=False, startrow=len(resumo) + 2)

    print(f'OK. {out_path}')
    print(f'  Apontamentos:      {len(ap_out)} linhas '
          f'({ap_out["mo"].nunique() if len(ap_out) else 0} MOs)')
    print(f'  Compras recebidas: {len(co_out)} linhas (inter-company excluidas: {n_inter})')
    print('\n=== RESUMO ===')
    print(resumo.to_string(index=False))


if __name__ == '__main__':
    main()
