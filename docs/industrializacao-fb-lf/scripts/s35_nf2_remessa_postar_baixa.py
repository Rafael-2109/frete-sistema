#!/usr/bin/env python3
"""S35 — NF-2 (insumos 5902) FINAL: fonte = REMESSA (qty+price, invariante 5902=5901) +
postar no RETIND 1083 + MEDIR a baixa da PASSIVA 5101020001 end-to-end.

Consolida os achados da sessao (s27-s34):
  - fonte = linhas product da remessa 735679 (RPI/2026/00245): os 16 insumos exatos,
    qty E price da remessa (s34: total=279,23 = untax remessa). NAO usar BoM/standard_price.
  - header l10n_br_calcular_imposto=False (replica a NF real) + tipo_pedido + op 2864 + fp 111.
  - linhas op 2864 + operacao_manual=True -> cfop 5902 / CST 50 (recompute) + remap conta -> 1150100012.
  - SEM limpeza de imposto: o "-278/total 0" e' a BAIXA da PASSIVA (no_payment), nao tributo (s31-s33).
  - vNF SEFAZ = l10n_br_total_nfe = valor cheio (s33); tributo real nas linhas = 0 (s32).

MODOS:
  (sem flag)        dry-run READ: remessa + 16 linhas (qty/price) + checa journal (reversivel?) + saldo PASSIVA
  --confirmar       SA monta a NF-2 draft no RETIND 1083 (price=remessa) + recompute + remap + mede (NAO posta)
  --postar NF_ID    action_post + mede a baixa da PASSIVA 5101020001 (saldo antes/depois + linha da NF)
  --cleanup NF_ID   button_draft (se posted) + unlink (reverte; sem SEFAZ -> nao sobra rabo)
"""
import sys
import argparse
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
COD_PA = '4870112'
J_RETIND = 1083
PARTNER_FB = 1
OP_5902 = 2864
TIPO_PEDIDO = 'venda-industrializacao'
FP_RETIND = 111
REMESSA = 735679           # RPI/2026/00245 (fonte: qty+price, cfop 5901)
ACC_PASSIVA_LF = 26667     # 5101020001 PASSIVA LF (a baixar)
CONTA_ALVO = '1150100012'  # conta das 5902
NF_RETORNO_REAL = 709632


