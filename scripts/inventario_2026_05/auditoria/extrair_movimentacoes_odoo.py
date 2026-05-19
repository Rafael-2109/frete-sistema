"""Extrai TODAS as movimentacoes Odoo de 2026-05-16 ate agora, EXCLUINDO
as feitas pelo servico de recebimento LF no Render.

Inclui:
- inventory adjustments (stock.move sem picking) — Onda 5 D007, emergenciais
- pickings do INVENTARIO (rafael) — 14 pickings conhecidos
- moves sem picking ou de outros pickings (manuais, transferencias)

Exclui:
- 7 pickings odoo_picking_id da recebimento_lf
- 4 transfer_out + 3 transfer_in pickings da mesma tabela

Output: docs/inventario-2026-05/07-relatorios/MOVIMENTACOES_ODOO_2026_05_18.xlsx
"""
import os
import sys
import time
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

RELATORIOS_DIR = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/07-relatorios'
OUT_PATH = os.path.join(RELATORIOS_DIR, 'MOVIMENTACOES_ODOO_2026_05_18.xlsx')

DATA_INICIO = '2026-05-16 00:00:00'
COMPANIES = [1, 4, 5]
COMPANY_NAME = {1: 'FB', 4: 'CD', 5: 'LF'}

BATCH_SIZE = 200


