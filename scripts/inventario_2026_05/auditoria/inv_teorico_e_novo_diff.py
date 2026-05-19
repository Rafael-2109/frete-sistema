"""Pega inventario fisico do sabado, aplica movimentacoes Odoo (exceto
recebimento LF Render) e compara com estoque atual Odoo.

Gera novo diff: o que ainda nao bate apos aplicar minhas mudancas.

Output: docs/inventario-2026-05/07-relatorios/INVENTARIO_TEORICO_E_NOVO_DIFF_2026_05_18.xlsx
"""
import os
import sys
import time
import pandas as pd
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

INVENTARIO_DIR = '/mnt/c/Users/rafael.nascimento/Downloads/INVENTARIO 16-05-26'
RELATORIOS_DIR = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/07-relatorios'
OUT_PATH = os.path.join(RELATORIOS_DIR, 'INVENTARIO_TEORICO_E_NOVO_DIFF_2026_05_18.xlsx')

DATA_INICIO = '2026-05-16 00:00:00'
COMPANIES = [1, 4, 5]
COMPANY_NAME = {1: 'FB', 4: 'CD', 5: 'LF'}
BATCH_SIZE = 200


def _norm_lote(x):
    if x is None:
        return ''
    if isinstance(x, float):
        if pd.isna(x):
            return ''
        if x == int(x):
            return str(int(x))
        return str(x)
    if isinstance(x, int):
        return str(x)
    return str(x).strip()


def _norm_cod(x):
    if x is None:
        return ''
    if isinstance(x, float):
        if pd.isna(x):
            return ''
        if x == int(x):
            return str(int(x))
        return str(x)
    if isinstance(x, int):
        return str(x)
    s = str(x).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s


def is_location_interna(loc_name):
    """Detecta se loc_name eh estoque interno (FB/, CD/, LF/) e nao virtual."""
    if not loc_name:
        return False
    if not (loc_name.startswith('FB/') or loc_name.startswith('CD/') or loc_name.startswith('LF/')):
        return False
    virtual_kw = ['Virtual', 'Parceiros', 'Production', 'Inventory adjustment',
                  'Cliente', 'Customers', 'Vendors', 'Fornecedor']
    return not any(k in loc_name for k in virtual_kw)


def carregar_inv_fisico():
    """COMPILADO INV. 16.05.2026.xlsx — 3 abas (FB, LF, CD)."""
    path = os.path.join(INVENTARIO_DIR, 'COMPILADO INV. 16.05.2026.xlsx')
    rows = []
    for filial in ['FB', 'LF', 'CD']:
        df = pd.read_excel(path, sheet_name=filial)
        df.columns = [c.strip().upper() for c in df.columns]
        df = df.rename(columns={c: 'LOTE' for c in df.columns if c.strip() == 'LOTE'})
        df['cod'] = df['CODIGO'].apply(_norm_cod)
        df = df[df['cod'].str.isdigit()]
        df['lote'] = df['LOTE'].apply(_norm_lote)
        df['qtd'] = pd.to_numeric(df['QTD'], errors='coerce').fillna(0)
        df['filial'] = filial
        rows.append(df[['filial', 'cod', 'lote', 'qtd']])
    return pd.concat(rows, ignore_index=True).groupby(
        ['filial', 'cod', 'lote'], as_index=False)['qtd'].sum()