def m2o(v):
    return f"{v[0]}|{str(v[1])[:26]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true')
    ap.add_argument('--postar', type=int, metavar='NF_ID')
    ap.add_argument('--cleanup', type=int, metavar='NF_ID')
    args = ap.parse_args()
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    def saldo_passiva():
        lns = rr('account.move.line', [('account_id', '=', ACC_PASSIVA_LF),
                                       ('parent_state', '=', 'posted'), ('company_id', '=', 5)], ['balance'])
        return round(sum(l.get('balance') or 0 for l in lns), 2)

    # ---------- CLEANUP ----------
    if args.cleanup:
        nf = args.cleanup
        st = rr('account.move', [('id', '=', nf)], ['state', 'name'])
        if not st:
            print(f"  NF {nf} ja nao existe"); return
        if st[0]['state'] == 'posted':
            o.execute_kw('account.move', 'button_draft', [[nf]], {'context': CTX})
            print(f"  NF {nf}: posted -> draft")
        try:
            o.execute_kw('account.move', 'unlink', [[nf]], {'context': CTX})
            print(f"  NF {nf} ({st[0].get('name')}) DELETADA")
        except Exception as e:
            o.execute_kw('account.move', 'button_cancel', [[nf]], {'context': CTX})
            print(f"  NF {nf} unlink falhou ({str(e)[:60]}); CANCELADA")
        return

    # ---------- POSTAR + MEDIR BAIXA ----------
    if args.postar:
        nf = args.postar
        st = rr('account.move', [('id', '=', nf)], ['state', 'name', 'amount_untaxed', 'l10n_br_total_nfe'])
        assert st, f"NF {nf} nao existe"
        print(f"  NF {nf} = {st[0]['name']} state={st[0]['state']} untax={st[0]['amount_untaxed']} "
              f"vNF={st[0]['l10n_br_total_nfe']}")
        if st[0]['state'] != 'draft':
            print(f"  (NF nao esta em draft — abortando post)"); return
        antes = saldo_passiva()
        print(f"\n  saldo PASSIVA 5101020001 (LF) ANTES = {antes}")
        print(f"  >>> action_post...")
        try:
            o.execute_kw('account.move', 'action_post', [[nf]],
                         {'context': dict(CTX, allowed_company_ids=[5])})
        except Exception as e:
            print(f"  ❌ action_post FALHOU: {str(e)[:240]}")
            return
        depois = saldo_passiva()
        nfl = rr('account.move.line', [('move_id', '=', nf), ('account_id', '=', ACC_PASSIVA_LF)],
                 ['debit', 'credit', 'balance', 'display_type'])
        h2 = rr('account.move', [('id', '=', nf)], ['state', 'amount_total', 'l10n_br_total_nfe'])
        print(f"  saldo PASSIVA 5101020001 (LF) DEPOIS = {depois}  | Δ = {round(depois-antes,2)}")
        print(f"  linha(s) da NF na conta 26667: {[{'D':l['debit'],'C':l['credit'],'dt':l['display_type']} for l in nfl]}")
        print(f"  NF agora: state={h2[0]['state']} amount_total={h2[0]['amount_total']} vNF={h2[0]['l10n_br_total_nfe']}")
        debito_nf = round(sum(l.get('debit') or 0 for l in nfl), 2)
        print(f"\n  >>> BAIXA da PASSIVA = D {debito_nf} na 5101020001 "
              f"{'✅' if debito_nf > 0 and abs((depois-antes)-debito_nf) < 0.01 else '⚠️ conferir'}")
        print(f"  >>> reverter (sem SEFAZ): --cleanup {nf}")
        return

    # ---------- DRY-RUN / MONTAR ----------
    rem = rr('account.move', [('id', '=', REMESSA)], ['name', 'state', 'amount_untaxed'])
    rlines = rr('account.move.line', [('move_id', '=', REMESSA), ('display_type', '=', 'product')],
                ['product_id', 'l10n_br_cfop_codigo', 'quantity', 'price_unit', 'price_subtotal'], order='id')
    total_src = round(sum(l.get('price_subtotal') or 0 for l in rlines), 2)

    print("=" * 94)
    print(f"S35 — NF-2 (insumos) FINAL: fonte = REMESSA {REMESSA} ({rem[0]['name']}), price invariante 5902=5901")
    print("=" * 94)
    print(f"  {len(rlines)} linhas a criar (qty+price da remessa) | total esperado = R$ {total_src} "
          f"(= untax remessa {rem[0]['amount_untaxed']})")
    for l in rlines:
        print(f"     {m2o(l['product_id'])[:42]:42} qty={l['quantity']} pu={round(l['price_unit'],6)} "
              f"sub={l['price_subtotal']}")

    # validacao vs NF real
    real = rr('account.move.line', [('move_id', '=', NF_RETORNO_REAL), ('display_type', '=', 'product'),
                                    ('l10n_br_cfop_codigo', '=', '5902')], ['product_id'])
    real_ids = {l['product_id'][0] for l in real}
    src_ids = {l['product_id'][0] for l in rlines}
    print(f"\n  vs NF real {NF_RETORNO_REAL}: {'✅ MATCH EXATO (16)' if real_ids == src_ids else f'⚠️ falta={real_ids-src_ids} sobra={src_ids-real_ids}'}")

    # journal reversivel?
    j = rr('account.journal', [('id', '=', J_RETIND)],
           ['name', 'restrict_mode_hash_table', 'l10n_br_tipo_pedido'])
    hashed = j[0].get('restrict_mode_hash_table') if j else None
    print(f"\n  journal {J_RETIND} ({j[0]['name'] if j else '?'}): restrict_mode_hash_table={hashed} "
          f"-> {'⚠️ post NAO reversivel (hash); usar journal de teste' if hashed else '✅ post reversivel (button_draft+unlink)'}")
    print(f"  saldo atual PASSIVA 5101020001 (LF) = {saldo_passiva()} (a baixa esperada no post = D {total_src})")

    if not args.confirmar:
        print(f"\n  [DRY-RUN] nada escrito. Montar (draft): --confirmar | depois postar: --postar NF_ID")
        return

    # ---- montar via server action (fonte=remessa, sem limpeza de imposto) ----
    code = (
        "rem = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').browse(%d)\n"
        "rlines = rem.invoice_line_ids.filtered(lambda l: l.display_type=='product')\n"
        "move = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').create({\n"
        "    'move_type':'out_invoice','journal_id':%d,'partner_id':%d,'company_id':5,\n"
        "    'l10n_br_tipo_pedido':'%s','l10n_br_operacao_id':%d,'fiscal_position_id':%d,\n"
        "    'l10n_br_calcular_imposto':False,'invoice_date': datetime.date.today()})\n"
        "criadas=0; erros=[]\n"
        "for rl in rlines:\n"
        "    try:\n"
        "        env['account.move.line'].sudo().with_context(allowed_company_ids=[5], check_move_validity=False).create({\n"
        "            'move_id':move.id,'product_id':rl.product_id.id,'quantity':rl.quantity,\n"
        "            'l10n_br_operacao_id':%d,'l10n_br_operacao_manual':True,'price_unit':rl.price_unit})\n"
        "        criadas+=1\n"
        "    except Exception as e:\n"
        "        erros.append('%%s:%%s'%%(rl.product_id.default_code,str(e)[:50]))\n"
        "try:\n"
        "    move.onchange_l10n_br_calcular_imposto(); move.onchange_l10n_br_calcular_imposto_btn()\n"
        "except Exception as e:\n"
        "    log('S35 recompute erro: %%s'%%str(e)[:140])\n"
        "amap = {}\n"
        "for fa in env['account.fiscal.position.account'].sudo().search([('position_id','=',%d)]):\n"
        "    amap[fa.account_src_id.id] = fa.account_dest_id.id\n"
        "remap = 0\n"
        "for l in move.invoice_line_ids.filtered(lambda x: x.display_type=='product'):\n"
        "    dest = amap.get(l.account_id.id)\n"
        "    if dest and dest != l.account_id.id:\n"
        "        l.with_context(check_move_validity=False).write({'account_id': dest}); remap += 1\n"
        "pl = move.invoice_line_ids.filtered(lambda l: l.display_type=='product')\n"
        "cfops = dict((c, list(pl.mapped('l10n_br_cfop_codigo')).count(c)) for c in set(pl.mapped('l10n_br_cfop_codigo')))\n"
        "csts = dict((c, list(pl.mapped('l10n_br_icms_cst')).count(c)) for c in set(pl.mapped('l10n_br_icms_cst')))\n"
        "contas = sorted(set(pl.mapped('account_id.code')))\n"
        "trib = sum((l.l10n_br_icms_valor or 0)+(l.l10n_br_pis_valor or 0)+(l.l10n_br_cofins_valor or 0)+(l.l10n_br_ipi_valor or 0) for l in pl)\n"
        "log('S35-RESULT inv=%%s criadas=%%s linhas=%%s cfops=%%s csts=%%s contas=%%s untax=%%s total=%%s vNF=%%s tributo=%%s remap=%%s erros=%%s' %% (str(move.ids), criadas, len(pl), str(cfops), str(csts), str(contas), move.amount_untaxed, move.amount_total, move.l10n_br_total_nfe, round(trib,2), remap, str(erros[:3])))\n"
    ) % (REMESSA, J_RETIND, PARTNER_FB, TIPO_PEDIDO, OP_5902, FP_RETIND, OP_5902, FP_RETIND)

    model_id = o.execute_kw('ir.model', 'search', [[('model', '=', 'account.move')]], {'context': CTX})[0]
    print("\n  [1] criando server action de teste...")
    sa = o.execute_kw('ir.actions.server', 'create',
                      [{'name': 'ZZ TESTE S35 NF-2 REMESSA - DELETAR', 'model_id': model_id,
                        'state': 'code', 'code': code}], {'context': CTX})
    print(f"      SA {sa} criada; executando...")
    try:
        o.execute_kw('ir.actions.server', 'run', [[sa]],
                     {'context': dict(CTX, active_model='account.move', active_id=False, active_ids=[])})
    except Exception as e:
        print(f"      SA run aviso: {str(e)[:160]}")
    rec = rr('account.move', [('journal_id', '=', J_RETIND), ('state', '=', 'draft')], ['id'], order='id desc', limit=1)
    nf_id = rec[0]['id'] if rec else None
    lg = rr('ir.logging', [('message', '=like', 'S35-RESULT%')], ['message'], order='id desc', limit=1)
    if lg:
        print(f"\n  LOG: {lg[0]['message'][:460]}")
    o.execute_kw('ir.actions.server', 'unlink', [[sa]], {'context': CTX})
    print(f"  SA {sa} DELETADA")
    if nf_id:
        h = rr('account.move', [('id', '=', nf_id)],
               ['amount_untaxed', 'amount_total', 'l10n_br_total_nfe', 'l10n_br_calcular_imposto'])[0]
        nl = rr('account.move.line', [('move_id', '=', nf_id), ('display_type', '=', 'product')],
                ['l10n_br_cfop_codigo', 'l10n_br_icms_cst', 'tax_ids', 'account_id'])
        ok = (all(str(x.get('l10n_br_cfop_codigo')) == '5902' for x in nl)
              and all(str(x.get('l10n_br_icms_cst')) == '50' for x in nl)
              and all(CONTA_ALVO in m2o(x.get('account_id')) for x in nl)
              and all(not x.get('tax_ids') for x in nl))
        print(f"\n  >>> NF-2 {nf_id}: {len(nl)} linhas | untax={h['amount_untaxed']} total_contabil={h['amount_total']} "
              f"vNF_SEFAZ={h['l10n_br_total_nfe']} calc_imp={h['l10n_br_calcular_imposto']}")
        print(f"      CFOP={dict(Counter(str(x.get('l10n_br_cfop_codigo')) for x in nl))} "
              f"CST={dict(Counter(str(x.get('l10n_br_icms_cst')) for x in nl))} "
              f"estrutura={'✅ OK' if ok else '❌ conferir'}")
        print(f"  >>> postar+medir baixa: --postar {nf_id}  |  reverter: --cleanup {nf_id}")


if __name__ == '__main__':
    main()