def main():
    print('=' * 70)
    print('EXTRACAO DE MOVIMENTACOES ODOO desde 16/05/2026')
    print('=' * 70)

    # ===== 1. Coletar listas de exclusao e inclusao =====
    from app import create_app, db
    app = create_app()
    with app.app_context():
        rec_main = db.session.execute(db.text("""
            SELECT odoo_picking_id, odoo_transfer_out_picking_id, odoo_transfer_in_picking_id
            FROM recebimento_lf
            WHERE criado_em >= '2026-05-16'
        """)).fetchall()
        pickings_excluir = set()
        for row in rec_main:
            for pid in row:
                if pid:
                    pickings_excluir.add(int(pid))

        inv_pickings = db.session.execute(db.text("""
            SELECT DISTINCT picking_id_odoo
            FROM ajuste_estoque_inventario
            WHERE ciclo='INVENTARIO_2026_05' AND picking_id_odoo IS NOT NULL
        """)).scalars().all()
        pickings_inventario = set(int(p) for p in inv_pickings if p)

    print(f'\nPickings a EXCLUIR (recebimento LF Render): {len(pickings_excluir)}')
    print(f'  IDs: {sorted(pickings_excluir)}')
    print(f'\nPickings INVENTARIO conhecidos: {len(pickings_inventario)}')
    print(f'  IDs: {sorted(pickings_inventario)}')

    # ===== 2. Conectar Odoo =====
    from app.odoo.utils.connection import get_odoo_connection
    print('\nConectando Odoo...')
    odoo = get_odoo_connection()

    # ===== 3. Buscar stock.move.line desde 16/05 nas 3 companies =====
    print(f'\nBuscando stock.move.line com date >= {DATA_INICIO} em companies {COMPANIES}...')
    domain = [
        ('date', '>=', DATA_INICIO),
        ('company_id', 'in', COMPANIES),
        ('state', '=', 'done'),
    ]
    move_line_ids = odoo.search('stock.move.line', domain)
    print(f'  Total stock.move.line encontrados: {len(move_line_ids)}')

    if not move_line_ids:
        print('Nenhuma movimentacao encontrada. Saindo.')
        return

    # ===== 4. Buscar dados em batches =====
    fields = [
        'id', 'date', 'create_date', 'company_id',
        'product_id', 'product_uom_id', 'qty_done',
        'lot_id', 'lot_name',
        'location_id', 'location_dest_id',
        'picking_id', 'move_id', 'reference',
        'origin', 'create_uid', 'write_uid',
        'owner_id', 'state',
    ]
    moves = []
    t0 = time.time()
    for i in range(0, len(move_line_ids), BATCH_SIZE):
        batch = move_line_ids[i:i + BATCH_SIZE]
        try:
            data = odoo.read('stock.move.line', batch, fields)
        except Exception as e:
            print(f'  batch {i}: erro {e} — tentando com fields menores')
            data = odoo.read('stock.move.line', batch, ['id', 'date', 'company_id',
                                                         'product_id', 'qty_done',
                                                         'lot_id', 'picking_id', 'origin',
                                                         'location_id', 'location_dest_id',
                                                         'reference', 'create_uid', 'state'])
        moves.extend(data)
        elapsed = time.time() - t0
        print(f'  {i + len(batch)}/{len(move_line_ids)} ({elapsed:.0f}s)', end='\r')
    print(f'\n  OK. {len(moves)} linhas lidas em {time.time() - t0:.0f}s')

    df = pd.DataFrame(moves)

    # ===== 5. Normalizar many2one (vem como [id, name] ou False) =====
    def m2o_id(x):
        if isinstance(x, list) and len(x) >= 1:
            return x[0]
        return None

    def m2o_name(x):
        if isinstance(x, list) and len(x) >= 2:
            return x[1]
        return ''

    for col in ['company_id', 'product_id', 'product_uom_id', 'lot_id',
                'location_id', 'location_dest_id', 'picking_id', 'move_id',
                'create_uid', 'write_uid', 'owner_id']:
        if col in df.columns:
            df[f'{col}_id'] = df[col].apply(m2o_id)
            df[f'{col}_name'] = df[col].apply(m2o_name)

    # ===== 6. Buscar default_code dos produtos =====
    product_ids = df['product_id_id'].dropna().unique().tolist()
    print(f'\nBuscando default_code de {len(product_ids)} produtos...')
    product_map = {}
    for i in range(0, len(product_ids), BATCH_SIZE):
        batch = product_ids[i:i + BATCH_SIZE]
        data = odoo.read('product.product', list(batch), ['default_code', 'name'])
        for p in data:
            product_map[p['id']] = (p.get('default_code') or '', p.get('name') or '')
    df['cod_produto'] = df['product_id_id'].map(lambda x: product_map.get(x, ('', ''))[0])
    df['nome_produto'] = df['product_id_id'].map(lambda x: product_map.get(x, ('', ''))[1])

    # ===== 7. Classificar origem =====
    # PRIORIDADE: inventario > recebimento_lf. Pickings em AMBAS as listas
    # foram criados pelo INVENTARIO (Rafael) mas registrados tambem em
    # recebimento_lf porque o pipeline LF->FB reusa RecebimentoLfOdooService.processar_transfer_only.
    pickings_excluir_efetivo = pickings_excluir - pickings_inventario
    print(f'\nPickings overlapping (inventario + recebimento_lf): {sorted(pickings_excluir & pickings_inventario)}')
    print(f'Pickings excluir EFETIVO (so recebimento_lf puro): {sorted(pickings_excluir_efetivo)}')

    def classificar(row):
        pid = row.get('picking_id_id')
        if pid is None or pd.isna(pid):
            return 'INVENTORY_ADJUST'  # sem picking = inventory adjust direto (Rafael / pre-etapa)
        pid = int(pid)
        if pid in pickings_inventario:
            return 'INVENTARIO_PICKING'  # prioridade
        if pid in pickings_excluir_efetivo:
            return 'RECEBIMENTO_LF_RENDER'
        return 'OUTROS_PICKING'

    df['origem_classificada'] = df.apply(classificar, axis=1)

    # ===== 8. Manter apenas o que o Rafael pediu (excluir RECEBIMENTO_LF_RENDER) =====
    df_incluir = df[df['origem_classificada'] != 'RECEBIMENTO_LF_RENDER'].copy()
    df_excluir = df[df['origem_classificada'] == 'RECEBIMENTO_LF_RENDER'].copy()

    print(f'\n=== Classificacao ===')
    cnt = df['origem_classificada'].value_counts()
    for k, v in cnt.items():
        print(f'  {k}: {v}')

    # ===== 9. Filial e tipo de movimento =====
    df_incluir['filial'] = df_incluir['company_id_id'].map(COMPANY_NAME).fillna('?')

    def tipo_mov(row):
        loc_src = row.get('location_id_name', '') or ''
        loc_dst = row.get('location_dest_id_name', '') or ''
        if 'Virtual' in loc_src or 'Virtual' in loc_dst:
            return 'AJUSTE_INVENTARIO'
        if loc_src.startswith('FB/') and loc_dst.startswith('FB/'):
            return 'INTERNA_FB'
        if loc_src.startswith('CD/') and loc_dst.startswith('CD/'):
            return 'INTERNA_CD'
        if loc_src.startswith('LF/') and loc_dst.startswith('LF/'):
            return 'INTERNA_LF'
        if (loc_src.startswith('FB/') and loc_dst.startswith('CD/')) or \
           (loc_src.startswith('CD/') and loc_dst.startswith('FB/')):
            return 'INTER_FB_CD'
        if (loc_src.startswith('FB/') and loc_dst.startswith('LF/')) or \
           (loc_src.startswith('LF/') and loc_dst.startswith('FB/')):
            return 'INTER_FB_LF'
        if (loc_src.startswith('CD/') and loc_dst.startswith('LF/')) or \
           (loc_src.startswith('LF/') and loc_dst.startswith('CD/')):
            return 'INTER_CD_LF'
        if 'Partner' in loc_src or 'Partner' in loc_dst or 'Cliente' in loc_src or 'Cliente' in loc_dst:
            return 'FATURAMENTO'
        return 'OUTROS'

    df_incluir['tipo_movimento'] = df_incluir.apply(tipo_mov, axis=1)

    # ===== 10. Resumos =====
    resumo_origem = df_incluir.groupby(['filial', 'origem_classificada'], as_index=False).agg(
        n=('id', 'count'),
        qty_total=('qty_done', 'sum')
    )
    resumo_tipo = df_incluir.groupby(['filial', 'tipo_movimento'], as_index=False).agg(
        n=('id', 'count'),
        qty_total=('qty_done', 'sum')
    )
    resumo_dia = df_incluir.copy()
    resumo_dia['data'] = pd.to_datetime(resumo_dia['date']).dt.date
    resumo_dia = resumo_dia.groupby(['data', 'filial'], as_index=False).agg(
        n=('id', 'count'),
        qty_total=('qty_done', 'sum')
    )

    # Quem criou (por user) — ajuda Rafael identificar "do dele" vs operacao normal
    resumo_user = df_incluir.groupby(
        ['filial', 'origem_classificada', 'create_uid_name'], as_index=False
    ).agg(n=('id', 'count'), qty_total=('qty_done', 'sum'))
    resumo_user = resumo_user.sort_values(['filial', 'n'], ascending=[True, False])

    # Sumario por picking (1 linha por picking_id, agregado)
    if 'picking_id_id' in df_incluir.columns:
        with_pick = df_incluir[df_incluir['picking_id_id'].notna()].copy()
        sumario_picking = with_pick.groupby(
            ['picking_id_id', 'picking_id_name', 'filial', 'origem_classificada',
             'tipo_movimento'],
            as_index=False
        ).agg(
            n_moves=('id', 'count'),
            qty_total=('qty_done', 'sum'),
            data_primeira=('date', 'min'),
            data_ultima=('date', 'max'),
            origin=('origin', 'first'),
            reference=('reference', 'first'),
            create_uid=('create_uid_name', 'first')
        )
        sumario_picking = sumario_picking.sort_values('data_primeira')
    else:
        sumario_picking = pd.DataFrame()

    # ===== 11. Escrever Excel =====
    os.makedirs(RELATORIOS_DIR, exist_ok=True)
    print(f'\nEscrevendo {OUT_PATH}...')

    cols_out = [
        'id', 'date', 'create_date', 'state',
        'filial', 'company_id_id',
        'cod_produto', 'nome_produto', 'product_id_id',
        'lot_id_id', 'lot_id_name', 'lot_name',
        'qty_done',
        'location_id_id', 'location_id_name',
        'location_dest_id_id', 'location_dest_id_name',
        'picking_id_id', 'picking_id_name',
        'move_id_id', 'reference', 'origin',
        'create_uid_id', 'create_uid_name',
        'origem_classificada', 'tipo_movimento'
    ]
    cols_out = [c for c in cols_out if c in df_incluir.columns]

    with pd.ExcelWriter(OUT_PATH, engine='xlsxwriter') as writer:
        # README
        readme = pd.DataFrame([
            ['Data analise', '2026-05-18'],
            ['Periodo', '2026-05-16 00:00 ate agora'],
            ['Companies', 'FB(1), CD(4), LF(5)'],
            ['Modelo Odoo', 'stock.move.line (state=done)'],
            ['Total bruto Odoo', len(df)],
            ['EXCLUIDAS (recebimento_lf Render)', len(df_excluir)],
            ['INCLUIDAS (Rafael + outras)', len(df_incluir)],
            ['', ''],
            ['Pickings excluidos', f'{len(pickings_excluir)} ({sorted(pickings_excluir)})'],
            ['Pickings inventario marcados', f'{len(pickings_inventario)} ({sorted(pickings_inventario)})'],
            ['', ''],
            ['origem_classificada', ''],
            ['  INVENTORY_ADJUST', 'sem picking — inventory adjustment direto (Onda 5 D007, emergenciais E01-E10, RENOMEAR_LOTE)'],
            ['  INVENTARIO_PICKING', 'picking criado pelo pipeline INVENTARIO (Onda 1 LF, Onda 2 FB-CD)'],
            ['  OUTROS_PICKING', 'picking nao classificado — pode ser manual, transferencia normal, etc.'],
            ['  RECEBIMENTO_LF_RENDER', 'EXCLUIDO — recebimento LF normal via worker Render'],
            ['', ''],
            ['tipo_movimento', 'derivado das locations origem/destino'],
        ], columns=['Campo', 'Valor'])
        readme.to_excel(writer, sheet_name='README', index=False)

        # Resumos
        resumo_origem.to_excel(writer, sheet_name='1_Resumo_Origem', index=False)
        resumo_tipo.to_excel(writer, sheet_name='2_Resumo_Tipo', index=False)
        resumo_dia.to_excel(writer, sheet_name='3_Resumo_Dia', index=False)
        resumo_user.to_excel(writer, sheet_name='3b_Por_User', index=False)
        if len(sumario_picking):
            sumario_picking.to_excel(writer, sheet_name='3c_Sumario_Picking', index=False)

        # Detalhe completo
        df_incluir[cols_out].sort_values('date').to_excel(
            writer, sheet_name='4_Movimentacoes_TODAS', index=False
        )

        # Por categoria (abas separadas para facilitar)
        for cat in ['INVENTORY_ADJUST', 'INVENTARIO_PICKING', 'OUTROS_PICKING']:
            sub = df_incluir[df_incluir['origem_classificada'] == cat]
            if len(sub) > 0 and len(sub) <= 1_000_000:
                sheet_name = f'5_{cat[:25]}'
                sub[cols_out].sort_values('date').to_excel(
                    writer, sheet_name=sheet_name, index=False
                )

        # EXCLUIDAS (auditoria) — separado em aba final, so 7 pickings
        if len(df_excluir) > 0:
            df_excluir['filial'] = df_excluir['company_id_id'].map(COMPANY_NAME)
            df_excluir[[c for c in cols_out if c in df_excluir.columns]].sort_values('date').to_excel(
                writer, sheet_name='9_Excluidas_Rec_LF', index=False
            )

    print(f'\nOK. {OUT_PATH}')
    print(f'\n=== Resumo por origem ===')
    print(resumo_origem.to_string(index=False))
    print(f'\n=== Resumo por tipo de movimento ===')
    print(resumo_tipo.to_string(index=False))


if __name__ == '__main__':
    main()
