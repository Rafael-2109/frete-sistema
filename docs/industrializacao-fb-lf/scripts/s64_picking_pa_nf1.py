#!/usr/bin/env python3
"""S64 — R2.3 NF-1: picking de entrada manual do PA + fatura a NF-1 (servico).

D-V30-1 confirmado (testado: nem [1,5] nem [1] FB-only geram picking nativo p/
PO de industrializacao). Caminho padrao = picking manual (atomo C9). Faz o PA
entrar fisicamente na FB (pre-req do ajuste de custo do AVCO) + gera qty_received
=> destrava criar_invoice_from_po da NF-1.

C9 cria E valida (button_validate + G019/G020) -> picking done.

Modos:
  --plan      (DEFAULT) le tracking do PA + mostra params (NAO escreve)
  --criar     C9 (cria+valida picking) + criar_invoice_from_po(43464) -> inv NF-1 DRAFT
  --cleanup   cancela invoice NF-1 + picking do PA

PRODUCAO. Escrita SO com --criar e go. NAO posta a invoice.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.estoque.scripts.picking import StockPickingService
from app.odoo.estoque.scripts.escrituracao import EscrituracaoLfService

COMPANY_FB = 1
PA = 27834            # [4870112] MOLHO SHOYU PET (produto)
QTY = 1.0
LOTE = 'PILOTO-3105'
PO_NF1 = 43464        # C2620345
PO_LINE = 131508      # purchase.order.line da NF-1
SRC = 26489           # Em Transito Industrializacao (src pt52)
DST = 8               # FB/Estoque (dst pt52)
PT52 = 52             # Recebimentos Industrializacao (FB)
PARTNER_LF = 35       # LF (emitente da NF de retorno)
ORIGIN = 'RET-IND-4870112-PILOTO-PA'
CTX = {'allowed_company_ids': [1], 'company_id': 1, 'lang': 'pt_BR'}  # FB-only
SEP = '=' * 96


def main():
    args = sys.argv[1:]
    o = get_odoo_connection()
    assert o.authenticate(), 'FALHA AUTH'

    def rd(model, ids, f):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': f, 'context': CTX})

    if '--cleanup' in args:
        # invoice da NF-1
        po = rd('purchase.order', [PO_NF1], ['invoice_ids'])[0]
        for inv in po.get('invoice_ids', []):
            st = rd('account.move', [inv], ['state'])[0]['state']
            if st == 'posted':
                o.execute_kw('account.move', 'button_draft', [[inv]], {'context': CTX})
            o.execute_kw('account.move', 'button_cancel', [[inv]], {'context': CTX})
            print(f'  invoice {inv} cancelada')
        pk = o.execute_kw('stock.picking', 'search_read', [[('origin', '=', ORIGIN)]],
                          {'fields': ['id', 'state'], 'context': CTX})
        for p in pk:
            if p['state'] == 'done':
                o.execute_kw('stock.picking', 'button_validate', [[p['id']]], {'context': CTX})  # noop guard
            o.execute_kw('stock.picking', 'action_cancel', [[p['id']]], {'context': CTX})
            print(f"  picking {p['id']} cancelado (era {p['state']})")
        print('  [CLEANUP] feito.')
        return

    pa = rd('product.product', [PA], ['name', 'tracking', 'type', 'purchase_method'])[0]
    pl = rd('purchase.order.line', [PO_LINE], ['qty_received', 'qty_invoiced', 'product_qty'])[0]
    print(SEP)
    print('S64 — picking do PA (NF-1) + fatura')
    print(SEP)
    print(f"\n  PA {PA}: {pa['name'][:46]} tracking={pa['tracking']} method={pa['purchase_method']}")
    print(f"  PO-line {PO_LINE}: qty={pl['product_qty']} received={pl['qty_received']} invoiced={pl['qty_invoiced']}")
    print(f"\n  C9 params:")
    print(f"    company_destino={COMPANY_FB} src={SRC} dst={DST} pt={PT52} partner={PARTNER_LF}")
    print(f"    origin='{ORIGIN}'")
    print(f"    move: product={PA} qty={QTY} lot_dest_name='{LOTE}' purchase_line_id={PO_LINE}")
    print(f"  depois: criar_invoice_from_po({PO_NF1}) -> invoice NF-1 DRAFT")

    if '--criar' not in args:
        print('\n  [PLAN] nada escrito. Para criar: --criar')
        print(SEP)
        return

    psvc = StockPickingService(odoo=o)
    moves = [{'product_id': PA, 'quantity': QTY, 'lot_dest_name': LOTE,
              'purchase_line_id': PO_LINE}]
    r = psvc.criar_picking_entrada_destino_manual(
        company_destino_id=COMPANY_FB, location_origem_id=SRC,
        location_destino_id=DST, moves_data=moves, picking_type_id=PT52,
        origin=ORIGIN, partner_id=PARTNER_LF)
    print(f"\n  C9: {r}")
    pl2 = rd('purchase.order.line', [PO_LINE], ['qty_received'])[0]
    print(f"  PO-line qty_received agora = {pl2['qty_received']}")

    esvc = EscrituracaoLfService(odoo=o)
    r_inv = esvc.criar_invoice_from_po(po_id=PO_NF1, dry_run=False)
    print(f"  criar_invoice_from_po: status={r_inv.get('status')} inv={r_inv.get('invoice_id')} erro={r_inv.get('erro')}")
    inv_id = r_inv.get('invoice_id')
    if inv_id:
        o.execute_kw('account.move', 'write', [[inv_id], {'invoice_origin': 'RET-IND-4870112-PILOTO'}], {'context': CTX})
        invf = rd('account.move', [inv_id],
                  ['name', 'state', 'journal_id', 'amount_total', 'amount_untaxed', 'invoice_origin'])[0]
        print(f"  INVOICE NF-1 draft: {invf}")
    print(SEP)


if __name__ == '__main__':
    main()
