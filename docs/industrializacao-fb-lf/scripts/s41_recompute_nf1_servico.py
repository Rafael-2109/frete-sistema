#!/usr/bin/env python3
"""S41 — CORRECAO: materializar as tax lines de PIS/COFINS na NF-1 servico (789484) via
recompute server-side. A SA s37 fez create_invoice (linha 5124 + tax_ids vinculados +
vNF=28,91) MAS nao rodou o recompute -> as tax lines (display_type='tax') nao foram
criadas -> ao postar: D 28,91 (CLIENTES) != C 27,57 (receita), falta C 1,34 (PIS/COFINS).

Roda onchange_l10n_br_calcular_imposto[_btn] na NF-1 (server-side persiste) -> materializa
as tax lines -> equilibra. Draft, NAO posta. Reversivel.

MODOS:
  (sem flag)   READ: estado atual da NF-1 (linhas, equilibrio)
  --executar   SA roda o recompute na NF-1 + mede equilibrio
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF1 = 789484


def m2o(v):
    return f"{v[0]}|{str(v[1])[:22]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--executar', action='store_true')
    args = ap.parse_args()
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    def mostrar(tag):
        h = rr('account.move', [('id', '=', NF1)],
               ['name', 'state', 'amount_untaxed', 'amount_tax', 'amount_total',
                'l10n_br_total_nfe', 'l10n_br_calcular_imposto'])[0]
        lns = rr('account.move.line', [('move_id', '=', NF1)],
                 ['display_type', 'account_id', 'debit', 'credit', 'tax_line_id'], order='id')
        tot_d = round(sum(l['debit'] for l in lns), 2); tot_c = round(sum(l['credit'] for l in lns), 2)
        ntax = sum(1 for l in lns if l.get('display_type') == 'tax')
        print(f"  [{tag}] state={h['state']} untax={h['amount_untaxed']} tax={h['amount_tax']} "
              f"total={h['amount_total']} vNF={h['l10n_br_total_nfe']} calc_imp={h['l10n_br_calcular_imposto']}")
        print(f"        {len(lns)} linhas ({ntax} tax) | D={tot_d} C={tot_c} | equilibrio={'✅' if abs(tot_d-tot_c)<0.01 else '❌ falta '+str(round(tot_d-tot_c,2))}")
        for l in lns:
            print(f"          [{l.get('display_type') or 'lancto':12}] {m2o(l.get('account_id')):26} D={l['debit']} C={l['credit']} taxline={m2o(l.get('tax_line_id'))}")
        return abs(tot_d - tot_c) < 0.01, ntax

    print("=" * 88)
    print("S41 — recompute NF-1 servico (materializa tax lines PIS/COFINS)")
    print("=" * 88)
    print("ANTES:")
    mostrar('antes')

    if not args.executar:
        print("\n  [DRY-RUN] nada escrito. Aplicar: --executar")
        return

    code = (
        "m = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').browse(%d)\n"
        "try:\n"
        "    m.onchange_l10n_br_calcular_imposto(); m.onchange_l10n_br_calcular_imposto_btn()\n"
        "except Exception as e:\n"
        "    log('S41 recompute erro: %%s'%%str(e)[:140])\n"
        "tl = m.line_ids.filtered(lambda l: l.display_type=='tax')\n"
        "td = sum(m.line_ids.mapped('debit')); tc = sum(m.line_ids.mapped('credit'))\n"
        "log('S41-RESULT inv=%%s tax=%%s total=%%s vNF=%%s n_tax=%%s D=%%s C=%%s eq=%%s calc_imp=%%s' %% (str(m.ids), m.amount_tax, m.amount_total, m.l10n_br_total_nfe, len(tl), round(td,2), round(tc,2), abs(td-tc)<0.01, m.l10n_br_calcular_imposto))\n"
    ) % NF1
    model_id = o.execute_kw('ir.model', 'search', [[('model', '=', 'account.move')]], {'context': CTX})[0]
    sa = o.execute_kw('ir.actions.server', 'create',
                      [{'name': 'ZZ TESTE S41 RECOMPUTE NF1 - DELETAR', 'model_id': model_id,
                        'state': 'code', 'code': code}], {'context': CTX})
    print(f"\n  SA {sa} criada; rodando recompute na NF-1...")
    try:
        o.execute_kw('ir.actions.server', 'run', [[sa]],
                     {'context': dict(CTX, active_model='account.move', active_id=False, active_ids=[])})
    except Exception as e:
        print(f"  SA run aviso: {str(e)[:160]}")
    lg = rr('ir.logging', [('message', '=like', 'S41-RESULT%')], ['message'], order='id desc', limit=1)
    if lg:
        print(f"  LOG: {lg[0]['message'][:300]}")
    o.execute_kw('ir.actions.server', 'unlink', [[sa]], {'context': CTX})
    print(f"  SA {sa} DELETADA\n\nDEPOIS:")
    eq, ntax = mostrar('depois')
    print(f"\n  >>> {'✅ NF-1 EQUILIBRADA — postavel' if eq and ntax > 0 else '❌ ainda desequilibrada — investigar'}")


if __name__ == '__main__':
    main()
