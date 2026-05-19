"""Auditoria com LOTES + regras de negocio do Rafael (2026-05-18).

REGRAS POR FILIAL:

LF (company_id=5):
  - Apenas NF FB<->LF
  - LF nao pode ter lote MIGRACAO
  - POSITIVO (inv > Odoo): NF FB -> LF
  - NEGATIVO (Odoo > inv): NF LF -> FB

CD (company_id=4):
  - POSITIVO: cascata
    1. rename lote (lote_odoo -> lote_inv) se sum_cod bate
    2. transf de MIGRACAO_CD para lote_inv (intra-CD)
    3. transf de qualquer lote_FB para lote_inv (cross-company FB->CD)
    4. ajuste positivo puro
  - NEGATIVO: rename lote_odoo -> MIGRACAO_CD

FB (company_id=1):
  - POSITIVO: cascata
    1. rename lote
    2. transf de MIGRACAO_CD para FB (cross-company CD->FB)
    3. ajuste positivo
  - NEGATIVO: rename lote -> MIGRACAO_FB

ORDEM: CD primeiro (cria MIGRACAO_CD), depois FB usa.

COBERTURA:
- Item Odoo SEM inv → ajuste negativo conforme regra da filial
- Item inv SEM Odoo → ajuste positivo conforme cascata da filial

Output: docs/inventario-2026-05/07-relatorios/RELATORIO_LOTES_SOT_2026_05_18.xlsx
"""
import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

INVENTARIO_DIR = '/mnt/c/Users/rafael.nascimento/Downloads/INVENTARIO 16-05-26'
RELATORIOS_DIR = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/07-relatorios'
OUT_PATH = os.path.join(RELATORIOS_DIR, 'RELATORIO_LOTES_SOT_2026_05_18.xlsx')

COMPANY_ID = {'FB': 1, 'CD': 4, 'LF': 5}
COMPANY_NAME = {1: 'FB', 4: 'CD', 5: 'LF'}

LOTE_MIGRACAO = 'MIGRACAO'  # nome canonico — pode ter variantes "MIGRAÇÃO" etc.


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


def _is_migracao(lote):
    """Detecta lote MIGRACAO em qualquer variante (MIGRACAO, MIGRAÇÃO, MIG, etc.)."""
    if not lote:
        return False
    up = lote.upper().strip()
    return up in ('MIGRACAO', 'MIGRAÇÃO', 'MIGRACÃO', 'MIGRAÇAO', 'MIG')


# ==============================================================
# CARREGAR INV (com lote)
# ==============================================================
def carregar_inv():
    path = os.path.join(INVENTARIO_DIR, 'COMPILADO INV. 16.05.2026.xlsx')
    out = []
    for filial in ['FB', 'LF', 'CD']:
        df = pd.read_excel(path, sheet_name=filial)
        df.columns = [c.strip().upper() for c in df.columns]
        df = df.rename(columns={c: 'LOTE' for c in df.columns if c.strip() == 'LOTE'})
        df['cod_produto'] = df['CODIGO'].apply(_norm_cod)
        df = df[df['cod_produto'].str.isdigit()]
        df['lote'] = df['LOTE'].apply(_norm_lote)
        df['qtd'] = pd.to_numeric(df['QTD'], errors='coerce').fillna(0)
        df['filial'] = filial
        df['company_id'] = COMPANY_ID[filial]
        out.append(df[['company_id', 'filial', 'cod_produto', 'lote', 'qtd']])
    res = pd.concat(out, ignore_index=True)
    # agregar duplicatas (mesmo cod+lote+filial)
    res = res.groupby(['company_id', 'filial', 'cod_produto', 'lote'], as_index=False)['qtd'].sum()
    return res


# ==============================================================
# CARREGAR ODOO (com lote)
# ==============================================================
def carregar_odoo():
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
        out.append(df[['company_id', 'filial', 'cod_produto', 'lote', 'qtd', 'valor']])
    res = pd.concat(out, ignore_index=True)
    res = res.groupby(['company_id', 'filial', 'cod_produto', 'lote'], as_index=False).agg(
        qtd=('qtd', 'sum'), valor=('valor', 'sum')
    )
    return res


