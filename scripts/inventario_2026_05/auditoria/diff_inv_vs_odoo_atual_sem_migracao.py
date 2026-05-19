"""DIFF DIRETO: Inv fisico 16/05 vs Odoo ATUAL — APENAS lotes != MIGRACAO.

Logica: o saldo "real disponivel" eh tudo em lote != MIGRACAO. Se as movs
do Rafael foram corretas, o Odoo atual em lotes ativos deve refletir
o inv fisico (mais ou menos, modulo SKUs nao inventariados).

Le do Excel anterior (que ja tem inv_fisico e Odoo_atual extraidos).

Output: docs/inventario-2026-05/07-relatorios/DIFF_INV_VS_ODOO_ATUAL_2026_05_18.xlsx
"""
import os
import pandas as pd
import numpy as np

RELATORIOS_DIR = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/07-relatorios'
SRC = os.path.join(RELATORIOS_DIR, 'INVENTARIO_TEORICO_E_NOVO_DIFF_2026_05_18.xlsx')
OUT = os.path.join(RELATORIOS_DIR, 'DIFF_INV_VS_ODOO_ATUAL_2026_05_18.xlsx')


def _is_migracao(lote):
    if pd.isna(lote) or not lote:
        return False
    return str(lote).upper().strip() in ('MIGRACAO', 'MIGRAÇÃO', 'MIGRACÃO', 'MIGRAÇAO', 'MIG')


def _norm(x):
    if pd.isna(x):
        return ''
    s = str(x).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s


