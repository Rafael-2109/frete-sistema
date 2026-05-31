#!/usr/bin/env python3
"""
ETAPA 1 — DRY-RUN/PREVIEW da REMESSA FB->LF (pt53, NF 5901). READ-ONLY: NAO cria nada.

Mostra a RECEITA EXATA que seria remetida para N caixa(s) de 4870112:
  - explode BoM 3695 (PA) + 3646 (BATELADA) ao vivo, dividindo pelo rendimento (product_qty)
    de cada BoM -> 16 componentes remetidos (semi BATELADA produzido na LF NAO remete;
    AGUA e' consu propria LF)
  - LISTA lotes com saldo livre em FB/Estoque(8 + sublocations), ordem FIFO por in_date
    (operador confirma o lote); confere disponibilidade (saldo livre >= qty necessaria)
  - custo (standard_price FB) -> Ic (valor da remessa)
  - CHECKLIST das pre-condicoes de liberar_faturamento (ACHADOS §4, campos Odoo 17):
    stock.picking.incoterm=6 (NAO incoterm_id), carrier_id=996, res.company(FB).warehouse_id,
    operacao 5901 (op 80) + CFOP 5901 (codigo_cfop) na linha
  - estado do rastro 29/05 (picking 322049 done + NF 725676 cancel + devolucao) p/ decidir
    reaproveitar-vs-nova

Odoo 17: linhas de produto da fatura tem display_type='product'; CFOP usa codigo_cfop.

Uso:
    python e2e_remessa_etapa1_dryrun.py            # 1 caixa
    python e2e_remessa_etapa1_dryrun.py --caixas 1
"""
import argparse
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_FB = 1
BOM_PA = 3695
BOM_BAT = 3646
SEMI_CODE = '3800018'      # BATELADA — produzido na LF, nao remete
LOC_FB = 8                 # FB/Estoque (+ sublocations)
LOC_TRANSITO = 26489       # destino da remessa
PT_REMESSA = 53            # FB: Expedicao Industrializacao
INCOTERM_OK = 6            # CIF (campo stock.picking.incoterm)
CARRIER_OK = 996
JOURNAL_REMESSA = 17       # REMESSA P/ INDUSTRIALIZACAO


def ctx_fb():
    return {'allowed_company_ids': [CMP_FB], 'company_id': CMP_FB}


