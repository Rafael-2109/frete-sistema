"""Re-filtra o diff anterior considerando APENAS lotes != MIGRACAO.

A logica de negocio do Rafael:
- CD/FB: lotes-fantasma vao para MIGRACAO (saldo total inalterado, so isolado)
- LF: sem MIGRACAO, movs via NF FB<->LF

Logo, o diff RELEVANTE eh: lotes nao-MIGRACAO devem bater
inv_teorico vs odoo_atual. Esses sao os lotes "ativos" (com saldo correto
para venda/uso).

Le do Excel anterior, filtra, regenera relatorio.

Output: docs/inventario-2026-05/07-relatorios/DIFF_LOTES_ATIVOS_2026_05_18.xlsx
"""
import os
import pandas as pd
import numpy as np

RELATORIOS_DIR = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/07-relatorios'
SRC = os.path.join(RELATORIOS_DIR, 'INVENTARIO_TEORICO_E_NOVO_DIFF_2026_05_18.xlsx')
OUT = os.path.join(RELATORIOS_DIR, 'DIFF_LOTES_ATIVOS_2026_05_18.xlsx')


def _is_migracao(lote):
    if pd.isna(lote) or not lote:
        return False
    return str(lote).upper().strip() in ('MIGRACAO', 'MIGRAÇÃO', 'MIGRACÃO', 'MIGRAÇAO', 'MIG')


def main():
    print('Lendo diff anterior...')
    diff = pd.read_excel(SRC, sheet_name='5_Diff_Novo')
    movs = pd.read_excel(SRC, sheet_name='2_Movimentacoes')
    print(f'  {len(diff)} linhas no diff total')

    # Marcar MIGRACAO
    diff['eh_migracao'] = diff['lote'].apply(_is_migracao)

    # Separar
    df_ativos = diff[~diff['eh_migracao']].copy()
    df_migr = diff[diff['eh_migracao']].copy()
    print(f'  {len(df_ativos)} lotes ATIVOS (nao-MIGRACAO)')
    print(f'  {len(df_migr)} lotes MIGRACAO (separados)')

    # Recalcular status com tolerancia
    df_ativos['status'] = np.where(df_ativos['diff_qtd'].abs() < 0.01, 'OK', 'DIVERGENTE')

    # Resumo ATIVOS por filial
    resumo = df_ativos.groupby('filial', as_index=False).agg(
        n=('cod', 'count'),
        OK=('status', lambda s: (s == 'OK').sum()),
        DIV=('status', lambda s: (s == 'DIVERGENTE').sum()),
        teorico=('qtd_teorica', 'sum'),
        odoo=('qtd_odoo_atual', 'sum'),
        diff_qtd=('diff_qtd', 'sum'),
        diff_valor=('diff_valor', 'sum'),
    )
    # Cobertura
    resumo_cob = df_ativos.groupby(['filial', 'cobertura'], as_index=False).agg(
        n=('cod', 'count'),
        diff_qtd=('diff_qtd', 'sum'),
        diff_valor=('diff_valor', 'sum'),
    )

    # Resumo MIGRACAO por filial (saldo acumulado)
    resumo_migr = df_migr.groupby('filial', as_index=False).agg(
        n_chaves=('cod', 'count'),
        teorico=('qtd_teorica', 'sum'),
        odoo=('qtd_odoo_atual', 'sum'),
        diff_qtd=('diff_qtd', 'sum'),
        diff_valor=('diff_valor', 'sum'),
    )

    # Divergentes ativos ordenados por valor
    div_ativos = df_ativos[df_ativos['status'] == 'DIVERGENTE'].copy()
    div_ativos['abs_v'] = div_ativos['diff_valor'].abs()
    div_ativos = div_ativos.sort_values('abs_v', ascending=False)

    # TOP divergencias por (filial, cod) agregado
    cod_agg = div_ativos.groupby(['filial', 'cod'], as_index=False).agg(
        n_lotes=('lote', 'count'),
        diff_qtd_total=('diff_qtd', 'sum'),
        diff_valor_total=('diff_valor', 'sum'),
    )
    cod_agg['abs_v'] = cod_agg['diff_valor_total'].abs()
    cod_agg = cod_agg.sort_values('abs_v', ascending=False)

    print('\n=== RESUMO LOTES ATIVOS (nao-MIGRACAO) ===')
    print(resumo.to_string(index=False, float_format=lambda x: f'{x:>12,.2f}'))
    print('\n=== COBERTURA LOTES ATIVOS ===')
    print(resumo_cob.to_string(index=False, float_format=lambda x: f'{x:>12,.2f}'))
    print('\n=== LOTES MIGRACAO (acumulado fantasma) ===')
    print(resumo_migr.to_string(index=False, float_format=lambda x: f'{x:>12,.2f}'))

    print(f'\nEscrevendo {OUT}...')
    with pd.ExcelWriter(OUT, engine='xlsxwriter') as writer:
        readme = pd.DataFrame([
            ['Data', '2026-05-18'],
            ['Fonte', 'INVENTARIO_TEORICO_E_NOVO_DIFF_2026_05_18.xlsx (aba 5_Diff_Novo)'],
            ['Filtro', 'Lotes != MIGRACAO/MIGRAÇÃO'],
            ['', ''],
            ['Logica', 'Lotes ativos devem bater inv_teorico vs odoo_atual (saldo correto)'],
            ['Migracao', 'Separado — apenas saldo acumulado de fantasmas (CD/FB)'],
            ['', ''],
            ['Status', 'OK = diff_qtd < 0.01 | DIVERGENTE = caso contrario'],
            ['cobertura', 'AMBOS / SO_TEORICO / SO_ODOO'],
        ], columns=['Campo', 'Valor'])
        readme.to_excel(writer, sheet_name='README', index=False)

        resumo.to_excel(writer, sheet_name='1_Resumo_Ativos', index=False)
        resumo_cob.to_excel(writer, sheet_name='2_Cobertura', index=False)
        resumo_migr.to_excel(writer, sheet_name='3_Migracao_Saldo', index=False)

        cols_diff = ['filial', 'cod', 'lote', 'qtd_teorica', 'qtd_odoo_atual',
                     'diff_qtd', 'custo_unit', 'diff_valor', 'cobertura', 'status']
        df_ativos[cols_diff].sort_values(['filial', 'cod', 'lote']).to_excel(
            writer, sheet_name='4_Diff_Lotes_Ativos', index=False
        )

        div_ativos[cols_diff].head(2000).to_excel(
            writer, sheet_name='5_Divergentes_TOP', index=False
        )

        cod_agg.head(500).to_excel(writer, sheet_name='6_Por_Cod_TOP', index=False)

        df_migr[cols_diff].sort_values(['filial', 'cod']).to_excel(
            writer, sheet_name='7_Lotes_MIGRACAO', index=False
        )

    print(f'OK. {OUT}')


if __name__ == '__main__':
    main()
