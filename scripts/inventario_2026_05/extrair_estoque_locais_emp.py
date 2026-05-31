"""Extrai estoque ATUAL do Odoo para todas as 4 companies (FB/SC/CD/LF).

Modo DEFAULT (inventario): filtra apenas locais internos {emp}/* EXCETO os
locais 'Indisponivel'.

Locais Indisponivel excluidos no modo default (D011):
  - 31088 FB/Indisponivel
  - 31089 SC/Indisponivel
  - 31090 CD/Indisponivel
  - 31091 LF/Indisponivel

Modo --completo (relatorio completo): NAO exclui Indisponivel e NAO filtra so
locais raiz — inclui TODOS os locais fisicos (location_id.usage = 'internal')
de todas as empresas. Adiciona colunas `local_tipo` (Estoque/Indisponivel) e
`is_migracao` (lote MIGRACAO = estoque fantasma) para o usuario separar
estoque real de fantasma.

Output: Excel com 3 abas:
  1) Estoque       - linha por (filial, location, produto, lote)
  2) Resumo Filial - totais agregados por company
  3) Resumo Local  - totais por location_id

Uso:
    source .venv/bin/activate
    # Modo inventario (default — exclui Indisponivel):
    python scripts/inventario_2026_05/extrair_estoque_locais_emp.py
    # Modo relatorio completo (todos os locais internos):
    python scripts/inventario_2026_05/extrair_estoque_locais_emp.py --completo
    python scripts/inventario_2026_05/extrair_estoque_locais_emp.py --completo --output /caminho/arquivo.xlsx
"""
import argparse
import os
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


# ===== Constantes =====
COMPANIES = [1, 3, 4, 5]
COMPANY_NAME = {1: 'FB', 3: 'SC', 4: 'CD', 5: 'LF'}
COMPANY_FULL = {
    1: 'NACOM GOYA - FB',
    3: 'NACOM GOYA - SC',
    4: 'NACOM GOYA - CD',
    5: 'LA FAMIGLIA - LF',
}
LOCAIS_INDISPONIVEL_IDS = [31088, 31089, 31090, 31091]
ODOO_BATCH_SIZE = 200

LOTES_PROXY_VAZIO = {'P-15/05'}

# Variantes de encoding do lote MIGRACAO (estoque fantasma — nao e real)
LOTES_MIGRACAO = {'MIGRACAO', 'MIGRAÇÃO', 'MIGRACÃO', 'MIGRAÇAO', 'MIG'}


def is_migracao(lot_name):
    """True se o nome bruto do lote for variante de MIGRACAO."""
    if not lot_name:
        return False
    return str(lot_name).upper().strip() in LOTES_MIGRACAO


def classificar_local(location_id):
    """Classifica o local: 'Indisponivel' (location especial) ou 'Estoque'."""
    if location_id in LOCAIS_INDISPONIVEL_IDS:
        return 'Indisponivel'
    return 'Estoque'


# ===== Helpers =====
def m2o_id(x):
    if isinstance(x, list) and len(x) >= 1:
        return x[0]
    return None


def m2o_name(x):
    if isinstance(x, list) and len(x) >= 2:
        return x[1]
    return ''


def norm_cod(x):
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


def norm_lote(x):
    if x is None:
        return ''
    if isinstance(x, float):
        if pd.isna(x):
            return ''
        if x == int(x):
            s = str(int(x))
        else:
            s = str(x)
    elif isinstance(x, int):
        s = str(x)
    else:
        s = str(x).strip()
    if s in LOTES_PROXY_VAZIO:
        return ''
    return s


def is_location_emp_root(loc_name):
    """Verdadeiro se loc_name comeca com FB/, SC/, CD/ ou LF/ e nao e virtual."""
    if not loc_name:
        return False
    prefixos = ('FB/', 'SC/', 'CD/', 'LF/')
    if not loc_name.startswith(prefixos):
        return False
    # Defensivo: excluir qualquer "Virtual/Production/Parceiros" se aparecer como interno
    virtual_kw = ['Virtual', 'Production', 'Inventory adjustment', 'Customers', 'Vendors']
    return not any(k in loc_name for k in virtual_kw)


