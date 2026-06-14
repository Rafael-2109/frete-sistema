#!/usr/bin/env python3
"""S37 — Task #4: SA "Gerar Retorno Industrializacao" — UNE NF-1 (servico 5124) + NF-2
(insumos 5902) numa MESMA server action + vinculo R3 (invoice_origin comum +
referencia_ids->chave da remessa). Consolida GATE 1c (s15, NF-1) + s35 (NF-2).

A SA (server-side, ctx LF-only [5]):
  1. NF-1 SERVICO: stock.invoice.onshipping.create_invoice(picking pt66) -> j847, 1x5124 (op 2702/CST 51)
  2. NF-2 INSUMOS: account.move novo no RETIND 1083 + 16x5902 da remessa (op 2864, operacao_manual,
     calcular_imposto=False) + recompute + remap conta -> 1150100012 (= s35; baixa PASSIVA no post)
  3. CADASTRO FISCAL SEFAZ (4 gaps provados na transmissao real 2026-06-14 — s51/s53/s55/s58):
     incoterm CIF(6) [frete do emitente LF] + carrier LF(999) + payment_provider(31) nas 2 +
     vencimento a-prazo (emissao+1) so na NF-1 (senao a duplicata cai em 'a vista' -> SEFAZ rejeita).
  4. R3 (draft): invoice_origin comum nas 2 + referencia_ids (refNFe) -> chave da remessa RPI em ambas
     (cross-refNFe NF-1<->NF-2 fica p/ o GATE 2, pos-SEFAZ — chave so existe apos autorizar)
  5. mede ambas (estrutura + vinculo). SEM action_post, SEM SEFAZ. Draft. Reversivel.

PILOTO FIRMADO 2026-06-14: NF-1 791437 (VND/2026/00384) + NF-2 791441 (RETIN/2026/00001),
AMBAS cstat=100 na SEFAZ via SERVER ACTION (action_previsualizar_xml_nfe + action_gerar_nfe;
Playwright NAO foi necessario). Baixa PASSIVA Δ+279,23, R3 completo (refNFe remessa + cross).

MODOS:
  (sem flag)              dry-run READ: estado PA + picking + remessa/chave + campos req do refNFe + plano
  --criar-picking         cria o picking pt66 do PA (31093->5 Clientes), validado, anti-robo [escrita 1]
  --gerar PICK_ID         SA: NF-1 + NF-2 + R3 + mede (deixa as 2 em DRAFT) [escrita 2]
  --cleanup PICK [NF1 NF2]  deleta NFs (draft/posted) + devolve picking 5->31093 (sem rabo)
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
LF, FB = 5, 1
PA_PROD = 27834           # 4870112
PA_LOT = 60542            # PILOTO-3105
LOC_SRC = 31093           # LF/PA de Terceiros
LOC_DST = 5               # Clientes (saida p/ FB)
PT_RET = 66               # pt66 Expedicao Industrializacao
J847 = 847                # NF-1 servico (venda-industrializacao)
RETIND = 1083             # NF-2 insumos (no_payment PASSIVA 26667)
REMESSA = 735679          # RPI/2026/00245 (fonte das 5902 + chave do refNFe)
OP_5902 = 2864
FP_RETIND = 111
ORIGIN = 'RET-IND-4870112-PILOTO'   # invoice_origin comum (vinculo R3 em draft)
REF_MODEL = 'l10n_br_ciel_it_account.account.move.referencia'


def m2o(v):
    return f"{v[0]}|{str(v[1])[:28]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--criar-picking', action='store_true')
    ap.add_argument('--gerar', type=int, metavar='PICK_ID')
    ap.add_argument('--cleanup', nargs='+', type=int, metavar='PICK [NF1 NF2]')
    args = ap.parse_args()
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)
    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})
    def w(model, ids, vals):
        return o.execute_kw(model, 'write', [list(ids), vals], {'context': CTX})

    # ============ CLEANUP ============
    if args.cleanup:
        pid = args.cleanup[0]
        nfs = args.cleanup[1:]
        print(f"=== CLEANUP picking {pid} + NFs {nfs} ===")
        for mv in nfs:
            st = rd('account.move', [mv], ['state', 'name'])
            if not st:
                print(f"  NF {mv}: ja nao existe"); continue
            if st[0]['state'] == 'posted':
                o.execute_kw('account.move', 'button_draft', [[mv]], {'context': CTX})
            try:
                o.execute_kw('account.move', 'unlink', [[mv]], {'context': CTX})
                print(f"  NF {mv} ({st[0].get('name')}) DELETADA")
            except Exception as e:
                o.execute_kw('account.move', 'button_cancel', [[mv]], {'context': CTX})
                print(f"  NF {mv} unlink falhou; CANCELADA ({str(e)[:50]})")
        pst = rd('stock.picking', [pid], ['state']) if pid else []
        if pst and pst[0].get('state') == 'done':
            prod = rd('product.product', [PA_PROD], ['uom_id'])[0]; uom = prod['uom_id'][0]
            ipt = rr('stock.picking.type', [('company_id', '=', LF), ('code', '=', 'internal')], ['id'], limit=1)
            rpid = o.execute_kw('stock.picking', 'create', [{
                'picking_type_id': ipt[0]['id'], 'location_id': LOC_DST, 'location_dest_id': LOC_SRC,
                'company_id': LF, 'origin': ORIGIN + '-REVERT'}], {'context': CTX})
            mid_r = o.execute_kw('stock.move', 'create', [{
                'name': 'REVERT PA', 'picking_id': rpid, 'product_id': PA_PROD,
                'product_uom_qty': 1.0, 'product_uom': uom, 'location_id': LOC_DST,
                'location_dest_id': LOC_SRC, 'company_id': LF}], {'context': CTX})
            o.execute_kw('stock.picking', 'action_confirm', [[rpid]], {'context': CTX})
            mlf = o.execute_kw('stock.move.line', 'fields_get', [], {'attributes': [], 'context': CTX})
            mlv = {'move_id': mid_r, 'picking_id': rpid, 'product_id': PA_PROD, 'lot_id': PA_LOT,
                   'location_id': LOC_DST, 'location_dest_id': LOC_SRC, 'product_uom_id': uom,
                   'quantity': 1.0, 'company_id': LF}
            if 'qty_done' in mlf: mlv['qty_done'] = 1.0
            if 'picked' in mlf: mlv['picked'] = True
            o.execute_kw('stock.move.line', 'create', [mlv], {'context': CTX})
            o.execute_kw('stock.picking', 'button_validate', [[rpid]],
                         {'context': dict(CTX, skip_backorder=True, skip_immediate=True)})
            print(f"  PA devolvido 5->31093 via picking {rpid}")
        else:
            print(f"  picking {pid}: state={pst[0].get('state') if pst else '?'} — sem devolucao")
        return

    # ============ CRIAR PICKING pt66 ============
    if args.criar_picking:
        print(f"=== CRIAR PICKING pt66 (PA {PA_PROD}, {LOC_SRC}->5 Clientes, origin={ORIGIN}) ===")
        prod = rd('product.product', [PA_PROD], ['uom_id'])[0]; uom = prod['uom_id'][0]
        pid = o.execute_kw('stock.picking', 'create', [{
            'picking_type_id': PT_RET, 'partner_id': FB, 'location_id': LOC_SRC,
            'location_dest_id': LOC_DST, 'company_id': LF, 'origin': ORIGIN}], {'context': CTX})
        mid = o.execute_kw('stock.move', 'create', [{
            'name': f'PA {PA_PROD} {ORIGIN}', 'picking_id': pid, 'product_id': PA_PROD,
            'product_uom_qty': 1.0, 'product_uom': uom, 'location_id': LOC_SRC,
            'location_dest_id': LOC_DST, 'company_id': LF}], {'context': CTX})
        o.execute_kw('stock.picking', 'action_confirm', [[pid]], {'context': CTX})
        o.execute_kw('stock.picking', 'action_assign', [[pid]], {'context': CTX})
        mlf = o.execute_kw('stock.move.line', 'fields_get', [], {'attributes': ['type'], 'context': CTX})
        upd = {'lot_id': PA_LOT, 'quantity': 1.0}
        if 'qty_done' in mlf: upd['qty_done'] = 1.0
        if 'picked' in mlf: upd['picked'] = True
        mls = rr('stock.move.line', [('picking_id', '=', pid)], ['id'])
        if mls:
            w('stock.move.line', [mls[0]['id']], upd)
        else:
            upd.update({'move_id': mid, 'picking_id': pid, 'product_id': PA_PROD,
                        'location_id': LOC_SRC, 'location_dest_id': LOC_DST, 'product_uom_id': uom, 'company_id': LF})
            o.execute_kw('stock.move.line', 'create', [upd], {'context': CTX})
        w('stock.picking', [pid], {'liberado_faturamento': False, 'robo': 0})
        o.execute_kw('stock.picking', 'button_validate', [[pid]],
                     {'context': dict(CTX, skip_backorder=True, skip_immediate=True)})
        p = rd('stock.picking', [pid], ['name', 'state', 'liberado_faturamento', 'robo'])[0]
        print(f"  picking {pid} {p['name']} state={p['state']} "
              f"liberado_faturamento={p.get('liberado_faturamento')} robo={p.get('robo')}")
        print(f"  >>> proximo: --gerar {pid}   (revert: --cleanup {pid} <NF1> <NF2>)")
        return

    # ============ GERAR (SA: NF-1 + NF-2 + R3) ============
    if args.gerar:
        pick = args.gerar
        chave = rd('account.move', [REMESSA], ['l10n_br_chave_nf'])[0].get('l10n_br_chave_nf')
        assert chave, "remessa sem chave NFe — refNFe impossivel"
        code = (
            "pk = env['stock.picking'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').browse(%d)\n"
            "wiz = env['stock.invoice.onshipping'].with_context(active_ids=[%d], active_model='stock.picking', allowed_company_ids=[5], lang='pt_BR').create({'company_id':5,'journal_id':%d})\n"
            "inv1 = wiz.create_invoice()\n"
            "nf1 = pk.invoice_ids[:1] if pk.invoice_ids else env['account.move'].browse(inv1)\n"
            "nf1 = nf1[:1]\n"
            # recompute NF-1: materializa as tax lines de PIS/COFINS (servico 5124 e' tributado);
            # sem isto a NF-1 fica desequilibrada (vNF tem imposto mas faltam as tax lines) -> nao posta
            "try:\n"
            "    nf1.onchange_l10n_br_calcular_imposto(); nf1.onchange_l10n_br_calcular_imposto_btn()\n"
            "except Exception as e:\n"
            "    log('S37 nf1 recompute erro: %%s'%%str(e)[:120])\n"
            # cadastro fiscal SEFAZ (gaps provados na transmissao 2026-06-14, s51/s53/s55/s58):
            # incoterm CIF (frete do emitente LF) + carrier LF(999) + forma pgto(31) + vencimento
            # a-prazo (emissao+1) — senao a duplicata do servico cai em 'a vista' e a SEFAZ rejeita.
            "nf1.with_context(check_move_validity=False).write({'invoice_incoterm_id':6,'l10n_br_carrier_id':999,'payment_provider_id':31})\n"
            "_due = (nf1.invoice_date + datetime.timedelta(days=1)) if nf1.invoice_date else False\n"
            "if _due:\n"
            "    for _pl in nf1.line_ids.filtered(lambda x: x.display_type=='payment_term'):\n"
            "        _pl.with_context(check_move_validity=False).write({'date_maturity':_due})\n"
            "    nf1.with_context(check_move_validity=False).write({'invoice_date_due':_due})\n"
            # --- NF-2 insumos (= s35) ---
            "rem = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').browse(%d)\n"
            "rlines = rem.invoice_line_ids.filtered(lambda l: l.display_type=='product')\n"
            "nf2 = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').create({\n"
            "    'move_type':'out_invoice','journal_id':%d,'partner_id':1,'company_id':5,\n"
            "    'l10n_br_tipo_pedido':'venda-industrializacao','l10n_br_operacao_id':%d,'fiscal_position_id':%d,\n"
            # cadastro fiscal SEFAZ (= NF-1): incoterm CIF + carrier LF + forma pgto. NF-2 nao tem
            # duplicata (total contabil 0 / no_payment), entao sem vencimento a-prazo.
            "    'invoice_incoterm_id':6,'l10n_br_carrier_id':999,'payment_provider_id':31,\n"
            # invoice_date = o da NF-1 (data BRT correta). datetime.date.today() na SA da' UTC
            # (gotcha TZ: 14/06 apos 21h BRT) e desalinha vs NF-1 -> post da NF-2 falha por data.
            "    'l10n_br_calcular_imposto':False,'invoice_date': nf1.invoice_date or datetime.date.today()})\n"
            "erros=[]\n"
            "for rl in rlines:\n"
            "    try:\n"
            "        env['account.move.line'].sudo().with_context(allowed_company_ids=[5], check_move_validity=False).create({\n"
            "            'move_id':nf2.id,'product_id':rl.product_id.id,'quantity':rl.quantity,\n"
            "            'l10n_br_operacao_id':%d,'l10n_br_operacao_manual':True,'price_unit':rl.price_unit})\n"
            "    except Exception as e:\n"
            "        erros.append(str(e)[:40])\n"
            "try:\n"
            "    nf2.onchange_l10n_br_calcular_imposto(); nf2.onchange_l10n_br_calcular_imposto_btn()\n"
            "except Exception as e:\n"
            "    log('S37 recompute erro: %%s'%%str(e)[:120])\n"
            "amap={}\n"
            "for fa in env['account.fiscal.position.account'].sudo().search([('position_id','=',%d)]):\n"
            "    amap[fa.account_src_id.id]=fa.account_dest_id.id\n"
            "for l in nf2.invoice_line_ids.filtered(lambda x: x.display_type=='product'):\n"
            "    dest=amap.get(l.account_id.id)\n"
            "    if dest and dest!=l.account_id.id:\n"
            "        l.with_context(check_move_validity=False).write({'account_id':dest})\n"
            # --- R3 vinculo ---
            "chave='%s'\n"
            "nf1.with_context(check_move_validity=False).write({'invoice_origin':'%s','referencia_ids':[(0,0,{'l10n_br_chave_nf':chave,'company_id':5})]})\n"
            "nf2.with_context(check_move_validity=False).write({'invoice_origin':'%s','referencia_ids':[(0,0,{'l10n_br_chave_nf':chave,'company_id':5})]})\n"
            # --- medir ---
            "p1=nf1.invoice_line_ids.filtered(lambda l: l.display_type=='product')\n"
            "p2=nf2.invoice_line_ids.filtered(lambda l: l.display_type=='product')\n"
            "log('S37-RESULT nf1=%%s nf1_n=%%s nf1_cfop=%%s nf1_journal=%%s nf2=%%s nf2_n=%%s nf2_cfop=%%s nf2_cst=%%s nf2_total=%%s nf2_vNF=%%s origin1=%%s origin2=%%s ref1=%%s ref2=%%s erros=%%s' %% (str(nf1.ids), len(p1), str(set(p1.mapped('l10n_br_cfop_codigo'))), nf1.journal_id.code, str(nf2.ids), len(p2), str(set(p2.mapped('l10n_br_cfop_codigo'))), str(set(p2.mapped('l10n_br_icms_cst'))), nf2.amount_total, nf2.l10n_br_total_nfe, nf1.invoice_origin, nf2.invoice_origin, len(nf1.referencia_ids), len(nf2.referencia_ids), str(erros[:2])))\n"
        ) % (pick, pick, J847, REMESSA, RETIND, OP_5902, FP_RETIND, OP_5902, FP_RETIND,
             chave, ORIGIN, ORIGIN)

        model_id = o.execute_kw('ir.model', 'search', [[('model', '=', 'account.move')]], {'context': CTX})[0]
        print(f"=== GERAR 2 NFs (picking {pick}) via server action ===")
        sa = o.execute_kw('ir.actions.server', 'create',
                          [{'name': 'ZZ TESTE S37 RETORNO 2NF - DELETAR', 'model_id': model_id,
                            'state': 'code', 'code': code}], {'context': CTX})
        print(f"  SA {sa} criada; executando (create_invoice NF-1 + monta NF-2 + R3)...")
        try:
            o.execute_kw('ir.actions.server', 'run', [[sa]],
                         {'context': dict(CTX, active_model='account.move', active_id=False, active_ids=[])})
        except Exception as e:
            print(f"  SA run aviso: {str(e)[:200]}")
        lg = rr('ir.logging', [('message', '=like', 'S37-RESULT%')], ['message'], order='id desc', limit=1)
        rerr = rr('ir.logging', [('message', '=like', 'S37 recompute%')], ['message'], order='id desc', limit=1)
        if rerr:
            print(f"  {rerr[0]['message'][:160]}")
        o.execute_kw('ir.actions.server', 'unlink', [[sa]], {'context': CTX})
        print(f"  SA {sa} DELETADA")
        if lg:
            print(f"\n  LOG: {lg[0]['message'][:520]}")
        # captura as 2 NFs e mede (CIEL IT vincula picking->NF-1 via invoice_id m2o, nao invoice_ids)
        pf = o.execute_kw('stock.picking', 'fields_get', [], {'attributes': [], 'context': CTX})
        flds = [x for x in ['invoice_id', 'invoice_ids'] if x in pf]
        p = rd('stock.picking', [pick], flds)[0]
        nf1 = (p['invoice_id'][0] if p.get('invoice_id') else (p.get('invoice_ids') or [None])[0])
        nf2rec = rr('account.move', [('journal_id', '=', RETIND), ('state', '=', 'draft')], ['id'], order='id desc', limit=1)
        nf2 = nf2rec[0]['id'] if nf2rec else None
        print(f"\n  >>> NF-1 (servico) = {nf1} | NF-2 (insumos) = {nf2}")
        if nf1 and nf2:
            print(f"  >>> reverter: --cleanup {pick} {nf1} {nf2}")
        return

    # ============ DRY-RUN (default) ============
    print("=" * 92)
    print("S37 — Task #4 (DRY-RUN): SA que une NF-1 (5124) + NF-2 (5902) + R3")
    print("=" * 92)
    q = rr('stock.quant', [('product_id', '=', PA_PROD), ('location_id', '=', LOC_SRC)],
           ['lot_id', 'quantity', 'reserved_quantity'])
    livre = sum((x.get('quantity') or 0) - (x.get('reserved_quantity') or 0)
                for x in q if isinstance(x.get('lot_id'), list) and x['lot_id'][0] == PA_LOT)
    print(f"  [1] PA {PA_PROD} em 31093 lote PILOTO-3105: livre={livre} {'✅' if livre >= 1 else '❌'}")
    rem = rd('account.move', [REMESSA], ['name', 'state', 'amount_untaxed', 'l10n_br_chave_nf'])[0]
    print(f"  [2] remessa {rem['name']} state={rem['state']} untax={rem['amount_untaxed']}")
    print(f"      chave (refNFe das 2 NFs) = {rem.get('l10n_br_chave_nf')}")
    # campos required do modelo referencia (p/ o refNFe nao falhar)
    rfg = o.execute_kw(REF_MODEL, 'fields_get', [], {'attributes': ['string', 'required', 'type'], 'context': CTX})
    reqs = [f for f, mt in rfg.items() if mt.get('required') and f not in ('move_id',)]
    print(f"  [3] modelo refNFe {REF_MODEL}: campos required (alem de move_id) = {reqs or 'só a chave basta'}")
    print(f"  [4] PLANO da SA: NF-1 create_invoice(picking) j{J847} (5124) + NF-2 RETIND {RETIND} (16x5902, =s35)")
    print(f"      + R3: invoice_origin='{ORIGIN}' nas 2 + referencia_ids->chave remessa nas 2")
    print(f"\n  [DRY-RUN] nada escrito. Passos: --criar-picking -> --gerar PICK_ID -> --cleanup PICK NF1 NF2")


if __name__ == '__main__':
    main()
