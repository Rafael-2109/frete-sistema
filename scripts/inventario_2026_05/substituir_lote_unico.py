# etapa: orquestrador
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""Substituir lote de 1 item — 205030410 FB.

Operacao pontual (nao planilha):
    Produto       : default_code 205030410 (id=27987,
                    BOBINA DE FILME - 80 G AZ VSC - CAMPO BELO)
    Empresa       : FB (company_id=1)
    Location      : FB/Pre-Producao/Linha Balde (location_id=4068)
    Lote origem   : 'ME135 - 093/25'  (id=32717)
    Lote destino  : 'ME 138-086/26'   (id=52671 — ja existe)
                    Usuario pediu '138-086/26'. Mantida convencao do
                    produto ('ME ' prefixo) — lote ja cadastrado com
                    esse nome canonico na FB.
    Quantidade    : 298.566

Particularidade:
    O saldo do lote origem em Linha Balde esta 100% reservado por
    2 stock.move de Manufacturing Orders `confirmed` (consumo de
    materia-prima):
        - MO 14699 / move 815692 / move_line 217483844 — 53.622
        - MO 15086 / move 839726 / move_line 217483950 — 244.944
    Sequencia da operacao:
        1. _do_unreserve nas 2 moves (libera reserva)
        2. transferir_quantidade_para_lote 298.566 de 32717 → 52671
        3. _action_assign nas 2 moves (reatribui — agora no lote novo)

Uso:
    python scripts/inventario_2026_05/substituir_lote_unico.py            # dry-run
    python scripts/inventario_2026_05/substituir_lote_unico.py --confirmar
