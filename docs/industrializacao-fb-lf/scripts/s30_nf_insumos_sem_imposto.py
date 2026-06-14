#!/usr/bin/env python3
"""S30 — NF-INSUMOS (5902) do shoyu 4870112 SEM IMPOSTO ESPURIO (sucessor do s24).

PROBLEMA do s24: o recompute (onchange_l10n_br_calcular_imposto_btn) gera tax lines de
compensacao espurias (amount_tax=-278,17 / total=0). A NF de retorno REAL (709632) tem
as 5902 com tax_ids=[] / valores de imposto = 0 / subtotal=total (VALOR CHEIO creditando
1150100012); o header tem l10n_br_calcular_imposto=False (a operadora NAO recalcula). As
8 tax lines da NF mista sao TODAS do servico 5124 — as 5902 nao tem nenhuma.
[FONTE: s27/s28/s29 — diagnostico READ-only desta sessao]

RECEITA (determinista) p/ replicar o estado-alvo das 5902:
  1. header com l10n_br_calcular_imposto=False (desde o create) + tipo_pedido + op 2864 + fp 111
  2. cria as N linhas (op 2864, operacao_manual=True) — fonte = MATERIAIS DE TERCEIROS (s23/s24)
  3. recompute (deriva cfop 5902 / CST 50 / conta) — gera tax lixo
  4. remap de conta -> 1150100012 (fp 111, igual s24)
  5. LIMPEZA: tax_ids=[] nas product lines + unlink das tax lines + zera l10n_br_*_valor
     + reforca calcular_imposto=False
  -> ALVO: tax_ids=[] | amount_tax=0 | amount_total = soma dos insumos (valor cheio)
           cfop 5902 | CST 50 | conta 1150100012

A baixa da PASSIVA 5101020001 NAO acontece aqui (draft); vem do no_payment=26667 do
RETIND 1083 no action_post (GATE 0 ja provou). Medir no GATE 3 (Task #3).

READ-only no dry-run. Escrita (--confirmar) = server action; draft, sem SEFAZ; --cleanup deleta.

MODOS:
  (sem flag)      dry-run: explode + filtra + valida vs NF real + lista os 16 + plano de limpeza
  --confirmar     SA cria NF-insumos draft + N x 5902 (op 2864) + recompute + LIMPEZA + medicao
  --cleanup NF_ID button_draft + unlink da NF de teste
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
NF_RETORNO_REAL = 709632   # VND real do shoyu: 1x5124 + 16x5902 (validacao + alvo fiscal)
CONTA_ALVO = '1150100012'  # FATURAMENTO FISICO FISCAL (conta das 5902 na NF real)


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def explode_bom(o, rr, tmpl_id, fator, folhas):
    boms = rr('mrp.bom', ['|', ('product_tmpl_id', '=', tmpl_id), ('product_id', '=', tmpl_id)],
              ['id', 'product_qty'], limit=1)
    if not boms:
        return False
    rende = boms[0].get('product_qty') or 1.0
    lines = rr('mrp.bom.line', [('bom_id', '=', boms[0]['id'])], ['product_id', 'product_qty'], order='id')
    for ln in lines:
        cid = ln['product_id'][0]
        ctmpl = rr('product.product', [('id', '=', cid)], ['product_tmpl_id'])[0]['product_tmpl_id'][0]
        q = fator * (ln['product_qty'] / rende)
        sub = rr('mrp.bom', ['|', ('product_tmpl_id', '=', ctmpl), ('product_id', '=', cid)], ['id'], limit=1)
        if sub:
            explode_bom(o, rr, ctmpl, q, folhas)
        else:
            folhas[cid] = folhas.get(cid, 0.0) + q
    return True


def montar_fonte(o, rr):
    prod = rr('product.product', [('default_code', '=', COD_PA)], ['id', 'product_tmpl_id'], limit=1)
    ptmpl = prod[0]['product_tmpl_id'][0]
    folhas = {}
    explode_bom(o, rr, ptmpl, 1.0, folhas)
    pinfo = rr('product.product', [('id', 'in', list(folhas))],
               ['id', 'default_code', 'name', 'type', 'standard_price'])
    by = {p['id']: p for p in pinfo}
    out = []
    for pid, qty in folhas.items():
        p = by.get(pid, {})
        out.append({'product_id': pid, 'qty': round(qty, 6), 'code': p.get('default_code'),
                    'name': (p.get('name') or '')[:34], 'type': p.get('type'),
                    'price': p.get('standard_price') or 0.01})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true')
    ap.add_argument('--cleanup', type=int, metavar='NF_ID')
    args = ap.parse_args()
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    if args.cleanup:
        nf = args.cleanup
        st = rr('account.move', [('id', '=', nf)], ['state', 'name'])
        if not st:
            print(f"  NF {nf} ja nao existe"); return
        if st[0]['state'] == 'posted':
            o.execute_kw('account.move', 'button_draft', [[nf]], {'context': CTX})
        try:
            o.execute_kw('account.move', 'unlink', [[nf]], {'context': CTX})
            print(f"  NF {nf} ({st[0].get('name')}) DELETADA")
        except Exception as e:
            o.execute_kw('account.move', 'button_cancel', [[nf]], {'context': CTX})
            print(f"  NF {nf} unlink falhou ({str(e)[:60]}); CANCELADA")
        return

    fonte = montar_fonte(o, rr)
    terceiros = [f for f in fonte if f['type'] == 'product']
    excluidos = [f for f in fonte if f['type'] != 'product']

    print("=" * 92)
    print(f"S30 — NF-INSUMOS do shoyu {COD_PA}: fonte = MATERIAIS DE TERCEIROS, SEM IMPOSTO ESPURIO")
    print("=" * 92)
    print(f"  BoM explodida = {len(fonte)} folhas | terceiros(type=product) = {len(terceiros)} | "
          f"excluidos(consu/service) = {len(excluidos)}")
    for e in excluidos:
        print(f"     EXCLUIDO: [{e['code']}] {e['name']} type={e['type']} qty={e['qty']}")

    real = rr('account.move.line', [('move_id', '=', NF_RETORNO_REAL), ('display_type', '=', 'product'),
                                    ('l10n_br_cfop_codigo', '=', '5902')], ['product_id'])
    real_ids = {l['product_id'][0] for l in real}
    fonte_ids = {f['product_id'] for f in terceiros}
    falta = real_ids - fonte_ids
    sobra = fonte_ids - real_ids
    print(f"\n  VALIDACAO vs NF real {NF_RETORNO_REAL}: real={len(real_ids)} 5902 | fonte={len(fonte_ids)} | "
          f"{'✅ MATCH EXATO' if not falta and not sobra else '⚠️ DIVERGENCIA'}")
    if falta:
        print(f"     na NF real mas NAO na fonte: {falta}")
    if sobra:
        print(f"     na fonte mas NAO na NF real: {sobra}")

    print(f"\n  ALVO fiscal (= 5902 da NF real {NF_RETORNO_REAL}): tax_ids=[] | amount_tax=0 | "
          f"cfop 5902 | CST 50 | conta {CONTA_ALVO} | total = soma dos insumos (valor cheio)")
    print(f"  Plano de limpeza pos-recompute: tax_ids=[] nas product lines + unlink das tax lines + "
          f"zera l10n_br_*_valor + calcular_imposto=False")
    print(f"\n  {len(terceiros)} linhas 5902 a criar (op {OP_5902}, price=standard p/ ESTE teste — "
          f"price real (remessa) = Task #2):")
    for f in sorted(terceiros, key=lambda x: x['code'] or ''):
        print(f"     [{f['code']}] {f['name']:34} qty={f['qty']} price={f['price']}")

    if not args.confirmar:
        print("\n  [DRY-RUN] nada escrito no Odoo. Com 'go': --confirmar")
        return

    # ---- montagem + limpeza via server action ----
    linhas_py = "[" + ",".join(f"({f['product_id']},{f['qty']},{f['price']})" for f in terceiros) + "]"
    code = (
        "move = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').create({\n"
        "    'move_type':'out_invoice','journal_id':%d,'partner_id':%d,'company_id':5,\n"
        "    'l10n_br_tipo_pedido':'%s','l10n_br_operacao_id':%d,'fiscal_position_id':%d,\n"
        "    'l10n_br_calcular_imposto':False,'invoice_date': datetime.date.today()})\n"
        "criadas=0; erros=[]\n"
        "for (pid,qty,pu) in %s:\n"
        "    try:\n"
        "        env['account.move.line'].sudo().with_context(allowed_company_ids=[5], check_move_validity=False).create({\n"
        "            'move_id':move.id,'product_id':pid,'quantity':qty,\n"
        "            'l10n_br_operacao_id':%d,'l10n_br_operacao_manual':True,'price_unit':pu})\n"
        "        criadas+=1\n"
        "    except Exception as e:\n"
        "        erros.append('%%s:%%s'%%(pid,str(e)[:50]))\n"
        # recompute -> deriva cfop/CST/conta (e gera tax lixo, que limpamos depois)
        "try:\n"
        "    move.onchange_l10n_br_calcular_imposto(); move.onchange_l10n_br_calcular_imposto_btn()\n"
        "except Exception as e:\n"
        "    log('S30 recompute erro: %%s'%%str(e)[:140])\n"
        # remap de conta (fp do move reseta no recompute) -> 1150100012 (igual s24)
        "amap = {}\n"
        "for fa in env['account.fiscal.position.account'].sudo().search([('position_id','=',%d)]):\n"
        "    amap[fa.account_src_id.id] = fa.account_dest_id.id\n"
        "remap = 0\n"
        "for l in move.invoice_line_ids.filtered(lambda x: x.display_type=='product'):\n"
        "    dest = amap.get(l.account_id.id)\n"
        "    if dest and dest != l.account_id.id:\n"
        "        l.with_context(check_move_validity=False).write({'account_id': dest}); remap += 1\n"
        # ---- LIMPEZA do imposto (retorno 5902 NAO tem ICMS/PIS/COFINS) ----
        "tax_before = move.amount_tax\n"
        "prod = move.invoice_line_ids.filtered(lambda l: l.display_type=='product')\n"
        "zera = ['l10n_br_icms_valor','l10n_br_icms_base','l10n_br_pis_valor','l10n_br_pis_base',\n"
        "        'l10n_br_cofins_valor','l10n_br_cofins_base','l10n_br_ipi_valor','l10n_br_ipi_base']\n"
        "for l in prod:\n"
        "    vals = {'tax_ids':[(5,0,0)]}\n"
        "    for fn in zera:\n"
        "        if fn in l._fields: vals[fn]=0.0\n"
        "    l.with_context(check_move_validity=False).write(vals)\n"
        "tl = move.line_ids.filtered(lambda l: l.display_type=='tax')\n"
        "n_tl = len(tl)\n"
        "tl.with_context(check_move_validity=False).unlink()\n"
        "move.with_context(check_move_validity=False).write({'l10n_br_calcular_imposto':False})\n"
        # medicao
        "pl = move.invoice_line_ids.filtered(lambda l: l.display_type=='product')\n"
        "cfops = dict((c, list(pl.mapped('l10n_br_cfop_codigo')).count(c)) for c in set(pl.mapped('l10n_br_cfop_codigo')))\n"
        "csts = dict((c, list(pl.mapped('l10n_br_icms_cst')).count(c)) for c in set(pl.mapped('l10n_br_icms_cst')))\n"
        "contas = sorted(set(pl.mapped('account_id.code')))\n"
        "n_tax_ids = sum(len(l.tax_ids) for l in pl)\n"
        "n_tax_lines = len(move.line_ids.filtered(lambda l: l.display_type=='tax'))\n"
        "log('S30-RESULT inv=%%s criadas=%%s linhas=%%s cfops=%%s csts=%%s contas=%%s untax=%%s tax_before=%%s tax_after=%%s total=%%s tax_ids=%%s tax_lines=%%s tl_removidas=%%s remap=%%s erros=%%s' %% (str(move.ids), criadas, len(pl), str(cfops), str(csts), str(contas), move.amount_untaxed, tax_before, move.amount_tax, move.amount_total, n_tax_ids, n_tax_lines, n_tl, remap, str(erros[:3])))\n"
    ) % (J_RETIND, PARTNER_FB, TIPO_PEDIDO, OP_5902, FP_RETIND, linhas_py, OP_5902, FP_RETIND)

    model_id = o.execute_kw('ir.model', 'search', [[('model', '=', 'account.move')]], {'context': CTX})[0]
    print("\n  [1] criando server action de teste...")
    sa = o.execute_kw('ir.actions.server', 'create',
                      [{'name': 'ZZ TESTE S30 NF-INSUMOS SEM IMPOSTO - DELETAR', 'model_id': model_id,
                        'state': 'code', 'code': code}], {'context': CTX})
    print(f"      SA {sa} criada; executando...")
    try:
        o.execute_kw('ir.actions.server', 'run', [[sa]],
                     {'context': dict(CTX, active_model='account.move', active_id=False, active_ids=[])})
    except Exception as e:
        print(f"      SA run aviso: {str(e)[:160]}")
    rec = rr('account.move', [('journal_id', '=', J_RETIND), ('state', '=', 'draft')],
             ['id'], order='id desc', limit=1)
    nf_id = rec[0]['id'] if rec else None
    lg = rr('ir.logging', [('message', '=like', 'S30-RESULT%')], ['message'], order='id desc', limit=1)
    if lg:
        print(f"\n  LOG: {lg[0]['message'][:480]}")
    o.execute_kw('ir.actions.server', 'unlink', [[sa]], {'context': CTX})
    print(f"  SA {sa} DELETADA")
    if nf_id:
        hl = rr('account.move', [('id', '=', nf_id)],
                ['amount_untaxed', 'amount_tax', 'amount_total', 'l10n_br_calcular_imposto'])
        nl = rr('account.move.line', [('move_id', '=', nf_id), ('display_type', '=', 'product')],
                ['l10n_br_cfop_codigo', 'l10n_br_icms_cst', 'tax_ids', 'account_id'])
        h = hl[0] if hl else {}
        ok_tax = (h.get('amount_tax') == 0) and all(not x.get('tax_ids') for x in nl)
        ok_cfop = all(str(x.get('l10n_br_cfop_codigo')) == '5902' for x in nl)
        ok_cst = all(str(x.get('l10n_br_icms_cst')) == '50' for x in nl)
        ok_conta = all(CONTA_ALVO in m2o(x.get('account_id')) for x in nl)
        print(f"\n  >>> NF-insumos {nf_id}: {len(nl)} linhas | untax={h.get('amount_untaxed')} "
              f"tax={h.get('amount_tax')} total={h.get('amount_total')} calcular_imposto={h.get('l10n_br_calcular_imposto')}")
        print(f"      CFOPs={dict(Counter(str(x.get('l10n_br_cfop_codigo')) for x in nl))} "
              f"CST={dict(Counter(str(x.get('l10n_br_icms_cst')) for x in nl))} "
              f"tax_ids_total={sum(len(x.get('tax_ids') or []) for x in nl)}")
        print(f"      GATES: imposto_zerado={'✅' if ok_tax else '❌'} cfop5902={'✅' if ok_cfop else '❌'} "
              f"cst50={'✅' if ok_cst else '❌'} conta{CONTA_ALVO}={'✅' if ok_conta else '❌'}")
        print(f"  >>> limpar: --cleanup {nf_id}")


if __name__ == '__main__':
    main()
