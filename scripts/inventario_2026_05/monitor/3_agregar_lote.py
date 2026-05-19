"""SCRIPT 3: Agrega inventario fisico + movimentacoes NAO-AJUSTE em saldo teorico.

REGRA: aplica APENAS as movs cuja origem_classificada == 'RECEBIMENTO_LF_RENDER'
(unicas movs que NAO sao ajuste do Rafael). Demais (INVENTARIO_PICKING,
INVENTORY_ADJUST, OUTROS_PICKING) sao DESCARTADAS — sao os proprios ajustes
que queremos monitorar.

Estado inicial = inventario fisico (COMPILADO INV 16.05.2026.xlsx).
Aplica movs filtradas: se loc_src eh interna da filial, subtrai;
se loc_dst eh interna, soma.

Output: <cache>/inv_teorico.csv

Uso:
    python 3_agregar_lote.py [--cache-dir <path>] [--inv-path <COMPILADO>.xlsx]
                             [--apenas <categoria>] (default: RECEBIMENTO_LF_RENDER)
"""
import argparse
import os
import sys
from collections import defaultdict

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import (
    COMPANY_NAME, INVENTARIO_DIR_DEFAULT,
    norm_cod, norm_lote, garantir_cache_dir,
)


def carregar_inv_fisico(path):
    """Le COMPILADO INV em 3 abas (FB, LF, CD). Retorna DataFrame agregado."""
    rows = []
    for filial in ['FB', 'LF', 'CD']:
        df = pd.read_excel(path, sheet_name=filial)
        df.columns = [c.strip().upper() for c in df.columns]
        df = df.rename(columns={c: 'LOTE' for c in df.columns if c.strip() == 'LOTE'})
        df['cod'] = df['CODIGO'].apply(norm_cod)
        df = df[df['cod'].str.isdigit()]
        df['lote'] = df['LOTE'].apply(norm_lote)
        df['qtd'] = pd.to_numeric(df['QTD'], errors='coerce').fillna(0)
        df['filial'] = filial
        rows.append(df[['filial', 'cod', 'lote', 'qtd']])
    inv = pd.concat(rows, ignore_index=True)
    return inv.groupby(['filial', 'cod', 'lote'], as_index=False)['qtd'].sum()


def aplicar_movs(inv_fisico, movs):
    """Aplica movs ao inv_fisico. Retorna DataFrame com saldo teorico por lote."""
    # Estado inicial
    estado = defaultdict(lambda: {'inicial': 0.0, 'entrada': 0.0, 'saida': 0.0})
    for _, r in inv_fisico.iterrows():
        chave = (r['filial'], r['cod'], r['lote'])
        estado[chave]['inicial'] += r['qtd']

    aplicadas = 0
    ignoradas = 0
    for _, m in movs.iterrows():
        cod = m['cod']
        lote = m['lote']
        qty = m['qty_done']
        filial = m['filial']
        if not cod or not str(cod).isdigit() or qty == 0:
            ignoradas += 1
            continue
        src = bool(m.get('src_interna', False))
        dst = bool(m.get('dst_interna', False))
        if not (src or dst):
            ignoradas += 1
            continue
        chave = (filial, cod, lote)
        if src:
            estado[chave]['saida'] += qty
        if dst:
            estado[chave]['entrada'] += qty
        aplicadas += 1

    rows = []
    for (filial, cod, lote), v in estado.items():
        qtd_teorica = v['inicial'] + v['entrada'] - v['saida']
        rows.append({
            'filial': filial, 'cod': cod, 'lote': lote,
            'qtd_inicial_inv': v['inicial'],
            'qtd_movs_entrada': v['entrada'],
            'qtd_movs_saida': v['saida'],
            'qtd_teorica': qtd_teorica,
        })
    print(f'  Movs aplicadas: {aplicadas} | ignoradas (virtuais/cod invalido): {ignoradas}')
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache-dir', default=None)
    ap.add_argument('--inv-path', default=os.path.join(INVENTARIO_DIR_DEFAULT,
                                                       'COMPILADO INV. 16.05.2026.xlsx'))
    ap.add_argument('--apenas', default='RECEBIMENTO_LF_RENDER',
                    help='Filtra movs por origem_classificada (CSV). Default: RECEBIMENTO_LF_RENDER')
    args = ap.parse_args()

    cache_dir = garantir_cache_dir(args.cache_dir) if args.cache_dir else garantir_cache_dir()

    print(f'Lendo inventario fisico: {args.inv_path}')
    inv = carregar_inv_fisico(args.inv_path)
    print(f'  {len(inv)} (filial, cod, lote) no inventario')

    movs_path = os.path.join(cache_dir, 'movimentacoes.csv')
    if not os.path.exists(movs_path):
        sys.exit(f'ERRO: {movs_path} nao existe. Rode 2_baixar_movimentacoes.py antes.')

    print(f'Lendo movs: {movs_path}')
    movs = pd.read_csv(movs_path, low_memory=False)
    # garantir tipos
    movs['cod'] = movs['cod'].apply(norm_cod)
    movs['lote'] = movs['lote'].apply(norm_lote)
    movs['qty_done'] = pd.to_numeric(movs['qty_done'], errors='coerce').fillna(0)
    print(f'  {len(movs)} movs no CSV')

    # Filtrar APENAS as categorias permitidas (nao-ajuste)
    categorias = [c.strip() for c in args.apenas.split(',') if c.strip()]
    movs_filtradas = movs[movs['origem_classificada'].isin(categorias)].copy()
    print(f'  {len(movs_filtradas)} movs APLICADAS (origem_classificada in {categorias})')
    print(f'  {len(movs) - len(movs_filtradas)} DESCARTADAS (sao ajustes — fora do teorico)')

    print('Aplicando movs ao inventario fisico...')
    teorico = aplicar_movs(inv, movs_filtradas)

    out_path = os.path.join(cache_dir, 'inv_teorico.csv')
    teorico.to_csv(out_path, index=False)
    print(f'\nOK. {len(teorico)} (filial, cod, lote) salvos em {out_path}')

    # Resumo
    print('\n=== Resumo teorico ===')
    print(teorico.groupby('filial', as_index=False).agg(
        n_chaves=('cod', 'count'),
        inv_inicial=('qtd_inicial_inv', 'sum'),
        movs_entrada=('qtd_movs_entrada', 'sum'),
        movs_saida=('qtd_movs_saida', 'sum'),
        qtd_teorica=('qtd_teorica', 'sum'),
    ).to_string(index=False, float_format=lambda x: f'{x:>14,.2f}'))


if __name__ == '__main__':
    main()
