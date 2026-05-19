"""Confronto direto: SOT vs 3 fontes derivadas.

POR (filial, cod_produto) — agregado.
POR (filial, cod_produto, lote) — detalhado.

Output unico: docs/inventario-2026-05/07-relatorios/CONFRONTO_4_FONTES_2026_05_18.xlsx

Sem interpretacao de acoes/ondas. So numeros brutos.
"""
import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

INVENTARIO_DIR = '/mnt/c/Users/rafael.nascimento/Downloads/INVENTARIO 16-05-26'
RELATORIOS_DIR = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/07-relatorios'
OUT_PATH = os.path.join(RELATORIOS_DIR, 'CONFRONTO_4_FONTES_2026_05_18.xlsx')

COMPANY_ID = {'FB': 1, 'CD': 4, 'LF': 5}
COMPANY_NAME = {1: 'FB', 4: 'CD', 5: 'LF'}


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


# ============================================================
# FONTE 1: SOT (COMPILADO INV + estoque-odoo)
# ============================================================
def sot_por_cod():
    """Por (filial, cod): sum_inv (do COMPILADO) + sum_odoo (do estoque-odoo)."""
    inv_rows, odoo_rows = [], []
    path_inv = os.path.join(INVENTARIO_DIR, 'COMPILADO INV. 16.05.2026.xlsx')
    for filial in ['FB', 'LF', 'CD']:
        df = pd.read_excel(path_inv, sheet_name=filial)
        df.columns = [c.strip().upper() for c in df.columns]
        df = df.rename(columns={c: 'LOTE' for c in df.columns if c.strip() == 'LOTE'})
        df['cod'] = df['CODIGO'].apply(_norm_cod)
        df = df[df['cod'].str.isdigit()]
        df['lote'] = df['LOTE'].apply(_norm_lote)
        df['qtd'] = pd.to_numeric(df['QTD'], errors='coerce').fillna(0)
        df['company_id'] = COMPANY_ID[filial]
        df['filial'] = filial
        inv_rows.append(df[['company_id', 'filial', 'cod', 'lote', 'qtd']])
    inv = pd.concat(inv_rows, ignore_index=True)
    inv_full = inv.copy()
    inv = inv.groupby(['company_id', 'filial', 'cod'], as_index=False)['qtd'].sum()
    inv = inv.rename(columns={'qtd': 'SOT_inv'})

    for filial in ['FB', 'LF', 'CD']:
        df = pd.read_excel(os.path.join(INVENTARIO_DIR, f'estoque-odoo-{filial}.xlsx'))
        df['cod'] = df['cod_produto'].apply(_norm_cod)
        df['lote'] = df['lot_name'].apply(_norm_lote)
        df['qtd'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        df['valor'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)
        df['company_id'] = COMPANY_ID[filial]
        df['filial'] = filial
        odoo_rows.append(df[['company_id', 'filial', 'cod', 'lote', 'qtd', 'valor']])
    odoo_full = pd.concat(odoo_rows, ignore_index=True)
    odoo = odoo_full.groupby(['company_id', 'filial', 'cod'], as_index=False).agg(
        SOT_odoo=('qtd', 'sum'),
        SOT_valor_odoo=('valor', 'sum')
    )
    sot = inv.merge(odoo, on=['company_id', 'filial', 'cod'], how='outer')
    sot['SOT_inv'] = sot['SOT_inv'].fillna(0)
    sot['SOT_odoo'] = sot['SOT_odoo'].fillna(0)
    sot['SOT_valor_odoo'] = sot['SOT_valor_odoo'].fillna(0)
    sot['filial'] = sot.apply(
        lambda r: r['filial'] if pd.notna(r['filial']) else COMPANY_NAME.get(r['company_id'], '?'),
        axis=1
    )
    sot['SOT_diff'] = sot['SOT_inv'] - sot['SOT_odoo']
    return sot, inv_full, odoo_full


# ============================================================
# FONTE 2: DIFFS (diff-inv-vs-odoo-*.xlsx)
# ============================================================
def diffs_por_cod():
    """Para cada filial, agregamos qtd_ajuste do diff por cod.

    Tambem agregamos qtd_inventario por (cod, lote_inv DISTINCT) e
    qtd_odoo por (cod, lote_odoo DISTINCT) para reconstruir o saldo total.
    """
    rows = []
    rows_lote = []
    for filial in ['FB', 'LF', 'CD']:
        path = os.path.join(INVENTARIO_DIR, f'diff-inv-vs-odoo-{filial}.xlsx')
        df = pd.read_excel(path)
        df['cod'] = df['cod_produto'].apply(_norm_cod)
        df['lote_inv'] = df['lote_inventariado'].apply(_norm_lote)
        df['lote_odoo'] = df['lote_odoo'].apply(_norm_lote)
        df['qtd_inv'] = pd.to_numeric(df['qtd_inventario'], errors='coerce').fillna(0)
        df['qtd_odoo'] = pd.to_numeric(df['qtd_odoo'], errors='coerce').fillna(0)
        df['qtd_ajuste'] = pd.to_numeric(df['qtd_ajuste'], errors='coerce').fillna(0)
        df['valor_mov'] = pd.to_numeric(df['valor_movimentacao'], errors='coerce').fillna(0)
        df['filial'] = filial
        df['company_id'] = COMPANY_ID[filial]
        rows_lote.append(df.copy())

    df_all = pd.concat(rows_lote, ignore_index=True)

    # Para reconstituir SOT do diff: distinguindo por lote_inv (qtd inv unica por lote)
    # e por lote_odoo (qtd odoo unica por lote)
    inv_distinct = df_all.drop_duplicates(['company_id', 'cod', 'lote_inv'])
    inv_agg = inv_distinct.groupby(['company_id', 'filial', 'cod'], as_index=False)['qtd_inv'].sum()

    odoo_distinct = df_all.drop_duplicates(['company_id', 'cod', 'lote_odoo'])
    odoo_agg = odoo_distinct.groupby(['company_id', 'filial', 'cod'], as_index=False)['qtd_odoo'].sum()

    # Soma direta de qtd_ajuste (essa soma representa o ajuste liquido do diff)
    ajuste_agg = df_all.groupby(['company_id', 'filial', 'cod'], as_index=False).agg(
        DIFFS_qtd_ajuste=('qtd_ajuste', 'sum'),
        DIFFS_valor=('valor_mov', 'sum'),
        DIFFS_n_linhas=('cod', 'count')
    )

    diffs = inv_agg.rename(columns={'qtd_inv': 'DIFFS_inv'}).merge(
        odoo_agg.rename(columns={'qtd_odoo': 'DIFFS_odoo'}),
        on=['company_id', 'filial', 'cod'], how='outer'
    ).merge(ajuste_agg, on=['company_id', 'filial', 'cod'], how='outer')
    for c in ['DIFFS_inv', 'DIFFS_odoo', 'DIFFS_qtd_ajuste', 'DIFFS_valor', 'DIFFS_n_linhas']:
        if c in diffs.columns:
            diffs[c] = diffs[c].fillna(0)
    return diffs, df_all


# ============================================================
# FONTE 3: TABELA ajuste_estoque_inventario
# ============================================================
def tabela_por_cod():
    from app import create_app, db
    app = create_app()
    with app.app_context():
        rows = db.session.execute(db.text("""
            SELECT id, company_id, cod_produto,
                   COALESCE(lote_inventariado,'') AS lote_inv,
                   COALESCE(lote_odoo,'') AS lote_odoo,
                   COALESCE(lote_origem,'') AS lote_origem,
                   COALESCE(lote_destino,'') AS lote_destino,
                   qtd_inventario::float AS qtd_inv,
                   qtd_odoo::float AS qtd_odoo,
                   qtd_ajuste::float AS qtd_ajuste,
                   COALESCE(custo_medio,0)::float AS custo_medio,
                   acao_decidida, status
            FROM ajuste_estoque_inventario
            WHERE ciclo='INVENTARIO_2026_05'
              AND status != 'CANCELADO'
        """)).mappings().all()
    df = pd.DataFrame(rows)
    df['cod'] = df['cod_produto'].apply(_norm_cod)
    for c in ['lote_inv', 'lote_odoo', 'lote_origem', 'lote_destino']:
        df[c] = df[c].apply(_norm_lote)
    df['filial'] = df['company_id'].map(COMPANY_NAME)
    df['valor_aj'] = df['qtd_ajuste'] * df['custo_medio']

    # Reconstruir saldo: por (filial, cod, lote_inv) tomando MAX(qtd_inv)
    # (todas as linhas com mesmo lote_inv tem mesmo qtd_inv idealmente)
    inv_distinct = df.drop_duplicates(['company_id', 'cod', 'lote_inv'])
    inv_agg = inv_distinct.groupby(['company_id', 'cod'], as_index=False)['qtd_inv'].sum()
    inv_agg = inv_agg.rename(columns={'qtd_inv': 'TAB_inv'})

    odoo_distinct = df.drop_duplicates(['company_id', 'cod', 'lote_odoo'])
    odoo_agg = odoo_distinct.groupby(['company_id', 'cod'], as_index=False)['qtd_odoo'].sum()
    odoo_agg = odoo_agg.rename(columns={'qtd_odoo': 'TAB_odoo'})

    # Soma de qtd_ajuste por (filial, cod)
    ajuste_agg = df.groupby(['company_id', 'cod'], as_index=False).agg(
        TAB_qtd_ajuste=('qtd_ajuste', 'sum'),
        TAB_valor=('valor_aj', 'sum'),
        TAB_n=('id', 'count'),
        TAB_acoes=('acao_decidida', lambda s: ','.join(sorted(set(s)))),
        TAB_status=('status', lambda s: ','.join(sorted(set(s)))),
    )
    tab = inv_agg.merge(odoo_agg, on=['company_id', 'cod'], how='outer').merge(
        ajuste_agg, on=['company_id', 'cod'], how='outer'
    )
    for c in ['TAB_inv', 'TAB_odoo', 'TAB_qtd_ajuste', 'TAB_valor', 'TAB_n']:
        if c in tab.columns:
            tab[c] = tab[c].fillna(0)
    for c in ['TAB_acoes', 'TAB_status']:
        if c in tab.columns:
            tab[c] = tab[c].fillna('')
    return tab, df


# ============================================================
# FONTE 4: PLANO-PRE-ETAPA-CD
# ============================================================
def plano_por_cod():
    path = os.path.join(RELATORIOS_DIR, 'plano-pre-etapa-cd.xlsx')
    res = {}
    res['internas'] = pd.read_excel(path, sheet_name='Internas')
    res['residual'] = pd.read_excel(path, sheet_name='Residual FB-CD')
    res['positivos'] = pd.read_excel(path, sheet_name='Positivos Puros')

    # Internas: transferencia interna no CD (tipo POS / NEG)
    df = res['internas'].copy()
    df['cod'] = df['cod_produto'].apply(_norm_cod)
    df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0)
    df['valor'] = pd.to_numeric(df['valor_movimentacao'], errors='coerce').fillna(0)
    df['filial'] = 'CD'
    df['company_id'] = 4
    internas_pos = df[df['tipo'] == 'POS'].groupby(['company_id', 'cod'], as_index=False).agg(
        PLANO_internas_POS_qty=('qty', 'sum'),
        PLANO_internas_POS_valor=('valor', 'sum'),
        PLANO_internas_POS_n=('cod', 'count')
    )
    internas_neg = df[df['tipo'] == 'NEG'].groupby(['company_id', 'cod'], as_index=False).agg(
        PLANO_internas_NEG_qty=('qty', 'sum'),
        PLANO_internas_NEG_valor=('valor', 'sum'),
        PLANO_internas_NEG_n=('cod', 'count')
    )
    # Residual FB->CD
    df = res['residual'].copy()
    df['cod'] = df['cod_produto'].apply(_norm_cod)
    df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0)
    df['valor'] = pd.to_numeric(df['valor_movimentacao'], errors='coerce').fillna(0)
    df['company_id'] = 4
    residual = df.groupby(['company_id', 'cod'], as_index=False).agg(
        PLANO_residual_qty=('qty', 'sum'),
        PLANO_residual_valor=('valor', 'sum')
    )
    # Positivos puros
    df = res['positivos'].copy()
    df['cod'] = df['cod_produto'].apply(_norm_cod)
    df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0)
    df['valor'] = pd.to_numeric(df['valor_movimentacao'], errors='coerce').fillna(0)
    df['company_id'] = 4
    positivos = df.groupby(['company_id', 'cod'], as_index=False).agg(
        PLANO_positivos_qty=('qty', 'sum'),
        PLANO_positivos_valor=('valor', 'sum')
    )
    # Merge plano
    plano = internas_pos.merge(internas_neg, on=['company_id', 'cod'], how='outer')
    plano = plano.merge(residual, on=['company_id', 'cod'], how='outer')
    plano = plano.merge(positivos, on=['company_id', 'cod'], how='outer')
    for c in plano.columns:
        if c not in ('company_id', 'cod'):
            plano[c] = plano[c].fillna(0)
    plano['filial'] = 'CD'
    return plano


