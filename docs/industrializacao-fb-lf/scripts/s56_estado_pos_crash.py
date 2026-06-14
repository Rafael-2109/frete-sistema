#!/usr/bin/env python3
"""S56 — ESTADO AO VIVO pos-crash (READ-only). O PC desligou logo apos a saga s54 (NF-1
rejeitada na SEFAZ: 'Dados de cobranca nao devem ser informados para pagamento a vista').
Confirma o estado REAL no Odoo (servidor) das 2 NFs + picking + saldo PASSIVA.
READ-ONLY.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF1, NF2 = 791437, 791441
PICK = 325346
ACC_PASSIVA = 26667


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    F = ['name', 'state', 'l10n_br_situacao_nf', 'l10n_br_cstat_nf', 'l10n_br_chave_nf',
         'l10n_br_xmotivo_nf', 'amount_total', 'l10n_br_total_nfe', 'invoice_incoterm_id',
         'payment_provider_id', 'l10n_br_carrier_id']

    print("=" * 96)
    print("S56 — ESTADO AO VIVO pos-crash (Odoo = fonte da verdade)")
    print("=" * 96)
    for label, nf in [('NF-1 servico', NF1), ('NF-2 insumos', NF2)]:
        h = rd('account.move', [nf], F)
        if not h:
            print(f"  {label} {nf}: INEXISTENTE"); continue
        h = h[0]
        chave = h.get('l10n_br_chave_nf')
        print(f"\n  {label} {nf} — {h.get('name')}")
        print(f"    state={h['state']} | situacao_nf={h.get('l10n_br_situacao_nf')} | cstat={h.get('l10n_br_cstat_nf') or '-'}")
        print(f"    chave={chave or '-'} ({'44d AUTORIZADA' if chave and len(str(chave))==44 else 'sem chave valida'})")
        print(f"    xmotivo={h.get('l10n_br_xmotivo_nf') or '-'}")
        print(f"    total={h.get('amount_total')} vNF={h.get('l10n_br_total_nfe')} "
              f"incoterm={h.get('invoice_incoterm_id')} pag={h.get('payment_provider_id')}")

    # picking
    p = rd('stock.picking', [PICK], ['name', 'state'])
    print(f"\n  PICKING {PICK}: {p[0].get('name') if p else 'INEXISTENTE'} state={p[0].get('state') if p else '-'}")

    # saldo PASSIVA
    lns = rr('account.move.line', [('account_id', '=', ACC_PASSIVA), ('parent_state', '=', 'posted'),
                                   ('company_id', '=', 5)], ['balance'])
    saldo = round(sum(l.get('balance') or 0 for l in lns), 2)
    nfl = rr('account.move.line', [('move_id', '=', NF2), ('account_id', '=', ACC_PASSIVA)], ['debit'])
    debito_nf2 = round(sum(l.get('debit') or 0 for l in nfl), 2)
    print(f"\n  SALDO PASSIVA 5101020001 (26667) = {saldo}")
    print(f"    (D da NF-2 na PASSIVA = {debito_nf2}; baseline pre-Fase-A = -37.749.789,11; pos-baixa = -37.749.509,88)")

    print(f"\n  >>> RESUMO: NF-1 autorizada? {'SIM' if False else 'verificar cstat/chave acima'}; "
          f"as NFs seguem POSTED e reversiveis (cleanup s37) se nao autorizadas.")


if __name__ == '__main__':
    main()