# ===== Extracao =====
def baixar_estoque(odoo, completo=False, companies=None):
    companies = companies or COMPANIES
    if completo:
        print(f'Buscando stock.quant em companies {companies} (TODOS os locais internal — modo completo)...')
        domain = [
            ('company_id', 'in', companies),
            ('location_id.usage', '=', 'internal'),
        ]
    else:
        print(f'Buscando stock.quant em companies {companies} (location internal, exceto Indisponivel)...')
        domain = [
            ('company_id', 'in', companies),
            ('location_id.usage', '=', 'internal'),
            ('location_id', 'not in', LOCAIS_INDISPONIVEL_IDS),
        ]
    qids = odoo.search('stock.quant', domain)
    print(f'  {len(qids)} quants encontrados')

    rows = []
    t0 = time.time()
    fields = ['id', 'company_id', 'product_id', 'lot_id',
              'location_id', 'quantity', 'reserved_quantity', 'value']
    for i in range(0, len(qids), ODOO_BATCH_SIZE):
        batch = qids[i:i + ODOO_BATCH_SIZE]
        data = odoo.read('stock.quant', batch, fields)
        rows.extend(data)
        print(f'  {i + len(batch)}/{len(qids)} ({time.time() - t0:.0f}s)', end='\r')
    print()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df['company_id_n'] = df['company_id'].apply(m2o_id)
    df['filial'] = df['company_id_n'].map(COMPANY_NAME).fillna('?')
    df['product_id_n'] = df['product_id'].apply(m2o_id)
    df['product_name'] = df['product_id'].apply(m2o_name)
    df['lot_id_n'] = df['lot_id'].apply(m2o_id)
    df['lot_name'] = df['lot_id'].apply(m2o_name)
    df['lote'] = df['lot_name'].apply(norm_lote)
    df['location_id_n'] = df['location_id'].apply(m2o_id)
    df['location_name'] = df['location_id'].apply(m2o_name)
    df['qtd'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
    df['reservado'] = pd.to_numeric(df['reserved_quantity'], errors='coerce').fillna(0)
    df['valor'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)

    # Classificacao de local + flag migracao (estoque fantasma)
    df['local_tipo'] = df['location_id_n'].apply(classificar_local)
    df['is_migracao'] = df['lot_name'].apply(is_migracao)

    if not completo:
        # Modo inventario: garantir filtro de locais raiz {emp}/ (e nao filhos virtuais)
        df = df[df['location_name'].apply(is_location_emp_root)].copy()

    # buscar default_code
    pids = df['product_id_n'].dropna().unique().tolist()
    print(f'Buscando default_code de {len(pids)} produtos...')
    pmap = {}
    for i in range(0, len(pids), ODOO_BATCH_SIZE):
        b = pids[i:i + ODOO_BATCH_SIZE]
        d = odoo.read('product.product', list(b), ['default_code'])
        for p in d:
            pmap[p['id']] = p.get('default_code') or ''
    df['cod'] = df['product_id_n'].map(lambda x: pmap.get(x, ''))
    df['cod'] = df['cod'].apply(norm_cod)

    # Manter linhas sem cod (paletes / itens sem default_code) -> marcar
    df['cod_display'] = df['cod'].where(df['cod'].astype(bool), other='(sem cod)')

    # Saldo disponivel = quantity - reserved
    df['disponivel'] = df['qtd'] - df['reservado']

    # Custo unitario
    df['custo_unit'] = np.where(df['qtd'] > 0, df['valor'] / df['qtd'], 0)

    # agregar por (filial, location_name, cod, lote)
    out = df.groupby(
        ['filial', 'company_id_n', 'location_id_n', 'location_name',
         'cod_display', 'lote'],
        as_index=False,
    ).agg(
        qtd=('qtd', 'sum'),
        reservado=('reservado', 'sum'),
        disponivel=('disponivel', 'sum'),
        valor=('valor', 'sum'),
        n_quants=('id', 'count'),
        nome_produto=('product_name', 'first'),
        local_tipo=('local_tipo', 'first'),
        is_migracao=('is_migracao', 'first'),
    )
    out['custo_unit'] = np.where(out['qtd'] > 0, out['valor'] / out['qtd'], 0)

    # Renomear cod_display -> cod (mais limpo na saida)
    out = out.rename(columns={'cod_display': 'cod'})

    # Reorganizar colunas
    cols = ['filial', 'company_id_n', 'location_id_n', 'location_name', 'local_tipo',
            'cod', 'nome_produto', 'lote', 'is_migracao',
            'qtd', 'reservado', 'disponivel', 'custo_unit', 'valor', 'n_quants']
    out = out[cols]

    # Ordenar
    out = out.sort_values(['filial', 'location_name', 'cod', 'lote']).reset_index(drop=True)
    return out


def gerar_resumos(df):
    """Retorna (resumo_filial, resumo_local)."""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    resumo_filial = df.groupby('filial', as_index=False).agg(
        n_skus=('cod', 'nunique'),
        n_linhas=('cod', 'count'),
        qtd_total=('qtd', 'sum'),
        reservado_total=('reservado', 'sum'),
        disponivel_total=('disponivel', 'sum'),
        valor_total=('valor', 'sum'),
    ).sort_values('filial').reset_index(drop=True)

    resumo_local = df.groupby(
        ['filial', 'location_id_n', 'location_name'], as_index=False
    ).agg(
        n_skus=('cod', 'nunique'),
        n_linhas=('cod', 'count'),
        qtd_total=('qtd', 'sum'),
        reservado_total=('reservado', 'sum'),
        disponivel_total=('disponivel', 'sum'),
        valor_total=('valor', 'sum'),
    ).sort_values(['filial', 'location_name']).reset_index(drop=True)
    return resumo_filial, resumo_local


def salvar_excel(df, resumo_filial, resumo_local, output_path):
    """Salva Excel multi-sheet com formatacao numerica BR-friendly."""
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        # Aba 1: Estoque detalhado
        df.to_excel(writer, sheet_name='Estoque', index=False)
        # Aba 2: Resumo Filial
        resumo_filial.to_excel(writer, sheet_name='Resumo Filial', index=False)
        # Aba 3: Resumo Local
        resumo_local.to_excel(writer, sheet_name='Resumo Local', index=False)

        wb = writer.book
        fmt_num = wb.add_format({'num_format': '#,##0.000'})
        fmt_int = wb.add_format({'num_format': '#,##0'})
        fmt_money = wb.add_format({'num_format': 'R$ #,##0.00'})
        fmt_header = wb.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})

        # Formatar aba Estoque
        ws = writer.sheets['Estoque']
        # header
        for col_idx, col_name in enumerate(df.columns):
            ws.write(0, col_idx, col_name, fmt_header)
        # larguras
        ws.set_column('A:A', 7)    # filial
        ws.set_column('B:B', 11)   # company_id_n
        ws.set_column('C:C', 12)   # location_id_n
        ws.set_column('D:D', 32)   # location_name
        ws.set_column('E:E', 14)   # local_tipo
        ws.set_column('F:F', 10)   # cod
        ws.set_column('G:G', 42)   # nome_produto
        ws.set_column('H:H', 18)   # lote
        ws.set_column('I:I', 11)   # is_migracao
        ws.set_column('J:L', 13, fmt_num)   # qtd/reservado/disponivel
        ws.set_column('M:M', 13, fmt_num)   # custo_unit
        ws.set_column('N:N', 15, fmt_money) # valor
        ws.set_column('O:O', 9, fmt_int)    # n_quants
        ws.freeze_panes(1, 6)
        ws.autofilter(0, 0, len(df), len(df.columns) - 1)

        # Formatar aba Resumo Filial
        ws = writer.sheets['Resumo Filial']
        for col_idx, col_name in enumerate(resumo_filial.columns):
            ws.write(0, col_idx, col_name, fmt_header)
        ws.set_column('A:A', 8)
        ws.set_column('B:C', 10, fmt_int)
        ws.set_column('D:F', 16, fmt_num)
        ws.set_column('G:G', 18, fmt_money)

        # Formatar aba Resumo Local
        ws = writer.sheets['Resumo Local']
        for col_idx, col_name in enumerate(resumo_local.columns):
            ws.write(0, col_idx, col_name, fmt_header)
        ws.set_column('A:A', 8)
        ws.set_column('B:B', 13)
        ws.set_column('C:C', 36)
        ws.set_column('D:E', 10, fmt_int)
        ws.set_column('F:H', 16, fmt_num)
        ws.set_column('I:I', 18, fmt_money)
        ws.freeze_panes(1, 3)


