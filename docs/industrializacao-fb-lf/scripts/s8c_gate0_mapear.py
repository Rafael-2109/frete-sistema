#!/usr/bin/env python3
"""GATE 0 — FASE READ (mapeamento, READ-only). Fundamenta o experimento das 2 vias
para a NF do PA sair SO-5124.

VIA 1 (tipo-sem-explode): existe operacao com CFOP 5124 cujo tipo_pedido != 'venda-
  industrializacao'? Se sim, da p/ rotear o PA por um tipo que (talvez) nao explode.
VIA 2 (split em draft): qual a VND mista real menor p/ copiar e separar as 5902?

Mapeia (NAO escreve nada):
1. TODAS operacoes com codigo_cfop 5124 (+ tipo_pedido, movimento_estoque) e 5902.
2. tipos_pedido sale LF + journals + no_payment (confirma gap PASSIVA 26667).
3. pickings done do PA (27834) NAO-faturados (reusaveis p/ experimento via1).
4. VND mista referencia (menor j847) p/ via2.
5. quants do PA piloto (onde fatuar a partir).
Salva /tmp/s8c_gate0.txt.
"""
import sys
import io
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
_buf = io.StringIO()
def out(*a):
    s = ' '.join(str(x) for x in a); print(s); _buf.write(s + '\n')

