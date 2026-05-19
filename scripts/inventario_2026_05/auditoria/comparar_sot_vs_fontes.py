"""Compara SOT (inventario fisico + Odoo snapshot 17/05 21:44) com as 3 fontes
derivadas: tabela ajuste_estoque_inventario, diffs originais, plano-pre-etapa-cd.

NAO MEXE NAS PLANILHAS ORIGINAIS. Gera novo Excel em
docs/inventario-2026-05/07-relatorios/COMPARACAO_SOT_2026_05_18.xlsx

Premissas:
- SOT-INV: COMPILADO INV. 16.05.2026.xlsx (3 abas FB, LF, CD) - inventario fisico sabado 16/05
- SOT-ODOO: estoque-odoo-{FB,LF,CD}.xlsx - snapshot Odoo domingo 17/05 21:44 PRE-execucoes
- Tabela: ajuste_estoque_inventario WHERE ciclo='INVENTARIO_2026_05'
- Diffs: diff-inv-vs-odoo-{FB,LF,CD}.xlsx (gerados 17/05 23:18)
- Plano CD: plano-pre-etapa-cd.xlsx (D007 executado 18/05 madrugada)

Companies: FB=1, CD=4, LF=5
"""
import os
import sys
import argparse
import pandas as pd
import numpy as np
from decimal import Decimal
from collections import defaultdict

# Path setup para imports do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

INVENTARIO_DIR = '/mnt/c/Users/rafael.nascimento/Downloads/INVENTARIO 16-05-26'
RELATORIOS_DIR = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/07-relatorios'
OUT_PATH = os.path.join(RELATORIOS_DIR, 'COMPARACAO_SOT_2026_05_18.xlsx')

COMPANY_ID = {'FB': 1, 'CD': 4, 'LF': 5}
COMPANY_NAME = {1: 'FB', 4: 'CD', 5: 'LF'}


def _norm_lote(x):
    """Normaliza lote para chave (string, sem espacos, sem .0 de int convertido para float)."""
    if x is None:
        return ''
    if isinstance(x, float):
        if pd.isna(x):
            return ''
        # int float -> int -> str
        if x == int(x):
            return str(int(x))
        return str(x)
    if isinstance(x, int):
        return str(x)
    return str(x).strip()


