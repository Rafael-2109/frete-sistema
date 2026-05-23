"""Consolidar grafias do lote 027-098/26 do SAL SEM IODO (104000015) na FB
e zerar o saldo negativo da Linha Salmoura.

CONTEXTO (investigacao 2026-05-21):
    O lote fisico 027-098/26 do SAL SEM IODO existe no Odoo em DUAS grafias
    (dois stock.lot distintos), por divergencia de padronizacao:
        - lot#53776 'MI 027-098/26'  (canonico, criado 2026-04-13)
        - lot#57478 '027-098/26'     (duplicado, criado 2026-05-19 madrugada)

    O abastecimento da Linha Salmoura (FB/FB/EMB/*) usou a grafia '027-098/26'
    enquanto varios consumos de producao (FB/OP/SALMOURA/*) sairam da grafia
    'MI 027-098/26'. Resultado: a grafia 'MI 027-098/26' ficou NEGATIVA
    (-1203,94 na Linha Salmoura) enquanto a '027-098/26' ficou positiva.
    O monitor (que agrega a grafia 'MI 027-098/26') mostra -825,07.

    NAO ha falta fisica: somando as duas grafias o lote tem ~+3.676 un internas.

OBJETIVO (escopo confirmado pelo usuario "Consolidar + zerar a Linha"):
    1. Consolidar '027-098/26' (57478) -> 'MI 027-098/26' (53776) em FB/Estoque
       (move SO o saldo LIVRE, preserva reserva).
    2. Idem na Linha Salmoura.
    3. Zerar o saldo negativo residual da grafia 'MI 027-098/26' na Linha
       Salmoura trazendo o equivalente de FB/Estoque (transferencia inter-local
       via 2 inventory adjustments, padrao do script 15).

    Conjunto NET-ZERO: o total fisico do lote em FB e preservado.

Particularidades:
    - Producao pode estar ATIVA. O script RELE o estado fresco a cada passo e
      calcula as quantidades dinamicamente (nao hardcode). Idealmente rodar com
      a Linha Salmoura sem OP em andamento.
    - transferir_entre_lotes (Op1/Op2) ja valida reserva e faz clamp de
      arredondamento.

Uso:
    python scripts/inventario_2026_05/consolidar_lote_104000015_sal_fb.py            # dry-run
    python scripts/inventario_2026_05/consolidar_lote_104000015_sal_fb.py --confirmar
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
logger = logging.getLogger('consolidar_104000015')

DEFAULT_CODE = '104000015'
PROD_ID = 27918
COMPANY_ID = 1                 # FB
FB_ESTOQUE = 8                 # FB/Estoque
LINHA_SALMOURA = 27458         # FB/Pre-Producao/Linha Salmoura
LOT_MI = 53776                 # 'MI 027-098/26' (canonico = destino)
LOT_SEM = 57478                # '027-098/26' (duplicado = origem a eliminar)
TOL = 0.001


def banner(t, c='='):
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def saldo(svc, loc, lot):
    """Retorna (quantity, reserved, livre) de 1 quant ou (0,0,0)."""
    q = svc.buscar_quant(PROD_ID, COMPANY_ID, loc, lot)
    if not q:
        return 0.0, 0.0, 0.0, None
    qty = float(q['quantity'])
    rsv = float(q.get('reserved_quantity', 0) or 0)
    return qty, rsv, round(qty - rsv, 6), q['id']


def snapshot(svc, titulo):
    print(f'\n--- {titulo} ---')
    print(f'  {"location":<34} {"grafia":<16} {"qty":>12} {"reserv":>10} {"livre":>12}')
    tot_mi = 0.0
    for loc, locn in [(FB_ESTOQUE, 'FB/Estoque'),
                      (LINHA_SALMOURA, 'FB/.../Linha Salmoura')]:
        for lot, lotn in [(LOT_MI, 'MI 027-098/26'), (LOT_SEM, '027-098/26')]:
            qty, rsv, livre, _ = saldo(svc, loc, lot)
            print(f'  {locn:<34} {lotn:<16} {qty:>12.4f} {rsv:>10.4f} {livre:>12.4f}')
            if lot == LOT_MI:
                tot_mi += qty
    print(f'  >> TOTAL grafia MI 027-098/26 (o que o monitor mostra): {tot_mi:>12.4f}')
    return tot_mi


def transferir_inter_local(odoo, svc, loc_origem, loc_dest, lot_id, qty, dry):
    """Move `qty` do mesmo lote entre locations via 2 inventory adjustments
    (padrao do script 15). Reduz origem, aumenta/cria destino. NET-ZERO."""
    qo, _, livre_o, qid_o = saldo(svc, loc_origem, lot_id)
    if livre_o + TOL < qty:
        raise SystemExit(
            f'!! Origem (loc {loc_origem}, lot {lot_id}) tem livre {livre_o} '
            f'< {qty} pedido. Abortando Op3.'
        )
    qd, _, _, qid_d = saldo(svc, loc_dest, lot_id)
    print(f'  Op3 inter-local: -{qty:.4f} em loc {loc_origem} (de {qo:.4f}->{qo-qty:.4f}) '
          f'/ +{qty:.4f} em loc {loc_dest} (de {qd:.4f}->{qd+qty:.4f})')
    if dry:
        return
    # 1. Reduzir origem
    odoo.write('stock.quant', [qid_o], {'inventory_quantity': round(qo - qty, 6)})
    odoo.execute_kw('stock.quant', 'action_apply_inventory', [[qid_o]])
    # 2. Aumentar/criar destino
    if qid_d:
        odoo.write('stock.quant', [qid_d], {'inventory_quantity': round(qd + qty, 6)})
        odoo.execute_kw('stock.quant', 'action_apply_inventory', [[qid_d]])
    else:
        new_id = odoo.create('stock.quant', {
            'product_id': PROD_ID, 'company_id': COMPANY_ID,
            'location_id': loc_dest, 'lot_id': lot_id,
            'inventory_quantity': round(qd + qty, 6),
        })
        odoo.execute_kw('stock.quant', 'action_apply_inventory', [[new_id]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true',
                    help='Executa de fato (default = dry-run)')
    args = ap.parse_args()
    dry = not args.confirmar

    banner(f'CONSOLIDAR LOTE 027-098/26 — SAL SEM IODO ({DEFAULT_CODE}) FB')
    print(f'  Destino (canonico): lot#{LOT_MI} MI 027-098/26')
    print(f'  Origem (eliminar):  lot#{LOT_SEM} 027-098/26')
    print(f'  Modo: {"DRY-RUN" if dry else ">>> EXECUTAR <<<"}')

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        svc = StockInternalTransferService(odoo=odoo, lot_svc=lot_svc)

        snapshot(svc, 'ESTADO INICIAL')

        # ---- Op1: FB/Estoque  sem-MI -> MI (saldo livre) ----
        # Margem TOL acima da reserva: o service valida sobra >= reserva com
        # comparacao estrita; float64 faz (qty-livre) cair 1e-13 abaixo da
        # reserva. Deixar TOL de folga absorve o erro (residuo desprezivel).
        banner('Op1 — FB/Estoque: 027-098/26 -> MI 027-098/26 (livre)', '-')
        _, rsv1, livre1, _ = saldo(svc, FB_ESTOQUE, LOT_SEM)
        qty1 = round(livre1 - TOL, 6) if rsv1 > TOL else livre1
        if qty1 > TOL:
            print(f'  Transferir {qty1:.4f} (livre {livre1:.4f}, reserva {rsv1:.4f}) '
                  f'de sem-MI -> MI em FB/Estoque')
            if not dry:
                r = svc.transferir_entre_lotes(PROD_ID, COMPANY_ID, FB_ESTOQUE,
                                               qty1, LOT_SEM, LOT_MI)
                print(f'    origem {r["quant_origem_qty_antes"]:.4f}->{r["quant_origem_qty_apos"]:.4f}'
                      f' | destino {r["quant_destino_qty_antes"]:.4f}->{r["quant_destino_qty_apos"]:.4f}')
        else:
            print('  Nada livre a transferir.')

        # ---- Op2: Linha Salmoura  sem-MI -> MI (saldo livre) ----
        banner('Op2 — Linha Salmoura: 027-098/26 -> MI 027-098/26 (livre)', '-')
        _, rsv2, livre2, _ = saldo(svc, LINHA_SALMOURA, LOT_SEM)
        qty2 = round(livre2 - TOL, 6) if rsv2 > TOL else livre2
        if qty2 > TOL:
            print(f'  Transferir {qty2:.4f} (livre {livre2:.4f}, reserva {rsv2:.4f}) '
                  f'de sem-MI -> MI na Linha Salmoura')
            if not dry:
                r = svc.transferir_entre_lotes(PROD_ID, COMPANY_ID, LINHA_SALMOURA,
                                               qty2, LOT_SEM, LOT_MI)
                print(f'    origem {r["quant_origem_qty_antes"]:.4f}->{r["quant_origem_qty_apos"]:.4f}'
                      f' | destino {r["quant_destino_qty_antes"]:.4f}->{r["quant_destino_qty_apos"]:.4f}')
        else:
            print('  Nada livre a transferir.')

        # ---- Op3: zerar MI@Linha trazendo de MI@FB/Estoque ----
        banner('Op3 — Zerar Linha Salmoura (grafia MI) via FB/Estoque', '-')
        # No dry-run, simular o estado pos Op1/Op2 para calcular Op3
        if dry:
            qmi_linha, _, _, _ = saldo(svc, LINHA_SALMOURA, LOT_MI)
            falta_sim = -(qmi_linha + qty2)   # apos Op2 a linha MI sobe qty2
            print(f'  [simulado] MI@Linha apos Op2 ~ {qmi_linha + qty2:.4f}')
            if falta_sim > TOL:
                print(f'  [simulado] Op3 traria {falta_sim:.4f} de FB/Estoque p/ zerar a Linha')
            else:
                print('  [simulado] Linha nao ficaria negativa apos Op2 — Op3 desnecessaria.')
        else:
            qmi_linha, _, _, _ = saldo(svc, LINHA_SALMOURA, LOT_MI)
            if qmi_linha < -TOL:
                falta = round(-qmi_linha, 6)
                transferir_inter_local(odoo, svc, FB_ESTOQUE, LINHA_SALMOURA,
                                       LOT_MI, falta, dry=False)
            else:
                print(f'  MI@Linha = {qmi_linha:.4f} (nao negativo) — Op3 desnecessaria.')

        # ---- Resultado ----
        if dry:
            banner('DRY-RUN — nada gravado. Rode com --confirmar para executar.')
            return 0
        tot_final = snapshot(svc, 'ESTADO FINAL')
        banner('RESULTADO')
        if tot_final >= -TOL:
            print(f'  OK — grafia MI 027-098/26 total = {tot_final:.4f} (nao negativo).')
        else:
            print(f'  !! ATENCAO: grafia MI ainda {tot_final:.4f} — revisar.')
        return 0


if __name__ == '__main__':
    sys.exit(main())
