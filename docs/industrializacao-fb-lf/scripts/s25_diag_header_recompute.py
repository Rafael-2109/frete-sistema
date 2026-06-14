#!/usr/bin/env python3
"""S25 — diagnostico: por que o recompute nao computou cfop/CST na NF-insumos nua?
Compara o HEADER + 1 linha de 3 NFs: a nossa nua (788273), a SARET separada real
(725475) e a mista real (709632). Revela quais campos do HEADER (tipo_pedido /
operacao / fiscal_position / documento) o CIEL IT precisa p/ derivar 5902/CST 50,
e se a LINHA precisa de l10n_br_operacao_manual=True. READ-ONLY.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NFS = {'NUA-788273': 788273, 'SARET-725475': 725475, 'MISTA-709632': 709632}


def m2o(v):
    return f"{v[0]}|{str(v[1])[:24]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    mf = o.execute_kw('account.move', 'fields_get', [], {'attributes': ['type'], 'context': CTX})
    hwant = [f for f in ['name', 'journal_id', 'l10n_br_tipo_pedido', 'l10n_br_operacao_id',
                         'fiscal_position_id', 'l10n_br_fiscal_position_id', 'l10n_br_documento_id',
                         'l10n_br_cfop_id', 'move_type', 'l10n_br_calcular_imposto', 'state'] if f in mf]
    lf = o.execute_kw('account.move.line', 'fields_get', [], {'attributes': ['type'], 'context': CTX})
    lwant = [f for f in ['product_id', 'l10n_br_operacao_id', 'l10n_br_operacao_manual',
                         'l10n_br_cfop_codigo', 'l10n_br_icms_cst', 'account_id',
                         'l10n_br_tipo_pedido', 'l10n_br_calcular_imposto'] if f in lf]

    for label, nf in NFS.items():
        h = rd('account.move', [nf], hwant)
        if not h:
            print(f"\n### {label}: NF nao existe (talvez ja limpa)"); continue
        h = h[0]
        print(f"\n{'='*84}\n### {label} — HEADER")
        for k in hwant:
            v = h.get(k)
            if v not in (False, None, '', []):
                print(f"   {k} = {m2o(v) if isinstance(v, list) else v}")
        ln = o.execute_kw('account.move.line', 'search_read',
                          [[('move_id', '=', nf), ('display_type', '=', 'product')]],
                          {'fields': lwant, 'context': CTX, 'limit': 1, 'order': 'id'})
        if ln:
            print(f"   --- 1a linha-produto ---")
            for k in lwant:
                print(f"      {k} = {m2o(ln[0].get(k)) if isinstance(ln[0].get(k), list) else ln[0].get(k)}")


if __name__ == '__main__':
    main()