# ============================================================
# MAIN
# ============================================================
def main():
    print('=' * 70)
    print('CONFRONTO 4 FONTES — Inventario 2026-05')
    print('=' * 70)

    print('\n[1] SOT (COMPILADO INV + estoque-odoo)...')
    sot, sot_inv_full, sot_odoo_full = sot_por_cod()
    print(f'  {len(sot)} pares (filial, cod)')

    print('\n[2] DIFFS (diff-inv-vs-odoo-*.xlsx)...')
    diffs, diffs_full = diffs_por_cod()
    print(f'  {len(diffs)} pares (filial, cod) | total linhas: {len(diffs_full)}')

    print('\n[3] TABELA ajuste_estoque_inventario...')
    tab, tab_full = tabela_por_cod()
    print(f'  {len(tab)} pares (filial, cod)')

    print('\n[4] PLANO pre-etapa-cd...')
    plano = plano_por_cod()
    print(f'  {len(plano)} cods CD')

    # ============ JOIN FINAL ============
    # SOT eh a master
    out = sot.copy()
    out = out.merge(diffs.drop(columns=['filial']), on=['company_id', 'cod'], how='left')
    out = out.merge(tab, on=['company_id', 'cod'], how='left')
    out = out.merge(plano.drop(columns=['filial']), on=['company_id', 'cod'], how='left')

    # Preencher NaN com 0
    for c in out.columns:
        if c not in ('company_id', 'filial', 'cod'):
            if out[c].dtype == 'object':
                out[c] = out[c].fillna('')
            else:
                out[c] = out[c].fillna(0)

    # ============ DELTAS ============
    out['delta_SOT_DIFFS_inv'] = out['DIFFS_inv'] - out['SOT_inv']
    out['delta_SOT_DIFFS_odoo'] = out['DIFFS_odoo'] - out['SOT_odoo']
    out['delta_SOT_TAB_inv'] = out['TAB_inv'] - out['SOT_inv']
    out['delta_SOT_TAB_odoo'] = out['TAB_odoo'] - out['SOT_odoo']
    out['SOT_diff'] = out['SOT_inv'] - out['SOT_odoo']
    out['delta_DIFFS_ajuste_vs_SOT'] = out['DIFFS_qtd_ajuste'] - out['SOT_diff']
    out['delta_TAB_ajuste_vs_SOT'] = out['TAB_qtd_ajuste'] - out['SOT_diff']

    # ============ FLAG DE CONFIABILIDADE ============
    tol = 0.5  # 0.5 unidade

    def classifica(r):
        flags = []
        if abs(r['delta_SOT_DIFFS_inv']) > tol or abs(r['delta_SOT_DIFFS_odoo']) > tol:
            flags.append('DIFFS_div')
        if abs(r['delta_SOT_TAB_inv']) > tol or abs(r['delta_SOT_TAB_odoo']) > tol:
            flags.append('TAB_div')
        return '/'.join(flags) if flags else 'OK'
    out['confronto'] = out.apply(classifica, axis=1)

    # ============ RESUMO ============
    resumo = []
    for cid, fil in [(1, 'FB'), (4, 'CD'), (5, 'LF')]:
        sub = out[out['company_id'] == cid]
        resumo.append({
            'filial': fil,
            'n_cods': len(sub),
            'SOT_inv': sub['SOT_inv'].sum(),
            'SOT_odoo': sub['SOT_odoo'].sum(),
            'SOT_diff': sub['SOT_diff'].sum(),
            'DIFFS_inv': sub['DIFFS_inv'].sum(),
            'DIFFS_odoo': sub['DIFFS_odoo'].sum(),
            'DIFFS_qtd_ajuste': sub['DIFFS_qtd_ajuste'].sum(),
            'TAB_inv': sub['TAB_inv'].sum(),
            'TAB_odoo': sub['TAB_odoo'].sum(),
            'TAB_qtd_ajuste': sub['TAB_qtd_ajuste'].sum(),
            'PLANO_internas_POS_qty': sub.get('PLANO_internas_POS_qty', pd.Series([0])).sum(),
            'PLANO_internas_NEG_qty': sub.get('PLANO_internas_NEG_qty', pd.Series([0])).sum(),
            'PLANO_residual_qty': sub.get('PLANO_residual_qty', pd.Series([0])).sum(),
            'PLANO_positivos_qty': sub.get('PLANO_positivos_qty', pd.Series([0])).sum(),
            'delta_SOT_vs_DIFFS_inv': sub['delta_SOT_DIFFS_inv'].sum(),
            'delta_SOT_vs_DIFFS_odoo': sub['delta_SOT_DIFFS_odoo'].sum(),
            'delta_SOT_vs_TAB_inv': sub['delta_SOT_TAB_inv'].sum(),
            'delta_SOT_vs_TAB_odoo': sub['delta_SOT_TAB_odoo'].sum(),
        })
    df_resumo = pd.DataFrame(resumo)

    # ============ ESCREVER EXCEL ============
    os.makedirs(RELATORIOS_DIR, exist_ok=True)
    print(f'\n[5] Escrevendo {OUT_PATH}...')

    with pd.ExcelWriter(OUT_PATH, engine='xlsxwriter') as writer:
        readme = pd.DataFrame([
            ['Data', '2026-05-18'],
            ['Pergunta', 'As 3 fontes derivadas (diffs, tabela, plano) refletem a SOT?'],
            ['', ''],
            ['SOT_inv', 'SUM(qtd) por (filial, cod) em COMPILADO INV. 16.05.2026.xlsx'],
            ['SOT_odoo', 'SUM(quantity) por (filial, cod) em estoque-odoo-{X}.xlsx'],
            ['SOT_diff', 'SOT_inv - SOT_odoo (delta liquido por cod)'],
            ['', ''],
            ['DIFFS_inv/odoo', 'SUM(DISTINCT por lote_inv ou lote_odoo) em diff-inv-vs-odoo-{X}.xlsx'],
            ['DIFFS_qtd_ajuste', 'SUM(qtd_ajuste) nas mesmas linhas — total ajuste liquido segundo diff'],
            ['', ''],
            ['TAB_inv/odoo', 'Mesma logica do DIFFS, agora na tabela ajuste_estoque_inventario'],
            ['TAB_qtd_ajuste', 'SUM(qtd_ajuste) — total ajuste liquido segundo a tabela. ATENCAO: inclui INDISPONIBILIZAR que tem qtd_ajuste mas nao move estoque'],
            ['', ''],
            ['PLANO_*_qty', 'SUM(qty) por aba do plano-pre-etapa-cd (so CD)'],
            ['', ''],
            ['delta_SOT_DIFFS_inv', 'DIFFS_inv - SOT_inv: se != 0, planilha diff diverge da SOT em qtd_inv'],
            ['delta_SOT_TAB_inv', 'TAB_inv - SOT_inv: se != 0, tabela diverge da SOT em qtd_inv'],
            ['confronto', 'OK | DIFFS_div | TAB_div | DIFFS_div/TAB_div'],
            ['Tolerancia', '0.5 unidade'],
        ], columns=['Campo', 'Significado'])
        readme.to_excel(writer, sheet_name='README', index=False)

        df_resumo.to_excel(writer, sheet_name='1_Resumo_Filial', index=False)

        # Resumo por confronto
        cont = out.groupby(['filial', 'confronto'], as_index=False).agg(
            n=('cod', 'count'),
            SOT_diff_sum=('SOT_diff', 'sum'),
            SOT_inv_sum=('SOT_inv', 'sum'),
            SOT_odoo_sum=('SOT_odoo', 'sum'),
        )
        cont.to_excel(writer, sheet_name='2_Confronto', index=False)

        # Tabela COMPLETA: 1 linha por (filial, cod)
        cols_main = ['filial', 'company_id', 'cod',
                     'SOT_inv', 'SOT_odoo', 'SOT_diff',
                     'DIFFS_inv', 'DIFFS_odoo', 'DIFFS_qtd_ajuste', 'DIFFS_valor', 'DIFFS_n_linhas',
                     'TAB_inv', 'TAB_odoo', 'TAB_qtd_ajuste', 'TAB_valor', 'TAB_n',
                     'TAB_acoes', 'TAB_status',
                     'PLANO_internas_POS_qty', 'PLANO_internas_NEG_qty',
                     'PLANO_residual_qty', 'PLANO_positivos_qty',
                     'delta_SOT_DIFFS_inv', 'delta_SOT_DIFFS_odoo',
                     'delta_SOT_TAB_inv', 'delta_SOT_TAB_odoo',
                     'delta_DIFFS_ajuste_vs_SOT', 'delta_TAB_ajuste_vs_SOT',
                     'confronto']
        cols_main = [c for c in cols_main if c in out.columns]
        out[cols_main].sort_values(['filial', 'cod']).to_excel(
            writer, sheet_name='3_Por_Cod_TODOS', index=False
        )

        # So divergentes
        div = out[out['confronto'] != 'OK'].copy()
        div['abs_delta'] = (
            div['delta_SOT_TAB_inv'].abs() + div['delta_SOT_TAB_odoo'].abs() +
            div['delta_SOT_DIFFS_inv'].abs() + div['delta_SOT_DIFFS_odoo'].abs()
        )
        div = div.sort_values('abs_delta', ascending=False)
        div[cols_main].head(1000).to_excel(writer, sheet_name='4_Divergentes_TOP1000', index=False)

    print(f'OK. {OUT_PATH}')

    print('\n' + '=' * 70)
    print('RESUMO POR FILIAL — fontes lado a lado')
    print('=' * 70)
    cols_print = ['filial', 'n_cods', 'SOT_inv', 'SOT_odoo', 'SOT_diff',
                  'DIFFS_inv', 'DIFFS_odoo', 'DIFFS_qtd_ajuste',
                  'TAB_inv', 'TAB_odoo', 'TAB_qtd_ajuste']
    print(df_resumo[cols_print].to_string(index=False, float_format=lambda x: f'{x:>14,.0f}'))

    print('\nDELTAS (DIFFS vs SOT, TAB vs SOT)')
    cols_d = ['filial', 'delta_SOT_vs_DIFFS_inv', 'delta_SOT_vs_DIFFS_odoo',
              'delta_SOT_vs_TAB_inv', 'delta_SOT_vs_TAB_odoo']
    print(df_resumo[cols_d].to_string(index=False, float_format=lambda x: f'{x:>14,.0f}'))

    print('\nPLANO CD (qty por aba)')
    cd = df_resumo[df_resumo['filial']=='CD'].iloc[0]
    print(f"  internas POS:  {cd['PLANO_internas_POS_qty']:>14,.0f}")
    print(f"  internas NEG:  {cd['PLANO_internas_NEG_qty']:>14,.0f}")
    print(f"  residual FB-CD:{cd['PLANO_residual_qty']:>14,.0f}")
    print(f"  positivos puro:{cd['PLANO_positivos_qty']:>14,.0f}")


if __name__ == '__main__':
    main()
