#!/usr/bin/env python3
"""S8 — GROUNDING DA HIPOTESE (i) + ESTADO DO PILOTO (READ-only, sessao 8).

Pergunta central (passo 1 do handoff): o `create_invoice()` do wizard CIEL IT
`stock.invoice.onshipping` SEPARA a expansao da BoM por picking_type (=> 2 NFs
nativas, so config) ou FUNDE tudo na NF do picking faturado (=> precisa do nosso
pipeline / Forma 2)?

Triangulacao READ-only (nao escreve NADA):
  BLOCO 1 — hipotese (i):
    1a campos de vinculo picking<->invoice (invoice_id singular? invoice_ids?)
    1b empirico: moves j847 (venda-industrializacao LF) recentes — agrupa por `ref`
       (=picking) e detecta se ALGUM picking gerou >1 NF (validaria a hipotese)
    1c empirico: cada move j847 mistura CFOPs 5124+5902 no MESMO move? (=funde)
    1d config: campos do picking_type (66/97/98/94/53/52) e operacoes (2702/2864)
       que controlem separacao/expansao/industrializacao; reconfirma wizard
  BLOCO 2 — estado AO VIVO do piloto (4870112, lote PILOTO-3105):
    2a PA em 31093? trânsito 26489=0? 30720=42,29? 31092 consumido?
    2b contas de compensacao do ciclo (5101010001 FB / 5101020001 LF) — obrigacao
       aberta (~R$278,56) ainda NAO baixada?
    2c docs do piloto: RPI/2026/00245 (735679), ENTIN 737062, MOs 20252/20254
  BLOCO 3 — gaps de config p/ caminho (b)/Forma 2:
    3a NENHUM journal sale LF aponta no_payment=26667 (PASSIVA 5101020001)?
    3b j1001 (FB ENTSI) no_payment atual (esperado VAZIO)
    3c pt98 tipo_pedido (esperado False) + invoice_move_type

Salva tudo em /tmp/s8_hipotese_i.txt.
"""
import sys
import io
from collections import Counter, defaultdict
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}

