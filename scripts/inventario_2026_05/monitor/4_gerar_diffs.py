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
    COMPANY_FULL, FILIAL_TO_COMPANY,
)


def carregar(cache_dir):
    estoques_path = os.path.join(cache_dir, 'estoques.csv')
    teorico_path = os.path.join(cache_dir, 'inv_teorico.csv')
    movs_path = os.path.join(cache_dir, 'movimentacoes.csv')
    if not os.path.exists(estoques_path):
        sys.exit(f'ERRO: {estoques_path} nao existe (rode script 1)')
    if not os.path.exists(teorico_path):
        sys.exit(f'ERRO: {teorico_path} nao existe (rode script 3)')

    odoo = pd.read_csv(estoques_path, low_memory=False)
    teorico = pd.read_csv(teorico_path, low_memory=False)
    movs = pd.read_csv(movs_path, low_memory=False) if os.path.exists(movs_path) else pd.DataFrame()

    for df in (odoo, teorico):
        df['cod'] = df['cod'].apply(norm_cod)
        df['lote'] = df['lote'].apply(norm_lote)
    if len(movs):
        movs['cod'] = movs['cod'].apply(norm_cod)
        movs['lote'] = movs['lote'].apply(norm_lote)

    return odoo, teorico, movs


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
    j['diff_qtd'] = (j['qtd_teorica'] - j['qtd_odoo_atual']).round(4)
    j['qtd_teorica'] = j['qtd_teorica'].round(4)
    j['qtd_odoo_atual'] = j['qtd_odoo_atual'].round(4)
    j['diff_valor'] = (j['diff_qtd'] * j['custo_unit']).round(2)
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

    odoo, teorico, movs = carregar(cache_dir)
    print(f'  Estoques Odoo: {len(odoo)} chaves')
    print(f'  Inv teorico:    {len(teorico)} chaves')
    print(f'  Movimentacoes:  {len(movs)} linhas')

    j, teorico_migr, odoo_migr = gerar_diff(odoo, teorico)
    print(f'  Diff lotes ATIVOS: {len(j)}')

    # Mapa cod -> nome_produto (do estoques.csv)
    if 'nome_produto' in odoo.columns:
        nome_map = odoo.drop_duplicates('cod').set_index('cod')['nome_produto'].to_dict()
    else:
        nome_map = {}

    def add_nome(df):
        if 'cod' in df.columns:
            df['nome_produto'] = df['cod'].map(nome_map).fillna('')
        if 'filial' in df.columns:
            df['empresa'] = df['filial'].map(
                lambda f: COMPANY_FULL.get(FILIAL_TO_COMPANY.get(f, 0), '')
            ).fillna('')
        return df

    j = add_nome(j)
    migr = teorico_migr.merge(
        odoo_migr[['filial', 'cod', 'lote', 'qtd_odoo_atual', 'custo_unit']],
        on=['filial', 'cod', 'lote'], how='outer'
    )
    for c in ['qtd_teorica', 'qtd_odoo_atual', 'custo_unit']:
        if c in migr.columns:
            migr[c] = migr[c].fillna(0)
    migr['diff_qtd'] = (migr['qtd_teorica'] - migr['qtd_odoo_atual']).round(4)
    migr['qtd_teorica'] = migr['qtd_teorica'].round(4)
    migr['qtd_odoo_atual'] = migr['qtd_odoo_atual'].round(4)
    migr['diff_valor'] = (migr['diff_qtd'] * migr['custo_unit']).round(2)
    migr = add_nome(migr)

    # Movs com lote MIGRACAO (entradas e saidas)
    movs_migr = pd.DataFrame()
    if len(movs):
        movs['eh_migr'] = movs['lote'].apply(is_migracao)
        movs_migr = movs[movs['eh_migr']].copy()
        if 'nome_produto' not in movs_migr.columns:
            movs_migr = add_nome(movs_migr)
        # Colunas entrada/saida/saldo (mesmo criterio do Diff_Por_Lote)
        def _entrada(r):
            return r['qty_done'] if bool(r.get('dst_interna', False)) else 0
        def _saida(r):
            return -r['qty_done'] if bool(r.get('src_interna', False)) else 0
        movs_migr['entrada'] = movs_migr.apply(_entrada, axis=1).round(4)
        movs_migr['saida'] = movs_migr.apply(_saida, axis=1).round(4)
        movs_migr['saldo'] = (movs_migr['entrada'] + movs_migr['saida']).round(4)

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
    by_cod = add_nome(by_cod)

    resumo_cod = by_cod.groupby('filial', as_index=False).agg(
        n_cods=('cod', 'count'),
        OK=('status', lambda s: (s == 'OK').sum()),
        DIV=('status', lambda s: (s == 'DIVERGENTE').sum()),
        diff_total=('diff_total', 'sum'),
        diff_valor=('diff_valor_total', 'sum'),
    )

    # migr ja foi calculado e tem nome_produto (acima)
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
        cols_lote = ['empresa', 'filial', 'cod', 'nome_produto', 'lote', 'qtd_inicial_inv',
                     'qtd_movs_entrada', 'qtd_movs_saida', 'qtd_teorica',
                     'qtd_odoo_atual', 'diff_qtd', 'custo_unit', 'diff_valor',
                     'cobertura', 'status']
        cols_lote = [c for c in cols_lote if c in j.columns]
        j[cols_lote].sort_values(['filial', 'cod', 'lote']).to_excel(
            writer, sheet_name='Diff_Por_Lote', index=False
        )

        cols_cod = ['empresa', 'filial', 'cod', 'nome_produto', 'n_lotes', 'teorico_total',
                    'odoo_total', 'diff_total', 'diff_valor_total', 'status']
        cols_cod = [c for c in cols_cod if c in by_cod.columns]
        by_cod[cols_cod].sort_values(['filial', 'cod']).to_excel(
            writer, sheet_name='Diff_Por_Cod', index=False
        )

        # MIGRACAO saldo detalhe
        cols_migr = ['empresa', 'filial', 'cod', 'nome_produto', 'lote', 'qtd_teorica',
                     'qtd_odoo_atual', 'diff_qtd', 'custo_unit', 'diff_valor']
        cols_migr = [c for c in cols_migr if c in migr.columns]
        migr[cols_migr].sort_values(['filial', 'cod']).to_excel(
            writer, sheet_name='MIGRACAO_Saldo', index=False
        )

        # MIGRACAO movimentacoes (entradas e saidas com lote MIGRACAO)
        if len(movs_migr):
            cols_movs = ['date', 'empresa', 'filial', 'cod', 'nome_produto', 'lote',
                         'entrada', 'saida', 'saldo',
                         'loc_src_name', 'loc_dst_name',
                         'picking_id_n', 'picking_name', 'origin',
                         'create_uid_name', 'origem_classificada']
            cols_movs = [c for c in cols_movs if c in movs_migr.columns]
            movs_migr[cols_movs].sort_values(['filial', 'cod', 'date']).to_excel(
                writer, sheet_name='MIGRACAO_Movimentacoes', index=False
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