def main():
    print('Lendo Inv fisico e Odoo atual (do Excel anterior)...')

    # Inv fisico (re-carregar do COMPILADO)
    INVENTARIO_DIR = '/mnt/c/Users/rafael.nascimento/Downloads/INVENTARIO 16-05-26'
    path_inv = os.path.join(INVENTARIO_DIR, 'COMPILADO INV. 16.05.2026.xlsx')
    inv_rows = []
    for filial in ['FB', 'LF', 'CD']:
        df = pd.read_excel(path_inv, sheet_name=filial)
        df.columns = [c.strip().upper() for c in df.columns]
        df = df.rename(columns={c: 'LOTE' for c in df.columns if c.strip() == 'LOTE'})
        df['cod'] = df['CODIGO'].apply(_norm)
        df = df[df['cod'].str.isdigit()]
        df['lote'] = df['LOTE'].apply(_norm)
        df['qtd_inv'] = pd.to_numeric(df['QTD'], errors='coerce').fillna(0)
        df['filial'] = filial
        inv_rows.append(df[['filial', 'cod', 'lote', 'qtd_inv']])
    inv = pd.concat(inv_rows, ignore_index=True).groupby(
        ['filial', 'cod', 'lote'], as_index=False)['qtd_inv'].sum()
    print(f'  Inv fisico: {len(inv)} (filial, cod, lote)')

    # Odoo atual (le do Excel anterior)
    odoo = pd.read_excel(SRC, sheet_name='4_Odoo_Atual')
    odoo['cod'] = odoo['cod'].apply(_norm)
    odoo['lote'] = odoo['lote'].apply(_norm)
    print(f'  Odoo atual: {len(odoo)} (filial, cod, lote)')

    # Filtrar MIGRACAO de AMBOS
    inv['eh_migr'] = inv['lote'].apply(_is_migracao)
    odoo['eh_migr'] = odoo['lote'].apply(_is_migracao)

    inv_ativo = inv[~inv['eh_migr']].copy()
    odoo_ativo = odoo[~odoo['eh_migr']].copy()
    inv_migr = inv[inv['eh_migr']].copy()
    odoo_migr = odoo[odoo['eh_migr']].copy()

    print(f'  Inv fisico ATIVO (lote!=MIGRACAO): {len(inv_ativo)} | MIGRACAO: {len(inv_migr)}')
    print(f'  Odoo atual ATIVO (lote!=MIGRACAO): {len(odoo_ativo)} | MIGRACAO: {len(odoo_migr)}')

    # MERGE ATIVO por (filial, cod, lote)
    j = inv_ativo[['filial', 'cod', 'lote', 'qtd_inv']].merge(
        odoo_ativo[['filial', 'cod', 'lote', 'qtd_odoo_atual', 'custo_unit']],
        on=['filial', 'cod', 'lote'], how='outer'
    )
    j['qtd_inv'] = j['qtd_inv'].fillna(0)
    j['qtd_odoo_atual'] = j['qtd_odoo_atual'].fillna(0)
    j['custo_unit'] = j['custo_unit'].fillna(0)
    j['diff_qtd'] = j['qtd_inv'] - j['qtd_odoo_atual']
    j['diff_valor'] = j['diff_qtd'] * j['custo_unit']
    j['cobertura'] = np.where(
        (j['qtd_inv'].abs() > 0.01) & (j['qtd_odoo_atual'].abs() > 0.01), 'AMBOS',
        np.where(j['qtd_inv'].abs() > 0.01, 'SO_INV', 'SO_ODOO')
    )
    j['status'] = np.where(j['diff_qtd'].abs() < 0.01, 'OK', 'DIVERGENTE')

    # Agregado por (filial, cod) — saldo ativo total
    inv_por_cod = inv_ativo.groupby(['filial', 'cod'], as_index=False)['qtd_inv'].sum()
    inv_por_cod = inv_por_cod.rename(columns={'qtd_inv': 'INV_ativo_total'})
    odoo_por_cod = odoo_ativo.groupby(['filial', 'cod'], as_index=False).agg(
        ODOO_ativo_total=('qtd_odoo_atual', 'sum'),
        ODOO_valor_ativo=('valor_atual', 'sum'),
    )
    por_cod = inv_por_cod.merge(odoo_por_cod, on=['filial', 'cod'], how='outer')
    for c in ['INV_ativo_total', 'ODOO_ativo_total', 'ODOO_valor_ativo']:
        if c in por_cod.columns:
            por_cod[c] = por_cod[c].fillna(0)
    por_cod['diff_ativo'] = por_cod['INV_ativo_total'] - por_cod['ODOO_ativo_total']
    por_cod['cu'] = np.where(por_cod['ODOO_ativo_total'] > 0,
                              por_cod['ODOO_valor_ativo'] / por_cod['ODOO_ativo_total'], 0)
    por_cod['diff_valor'] = por_cod['diff_ativo'] * por_cod['cu']
    por_cod['status'] = np.where(por_cod['diff_ativo'].abs() < 0.5, 'OK', 'DIVERGENTE')

    # ===== Resumos =====
    resumo_lote = j.groupby('filial', as_index=False).agg(
        n=('cod', 'count'),
        OK=('status', lambda s: (s == 'OK').sum()),
        DIV=('status', lambda s: (s == 'DIVERGENTE').sum()),
        INV_ativo=('qtd_inv', 'sum'),
        ODOO_ativo=('qtd_odoo_atual', 'sum'),
        diff_qtd=('diff_qtd', 'sum'),
        diff_valor=('diff_valor', 'sum'),
    )

    resumo_cob = j.groupby(['filial', 'cobertura'], as_index=False).agg(
        n=('cod', 'count'),
        diff_qtd=('diff_qtd', 'sum'),
        diff_valor=('diff_valor', 'sum'),
    )

    resumo_cod = por_cod.groupby('filial', as_index=False).agg(
        n_cods=('cod', 'count'),
        OK=('status', lambda s: (s == 'OK').sum()),
        DIV=('status', lambda s: (s == 'DIVERGENTE').sum()),
        INV_ativo=('INV_ativo_total', 'sum'),
        ODOO_ativo=('ODOO_ativo_total', 'sum'),
        diff_ativo=('diff_ativo', 'sum'),
        diff_valor=('diff_valor', 'sum'),
    )

    # Resumo MIGRACAO
    migr = inv_migr[['filial', 'cod', 'lote', 'qtd_inv']].merge(
        odoo_migr[['filial', 'cod', 'lote', 'qtd_odoo_atual', 'custo_unit']],
        on=['filial', 'cod', 'lote'], how='outer'
    )
    for c in ['qtd_inv', 'qtd_odoo_atual', 'custo_unit']:
        if c in migr.columns:
            migr[c] = migr[c].fillna(0)
    resumo_migr = migr.groupby('filial', as_index=False).agg(
        n=('cod', 'count'),
        ODOO_em_MIGRACAO=('qtd_odoo_atual', 'sum'),
    )

    # ===== Print =====
    print('\n=== DIFF POR LOTE (ativos, !=MIGRACAO) ===')
    print(resumo_lote.to_string(index=False, float_format=lambda x: f'{x:>14,.2f}'))
    print('\n=== COBERTURA ===')
    print(resumo_cob.to_string(index=False, float_format=lambda x: f'{x:>14,.2f}'))
    print('\n=== AGREGADO POR COD (lote != MIGRACAO) ===')
    print(resumo_cod.to_string(index=False, float_format=lambda x: f'{x:>14,.2f}'))
    print('\n=== MIGRACAO (acumulado no Odoo atual) ===')
    print(resumo_migr.to_string(index=False, float_format=lambda x: f'{x:>14,.2f}'))

    # Top divergencias
    div = j[j['status'] == 'DIVERGENTE'].copy()
    div['abs_v'] = div['diff_valor'].abs()
    div = div.sort_values('abs_v', ascending=False)

    # Top divergencias por cod
    cod_div = por_cod[por_cod['status'] == 'DIVERGENTE'].copy()
    cod_div['abs_v'] = cod_div['diff_valor'].abs()
    cod_div = cod_div.sort_values('abs_v', ascending=False)

    # ===== Escrever =====
    print(f'\nEscrevendo {OUT}...')
    with pd.ExcelWriter(OUT, engine='xlsxwriter') as writer:
        readme = pd.DataFrame([
            ['Data', '2026-05-18'],
            ['Logica', 'Inv fisico 16/05 vs Odoo ATUAL — APENAS lotes != MIGRACAO'],
            ['', ''],
            ['Por que sem MIGRACAO', 'Esse e o lote consolidador de fantasma — saldo nao deve ser comparado'],
            ['', ''],
            ['Lotes ativos batendo => movs do Rafael consolidaram corretamente'],
            ['Saldo em MIGRACAO mostrado separadamente para auditoria'],
            ['', ''],
            ['status', 'OK = diff_qtd < 0.01 | DIVERGENTE = caso contrario'],
            ['cobertura', 'AMBOS = lote tem saldo no inv E Odoo | SO_INV | SO_ODOO'],
        ], columns=['Campo', 'Valor'])
        readme.to_excel(writer, sheet_name='README', index=False)

        resumo_lote.to_excel(writer, sheet_name='1_Resumo_Lote', index=False)
        resumo_cob.to_excel(writer, sheet_name='2_Cobertura', index=False)
        resumo_cod.to_excel(writer, sheet_name='3_Resumo_Cod', index=False)
        resumo_migr.to_excel(writer, sheet_name='4_Saldo_MIGRACAO', index=False)

        cols_lote = ['filial', 'cod', 'lote', 'qtd_inv', 'qtd_odoo_atual',
                     'diff_qtd', 'custo_unit', 'diff_valor', 'cobertura', 'status']
        j[cols_lote].sort_values(['filial', 'cod', 'lote']).to_excel(
            writer, sheet_name='5_Diff_Por_Lote', index=False
        )
        cols_cod = ['filial', 'cod', 'INV_ativo_total', 'ODOO_ativo_total',
                    'diff_ativo', 'cu', 'diff_valor', 'status']
        por_cod[cols_cod].sort_values(['filial', 'cod']).to_excel(
            writer, sheet_name='6_Diff_Por_Cod', index=False
        )

        div[cols_lote].head(2000).to_excel(writer, sheet_name='7_DIV_Lote_TOP', index=False)
        cod_div[cols_cod].head(500).to_excel(writer, sheet_name='8_DIV_Cod_TOP', index=False)

    print(f'OK. {OUT}')


if __name__ == '__main__':
    main()