# captura tudo p/ arquivo
_buf = io.StringIO()
def out(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    _buf.write(s + '\n')


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v is False or v is None else str(v)


def cfop(v):
    # l10n_br_cfop_id label tipicamente "5902 - ..." ou codigo_cfop separado
    return v[1].split(' - ')[0].split()[0].strip() if isinstance(v, list) and v else '-'


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    out(f"UID {o._uid}  CTX={CTX}")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    def rd(model, ids, fields):
        ids = [i for i in ids if i]
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX}) if ids else []

    def fg(model, *needles):
        f = o.execute_kw(model, 'fields_get', [], {'attributes': ['string', 'type', 'relation'], 'context': CTX})
        if not needles:
            return f
        return {k: v for k, v in f.items() if any(n in k.lower() for n in needles)}

    # =================================================================
    out("\n" + "#" * 90)
    out("# BLOCO 1 — HIPOTESE (i): create_invoice separa por picking_type ou funde?")
    out("#" * 90)

    out("\n=== 1a) campos de vinculo picking<->invoice ===")
    pv = fg('stock.picking', 'invoice')
    for k, v in sorted(pv.items()):
        out(f"  stock.picking.{k:30} {v.get('type'):10} rel={v.get('relation')}  '{v.get('string')}'")
    mvv = fg('account.move', 'picking', 'stock', 'onshipping')
    for k, v in sorted(mvv.items()):
        out(f"  account.move.{k:30} {v.get('type'):10} rel={v.get('relation')}  '{v.get('string')}'")

    out("\n=== 1b) moves j847 (venda-industrializacao LF) recentes: 1 picking -> quantas NFs? ===")
    vnd = rr('account.move', [('journal_id', '=', 847), ('company_id', '=', 5),
                              ('move_type', '=', 'out_invoice'), ('state', '=', 'posted')],
             ['id', 'name', 'ref', 'invoice_origin', 'amount_total', 'amount_untaxed'],
             limit=200, order='id desc')
    out(f"  total VND posted lidas: {len(vnd)}")
    by_ref = defaultdict(list)
    for m in vnd:
        key = (m.get('ref') or '') or ('origin:' + str(m.get('invoice_origin') or ''))
        by_ref[key].append(m['id'])
    multi = {k: v for k, v in by_ref.items() if len(v) > 1 and k}
    out(f"  pickings/refs distintos: {len(by_ref)}")
    out(f"  >>> refs com >1 NF (anomalia que VALIDARIA a hipotese i): {len(multi)}")
    for k, v in list(multi.items())[:15]:
        out(f"       ref={k!r} -> moves {v}")
    if not multi:
        out("       (NENHUM ref gerou 2 NFs => 1 picking = 1 NF, consistente com 'funde')")

    out("\n=== 1c) cada move j847 mistura CFOP 5124+5902 no MESMO move? (=funde) ===")
    amostra = [m['id'] for m in vnd[:25]]
    mistos = so5124 = so5902 = 0
    detalhe = []
    for mid in amostra:
        ln = rr('account.move.line', [('move_id', '=', mid), ('display_type', '=', 'product')],
                ['l10n_br_cfop_id', 'product_id'], limit=200)
        cfs = Counter(cfop(l.get('l10n_br_cfop_id')) for l in ln)
        tem5124 = '5124' in cfs
        tem5902 = '5902' in cfs
        if tem5124 and tem5902:
            mistos += 1
        elif tem5124:
            so5124 += 1
        elif tem5902:
            so5902 += 1
        detalhe.append((mid, dict(cfs)))
    out(f"  amostra de {len(amostra)} moves j847:")
    out(f"     MISTOS (5124+5902 juntos): {mistos}")
    out(f"     so 5124: {so5124}   so 5902: {so5902}   outros: {len(amostra)-mistos-so5124-so5902}")
    for mid, cfs in detalhe[:12]:
        out(f"     move {mid}: CFOPs={cfs}")

    out("\n=== 1d) config: picking_types e operacoes — flags de separacao/expansao? ===")
    ptf = fg('stock.picking.type', 'tipo_pedido', 'invoice', 'industri', 'retorno', 'devol',
             'componente', 'bom', 'separ', 'simbol', 'l10n_br')
    out(f"  campos picking_type relevantes: {sorted(ptf.keys())}")
    pts = rd('stock.picking.type', [66, 97, 98, 94, 53, 52, 64], ['id', 'name', 'code'] + list(ptf.keys()))
    for p in pts:
        out(f"\n  pt{p['id']} {p.get('name')} code={p.get('code')}")
        for k in ptf:
            v = p.get(k)
            if v not in (False, None, '', []):
                out(f"      {k:28} = {m2o(v) if isinstance(v, list) else v}")
    # operacoes 2702 (5124) e 2864 (5902)
    out("\n  --- operacoes fiscais 2702(5124) / 2864(5902): campos de industrializacao/expansao ---")
    opf = fg('l10n_br_ciel_it_account.operacao', 'industri', 'componente', 'bom', 'retorno',
             'devol', 'tipo_pedido', 'movimento_estoque', 'simbol', 'expand', 'remessa')
    ops = rd('l10n_br_ciel_it_account.operacao', [2702, 2864, 850, 2710, 2711, 3252],
             ['id', 'name'] + list(opf.keys()))
    for op in ops:
        out(f"  op{op['id']} {op.get('name')}")
        for k in opf:
            v = op.get(k)
            if v not in (False, None, '', []):
                out(f"      {k:28} = {m2o(v) if isinstance(v, list) else v}")
    # wizard onshipping — TODOS os campos custom (nao-padrao)
    out("\n  --- wizard stock.invoice.onshipping: campos (procurando separacao/journal/group) ---")
    wf = fg('stock.invoice.onshipping')
    interess = {k: v for k, v in wf.items() if any(n in k.lower() for n in
               ('journal', 'group', 'industri', 'componente', 'bom', 'separ', 'retorno', 'tipo', 'l10n_br'))}
    for k, v in sorted(interess.items()):
        out(f"      {k:30} {v.get('type'):10} rel={v.get('relation')}  '{v.get('string')}'")

    # =================================================================
    out("\n" + "#" * 90)
    out("# BLOCO 2 — ESTADO AO VIVO DO PILOTO (4870112, lote PILOTO-3105)")
    out("#" * 90)

    out("\n=== 2a) quants do PA 4870112 + componentes lote PILOTO-3105 por location ===")
    # PA product
    pa = rr('product.product', [('default_code', '=', '4870112')], ['id', 'default_code', 'name'])
    out(f"  PA 4870112 -> {[m2o([p['id'], p['name']]) for p in pa]}")
    locs = {8: 'FB/Estoque', 42: 'LF/Estoque', 26489: 'Em Transito Ind', 30720: 'FB->poder LF',
            31092: 'LF/Mat-Terceiros', 31093: 'LF/PA-Terceiros'}
    for prod_code in ['4870112']:
        q = rr('stock.quant', [('product_id.default_code', '=', prod_code),
                               ('location_id', 'in', list(locs.keys()))],
               ['location_id', 'lot_id', 'quantity', 'reserved_quantity', 'company_id'], limit=100)
        out(f"  quants do PA {prod_code} nas locations-chave: {len(q)}")
        for x in q:
            out(f"     loc={m2o(x.get('location_id'))[:34]:34} lot={m2o(x.get('lot_id'))[:20]:20} "
                f"qty={x.get('quantity')} resv={x.get('reserved_quantity')} cmp={m2o(x.get('company_id'))}")
    out("\n  --- trânsito 26489 + 30720: QUALQUER quant do lote PILOTO-3105 (deve: 26489~0, 30720~42,29) ---")
    qt = rr('stock.quant', [('lot_id.name', '=', 'PILOTO-3105'),
                            ('location_id', 'in', [26489, 30720, 31092, 31093])],
            ['product_id', 'location_id', 'lot_id', 'quantity', 'company_id'], limit=300)
    agg = defaultdict(float)
    for x in qt:
        agg[m2o(x.get('location_id'))] += x.get('quantity') or 0
    out(f"  quants lote PILOTO-3105 nessas locs: {len(qt)}; soma por loc:")
    for loc, s in agg.items():
        out(f"     {loc[:40]:40} soma_qty={round(s,4)}")

    out("\n=== 2b) contas de compensacao do ciclo (saldo total — contexto, NAO so o ciclo) ===")
    # saldo geral das contas-chave (ATIVA FB 22800 / PASSIVA LF 26667)
    for acc_id, lbl in [(22800, '5101010001 ATIVA (FB)'), (26667, '5101020001 PASSIVA (LF)')]:
        try:
            grp = o.execute_kw('account.move.line', 'read_group',
                               [[('account_id', '=', acc_id), ('parent_state', '=', 'posted')]],
                               {'fields': ['balance:sum', 'debit:sum', 'credit:sum'],
                                'groupby': [], 'context': CTX})
            g = grp[0] if grp else {}
            out(f"  {lbl}: saldo={g.get('balance')} D={g.get('debit')} C={g.get('credit')} n={g.get('__count')}")
        except Exception as e:
            out(f"  {lbl}: read_group falhou ({e})")

    out("\n=== 2c) documentos do piloto: RPI 735679, ENTIN 737062, MOs 20252/20254 ===")
    docs = rd('account.move', [735679, 737062], ['id', 'name', 'state', 'journal_id', 'move_type',
              'amount_untaxed', 'amount_total', 'l10n_br_situacao_nf', 'company_id'])
    for d in docs:
        out(f"  move {d['id']} {d.get('name')} state={d.get('state')} jrnl={m2o(d.get('journal_id'))[:24]} "
            f"sit_nf={d.get('l10n_br_situacao_nf')} untax={d.get('amount_untaxed')} cmp={m2o(d.get('company_id'))}")
    mos = rd('mrp.production', [20252, 20254], ['id', 'name', 'state', 'product_id', 'product_qty', 'company_id'])
    for mo in mos:
        out(f"  MO {mo['id']} {mo.get('name')} state={mo.get('state')} prod={m2o(mo.get('product_id'))[:30]} "
            f"qty={mo.get('product_qty')}")

    # =================================================================
    out("\n" + "#" * 90)
    out("# BLOCO 3 — GAPS DE CONFIG p/ caminho (b)/Forma 2")
    out("#" * 90)

    out("\n=== 3a) journals sale LF e seu no_payment — ALGUM aponta 26667 (PASSIVA 5101020001)? ===")
    # confirma nomes de campo
    jfields = fg('account.journal', 'no_payment', 'tipo_pedido')
    out(f"  campos journal no_payment/tipo_pedido: {sorted(jfields.keys())}")
    use = ['id', 'name', 'type', 'l10n_br_tipo_pedido'] + [k for k in jfields if 'no_payment' in k]
    js = rr('account.journal', [('company_id', '=', 5), ('type', '=', 'sale')], use, limit=80)
    out(f"  journals sale LF: {len(js)}")
    aponta_passiva = []
    for j in js:
        npid = j.get('account_no_payment_id')
        flag = ''
        if isinstance(npid, list) and npid and npid[0] == 26667:
            flag = '  <<< APONTA PASSIVA 26667!'
            aponta_passiva.append(j['id'])
        out(f"     j{j['id']:<5} tp={str(j.get('l10n_br_tipo_pedido')):24} "
            f"no_pay={m2o(npid)}{flag}")
    out(f"  >>> journals sale LF apontando PASSIVA 26667: {aponta_passiva or 'NENHUM (gap confirmado)'}")

    out("\n=== 3b) j1001 (FB ENTSI) no_payment atual (esperado VAZIO) ===")
    j1001 = rd('account.journal', [1001], ['id', 'name', 'type', 'l10n_br_tipo_pedido',
               'l10n_br_tipo_pedido_entrada', 'account_no_payment_id'])
    for j in j1001:
        out(f"  j{j['id']} {j.get('name')} type={j.get('type')} "
            f"tpe={j.get('l10n_br_tipo_pedido_entrada')} no_pay={m2o(j.get('account_no_payment_id'))}")

    out("\n=== 3c) pt98/pt66/pt97 tipo_pedido + invoice_move_type ===")
    pts2 = rd('stock.picking.type', [98, 66, 97, 94], ['id', 'name', 'l10n_br_tipo_pedido',
              'invoice_move_type', 'default_location_src_id', 'default_location_dest_id'])
    for p in pts2:
        out(f"  pt{p['id']} {p.get('name')[:30]:30} tp={str(p.get('l10n_br_tipo_pedido')):24} "
            f"inv_move={p.get('invoice_move_type')} "
            f"src={m2o(p.get('default_location_src_id'))[:18]} dst={m2o(p.get('default_location_dest_id'))[:18]}")

    out("\n[FIM s8_hipotese_i_grounding — READ-only]")

    with open('/tmp/s8_hipotese_i.txt', 'w') as f:
        f.write(_buf.getvalue())
    out("\n>>> salvo em /tmp/s8_hipotese_i.txt")


if __name__ == '__main__':
    main()