def sec(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


def explode(o, caixas):
    """Explode BoM dividindo pelo rendimento -> {pid: {...}} remetidos (sem semi/consu)."""
    comps = {}

    def add(pid, qty, via):
        p = o.read('product.product', [pid], ['default_code', 'name', 'type'])[0]
        comps[pid] = {'cod': p['default_code'], 'nome': p['name'][:34], 'type': p['type'], 'qty': qty, 'via': via}
        return p

    bpa = o.read('mrp.bom', [BOM_PA], ['product_qty'])[0]
    rende_pa = bpa['product_qty'] or 1.0
    factor_pa = caixas / rende_pa
    semi_pid, semi_qty = None, 0.0
    for l in o.search_read('mrp.bom.line', [('bom_id', '=', BOM_PA)], ['product_id', 'product_qty']):
        pid = l['product_id'][0]
        p = add(pid, l['product_qty'] * factor_pa, 'PA-direto')
        if (p['default_code'] or '').strip() == SEMI_CODE:
            semi_pid, semi_qty = pid, l['product_qty'] * factor_pa
    if semi_pid:
        del comps[semi_pid]
        bbat = o.read('mrp.bom', [BOM_BAT], ['product_qty'])[0]
        rende_bat = bbat['product_qty'] or 1.0
        factor_bat = semi_qty / rende_bat
        for l in o.search_read('mrp.bom.line', [('bom_id', '=', BOM_BAT)], ['product_id', 'product_qty']):
            pid = l['product_id'][0]
            add(pid, l['product_qty'] * factor_bat, f'BATELADA x{semi_qty:g}')
    remetidos = {pid: c for pid, c in comps.items() if c['type'] == 'product'}
    consu = {pid: c for pid, c in comps.items() if c['type'] != 'product'}
    return remetidos, consu, semi_qty


def lots_fb(o, pid):
    """quants do produto em FB/Estoque(8)+sublocations, qty>0, ordem FIFO (in_date asc)."""
    locs = o.search_read('stock.location', [('id', 'child_of', LOC_FB)], ['id'], limit=500)
    loc_ids = [x['id'] for x in locs]
    return o.search_read('stock.quant',
                         [('product_id', '=', pid), ('location_id', 'in', loc_ids), ('quantity', '>', 0)],
                         ['lot_id', 'location_id', 'quantity', 'reserved_quantity', 'in_date'],
                         limit=100, order='in_date asc')


def resolve_op_5901(o):
    """op fiscal da linha 5901 numa remessa pt53 REAL posted (codigo_cfop 5901). Retorna (op, cfop)."""
    try:
        nfs = o.search_read('account.move', [('journal_id', '=', JOURNAL_REMESSA),
                                             ('move_type', '=', 'out_invoice'), ('state', '=', 'posted')],
                            ['invoice_line_ids', 'name'], limit=8, order='id desc')
        for n in nfs:
            if not n.get('invoice_line_ids'):
                continue
            ls = o.read('account.move.line', n['invoice_line_ids'],
                        ['product_id', 'l10n_br_operacao_id', 'l10n_br_cfop_id'])
            for l in ls:
                cfop = l['l10n_br_cfop_id']
                if l['product_id'] and cfop and isinstance(cfop, list) and cfop[1].strip().startswith('5901'):
                    return l['l10n_br_operacao_id'], cfop, n['name']
    except Exception as e:
        print(f"  [aviso] resolve op 5901 falhou: {e}")
    return None, None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--caixas', type=float, default=1.0)
    args = ap.parse_args()
    o = get_odoo_connection(); o.authenticate()

    sec(f"ETAPA 1 — PREVIEW REMESSA FB->LF (pt53, NF 5901) — {args.caixas:g} caixa(s) de 4870112 — READ-ONLY")

    remetidos, consu, semi_qty = explode(o, args.caixas)
    pids = list(remetidos)
    costs = {c['id']: c['standard_price'] for c in
             o.execute_kw('product.product', 'read', [pids, ['standard_price']], {'context': ctx_fb()})}

    print(f"\n{'cod':>12} {'componente':<34} {'qty':>12} {'std_price':>10} {'valor':>11} {'disp.livre.FB':>13} lote(s) FIFO")
    print("-" * 132)
    Ic = 0.0
    faltam = []
    for pid in sorted(pids, key=lambda x: remetidos[x]['cod'] or ''):
        c = remetidos[pid]
        cst = costs.get(pid, 0.0)
        val = c['qty'] * cst
        Ic += val
        qs = lots_fb(o, pid)
        disp = sum(x['quantity'] - x['reserved_quantity'] for x in qs)
        lots = ", ".join(f"{(x['lot_id'][1] if x['lot_id'] else 's/lote')}={max(0.0, x['quantity']-x['reserved_quantity']):g}" for x in qs[:3])
        falta = "  *** FALTA" if disp < c['qty'] - 1e-6 else ""
        if falta:
            faltam.append((c['cod'], round(c['qty'], 4), round(disp, 4)))
        print(f"{c['cod'] or '?':>12} {c['nome']:<34} {c['qty']:>12.6f} {cst:>10.4f} {val:>11.2f} {disp:>13.4f} {lots[:42]}{falta}")
    print("-" * 132)
    print(f">>> {len(pids)} componentes remetidos | Ic (valor remessa, AVCO FB) = R$ {Ic:,.2f}")
    print(f">>> S (valor agregado LF) = R$ 35,00/cx x {args.caixas:g} = R$ {35.0*args.caixas:,.2f}  |  PA(Ic+S) = R$ {Ic + 35.0*args.caixas:,.2f}")
    for pid, c in consu.items():
        print(f"    [NAO remete] {c['cod']} {c['nome']} qty={c['qty']:.4f} ({c['type']}, propria LF)")
    print(f"    [NAO remete] BATELADA semi (produzida na MO LF) — {semi_qty:g} un")
    if faltam:
        print(f"\n  *** BLOQUEADOR: {len(faltam)} componente(s) SEM saldo livre suficiente em FB/Estoque: {faltam}")
        print(f"      -> repor/transferir p/ FB/Estoque(8) ANTES de criar a remessa.")

    # ---- picking type + locations
    sec("PICKING TYPE DE CRIACAO + LOCATIONS")
    pt = o.read('stock.picking.type', [PT_REMESSA],
                ['name', 'code', 'default_location_src_id', 'default_location_dest_id', 'warehouse_id'])
    if pt:
        pt = pt[0]
        print(f"  pt{PT_REMESSA} {pt['name']} code={pt['code']} src={pt['default_location_src_id']} dst={pt['default_location_dest_id']} wh={pt['warehouse_id']}")
    print(f"  remessa: FB/Estoque(8) -> Em Transito Industrializacao(26489)")

    # ---- checklist pre-condicoes liberar_faturamento
    sec("CHECKLIST PRE-CONDICOES liberar_faturamento (ACHADOS §4)")
    print("  AMBIENTE (ja satisfeito):")
    comp = o.read('res.company', [CMP_FB], ['name', 'warehouse_id'])
    wh = comp[0].get('warehouse_id') if comp else None
    print(f"    [{'OK' if wh else 'FALTA'}] res.company(FB).warehouse_id = {wh}")
    print("  POR-PICKING (setar na remessa antes de liberar):")
    inc = o.read('account.incoterms', [INCOTERM_OK], ['code', 'name'])
    print(f"    [setar] stock.picking.incoterm = {INCOTERM_OK} {inc[0] if inc else ''}  (campo 'incoterm', NAO 'incoterm_id')")
    try:
        car = o.read('delivery.carrier', [CARRIER_OK], ['name'])
        print(f"    [{'OK' if car else 'FALTA'}] stock.picking.carrier_id = {CARRIER_OK} {car[0]['name'] if car else '(nao encontrado!)'}")
    except Exception as e:
        print(f"    [?] carrier {CARRIER_OK}: {e}")
    op5901, cfop5901, nf_ref = resolve_op_5901(o)
    print(f"    [{'OK' if op5901 else 'FALTA'}] operacao+CFOP 5901 na linha = op {op5901} / cfop {cfop5901}  (ref remessa real {nf_ref})")
    print(f"  GATE: action_liberar_faturamento SO apos picking validado + op/CFOP 5901 != False na(s) linha(s).")
    print(f"        -> robo CIEL IT cria a NF em ~90s -> conferir 5901 -> (so com GO) transmitir SEFAZ [IRREVERSIVEL]")

    # ---- rastro 29/05 -> reaproveitar vs nova
    sec("RASTRO 29/05 — reaproveitar vs criar NOVA")
    pk = o.read('stock.picking', [322049], ['name', 'state', 'picking_type_id'])
    mv = o.read('account.move', [725676], ['name', 'state', 'amount_untaxed'])
    print(f"  picking 322049 = {pk[0] if pk else '?'}")
    print(f"  NF 725676 = {mv[0] if mv else '?'}  (era 10 caixas; reversao via FB/DEV/00658)")
    dev = o.search_read('stock.picking', [('origin', 'ilike', 'Devolução de FB/SAI/IND/01606')],
                        ['name', 'state', 'location_id', 'location_dest_id'], limit=5)
    print(f"  devolucao 26489->8: {[(d['name'], d['state']) for d in dev]}")
    print(f"  >>> RECOMENDACAO: NF SEFAZ cancelada NAO se reabre; picking done + NF cancel + devolucao feita = criar REMESSA NOVA.")

    print("\n" + "=" * 100 + "\nFIM PREVIEW (nada escrito)\n" + "=" * 100)


if __name__ == '__main__':
    main()
