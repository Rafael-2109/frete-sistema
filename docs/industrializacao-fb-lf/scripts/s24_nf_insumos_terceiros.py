#!/usr/bin/env python3
"""S24 — NF-INSUMOS (5902) com fonte = MATERIAIS DE TERCEIROS (estrategia firmada
2026-06-13). Sucessor do s18: troca a fonte de "remessa" -> "materiais de terceiros
via BoM/MO", EXCLUINDO agua (consumo local) e semis. Cobaia = shoyu 4870112 (que o
s18/remessa nao cobria por nao ter BoM subcontract; aqui usa a BoM normal explodida).

A fonte:
  - explode a BoM do PA recursivamente ate as folhas (= s23: 17 folhas, inclui AGUA);
  - FILTRO p/ materiais de terceiros: exclui type='consu'/'service' (agua e' consumo
    local) -> deve dar os 16 que a NF real tem.
  - VALIDA contra a NF de retorno REAL (709632): os 16 produtos batem?

READ-only no dry-run. Montagem (--confirmar) = server action que cria a NF-insumos no
RETIND 1083 (op 2864) + recompute; draft, sem SEFAZ; --cleanup deleta. Go por escrita.

MODOS:
  (sem flag)      dry-run: explode + filtra + valida vs NF real + lista os 16
  --confirmar     SA cria NF-insumos draft no RETIND 1083 + N x 5902 (op 2864) + recompute
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
TIPO_PEDIDO = 'venda-industrializacao'   # tipo_pedido da op 2864 (header precisa p/ recompute)
FP_RETIND = 111                          # fiscal_position SAIDA SERVICO INDUSTRIALIZACAO (comporta 5902)
NF_RETORNO_REAL = 709632   # VND real do shoyu: 1x5124 + 16x5902 (validacao)


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def explode_bom(o, rr, tmpl_id, fator, folhas):
    """Explode a BoM recursivamente; acumula folhas {product_id: qty} (sem BoM propria)."""
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
            explode_bom(o, rr, ctmpl, q, folhas)   # semi -> desce um nivel
        else:
            folhas[cid] = folhas.get(cid, 0.0) + q
    return True


def montar_fonte(o, rr):
    """Retorna lista de materiais de TERCEIROS (folhas estocaveis): [{product_id, qty, code, name, type, price}]."""
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
    terceiros = [f for f in fonte if f['type'] == 'product']   # exclui consu (agua) / service
    excluidos = [f for f in fonte if f['type'] != 'product']

    print("=" * 90)
    print(f"S24 — NF-INSUMOS do shoyu {COD_PA}: fonte = MATERIAIS DE TERCEIROS (BoM explodida, exclui consu)")
    print("=" * 90)
    print(f"  BoM explodida = {len(fonte)} folhas | terceiros(type=product) = {len(terceiros)} | "
          f"excluidos(consu/service) = {len(excluidos)}")
    if excluidos:
        for e in excluidos:
            print(f"     EXCLUIDO: [{e['code']}] {e['name']} type={e['type']} qty={e['qty']}")

    # validacao vs NF real
    real = rr('account.move.line', [('move_id', '=', NF_RETORNO_REAL), ('display_type', '=', 'product'),
                                    ('l10n_br_cfop_codigo', '=', '5902')], ['product_id'])
    real_ids = {l['product_id'][0] for l in real}
    fonte_ids = {f['product_id'] for f in terceiros}
    print(f"\n  VALIDACAO vs NF real {NF_RETORNO_REAL}: real={len(real_ids)} 5902 | fonte={len(fonte_ids)}")
    falta = real_ids - fonte_ids
    sobra = fonte_ids - real_ids
    print(f"     na NF real mas NAO na fonte: {falta or 'nenhum'}")
    print(f"     na fonte mas NAO na NF real: {sobra or 'nenhum'}")
    print(f"     {'✅ MATCH EXATO' if not falta and not sobra else '⚠️ DIVERGENCIA — ajustar filtro'}")

    print(f"\n  {len(terceiros)} linhas 5902 a criar (op {OP_5902}, qty teorica × 1 PA, price=standard p/ teste):")
    for f in sorted(terceiros, key=lambda x: x['code'] or ''):
        print(f"     [{f['code']}] {f['name']:34} qty={f['qty']} price={f['price']}")

    if not args.confirmar:
        print("\n  [DRY-RUN] nada escrito no Odoo. Com 'go': --confirmar")
        return

    # ---- montagem via server action ----
    linhas_py = "[" + ",".join(f"({f['product_id']},{f['qty']},{f['price']})" for f in terceiros) + "]"
    code = (
        "move = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').create({\n"
        "    'move_type':'out_invoice','journal_id':%d,'partner_id':%d,'company_id':5,\n"
        "    'l10n_br_tipo_pedido':'%s','l10n_br_operacao_id':%d,'fiscal_position_id':%d,\n"
        "    'invoice_date': datetime.date.today()})\n"
        "criadas=0; erros=[]\n"
        "for (pid,qty,pu) in %s:\n"
        "    try:\n"
        "        env['account.move.line'].sudo().with_context(allowed_company_ids=[5], check_move_validity=False).create({\n"
        "            'move_id':move.id,'product_id':pid,'quantity':qty,\n"
        "            'l10n_br_operacao_id':%d,'l10n_br_operacao_manual':True,'price_unit':pu})\n"
        "        criadas+=1\n"
        "    except Exception as e:\n"
        "        erros.append('%%s:%%s'%%(pid,str(e)[:50]))\n"
        "try:\n"
        "    move.onchange_l10n_br_calcular_imposto(); move.onchange_l10n_br_calcular_imposto_btn()\n"
        "except Exception as e:\n"
        "    log('S24 recompute erro: %%s'%%str(e)[:140])\n"
        "amap = {}\n"   # fp do move reseta p/ False no recompute -> usar a fp fixa (mapeamento oficial)
        "for fa in env['account.fiscal.position.account'].sudo().search([('position_id','=',%d)]):\n"
        "    amap[fa.account_src_id.id] = fa.account_dest_id.id\n"
        "remap = 0\n"
        "for l in move.invoice_line_ids.filtered(lambda x: x.display_type=='product'):\n"
        "    dest = amap.get(l.account_id.id)\n"
        "    if dest and dest != l.account_id.id:\n"
        "        l.with_context(check_move_validity=False).write({'account_id': dest}); remap += 1\n"
        "log('S24 remap_conta=%%s amap=%%s' %% (remap, str(amap)))\n"
        "pl = move.invoice_line_ids.filtered(lambda l: l.display_type=='product')\n"
        "cfops = dict((c, list(pl.mapped('l10n_br_cfop_codigo')).count(c)) for c in set(pl.mapped('l10n_br_cfop_codigo')))\n"
        "csts = dict((c, list(pl.mapped('l10n_br_icms_cst')).count(c)) for c in set(pl.mapped('l10n_br_icms_cst')))\n"
        "contas = sorted(set(pl.mapped('account_id.code')))\n"
        "log('S24-RESULT inv=%%s criadas=%%s total=%%s cfops=%%s csts=%%s contas=%%s amount=%%s erros=%%s' %% (str(move.ids), criadas, len(pl), str(cfops), str(csts), str(contas), move.amount_total, str(erros[:3])))\n"
    ) % (J_RETIND, PARTNER_FB, TIPO_PEDIDO, OP_5902, FP_RETIND, linhas_py, OP_5902, FP_RETIND)

    model_id = o.execute_kw('ir.model', 'search', [[('model', '=', 'account.move')]], {'context': CTX})[0]
    print("\n  [1] criando server action de teste...")
    sa = o.execute_kw('ir.actions.server', 'create',
                      [{'name': 'ZZ TESTE S24 NF-INSUMOS TERCEIROS - DELETAR', 'model_id': model_id,
                        'state': 'code', 'code': code}], {'context': CTX})
    print(f"      SA {sa} criada; executando...")
    try:
        o.execute_kw('ir.actions.server', 'run', [[sa]],
                     {'context': dict(CTX, active_model='account.move', active_id=False, active_ids=[])})
    except Exception as e:
        print(f"      SA run aviso: {str(e)[:160]}")
    # captura ROBUSTA: a NF recem-criada = draft mais recente no RETIND 1083
    # (o ir.logging acumula S24-RESULT de rodadas anteriores -> nao confiavel p/ id)
    rec = rr('account.move', [('journal_id', '=', J_RETIND), ('state', '=', 'draft')],
             ['id'], order='id desc', limit=1)
    nf_id = rec[0]['id'] if rec else None
    lg = rr('ir.logging', [('message', '=like', 'S24-RESULT%')], ['message'], order='id desc', limit=1)
    if lg:
        print(f"  LOG: {lg[0]['message'][:320]}")
    o.execute_kw('ir.actions.server', 'unlink', [[sa]], {'context': CTX})
    print(f"  SA {sa} DELETADA")
    if nf_id:
        nl = rr('account.move.line', [('move_id', '=', nf_id), ('display_type', '=', 'product')],
                ['l10n_br_cfop_codigo', 'l10n_br_icms_cst'])
        print(f"\n  >>> NF-insumos {nf_id}: {len(nl)} linhas | "
              f"CFOPs={dict(Counter(str(x.get('l10n_br_cfop_codigo')) for x in nl))} "
              f"CST={dict(Counter(str(x.get('l10n_br_icms_cst')) for x in nl))}")
        print(f"  >>> limpar: --cleanup {nf_id}")


if __name__ == '__main__':
    main()