"""
import argparse
import logging
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app  # noqa: E402
from app.odoo.services.stock_internal_transfer_service import (  # noqa: E402
    StockInternalTransferService,
)
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('subst_lote_205030410')

DEFAULT_CODE = '205030410'
COMPANY_ID = 1                  # FB
LOCATION_ID = 4068              # FB/Pre-Producao/Linha Balde
LOTE_ORIGEM = 'ME135 - 093/25'
LOTE_DESTINO = 'ME 138-086/26'  # padrao do produto (com 'ME ')
QTD = 298.566
MOVE_IDS = [815692, 839726]     # moves de consumo das 2 MOs


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--confirmar', action='store_true',
                        help='Executa de fato (default = dry-run)')
    args = parser.parse_args()

    dry = not args.confirmar

    banner(f'SUBSTITUIR LOTE — produto {DEFAULT_CODE} (FB)')
    print(f'  Lote origem  : {LOTE_ORIGEM!r}')
    print(f'  Lote destino : {LOTE_DESTINO!r}')
    print(f'  Quantidade   : {QTD}')
    print(f'  Company      : {COMPANY_ID} (FB)  Location: {LOCATION_ID} (Linha Balde)')
    print(f'  Modo         : {"DRY-RUN" if dry else "EXECUTAR"}')

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        transfer_svc = StockInternalTransferService(odoo=odoo, lot_svc=lot_svc)

        # 1. Produto
        prod_ids = odoo.search('product.product',
                               [['default_code', '=', DEFAULT_CODE]], limit=2)
        if not prod_ids or len(prod_ids) > 1:
            raise SystemExit(f'Produto {DEFAULT_CODE} ambiguo/ausente: {prod_ids}')
        prod = odoo.read('product.product', prod_ids[0],
                         ['id', 'name', 'default_code', 'tracking'])[0]
        print()
        print(f'Produto Odoo: id={prod["id"]}  default_code={prod["default_code"]}  '
              f'name={prod["name"]!r}')

        # 2. Lote origem
        lot_id_origem = lot_svc.buscar_por_nome(LOTE_ORIGEM, prod['id'], COMPANY_ID)
        if not lot_id_origem:
            raise SystemExit(f'Lote origem {LOTE_ORIGEM!r} nao encontrado')
        lote_o = odoo.read('stock.lot', lot_id_origem,
                           ['id', 'name', 'expiration_date'])[0]
        print(f'Lote origem : id={lote_o["id"]}  name={lote_o["name"]!r}  '
              f'exp={lote_o.get("expiration_date")}')

        # 3. Lote destino — usar o existente
        lot_id_destino = lot_svc.buscar_por_nome(LOTE_DESTINO, prod['id'], COMPANY_ID)
        if not lot_id_destino:
            raise SystemExit(
                f'Lote destino {LOTE_DESTINO!r} nao encontrado. '
                'Esperava-se o lote canonico ja cadastrado.'
            )
        lote_d = odoo.read('stock.lot', lot_id_destino,
                           ['id', 'name', 'expiration_date'])[0]
        print(f'Lote destino: id={lote_d["id"]}  name={lote_d["name"]!r}  '
              f'exp={lote_d.get("expiration_date")}')

        # 4. Quant origem
        quant_o = transfer_svc.buscar_quant(prod['id'], COMPANY_ID, LOCATION_ID,
                                            lot_id=lot_id_origem)
        if not quant_o:
            raise SystemExit(
                f'Quant origem nao encontrado em location {LOCATION_ID} '
                f'(lote {lot_id_origem})'
            )
        print(f'Quant origem: id={quant_o["id"]}  qty={quant_o["quantity"]}  '
              f'reserved={quant_o.get("reserved_quantity")}')

        # 4b. Sanidade qty
        diff = abs(float(quant_o['quantity']) - QTD)
        if diff > 0.001:
            print(f'!! ATENCAO: qty do quant ({quant_o["quantity"]}) DIVERGE '
                  f'de {QTD} (diff {diff:.6f})')

        # 5. Moves a desreservar/reatribuir
        moves = odoo.read('stock.move', MOVE_IDS,
                          ['id', 'name', 'state', 'product_uom_qty', 'quantity'])
        print()
        print('Moves a manipular (unreserve -> transfer -> reassign):')
        for mv in moves:
            print(f'  move_id={mv["id"]}  name={mv["name"]!r}  '
                  f'state={mv["state"]}  demanded={mv["product_uom_qty"]}  '
                  f'done={mv["quantity"]}')

        if dry:
            print()
            print('DRY-RUN — nada gravado. Use --confirmar para executar.')
            return 0

        # ============================================================
        # EXECUCAO
        # ============================================================

        banner('ETAPA 1/3 — DESRESERVAR MOVES')
        odoo.execute_kw('stock.move', '_do_unreserve', [MOVE_IDS])
        # Reconferir quant origem
        quant_o2 = transfer_svc.buscar_quant(prod['id'], COMPANY_ID, LOCATION_ID,
                                             lot_id=lot_id_origem)
        print(f'Quant origem pos-unreserve: qty={quant_o2["quantity"]}  '
              f'reserved={quant_o2.get("reserved_quantity")}')
        if float(quant_o2.get('reserved_quantity') or 0) > 0.001:
            raise SystemExit(
                '!! Reserva nao zerou apos _do_unreserve. Abortando '
                'antes de transferir — verificar manualmente.'
            )

        banner('ETAPA 2/3 — TRANSFERIR ENTRE LOTES')
        res = transfer_svc.transferir_entre_lotes(
            product_id=prod['id'],
            company_id=COMPANY_ID,
            location_id=LOCATION_ID,
            qty=QTD,
            lot_id_origem=lot_id_origem,
            lot_id_destino=lot_id_destino,
        )
        for k, v in res.items():
            print(f'  {k:<32} {v}')

        banner('ETAPA 3/3 — REATRIBUIR MOVES')
        odoo.execute_kw('stock.move', '_action_assign', [MOVE_IDS])

        # Validacao final
        moves_pos = odoo.read('stock.move', MOVE_IDS,
                              ['id', 'name', 'state', 'product_uom_qty', 'quantity'])
        print()
        print('Moves pos-reatribuicao:')
        for mv in moves_pos:
            print(f'  move_id={mv["id"]}  state={mv["state"]}  '
                  f'demanded={mv["product_uom_qty"]}  done={mv["quantity"]}')

        # Move lines agora apontam pro lote destino?
        lines_pos = odoo.search_read('stock.move.line', [
            ['move_id', 'in', MOVE_IDS],
            ['state', 'not in', ['done', 'cancel']],
        ], ['id', 'move_id', 'lot_id', 'quantity', 'state'])
        print()
        print('Move lines apos reatribuicao:')
        for ml in lines_pos:
            print(f'  ml_id={ml["id"]}  move={ml.get("move_id")}  '
                  f'lot={ml.get("lot_id")}  qty={ml["quantity"]}  '
                  f'state={ml["state"]}')

        quant_o3 = transfer_svc.buscar_quant(prod['id'], COMPANY_ID, LOCATION_ID,
                                             lot_id=lot_id_origem)
        quant_d3 = transfer_svc.buscar_quant(prod['id'], COMPANY_ID, LOCATION_ID,
                                             lot_id=lot_id_destino)
        print()
        print('Quants finais:')
        print(f'  origem  (lot {lot_id_origem}): '
              f'qty={quant_o3["quantity"] if quant_o3 else 0} '
              f'reserved={quant_o3.get("reserved_quantity") if quant_o3 else 0}')
        print(f'  destino (lot {lot_id_destino}): '
              f'qty={quant_d3["quantity"] if quant_d3 else 0} '
              f'reserved={quant_d3.get("reserved_quantity") if quant_d3 else 0}')

        return 0


if __name__ == '__main__':
    sys.exit(main())
