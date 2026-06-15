#!/usr/bin/env python3
"""S69 — READ-only: DESCOBERTA AUTOMÁTICA da fonte da NF-2 (item 1 da automação).

Corrige as 2 lacunas que o s46 deixou marcadas para a automação:
  (iii-valor) o valor NÃO sai do quant atual de 31092 (consumo zera o quant -> vu=0):
              usa o SVL HISTÓRICO do move de consumo (unit_cost = valor de recebimento
              do material de terceiros = valor da remessa; invariante 5902=5901).
  (remessa)   a remessa NÃO é hardcoded: descobre a RPI rastreando cada material de
              terceiros consumido -> move de ENTRADA em 31092 -> picking/DFe -> NF de remessa.

Mantém a genealogia recursiva PROVADA do s46 (explode lote->MOs->semis->31092),
exclui ÁGUA (type=consu, consumo local), total = produção REAL (qty_producing).

Âncoras VIVAS (validadas 2026-06-15): NF-1 791437 VND/2026/00384 -> PA 27834 lote 60542,
qtd faturada 1,0. Remessa-alvo: RPI/2026/00245 (move 735679), 16 itens, R$ 279,23.
READ-ONLY: zero escrita no Odoo.
"""
import sys
from collections import defaultdict
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF1 = 791437              # NF-1 serviço viva (autorizada SEFAZ)
LOC_TERCEIROS = 31092     # LF / Materiais de Terceiros
REMESSA_ESPERADA = 735679  # move da RPI/2026/00245 (só p/ conferência do resultado)


