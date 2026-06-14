#!/usr/bin/env python3
"""G9 ESCOPO (READ-ONLY) — universo da REGULARIZACAO HISTORICA da industrializacao FB<->LF.

Responde o GAP de escopo: "desde 01/2025" (Rafael) vs "date>=2026-01-01" (analises previas).
Mede:
  Q1 range real de datas + contagem de NFs de retorno (j847, partner FB) por ANO-MES;
  Q2 saldo das contas de compensacao ATIVA (5101010001 FB acc 22800) e PASSIVA (5101020001 LF acc 26667)
     por ANO (debito/credito/saldo) — para dimensionar o acumulado por periodo;
  Q3 valor dos insumos 5902 (que deveriam baixar a PASSIVA) por ANO.
NAO escreve nada.
"""
import sys
from collections import defaultdict
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
OPS_5902 = [2864, 2710]   # insumos consumidos (retorno) - NF mista
OPS_5903 = [2711]         # perda/sobra
OPS_5124 = [2702, 3039]   # servico
ACC_ATIVA_FB = 22800      # 5101010001 ATIVA (company 1 FB)
ACC_PASSIVA_LF = 26667    # 5101020001 PASSIVA (company 5 LF)
ACC_ATIVA_LF = 26652      # 5101010001 ATIVA (company 5 LF) - usada errado pelo PERDAS
ACC_PASSIVA_FB = 22815    # 5101020001 PASSIVA (company 1 FB)


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}\n")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    def rg(model, domain, fields, groupby, **kw):
        kwargs = {'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'read_group', [domain, fields, groupby], kwargs)

    # ===== Q1: NFs do j847 (retorno LF->FB) — range + por ano-mes =====
    print("=" * 70)
    print("Q1 — NFs em j847 (LF sale, out_invoice posted, company 5)")
    print("=" * 70)
    g = rg('account.move',
           [('journal_id', '=', 847), ('company_id', '=', 5),
            ('state', '=', 'posted'), ('move_type', '=', 'out_invoice')],
           ['amount_total:sum'], ['date:month'], lazy=False)
    total_nfs = 0
    for row in sorted(g, key=lambda r: r.get('date:month') or ''):
        per = row.get('date:month')
        cnt = row.get('__count', 0)
        tot = row.get('amount_total', 0) or 0
        total_nfs += cnt
        print(f"    {per:>12}  {cnt:5} NFs   total R$ {tot:>16,.2f}")
    print(f"    {'TOTAL':>12}  {total_nfs:5} NFs")

    # range absoluto
    mn = rr('account.move', [('journal_id', '=', 847), ('company_id', '=', 5),
                             ('state', '=', 'posted'), ('move_type', '=', 'out_invoice')],
            ['date'], limit=1, order='date asc')
    mx = rr('account.move', [('journal_id', '=', 847), ('company_id', '=', 5),
                             ('state', '=', 'posted'), ('move_type', '=', 'out_invoice')],
            ['date'], limit=1, order='date desc')
    print(f"\n    range: {mn[0]['date'] if mn else '-'}  ate  {mx[0]['date'] if mx else '-'}")

    # ===== Q2: saldos das contas de compensacao por ANO =====
    for label, acc, comp in [("ATIVA 5101010001 (FB, acc 22800)", ACC_ATIVA_FB, 1),
                             ("PASSIVA 5101020001 (LF, acc 26667)", ACC_PASSIVA_LF, 5),
                             ("ATIVA 5101010001 (LF, acc 26652) [perdas?]", ACC_ATIVA_LF, 5),
                             ("PASSIVA 5101020001 (FB, acc 22815)", ACC_PASSIVA_FB, 1)]:
        print("\n" + "=" * 70)
        print(f"Q2 — {label}")
        print("=" * 70)
        g = rg('account.move.line',
               [('account_id', '=', acc), ('parent_state', '=', 'posted')],
               ['debit:sum', 'credit:sum'], ['date:year'], lazy=False)
        td = tc = 0.0
        for row in sorted(g, key=lambda r: r.get('date:year') or ''):
            yr = row.get('date:year')
            d = row.get('debit', 0) or 0
            c = row.get('credit', 0) or 0
            cnt = row.get('__count', 0)
            td += d
            tc += c
            print(f"    {yr:>8}  {cnt:5} ln   D R$ {d:>16,.2f}   C R$ {c:>16,.2f}   saldo R$ {d-c:>16,.2f}")
        print(f"    {'TOTAL':>8}         D R$ {td:>16,.2f}   C R$ {tc:>16,.2f}   SALDO R$ {td-tc:>16,.2f}")

    # ===== Q3: valor 5902 (insumos retorno) por ano — o que deveria baixar a PASSIVA =====
    print("\n" + "=" * 70)
    print("Q3 — linhas 5902 (insumos retorno, op 2864/2710) em j847 por ANO")
    print("=" * 70)
    g = rg('account.move.line',
           [('journal_id', '=', 847), ('parent_state', '=', 'posted'),
            ('l10n_br_operacao_id', 'in', OPS_5902)],
           ['credit:sum', 'debit:sum'], ['date:year'], lazy=False)
    tot5902 = 0.0
    for row in sorted(g, key=lambda r: r.get('date:year') or ''):
        yr = row.get('date:year')
        c = row.get('credit', 0) or 0
        d = row.get('debit', 0) or 0
        cnt = row.get('__count', 0)
        tot5902 += (c - d)
        print(f"    {yr:>8}  {cnt:5} ln   C R$ {c:>16,.2f}   D R$ {d:>16,.2f}")
    print(f"    => total insumos 5902 (C-D) que NAO baixaram a PASSIVA: R$ {tot5902:,.2f}")

    print("\n[FIM G9 ESCOPO — nada foi escrito]")


if __name__ == '__main__':
    main()
