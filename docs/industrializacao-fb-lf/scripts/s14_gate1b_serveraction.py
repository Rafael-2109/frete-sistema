#!/usr/bin/env python3
"""S14 — GATE 1b: prova que a expansao dos 5902 e SERVER-SIDE.

Cria uma ir.actions.server (state=code) que replica o robo 1512 (create_invoice +
onchange_l10n_br_calcular_imposto(_btn)) num picking de retorno, roda server-side,
e mede se a NF expande (1x5124 -> 1x5124 + Nx5902). SEM action_post, SEM SEFAZ.

REVERSIVEL: a SA e DELETADA no fim; a NF draft + picking devem ser revertidos via
`s11 --revert`. Autorizado por Rafael (2026-06-13) — criar/rodar codigo em Odoo PROD.

MODOS:
  --rodar PICK_ID   cria a SA + roda no picking + mede a NF gerada + DELETA a SA
  --cleanup-sa      deleta qualquer SA de teste residual (ZZ TESTE GATE1B%)
"""
import sys
import argparse
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5}
J847 = 847


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and len(v) == 2 and isinstance(v[1], str) else v


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
        sas = rr('ir.actions.server', [('name', 'like', 'ZZ TESTE GATE1B%')], ['id', 'name'])
        for s in sas:
            o.execute_kw('ir.actions.server', 'unlink', [[s['id']]], {'context': CTX})
            print(f"  SA {s['id']} '{s['name']}' DELETADA")
        if not sas:
            print("  nenhuma SA de teste residual")
        return

    if not args.rodar:
        print("uso: --rodar PICK_ID  |  --cleanup-sa")
        return

    pick = args.rodar
    # code da SA: replica o robo 1512 FIELMENTE (sudo, lang, journal por tipo_pedido,
    # create_invoice + onchange + action_post) e mede ONDE expande (n0/n1/n2).
    code = (
        "pk = env['stock.picking'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').browse(%d)\n"
        "jr = env['account.journal'].with_context(allowed_company_ids=[5]).search([('company_id','=',5),('type','=','sale'),('l10n_br_tipo_pedido','=',pk.picking_type_id.l10n_br_tipo_pedido)], limit=1)\n"
        "wiz = env['stock.invoice.onshipping'].with_context(active_ids=[%d], allowed_company_ids=[5], lang='pt_BR').create({'company_id': 5, 'journal_id': jr.id})\n"
        "inv = wiz.create_invoice()\n"
        "move = env['account.move'].sudo().with_context(lang='pt_BR').browse(inv)\n"
        "npl = lambda m: len(m.invoice_line_ids.filtered(lambda l: l.display_type=='product'))\n"
        "n0 = npl(move)\n"
        "try:\n"
        "    move.onchange_l10n_br_calcular_imposto(); move.onchange_l10n_br_calcular_imposto_btn()\n"
        "except Exception as e:\n"
        "    log('GATE1B-SA onchange erro: %%s' %% str(e)[:120])\n"
        "n1 = npl(move)\n"
        "pl = move.invoice_line_ids.filtered(lambda l: l.display_type=='product')\n"
        "log('GATE1B-SA-RESULT inv=%%s journal=%%s n0_create=%%s n1_onchange=%%s cfops=%%s' %% (str(move.ids), jr.id, n0, n1, str(pl.mapped('l10n_br_cfop_codigo'))))\n"
    ) % (pick, pick, )

    model_id = o.execute_kw('ir.model', 'search', [[('model', '=', 'account.move')]], {'context': CTX})[0]
    print(f"=== GATE 1b SERVER ACTION (picking {pick}) ===")
    sa = o.execute_kw('ir.actions.server', 'create',
                      [{'name': 'ZZ TESTE GATE1B SA - DELETAR', 'model_id': model_id,
                        'state': 'code', 'code': code}], {'context': CTX})
    print(f"  SA criada: {sa}")
    try:
        o.execute_kw('ir.actions.server', 'run', [[sa]],
                     {'context': dict(CTX, active_model='account.move', active_id=False, active_ids=[])})
        print("  SA executada (server-side).")
    except Exception as e:
        print(f"  SA run aviso: {str(e)[:160]}")

    # ler o log + medir a NF gerada (via picking.invoice_id)
    logs = rr('ir.logging', [('message', 'like', 'GATE1B-SA%')], ['message'], order='id desc', limit=4)
    for lg in logs:
        print(f"  LOG: {lg['message'][:200]}")
    pf = o.execute_kw('stock.picking', 'fields_get', [], {'attributes': [], 'context': CTX})
    fl = [x for x in ['invoice_id', 'invoice_ids'] if x in pf]
    p = o.execute_kw('stock.picking', 'read', [[pick]], {'fields': fl, 'context': CTX})[0]
    inv_ids = ([p['invoice_id'][0]] if p.get('invoice_id') else []) + (p.get('invoice_ids') or [])
    print(f"  picking.invoice: {inv_ids}")
    for mv in inv_ids:
        nl = rr('account.move.line', [('move_id', '=', mv), ('display_type', '=', 'product')],
                ['l10n_br_cfop_codigo'])
        print(f"  >>> NF {mv}: {len(nl)} linhas-produto | CFOPs={dict(Counter(str(x.get('l10n_br_cfop_codigo')) for x in nl))}")

    # deletar a SA (nao deixar rabo)
    o.execute_kw('ir.actions.server', 'unlink', [[sa]], {'context': CTX})
    print(f"  SA {sa} DELETADA")
    if inv_ids:
        print(f"  >>> reverter: s11 --revert {pick} {' '.join(map(str, inv_ids))} --produto <P> --lote <L> --src <S>")


if __name__ == '__main__':
    main()
