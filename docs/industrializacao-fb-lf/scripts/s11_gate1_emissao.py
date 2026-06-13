#!/usr/bin/env python3
"""S11 — GATE 1: ensaio da emissao 2-NF no piloto 4870112 (DRAFT-only, sem SEFAZ).

Testa o desenho SOT §6.1 no contexto REAL do piloto (pt98, 0 usos historicos — o
maior risco do painel). Tudo reversivel: NF draft (deletavel) + picking (devolvivel).

MODOS:
  (sem flag / --preflight)  READ: confirma pre-condicoes (PA, pt98, RETIND, partner FB,
                            remessa p/ price_unit, BoM esperada). NAO escreve.
  --criar-picking           cria o picking pt98 do PA (31093->26489), liberado=False,
                            robo fora de 1..11; valida (done). [escrita 1]
  --faturar PICK_ID         chama o wizard stock.invoice.onshipping(journal=847) ->
                            NF mista DRAFT + recompute (mede timeout). [escrita 2]
  --medir MOVE_ID           READ: asserts a-g (wizard aceitou? BoM expandiu? CFOP/CST?
                            onchange nao re-expande? contrapartida 5902?).
  --revert PICK_ID [MOVE_IDS...]  deleta NFs draft + devolve/cancela picking.

ASSERTS (SOT §6.1 GATE 1): (a) wizard aceita pt98; (b) nº linhas 5902 == BoM;
(c) CFOP 5124/5902 + CST (5124=51, 5902=50); (d) onchange nao re-expande;
(e) price_unit forcavel = remessa; (f) RETIND nao pego pelo robo; (g) refNFe gravavel.
"""
import sys
import time
import argparse
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5}
LF, FB = 5, 1
PA_PROD = 27834           # 4870112 (PA piloto)
PA_LOT = 60542            # PILOTO-3105
LOC_SRC = 31093           # LF/PA de Terceiros
LOC_DST = 5               # Parceiros/Clientes (saida p/ FB) — GATE 1 provou: dst=26489 NAO
                          # dispara a operacao fiscal 2702/2864 (cai na conta income FB do produto).
                          # As VND reais de retorno saem por pt66 -> 5 (Clientes). v3.2.