def m2o(v):
    return f"{v[0]}|{str(v[1])[:24]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    acc_qty = defaultdict(float)        # pid -> qty rateada
    acc_moves = defaultdict(list)       # pid -> [consumption move ids] (p/ SVL e remessa)
    log = []

    def explode(lot_id, fator, depth=0):
        """Acumula materiais de terceiros (31092) consumidos p/ produzir `fator` un do lote."""
        mos = rr('mrp.production', [('lot_producing_id', '=', lot_id), ('state', '=', 'done')],
                 ['id', 'name', 'product_qty', 'qty_producing'])
        if not mos:
            return False   # folha (não produzido aqui = matéria-prima)
        total = sum((m.get('qty_producing') or m.get('product_qty') or 0) for m in mos) or 1.0
        log.append(f"{'  '*depth}lote {lot_id}: {len(mos)} MO(s) total_prod_REAL={total} fator={round(fator,5)}")
        for mo in mos:
            raws = rr('stock.move', [('raw_material_production_id', '=', mo['id']),
                                     ('state', '=', 'done')],
                     ['id', 'product_id', 'product_qty', 'location_id', 'product_uom_qty'])
            for r in raws:
                pid = r['product_id'][0]; q = r.get('product_qty') or 0
                mls = rr('stock.move.line', [('move_id', '=', r['id'])], ['lot_id'], limit=1)
                comp_lot = mls[0]['lot_id'][0] if (mls and mls[0].get('lot_id')) else None
                share = q * fator / total
                is_semi = False
                if comp_lot:
                    is_semi = explode(comp_lot, share, depth + 1)
                if not is_semi and r.get('location_id') and r['location_id'][0] == LOC_TERCEIROS:
                    acc_qty[pid] += share
                    acc_moves[pid].append(r['id'])
        return True

    # ── NF-1 -> PA + lote + qtd faturada ───────────────────────────────────
    pal = rr('account.move.line', [('move_id', '=', NF1), ('l10n_br_cfop_codigo', '=', '5124')],
             ['product_id', 'quantity'], limit=1)
    assert pal, f"NF-1 {NF1} sem linha 5124"
    pa_pid = pal[0]['product_id'][0]; pa_qty = pal[0]['quantity']
    pk = rr('stock.picking', ['|', ('invoice_id', '=', NF1), ('invoice_ids', 'in', [NF1])], ['id'], limit=1)
    ml = rr('stock.move.line', [('picking_id', '=', pk[0]['id']), ('product_id', '=', pa_pid)], ['lot_id'], limit=1)
    lot_pa = ml[0]['lot_id'][0]
    print("=" * 96)
    print(f"### NF-1 {NF1}: fatura {pa_qty} un do PA {m2o(pal[0]['product_id'])} lote {lot_pa}")
    print("=" * 96)
    explode(lot_pa, pa_qty)
    for l in log:
        print("   " + l)

    pinfo = {p['id']: p for p in rr('product.product', [('id', 'in', list(acc_qty))],
             ['id', 'default_code', 'name', 'standard_price', 'type'])}

    # ── filtro ÁGUA (type=consu, consumo local, não é material de terceiros) ─
    agua = [pid for pid in acc_qty if (pinfo.get(pid, {}).get('type') == 'consu')]
    for pid in agua:
        log.append(f"  EXCLUI ÁGUA/consu [{pinfo[pid].get('default_code')}]")
        del acc_qty[pid]
    comps = list(acc_qty)

    # ── VALOR via SVL histórico do move de ENTRADA em 31092 (= preço da remessa) ──
    # 🔑 CONFIRMADO (s69): o SVL da ENTRADA (location_dest=31092) tem unit_cost == price_unit
    # da remessa (invariante 5902=5901). O SVL do CONSUMO daria o AVCO interno da LF (errado).
    # Mesma query serve à DESCOBERTA DA REMESSA (picking de origem da entrada).
    remessa_votos = defaultdict(float)
    entrada_moves = rr('stock.move',
                       [('product_id', 'in', comps), ('location_dest_id', '=', LOC_TERCEIROS),
                        ('state', '=', 'done')],
                       ['id', 'product_id', 'picking_id', 'origin', 'reference', 'date'])
    svl_ent = rr('stock.valuation.layer',
                 [('stock_move_id', 'in', [e['id'] for e in entrada_moves])],
                 ['stock_move_id', 'product_id', 'quantity', 'value', 'unit_cost'])
    # unit_cost da entrada mais recente por produto (= preço de recebimento = remessa)
    vu_svl = {}
    ent_by_prod = defaultdict(list)
    for e in entrada_moves:
        ent_by_prod[e['product_id'][0]].append(e)
        key = m2o(e.get('picking_id')) if e.get('picking_id') else (e.get('origin') or e.get('reference') or '?')
        remessa_votos[key] += 1
    svl_by_move = {s['stock_move_id'][0]: s for s in svl_ent if s.get('stock_move_id')}
    for pid, ems in ent_by_prod.items():
        ems_sorted = sorted(ems, key=lambda x: x.get('date') or '', reverse=True)
        for em in ems_sorted:
            s = svl_by_move.get(em['id'])
            if s and s.get('unit_cost'):
                vu_svl[pid] = s['unit_cost']
                break

    # ── relatório ───────────────────────────────────────────────────────────
    print(f"\n### {len(comps)} materiais de terceiros (qty rateada p/ {pa_qty} un PA) + VALOR via SVL")
    total_svl = 0.0
    for pid in sorted(comps, key=lambda x: pinfo.get(x, {}).get('default_code') or ''):
        p = pinfo.get(pid, {}); q = acc_qty[pid]
        vu = vu_svl.get(pid)
        vu_q = round(vu, 5) if vu is not None else f"SEM-SVL(std={p.get('standard_price')})"
        sub = (q * vu) if vu is not None else 0
        total_svl += sub
        print(f"   [{p.get('default_code')}] {str(p.get('name'))[:30]:30} qty={round(q,5):>9} "
              f"vu_SVL={str(vu_q):>16} sub={round(sub,2):>8}")

    # comparação com a remessa esperada (conferência)
    rl = rr('account.move.line', [('move_id', '=', REMESSA_ESPERADA), ('display_type', '=', 'product')],
            ['product_id', 'price_subtotal', 'quantity'])
    rem_ids = {l['product_id'][0] for l in rl}
    rem_total = round(sum(l.get('price_subtotal') or 0 for l in rl), 2)
    der_ids = set(comps)
    print(f"\n### Conferência vs remessa esperada (move {REMESSA_ESPERADA} = RPI/2026/00245)")
    print(f"   itens remessa={len(rem_ids)} derivado={len(der_ids)} | "
          f"falta={[pinfo.get(i,{}).get('default_code') or i for i in (rem_ids-der_ids)] or '-'} | "
          f"sobra={[pinfo.get(i,{}).get('default_code') or i for i in (der_ids-rem_ids)] or '-'} | "
          f"{'✅ MATCH itens' if rem_ids==der_ids else '⚠️ DIVERGE itens'}")
    pa_mos = rr('mrp.production', [('lot_producing_id', '=', lot_pa), ('state', '=', 'done')],
                ['qty_producing'])
    total_prod = sum(m.get('qty_producing') or 0 for m in pa_mos)
    print(f"\n   🔴 DECISÃO DE FUNDO (valor da NF-2):")
    print(f"      (A) RATEIO por qtd faturada (NF-1={pa_qty} de {total_prod} PA produzidos no lote) "
          f"= SVL_entrada x qty_genealogia = R$ {round(total_svl,2)}")
    print(f"      (B) REMESSA INTEIRA (o que o piloto s37 retornou)              = R$ {rem_total}")
    print(f"      -> Esfera fiscal: a ATIVA (5101010001) só zera retornando a remessa INTEIRA;")
    print(f"         rateio deixa saldo aberto até os demais PA voltarem (perna 5903 p/ sobras).")

    print(f"\n### Descoberta da REMESSA (votos por candidato origem da entrada em 31092)")
    for k, v in sorted(remessa_votos.items(), key=lambda x: -x[1]):
        print(f"   {int(v):>3}x  {k}")


if __name__ == '__main__':
    main()
