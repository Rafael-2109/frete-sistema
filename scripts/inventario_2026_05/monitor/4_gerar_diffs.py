"""SCRIPT 4: Gera DIFFS por (filial, cod, lote) considerando script 3 SEM MIGRACAO.

Le:
  - <cache>/estoques.csv (script 1)
  - <cache>/inv_teorico.csv (script 3)

Filtra MIGRACAO (de ambos os lados) e gera:
  - Resumo por filial
  - Cobertura (AMBOS / SO_INV / SO_ODOO)
  - Detalhe por lote
  - Agregado por (filial, cod)
  - TOP divergencias por valor
  - Saldo MIGRACAO separado (auditoria)

Output: docs/inventario-2026-05/07-relatorios/MONITOR_DIFF_<YYYY-MM-DD_HH-MM>.xlsx

Uso:
    python 4_gerar_diffs.py [--cache-dir <path>] [--output-name <nome>]
"""
import argparse
import os
import sys
import datetime as _dt

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import (
    norm_cod, norm_lote, is_migracao,
    garantir_cache_dir, garantir_relatorios_dir,
)


def carregar(cache_dir):
    estoques_path = os.path.join(cache_dir, 'estoques.csv')
    teorico_path = os.path.join(cache_dir, 'inv_teorico.csv')
    if not os.path.exists(estoques_path):
        sys.exit(f'ERRO: {estoques_path} nao existe (rode script 1)')
    if not os.path.exists(teorico_path):
        sys.exit(f'ERRO: {teorico_path} nao existe (rode script 3)')

    odoo = pd.read_csv(estoques_path, low_memory=False)
    teorico = pd.read_csv(teorico_path, low_memory=False)

    for df in (odoo, teorico):
        df['cod'] = df['cod'].apply(norm_cod)
        df['lote'] = df['lote'].apply(norm_lote)

    return odoo, teorico


