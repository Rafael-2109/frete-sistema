#!/usr/bin/env python3
"""G9 CORRECAO (caso-piloto) — reversao pura per-documento da NF VND/2026/00234.

DRY-RUN e o DEFAULT. So efetiva com --confirmar.

Cria 2 lancamentos de ajuste (account.move move_type='entry', journal DIVERSOS), reversiveis:
  LF (company 5): D 5101020001 PASSIVA (26667) / C 1120100001 CLIENTES (26085)  -> baixa PASSIVA + desinfla recebivel
                  + concilia o credito com o recebivel da NF (562158, line 3437761) -> residual 2798,95 -> 871,51
  FB (company 1): D 3201000001 CPV (22527) / C 5101010001 ATIVA (22800)         -> reconhece custo (PA vendido) + baixa ATIVA

Valor = soma das linhas 5902 (op 2864) da NF LF (insumos). Datas = data das NFs (periodo ABERTO nos 2 lados).
Idempotente: aborta se ja existe entry com o REF.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

LF_MOVE = 562158          # VND/2026/00234
FB_MOVE = 564486          # ENTSI/2026/04/0025
RECV_LINE = 3437761       # linha de recebivel da NF LF (account 26085) a conciliar
REF = "G9-REGULARIZACAO IND. VND/2026/00234 (reversao pura per-doc)"

# contas
ACC_PASSIVA_LF = 26667    # 5101020001 PASSIVA (LF)
ACC_CLIENTES_LF = 26085   # 1120100001 CLIENTES (LF)
ACC_CPV_FB = 22527        # 3201000001 CUSTO DOS PRODUTOS VENDIDOS (FB)
ACC_ATIVA_FB = 22800      # 5101010001 ATIVA (FB)
J_DIV_LF = 894            # DIVERSOS (LF)
J_DIV_FB = 893            # DIVERSOS (FB)

CONFIRMAR = '--confirmar' in sys.argv


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid} | MODO: {'CONFIRMAR (ESCREVE)' if CONFIRMAR else 'DRY-RUN (nao escreve)'}\n")

    def rr(model, domain, fields, ctx, **kw):
        kwargs = {'fields': fields, 'context': ctx}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    CTX_LF = {'allowed_company_ids': [5]}
    CTX_FB = {'allowed_company_ids': [1]}
    CTX_BOTH = {'allowed_company_ids': [1, 5]}

    # ---- valor a regularizar = soma das linhas 5902 (op 2864) da NF LF ----
    lines5902 = rr('account.move.line', [('move_id', '=', LF_MOVE), ('l10n_br_operacao_id', '=', 2864)],
                   ['credit'], CTX_BOTH, limit=200)
    valor = round(sum(l.get('credit') or 0 for l in lines5902), 2)
    print(f"Insumos 5902 da NF (n={len(lines5902)}): VALOR A REGULARIZAR = R$ {valor:,.2f}")
    assert valor > 0, "valor zero — abortar"

    # ---- partner do recebivel (p/ conciliacao casar) ----
    rl = rr('account.move.line', [('id', '=', RECV_LINE)],
            ['partner_id', 'debit', 'amount_residual', 'reconciled', 'account_id'], CTX_BOTH)
    assert rl, "linha recebivel nao encontrada"
    partner_id = rl[0]['partner_id'][0] if isinstance(rl[0]['partner_id'], list) else False
    print(f"Recebivel NF: line {RECV_LINE} D {rl[0]['debit']:,.2f} residual {rl[0]['amount_residual']:,.2f} "
          f"reconciled={rl[0]['reconciled']} partner={rl[0]['partner_id']}")
    assert not rl[0]['reconciled'], "recebivel JA conciliado — revisar"

    # ---- idempotencia: ja existe entry com o REF? ----
    dup = rr('account.move', [('ref', '=', REF)], ['id', 'company_id', 'state'], CTX_BOTH, limit=5)
    if dup:
        print(f"\n[ABORT] ja existem entries com REF: {dup} — correcao ja aplicada. Nada a fazer.")
        return

    # ---- lock dates ----
    comps = rr('res.company', [('id', 'in', [1, 5])], ['id', 'fiscalyear_lock_date'], CTX_BOTH)
    locks = {c['id']: c.get('fiscalyear_lock_date') for c in comps}
    print(f"\nLock dates: FB={locks.get(1)} | LF={locks.get(5)}  (lancamentos em 2026-04 = ABERTO)")

    # ---- montar os entries ----
    entry_lf = {
        'move_type': 'entry', 'journal_id': J_DIV_LF, 'company_id': 5,
        'date': '2026-04-08', 'ref': REF,
        'line_ids': [
            (0, 0, {'account_id': ACC_PASSIVA_LF, 'partner_id': partner_id, 'name': REF,
                    'debit': valor, 'credit': 0.0}),
            (0, 0, {'account_id': ACC_CLIENTES_LF, 'partner_id': partner_id, 'name': REF,
                    'debit': 0.0, 'credit': valor}),
        ],
    }
    entry_fb = {
        'move_type': 'entry', 'journal_id': J_DIV_FB, 'company_id': 1,
        'date': '2026-04-09', 'ref': REF,
        'line_ids': [
            (0, 0, {'account_id': ACC_CPV_FB, 'name': REF, 'debit': valor, 'credit': 0.0}),
            (0, 0, {'account_id': ACC_ATIVA_FB, 'name': REF, 'debit': 0.0, 'credit': valor}),
        ],
    }

    def show(label, e):
        print(f"\n  [{label}] journal={e['journal_id']} company={e['company_id']} date={e['date']}")
        d = c = 0.0
        for _, _, ln in e['line_ids']:
            d += ln['debit']; c += ln['credit']
            print(f"     acc={ln['account_id']:6} D {ln['debit']:>10,.2f} C {ln['credit']:>10,.2f}")
        print(f"     balance: D {d:,.2f} == C {c:,.2f} -> {'OK' if abs(d-c) < 0.01 else 'DESBALANCEADO!'}")

    print("\n" + "=" * 70)
    print("LANCAMENTOS A CRIAR")
    print("=" * 70)
    show("LF entry - baixa PASSIVA + desinfla recebivel", entry_lf)
    show("FB entry - reconhece custo (CPV) + baixa ATIVA", entry_fb)
    print(f"\n  Apos conciliar: recebivel NF {rl[0]['debit']:,.2f} -> {rl[0]['debit']-valor:,.2f}")

    if not CONFIRMAR:
        print("\n[DRY-RUN] nada foi escrito. Para efetivar: --confirmar")
        return

    # ================= ESCRITA =================
    print("\n" + "=" * 70)
    print("EXECUTANDO (--confirmar)")
    print("=" * 70)

    # LF
    lf_id = o.execute_kw('account.move', 'create', [entry_lf], {'context': CTX_LF})
    print(f"  LF entry criado: id={lf_id}")
    o.execute_kw('account.move', 'action_post', [[lf_id]], {'context': CTX_LF})
    print(f"  LF entry POSTADO")
    # conciliar credito (account 26085) com o recebivel da NF
    lf_credit = o.execute_kw('account.move.line', 'search',
                             [[('move_id', '=', lf_id), ('account_id', '=', ACC_CLIENTES_LF)]],
                             {'context': CTX_LF})
    print(f"  LF credit line: {lf_credit}")
    o.execute_kw('account.move.line', 'reconcile', [[lf_credit[0], RECV_LINE]], {'context': CTX_LF})
    print(f"  CONCILIADO credito do ajuste com recebivel da NF (line {RECV_LINE})")
    # verifica residual
    chk = o.execute_kw('account.move.line', 'read', [[RECV_LINE], ['amount_residual', 'reconciled']],
                       {'context': CTX_LF})
    print(f"  >> recebivel agora: residual {chk[0]['amount_residual']:,.2f} reconciled={chk[0]['reconciled']}")

    # FB
    fb_id = o.execute_kw('account.move', 'create', [entry_fb], {'context': CTX_FB})
    print(f"  FB entry criado: id={fb_id}")
    o.execute_kw('account.move', 'action_post', [[fb_id]], {'context': CTX_FB})
    print(f"  FB entry POSTADO")

    print(f"\n[OK] correcao do caso aplicada. Entries: LF={lf_id} FB={fb_id} (ref='{REF}')")
    print("     reversivel: estornar os 2 entries (button_draft/reverse) desfaz a correcao.")


if __name__ == '__main__':
    main()