PT_RET = 66               # pt66 Expedicao Industrializacao (PROVADO; src override 31093)
PT98 = 98                 # (legado preflight) pt98 Retorno Ind. — abandonado (dst 26489 falha)
J847 = 847               # VENDA PRODUCAO (venda-industrializacao) — wizard
RETIND = 1083            # journal RETIND (no_payment PASSIVA 26667)
RPI_PILOTO = 735679      # RPI/2026/00245 (remessa do piloto; linhas 5901 = price_unit alvo)


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preflight', action='store_true')
    ap.add_argument('--criar-picking', action='store_true')
    ap.add_argument('--faturar', type=int, metavar='PICK_ID')
    ap.add_argument('--medir', type=int, metavar='MOVE_ID')
    ap.add_argument('--revert', nargs='+', type=int, metavar='PICK_ID MOVE_IDS')
    ap.add_argument('--produto', type=int, default=PA_PROD, help='product.product id (default shoyu)')
    ap.add_argument('--lote', type=int, default=PA_LOT, help='stock.lot id')
    ap.add_argument('--src', type=int, default=LOC_SRC, help='location origem')
    ap.add_argument('--origin', default='GATE1', help='origin/label do picking')
    args = ap.parse_args()
    PROD, LOTE, SRC, ORIGIN = args.produto, args.lote, args.src, args.origin

    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, domain, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kw2)
    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    # ============ PREFLIGHT (default) ============
    if args.faturar is None and args.medir is None and not args.criar_picking and not args.revert:
        print("=" * 86); print("GATE 1 — PREFLIGHT (READ-only)"); print("=" * 86)

        q = rr('stock.quant', [('product_id', '=', PA_PROD), ('location_id', '=', LOC_SRC)],
               ['lot_id', 'quantity', 'reserved_quantity'])
        print(f"\n[1] PA {PA_PROD} (4870112) em 31093:")
        for x in q:
            print(f"    lote={m2o(x.get('lot_id'))} qty={x.get('quantity')} resv={x.get('reserved_quantity')}")
        ok_pa = any(isinstance(x.get('lot_id'), list) and x['lot_id'][0] == PA_LOT
                    and x.get('quantity', 0) - x.get('reserved_quantity', 0) >= 1 for x in q)
        print(f"    >>> PA livre lote PILOTO-3105: {'OK' if ok_pa else 'FALTA'}")

        pt = rd('stock.picking.type', [PT98], ['name', 'invoice_move_type', 'l10n_br_tipo_pedido'])[0]
        print(f"\n[2] pt98: invoice_move_type={pt.get('invoice_move_type')} "
              f"tipo_pedido={pt.get('l10n_br_tipo_pedido')}")

        j = rd('account.journal', [RETIND], ['name', 'l10n_br_no_payment', 'account_no_payment_id'])[0]
        print(f"\n[3] RETIND {RETIND}: no_payment={j.get('l10n_br_no_payment')} "
              f"conta={m2o(j.get('account_no_payment_id'))}")

        # partner FB usado nas VND de retorno (j847) — p/ o picking
        print(f"\n[4] partner das VND de retorno (j847) — p/ o picking pt98:")
        vnds = rr('account.move', [('journal_id', '=', J847), ('move_type', '=', 'out_invoice'),
                                   ('state', '=', 'posted')], ['partner_id'], limit=20, order='id desc')
        parts = Counter(m2o(v.get('partner_id')) for v in vnds)
        print(f"    partners (top): {dict(parts.most_common(4))}")

        # remessa do piloto — linhas 5901 (price_unit alvo p/ forcar na NF-insumos)
        print(f"\n[5] remessa RPI/2026/00245 ({RPI_PILOTO}) — linhas (price_unit alvo):")
        rl = rr('account.move.line', [('move_id', '=', RPI_PILOTO), ('display_type', '=', 'product')],
                ['product_id', 'quantity', 'price_unit', 'l10n_br_cfop_codigo'], limit=40)
        print(f"    {len(rl)} linhas:")
        for l in rl:
            print(f"      cfop={l.get('l10n_br_cfop_codigo')} [{m2o(l.get('product_id'))[:34]:34}] "
                  f"qty={l.get('quantity')} pu={l.get('price_unit')}")

        # BoM do PA — quantos componentes esperar na expansao
        print(f"\n[6] BoM do PA {PA_PROD} (componentes esperados na expansao 5902):")
        boms = rr('mrp.bom', [('product_id', '=', PA_PROD), ('company_id', 'in', [LF, False])],
                  ['id', 'type', 'product_qty', 'company_id'], limit=10)
        if not boms:
            tmpl = rd('product.product', [PA_PROD], ['product_tmpl_id'])[0].get('product_tmpl_id')
            if tmpl:
                boms = rr('mrp.bom', [('product_tmpl_id', '=', tmpl[0])],
                          ['id', 'type', 'product_qty', 'company_id'], limit=10)
        for b in boms:
            bl = rr('mrp.bom.line', [('bom_id', '=', b['id'])], ['product_id', 'product_qty'], limit=60)
            print(f"    BoM {b['id']} type={b.get('type')} qty={b.get('product_qty')} "
                  f"cmp={m2o(b.get('company_id'))} -> {len(bl)} linhas")

        # ja existe picking pt98?
        ex = rr('stock.picking', [('picking_type_id', '=', PT98)], ['id', 'name', 'state'], limit=5)
        print(f"\n[7] pickings pt98 existentes: {len(ex)} {[(p['id'], p['state']) for p in ex]}")
        print("\n[FIM PREFLIGHT] — proximo: --criar-picking (com go)")
        return

    def w(model, ids, vals):
        return o.execute_kw(model, 'write', [list(ids), vals], {'context': CTX})

    # ============ CRIAR PICKING pt66 (PA, src->5 Clientes) — [escrita 1] ============
    if args.criar_picking:
        print(f"=== CRIAR PICKING pt66 (produto {PROD}, {SRC}->5 Clientes) ===")
        prod = rd('product.product', [PROD], ['uom_id'])[0]
        uom = prod['uom_id'][0]
        pid = o.execute_kw('stock.picking', 'create', [{
            'picking_type_id': PT_RET, 'partner_id': FB, 'location_id': SRC,
            'location_dest_id': LOC_DST, 'company_id': LF, 'origin': ORIGIN,
        }], {'context': CTX})
        mid = o.execute_kw('stock.move', 'create', [{
            'name': f'PA {PROD} {ORIGIN}', 'picking_id': pid, 'product_id': PROD,
            'product_uom_qty': 1.0, 'product_uom': uom, 'location_id': SRC,
            'location_dest_id': LOC_DST, 'company_id': LF,
        }], {'context': CTX})
        o.execute_kw('stock.picking', 'action_confirm', [[pid]], {'context': CTX})
        o.execute_kw('stock.picking', 'action_assign', [[pid]], {'context': CTX})
        mlf = o.execute_kw('stock.move.line', 'fields_get', [], {'attributes': ['type'], 'context': CTX})
        upd = {'lot_id': LOTE, 'quantity': 1.0}
        if 'qty_done' in mlf: upd['qty_done'] = 1.0
        if 'picked' in mlf: upd['picked'] = True
        mls = rr('stock.move.line', [('picking_id', '=', pid)], ['id'])
        if mls:
            w('stock.move.line', [mls[0]['id']], upd)
        else:
            upd.update({'move_id': mid, 'picking_id': pid, 'product_id': PROD,
                        'location_id': SRC, 'location_dest_id': LOC_DST, 'product_uom_id': uom, 'company_id': LF})
            o.execute_kw('stock.move.line', 'create', [upd], {'context': CTX})
        w('stock.picking', [pid], {'liberado_faturamento': False, 'robo': 0})  # anti-robo
        o.execute_kw('stock.picking', 'button_validate', [[pid]],
                     {'context': dict(CTX, skip_backorder=True, skip_immediate=True)})
        p = rd('stock.picking', [pid], ['name', 'state', 'liberado_faturamento', 'robo'])[0]
        print(f"  picking {pid} {p['name']} state={p['state']} "
              f"liberado_faturamento={p.get('liberado_faturamento')} robo={p.get('robo')}")
        print(f"  (PA saiu p/ Clientes 5; revert = devolucao 5->31093)")
        print(f"  >>> proximo: --faturar {pid}   (revert: --revert {pid})")
        return

    # ============ FATURAR via wizard — NF mista DRAFT [escrita 2] ============
    if args.faturar:
        pid = args.faturar
        print(f"=== FATURAR via wizard stock.invoice.onshipping (picking {pid}, journal {J847}) ===")
        # GATE 1 GOTCHA: contexto LF-ONLY (allowed_company_ids=[5]), como o robo (company.ids).
        # Com [1,5] o Odoo resolve a income da categoria na company FB -> "empresas incompativeis".
        wctx = {'allowed_company_ids': [LF], 'company_id': LF, 'active_ids': [pid],
                'active_model': 'stock.picking'}
        wiz = o.execute_kw('stock.invoice.onshipping', 'create',
                           [{'company_id': LF, 'journal_id': J847}], {'context': wctx})
        print(f"  wizard {wiz} criado; chamando create_invoice() ... (mede timeout)")
        t0 = time.time()
        try:
            res = o.execute_kw('stock.invoice.onshipping', 'create_invoice', [[wiz]], {'context': wctx})
        except Exception as e:
            print(f"  !! create_invoice FALHOU em {time.time()-t0:.0f}s: {str(e)[:300]}")
            print("  >>> ASSERT (a) wizard aceita pt98: FALHOU — diagnosticar")
            return
        dt = time.time() - t0
        # achar a invoice gerada — via picking.invoice_id(s) (mais confiavel)
        pf = o.execute_kw('stock.picking', 'fields_get', [], {'attributes': [], 'context': CTX})
        pflds = [x for x in ['invoice_id', 'invoice_ids'] if x in pf]
        p = rd('stock.picking', [pid], pflds + ['name'])[0]
        inv_ids = []
        if p.get('invoice_id'): inv_ids.append(p['invoice_id'][0])
        if p.get('invoice_ids'): inv_ids += p['invoice_ids']
        if not inv_ids and isinstance(res, list): inv_ids = res
        if not inv_ids:
            inv_ids = [i['id'] for i in rr('account.move', [('ref', '=', p['name'])], ['id'], limit=3)]
        print(f"  create_invoice OK em {dt:.0f}s; res={res}; invoices={inv_ids}")
        print(f"  >>> ASSERT (a) wizard aceita pt66/dst=5: OK")
        print(f"  >>> ASSERT timeout recompute: {dt:.0f}s ({'OK <300s' if dt < 300 else 'LENTO — pesa pro server-side/SA'})")
        print(f"  >>> proximo: --medir {inv_ids[0] if inv_ids else '<MOVE_ID>'}")
        return

    # ============ MEDIR NF mista (asserts b/c/d/contrapartida) — READ ============
    if args.medir:
        mv = args.medir
        m = rd('account.move', [mv], ['name', 'state', 'journal_id', 'amount_total', 'amount_untaxed',
                                      'partner_id'])[0]
        print(f"=== MEDIR NF {mv} {m['name']} state={m['state']} journal={m2o(m['journal_id'])} "
              f"untax={m.get('amount_untaxed')} total={m.get('amount_total')} partner={m2o(m.get('partner_id'))} ===")
        nl = rr('account.move.line', [('move_id', '=', mv), ('display_type', '=', 'product')],
                ['product_id', 'quantity', 'price_unit', 'l10n_br_cfop_codigo', 'l10n_br_icms_cst',
                 'account_id', 'l10n_br_operacao_id'], limit=60)
        cfs = Counter(str(l.get('l10n_br_cfop_codigo')) for l in nl)
        print(f"\n  [b] linhas-produto: {len(nl)} | CFOPs: {dict(cfs)}")
        n5902 = sum(1 for l in nl if str(l.get('l10n_br_cfop_codigo')) == '5902')
        print(f"      5902={n5902} (esperado 16=2niveis OU 8=1nivel-com-semi)")
        print(f"\n  [c] CST por CFOP:")
        for cf in sorted(cfs):
            cst = Counter(str(l.get('l10n_br_icms_cst')) for l in nl if str(l.get('l10n_br_cfop_codigo')) == cf)
            print(f"      CFOP {cf}: CST {dict(cst)}")
        print(f"\n  detalhe linhas (produto / cfop / cst / conta / price_unit):")
        for l in nl:
            print(f"    [{m2o(l.get('product_id'))[:30]:30}] cfop={str(l.get('l10n_br_cfop_codigo')):5} "
                  f"cst={l.get('l10n_br_icms_cst')} conta={m2o(l.get('account_id'))[:28]:28} pu={l.get('price_unit')}")
        return

    # ============ REVERT — deleta NFs draft + devolve picking ============
    if args.revert:
        pid = args.revert[0]
        moves = args.revert[1:]
        print(f"=== REVERT picking {pid} + NFs {moves} ===")
        for mv in moves:
            st = rd('account.move', [mv], ['state'])
            if not st:
                print(f"  move {mv}: ja nao existe"); continue
            if st[0]['state'] == 'posted':
                o.execute_kw('account.move', 'button_draft', [[mv]], {'context': CTX})
            try:
                o.execute_kw('account.move', 'unlink', [[mv]], {'context': CTX})
                print(f"  move {mv} DELETADO")
            except Exception as e:
                o.execute_kw('account.move', 'button_cancel', [[mv]], {'context': CTX})
                print(f"  move {mv} unlink falhou; CANCELADO ({str(e)[:60]})")
        # devolver 1 un p/ src SE o picking de saida estiver done (sempre moveu 1 un p/ Clientes 5).
        # BUG-FIX: NAO checar estoque em SRC — produtos com saldo pre-existente (ex. azeite tem 4)
        # enganam a checagem e deixam 1 un presa em Clientes. Rodar --revert 1x (nao idempotente).
        pst = rd('stock.picking', [pid], ['state'])
        saiu = bool(pst and pst[0].get('state') == 'done')
        print(f"  picking saida {pid} state={pst[0].get('state') if pst else '?'} -> devolver={saiu}")
        if saiu:
            prod = rd('product.product', [PROD], ['uom_id'])[0]; uom = prod['uom_id'][0]
            ipt = rr('stock.picking.type', [('company_id', '=', LF), ('code', '=', 'internal')],
                     ['id'], limit=1)
            rpid = o.execute_kw('stock.picking', 'create', [{
                'picking_type_id': ipt[0]['id'], 'location_id': LOC_DST, 'location_dest_id': SRC,
                'company_id': LF, 'origin': 'GATE1-REVERT'}], {'context': CTX})
            mid_r = o.execute_kw('stock.move', 'create', [{
                'name': 'REVERT PA GATE1', 'picking_id': rpid, 'product_id': PROD,
                'product_uom_qty': 1.0, 'product_uom': uom, 'location_id': LOC_DST,
                'location_dest_id': SRC, 'company_id': LF}], {'context': CTX})
            o.execute_kw('stock.picking', 'action_confirm', [[rpid]], {'context': CTX})
            # customer(5) nao reserva -> criar move.line manual
            mlf = o.execute_kw('stock.move.line', 'fields_get', [], {'attributes': [], 'context': CTX})
            mlv = {'move_id': mid_r, 'picking_id': rpid, 'product_id': PROD, 'lot_id': LOTE,
                   'location_id': LOC_DST, 'location_dest_id': SRC, 'product_uom_id': uom,
                   'quantity': 1.0, 'company_id': LF}
            if 'qty_done' in mlf: mlv['qty_done'] = 1.0
            if 'picked' in mlf: mlv['picked'] = True
            o.execute_kw('stock.move.line', 'create', [mlv], {'context': CTX})
            o.execute_kw('stock.picking', 'button_validate', [[rpid]],
                         {'context': dict(CTX, skip_backorder=True, skip_immediate=True)})
            print(f"  PA devolvido 5->31093 via picking {rpid}")
        else:
            print("  PA ja em 31093 — sem devolucao")
        print(f"  >>> revert concluido.")
        return


if __name__ == '__main__':
    main()