def gerar_diff(odoo, teorico):
    """Diff por (filial, cod, lote) — somente lotes != MIGRACAO."""
    # Renomear colunas Odoo para clareza
    odoo = odoo.rename(columns={'qtd': 'qtd_odoo_atual', 'valor': 'valor_odoo'}).copy()

    # Marcar MIGRACAO
    teorico['eh_migr'] = teorico['lote'].apply(is_migracao)
    odoo['eh_migr'] = odoo['lote'].apply(is_migracao)

    teorico_ativo = teorico[~teorico['eh_migr']].copy()
    odoo_ativo = odoo[~odoo['eh_migr']].copy()
    teorico_migr = teorico[teorico['eh_migr']].copy()
    odoo_migr = odoo[odoo['eh_migr']].copy()

    # MERGE
    j = teorico_ativo[['filial', 'cod', 'lote', 'qtd_teorica',
                       'qtd_inicial_inv', 'qtd_movs_entrada', 'qtd_movs_saida']].merge(
        odoo_ativo[['filial', 'cod', 'lote', 'qtd_odoo_atual', 'custo_unit']],
        on=['filial', 'cod', 'lote'], how='outer'
    )
    for c in ['qtd_teorica', 'qtd_inicial_inv', 'qtd_movs_entrada', 'qtd_movs_saida',
              'qtd_odoo_atual', 'custo_unit']:
        if c in j.columns:
            j[c] = j[c].fillna(0)
    j['diff_qtd'] = j['qtd_teorica'] - j['qtd_odoo_atual']
    j['diff_valor'] = j['diff_qtd'] * j['custo_unit']
    j['cobertura'] = np.where(
        (j['qtd_teorica'].abs() > 0.01) & (j['qtd_odoo_atual'].abs() > 0.01), 'AMBOS',
        np.where(j['qtd_teorica'].abs() > 0.01, 'SO_TEORICO', 'SO_ODOO')
    )
    j['status'] = np.where(j['diff_qtd'].abs() < 0.01, 'OK', 'DIVERGENTE')
    return j, teorico_migr, odoo_migr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache-dir', default=None)
    ap.add_argument('--output-name', default=None,
                    help='Nome do Excel final (default: MONITOR_DIFF_<timestamp>.xlsx)')
    args = ap.parse_args()

    cache_dir = garantir_cache_dir(args.cache_dir) if args.cache_dir else garantir_cache_dir()
    rel_dir = garantir_relatorios_dir()

    odoo, teorico = carregar(cache_dir)
    print(f'  Estoques Odoo: {len(odoo)} chaves')
    print(f'  Inv teorico:    {len(teorico)} chaves')

    j, teorico_migr, odoo_migr = gerar_diff(odoo, teorico)
    print(f'  Diff lotes ATIVOS: {len(j)}')

    # ===== Resumos =====
    resumo_lote = j.groupby('filial', as_index=False).agg(
        n=('cod', 'count'),
        OK=('status', lambda s: (s == 'OK').sum()),
        DIV=('status', lambda s: (s == 'DIVERGENTE').sum()),
        teorico=('qtd_teorica', 'sum'),
        odoo_atual=('qtd_odoo_atual', 'sum'),
        diff_qtd=('diff_qtd', 'sum'),
        diff_valor=('diff_valor', 'sum'),
    )

    cobertura = j.groupby(['filial', 'cobertura'], as_index=False).agg(
        n=('cod', 'count'),
        diff_qtd=('diff_qtd', 'sum'),
        diff_valor=('diff_valor', 'sum'),
    )

    # Agregado por (filial, cod) — saldo total ativo
    by_cod = j.groupby(['filial', 'cod'], as_index=False).agg(
        n_lotes=('lote', 'count'),
        teorico_total=('qtd_teorica', 'sum'),
        odoo_total=('qtd_odoo_atual', 'sum'),
        diff_total=('diff_qtd', 'sum'),
        diff_valor_total=('diff_valor', 'sum'),
    )
    by_cod['status'] = np.where(by_cod['diff_total'].abs() < 0.5, 'OK', 'DIVERGENTE')

    resumo_cod = by_cod.groupby('filial', as_index=False).agg(
        n_cods=('cod', 'count'),
        OK=('status', lambda s: (s == 'OK').sum()),
        DIV=('status', lambda s: (s == 'DIVERGENTE').sum()),
        diff_total=('diff_total', 'sum'),
        diff_valor=('diff_valor_total', 'sum'),
    )

    # Saldo MIGRACAO
    migr = teorico_migr[['filial', 'cod', 'lote', 'qtd_teorica']].merge(
        odoo_migr[['filial', 'cod', 'lote', 'qtd_odoo_atual', 'custo_unit']],
        on=['filial', 'cod', 'lote'], how='outer'
    )
    for c in ['qtd_teorica', 'qtd_odoo_atual', 'custo_unit']:
        if c in migr.columns:
            migr[c] = migr[c].fillna(0)
    migr['diff_qtd'] = migr['qtd_teorica'] - migr['qtd_odoo_atual']
    migr['diff_valor'] = migr['diff_qtd'] * migr['custo_unit']
    resumo_migr = migr.groupby('filial', as_index=False).agg(
        n=('cod', 'count'),
        teorico=('qtd_teorica', 'sum'),
        odoo_atual=('qtd_odoo_atual', 'sum'),
        diff_qtd=('diff_qtd', 'sum'),
    )

    # ===== Output =====
    ts = _dt.datetime.now().strftime('%Y-%m-%d_%H-%M')
    out_name = args.output_name or f'MONITOR_DIFF_{ts}.xlsx'
    out_path = os.path.join(rel_dir, out_name)
    print(f'\nEscrevendo {out_path}...')

    # Divergencias ordenadas
    div = j[j['status'] == 'DIVERGENTE'].copy()
    div['abs_v'] = div['diff_valor'].abs()
    div = div.sort_values('abs_v', ascending=False)

    div_cod = by_cod[by_cod['status'] == 'DIVERGENTE'].copy()
    div_cod['abs_v'] = div_cod['diff_valor_total'].abs()
    div_cod = div_cod.sort_values('abs_v', ascending=False)

    with pd.ExcelWriter(out_path, engine='xlsxwriter') as writer:
        readme = pd.DataFrame([
            ['Gerado em', ts],
            ['Logica', 'Inv fisico + movs (16/05 -> agora) vs Odoo atual'],
            ['Filtro', 'APENAS lotes != MIGRACAO'],
            ['MIGRACAO', 'Mostrado em aba separada (auditoria)'],
            ['', ''],
            ['Pipeline', '1_baixar_estoques -> 2_baixar_movimentacoes -> 3_agregar_lote -> 4_gerar_diffs'],
            ['Cache', 'CSVs intermediarios em /tmp/inventario_monitor/'],
            ['', ''],
            ['status', 'OK = diff_qtd < 0.01'],
            ['cobertura', 'AMBOS / SO_TEORICO / SO_ODOO'],
        ], columns=['Campo', 'Valor'])
        readme.to_excel(writer, sheet_name='README', index=False)

        resumo_lote.to_excel(writer, sheet_name='1_Resumo_Lote', index=False)
        cobertura.to_excel(writer, sheet_name='2_Cobertura', index=False)
        resumo_cod.to_excel(writer, sheet_name='3_Resumo_Cod', index=False)
        resumo_migr.to_excel(writer, sheet_name='4_Saldo_MIGRACAO', index=False)

        cols_lote = ['filial', 'cod', 'lote', 'qtd_inicial_inv',
                     'qtd_movs_entrada', 'qtd_movs_saida', 'qtd_teorica',
                     'qtd_odoo_atual', 'diff_qtd', 'custo_unit', 'diff_valor',
                     'cobertura', 'status']
        j[cols_lote].sort_values(['filial', 'cod', 'lote']).to_excel(
            writer, sheet_name='5_Diff_Por_Lote', index=False
        )
        cols_cod = ['filial', 'cod', 'n_lotes', 'teorico_total', 'odoo_total',
                    'diff_total', 'diff_valor_total', 'status']
        by_cod[cols_cod].sort_values(['filial', 'cod']).to_excel(
            writer, sheet_name='6_Diff_Por_Cod', index=False
        )

        div[cols_lote].head(2000).to_excel(writer, sheet_name='7_DIV_Lote_TOP', index=False)
        div_cod[cols_cod].head(500).to_excel(writer, sheet_name='8_DIV_Cod_TOP', index=False)

        # MIGRACAO detalhe
        cols_migr = ['filial', 'cod', 'lote', 'qtd_teorica', 'qtd_odoo_atual',
                     'diff_qtd', 'custo_unit', 'diff_valor']
        cols_migr = [c for c in cols_migr if c in migr.columns]
        migr[cols_migr].sort_values(['filial', 'cod']).to_excel(
            writer, sheet_name='9_MIGRACAO_Detalhe', index=False
        )

    print(f'OK. {out_path}')

    print('\n=== Resumo por filial (lotes ativos) ===')
    print(resumo_lote.to_string(index=False, float_format=lambda x: f'{x:>14,.2f}'))
    print('\n=== Cobertura ===')
    print(cobertura.to_string(index=False, float_format=lambda x: f'{x:>14,.2f}'))
    print('\n=== Saldo MIGRACAO ===')
    print(resumo_migr.to_string(index=False, float_format=lambda x: f'{x:>14,.2f}'))


if __name__ == '__main__':
    main()