def _norm_cod(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ''
    if isinstance(x, float) and x == int(x):
        return str(int(x))
    if isinstance(x, int):
        return str(x)
    s = str(x).strip()
    # remove .0 de float-string
    if s.endswith('.0'):
        s = s[:-2]
    return s


# ============================================================
# 1. SOT INVENTARIO FISICO
# ============================================================
def carregar_sot_inventario():
    """Carrega COMPILADO INV e agrega por (filial, cod, lote)."""
    path = os.path.join(INVENTARIO_DIR, 'COMPILADO INV. 16.05.2026.xlsx')
    out = []
    for filial in ['FB', 'LF', 'CD']:
        df = pd.read_excel(path, sheet_name=filial)
        df.columns = [c.strip().upper() for c in df.columns]
        # Normalizar nome da coluna LOTE (FB tem 'LOTE ' com espaco)
        df = df.rename(columns={c: 'LOTE' for c in df.columns if c.strip() == 'LOTE'})
        df = df.rename(columns={'CODIGO': 'COD'})
        # Filtrar outliers cod nao-digito
        df['COD_STR'] = df['COD'].apply(_norm_cod)
        df = df[df['COD_STR'].str.isdigit()]
        df['LOTE_STR'] = df['LOTE'].apply(_norm_lote)
        df['QTD_N'] = pd.to_numeric(df['QTD'], errors='coerce').fillna(0)
        ag = df.groupby(['COD_STR', 'LOTE_STR'], as_index=False)['QTD_N'].sum()
        ag['filial'] = filial
        ag['company_id'] = COMPANY_ID[filial]
        ag = ag.rename(columns={'COD_STR': 'cod_produto', 'LOTE_STR': 'lote', 'QTD_N': 'qtd_inv'})
        out.append(ag)
    df_all = pd.concat(out, ignore_index=True)
    print(f'SOT INV: {len(df_all)} pares (filial, cod, lote) | total qtd = {df_all["qtd_inv"].sum():.0f}')
    return df_all


# ============================================================
# 2. SOT ODOO SNAPSHOT
# ============================================================
def carregar_sot_odoo():
    """Carrega estoque-odoo-{FB,LF,CD} e agrega por (filial, cod, lote).

    Importante: usa apenas locations 'internos' (Estoque + sub-areas + Linhas + Pre-Producao + Sala).
    NAO inclui virtual locations (Producao, Adjustments, etc.) - estes nao sao 'estoque real'.
    Pelo padrao Odoo, snapshot inclui location_id de estoque (8 FB, 32 CD, 42 LF) e filhos.
    """
    out = []
    for filial in ['FB', 'LF', 'CD']:
        path = os.path.join(INVENTARIO_DIR, f'estoque-odoo-{filial}.xlsx')
        df = pd.read_excel(path)
        df['COD_STR'] = df['cod_produto'].apply(_norm_cod)
        df['LOTE_STR'] = df['lot_name'].apply(_norm_lote)
        df['QTD_N'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        df['VALOR_N'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)
        # custo unitario medio ponderado (proxy)
        ag = df.groupby(['COD_STR', 'LOTE_STR'], as_index=False).agg(
            qtd_odoo=('QTD_N', 'sum'),
            valor_odoo=('VALOR_N', 'sum')
        )
        ag['filial'] = filial
        ag['company_id'] = COMPANY_ID[filial]
        ag = ag.rename(columns={'COD_STR': 'cod_produto', 'LOTE_STR': 'lote'})
        ag['custo_unit'] = np.where(ag['qtd_odoo'] != 0, ag['valor_odoo'] / ag['qtd_odoo'], 0)
        out.append(ag)
    df_all = pd.concat(out, ignore_index=True)
    print(f'SOT ODOO: {len(df_all)} pares (filial, cod, lote) | total qtd = {df_all["qtd_odoo"].sum():.0f}')
    return df_all


# ============================================================
# 3. CALCULAR DIFF REAL (SOT)
# ============================================================
def calcular_diff_sot(sot_inv, sot_odoo):
    """Full outer join INV x ODOO por (company, cod, lote).

    diff = qtd_inv - qtd_odoo (positivo = entrar; negativo = sair)
    """
    df = pd.merge(
        sot_inv[['company_id', 'filial', 'cod_produto', 'lote', 'qtd_inv']],
        sot_odoo[['company_id', 'cod_produto', 'lote', 'qtd_odoo', 'custo_unit']],
        on=['company_id', 'cod_produto', 'lote'],
        how='outer'
    )
    df['qtd_inv'] = df['qtd_inv'].fillna(0)
    df['qtd_odoo'] = df['qtd_odoo'].fillna(0)
    df['custo_unit'] = df['custo_unit'].fillna(0)
    # filial pode estar NaN se veio so do Odoo
    df['filial'] = df.apply(
        lambda r: r['filial'] if pd.notna(r['filial']) else COMPANY_NAME.get(r['company_id'], '?'),
        axis=1
    )
    df['diff_sot'] = df['qtd_inv'] - df['qtd_odoo']
    df['valor_diff_sot'] = df['diff_sot'] * df['custo_unit']
    df['situacao_lote'] = np.where(
        (df['qtd_inv'] != 0) & (df['qtd_odoo'] != 0), 'AMBOS',
        np.where(df['qtd_inv'] != 0, 'SO_INV', 'SO_ODOO')
    )
    return df


# ============================================================
# 4. CARREGAR TABELA SISTEMA
# ============================================================
def carregar_tabela_sistema():
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
                   acao_decidida, status, fase_pipeline, criado_por
            FROM ajuste_estoque_inventario
            WHERE ciclo='INVENTARIO_2026_05'
        """)).mappings().all()
    df = pd.DataFrame(rows)
    df['cod_produto'] = df['cod_produto'].apply(_norm_cod)
    for c in ['lote_inv', 'lote_odoo', 'lote_origem', 'lote_destino']:
        df[c] = df[c].apply(_norm_lote)
    df['valor_ajuste'] = df['qtd_ajuste'] * df['custo_medio']
    print(f'TABELA: {len(df)} ajustes carregados')
    return df


# ============================================================
# 5. CARREGAR DIFFS ORIGINAIS
# ============================================================
def carregar_diffs():
    out = []
    for filial in ['FB', 'LF', 'CD']:
        path = os.path.join(INVENTARIO_DIR, f'diff-inv-vs-odoo-{filial}.xlsx')
        if not os.path.exists(path):
            continue
        # Carregar todas as abas
        xl = pd.ExcelFile(path)
        for sheet in xl.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            df['_filial'] = filial
            df['_aba'] = sheet
            out.append(df)
    return out


# ============================================================
# 6. CARREGAR PLANO CD
# ============================================================
def carregar_plano_cd():
    path = os.path.join(RELATORIOS_DIR, 'plano-pre-etapa-cd.xlsx')
    xl = pd.ExcelFile(path)
    abas = {}
    for sheet in xl.sheet_names:
        abas[sheet] = pd.read_excel(path, sheet_name=sheet)
    return abas


# ============================================================
# 7. AGREGADOR DA TABELA POR (company, cod, lote)
# ============================================================
def agregar_tabela_por_lote(tab):
    """Agrega tabela por (company_id, cod_produto, lote_inv) e (company_id, cod_produto, lote_odoo).

    Para cada ajuste:
    - lote_inv (lote alvo, do inventario fisico) -> qtd_ajuste positivo entra ali (se positivo)
    - lote_odoo (lote origem) -> qtd_ajuste negativo sai dali (se negativo)

    Mas a interpretacao depende da acao:
    - RENOMEAR_LOTE: qtd_ajuste=0 (so muda nome do lote: lote_origem -> lote_destino)
    - TRANSFERIR_X_Y: muda filial. Em cada filial o ajuste e' diferente.
    - INDISPONIBILIZAR_LOTE/LOCAL: tira do estoque ativo
    - PERDA_LF_FB / DEV_LF_FB: saida LF + entrada FB (mas tabela mostra so uma linha por filial)
    - INDUSTRIALIZACAO_FB_LF: saida FB + entrada LF

    Para simplificar: somar qtd_ajuste (saldo liquido) e qualificar por status.
    """
    excluir = ['CANCELADO']  # FALHA mantem (ainda nao executou mas foi proposto)
    df = tab[~tab['status'].isin(excluir)].copy()

    # Considerar EXECUTADO + APROVADO + PROPOSTO + FALHA como "demanda ativa"
    # Agrupar por (company, cod, lote_inv) - o lote do INVENTARIO
    g_inv = df.groupby(['company_id', 'cod_produto', 'lote_inv'], as_index=False).agg(
        qtd_ajuste_tab=('qtd_ajuste', 'sum'),
        valor_ajuste_tab=('valor_ajuste', 'sum'),
        n_ajustes=('id', 'count'),
        acoes=('acao_decidida', lambda s: ','.join(sorted(set(s)))),
        statuses=('status', lambda s: ','.join(sorted(set(s))))
    )
    g_inv = g_inv.rename(columns={'lote_inv': 'lote'})
    return g_inv


# ============================================================
# MAIN
# ============================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--companies', default='1,4,5', help='Filtro company_id')
    args = ap.parse_args()

    print('=' * 70)
    print('AUDITORIA SOT vs FONTES DERIVADAS — INVENTARIO 2026-05')
    print('=' * 70)

    print('\n[1/5] Carregando SOT inventario fisico...')
    sot_inv = carregar_sot_inventario()

    print('\n[2/5] Carregando SOT Odoo snapshot...')
    sot_odoo = carregar_sot_odoo()

    print('\n[3/5] Calculando diff real (SOT)...')
    diff_sot = calcular_diff_sot(sot_inv, sot_odoo)

    print('\n[4/5] Carregando tabela ajuste_estoque_inventario...')
    tabela = carregar_tabela_sistema()
    tab_ag = agregar_tabela_por_lote(tabela)

    # Resumo executivo por filial
    print('\n[5/5] Comparando SOT vs Tabela...')
    resumo = []
    for cid in [1, 4, 5]:
        d_sot = diff_sot[diff_sot['company_id'] == cid]
        d_tab = tab_ag[tab_ag['company_id'] == cid]
        resumo.append({
            'filial': COMPANY_NAME[cid],
            'company_id': cid,
            'sot_n_lotes': len(d_sot),
            'sot_qtd_inv': d_sot['qtd_inv'].sum(),
            'sot_qtd_odoo': d_sot['qtd_odoo'].sum(),
            'sot_diff_liquido': d_sot['diff_sot'].sum(),
            'sot_valor_diff': d_sot['valor_diff_sot'].sum(),
            'sot_so_inv_n': (d_sot['situacao_lote'] == 'SO_INV').sum(),
            'sot_so_odoo_n': (d_sot['situacao_lote'] == 'SO_ODOO').sum(),
            'sot_ambos_n': (d_sot['situacao_lote'] == 'AMBOS').sum(),
            'tab_n_ajustes': d_tab['n_ajustes'].sum() if not d_tab.empty else 0,
            'tab_qtd_ajuste': d_tab['qtd_ajuste_tab'].sum() if not d_tab.empty else 0,
            'tab_valor_ajuste': d_tab['valor_ajuste_tab'].sum() if not d_tab.empty else 0,
        })
    df_resumo = pd.DataFrame(resumo)

    # JOIN diff_sot x tab_ag por (company, cod, lote)
    join = pd.merge(
        diff_sot[['company_id', 'filial', 'cod_produto', 'lote', 'qtd_inv', 'qtd_odoo',
                  'diff_sot', 'custo_unit', 'valor_diff_sot', 'situacao_lote']],
        tab_ag,
        on=['company_id', 'cod_produto', 'lote'],
        how='outer'
    )
    join['filial'] = join.apply(
        lambda r: r['filial'] if pd.notna(r['filial']) else COMPANY_NAME.get(r['company_id'], '?'),
        axis=1
    )
    for col in ['qtd_inv', 'qtd_odoo', 'diff_sot', 'valor_diff_sot',
                'qtd_ajuste_tab', 'valor_ajuste_tab', 'n_ajustes']:
        if col in join.columns:
            join[col] = join[col].fillna(0)
    join['delta_tab_vs_sot'] = join['qtd_ajuste_tab'] - join['diff_sot']
    join['valor_delta'] = join['delta_tab_vs_sot'] * join['custo_unit']

    # Categorizar:
    # OK = delta proximo de 0 (tolerancia 0.01)
    # FALTANDO = SOT tem diff mas tabela nao tem ajuste correspondente
    # EXCESSO = tabela tem ajuste sem diff SOT
    # ERRADO = ambos existem mas qtd diferente
    def categorizar(row):
        tol = 0.01
        sot_zero = abs(row['diff_sot']) < tol
        tab_zero = abs(row['qtd_ajuste_tab']) < tol
        if sot_zero and tab_zero:
            return 'NENHUM_AJUSTE_OK'
        if abs(row['delta_tab_vs_sot']) < tol:
            return 'OK'
        if sot_zero and not tab_zero:
            return 'TABELA_EXTRA'
        if tab_zero and not sot_zero:
            return 'TABELA_FALTANDO'
        return 'TABELA_DIVERGENTE'
    join['categoria'] = join.apply(categorizar, axis=1)

    # Resumo por categoria
    cat_resumo = join.groupby(['filial', 'categoria'], as_index=False).agg(
        n=('cod_produto', 'count'),
        diff_sot_qtd=('diff_sot', 'sum'),
        tab_qtd=('qtd_ajuste_tab', 'sum'),
        delta=('delta_tab_vs_sot', 'sum'),
        valor_delta=('valor_delta', 'sum')
    )

    # Filtrar so divergencias relevantes
    divergencias = join[join['categoria'].isin(['TABELA_EXTRA', 'TABELA_FALTANDO', 'TABELA_DIVERGENTE'])].copy()
    divergencias = divergencias.sort_values('valor_delta', key=lambda s: s.abs(), ascending=False)

    # Top N por valor absoluto
    top50_divergencias = divergencias.head(200)

    # ============================================================
    # ESCREVER EXCEL
    # ============================================================
    os.makedirs(RELATORIOS_DIR, exist_ok=True)
    print(f'\nEscrevendo Excel em {OUT_PATH}...')
    with pd.ExcelWriter(OUT_PATH, engine='xlsxwriter') as writer:
        # Aba 1: README
        readme = pd.DataFrame([
            {'campo': 'Data analise', 'valor': '2026-05-18'},
            {'campo': 'Hora analise', 'valor': pd.Timestamp.now().strftime('%H:%M')},
            {'campo': 'SOT-INV', 'valor': 'COMPILADO INV. 16.05.2026.xlsx (3 abas FB, LF, CD) — inventario fisico sabado'},
            {'campo': 'SOT-ODOO', 'valor': 'estoque-odoo-{FB,LF,CD}.xlsx — snapshot Odoo 17/05 21:44 PRE-execucoes'},
            {'campo': 'Tabela', 'valor': 'ajuste_estoque_inventario WHERE ciclo=INVENTARIO_2026_05'},
            {'campo': 'Criterio', 'valor': 'diff_sot = qtd_inv - qtd_odoo (positivo=entrar, negativo=sair)'},
            {'campo': 'Categorias', 'valor': 'OK | TABELA_EXTRA | TABELA_FALTANDO | TABELA_DIVERGENTE | NENHUM_AJUSTE_OK'},
            {'campo': 'Tolerancia', 'valor': '0.01 unidade'},
        ])
        readme.to_excel(writer, sheet_name='README', index=False)

        # Aba 2: Resumo por filial
        df_resumo.to_excel(writer, sheet_name='1_Resumo_Filial', index=False)

        # Aba 3: Resumo categorias
        cat_resumo.to_excel(writer, sheet_name='2_Categorias', index=False)

        # Aba 4: SOT real (diff calculado)
        diff_sot_out = diff_sot[['company_id', 'filial', 'cod_produto', 'lote',
                                  'qtd_inv', 'qtd_odoo', 'diff_sot', 'custo_unit',
                                  'valor_diff_sot', 'situacao_lote']]
        diff_sot_out.to_excel(writer, sheet_name='3_SOT_Diff_Real', index=False)

        # Aba 5: Tabela agregada
        tab_ag.to_excel(writer, sheet_name='4_Tabela_Agregada', index=False)

        # Aba 6: JOIN completo (SOT vs Tabela)
        join_out = join[['company_id', 'filial', 'cod_produto', 'lote',
                         'qtd_inv', 'qtd_odoo', 'diff_sot', 'custo_unit', 'valor_diff_sot',
                         'qtd_ajuste_tab', 'valor_ajuste_tab', 'n_ajustes',
                         'acoes', 'statuses', 'delta_tab_vs_sot', 'valor_delta', 'categoria']]
        join_out.to_excel(writer, sheet_name='5_SOT_vs_Tabela_FULL', index=False)

        # Aba 7: Top 200 divergencias por valor
        top50_divergencias[['company_id', 'filial', 'cod_produto', 'lote',
                            'qtd_inv', 'qtd_odoo', 'diff_sot',
                            'qtd_ajuste_tab', 'delta_tab_vs_sot', 'valor_delta',
                            'acoes', 'statuses', 'categoria']].to_excel(
            writer, sheet_name='6_TOP200_Divergencias', index=False
        )

    print(f'\nOK. Arquivo: {OUT_PATH}')
    print('\n=== RESUMO ===')
    print(df_resumo.to_string(index=False))
    print('\n=== CATEGORIAS ===')
    print(cat_resumo.to_string(index=False))


if __name__ == '__main__':
    main()