# ==============================================================
# CARREGAR TABELA SISTEMA
# ==============================================================
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
                   acao_decidida, status
            FROM ajuste_estoque_inventario
            WHERE ciclo='INVENTARIO_2026_05'
        """)).mappings().all()
    df = pd.DataFrame(rows)
    df['cod_produto'] = df['cod_produto'].apply(_norm_cod)
    for c in ['lote_inv', 'lote_odoo', 'lote_origem', 'lote_destino']:
        df[c] = df[c].apply(_norm_lote)
    df['valor_ajuste'] = df['qtd_ajuste'] * df['custo_medio']
    return df


# ==============================================================
# ALGORITMO: classificar acoes por (filial, cod, lote)
# ==============================================================
def classificar_acoes(inv, odoo):
    """
    Para cada (filial, cod):
      - Pareamento por lote: AMBOS (inv & odoo), SO_INV, SO_ODOO
      - Calculo do liquido (sum_inv - sum_odoo)
      - Decisao da ACAO por filial conforme regras
    """
    # ============ JOIN por (filial, cod, lote) ============
    j = pd.merge(
        inv.rename(columns={'qtd': 'qtd_inv'}),
        odoo.rename(columns={'qtd': 'qtd_odoo'}),
        on=['company_id', 'filial', 'cod_produto', 'lote'],
        how='outer'
    )
    j['qtd_inv'] = j['qtd_inv'].fillna(0)
    j['qtd_odoo'] = j['qtd_odoo'].fillna(0)
    j['valor'] = j['valor'].fillna(0)
    j['filial'] = j.apply(
        lambda r: r['filial'] if pd.notna(r['filial']) else COMPANY_NAME.get(r['company_id'], '?'),
        axis=1
    )
    j['custo_unit'] = np.where(j['qtd_odoo'] > 0, j['valor'] / j['qtd_odoo'], 0)
    j['diff_lote'] = j['qtd_inv'] - j['qtd_odoo']
    j['cobertura_lote'] = np.where(
        (j['qtd_inv'] > 0.001) & (j['qtd_odoo'] > 0.001), 'AMBOS',
        np.where(j['qtd_inv'] > 0.001, 'SO_INV', 'SO_ODOO')
    )
    j['lote_e_migracao'] = j['lote'].apply(_is_migracao)

    # ============ Agregado por (filial, cod) ============
    by_cod = j.groupby(['company_id', 'filial', 'cod_produto'], as_index=False).agg(
        sum_inv=('qtd_inv', 'sum'),
        sum_odoo=('qtd_odoo', 'sum'),
        sum_valor_odoo=('valor', 'sum')
    )
    by_cod['liquido'] = by_cod['sum_inv'] - by_cod['sum_odoo']
    by_cod['cu_medio'] = np.where(by_cod['sum_odoo'] > 0,
                                   by_cod['sum_valor_odoo'] / by_cod['sum_odoo'], 0)
    by_cod['valor_liquido'] = by_cod['liquido'] * by_cod['cu_medio']

    def cenario_macro(row):
        sm = abs(row['sum_inv'] - row['sum_odoo'])
        # tolerancia 0.001 (1 milesimo) — mesma sumatoria
        if sm < 0.001:
            if row['sum_inv'] < 0.001:
                return 'AMBOS_ZERO'
            return 'RENAME_OU_OK'  # quantidades batem; verificar lotes
        if row['liquido'] > 0:
            return 'POSITIVO_LIQUIDO'
        return 'NEGATIVO_LIQUIDO'
    by_cod['cenario'] = by_cod.apply(cenario_macro, axis=1)

    # ============ Decisao por linha (lote) ============
    def decidir_acao(row, cenario_cod):
        """Decide acao para este lote especifico conforme regras da filial."""
        filial = row['filial']
        cob = row['cobertura_lote']
        qtd_inv = row['qtd_inv']
        qtd_odoo = row['qtd_odoo']
        diff = row['diff_lote']
        eh_migr = row['lote_e_migracao']

        # Caso trivial: lote bate em quantidade
        if cob == 'AMBOS' and abs(diff) < 0.001:
            return 'OK_LOTE_BATE'

        # ===== LF =====
        if filial == 'LF':
            if eh_migr:
                return 'ERRO_LF_TEM_MIGRACAO'
            if cob == 'SO_INV':
                # falta no Odoo → entra via NF FB->LF
                return 'NF_FB_LF_ENTRADA'
            if cob == 'SO_ODOO':
                # sobra no Odoo → sai via NF LF->FB
                return 'NF_LF_FB_SAIDA'
            # AMBOS com diff
            if diff > 0:
                return 'NF_FB_LF_PARCIAL'
            return 'NF_LF_FB_PARCIAL'

        # ===== CD =====
        if filial == 'CD':
            if cob == 'SO_INV':
                # falta no Odoo neste lote → POSITIVO cascata
                if cenario_cod == 'RENAME_OU_OK':
                    return 'RENAME_LOTE_CD'  # outro lote tem sobra mesma qtd
                return 'POS_CASCATA_CD'  # 1.rename 2.MIGRACAO_CD 3.qualquer FB 4.ajuste pos
            if cob == 'SO_ODOO':
                # sobra no Odoo neste lote
                if eh_migr:
                    return 'NEG_LOTE_JA_E_MIGRACAO'  # ja esta em MIGRACAO, nada a fazer
                if cenario_cod == 'RENAME_OU_OK':
                    return 'RENAME_LOTE_CD'  # outro lote tem falta
                return 'NEG_RENAME_PARA_MIGRACAO_CD'
            # AMBOS com diff
            if diff > 0:
                return 'POS_CASCATA_CD_PARCIAL'
            return 'NEG_RENAME_PARA_MIGRACAO_CD_PARCIAL'

        # ===== FB =====
        if filial == 'FB':
            if cob == 'SO_INV':
                if cenario_cod == 'RENAME_OU_OK':
                    return 'RENAME_LOTE_FB'
                return 'POS_CASCATA_FB'  # 1.rename 2.MIGRACAO_CD->FB 3.ajuste pos
            if cob == 'SO_ODOO':
                if eh_migr:
                    return 'NEG_LOTE_JA_E_MIGRACAO'
                if cenario_cod == 'RENAME_OU_OK':
                    return 'RENAME_LOTE_FB'
                return 'NEG_RENAME_PARA_MIGRACAO_FB'
            if diff > 0:
                return 'POS_CASCATA_FB_PARCIAL'
            return 'NEG_RENAME_PARA_MIGRACAO_FB_PARCIAL'

        return 'INDEFINIDO'

    cenario_map = {(r['company_id'], r['cod_produto']): r['cenario']
                   for _, r in by_cod.iterrows()}
    j['cenario_cod'] = j.apply(
        lambda r: cenario_map.get((r['company_id'], r['cod_produto']), 'INDEFINIDO'),
        axis=1
    )
    j['acao_proposta'] = j.apply(
        lambda r: decidir_acao(r, r['cenario_cod']),
        axis=1
    )
    j['valor_movimento'] = j['diff_lote'].abs() * j['custo_unit']

    return j, by_cod


# ==============================================================
# DISPONIBILIDADE DE MIGRACAO (CD e FB)
# ==============================================================
def disponibilidade_migracao(odoo):
    """Saldo atual do lote MIGRACAO no Odoo (pre-execucoes)."""
    odoo['eh_migr'] = odoo['lote'].apply(_is_migracao)
    mig = odoo[odoo['eh_migr']].copy()
    ag = mig.groupby(['filial', 'cod_produto'], as_index=False).agg(
        qtd_migracao=('qtd', 'sum'),
        valor_migracao=('valor', 'sum')
    )
    return ag


# ==============================================================
# COMPARAR COM TABELA SISTEMA (por filial+cod+lote)
# ==============================================================
def comparar_tabela(linhas_acao, tab):
    """Para cada linha proposta, busca na tabela do sistema se ja existe ajuste correspondente."""
    # Agregar tabela por (company, cod, lote_inv)
    tab_ativa = tab[tab['status'] != 'CANCELADO'].copy()
    # Tabela tem 2 visoes de lote: lote_inv (lote do inventario fisico) e lote_odoo
    # Vou agrupar por lote_inv principalmente (o que e' alvo)
    ag1 = tab_ativa.groupby(['company_id', 'cod_produto', 'lote_inv'], as_index=False).agg(
        tab_qtd_li=('qtd_ajuste', 'sum'),
        tab_valor_li=('valor_ajuste', 'sum'),
        tab_n_li=('id', 'count'),
        tab_status_li=('status', lambda s: ','.join(sorted(set(s)))),
        tab_acoes_li=('acao_decidida', lambda s: ','.join(sorted(set(s))))
    )
    ag1 = ag1.rename(columns={'lote_inv': 'lote'})

    # JOIN linhas_acao com tab por lote_inv
    res = linhas_acao.merge(ag1, on=['company_id', 'cod_produto', 'lote'], how='left')
    for c in ['tab_qtd_li', 'tab_valor_li', 'tab_n_li']:
        if c in res.columns:
            res[c] = res[c].fillna(0)
    for c in ['tab_status_li', 'tab_acoes_li']:
        if c in res.columns:
            res[c] = res[c].fillna('')
    return res


# ==============================================================
# MAIN
# ==============================================================
def main():
    print('=' * 70)
    print('AUDITORIA POR LOTE + REGRAS DE NEGOCIO RAFAEL')
    print('=' * 70)

    print('\n[1] Carregando SOT-INV (com lote)...')
    inv = carregar_inv()
    print(f'   {len(inv)} pares (filial, cod, lote) no inventario fisico')

    print('\n[2] Carregando SOT-ODOO (com lote)...')
    odoo = carregar_odoo()
    print(f'   {len(odoo)} pares (filial, cod, lote) no Odoo snapshot')

    print('\n[3] Classificando acoes por linha (regras de negocio)...')
    linhas, by_cod = classificar_acoes(inv, odoo)
    print(f'   {len(linhas)} linhas analisadas, {len(by_cod)} cods unicos')

    print('\n[4] Calculando disponibilidade MIGRACAO...')
    mig = disponibilidade_migracao(odoo)
    print(f'   MIGRACAO CD: {len(mig[mig["filial"]=="CD"])} cods | qtd {mig[mig["filial"]=="CD"]["qtd_migracao"].sum():,.0f}')
    print(f'   MIGRACAO FB: {len(mig[mig["filial"]=="FB"])} cods | qtd {mig[mig["filial"]=="FB"]["qtd_migracao"].sum():,.0f}')

    print('\n[5] Carregando tabela ajuste_estoque_inventario...')
    tab = carregar_tabela()
    linhas = comparar_tabela(linhas, tab)
    print(f'   Tabela: {len(tab)} ajustes')

    # ============ RESUMO POR ACAO ============
    resumo_acao = linhas.groupby(['filial', 'acao_proposta'], as_index=False).agg(
        n=('cod_produto', 'count'),
        qtd_inv=('qtd_inv', 'sum'),
        qtd_odoo=('qtd_odoo', 'sum'),
        diff=('diff_lote', 'sum'),
        valor_mov=('valor_movimento', 'sum')
    )

    # ============ RESUMO POR FILIAL ============
    resumo_filial = by_cod.groupby(['filial', 'company_id'], as_index=False).agg(
        n_cods=('cod_produto', 'count'),
        sum_inv=('sum_inv', 'sum'),
        sum_odoo=('sum_odoo', 'sum'),
        liquido=('liquido', 'sum'),
        valor_liquido=('valor_liquido', 'sum')
    )
    cen = by_cod.groupby(['filial', 'cenario'], as_index=False).agg(
        n=('cod_produto', 'count'),
        liquido=('liquido', 'sum'),
        valor=('valor_liquido', 'sum')
    )

    # ============ VEREDITO TABELA ============
    # Para cada (filial, cod, lote) com acao_proposta != OK_LOTE_BATE:
    # comparar com tabela
    relevante = linhas[~linhas['acao_proposta'].isin(['OK_LOTE_BATE', 'NEG_LOTE_JA_E_MIGRACAO', 'AMBOS_ZERO'])].copy()
    relevante['delta_tab'] = relevante['tab_qtd_li'] - relevante['diff_lote']
    relevante['delta_valor'] = relevante['delta_tab'] * relevante['custo_unit']

    # Categorizar
    def cat_tab(r):
        tol = 0.01
        has_tab = r['tab_n_li'] > 0
        if not has_tab:
            return 'TABELA_NAO_TEM'
        if abs(r['delta_tab']) < tol:
            return 'TABELA_BATE'
        return 'TABELA_DIVERGE'
    relevante['cat_tab'] = relevante.apply(cat_tab, axis=1)

    resumo_tab = relevante.groupby(['filial', 'acao_proposta', 'cat_tab'], as_index=False).agg(
        n=('cod_produto', 'count'),
        diff_total=('diff_lote', 'sum'),
        tab_total=('tab_qtd_li', 'sum'),
        delta_total=('delta_tab', 'sum'),
        valor_delta=('delta_valor', 'sum')
    )

    # ============ ESCREVER EXCEL ============
    os.makedirs(RELATORIOS_DIR, exist_ok=True)
    print(f'\n[6] Escrevendo {OUT_PATH}...')
    with pd.ExcelWriter(OUT_PATH, engine='xlsxwriter') as writer:
        # README
        readme = pd.DataFrame([
            ['Data', '2026-05-18'],
            ['', ''],
            ['SOT-INV', 'COMPILADO INV. 16.05.2026.xlsx (sabado, fisico)'],
            ['SOT-ODOO', 'estoque-odoo-{FB,LF,CD}.xlsx (domingo 21:44, PRE-execucoes)'],
            ['Granularidade', 'POR (filial, cod_produto, lote) — lotes considerados'],
            ['', ''],
            ['REGRAS DE NEGOCIO (Rafael, 2026-05-18)', ''],
            ['LF', 'Apenas NF FB<->LF. LF sem MIGRACAO. POS=NF FB->LF, NEG=NF LF->FB.'],
            ['CD POS', 'Cascata: rename -> MIGRACAO_CD -> qualquer lote FB -> ajuste positivo'],
            ['CD NEG', 'Rename lote_odoo -> MIGRACAO_CD'],
            ['FB POS', 'Cascata: rename -> MIGRACAO_CD->FB -> ajuste positivo'],
            ['FB NEG', 'Rename lote_odoo -> MIGRACAO_FB'],
            ['Ordem', 'CD primeiro (cria MIGRACAO_CD), depois FB usa'],
            ['', ''],
            ['Cenarios por COD', ''],
            ['RENAME_OU_OK', 'sum_inv == sum_odoo: so renomear lotes (sem mexer qtd)'],
            ['POSITIVO_LIQUIDO', 'sum_inv > sum_odoo: precisa entrada liquida via cascata'],
            ['NEGATIVO_LIQUIDO', 'sum_inv < sum_odoo: precisa saida liquida para MIGRACAO'],
            ['AMBOS_ZERO', 'cod sem saldo em nenhum dos lados'],
            ['', ''],
            ['Categoria por LOTE', ''],
            ['AMBOS', 'lote presente em inv E Odoo (mesma filial+cod)'],
            ['SO_INV', 'lote no inv mas nao Odoo'],
            ['SO_ODOO', 'lote no Odoo mas nao inv'],
        ], columns=['Campo', 'Valor'])
        readme.to_excel(writer, sheet_name='README', index=False)

        # 1. Resumo por filial
        resumo_filial.to_excel(writer, sheet_name='1_Resumo_Filial', index=False)

        # 2. Cenarios por cod
        cen.to_excel(writer, sheet_name='2_Cenarios_Cod', index=False)

        # 3. Resumo por acao proposta
        resumo_acao.to_excel(writer, sheet_name='3_Acoes_Propostas', index=False)

        # 4. Detalhe LF
        lf = linhas[linhas['filial'] == 'LF'][[
            'cod_produto', 'lote', 'qtd_inv', 'qtd_odoo', 'diff_lote',
            'cobertura_lote', 'cenario_cod', 'acao_proposta', 'custo_unit', 'valor_movimento',
            'tab_qtd_li', 'tab_valor_li', 'tab_status_li', 'tab_acoes_li'
        ]].sort_values(['cod_produto', 'lote'])
        lf.to_excel(writer, sheet_name='4_LF_Detalhe', index=False)

        # 5. Detalhe CD
        cd = linhas[linhas['filial'] == 'CD'][[
            'cod_produto', 'lote', 'qtd_inv', 'qtd_odoo', 'diff_lote',
            'cobertura_lote', 'cenario_cod', 'acao_proposta', 'custo_unit', 'valor_movimento',
            'tab_qtd_li', 'tab_valor_li', 'tab_status_li', 'tab_acoes_li'
        ]].sort_values(['cod_produto', 'lote'])
        cd.to_excel(writer, sheet_name='5_CD_Detalhe', index=False)

        # 6. Detalhe FB
        fb = linhas[linhas['filial'] == 'FB'][[
            'cod_produto', 'lote', 'qtd_inv', 'qtd_odoo', 'diff_lote',
            'cobertura_lote', 'cenario_cod', 'acao_proposta', 'custo_unit', 'valor_movimento',
            'tab_qtd_li', 'tab_valor_li', 'tab_status_li', 'tab_acoes_li'
        ]].sort_values(['cod_produto', 'lote'])
        fb.to_excel(writer, sheet_name='6_FB_Detalhe', index=False)

        # 7. Disponibilidade MIGRACAO
        mig_pivot = mig.pivot_table(
            index='cod_produto', columns='filial', values='qtd_migracao', fill_value=0
        ).reset_index()
        mig_pivot.to_excel(writer, sheet_name='7_MIGRACAO_Disponivel', index=False)

        # 8. Tabela vs SOT (linhas relevantes)
        resumo_tab.to_excel(writer, sheet_name='8_Tabela_vs_SOT_Resumo', index=False)

        # 9. Linhas onde TABELA_NAO_TEM
        nao_tem = relevante[relevante['cat_tab'] == 'TABELA_NAO_TEM'].copy()
        nao_tem['abs_v'] = nao_tem['valor_movimento'].abs()
        nao_tem = nao_tem.sort_values('abs_v', ascending=False)
        nao_tem[[
            'filial', 'cod_produto', 'lote', 'qtd_inv', 'qtd_odoo', 'diff_lote',
            'cobertura_lote', 'cenario_cod', 'acao_proposta', 'valor_movimento'
        ]].head(500).to_excel(writer, sheet_name='9_TOP500_TabelaNaoTem', index=False)

        # 10. Linhas onde TABELA_DIVERGE
        diverge = relevante[relevante['cat_tab'] == 'TABELA_DIVERGE'].copy()
        diverge['abs_v'] = diverge['delta_valor'].abs()
        diverge = diverge.sort_values('abs_v', ascending=False)
        diverge[[
            'filial', 'cod_produto', 'lote', 'qtd_inv', 'qtd_odoo', 'diff_lote',
            'acao_proposta', 'tab_qtd_li', 'delta_tab', 'tab_acoes_li', 'tab_status_li'
        ]].head(500).to_excel(writer, sheet_name='10_TOP500_TabelaDiverge', index=False)

    print(f'OK. Arquivo: {OUT_PATH}')

    # ============ IMPRIMIR VEREDITO ============
    print('\n' + '=' * 70)
    print('RESUMO POR FILIAL (agregado por cod)')
    print('=' * 70)
    print(resumo_filial.to_string(index=False, float_format=lambda x: f'{x:>16,.0f}'))

    print('\n' + '=' * 70)
    print('CENARIOS POR COD')
    print('=' * 70)
    print(cen.to_string(index=False, float_format=lambda x: f'{x:>16,.0f}'))

    print('\n' + '=' * 70)
    print('ACOES PROPOSTAS (por linha = filial+cod+lote)')
    print('=' * 70)
    print(resumo_acao.to_string(index=False, float_format=lambda x: f'{x:>16,.0f}'))

    print('\n' + '=' * 70)
    print('TABELA SISTEMA vs SOT (acoes relevantes)')
    print('=' * 70)
    print(resumo_tab.to_string(index=False, float_format=lambda x: f'{x:>16,.0f}'))

    # Total a ajustar
    movimentacao = linhas[~linhas['acao_proposta'].isin(['OK_LOTE_BATE', 'NEG_LOTE_JA_E_MIGRACAO', 'AMBOS_ZERO'])]
    print(f'\nTotal de linhas com movimentacao real: {len(movimentacao)}')
    print(f'Valor total movimentado (abs): R$ {movimentacao["valor_movimento"].sum():,.2f}')


if __name__ == '__main__':
    main()
