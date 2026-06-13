#!/usr/bin/env python3
"""S15 — GATE 1c: AUTOMATIZAR o passo manual da Josefa (montar as linhas 5902).

Via SERVER ACTION (decisao Rafael: server-side garante os computes fiscais como o robo):
dado o picking do PA, a SA faz create_invoice (NF do PA, 1x5124) e ENTAO adiciona as
linhas 5902 dos componentes (explode a BoM subcontract do PA), setando a operacao 2864
(Retorno de Industrializacao), e recomputa os impostos. Mede se as linhas ficam
fiscalmente corretas (cfop 5902, CST icms 50). SEM action_post, SEM SEFAZ.

Teste de VIABILIDADE com o azeite 4739099 (tem BoM subcontract 14794 = 9 componentes;
a NF real 738097 tem 9x5902 — o alvo a reproduzir).

REVERSIVEL: SA deletada no fim; NF draft + picking revertidos via `s11 --revert`.
Autorizado por Rafael (2026-06-13) — criar/rodar server action de ESCRITA em PROD.

MODOS:
  --rodar PICK_ID   cria a SA + roda (create_invoice + monta 5902) + mede + DELETA a SA
  --cleanup-sa      deleta SA de teste residual (ZZ TESTE GATE1C%)
"""
import sys
import argparse
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5}
J847 = 847
OP_RETORNO = 2864   # l10n_br_ciel_it_account.operacao "Retorno de Industrializacao por encomenda" (CFOP 5902)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rodar', type=int, metavar='PICK_ID')
    ap.add_argument('--cleanup-sa', action='store_true')
    args = ap.parse_args()

    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, domain, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kw2)

    if args.cleanup_sa:
        for s in rr('ir.actions.server', [('name', 'like', 'ZZ TESTE GATE1C%')], ['id', 'name']):
            o.execute_kw('ir.actions.server', 'unlink', [[s['id']]], {'context': CTX})
            print(f"  SA {s['id']} DELETADA")
        return

    if not args.rodar:
        print("uso: --rodar PICK_ID  |  --cleanup-sa"); return

    pick = args.rodar
    # SA: create_invoice (NF do PA) + explode BoM subcontract + cria linhas 5902 (op 2864) + recompute
    code = (
        "pk = env['stock.picking'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').browse(%d)\n"
        "wiz = env['stock.invoice.onshipping'].with_context(active_ids=[%d], allowed_company_ids=[5], lang='pt_BR').create({'company_id': 5, 'journal_id': %d})\n"
        "inv = wiz.create_invoice()\n"
        "move = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').browse(inv)\n"
        "npl = lambda m: m.invoice_line_ids.filtered(lambda l: l.display_type=='product')\n"
        "n0 = len(npl(move))\n"
        "pa_line = npl(move)[:1]\n"
        "pa_tmpl = pa_line.product_id.product_tmpl_id\n"
        "pa_qty = pa_line.quantity\n"
        "bom = env['mrp.bom'].sudo().search([('product_tmpl_id','=',pa_tmpl.id),('type','=','subcontract')], limit=1)\n"
        "log('GATE1C bom=%%s pa_qty=%%s comps=%%s' %% (bom.id, pa_qty, len(bom.bom_line_ids)))\n"
        "criadas = 0; erros = []\n"
        "for bl in bom.bom_line_ids:\n"
        "    try:\n"
        "        env['account.move.line'].sudo().with_context(allowed_company_ids=[5], check_move_validity=False).create({\n"
        "            'move_id': move.id, 'product_id': bl.product_id.id,\n"
        "            'quantity': bl.product_qty * pa_qty, 'l10n_br_operacao_id': %d,\n"
        "            'price_unit': bl.product_id.standard_price or 0.01,\n"
        "        })\n"
        "        criadas += 1\n"
        "    except Exception as e:\n"
        "        erros.append('%%s:%%s' %% (bl.product_id.default_code, str(e)[:60]))\n"
        "try:\n"
        "    move.onchange_l10n_br_calcular_imposto(); move.onchange_l10n_br_calcular_imposto_btn()\n"
        "except Exception as e:\n"
        "    log('GATE1C recompute erro: %%s' %% str(e)[:120])\n"
        "pl = npl(move)\n"
        "log('GATE1C-RESULT inv=%%s n0=%%s criadas=%%s total=%%s cfops=%%s csts=%%s erros=%%s' %% (str(move.ids), n0, criadas, len(pl), str(dict((c, list(pl.mapped('l10n_br_cfop_codigo')).count(c)) for c in set(pl.mapped('l10n_br_cfop_codigo')))), str(set(pl.mapped('l10n_br_icms_cst'))), str(erros[:3])))\n"
    ) % (pick, pick, J847, OP_RETORNO)

    model_id = o.execute_kw('ir.model', 'search', [[('model', '=', 'account.move')]], {'context': CTX})[0]
    print(f"=== GATE 1c — montar 5902 via server action (picking {pick}) ===")
    sa = o.execute_kw('ir.actions.server', 'create',
                      [{'name': 'ZZ TESTE GATE1C SA - DELETAR', 'model_id': model_id,
                        'state': 'code', 'code': code}], {'context': CTX})
    print(f"  SA criada: {sa}")
    try:
        o.execute_kw('ir.actions.server', 'run', [[sa]],
                     {'context': dict(CTX, active_model='account.move', active_id=False, active_ids=[])})
        print("  SA executada.")
    except Exception as e:
        print(f"  SA run aviso: {str(e)[:160]}")

    for lg in rr('ir.logging', [('message', 'like', 'GATE1C%')], ['message'], order='id desc', limit=5):
        print(f"  LOG: {lg['message'][:240]}")
    pf = o.execute_kw('stock.picking', 'fields_get', [], {'attributes': [], 'context': CTX})
    fl = [x for x in ['invoice_id', 'invoice_ids'] if x in pf]
    p = o.execute_kw('stock.picking', 'read', [[pick]], {'fields': fl, 'context': CTX})[0]
    inv_ids = ([p['invoice_id'][0]] if p.get('invoice_id') else []) + (p.get('invoice_ids') or [])
    for mv in inv_ids:
        nl = rr('account.move.line', [('move_id', '=', mv), ('display_type', '=', 'product')],
                ['l10n_br_cfop_codigo', 'l10n_br_icms_cst', 'l10n_br_operacao_id'])
        print(f"  >>> NF {mv}: {len(nl)} linhas | CFOPs={dict(Counter(str(x.get('l10n_br_cfop_codigo')) for x in nl))} "
              f"CST={dict(Counter(str(x.get('l10n_br_icms_cst')) for x in nl))}")
    o.execute_kw('ir.actions.server', 'unlink', [[sa]], {'context': CTX})
    print(f"  SA {sa} DELETADA")
    if inv_ids:
        print(f"  >>> reverter: s11 --revert {pick} {' '.join(map(str, inv_ids))} --produto 27753 --lote 61176 --src 42")


if __name__ == '__main__':
    main()
