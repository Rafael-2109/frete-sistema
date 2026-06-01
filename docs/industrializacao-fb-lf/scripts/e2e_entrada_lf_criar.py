#!/usr/bin/env python3
"""
PASSO C — ENTRADA LF da NF da FB (caminho A / FLUXO L3 1.2.1) — Model A. DRY-RUN-FIRST.

Model A (Rafael 2026-06-01): a entrada DRENA o transito 26489 -> 31092 (terceiros LF).
O companheiro nativo "Transferir TERCEIROS" (26489->30720) e' CANCELADO antes.

Compoe os atomos MATURADOS (nao reimplementa logica Odoo):
  - Skill 7 EscrituracaoLfService: escriturar_dfe, gerar_po_from_dfe, preencher_po,
    confirmar_po, criar_invoice_from_po, buscar_dfe
  - Skill 5 StockPickingService: preencher_lotes_picking, validar
  + override L2 (src=26489 / dst=31092) no picking nativo gerado via DFe->PO.

5 gates (cada um exige inspecao do anterior):
  (default DRY-RUN)        buscar_dfe + plano completo + escriturar_dfe(dry). NAO escreve.
  --modo cancelar-comp     cancela o companheiro 322400 (libera 26489). REVERSIVEL.
  --modo escriturar        escriturar_dfe -> gerar_po -> preencher_po(pt64) -> confirmar_po.
                           PARA e reporta o picking REAL (src/dst) — ponto de inspecao A1.
  --modo finalizar --picking <id>
                           override L2 (26489->31092) + preencher_lotes(PILOTO-3105) +
                           validar. button_validate = ponto fisico (interno, sem SEFAZ).
  --modo nf --po <id>      criar_invoice_from_po (draft ENTIN). NAO posta (inspecao contabil).
  --modo post --invoice <id>
                           account.move.action_post (lanca a ENTIN). REVERSIVEL (estorno).

Validar ao fim: e2e_piloto_validar.py --modo entrada-lf --picking <id> --nf <entin> --lote PILOTO-3105
"""
import argparse
import sys
import time
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CHAVE = '35260661724241000178550010000946041007356795'
NF_SAIDA = 735679           # account.move out_invoice (RPI/2026/00245)
REMESSA_PICKING = 322399    # FB/SAI/IND/01612 (tem picking_terceiro_id = companheiro)
COMPANY_FB, COMPANY_LF = 1, 5
LOTE = 'PILOTO-3105'
LOC_TRANSITO, LOC_TERCEIROS = 26489, 31092   # 26489 -> 31092 (Model A)
PT_RECEB_IND = 19           # LF/IN (src=Vendors->42); pt64 (src=26489 transito) NAO gera picking de compra.
                            # Picking gera Vendors->42; override L2 no 'finalizar' reescreve p/ 26489->31092.
LOC_VENDORS = 4             # Parceiros/Fornecedores (origem do receipt no Model B)
TIPO_DFE, TIPO_PO = 'serv-industrializacao', 'serv-industrializacao'  # canary 42868 usou serv-industr no DFe (escriturar_dfe rejeita 'compra')
TEAM_ID, PAYMENT_TERM, PAYMENT_PROVIDER = 143, 2791, 38

# 16 componentes da remessa (mesma lista do e2e_piloto_validar)
COMPS = ['207210014', '208000008', '208000010', '210030010', '210030110', '210030203',
         '210030322', '104000004', '104000007', '104000015', '104000018', '104000002',
         '105000023', '105000024', '105000039', '105000022']


def ctx_lf():
    # multi-company [1,5]: a NF/DFe/PO sao company LF=5, mas os lotes PILOTO-3105
    # foram criados na remessa em company FB=1 -> button_validate precisa le-los.
    return {'allowed_company_ids': [COMPANY_FB, COMPANY_LF], 'company_id': COMPANY_LF}


def ctx_fb():
    # companheiro "Transferir TERCEIROS" e' picking da FB (company=1)
    return {'allowed_company_ids': [COMPANY_FB, COMPANY_LF], 'company_id': COMPANY_FB}


