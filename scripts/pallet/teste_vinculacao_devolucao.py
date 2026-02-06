"""
Teste de Viabilidade: Vincular N Remessas de Pallet a 1 Devolução no Odoo
==========================================================================

Caso real: ATACADÃO 183
- Devolução: CD/IN/07208 (picking_id=300204, move_id=984267, 416 pallets)
- Remessas: N remessas órfãs mais antigas (FIFO) até totalizar ~416 pallets

Abordagem: Opção B — N moves no mesmo picking de devolução,
           cada move vinculado 1:1 à sua remessa de origem.

ETAPAS:
1. Buscar remessas órfãs (FIFO)
2. Selecionar até ~416 pallets
3. Ajustar move existente + criar N-1 novos moves
4. Vincular cada move à sua remessa
5. Verificar resultado
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.odoo.utils.connection import get_odoo_connection


def step1_buscar_remessas_orfas(conn):
    """Busca remessas de pallet do ATACADÃO 183 sem devolução vinculada (FIFO)"""
    print("\n" + "=" * 70)
    print("ETAPA 1: Buscando remessas órfãs do ATACADÃO 183 (FIFO)")
    print("=" * 70)

    # Buscar todas as remessas done do ATACADÃO 183
    remessas = conn.search_read(
        'stock.picking',
        [
            ['picking_type_id', '=', 84],  # CD: Expedição Pallet
            ['partner_id', '=', 88500],     # ATACADÃO 183
            ['state', '=', 'done'],
        ],
        fields=['id', 'name', 'date_done', 'qty_pallets', 'return_ids', 'move_ids'],
        order='date_done asc',
        limit=300
    )

    # Filtrar órfãs (sem return_ids)
    orfas = [r for r in remessas if not r.get('return_ids')]
    print(f"Total remessas: {len(remessas)}")
    print(f"Remessas órfãs: {len(orfas)}")

    return orfas


def step2_selecionar_remessas_fifo(orfas, qtd_alvo=416):
    """Seleciona remessas FIFO até totalizar a quantidade alvo"""
    print("\n" + "=" * 70)
    print(f"ETAPA 2: Selecionando remessas FIFO até ~{qtd_alvo} pallets")
    print("=" * 70)

    selecionadas = []
    acumulado = 0

    for r in orfas:
        qty = r.get('qty_pallets', 0)
        if qty <= 0:
            continue

        selecionadas.append(r)
        acumulado += qty

        print(f"  + {r['name']:30s} | {qty:>5.0f} pallets | acumulado: {acumulado:.0f}")

        if acumulado >= qtd_alvo:
            break

    print(f"\nSelecionadas: {len(selecionadas)} remessas = {acumulado:.0f} pallets (alvo: {qtd_alvo})")

    if acumulado > qtd_alvo:
        # Última remessa será parcial
        excesso = acumulado - qtd_alvo
        ultima = selecionadas[-1]
        qty_parcial = ultima.get('qty_pallets', 0) - excesso
        print(f"  ⚠️  Última remessa {ultima['name']} será parcial: {qty_parcial:.0f} de {ultima['qty_pallets']:.0f}")

    return selecionadas, acumulado


def step3_buscar_moves_remessas(conn, selecionadas):
    """Busca o move de cada remessa selecionada"""
    print("\n" + "=" * 70)
    print("ETAPA 3: Buscando moves das remessas selecionadas")
    print("=" * 70)

    move_ids = []
    for r in selecionadas:
        move_ids.extend(r.get('move_ids', []))

    if not move_ids:
        print("ERRO: Nenhum move encontrado nas remessas!")
        return []

    moves = conn.search_read(
        'stock.move',
        [['id', 'in', move_ids]],
        fields=[
            'id', 'picking_id', 'product_id', 'product_uom_qty',
            'quantity', 'state',
            'origin_returned_move_id', 'returned_move_ids',
            'move_orig_ids', 'move_dest_ids',
            'location_id', 'location_dest_id'
        ]
    )

    for m in moves:
        picking_name = m.get('picking_id', [None, ''])[1] if m.get('picking_id') else '?'
        print(f"  Move {m['id']} | Picking: {picking_name} | Qty: {m.get('product_uom_qty', 0)} | State: {m.get('state')}")

    return moves


def step4_ler_picking_devolucao(conn, picking_id=300204):
    """Lê o picking de devolução e seu move atual"""
    print("\n" + "=" * 70)
    print(f"ETAPA 4: Lendo picking de devolução (id={picking_id})")
    print("=" * 70)

    picking = conn.search_read(
        'stock.picking',
        [['id', '=', picking_id]],
        fields=[
            'id', 'name', 'state', 'partner_id', 'picking_type_id',
            'move_ids', 'return_id', 'is_return_picking', 'return_ids',
            'origin', 'location_id', 'location_dest_id', 'qty_pallets'
        ]
    )

    if not picking:
        print(f"ERRO: Picking {picking_id} não encontrado!")
        return None, None

    p = picking[0]
    print(f"  Name: {p['name']}")
    print(f"  State: {p['state']}")
    print(f"  Partner: {p.get('partner_id', [None, ''])[1] if p.get('partner_id') else 'N/A'}")
    print(f"  Picking Type: {p.get('picking_type_id', [None, ''])[1] if p.get('picking_type_id') else 'N/A'}")
    print(f"  Origin: {p.get('origin', 'N/A')}")
    print(f"  Qty Pallets: {p.get('qty_pallets', 0)}")
    print(f"  return_id: {p.get('return_id')}")
    print(f"  is_return_picking: {p.get('is_return_picking')}")
    print(f"  Location: {p.get('location_id', [None, ''])[1]} → {p.get('location_dest_id', [None, ''])[1]}")

    # Ler move
    move_ids = p.get('move_ids', [])
    moves = []
    if move_ids:
        moves = conn.search_read(
            'stock.move',
            [['id', 'in', move_ids]],
            fields=[
                'id', 'product_id', 'product_uom_qty', 'quantity',
                'state', 'origin_returned_move_id', 'move_orig_ids',
                'location_id', 'location_dest_id'
            ]
        )
        for m in moves:
            print(f"  Move {m['id']}: qty={m.get('product_uom_qty', 0)}, state={m.get('state')}")
            print(f"    origin_returned_move_id: {m.get('origin_returned_move_id')}")
            print(f"    move_orig_ids: {m.get('move_orig_ids')}")

    return p, moves


def step5_testar_vinculacao(conn, picking_dev, move_dev, moves_remessa, selecionadas, qtd_alvo=416):
    """
    Testa a vinculação:
    - Ajusta o move existente para a qty da 1ª remessa
    - Cria N-1 novos moves para as demais remessas
    - Vincula cada move à sua remessa via origin_returned_move_id
    """
    print("\n" + "=" * 70)
    print("ETAPA 5: Executando vinculação (Opção B)")
    print("=" * 70)

    picking_id = picking_dev['id']
    move_dev_id = move_dev[0]['id'] if move_dev else None

    if not move_dev_id:
        print("ERRO: Move de devolução não encontrado!")
        return False

    # Mapear: picking_id → move
    moves_por_picking = {}
    for m in moves_remessa:
        pid = m.get('picking_id', [None])[0] if m.get('picking_id') else None
        if pid:
            moves_por_picking[pid] = m

    # Preparar breakdown FIFO
    breakdown = []
    restante = qtd_alvo

    for r in selecionadas:
        qty_remessa = r.get('qty_pallets', 0)
        move_remessa = moves_por_picking.get(r['id'])

        if not move_remessa:
            print(f"  ⚠️  Remessa {r['name']} sem move encontrado, pulando...")
            continue

        qty_alocar = min(qty_remessa, restante)
        breakdown.append({
            'remessa_picking_id': r['id'],
            'remessa_picking_name': r['name'],
            'remessa_move_id': move_remessa['id'],
            'qty_alocar': qty_alocar,
            'qty_remessa_total': qty_remessa,
        })
        restante -= qty_alocar

        if restante <= 0:
            break

    print(f"\nBreakdown planejado ({len(breakdown)} moves):")
    for i, b in enumerate(breakdown):
        parcial = " (PARCIAL)" if b['qty_alocar'] < b['qty_remessa_total'] else ""
        print(f"  {i+1}. {b['remessa_picking_name']:30s} | {b['qty_alocar']:>5.0f} pallets{parcial} | move_remessa={b['remessa_move_id']}")

    total = sum(b['qty_alocar'] for b in breakdown)
    print(f"\nTotal alocado: {total:.0f} pallets (alvo: {qtd_alvo})")

    if not breakdown:
        print("ERRO: Nenhum breakdown possível!")
        return False

    # ==============================
    # EXECUTAR VINCULAÇÃO
    # ==============================
    print("\n--- EXECUTANDO VINCULAÇÃO ---")

    # Pegar dados do move de devolução original para replicar nos novos
    move_original = conn.read('stock.move', [move_dev_id], [
        'product_id', 'product_uom', 'name', 'state',
        'location_id', 'location_dest_id', 'company_id',
        'picking_id', 'picking_type_id', 'warehouse_id',
        'date', 'date_deadline', 'origin'
    ])[0]

    # 1) Ajustar o move existente para a 1ª remessa
    primeiro = breakdown[0]
    print(f"\n  1) Ajustando move existente {move_dev_id}:")
    print(f"     qty: 416 → {primeiro['qty_alocar']:.0f}")
    print(f"     origin_returned_move_id → {primeiro['remessa_move_id']}")

    conn.write('stock.move', [move_dev_id], {
        'product_uom_qty': primeiro['qty_alocar'],
        'quantity': primeiro['qty_alocar'],
        'origin_returned_move_id': primeiro['remessa_move_id'],
        'move_orig_ids': [(4, primeiro['remessa_move_id'])],  # Add link
    })
    print(f"     ✅ Move {move_dev_id} atualizado")

    # 2) Criar novos moves para as demais remessas
    moves_criados = [move_dev_id]

    for i, b in enumerate(breakdown[1:], start=2):
        print(f"\n  {i}) Criando novo move para {b['remessa_picking_name']}:")
        print(f"     qty: {b['qty_alocar']:.0f}")
        print(f"     origin_returned_move_id → {b['remessa_move_id']}")

        new_move_vals = {
            'name': move_original.get('name', 'PALLET'),
            'product_id': move_original['product_id'][0],
            'product_uom': move_original['product_uom'][0],
            'product_uom_qty': b['qty_alocar'],
            'quantity': b['qty_alocar'],
            'location_id': move_original['location_id'][0],
            'location_dest_id': move_original['location_dest_id'][0],
            'picking_id': picking_id,
            'picking_type_id': move_original.get('picking_type_id', [False])[0] if move_original.get('picking_type_id') else False,
            'company_id': move_original['company_id'][0] if move_original.get('company_id') else False,
            'state': 'done',
            'origin_returned_move_id': b['remessa_move_id'],
            'move_orig_ids': [(4, b['remessa_move_id'])],
            'origin': move_original.get('origin', ''),
            'date': move_original.get('date', False),
        }

        try:
            new_id = conn.create('stock.move', new_move_vals)
            print(f"     ✅ Move {new_id} criado")
            moves_criados.append(new_id)
        except Exception as e:
            print(f"     ❌ ERRO ao criar move: {e}")
            # Continuar tentando os demais
            continue

    # 3) Atualizar picking de devolução
    print(f"\n  Atualizando picking {picking_id}:")
    remessa_names = [b['remessa_picking_name'] for b in breakdown]

    conn.write('stock.picking', [picking_id], {
        'return_id': selecionadas[0]['id'],  # Referência principal = 1ª remessa
        'is_return_picking': True,
        'origin': f"Devolução de {', '.join(remessa_names[:5])}{'...' if len(remessa_names) > 5 else ''}",
    })
    print(f"  ✅ Picking atualizado (return_id={selecionadas[0]['id']}, is_return_picking=True)")

    print(f"\n  TOTAL: {len(moves_criados)} moves criados/atualizados")
    return moves_criados


def step6_verificar_resultado(conn, moves_criados, breakdown, picking_dev_id=300204):
    """Verifica o resultado da vinculação"""
    print("\n" + "=" * 70)
    print("ETAPA 6: Verificando resultado")
    print("=" * 70)

    # 1) Verificar picking de devolução
    picking = conn.search_read(
        'stock.picking', [['id', '=', picking_dev_id]],
        fields=['id', 'name', 'return_id', 'is_return_picking', 'origin', 'move_ids']
    )[0]
    print(f"\nPicking de devolução: {picking['name']}")
    print(f"  return_id: {picking.get('return_id')}")
    print(f"  is_return_picking: {picking.get('is_return_picking')}")
    print(f"  origin: {picking.get('origin')}")
    print(f"  move_ids: {picking.get('move_ids')}")

    # 2) Verificar moves de devolução
    if moves_criados:
        moves_dev = conn.read('stock.move', moves_criados, [
            'id', 'product_uom_qty', 'quantity', 'state',
            'origin_returned_move_id', 'move_orig_ids'
        ])
        print(f"\nMoves de devolução ({len(moves_dev)}):")
        for m in moves_dev:
            orig = m.get('origin_returned_move_id', [False, ''])
            print(f"  Move {m['id']}: qty={m.get('product_uom_qty', 0)}, state={m.get('state')}")
            print(f"    origin_returned_move_id: {orig}")
            print(f"    move_orig_ids: {m.get('move_orig_ids')}")

    # 3) Verificar remessas — agora devem ter returned_move_ids
    print(f"\nRemessas (verificando returned_move_ids e qty_returned):")
    for b in breakdown:
        move_rem = conn.read('stock.move', [b['remessa_move_id']], [
            'id', 'picking_id', 'product_uom_qty', 'returned_move_ids'
        ])
        if move_rem:
            mr = move_rem[0]
            picking_name = mr.get('picking_id', [None, ''])[1] if mr.get('picking_id') else '?'
            print(f"  Move {mr['id']} ({picking_name}): qty_remessa={mr.get('product_uom_qty', 0)}")
            print(f"    returned_move_ids: {mr.get('returned_move_ids', [])}")

    # 4) Verificar na remessa original se return_ids agora aparece
    primeiro_picking = breakdown[0]['remessa_picking_id']
    rem = conn.search_read(
        'stock.picking', [['id', '=', primeiro_picking]],
        fields=['id', 'name', 'return_ids']
    )
    if rem:
        print(f"\n1ª remessa {rem[0]['name']}: return_ids = {rem[0].get('return_ids', [])}")


def main():
    print("=" * 70)
    print("TESTE: Vinculação N Remessas → 1 Devolução de Pallet (Opção B)")
    print("Cliente: ATACADÃO 183 | Devolução: CD/IN/07208 (416 pallets)")
    print("=" * 70)

    conn = get_odoo_connection()
    if not conn.authenticate():
        print("ERRO: Falha na autenticação com Odoo!")
        return

    # Etapa 1: Buscar remessas órfãs
    orfas = step1_buscar_remessas_orfas(conn)

    # Etapa 2: Selecionar FIFO até ~416
    selecionadas, acumulado = step2_selecionar_remessas_fifo(orfas, qtd_alvo=416)

    # Etapa 3: Buscar moves das remessas
    moves_remessa = step3_buscar_moves_remessas(conn, selecionadas)

    # Etapa 4: Ler picking de devolução
    picking_dev, move_dev = step4_ler_picking_devolucao(conn, picking_id=300204)

    if not picking_dev or not move_dev:
        print("\nERRO: Não foi possível ler o picking de devolução!")
        return

    # Etapa 5: Executar vinculação
    moves_criados = step5_testar_vinculacao(
        conn, picking_dev, move_dev, moves_remessa, selecionadas, qtd_alvo=416
    )

    if not moves_criados:
        print("\nERRO: Vinculação falhou!")
        return

    # Montar breakdown para verificação
    moves_por_picking = {}
    for m in moves_remessa:
        pid = m.get('picking_id', [None])[0] if m.get('picking_id') else None
        if pid:
            moves_por_picking[pid] = m

    breakdown = []
    restante = 416
    for r in selecionadas:
        move_rem = moves_por_picking.get(r['id'])
        if not move_rem:
            continue
        qty = min(r.get('qty_pallets', 0), restante)
        breakdown.append({
            'remessa_picking_id': r['id'],
            'remessa_picking_name': r['name'],
            'remessa_move_id': move_rem['id'],
            'qty_alocar': qty,
        })
        restante -= qty
        if restante <= 0:
            break

    # Etapa 6: Verificar
    step6_verificar_resultado(conn, moves_criados, breakdown)

    print("\n" + "=" * 70)
    print("TESTE CONCLUÍDO")
    print("=" * 70)


if __name__ == '__main__':
    main()