def extrair_estoque_atual_odoo(odoo):
    """Extrai stock.quant ATUAL nas 3 companies."""
    print('  Buscando stock.quant atual (companies 1/4/5)...')
    domain = [('company_id', 'in', COMPANIES), ('location_id.usage', '=', 'internal')]
    qids = odoo.search('stock.quant', domain)
    print(f'    {len(qids)} quants encontrados')
    rows = []
    t0 = time.time()
    for i in range(0, len(qids), BATCH_SIZE):
        batch = qids[i:i + BATCH_SIZE]
        data = odoo.read('stock.quant', batch, [
            'id', 'company_id', 'product_id', 'lot_id',
            'location_id', 'quantity', 'value'
        ])
        rows.extend(data)
        print(f'    {i + len(batch)}/{len(qids)} ({time.time()-t0:.0f}s)', end='\r')
    print()
    df = pd.DataFrame(rows)

    def m2o_id(x):
        return x[0] if isinstance(x, list) and len(x) >= 1 else None

    def m2o_name(x):
        return x[1] if isinstance(x, list) and len(x) >= 2 else ''

    df['company_id_n'] = df['company_id'].apply(m2o_id)
    df['filial'] = df['company_id_n'].map(COMPANY_NAME).fillna('?')
    df['product_id_n'] = df['product_id'].apply(m2o_id)
    df['lot_name'] = df['lot_id'].apply(m2o_name)
    df['lote'] = df['lot_name'].apply(_norm_lote)
    df['loc_name'] = df['location_id'].apply(m2o_name)
    df['qtd'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
    df['valor'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)

    # buscar default_code
    pids = df['product_id_n'].dropna().unique().tolist()
    pmap = {}
    for i in range(0, len(pids), BATCH_SIZE):
        b = pids[i:i + BATCH_SIZE]
        d = odoo.read('product.product', list(b), ['default_code'])
        for p in d:
            pmap[p['id']] = p.get('default_code') or ''
    df['cod'] = df['product_id_n'].map(lambda x: pmap.get(x, ''))
    df['cod'] = df['cod'].apply(_norm_cod)
    df = df[df['cod'].str.isdigit()]
    out = df.groupby(['filial', 'cod', 'lote'], as_index=False).agg(
        qtd_odoo_atual=('qtd', 'sum'),
        valor_atual=('valor', 'sum')
    )
    out['custo_unit'] = np.where(out['qtd_odoo_atual'] > 0,
                                  out['valor_atual'] / out['qtd_odoo_atual'], 0)
    return out


def extrair_movimentacoes(odoo, pickings_inventario, pickings_excluir_efetivo):
    """Extrai stock.move.line desde 16/05, com classificacao."""
    print('  Buscando stock.move.line >= 2026-05-16...')
    domain = [('date', '>=', DATA_INICIO),
              ('company_id', 'in', COMPANIES),
              ('state', '=', 'done')]
    mids = odoo.search('stock.move.line', domain)
    print(f'    {len(mids)} move_lines encontradas')
    fields = ['id', 'date', 'company_id', 'product_id', 'qty_done',
              'lot_id', 'location_id', 'location_dest_id', 'picking_id',
              'reference', 'origin', 'create_uid', 'state']
    rows = []
    t0 = time.time()
    for i in range(0, len(mids), BATCH_SIZE):
        batch = mids[i:i + BATCH_SIZE]
        data = odoo.read('stock.move.line', batch, fields)
        rows.extend(data)
        print(f'    {i + len(batch)}/{len(mids)} ({time.time()-t0:.0f}s)', end='\r')
    print()
    df = pd.DataFrame(rows)

    def m2o_id(x):
        return x[0] if isinstance(x, list) and len(x) >= 1 else None

    def m2o_name(x):
        return x[1] if isinstance(x, list) and len(x) >= 2 else ''

    df['company_id_n'] = df['company_id'].apply(m2o_id)
    df['filial'] = df['company_id_n'].map(COMPANY_NAME).fillna('?')
    df['product_id_n'] = df['product_id'].apply(m2o_id)
    df['lot_name'] = df['lot_id'].apply(m2o_name)
    df['lote'] = df['lot_name'].apply(_norm_lote)
    df['loc_src_name'] = df['location_id'].apply(m2o_name)
    df['loc_dst_name'] = df['location_dest_id'].apply(m2o_name)
    df['picking_id_n'] = df['picking_id'].apply(m2o_id)
    df['picking_name'] = df['picking_id'].apply(m2o_name)
    df['create_uid_name'] = df['create_uid'].apply(m2o_name)
    df['qty_done'] = pd.to_numeric(df['qty_done'], errors='coerce').fillna(0)

    # buscar cod_produto
    pids = df['product_id_n'].dropna().unique().tolist()
    pmap = {}
    for i in range(0, len(pids), BATCH_SIZE):
        b = pids[i:i + BATCH_SIZE]
        d = odoo.read('product.product', list(b), ['default_code'])
        for p in d:
            pmap[p['id']] = p.get('default_code') or ''
    df['cod'] = df['product_id_n'].map(lambda x: pmap.get(x, ''))
    df['cod'] = df['cod'].apply(_norm_cod)

    # classificar
    def cls(pid):
        if pid is None or pd.isna(pid):
            return 'INVENTORY_ADJUST'
        pid = int(pid)
        if pid in pickings_inventario:
            return 'INVENTARIO_PICKING'
        if pid in pickings_excluir_efetivo:
            return 'RECEBIMENTO_LF_RENDER'
        return 'OUTROS_PICKING'

    df['origem_classificada'] = df['picking_id_n'].apply(cls)
    return df


def aplicar_movimentacoes(inv_fisico, movs):
    """Pega inv_fisico (DataFrame com filial, cod, lote, qtd) e aplica movs.

    Retorna DataFrame com inventario teorico atual.
    """
    estado = defaultdict(float)
    # Inicializa com inv fisico
    for _, r in inv_fisico.iterrows():
        estado[(r['filial'], r['cod'], r['lote'])] += r['qtd']

    movs_aplicadas = 0
    movs_ignoradas = 0
    for _, m in movs.iterrows():
        cod = m['cod']
        lote = m['lote']
        qty = m['qty_done']
        filial = m['filial']
        if not cod or not cod.isdigit() or qty == 0:
            movs_ignoradas += 1
            continue
        src_interna = is_location_interna(m['loc_src_name'])
        dst_interna = is_location_interna(m['loc_dst_name'])
        if src_interna:
            estado[(filial, cod, lote)] -= qty
        if dst_interna:
            estado[(filial, cod, lote)] += qty
        if src_interna or dst_interna:
            movs_aplicadas += 1
        else:
            movs_ignoradas += 1

    rows = []
    for (filial, cod, lote), qtd in estado.items():
        rows.append({'filial': filial, 'cod': cod, 'lote': lote, 'qtd_teorica': qtd})
    print(f'    Movs aplicadas: {movs_aplicadas} | ignoradas (virtuais ou cod invalido): {movs_ignoradas}')
    return pd.DataFrame(rows)


def main():
    print('=' * 70)
    print('INVENTARIO TEORICO + NOVO DIFF (vs Odoo atual)')
    print('=' * 70)

    from app import create_app, db
    app = create_app()
    with app.app_context():
        rec = db.session.execute(db.text("""
            SELECT odoo_picking_id, odoo_transfer_out_picking_id, odoo_transfer_in_picking_id
            FROM recebimento_lf WHERE criado_em >= '2026-05-16'
        """)).fetchall()
        pickings_excluir = set(int(p) for r in rec for p in r if p)
        inv_p = db.session.execute(db.text("""
            SELECT DISTINCT picking_id_odoo FROM ajuste_estoque_inventario
            WHERE ciclo='INVENTARIO_2026_05' AND picking_id_odoo IS NOT NULL
        """)).scalars().all()
        pickings_inventario = set(int(p) for p in inv_p if p)
    pickings_excluir_efetivo = pickings_excluir - pickings_inventario
    print(f'\nPickings excluir efetivo (rec LF puro): {sorted(pickings_excluir_efetivo)}')
    print(f'Pickings inventario (mantem): {sorted(pickings_inventario)}')

    from app.odoo.utils.connection import get_odoo_connection
    print('\n[1] Conectando Odoo...')
    odoo = get_odoo_connection()

    print('\n[2] Extraindo estoque ATUAL Odoo...')
    odoo_atual = extrair_estoque_atual_odoo(odoo)
    print(f'  {len(odoo_atual)} (filial, cod, lote) no Odoo atual')

    print('\n[3] Extraindo movimentacoes desde 16/05...')
    movs = extrair_movimentacoes(odoo, pickings_inventario, pickings_excluir_efetivo)
    # Excluir as movimentacoes do recebimento LF Render
    movs_incluidas = movs[movs['origem_classificada'] != 'RECEBIMENTO_LF_RENDER'].copy()
    movs_excluidas = movs[movs['origem_classificada'] == 'RECEBIMENTO_LF_RENDER'].copy()
    print(f'  {len(movs)} movs total | {len(movs_incluidas)} incluidas | {len(movs_excluidas)} excluidas')

    print('\n[4] Carregando inventario fisico...')
    inv = carregar_inv_fisico()
    print(f'  {len(inv)} (filial, cod, lote) no inventario')

    print('\n[5] Aplicando movs no inv fisico...')
    teorico = aplicar_movimentacoes(inv, movs_incluidas)
    print(f'  {len(teorico)} (filial, cod, lote) no inventario teorico')

    print('\n[6] Comparando teorico vs Odoo atual...')
    diff = teorico.merge(
        odoo_atual[['filial', 'cod', 'lote', 'qtd_odoo_atual', 'valor_atual', 'custo_unit']],
        on=['filial', 'cod', 'lote'], how='outer'
    )
    diff['qtd_teorica'] = diff['qtd_teorica'].fillna(0)
    diff['qtd_odoo_atual'] = diff['qtd_odoo_atual'].fillna(0)
    diff['valor_atual'] = diff['valor_atual'].fillna(0)
    diff['custo_unit'] = diff['custo_unit'].fillna(0)
    diff['diff_qtd'] = diff['qtd_teorica'] - diff['qtd_odoo_atual']
    diff['diff_valor'] = diff['diff_qtd'] * diff['custo_unit']
    diff['cobertura'] = np.where(
        (diff['qtd_teorica'].abs() > 0.01) & (diff['qtd_odoo_atual'].abs() > 0.01), 'AMBOS',
        np.where(diff['qtd_teorica'].abs() > 0.01, 'SO_TEORICO', 'SO_ODOO')
    )
    diff['status'] = np.where(diff['diff_qtd'].abs() < 0.01, 'OK', 'DIVERGENTE')

    # Resumo por filial
    resumo = diff.groupby('filial', as_index=False).agg(
        n_chaves=('cod', 'count'),
        n_OK=('status', lambda s: (s == 'OK').sum()),
        n_DIVERGENTE=('status', lambda s: (s == 'DIVERGENTE').sum()),
        sum_teorica=('qtd_teorica', 'sum'),
        sum_odoo=('qtd_odoo_atual', 'sum'),
        sum_diff=('diff_qtd', 'sum'),
        sum_diff_valor=('diff_valor', 'sum')
    )

    # ===== ESCREVER =====
    os.makedirs(RELATORIOS_DIR, exist_ok=True)
    print(f'\n[7] Escrevendo {OUT_PATH}...')

    cols_movs = ['id', 'date', 'filial', 'cod', 'lote',
                 'qty_done', 'loc_src_name', 'loc_dst_name',
                 'picking_id_n', 'picking_name', 'reference', 'origin',
                 'create_uid_name', 'origem_classificada']
    cols_movs = [c for c in cols_movs if c in movs_incluidas.columns]

    with pd.ExcelWriter(OUT_PATH, engine='xlsxwriter') as writer:
        readme = pd.DataFrame([
            ['Data', '2026-05-18'],
            ['', ''],
            ['Logica', 'Inv fisico 16/05 + movs Odoo (exceto recebimento LF Render) = inv teorico hoje'],
            ['', ''],
            ['Comparacao', 'inv teorico vs estoque atual Odoo'],
            ['diff_qtd', 'qtd_teorica - qtd_odoo_atual (positivo = sobrando no teorico)'],
            ['cobertura', 'AMBOS = (filial,cod,lote) em ambos | SO_TEORICO | SO_ODOO'],
            ['', ''],
            ['Excluidos', f'{len(pickings_excluir_efetivo)} pickings (recebimento LF Render puro): {sorted(pickings_excluir_efetivo)}'],
            ['Total movs no periodo', len(movs)],
            ['Movs incluidas', len(movs_incluidas)],
            ['Movs excluidas (rec LF Render)', len(movs_excluidas)],
        ], columns=['Campo', 'Valor'])
        readme.to_excel(writer, sheet_name='README', index=False)

        # Resumo
        resumo.to_excel(writer, sheet_name='1_Resumo', index=False)

        # Movimentacoes (1 aba so, como pedido)
        movs_incluidas[cols_movs].sort_values('date').to_excel(
            writer, sheet_name='2_Movimentacoes', index=False
        )

        # Inv teorico
        teorico[teorico['qtd_teorica'].abs() > 0.001].sort_values(
            ['filial', 'cod', 'lote']
        ).to_excel(writer, sheet_name='3_Inv_Teorico', index=False)

        # Odoo atual
        odoo_atual[odoo_atual['qtd_odoo_atual'].abs() > 0.001].sort_values(
            ['filial', 'cod', 'lote']
        ).to_excel(writer, sheet_name='4_Odoo_Atual', index=False)

        # Diff completo
        cols_diff = ['filial', 'cod', 'lote', 'qtd_teorica', 'qtd_odoo_atual',
                     'diff_qtd', 'custo_unit', 'diff_valor', 'cobertura', 'status']
        diff[cols_diff].sort_values(['filial', 'cod', 'lote']).to_excel(
            writer, sheet_name='5_Diff_Novo', index=False
        )

        # So divergentes
        div = diff[diff['status'] == 'DIVERGENTE'].copy()
        div['abs_v'] = div['diff_valor'].abs()
        div = div.sort_values('abs_v', ascending=False)
        div[cols_diff].head(2000).to_excel(writer, sheet_name='6_Divergentes_TOP', index=False)

    print(f'\nOK. {OUT_PATH}')
    print('\n=== Resumo ===')
    print(resumo.to_string(index=False, float_format=lambda x: f'{x:>12,.0f}'))


if __name__ == '__main__':
    main()
