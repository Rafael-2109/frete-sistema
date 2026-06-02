# etapa: audit
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""Versao COMPLETA: compara SOT contra TODAS as 3 fontes derivadas.

Adiciona ao primeiro script:
- Analise dos diffs originais (diff-inv-vs-odoo-{FB,LF,CD}.xlsx)
- Analise do plano-pre-etapa-cd.xlsx
- Visao MACRO por cod_produto (agregado, ignora lote — robusto a RENOMEAR/TRANSFERIR)
- Comparacao 3 fontes lado a lado

NAO MEXE NAS PLANILHAS ORIGINAIS.
Gera: docs/inventario-2026-05/07-relatorios/COMPARACAO_SOT_FULL_2026_05_18.xlsx
"""
import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

INVENTARIO_DIR = '/mnt/c/Users/rafael.nascimento/Downloads/INVENTARIO 16-05-26'
RELATORIOS_DIR = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/07-relatorios'
OUT_PATH = os.path.join(RELATORIOS_DIR, 'COMPARACAO_SOT_FULL_2026_05_18.xlsx')

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


# ==========================================================
# SOT: INVENTARIO FISICO
# ==========================================================
def carregar_sot_inv():
    path = os.path.join(INVENTARIO_DIR, 'COMPILADO INV. 16.05.2026.xlsx')
    out = []
    for filial in ['FB', 'LF', 'CD']:
        df = pd.read_excel(path, sheet_name=filial)
        df.columns = [c.strip().upper() for c in df.columns]
        df = df.rename(columns={c: 'LOTE' for c in df.columns if c.strip() == 'LOTE'})
        df = df.rename(columns={'CODIGO': 'COD'})
        df['cod_produto'] = df['COD'].apply(_norm_cod)
        df = df[df['cod_produto'].str.isdigit()]
        df['lote'] = df['LOTE'].apply(_norm_lote)
        df['qtd'] = pd.to_numeric(df['QTD'], errors='coerce').fillna(0)
        df['filial'] = filial
        df['company_id'] = COMPANY_ID[filial]
        out.append(df[['company_id', 'filial', 'cod_produto', 'lote', 'qtd']])
    return pd.concat(out, ignore_index=True)


# ==========================================================
# SOT: ODOO SNAPSHOT
# ==========================================================
def carregar_sot_odoo():
    out = []
    for filial in ['FB', 'LF', 'CD']:
        path = os.path.join(INVENTARIO_DIR, f'estoque-odoo-{filial}.xlsx')
        df = pd.read_excel(path)
        df['cod_produto'] = df['cod_produto'].apply(_norm_cod)
        df['lote'] = df['lot_name'].apply(_norm_lote)
        df['qtd'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        df['valor'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)
        df['filial'] = filial
        df['company_id'] = COMPANY_ID[filial]
        df['location_name'] = df['location_name'].fillna('')
        out.append(df[['company_id', 'filial', 'cod_produto', 'lote', 'qtd', 'valor', 'location_name']])
    return pd.concat(out, ignore_index=True)


# ==========================================================
# DIFFS ORIGINAIS
# ==========================================================
def carregar_diffs():
    """Carrega diff-inv-vs-odoo-{FB,LF,CD}.xlsx.

    Estrutura tipica (a verificar): cod_produto, lote, qtd_inv, qtd_odoo, diff.
    """
    out = []
    abas_info = []
    for filial in ['FB', 'LF', 'CD']:
        path = os.path.join(INVENTARIO_DIR, f'diff-inv-vs-odoo-{filial}.xlsx')
        if not os.path.exists(path):
            continue
        xl = pd.ExcelFile(path)
        for sheet in xl.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            abas_info.append({'filial': filial, 'aba': sheet, 'n_linhas': len(df), 'colunas': list(df.columns)})
            df['_filial'] = filial
            df['_aba'] = sheet
            df['_company_id'] = COMPANY_ID[filial]
            out.append(df)
    return out, pd.DataFrame(abas_info)


# ==========================================================
# PLANO CD
# ==========================================================
def carregar_plano_cd():
    path = os.path.join(RELATORIOS_DIR, 'plano-pre-etapa-cd.xlsx')
    if not os.path.exists(path):
        return {}, pd.DataFrame()
    xl = pd.ExcelFile(path)
    abas = {}
    info = []
    for sheet in xl.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet)
        abas[sheet] = df
        info.append({'aba': sheet, 'n_linhas': len(df), 'colunas': list(df.columns)})
    return abas, pd.DataFrame(info)


# ==========================================================
# TABELA SISTEMA
# ==========================================================
def carregar_tabela():
    from app import create_app, db
    app = create_app()
    with app.app_context():
        rows = db.session.execute(db.text("""
            SELECT id, company_id, cod_produto,
                   COALESCE(lote_inventariado, '') AS lote_inv,
                   COALESCE(lote_odoo, '') AS lote_odoo,
                   COALESCE(lote_origem, '') AS lote_origem,
                   COALESCE(lote_destino, '') AS lote_destino,
                   qtd_inventario::float AS qtd_inventario,
                   qtd_odoo::float AS qtd_odoo,
                   qtd_ajuste::float AS qtd_ajuste,
                   COALESCE(custo_medio, 0)::float AS custo_medio,
                   acao_decidida, status, fase_pipeline, criado_por,
                   criado_em
            FROM ajuste_estoque_inventario
            WHERE ciclo='INVENTARIO_2026_05'
        """)).mappings().all()
    df = pd.DataFrame(rows)
    df['cod_produto'] = df['cod_produto'].apply(_norm_cod)
    for c in ['lote_inv', 'lote_odoo', 'lote_origem', 'lote_destino']:
        df[c] = df[c].apply(_norm_lote)
    df['valor_ajuste'] = df['qtd_ajuste'] * df['custo_medio']
    return df


# ==========================================================
# COMPARACOES
# ==========================================================
def visao_por_cod_produto(sot_inv, sot_odoo, tabela, diffs_list):
    """Agrega TUDO por (company_id, cod_produto) — ignora lote.

    Esta e' a comparacao mais ROBUSTA porque RENOMEAR_LOTE/TRANSFERIR mudam
    o lote mas mantem o cod_produto.
    """
    # SOT INV
    inv = sot_inv.groupby(['company_id', 'cod_produto'], as_index=False)['qtd'].sum()
    inv = inv.rename(columns={'qtd': 'qtd_inv'})

    # SOT ODOO
    odoo = sot_odoo.groupby(['company_id', 'cod_produto'], as_index=False).agg(
        qtd_odoo=('qtd', 'sum'),
        valor_odoo=('valor', 'sum')
    )
    odoo['custo_unit_medio'] = np.where(odoo['qtd_odoo'] != 0, odoo['valor_odoo'] / odoo['qtd_odoo'], 0)

    # TABELA agregada por cod_produto (qtd_ajuste liquido)
    # Excluir CANCELADO
    tab_ativa = tabela[tabela['status'] != 'CANCELADO'].copy()
    tab_g = tab_ativa.groupby(['company_id', 'cod_produto'], as_index=False).agg(
        tab_qtd_ajuste=('qtd_ajuste', 'sum'),
        tab_valor=('valor_ajuste', 'sum'),
        tab_n=('id', 'count'),
        tab_status=('status', lambda s: ','.join(sorted(set(s)))),
        tab_acoes=('acao_decidida', lambda s: ','.join(sorted(set(s))))
    )

    # DIFFS originais agregados
    diffs_g_list = []
    for df in diffs_list:
        # Tentar identificar colunas
        df = df.copy()
        # Procurar coluna cod_produto
        cod_col = None
        for c in df.columns:
            cl = str(c).lower()
            if 'cod_produto' in cl or 'codigo' in cl or cl == 'cod':
                cod_col = c
                break
        if not cod_col:
            continue
        qty_inv_col = None
        qty_odoo_col = None
        diff_col = None
        for c in df.columns:
            cl = str(c).lower()
            if 'qtd_inv' in cl or 'qty_inv' in cl or 'inv_qtd' in cl:
                qty_inv_col = c
            if 'qtd_odoo' in cl or 'qty_odoo' in cl or 'odoo_qtd' in cl or 'qty_total_odoo' in cl:
                qty_odoo_col = c
            if cl in ('diff', 'diferenca', 'delta', 'diff_qtd', 'diff_total'):
                diff_col = c
        if not (qty_inv_col or qty_odoo_col or diff_col):
            continue
        df['_cod'] = df[cod_col].apply(_norm_cod)
        df = df[df['_cod'].str.isdigit()]
        cid = df['_company_id'].iloc[0] if len(df) else 0
        agg_dict = {}
        if qty_inv_col:
            df[qty_inv_col] = pd.to_numeric(df[qty_inv_col], errors='coerce').fillna(0)
            agg_dict['diff_qtd_inv'] = (qty_inv_col, 'sum')
        if qty_odoo_col:
            df[qty_odoo_col] = pd.to_numeric(df[qty_odoo_col], errors='coerce').fillna(0)
            agg_dict['diff_qtd_odoo'] = (qty_odoo_col, 'sum')
        if diff_col:
            df[diff_col] = pd.to_numeric(df[diff_col], errors='coerce').fillna(0)
            agg_dict['diff_delta'] = (diff_col, 'sum')
        ag = df.groupby('_cod', as_index=False).agg(**agg_dict)
        ag['company_id'] = cid
        ag = ag.rename(columns={'_cod': 'cod_produto'})
        diffs_g_list.append(ag)
    if diffs_g_list:
        diffs_g = pd.concat(diffs_g_list, ignore_index=True)
        # Consolidar duplicatas (cada filial tem multi-aba)
        diffs_g = diffs_g.groupby(['company_id', 'cod_produto'], as_index=False).sum(numeric_only=True)
    else:
        diffs_g = pd.DataFrame(columns=['company_id', 'cod_produto'])

    # MERGE TUDO
    j = inv.merge(odoo, on=['company_id', 'cod_produto'], how='outer')
    j = j.merge(tab_g, on=['company_id', 'cod_produto'], how='outer')
    j = j.merge(diffs_g, on=['company_id', 'cod_produto'], how='outer')

    # Preencher NaN
    num_cols = ['qtd_inv', 'qtd_odoo', 'valor_odoo', 'custo_unit_medio',
                'tab_qtd_ajuste', 'tab_valor', 'tab_n']
    for c in num_cols:
        if c in j.columns:
            j[c] = j[c].fillna(0)
    if 'tab_status' in j.columns:
        j['tab_status'] = j['tab_status'].fillna('')
    if 'tab_acoes' in j.columns:
        j['tab_acoes'] = j['tab_acoes'].fillna('')

    # Calculos chave
    j['SOT_diff'] = j['qtd_inv'] - j['qtd_odoo']
    j['SOT_valor_diff'] = j['SOT_diff'] * j['custo_unit_medio']
    j['delta_tab_vs_sot'] = j['tab_qtd_ajuste'] - j['SOT_diff']
    j['delta_valor'] = j['delta_tab_vs_sot'] * j['custo_unit_medio']
    j['filial'] = j['company_id'].map(COMPANY_NAME).fillna('?')

    def classificar(row):
        tol = 0.01
        sot_zero = abs(row['SOT_diff']) < tol
        tab_zero = abs(row['tab_qtd_ajuste']) < tol
        delta = abs(row['delta_tab_vs_sot'])
        if sot_zero and tab_zero:
            return 'OK_SEM_AJUSTE'
        if delta < tol:
            return 'OK'
        if delta / max(abs(row['SOT_diff']), 1.0) < 0.01:  # 1% de tolerancia
            return 'OK_TOLERANCIA'
        if sot_zero:
            return 'TABELA_EXTRA'
        if tab_zero:
            return 'TABELA_FALTANDO'
        # mesmo sinal: divergente quantitativo
        if row['SOT_diff'] * row['tab_qtd_ajuste'] > 0:
            return 'TABELA_DIVERGENTE_MESMO_SINAL'
        return 'TABELA_DIVERGENTE_SINAL_INVERSO'
    j['categoria'] = j.apply(classificar, axis=1)

    return j


# ==========================================================
# MAIN
# ==========================================================
def main():
    print('=' * 70)
    print('AUDITORIA COMPLETA SOT vs FONTES — INVENTARIO 2026-05')
    print('=' * 70)

    print('\n[1] Carregando SOT inventario fisico...')
    sot_inv = carregar_sot_inv()
    print(f'   {len(sot_inv)} linhas')

    print('\n[2] Carregando SOT Odoo snapshot...')
    sot_odoo = carregar_sot_odoo()
    print(f'   {len(sot_odoo)} linhas')

    print('\n[3] Carregando diffs originais...')
    diffs_list, abas_diffs = carregar_diffs()
    print(f'   {len(diffs_list)} abas | {sum(len(d) for d in diffs_list)} linhas')

    print('\n[4] Carregando plano-pre-etapa-cd...')
    plano_abas, abas_plano = carregar_plano_cd()
    print(f'   {len(plano_abas)} abas')

    print('\n[5] Carregando tabela ajuste_estoque_inventario...')
    tabela = carregar_tabela()
    print(f'   {len(tabela)} ajustes')

    print('\n[6] Computando visao por cod_produto (MACRO)...')
    macro = visao_por_cod_produto(sot_inv, sot_odoo, tabela, diffs_list)

    # ====== RESUMO POR FILIAL (visao macro) ======
    resumo_macro = macro.groupby(['filial', 'company_id'], as_index=False).agg(
        n_produtos=('cod_produto', 'count'),
        sot_total_inv=('qtd_inv', 'sum'),
        sot_total_odoo=('qtd_odoo', 'sum'),
        sot_diff_total=('SOT_diff', 'sum'),
        sot_valor_diff=('SOT_valor_diff', 'sum'),
        tab_total_ajuste=('tab_qtd_ajuste', 'sum'),
        tab_valor=('tab_valor', 'sum'),
        delta_qtd=('delta_tab_vs_sot', 'sum'),
        delta_valor=('delta_valor', 'sum')
    )

    # ====== CATEGORIAS ======
    cat = macro.groupby(['filial', 'categoria'], as_index=False).agg(
        n=('cod_produto', 'count'),
        sot_diff_qtd=('SOT_diff', 'sum'),
        sot_valor=('SOT_valor_diff', 'sum'),
        tab_qtd=('tab_qtd_ajuste', 'sum'),
        delta_valor=('delta_valor', 'sum')
    )

    # ====== DIVERGENCIAS RELEVANTES ======
    div = macro[macro['categoria'].isin([
        'TABELA_EXTRA', 'TABELA_FALTANDO',
        'TABELA_DIVERGENTE_MESMO_SINAL', 'TABELA_DIVERGENTE_SINAL_INVERSO'
    ])].copy()
    div['abs_valor'] = div['delta_valor'].abs()
    div = div.sort_values('abs_valor', ascending=False)

    # ====== Ja existe diff coluna? Comparar com SOT_diff
    if 'diff_qtd_inv' in macro.columns and 'diff_qtd_odoo' in macro.columns:
        macro['diff_sot_vs_diff_planilha'] = macro['SOT_diff'] - (
            macro['diff_qtd_inv'].fillna(0) - macro['diff_qtd_odoo'].fillna(0)
        )
    elif 'diff_delta' in macro.columns:
        macro['diff_sot_vs_diff_planilha'] = macro['SOT_diff'] - macro['diff_delta'].fillna(0)

    # ====== ESCREVER EXCEL ======
    os.makedirs(RELATORIOS_DIR, exist_ok=True)
    print(f'\n[7] Escrevendo Excel em {OUT_PATH}...')
    with pd.ExcelWriter(OUT_PATH, engine='xlsxwriter') as writer:
        # README
        readme = pd.DataFrame([
            ['Data', '2026-05-18'],
            ['Hora', pd.Timestamp.now().strftime('%H:%M')],
            ['SOT-INV', 'COMPILADO INV. 16.05.2026.xlsx (sabado, fisico)'],
            ['SOT-ODOO', 'estoque-odoo-{FB,LF,CD}.xlsx (domingo 21:44, pre-execucoes)'],
            ['Granularidade', 'POR cod_produto (ignora lote — robusto contra RENOMEAR/TRANSFERIR)'],
            ['SOT_diff', 'qtd_inv - qtd_odoo (positivo=falta entrar; negativo=falta sair)'],
            ['delta_tab_vs_sot', 'tab_qtd_ajuste - SOT_diff (~0 = OK; !=0 = problema)'],
            ['Categorias', 'OK | OK_TOLERANCIA | OK_SEM_AJUSTE | TABELA_EXTRA | TABELA_FALTANDO | TABELA_DIVERGENTE_*'],
            ['Notas', 'Pre-etapa CD (D007) sao transferencias internas (qtd=0). Nao contam como ajuste real.'],
        ], columns=['Campo', 'Valor'])
        readme.to_excel(writer, sheet_name='README', index=False)

        # Resumo macro por filial
        resumo_macro.to_excel(writer, sheet_name='1_Resumo_Macro', index=False)

        # Categorias
        cat.to_excel(writer, sheet_name='2_Categorias', index=False)

        # Macro completo
        cols_macro = ['company_id', 'filial', 'cod_produto',
                      'qtd_inv', 'qtd_odoo', 'SOT_diff', 'custo_unit_medio', 'SOT_valor_diff',
                      'tab_qtd_ajuste', 'tab_valor', 'tab_n', 'tab_acoes', 'tab_status',
                      'delta_tab_vs_sot', 'delta_valor', 'categoria']
        # incluir diff cols se existem
        for c in ['diff_qtd_inv', 'diff_qtd_odoo', 'diff_delta', 'diff_sot_vs_diff_planilha']:
            if c in macro.columns:
                cols_macro.append(c)
        macro[cols_macro].sort_values(['company_id', 'cod_produto']).to_excel(
            writer, sheet_name='3_Macro_TODOS', index=False
        )

        # Divergencias por valor decrescente
        div_cols = ['company_id', 'filial', 'cod_produto',
                    'qtd_inv', 'qtd_odoo', 'SOT_diff', 'SOT_valor_diff',
                    'tab_qtd_ajuste', 'tab_valor', 'tab_acoes', 'tab_status',
                    'delta_tab_vs_sot', 'delta_valor', 'categoria']
        div[div_cols].head(500).to_excel(writer, sheet_name='4_Top500_Divergencias', index=False)

        # Inventario das abas dos diffs
        if len(abas_diffs):
            abas_diffs['colunas'] = abas_diffs['colunas'].apply(lambda x: ', '.join(map(str, x)))
            abas_diffs.to_excel(writer, sheet_name='5_Diffs_Abas_Info', index=False)

        # Inventario das abas do plano CD
        if len(abas_plano):
            abas_plano['colunas'] = abas_plano['colunas'].apply(lambda x: ', '.join(map(str, x)))
            abas_plano.to_excel(writer, sheet_name='6_Plano_CD_Abas', index=False)

        # Top 100 ajustes na tabela por valor absoluto
        top_tab = tabela.copy()
        top_tab['abs_v'] = top_tab['valor_ajuste'].abs()
        top_tab = top_tab.sort_values('abs_v', ascending=False).head(100)
        top_tab[['id', 'company_id', 'cod_produto', 'lote_inv', 'lote_odoo',
                 'qtd_ajuste', 'custo_medio', 'valor_ajuste',
                 'acao_decidida', 'status', 'criado_por']].to_excel(
            writer, sheet_name='7_Top100_Ajustes_Tabela', index=False
        )

    print(f'\nOK. Arquivo gerado: {OUT_PATH}')

    print('\n' + '=' * 70)
    print('RESUMO MACRO POR FILIAL (visao por cod_produto)')
    print('=' * 70)
    print(resumo_macro.to_string(index=False, float_format=lambda x: f'{x:>15,.0f}'))

    print('\n' + '=' * 70)
    print('CATEGORIAS')
    print('=' * 70)
    print(cat.to_string(index=False, float_format=lambda x: f'{x:>15,.0f}'))

    # Comparacao SOT_diff vs diff_planilha (se existe)
    if 'diff_sot_vs_diff_planilha' in macro.columns:
        print('\n' + '=' * 70)
        print('SOT_diff vs DIFF nas PLANILHAS DIFFS (delta agregado)')
        print('=' * 70)
        cmp = macro.groupby('filial', as_index=False).agg(
            sot_diff=('SOT_diff', 'sum'),
            diff_pl_agg=('diff_sot_vs_diff_planilha', 'sum')
        )
        print(cmp.to_string(index=False, float_format=lambda x: f'{x:>15,.0f}'))

    print('\nFim.')


if __name__ == '__main__':
    main()