def main():
    ap = argparse.ArgumentParser(description='Extrai estoque Odoo (stock.quant) por filial/local/produto/lote')
    ap.add_argument('--output', default=None,
                    help='Caminho do .xlsx (default: /tmp/inventario_monitor/estoque_<modo>_<timestamp>.xlsx)')
    ap.add_argument('--completo', action='store_true',
                    help='Inclui TODOS os locais internal (com Indisponivel/MIGRACAO). '
                         'Default: modo inventario (exclui Indisponivel + so locais raiz)')
    ap.add_argument('--empresas', default=None,
                    help='CSV de filiais (FB,SC,CD,LF). Default: todas')
    ap.add_argument('--csv', action='store_true',
                    help='Tambem grava um .csv da aba Estoque ao lado do .xlsx')
    args = ap.parse_args()

    # Resolver empresas -> company_ids
    if args.empresas:
        name_to_id = {v: k for k, v in COMPANY_NAME.items()}
        companies = []
        for nome in args.empresas.split(','):
            nome = nome.strip().upper()
            if nome in name_to_id:
                companies.append(name_to_id[nome])
            else:
                print(f'AVISO: filial desconhecida ignorada: {nome}')
        if not companies:
            print('ERRO: nenhuma filial valida em --empresas')
            return
    else:
        companies = COMPANIES

    modo = 'completo' if args.completo else 'inventario'

    if args.output:
        output_path = args.output
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    else:
        cache_dir = '/tmp/inventario_monitor'
        os.makedirs(cache_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(cache_dir, f'estoque_{modo}_{ts}.xlsx')

    print(f'Modo: {modo} | Empresas: {[COMPANY_NAME.get(c, c) for c in companies]}')
    print(f'Output: {output_path}')

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.odoo.utils.connection import get_odoo_connection
        odoo = get_odoo_connection()
        df = baixar_estoque(odoo, completo=args.completo, companies=companies)

    if df.empty:
        print('ATENCAO: nenhum quant encontrado com os filtros — Excel nao gerado.')
        return

    resumo_filial, resumo_local = gerar_resumos(df)

    salvar_excel(df, resumo_filial, resumo_local, output_path)

    if args.csv:
        csv_path = output_path[:-5] + '.csv' if output_path.endswith('.xlsx') else output_path + '.csv'
        df.to_csv(csv_path, index=False)
        print(f'CSV salvo: {csv_path}')

    print(f'\nOK. Excel salvo: {output_path}')
    print(f'  Linhas (Estoque): {len(df)}')
    print(f'  Locais: {df["location_name"].nunique()}')
    print(f'  SKUs: {df["cod"].nunique()}')

    # Resumo console
    print('\n=== Resumo por Filial ===')
    print(resumo_filial.to_string(index=False,
        float_format=lambda x: f'{x:>14,.2f}'))


if __name__ == '__main__':
    main()