def sec(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


def resolver_dfe(o):
    r = o.search_read('l10n_br_ciel_it_account.dfe',
                      [('protnfe_infnfe_chnfe', '=', CHAVE), ('company_id', '=', COMPANY_LF)],
                      ['id', 'l10n_br_situacao_dfe', 'purchase_id', 'nfe_infnfe_ide_nnf'], limit=1)
    return r[0] if r else None


def resolver_companheiro(o):
    pk = o.read('stock.picking', [REMESSA_PICKING], ['picking_terceiro_id'])
    c = pk[0].get('picking_terceiro_id') if pk else None
    return c[0] if c else None


def quants_transito(o):
    """16 quants do lote PILOTO-3105 em 26489 -> lotes_data + lote_id por produto."""
    lots = o.search_read('stock.lot', [('name', 'ilike', LOTE)], ['id', 'product_id'], limit=60)
    lot_ids = [l['id'] for l in lots]
    qs = o.search_read('stock.quant',
                       [('location_id', '=', LOC_TRANSITO), ('lot_id', 'in', lot_ids), ('quantity', '!=', 0)],
                       ['product_id', 'lot_id', 'quantity'], limit=80)
    out = []
    for q in qs:
        out.append({'product_id': q['product_id'][0], 'cod': '', 'nome': q['product_id'][1][:30],
                    'lot_id': q['lot_id'][0] if q['lot_id'] else None,
                    'lote_nome': q['lot_id'][1] if q['lot_id'] else LOTE,
                    'quantidade': q['quantity']})
    # resolver cod
    pmap = {p['id']: p['default_code'] for p in o.search_read(
        'product.product', [('id', 'in', [x['product_id'] for x in out])], ['default_code'])}
    for x in out:
        x['cod'] = pmap.get(x['product_id'], '?')
    return out


# ---------------------------------------------------------------- L2 override
def override_l2(o, picking_id):
    """Forca picking + moves + move.lines para src=26489 / dst=31092 (Model A)."""
    o.execute_kw('stock.picking', 'write',
                 [[picking_id], {'location_id': LOC_TRANSITO, 'location_dest_id': LOC_TERCEIROS}],
                 {'context': ctx_lf()})
    mvs = o.search_read('stock.move', [('picking_id', '=', picking_id)], ['id'], limit=80)
    if mvs:
        o.execute_kw('stock.move', 'write',
                     [[m['id'] for m in mvs], {'location_id': LOC_TRANSITO, 'location_dest_id': LOC_TERCEIROS}],
                     {'context': ctx_lf()})
    mls = o.search_read('stock.move.line', [('picking_id', '=', picking_id)], ['id'], limit=120)
    if mls:
        o.execute_kw('stock.move.line', 'write',
                     [[m['id'] for m in mls], {'location_id': LOC_TRANSITO, 'location_dest_id': LOC_TERCEIROS}],
                     {'context': ctx_lf()})
    return len(mvs), len(mls)


def show_picking(o, picking_id, label='picking'):
    p = o.execute_kw('stock.picking', 'read', [[picking_id], ['name', 'state', 'location_id', 'location_dest_id', 'picking_type_id']], {'context': ctx_lf()})[0]
    print(f"  {label} {picking_id}: {p['name']} state={p['state']} SRC={p['location_id']} DST={p['location_dest_id']} pt={p['picking_type_id']}")
    for m in o.execute_kw('stock.move', 'search_read', [[('picking_id', '=', picking_id)], ['product_id', 'location_id', 'location_dest_id', 'product_qty', 'state']], {'context': ctx_lf(), 'limit': 20}):
        print(f"      move {m['product_id'][1][:24]:24} {m['location_id'][0]}->{m['location_dest_id'][0]} qty={m['product_qty']} ({m['state']})")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--modo', default='dry-run',
                    choices=['dry-run', 'cancelar-comp', 'completar-dfe', 'limpar-po', 'escriturar', 'compartilhar-lotes', 'criar-picking', 'criar-picking-b1', 'validar-picking', 'finalizar', 'nf', 'post'])
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--picking', type=int)
    ap.add_argument('--po', type=int)
    ap.add_argument('--invoice', type=int)
    args = ap.parse_args()
    o = get_odoo_connection(); o.authenticate()

    from app.odoo.estoque.scripts.escrituracao import EscrituracaoLfService
    from app.odoo.estoque.scripts.picking import StockPickingService
    escr = EscrituracaoLfService(odoo=o)
    pick = StockPickingService(odoo=o)

    # =================================================================== DRY-RUN (plano)
    if args.modo == 'dry-run':
        sec("PASSO C — ENTRADA LF (Model A: 26489 -> 31092) — DRY-RUN (nada escrito)")
        dfe = resolver_dfe(o)
        if not dfe:
            print("  [ABORT] DFe da chave nao encontrado no LF."); return 1
        print(f"  DFe: id={dfe['id']} nnf={dfe['nfe_infnfe_ide_nnf']} situacao={dfe['l10n_br_situacao_dfe']} purchase_id={dfe['purchase_id']}")
        bd = escr.buscar_dfe(chave_nfe=CHAVE, company_id=COMPANY_LF)
        print(f"  buscar_dfe -> encontrado={bd['encontrado']} status={bd['status']} (esperado pendente=caminho A)")
        comp = resolver_companheiro(o)
        if comp:
            c = o.read('stock.picking', [comp], ['name', 'state', 'location_dest_id'])[0]
            print(f"  COMPANHEIRO a CANCELAR: {comp} {c['name']} state={c['state']} dst={c['location_dest_id']}")
        qd = quants_transito(o)
        print(f"\n  lotes_data ({len(qd)} produtos em 26489, lote {LOTE}):")
        for x in sorted(qd, key=lambda y: y['cod']):
            print(f"    {x['cod']:>12} {x['nome']:<30} qty={x['quantidade']:>10}")
        print(f"\n  SEQUENCIA (Model A):")
        print(f"    1. cancelar-comp : cancela {comp} -> libera 26489")
        print(f"    2. escriturar    : escriturar_dfe(dfe={dfe['id']}, tipo='{TIPO_DFE}')")
        print(f"                       gerar_po_from_dfe -> preencher_po(pt={PT_RECEB_IND}, team={TEAM_ID}, "
              f"pterm={PAYMENT_TERM}, prov={PAYMENT_PROVIDER}, tipo_po='{TIPO_PO}') -> confirmar_po")
        print(f"    3. finalizar     : override L2 (src={LOC_TRANSITO}/dst={LOC_TERCEIROS}) + preencher_lotes({LOTE}) + validar")
        print(f"    4. nf            : criar_invoice_from_po (draft ENTIN)")
        print(f"    5. post          : action_post (ENTIN)")
        print(f"\n  CONTABIL esperado (cadeia do piloto):")
        print(f"    SVL   : D 1150200001 (terceiros) / C 1150100011  (Design A, via L1 vivo na categ 193)")
        print(f"    ENTIN : D 1150100011 / C 5101020001 (PASSIVA) cfop 1901")
        print(f"    NET   : D 1150200001 / C 5101020001  => Delta 1150100011(LF) = 0")
        print(f"    FISICO: 26489 (lote) -> 0 ; material em 31092")
        # escriturar_dfe em dry-run (sobre o DFe real, sem escrever)
        ed = escr.escriturar_dfe(dfe_id=dfe['id'], l10n_br_tipo_pedido=TIPO_DFE, dry_run=True)
        print(f"\n  escriturar_dfe(dry_run) -> status={ed['status']} tipo={ed.get('l10n_br_tipo_pedido')}")
        print("\n  DRY-RUN ok. Proximo: --modo cancelar-comp --execute")
        return 0

    # =================================================================== gate 1: cancelar companheiro
    if args.modo == 'cancelar-comp':
        sec("GATE 1 — cancelar companheiro (Transferir TERCEIROS) — libera 26489")
        comp = resolver_companheiro(o)
        if not comp:
            print("  [info] sem companheiro (picking_terceiro_id vazio). Nada a cancelar."); return 0
        c = o.execute_kw('stock.picking', 'read', [[comp], ['name', 'state']], {'context': ctx_fb()})[0]
        print(f"  companheiro {comp} {c['name']} state={c['state']} (picking FB company=1)")
        if c['state'] == 'cancel':
            print("  ja cancelado."); return 0
        if not args.execute:
            print("  DRY: rode com --execute para cancelar."); return 0
        o.execute_kw('stock.picking', 'action_cancel', [[comp]], {'context': ctx_fb()})
        st = o.execute_kw('stock.picking', 'read', [[comp], ['state']], {'context': ctx_fb()})[0]['state']
        nq = o.search_read('stock.quant', [('location_id', '=', LOC_TRANSITO),
              ('lot_id', 'in', [l['id'] for l in o.search_read('stock.lot', [('name', 'ilike', LOTE)], ['id'])]),
              ('quantity', '!=', 0)], ['quantity'])
        print(f"  [OK] companheiro state={st}; 26489 mantem {sum(q['quantity'] for q in nq):.4f} un do lote {LOTE}")
        print("  Proximo: --modo escriturar --execute")
        return 0

    # =================================================================== recuperacao: completar DFe resumo (sem linhas)
    if args.modo == 'completar-dfe':
        sec("RECUPERACAO — completar DFe (resumo SEFAZ sem linhas) com XML da NF de saida")
        dfe = resolver_dfe(o)
        if not dfe:
            print("  [ABORT] DFe nao encontrado."); return 1
        dfe_id = dfe['id']
        d = o.execute_kw('l10n_br_ciel_it_account.dfe', 'read',
                         [[dfe_id], ['l10n_br_status', 'purchase_fiscal_id', 'purchase_id']],
                         {'context': ctx_lf()})[0]
        nlines = o.execute_kw('l10n_br_ciel_it_account.dfe.line', 'search_count',
                              [[('dfe_id', '=', dfe_id)]], {'context': ctx_lf()})
        print(f"  DFe {dfe_id}: linhas={nlines} status={d.get('l10n_br_status')} "
              f"purchase_fiscal_id={d.get('purchase_fiscal_id')} purchase_id={d.get('purchase_id')}")
        if not args.execute:
            print("  DRY: rode com --execute para completar."); return 0
        # 1. cancelar PO vazia vinculada (so se vazia) + limpar vinculos DFe->PO
        pfid = d.get('purchase_fiscal_id')
        if pfid:
            po_vazia = pfid[0]
            po = o.execute_kw('purchase.order', 'read', [[po_vazia], ['state', 'order_line']], {'context': ctx_lf()})[0]
            if po.get('order_line'):
                print(f"  [ABORT] PO {po_vazia} tem linhas — NAO e' a PO vazia. Verifique manualmente."); return 1
            if po['state'] != 'cancel':
                o.execute_kw('purchase.order', 'button_cancel', [[po_vazia]], {'context': ctx_lf()})
                print(f"  PO vazia {po_vazia} cancelada (button_cancel)")
            o.execute_kw('l10n_br_ciel_it_account.dfe', 'write', [[dfe_id], {'purchase_fiscal_id': False}], {'context': ctx_lf()})
            print(f"  dfe.purchase_fiscal_id limpo")
        # 2. escrever XML autorizado da NF de saida no DFe
        inv = o.read('account.move', [NF_SAIDA], ['l10n_br_xml_aut_nfe'])[0]
        xml = inv.get('l10n_br_xml_aut_nfe')
        if not xml:
            print("  [ABORT] NF de saida sem l10n_br_xml_aut_nfe."); return 1
        o.execute_kw('l10n_br_ciel_it_account.dfe', 'write', [[dfe_id], {'l10n_br_xml_dfe': xml}], {'context': ctx_lf()})
        print(f"  XML autorizado escrito no DFe ({len(xml)} chars). Processando...")
        # 3. action_processar_arquivo_manual + poll por linhas
        o.execute_kw('l10n_br_ciel_it_account.dfe', 'action_processar_arquivo_manual', [[dfe_id]], {'context': ctx_lf()})
        nlines = 0
        for _ in range(40):
            time.sleep(3)
            nlines = o.execute_kw('l10n_br_ciel_it_account.dfe.line', 'search_count',
                                  [[('dfe_id', '=', dfe_id)]], {'context': ctx_lf()})
            if nlines > 0:
                break
        print(f"  processado -> {nlines} dfe.lines")
        if nlines == 0:
            print("  [FALHA] DFe continua sem linhas apos processar."); return 1
        # 4. alinhar company das linhas (B-V23-1 / F2a)
        al = escr.alinhar_dfe_lines_company(dfe_id=dfe_id, company_destino=COMPANY_LF)
        print(f"  alinhar_dfe_lines_company -> {al.get('status')} corrigidas={len(al.get('lines_corrigidas') or [])} {al.get('erro') or ''}")
        print(f"\n  [OK] DFe {dfe_id} completo com {nlines} linhas. Proximo: --modo escriturar --execute")
        return 0

    # =================================================================== limpar PO (cancelar + soltar vinculo DFe) p/ regenerar
    if args.modo == 'limpar-po':
        sec("LIMPAR-PO — cancela a PO + solta vinculo DFe (p/ regenerar com pt correto)")
        if not args.po:
            print("  [ABORT] --limpar-po exige --po <id>"); return 1
        po = o.execute_kw('purchase.order', 'read', [[args.po], ['name', 'state', 'order_line', 'picking_ids']], {'context': ctx_lf()})[0]
        print(f"  PO {args.po}: {po['name']} state={po['state']} linhas={len(po['order_line'] or [])} pickings={po['picking_ids']}")
        if po['picking_ids']:
            print(f"  [ABORT] PO ja tem picking {po['picking_ids']} — NAO limpar (use finalizar)."); return 1
        if not args.execute:
            print("  DRY: rode com --execute."); return 0
        if po['state'] != 'cancel':
            o.execute_kw('purchase.order', 'button_cancel', [[args.po]], {'context': ctx_lf()})
            print(f"  PO {args.po} cancelada")
        dfe = resolver_dfe(o)
        if dfe:
            d = o.execute_kw('l10n_br_ciel_it_account.dfe', 'read', [[dfe['id']], ['purchase_fiscal_id', 'purchase_id']], {'context': ctx_lf()})[0]
            vals = {}
            if d.get('purchase_fiscal_id') and d['purchase_fiscal_id'][0] == args.po:
                vals['purchase_fiscal_id'] = False
            if d.get('purchase_id') and d['purchase_id'][0] == args.po:
                vals['purchase_id'] = False
            if vals:
                o.execute_kw('l10n_br_ciel_it_account.dfe', 'write', [[dfe['id']], vals], {'context': ctx_lf()})
                print(f"  dfe {dfe['id']} vinculos limpos: {list(vals.keys())}")
        print(f"  [OK] Proximo: --modo escriturar --execute (regera PO com pt{PT_RECEB_IND})")
        return 0

    # =================================================================== gate 2: escriturar -> PO -> confirmar
    if args.modo == 'escriturar':
        sec("GATE 2 — escriturar_dfe -> gerar_po -> preencher_po(pt64) -> confirmar_po")
        dfe = resolver_dfe(o)
        if not dfe:
            print("  [ABORT] DFe nao encontrado."); return 1
        if not args.execute:
            print("  DRY: rode com --execute."); return 0
        ed = escr.escriturar_dfe(dfe_id=dfe['id'], l10n_br_tipo_pedido=TIPO_DFE, dry_run=False)
        print(f"  escriturar_dfe -> {ed['status']} {ed.get('erro') or ''}")
        if ed['status'] not in ('ESCRITURADO', 'DRY_RUN_OK', 'IDEMPOTENT_ESCRITURADO'):
            print("  [ABORT] escriturar_dfe falhou."); return 1
        gp = escr.gerar_po_from_dfe(dfe_id=dfe['id'], dry_run=False)
        print(f"  gerar_po_from_dfe -> {gp['status']} po_id={gp.get('po_id')} {gp.get('erro') or ''}")
        po_id = gp.get('po_id')
        if not po_id:
            print("  [ABORT] sem po_id (robo CIEL IT nao materializou — reexecute mais tarde)."); return 1
        pp = escr.preencher_po(po_id=po_id, team_id=TEAM_ID, payment_term_id=PAYMENT_TERM,
                               picking_type_id=PT_RECEB_IND, company_id=COMPANY_LF,
                               payment_provider_id=PAYMENT_PROVIDER, l10n_br_tipo_pedido=TIPO_PO, dry_run=False)
        print(f"  preencher_po -> {pp['status']} {pp.get('erro') or ''}")
        cf = escr.confirmar_po(po_id=po_id, dry_run=False)
        print(f"  confirmar_po -> {cf['status']} state_final={cf.get('state_final')} {cf.get('erro') or ''}")
        pks = o.execute_kw('purchase.order', 'read', [[po_id], ['picking_ids']], {'context': ctx_lf()})[0]['picking_ids']
        print(f"\n  >>> INSPECAO A1 — picking(s) gerado(s): {pks}")
        for pid in (pks or []):
            show_picking(o, pid)
        print(f"\n  Confira o SRC acima. Proximo: --modo finalizar --picking <id> --execute")
        return 0

    # =================================================================== A': criar picking 26489->31092 vinculado a PO + lotes + validar
    if args.modo == 'criar-picking':
        sec("CRIAR-PICKING (A') — picking 26489->31092 vinculado a PO + lote + validar")
        if not args.po:
            print("  [ABORT] --criar-picking exige --po <id>"); return 1
        po = o.execute_kw('purchase.order', 'read', [[args.po], ['name', 'state', 'partner_id', 'order_line', 'picking_ids']], {'context': ctx_lf()})[0]
        print(f"  PO {po['name']} state={po['state']} pickings={po['picking_ids']}")
        if po['picking_ids']:
            print(f"  [ABORT] PO ja tem picking {po['picking_ids']} — use finalizar."); return 1
        lines = o.execute_kw('purchase.order.line', 'read', [po['order_line'], ['product_id', 'product_qty', 'product_uom']], {'context': ctx_lf()})
        qmap = {x['product_id']: x for x in quants_transito(o)}
        plano = []
        for l in lines:
            pid = l['product_id'][0]
            q = qmap.get(pid)
            if not q:
                print(f"    *** {l['product_id'][1][:30]} SEM saldo em 26489 lote {LOTE}"); continue
            plano.append({'line': l['id'], 'pid': pid, 'nome': l['product_id'][1][:28],
                          'qty': min(l['product_qty'], q['quantidade']), 'uom': l['product_uom'][0], 'lot_id': q['lot_id']})
        print(f"\n  picking pt{PT_RECEB_IND} {LOC_TRANSITO}->{LOC_TERCEIROS}; {len(plano)}/{len(lines)} moves (purchase_line_id vinculado):")
        for m in plano:
            print(f"    {m['nome']:28} qty={m['qty']:>10} lote={LOTE} (PO line {m['line']})")
        if len(plano) != len(lines):
            print(f"  [ABORT] {len(lines)-len(plano)} linha(s) sem saldo em 26489."); return 1
        if not args.execute:
            print(f"\n  DRY-RUN: nada criado. --execute cria picking + move.lines (lote pinado) + valida.")
            print(f"  Efeito: 26489 drena -> 31092; SVL D 1150200001/C 1150100011; qty_received atualiza p/ ENTIN.")
            return 0
        move_vals = [(0, 0, {'name': f"ENT-PILOTO {m['pid']}", 'product_id': m['pid'], 'product_uom_qty': m['qty'],
                             'product_uom': m['uom'], 'location_id': LOC_TRANSITO, 'location_dest_id': LOC_TERCEIROS,
                             'company_id': COMPANY_LF, 'purchase_line_id': m['line']}) for m in plano]
        pk_id = o.execute_kw('stock.picking', 'create', [{'picking_type_id': PT_RECEB_IND, 'location_id': LOC_TRANSITO,
                             'location_dest_id': LOC_TERCEIROS, 'company_id': COMPANY_LF, 'partner_id': po['partner_id'][0],
                             'origin': po['name'], 'move_ids_without_package': move_vals}], {'context': ctx_lf()})
        print(f"\n  [criado] picking id={pk_id}")
        smoves = o.execute_kw('stock.move', 'search_read', [[('picking_id', '=', pk_id)], ['id', 'product_id', 'product_uom']], {'context': ctx_lf(), 'limit': 40})
        o.execute_kw('stock.move', 'write', [[m['id'] for m in smoves], {'company_id': COMPANY_LF}], {'context': ctx_lf()})
        o.execute_kw('stock.picking', 'action_confirm', [[pk_id]], {'context': ctx_lf()})
        for sm in smoves:
            m = next((x for x in plano if x['pid'] == (sm['product_id'][0] if sm['product_id'] else None)), None)
            if not m:
                continue
            ml = o.execute_kw('stock.move.line', 'create', [{'move_id': sm['id'], 'picking_id': pk_id, 'product_id': m['pid'],
                              'product_uom_id': sm['product_uom'][0] if sm['product_uom'] else m['uom'],
                              'location_id': LOC_TRANSITO, 'location_dest_id': LOC_TERCEIROS,
                              'lot_id': m['lot_id'], 'company_id': COMPANY_LF}], {'context': ctx_lf()})
            try:
                o.execute_kw('stock.move.line', 'write', [[ml], {'quantity': m['qty'], 'qty_done': m['qty']}], {'context': ctx_lf()})
            except Exception:
                o.execute_kw('stock.move.line', 'write', [[ml], {'quantity': m['qty']}], {'context': ctx_lf()})
        print(f"  {len(smoves)} move.lines com lote {LOTE} pinado")
        try:
            o.execute_kw('stock.picking', 'button_validate', [[pk_id]], {'context': dict(ctx_lf(), skip_backorder=True, picking_ids_not_to_backorder=[pk_id])})
        except Exception as e:
            if 'cannot marshal None' not in str(e):
                print(f"  [aviso button_validate] {e}")
        show_picking(o, pk_id, 'DEPOIS')
        qr = o.execute_kw('purchase.order.line', 'read', [po['order_line'][:1], ['qty_received']], {'context': ctx_lf()})
        print(f"  qty_received (linha 1) = {qr[0].get('qty_received')}")
        print(f"  Proximo: --modo nf --po {args.po} --execute")
        return 0

    # =================================================================== B1 (Model B): receipt Vendors->31092 c/ lotes LF
    if args.modo == 'criar-picking-b1':
        sec("CRIAR-PICKING-B1 (Model B) — cancela Model-A + receipt Vendors->31092 c/ lotes LF + validar")
        if not args.po:
            print("  [ABORT] exige --po <id>"); return 1
        po = o.execute_kw('purchase.order', 'read', [[args.po], ['name', 'state', 'partner_id', 'order_line', 'picking_ids']], {'context': ctx_lf()})[0]
        lines = o.execute_kw('purchase.order.line', 'read', [po['order_line'], ['product_id', 'product_qty', 'product_uom']], {'context': ctx_lf()})
        print(f"  PO {po['name']}: {len(lines)} linhas; receipt {LOC_VENDORS}(Vendors)->{LOC_TERCEIROS}(31092) c/ lotes LF novos")
        # picking(s) Model-A a cancelar
        cancelar = []
        for pid in (po['picking_ids'] or []):
            pst = o.execute_kw('stock.picking', 'read', [[pid], ['state']], {'context': ctx_lf()})[0]['state']
            if pst not in ('done', 'cancel'):
                cancelar.append(pid)
        print(f"  picking(s) Model-A a cancelar: {cancelar}")
        if not args.execute:
            for l in lines:
                print(f"    {l['product_id'][1][:28]:28} qty={l['product_qty']} lote=LF:{LOTE}")
            print(f"\n  DRY: cancelaria {cancelar} + criaria lotes LF + picking Vendors->31092 + validaria.")
            print(f"  Efeito: material FRESCO em 31092 (lotes LF); SVL D 1150200001/C 1150100011; qty_received -> ENTIN.")
            print(f"  (26489 fica c/ estoque FB — drena depois via companheiro/Skill, fora deste passo.)")
            return 0
        # 1. cancelar Model-A
        for pid in cancelar:
            o.execute_kw('stock.picking', 'action_cancel', [[pid]], {'context': ctx_lf()})
            print(f"  picking Model-A {pid} cancelado")
        # 2. criar/resolver lotes LF (company 5)
        lotmap = {}
        for l in lines:
            pid = l['product_id'][0]
            ex = o.execute_kw('stock.lot', 'search_read', [[('name', '=', LOTE), ('product_id', '=', pid), ('company_id', '=', COMPANY_LF)], ['id']], {'context': ctx_lf()})
            lotmap[pid] = ex[0]['id'] if ex else o.execute_kw('stock.lot', 'create', [{'name': LOTE, 'product_id': pid, 'company_id': COMPANY_LF}], {'context': ctx_lf()})
        print(f"  {len(lotmap)} lotes LF {LOTE} resolvidos/criados")
        # 3. criar picking Vendors->31092 c/ moves vinculados a PO
        move_vals = [(0, 0, {'name': f"ENT-B1 {l['product_id'][0]}", 'product_id': l['product_id'][0], 'product_uom_qty': l['product_qty'],
                             'product_uom': l['product_uom'][0], 'location_id': LOC_VENDORS, 'location_dest_id': LOC_TERCEIROS,
                             'company_id': COMPANY_LF, 'purchase_line_id': l['id']}) for l in lines]
        pk_id = o.execute_kw('stock.picking', 'create', [{'picking_type_id': PT_RECEB_IND, 'location_id': LOC_VENDORS,
                             'location_dest_id': LOC_TERCEIROS, 'company_id': COMPANY_LF, 'partner_id': po['partner_id'][0],
                             'origin': po['name'], 'move_ids_without_package': move_vals}], {'context': ctx_lf()})
        print(f"  [criado] picking id={pk_id}")
        o.execute_kw('stock.picking', 'action_confirm', [[pk_id]], {'context': ctx_lf()})
        smoves = o.execute_kw('stock.move', 'search_read', [[('picking_id', '=', pk_id)], ['id', 'product_id', 'product_uom', 'product_uom_qty']], {'context': ctx_lf(), 'limit': 40})
        # limpar move.lines auto-criadas (se houver) e criar com lote LF
        existing_mls = o.execute_kw('stock.move.line', 'search', [[('picking_id', '=', pk_id)]], {'context': ctx_lf()})
        if existing_mls:
            o.execute_kw('stock.move.line', 'unlink', [existing_mls], {'context': ctx_lf()})
        for sm in smoves:
            pid = sm['product_id'][0]
            ml = o.execute_kw('stock.move.line', 'create', [{'move_id': sm['id'], 'picking_id': pk_id, 'product_id': pid,
                              'product_uom_id': sm['product_uom'][0], 'location_id': LOC_VENDORS, 'location_dest_id': LOC_TERCEIROS,
                              'lot_id': lotmap[pid], 'company_id': COMPANY_LF}], {'context': ctx_lf()})
            try:
                o.execute_kw('stock.move.line', 'write', [[ml], {'quantity': sm['product_uom_qty'], 'qty_done': sm['product_uom_qty']}], {'context': ctx_lf()})
            except Exception:
                o.execute_kw('stock.move.line', 'write', [[ml], {'quantity': sm['product_uom_qty']}], {'context': ctx_lf()})
        print(f"  {len(smoves)} move.lines com lote LF {LOTE}")
        try:
            o.execute_kw('stock.picking', 'button_validate', [[pk_id]], {'context': dict(ctx_lf(), skip_backorder=True, picking_ids_not_to_backorder=[pk_id])})
        except Exception as e:
            if 'cannot marshal None' not in str(e):
                print(f"  [aviso button_validate] {e}")
        show_picking(o, pk_id, 'DEPOIS')
        st = o.execute_kw('stock.picking', 'read', [[pk_id], ['state']], {'context': ctx_lf()})[0]['state']
        qr = o.execute_kw('purchase.order.line', 'read', [po['order_line'][:1], ['qty_received']], {'context': ctx_lf()})
        print(f"  state={st}  qty_received(linha1)={qr[0].get('qty_received')}")
        print(f"  Proximo: --modo nf --po {args.po} --execute")
        return 0

    # =================================================================== tornar lotes PILOTO compartilhados (inter-company)
    if args.modo == 'compartilhar-lotes':
        sec("COMPARTILHAR-LOTES — company_id=False nos lotes PILOTO-3105 (p/ LF consumir trânsito FB)")
        lots = o.execute_kw('stock.lot', 'search_read', [[('name', 'ilike', LOTE)], ['id', 'name', 'company_id', 'product_id']],
                            {'context': dict(ctx_lf(), allowed_company_ids=[COMPANY_FB, COMPANY_LF]), 'limit': 60})
        fb_lots = [l for l in lots if l['company_id'] and l['company_id'][0] != False]
        print(f"  {len(lots)} lotes {LOTE}; {len(fb_lots)} com company setada:")
        for l in lots[:20]:
            print(f"    lot {l['id']} cmp={l['company_id']} prod={l['product_id'][1][:26] if l['product_id'] else '?'}")
        if not args.execute:
            print(f"\n  DRY: tornaria {len(fb_lots)} lotes company_id=False (compartilhado). Reversível.")
            return 0
        if fb_lots:
            o.execute_kw('stock.lot', 'write', [[l['id'] for l in fb_lots], {'company_id': False}],
                         {'context': dict(ctx_lf(), allowed_company_ids=[COMPANY_FB, COMPANY_LF])})
            print(f"  {len(fb_lots)} lotes -> company_id=False (compartilhado)")
        print(f"  Proximo: --modo validar-picking --picking <id> --execute")
        return 0

    # =================================================================== B1 (Model B): receipt Vendors->31092 c/ lotes LF
    if args.modo == 'criar-picking-b1':
        sec("CRIAR-PICKING-B1 (Model B) — receipt Vendors->31092 c/ lotes LF + validar")
        if not args.po:
            print("  [ABORT] exige --po <id>"); return 1
        po = o.execute_kw('purchase.order', 'read', [[args.po], ['name', 'state', 'partner_id', 'order_line', 'picking_ids']], {'context': ctx_lf()})[0]
        lines = o.execute_kw('purchase.order.line', 'read', [po['order_line'], ['product_id', 'product_qty', 'product_uom']], {'context': ctx_lf()})
        print(f"  PO {po['name']}: {len(lines)} linhas; receipt loc{LOC_VENDORS}->loc{LOC_TERCEIROS} c/ lotes LF {LOTE}")
        # pickings Model-A a cancelar
        cancelar = []
        for pid in (po['picking_ids'] or []):
            pst = o.execute_kw('stock.picking', 'read', [[pid], ['state']], {'context': ctx_lf()})[0]['state']
            if pst not in ('done', 'cancel'):
                cancelar.append(pid)
        if cancelar:
            print(f"  pickings Model-A a cancelar: {cancelar}")
        if not args.execute:
            for l in lines:
                print(f"    {l['product_id'][1][:28]:28} qty={l['product_qty']}")
            print(f"  DRY: cancelaria {cancelar}, criaria 16 lotes LF + picking {LOC_VENDORS}->{LOC_TERCEIROS} + validaria.")
            return 0
        for pid in cancelar:
            o.execute_kw('stock.picking', 'action_cancel', [[pid]], {'context': ctx_lf()})
            print(f"  picking Model-A {pid} cancelado")
        # lotes LF (company 5) — criar/resolver
        lotmap = {}
        for l in lines:
            pid = l['product_id'][0]
            ex = o.execute_kw('stock.lot', 'search_read', [[('name', '=', LOTE), ('product_id', '=', pid), ('company_id', '=', COMPANY_LF)], ['id']], {'context': ctx_lf()})
            lotmap[pid] = ex[0]['id'] if ex else o.execute_kw('stock.lot', 'create', [{'name': LOTE, 'product_id': pid, 'company_id': COMPANY_LF}], {'context': ctx_lf()})
        print(f"  {len(lotmap)} lotes LF {LOTE} resolvidos")
        move_vals = [(0, 0, {'name': f"ENT-B1 {l['product_id'][0]}", 'product_id': l['product_id'][0], 'product_uom_qty': l['product_qty'],
                             'product_uom': l['product_uom'][0], 'location_id': LOC_VENDORS, 'location_dest_id': LOC_TERCEIROS,
                             'company_id': COMPANY_LF, 'purchase_line_id': l['id']}) for l in lines]
        pk_id = o.execute_kw('stock.picking', 'create', [{'picking_type_id': PT_RECEB_IND, 'location_id': LOC_VENDORS,
                            'location_dest_id': LOC_TERCEIROS, 'company_id': COMPANY_LF, 'partner_id': po['partner_id'][0],
                            'origin': po['name'], 'move_ids_without_package': move_vals}], {'context': ctx_lf()})
        print(f"  [criado] picking id={pk_id}")
        o.execute_kw('stock.picking', 'action_confirm', [[pk_id]], {'context': ctx_lf()})
        smoves = o.execute_kw('stock.move', 'search_read', [[('picking_id', '=', pk_id)], ['id', 'product_id', 'product_uom', 'product_uom_qty']], {'context': ctx_lf(), 'limit': 40})
        for sm in smoves:
            pid = sm['product_id'][0]
            exml = o.execute_kw('stock.move.line', 'search_read', [[('move_id', '=', sm['id'])], ['id']], {'context': ctx_lf(), 'limit': 5})
            vals = {'lot_id': lotmap[pid], 'quantity': sm['product_uom_qty'], 'qty_done': sm['product_uom_qty'],
                    'location_id': LOC_VENDORS, 'location_dest_id': LOC_TERCEIROS}
            if exml:
                try:
                    o.execute_kw('stock.move.line', 'write', [[exml[0]['id']], vals], {'context': ctx_lf()})
                except Exception:
                    o.execute_kw('stock.move.line', 'write', [[exml[0]['id']], {k: v for k, v in vals.items() if k != 'qty_done'}], {'context': ctx_lf()})
            else:
                vals.update({'move_id': sm['id'], 'picking_id': pk_id, 'product_id': pid, 'product_uom_id': sm['product_uom'][0], 'company_id': COMPANY_LF})
                try:
                    o.execute_kw('stock.move.line', 'create', [vals], {'context': ctx_lf()})
                except Exception:
                    o.execute_kw('stock.move.line', 'create', [{k: v for k, v in vals.items() if k != 'qty_done'}], {'context': ctx_lf()})
        print(f"  {len(smoves)} move.lines com lote LF")
        try:
            o.execute_kw('stock.picking', 'button_validate', [[pk_id]], {'context': dict(ctx_lf(), skip_backorder=True, picking_ids_not_to_backorder=[pk_id])})
        except Exception as e:
            if 'cannot marshal None' not in str(e):
                print(f"  [aviso button_validate] {e}")
        show_picking(o, pk_id, 'DEPOIS')
        st = o.execute_kw('stock.picking', 'read', [[pk_id], ['state']], {'context': ctx_lf()})[0]['state']
        qr = o.execute_kw('purchase.order.line', 'read', [po['order_line'][:1], ['qty_received']], {'context': ctx_lf()})
        print(f"  state={st}  qty_received(linha1)={qr[0].get('qty_received')}")
        if st != 'done':
            print("  [FALHA] picking nao ficou done."); return 1
        print(f"  [OK] Proximo: --modo nf --po {args.po} --execute")
        return 0

    # =================================================================== validar picking ja criado (ctx multi-company)
    if args.modo == 'validar-picking':
        sec("VALIDAR-PICKING — button_validate (ctx [1,5] p/ ler lotes FB)")
        if not args.picking:
            print("  [ABORT] exige --picking <id>"); return 1
        print("  ANTES:"); show_picking(o, args.picking, 'picking')
        st = o.execute_kw('stock.picking', 'read', [[args.picking], ['state']], {'context': ctx_lf()})[0]['state']
        if st == 'done':
            print("  ja done."); return 0
        if not args.execute:
            print("  DRY: rode com --execute."); return 0
        try:
            o.execute_kw('stock.picking', 'button_validate', [[args.picking]],
                         {'context': dict(ctx_lf(), skip_backorder=True, picking_ids_not_to_backorder=[args.picking])})
        except Exception as e:
            if 'cannot marshal None' not in str(e):
                print(f"  [aviso button_validate] {e}")
        st = o.execute_kw('stock.picking', 'read', [[args.picking], ['state']], {'context': ctx_lf()})[0]['state']
        print(f"  picking state={st}")
        if st != 'done':
            print(f"  [FALHA] picking nao ficou done."); return 1
        show_picking(o, args.picking, 'DEPOIS')
        # verificar 26489 zerou + 31092 + qty_received
        q26489 = quants_transito(o)
        print(f"  26489 lote {LOTE}: {len(q26489)} quants restantes (esperado 0)")
        print(f"  [OK] Proximo: --modo nf --po <id> --execute")
        return 0

    # =================================================================== gate 3: override L2 + lotes + validar
    if args.modo == 'finalizar':
        sec("GATE 3 — override L2 (26489->31092) + preencher_lotes + validar")
        if not args.picking:
            print("  [ABORT] --finalizar exige --picking <id>"); return 1
        print("  ANTES:"); show_picking(o, args.picking, 'picking')
        if not args.execute:
            print("  DRY: rode com --execute."); return 0
        nm, nl = override_l2(o, args.picking)
        print(f"  override L2 aplicado: {nm} moves, {nl} move.lines -> src={LOC_TRANSITO}/dst={LOC_TERCEIROS}")
        qd = quants_transito(o)
        lotes_data = [{'product_id': x['product_id'], 'lote_nome': LOTE, 'quantidade': x['quantidade']} for x in qd]
        pl = pick.preencher_lotes_picking(picking_id=args.picking, lotes_data=lotes_data, dry_run=False)
        print(f"  preencher_lotes_picking -> {pl['status']} atualizadas={pl.get('mls_atualizadas')} criadas={pl.get('mls_criadas')} {pl.get('erro') or ''}")
        # garantir move.lines em 26489 (apos preencher_lotes)
        override_l2(o, args.picking)
        mls = o.search_read('stock.move.line', [('picking_id', '=', args.picking)],
                            ['product_id', 'lot_id', 'lot_name', 'quantity', 'location_id', 'location_dest_id'], limit=120)
        print(f"  {len(mls)} move.lines pre-validacao:")
        bad = [m for m in mls if (m['location_id'][0] if m['location_id'] else None) != LOC_TRANSITO]
        for m in mls[:20]:
            print(f"    {m['product_id'][1][:24]:24} lote={(m['lot_id'][1] if m['lot_id'] else m['lot_name'])} "
                  f"qty={m['quantity']} loc={m['location_id'][0] if m['location_id'] else '?'}->{m['location_dest_id'][0] if m['location_dest_id'] else '?'}")
        if bad:
            print(f"  [ABORT] {len(bad)} move.lines com location_id != {LOC_TRANSITO}. NAO validando."); return 1
        try:
            ok = pick.validar(args.picking)
            print(f"  validar -> {ok}")
        except Exception as e:
            print(f"  [FALHA validar] {e}")
            return 1
        show_picking(o, args.picking, 'DEPOIS')
        print("  Proximo: --modo nf --po <id> --execute")
        return 0

    # =================================================================== gate 4: criar invoice (draft)
    if args.modo == 'nf':
        sec("GATE 4 — criar_invoice_from_po (ENTIN draft)")
        if not args.po:
            print("  [ABORT] --nf exige --po <id>"); return 1
        if not args.execute:
            print("  DRY: rode com --execute."); return 0
        # B-V23-2 (D-V23-3): alinhar PO.line.account_id p/ company LF (action_create_invoice rejeita account FB)
        ol = o.execute_kw('purchase.order', 'read', [[args.po], ['order_line']], {'context': ctx_lf()})[0]['order_line']
        po_lines = o.execute_kw('purchase.order.line', 'read', [ol, ['account_id']], {'context': ctx_lf()})
        nfix = 0
        for pl in po_lines:
            acc = pl.get('account_id')
            if not acc:
                continue
            acc_data = o.execute_kw('account.account', 'read', [[acc[0]], ['code', 'company_id']], {'context': ctx_lf()})[0]
            if acc_data['company_id'] and acc_data['company_id'][0] != COMPANY_LF:
                lf_acc = o.execute_kw('account.account', 'search_read', [[('code', '=', acc_data['code']), ('company_id', '=', COMPANY_LF)], ['id']], {'context': ctx_lf()})
                if lf_acc:
                    o.execute_kw('purchase.order.line', 'write', [[pl['id']], {'account_id': lf_acc[0]['id']}], {'context': ctx_lf()})
                    nfix += 1
        if nfix:
            print(f"  B-V23-2: {nfix} PO.line.account_id alinhados FB->LF (code {acc_data['code']})")
        # limpar taxes FB (empresas incompativeis na fatura LF) — piloto: taxes a recuperar = refinamento
        o.execute_kw('purchase.order.line', 'write', [ol, {'taxes_id': [(5, 0, 0)]}], {'context': ctx_lf()})
        print(f"  taxes_id das {len(ol)} linhas limpos (eram taxes FB)")
        # action_create_invoice DIRETO em ctx LF [1,5] (atomo usa ctx FB -> sem acesso a account.account LF)
        before = set(o.execute_kw('purchase.order', 'read', [[args.po], ['invoice_ids']], {'context': ctx_lf()})[0]['invoice_ids'] or [])
        try:
            o.execute_kw('purchase.order', 'action_create_invoice', [[args.po]], {'context': ctx_lf()})
        except Exception as e:
            print(f"  [aviso action_create_invoice] {str(e)[:200]}")
        after = set(o.execute_kw('purchase.order', 'read', [[args.po], ['invoice_ids']], {'context': ctx_lf()})[0]['invoice_ids'] or [])
        novos = list(after - before)
        inv = novos[0] if novos else (sorted(after)[-1] if after else None)
        print(f"  invoice_ids da PO: {sorted(after)}; ENTIN={inv}")
        if inv:
            mv = o.execute_kw('account.move', 'read', [[inv], ['name', 'state', 'l10n_br_tipo_pedido']], {'context': ctx_lf()})[0]
            print(f"  ENTIN {inv}: {mv['name']} state={mv['state']} tipo={mv.get('l10n_br_tipo_pedido')}")
            for ml in o.execute_kw('account.move.line', 'search_read', [[('move_id', '=', inv)], ['account_id', 'debit', 'credit', 'l10n_br_cfop_id']], {'context': ctx_lf(), 'limit': 20}):
                acc = ml['account_id'][1].split(' ')[0] if ml['account_id'] else '?'
                cfop = ml['l10n_br_cfop_id'][1].split(' ')[0] if ml.get('l10n_br_cfop_id') else '-'
                print(f"      {acc:12} D={ml['debit']:>9.2f} C={ml['credit']:>9.2f} cfop={cfop}")
            print(f"  Inspecione as contas (esperado D 1150100011 / C 5101020001 cfop 1901). Proximo: --modo post --invoice {inv} --execute")
        return 0

    # =================================================================== gate 5: post
    if args.modo == 'post':
        sec("GATE 5 — action_post (ENTIN)")
        if not args.invoice:
            print("  [ABORT] --post exige --invoice <id>"); return 1
        mv = o.read('account.move', [args.invoice], ['name', 'state'])[0]
        print(f"  ENTIN {args.invoice}: {mv['name']} state={mv['state']}")
        if not args.execute:
            print("  DRY: rode com --execute."); return 0
        if mv['state'] == 'posted':
            print("  ja posted."); return 0
        o.execute_kw('account.move', 'action_post', [[args.invoice]], {'context': ctx_lf()})
        st = o.read('account.move', [args.invoice], ['state'])[0]['state']
        print(f"  [OK] ENTIN state={st}")
        print(f"  VALIDAR: python docs/industrializacao-fb-lf/scripts/e2e_piloto_validar.py "
              f"--modo entrada-lf --picking <id> --nf {args.invoice} --lote {LOTE}")
        return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