def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"
    out(f"UID {o._uid}")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}; kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)
    def rd(model, ids, fields):
        ids = [i for i in ids if i]
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX}) if ids else []
    def fg(model, *needles):
        f = o.execute_kw(model, 'fields_get', [], {'attributes': ['string', 'type', 'relation'], 'context': CTX})
        return {k: v for k, v in f.items() if not needles or any(n in k.lower() for n in needles)}

    # 0) descobrir o campo de CFOP na operacao
    out("\n" + "=" * 90)
    out("0) campos de CFOP/tipo_pedido na operacao")
    out("=" * 90)
    opf = fg('l10n_br_ciel_it_account.operacao', 'cfop', 'tipo_pedido', 'movimento_estoque', 'name')
    out(f"  campos: {sorted(opf.keys())}")

    # 1) operacoes 5124 e 5902 (por CFOP)
    out("\n" + "=" * 90)
    out("1) OPERACOES com CFOP 5124 e 5902 — quais tipos_pedido? (decide VIA 1)")
    out("=" * 90)
    # resolver o cfop 5124/5902 ids (campo correto = codigo_cfop)
    cfop_fields = fg('l10n_br_ciel_it_account.cfop', 'cod')
    out(f"  cfop fields (codigo): {sorted(cfop_fields.keys())}")
    cod_field = 'codigo_cfop' if 'codigo_cfop' in cfop_fields else list(cfop_fields.keys())[0]
    cfops = rr('l10n_br_ciel_it_account.cfop', [(cod_field, 'in', ['5124', '5902'])],
               ['id', cod_field], limit=30)
    cfop_map = {}
    for c in cfops:
        cfop_map.setdefault(str(c.get(cod_field)), []).append(c['id'])
    out(f"  cfop ids (por {cod_field}): {cfop_map}")

    # operacao tem 4 campos de cfop; p/ FB<->LF intraestadual = l10n_br_intra_cfop_id
    cfop_op_field = 'l10n_br_intra_cfop_id'
    out(f"  campo cfop intraestadual na operacao: {cfop_op_field}")
    for cfop_code in ['5124', '5902']:
        ids = cfop_map.get(cfop_code, [])
        if not ids:
            out(f"  CFOP {cfop_code}: sem ids — pulando")
            continue
        ops = rr('l10n_br_ciel_it_account.operacao', [(cfop_op_field, 'in', ids)],
                 ['id', 'name', 'l10n_br_tipo_pedido', 'l10n_br_movimento_estoque', 'company_id'], limit=80)
        out(f"\n  >>> CFOP {cfop_code}: {len(ops)} operacoes")
        tps = Counter(str(op.get('l10n_br_tipo_pedido')) for op in ops)
        out(f"      tipos_pedido distintos: {dict(tps)}")
        for op in ops:
            out(f"      op{op['id']:5} tp={str(op.get('l10n_br_tipo_pedido')):24} "
                f"mov_est={op.get('l10n_br_movimento_estoque')} cmp={m2o(op.get('company_id'))[:14]} | {op.get('name')[:40]}")

    # 2) tipos_pedido sale LF + journals + no_payment
    out("\n" + "=" * 90)
    out("2) journals sale LF: tipo_pedido + no_payment (confirma rota da 2a NF)")
    out("=" * 90)
    js = rr('account.journal', [('company_id', '=', 5), ('type', '=', 'sale')],
            ['id', 'name', 'l10n_br_tipo_pedido', 'account_no_payment_id'], limit=40)
    for j in js:
        np = m2o(j.get('account_no_payment_id'))
        flag = '  <<< PASSIVA 26667' if np.startswith('26667|') else ''
        out(f"  j{j['id']:<5} tp={str(j.get('l10n_br_tipo_pedido')):24} no_pay={np[:40]}{flag}")

    # 3) pickings done do PA NAO-faturados (reusaveis p/ experimento)
    out("\n" + "=" * 90)
    out("3) pickings out_invoice do PA 27834 (4870112) done NAO-faturados (reuso experimento)")
    out("=" * 90)
    # moves do PA em pickings de saida
    sm = rr('stock.move', [('product_id', '=', 27834), ('company_id', '=', 5)],
            ['id', 'picking_id', 'location_id', 'location_dest_id', 'state', 'quantity'], limit=50, order='id desc')
    pick_ids = list({s['picking_id'][0] for s in sm if isinstance(s.get('picking_id'), list)})
    picks = rd('stock.picking', pick_ids, ['id', 'name', 'state', 'picking_type_id', 'invoice_id',
               'location_id', 'location_dest_id', 'liberado_faturamento']) if pick_ids else []
    out(f"  pickings com move do PA: {len(picks)}")
    for p in picks[:20]:
        out(f"     pk{p['id']:6} {p.get('name'):20} state={p.get('state'):9} pt={m2o(p.get('picking_type_id'))[:24]:24} "
            f"inv={m2o(p.get('invoice_id'))[:14]} src={m2o(p.get('location_id'))[:16]}")

    # 4) VND mista referencia (menor j847) p/ via2 copy
    out("\n" + "=" * 90)
    out("4) VND mista menor (j847) — referencia p/ VIA 2 (copy+split)")
    out("=" * 90)
    vnd = rr('account.move', [('journal_id', '=', 847), ('company_id', '=', 5),
                              ('state', '=', 'posted'), ('move_type', '=', 'out_invoice'),
                              ('amount_total', '>', 0)],
             ['id', 'name', 'amount_total'], limit=20, order='amount_total asc')
    out(f"  3 menores VND mistas j847:")
    for v in vnd[:3]:
        nl = rr('account.move.line', [('move_id', '=', v['id']), ('display_type', '=', 'product')],
                ['l10n_br_cfop_codigo'], limit=100)
        cfs = Counter(str(l.get('l10n_br_cfop_codigo')) for l in nl)
        out(f"     move {v['id']} {v['name']} total={v['amount_total']} CFOPs={dict(cfs)}")

    # 5) quants PA piloto
    out("\n" + "=" * 90)
    out("5) quants do PA 27834 (de onde faturar no experimento)")
    out("=" * 90)
    q = rr('stock.quant', [('product_id', '=', 27834), ('location_id', 'in', [8, 42, 31093, 26489])],
           ['location_id', 'lot_id', 'quantity', 'reserved_quantity'], limit=30)
    for x in q:
        out(f"     loc={m2o(x.get('location_id'))[:30]:30} lot={m2o(x.get('lot_id'))[:18]:18} "
            f"qty={x.get('quantity')} resv={x.get('reserved_quantity')}")

    out("\n[FIM s8c_gate0_mapear — READ-only]")
    with open('/tmp/s8c_gate0.txt', 'w') as f:
        f.write(_buf.getvalue())
    out(">>> salvo em /tmp/s8c_gate0.txt")


if __name__ == '__main__':
    main()
