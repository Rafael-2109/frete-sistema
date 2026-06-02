# etapa: monitor
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""Export Excel sob demanda (complementa o pipeline do monitor):

  Aba 1 'Movimentacoes'    : todas as stock.move.line desde 16/05 (cache do script 2)
                             — data, empresa, cod, produto, lote, qtd, origem, destino, usuario
  Aba 2 'Estoque_por_Local': stock.quant interno Odoo (FB/CD/LF) por local
                             — empresa, local, cod, produto, lote, qtd, qtd_reservada
  Aba 3 'Estoque_Sistema'  : saldo do SISTEMA no Render (movimentacao_estoque)
                             — cod, produto, qtd, ultima_mov, data_extracao

Nome do produto = `product.product.name` (campo real, SEM o prefixo [default_code]
que vem no display_name da tupla many2one).

Pre-requisito: rodar antes 2_baixar_movimentacoes.py (gera movimentacoes.csv no cache).

Uso:
    python scripts/inventario_2026_05/monitor/export_excel_completo.py
    python scripts/inventario_2026_05/monitor/export_excel_completo.py --output-name MEU_NOME.xlsx
"""
import argparse
import datetime as _dt
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import (
    COMPANIES, COMPANY_NAME, ODOO_BATCH_SIZE, ENV_RENDER_DB_URL,
    norm_cod, m2o_id, m2o_name, garantir_cache_dir, garantir_relatorios_dir,
)


def buscar_produto_info(odoo, pids):
    """pid -> (name_limpo, cod). name = product.product.name (sem prefixo [###])."""
    info = {}
    pids = sorted({int(p) for p in pids if p is not None and not pd.isna(p)})
    for i in range(0, len(pids), ODOO_BATCH_SIZE):
        for r in odoo.read('product.product', pids[i:i + ODOO_BATCH_SIZE],
                           ['name', 'default_code']):
            info[r['id']] = (r.get('name') or '', norm_cod(r.get('default_code') or ''))
    return info


def buscar_lote_names(odoo, lot_ids):
    """lot_id -> name (real, sem normalizar) para a coluna lote das movs."""
    nomes = {}
    lot_ids = sorted({int(x) for x in lot_ids if x is not None and not pd.isna(x)})
    for i in range(0, len(lot_ids), ODOO_BATCH_SIZE):
        for r in odoo.read('stock.lot', lot_ids[i:i + ODOO_BATCH_SIZE], ['name']):
            nomes[r['id']] = r.get('name') or ''
    return nomes


def baixar_estoque_por_local(odoo):
    """stock.quant interno (FB/CD/LF) SEM agregar — mantem local, lote e reserva."""
    print(f'Buscando stock.quant interno em companies {COMPANIES}...')
    domain = [('company_id', 'in', COMPANIES), ('location_id.usage', '=', 'internal')]
    qids = odoo.search('stock.quant', domain)
    print(f'  {len(qids)} quants')
    fields = ['id', 'company_id', 'product_id', 'lot_id', 'location_id',
              'quantity', 'reserved_quantity']
    rows = []
    for i in range(0, len(qids), ODOO_BATCH_SIZE):
        rows.extend(odoo.read('stock.quant', qids[i:i + ODOO_BATCH_SIZE], fields))
    df = pd.DataFrame(rows)
    df['company_id_n'] = df['company_id'].apply(m2o_id)
    df['empresa'] = df['company_id_n'].map(COMPANY_NAME).fillna('?')
    df['product_id_n'] = df['product_id'].apply(m2o_id)
    df['lote'] = df['lot_id'].apply(m2o_name)
    df['local'] = df['location_id'].apply(m2o_name)
    df['qtd'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
    df['qtd_reservada'] = pd.to_numeric(df['reserved_quantity'], errors='coerce').fillna(0)
    return df


def saldo_sistema_render():
    """Saldo do sistema (movimentacao_estoque no Render) por cod_produto.
    qtd_movimentacao ja tem sinal embutido (ENTRADA/PRODUCAO +, FATURAMENTO/CONSUMO -)."""
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..', '..', '.env')))
    except ImportError:
        pass
    url = os.environ.get(ENV_RENDER_DB_URL)
    if not url:
        print(f'AVISO: {ENV_RENDER_DB_URL} nao configurada — aba Estoque_Sistema vazia')
        return pd.DataFrame(columns=['cod', 'nome_sistema', 'qtd', 'ultima_mov'])
    import psycopg2
    conn = psycopg2.connect(url, connect_timeout=15)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT cod_produto,
               MAX(nome_produto) AS nome_sistema,
               SUM(qtd_movimentacao) AS qtd,
               MAX(data_movimentacao) AS ultima_mov
        FROM movimentacao_estoque
        WHERE ativo = true
        GROUP BY cod_produto
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    df = pd.DataFrame(rows, columns=['cod', 'nome_sistema', 'qtd', 'ultima_mov'])
    df['cod'] = df['cod'].apply(norm_cod)
    df['qtd'] = pd.to_numeric(df['qtd'], errors='coerce').fillna(0)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache-dir', default=None)
    ap.add_argument('--output-name', default=None)
    args = ap.parse_args()

    cache_dir = garantir_cache_dir(args.cache_dir) if args.cache_dir else garantir_cache_dir()
    rel_dir = garantir_relatorios_dir()

    movs_path = os.path.join(cache_dir, 'movimentacoes.csv')
    if not os.path.exists(movs_path):
        sys.exit(f'ERRO: {movs_path} nao existe. Rode 2_baixar_movimentacoes.py antes.')
    movs = pd.read_csv(movs_path, low_memory=False)
    movs['cod'] = movs['cod'].apply(norm_cod)
    print(f'Movimentacoes lidas: {len(movs)}')

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.odoo.utils.connection import get_odoo_connection
        from app.utils.timezone import agora_brasil
        odoo = get_odoo_connection()
        data_extracao = agora_brasil().strftime('%Y-%m-%d %H:%M:%S')

        est = baixar_estoque_por_local(odoo)

        pids = set(movs['product_id_n'].dropna().tolist()) | set(est['product_id_n'].dropna().tolist())
        info = buscar_produto_info(odoo, pids)
        lote_nomes = buscar_lote_names(odoo, movs['lot_id_n'].dropna().tolist())

    def nome(pid):
        return info.get(int(pid), ('', ''))[0] if pd.notna(pid) else ''

    def cod_de(pid):
        return info.get(int(pid), ('', ''))[1] if pd.notna(pid) else ''

    # ----- Aba Movimentacoes -----
    movs['produto'] = movs['product_id_n'].map(nome)
    movs['lote_real'] = movs['lot_id_n'].map(
        lambda x: lote_nomes.get(int(x), '') if pd.notna(x) else '')
    mov_out = movs.rename(columns={
        'date': 'data', 'filial': 'empresa', 'qty_done': 'qtd',
        'loc_src_name': 'origem', 'loc_dst_name': 'destino', 'create_uid_name': 'usuario',
    })
    mov_out['lote'] = mov_out['lote_real']
    cols_mov = ['data', 'empresa', 'cod', 'produto', 'lote', 'qtd',
                'origem', 'destino', 'usuario']
    mov_out = mov_out[cols_mov].sort_values(['empresa', 'data'])

    # ----- Aba Estoque por Local -----
    est['produto'] = est['product_id_n'].map(nome)
    est['cod'] = est['product_id_n'].map(cod_de)
    cols_est = ['empresa', 'local', 'cod', 'produto', 'lote', 'qtd', 'qtd_reservada']
    est_out = est[cols_est].sort_values(['empresa', 'local', 'cod'])

    # ----- Aba Estoque Sistema (Render) -----
    df_render = saldo_sistema_render()
    if len(df_render):
        cod_para_name = {c: n for (n, c) in info.values() if c}
        df_render['produto'] = df_render.apply(
            lambda r: cod_para_name.get(str(r['cod'])) or r['nome_sistema'], axis=1)
        df_render['data_extracao'] = data_extracao
        df_render = df_render[['cod', 'produto', 'qtd', 'ultima_mov', 'data_extracao']]
        df_render = df_render.sort_values('cod')

    ts = _dt.datetime.now().strftime('%Y-%m-%d_%H-%M')
    out_name = args.output_name or f'MOVS_ESTOQUE_RENDER_{ts}.xlsx'
    out_path = os.path.join(rel_dir, out_name)
    print(f'\nEscrevendo {out_path}...')
    with pd.ExcelWriter(out_path, engine='xlsxwriter') as writer:
        mov_out.to_excel(writer, sheet_name='Movimentacoes', index=False)
        est_out.to_excel(writer, sheet_name='Estoque_por_Local', index=False)
        if len(df_render):
            df_render.to_excel(writer, sheet_name='Estoque_Sistema', index=False)

    print(f'OK. {out_path}')
    print(f'  Movimentacoes:     {len(mov_out)} linhas')
    print(f'  Estoque por local: {len(est_out)} linhas')
    print(f'  Estoque sistema:   {len(df_render)} produtos (extracao: {data_extracao})')


if __name__ == '__main__':
    main()
