#!/usr/bin/env python3
"""G9 CASO (READ-ONLY) — disseca 1 NF de retorno de abril/2026 (lado LF j847) ponta a ponta.

Para o item C (testar a correcao num caso real). Mede:
  1) lista NFs de retorno de abr/2026 (com 5902) p/ escolher 1 tipica;
  2) detalha a NF escolhida: header + TODAS as account.move.line (conta, op, cfop, D/C);
  3) lock dates contabeis (company 1 FB e 5 LF) — periodo fechado bloqueia lancamento retroativo;
  4) acha a entrada FB correspondente pela chave NFe (escrituracao do retorno) + suas linhas;
  5) stock moves/valuation ligados a NF FB (double-count de estoque).
NAO escreve nada.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
OPS_5902 = [2864, 2710]


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v in (False, None) else str(v)


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}\n")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    # ===== 3) LOCK DATES (faz primeiro — define se da' p/ lancar retroativo) =====
    print("=" * 70)
    print("LOCK DATES contabeis")
    print("=" * 70)
    comps = rr('res.company', [('id', 'in', [1, 5])],
               ['id', 'name', 'fiscalyear_lock_date', 'period_lock_date',
                'tax_lock_date'])
    for c in comps:
        print(f"  company {c['id']} {c['name']}")
        print(f"     fiscalyear_lock_date (geral): {c.get('fiscalyear_lock_date')}")
        print(f"     period_lock_date (usuarios) : {c.get('period_lock_date')}")
        print(f"     tax_lock_date               : {c.get('tax_lock_date')}")

    # ===== 1) NFs de retorno abr/2026 =====
    print("\n" + "=" * 70)
    print("NFs j847 retorno abr/2026 (amostra p/ escolher)")
    print("=" * 70)
    moves = rr('account.move',
               [('journal_id', '=', 847), ('company_id', '=', 5), ('state', '=', 'posted'),
                ('move_type', '=', 'out_invoice'),
                ('date', '>=', '2026-04-01'), ('date', '<=', '2026-04-30')],
               ['id', 'name', 'date', 'partner_id', 'amount_total', 'amount_untaxed',
                'l10n_br_chave_nf', 'invoice_origin'],
               limit=12, order='amount_total asc')
    for m in moves:
        print(f"  id={m['id']:7} {m['name']:20} {m['date']} total R$ {m['amount_total']:>12,.2f}  chave={str(m.get('l10n_br_chave_nf'))[:20]}")

    if not moves:
        print("  (nenhuma) — abortando detalhe")
        return

    # escolher uma tipica: a do meio da lista por valor
    chosen = moves[len(moves) // 2]
    mid = chosen['id']
    print(f"\n  >>> ESCOLHIDA p/ dissecar: id={mid} {chosen['name']} R$ {chosen['amount_total']:,.2f}")
    print(f"      chave={chosen.get('l10n_br_chave_nf')}  origin={chosen.get('invoice_origin')}")

    # ===== 2) linhas da NF LF =====
    print("\n" + "=" * 70)
    print(f"LINHAS da NF LF id={mid}")
    print("=" * 70)
    lines = rr('account.move.line', [('move_id', '=', mid)],
               ['account_id', 'name', 'l10n_br_operacao_id', 'l10n_br_cfop_id',
                'debit', 'credit', 'product_id', 'quantity', 'display_type'],
               limit=200, order='id')
    td = tc = 0.0
    for ln in lines:
        acc = m2o(ln.get('account_id'))
        op = m2o(ln.get('l10n_br_operacao_id'))
        cfop = m2o(ln.get('l10n_br_cfop_id'))
        d = ln.get('debit') or 0
        c = ln.get('credit') or 0
        td += d
        tc += c
        nm = (ln.get('name') or '')[:22]
        print(f"    acc={acc[:34]:34} op={op[:10]:10} cfop={cfop[:9]:9} D {d:>11,.2f} C {c:>11,.2f} | {nm}")
    print(f"    {'TOTAIS':>50} D {td:>11,.2f} C {tc:>11,.2f}")

    # ===== 4) entrada FB pela chave =====
    chave = chosen.get('l10n_br_chave_nf')
    print("\n" + "=" * 70)
    print(f"ENTRADA FB (company 1) que referencia a chave {str(chave)[:20]}...")
    print("=" * 70)
    fb_moves = []
    if chave:
        fb_moves = rr('account.move',
                      [('company_id', '=', 1), ('l10n_br_chave_nf', '=', chave)],
                      ['id', 'name', 'date', 'move_type', 'state', 'journal_id', 'amount_total'],
                      limit=10)
        if not fb_moves:
            # tentar por dfe / numero
            fb_moves = rr('account.move',
                          [('company_id', '=', 1), ('move_type', '=', 'in_invoice'),
                           ('invoice_origin', 'ilike', str(chosen['name']))],
                          ['id', 'name', 'date', 'move_type', 'state', 'journal_id', 'amount_total'],
                          limit=10)
    for fm in fb_moves:
        print(f"  id={fm['id']:7} {fm['name']:20} {fm['date']} {fm['move_type']:12} {fm['state']:8} j={m2o(fm['journal_id'])[:30]} R$ {fm['amount_total']:,.2f}")
    if not fb_moves:
        print("  (NENHUMA entrada FB achada pela chave/origin) — escrituracao do retorno pode nao existir ou usar outro vinculo")

    # detalhar a primeira entrada FB se houver
    if fb_moves:
        fbid = fb_moves[0]['id']
        print(f"\n  --- linhas da entrada FB id={fbid} ---")
        fblines = rr('account.move.line', [('move_id', '=', fbid)],
                     ['account_id', 'name', 'l10n_br_operacao_id', 'l10n_br_cfop_id',
                      'debit', 'credit', 'product_id'],
                     limit=200, order='id')
        td = tc = 0.0
        for ln in fblines:
            acc = m2o(ln.get('account_id'))
            op = m2o(ln.get('l10n_br_operacao_id'))
            cfop = m2o(ln.get('l10n_br_cfop_id'))
            d = ln.get('debit') or 0
            c = ln.get('credit') or 0
            td += d
            tc += c
            print(f"    acc={acc[:34]:34} op={op[:10]:10} cfop={cfop[:9]:9} D {d:>11,.2f} C {c:>11,.2f}")
        print(f"    {'TOTAIS':>50} D {td:>11,.2f} C {tc:>11,.2f}")

        # ===== 5) stock moves da entrada FB (double-count) =====
        print(f"\n  --- stock.move ligados a entrada FB (double-count?) ---")
        sm = rr('stock.move',
                [('company_id', '=', 1), '|',
                 ('origin', 'ilike', str(chosen['name'])),
                 ('picking_id.origin', 'ilike', str(chosen['name']))],
                ['id', 'product_id', 'product_uom_qty', 'location_id', 'location_dest_id', 'state'],
                limit=50)
        if not sm:
            print("    (busca por origin nao achou — stock.move pode estar vinculado por outro campo)")
        for s in sm[:20]:
            print(f"    move {s['id']} {m2o(s['product_id'])[:30]:30} qty={s['product_uom_qty']:>8} {m2o(s['location_id'])[:16]}->{m2o(s['location_dest_id'])[:16]} {s['state']}")

    print("\n[FIM G9 CASO — nada foi escrito]")


if __name__ == '__main__':
    main()
