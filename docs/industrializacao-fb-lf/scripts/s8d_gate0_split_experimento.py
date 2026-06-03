#!/usr/bin/env python3
"""GATE 0 — EXPERIMENTO: separar a NF mista de retorno em 2 documentos contabeis
(PA so-5124 / insumos so-5902 com no_payment PASSIVA) e medir se as contrapartidas
ficam corretas apos recompute + action_post NATIVO. TUDO em journals de teste,
SEM transmitir SEFAZ (action_post = so contabil; a NF NAO e' emitida). Postada e
DELETADA (zero sujeira). Valida a base da VIA B (separar na janela posted -> pre-SEFAZ).

METODO (espelha sessoes 5/6 — g4_experimento_no_payment.py):
  1. copia a VND mista menor (180552) p/ 2 journals de teste:
       - copia-A "PA" -> journal sale LF no_payment VAZIO (= j847); remove as linhas 5902
       - copia-B "INSUMOS" -> journal sale LF no_payment=26667 (PASSIVA); remove a linha 5124
  2. recompute fiscal nativo (onchange_l10n_br_calcular_imposto_btn) + setar invoice_date
  3. action_post das 2 -> ler contrapartidas (A: D CLIENTES so do servico; B: baixa 5101020001)
  4. cleanup: button_draft + unlink das 2 + arquivar/deletar journals

ALVO esperado:
  - copia-A (so 5124): D CLIENTES = servico+tributos, SEM as 5902 -> NF do PA limpa
  - copia-B (so 5902, no_payment 26667): linha no_payment credita/debita 5101020001 (PASSIVA) -> baixa

MODOS:
  (sem flag)              dry-run: acha a NF + mostra o plano (READ-only)
  --confirmar             cria 2 journals teste + 2 copias + separa linhas + DRAFT + le
  --postar A_ID B_ID      action_post das 2 copias + le contrapartidas (2o go)
  --cleanup A_ID B_ID JA JB   button_draft+unlink das 2 + arquiva/deleta journals
"""
import sys
import argparse
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
NO_PAY_PASSIVA = 26667           # 5101020001 PASSIVA LF (a 2a NF de insumos baixa aqui)
VND_MISTA_MENOR = 180552         # VND/2025/00089 (1x5124 + 24x5902, total 43,37)
CFOP_PA = '5124'
CFOP_INSUMO = '5902'


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v is False or v is None else str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true')
    ap.add_argument('--postar', nargs=2, type=int, metavar=('A_ID', 'B_ID'))
    ap.add_argument('--cleanup', nargs=4, type=int, metavar=('A_ID', 'B_ID', 'JA', 'JB'))
    args = ap.parse_args()

    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}; kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)
    def rd(model, ids, fields):
        ids = [i for i in ids if i]
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX}) if ids else []
    def w(model, ids, vals):
        return o.execute_kw(model, 'write', [list(ids), vals], {'context': CTX})

    def ler_linhas(move_id, titulo):
        mv = rd('account.move', [move_id], ['name', 'state', 'journal_id', 'amount_total', 'amount_untaxed'])[0]
        print(f"\n  --- {titulo} (move {move_id}) ---")
        print(f"  state={mv['state']} journal={m2o(mv['journal_id'])} untax={mv.get('amount_untaxed')} total={mv.get('amount_total')}")
        lines = rr('account.move.line', [('move_id', '=', move_id)],
                   ['account_id', 'l10n_br_cfop_codigo', 'l10n_br_operacao_id', 'debit', 'credit', 'display_type'],
                   limit=80)
        for ln in lines:
            if ln.get('display_type') in ('line_section', 'line_note'):
                continue
            acc = m2o(ln.get('account_id'))
            flag = ''
            if acc.startswith(f'{NO_PAY_PASSIVA}|') or '5101020001' in acc:
                flag = '  <<< 5101020001 PASSIVA (no_payment) — BAIXA'
            elif 'CLIENTE' in acc.upper():
                flag = '  <<< CLIENTES (recebivel servico)'
            print(f"      acc={acc[:44]:44} cfop={str(ln.get('l10n_br_cfop_codigo')):6} "
                  f"D={ln.get('debit')} C={ln.get('credit')}{flag}")

    # ---------- CLEANUP ----------
    if args.cleanup:
        a_id, b_id, ja, jb = args.cleanup
        for mid in (a_id, b_id):
            st = rd('account.move', [mid], ['state'])
            if not st:
                print(f"  move {mid}: ja nao existe"); continue
            if st[0]['state'] == 'posted':
                o.execute_kw('account.move', 'button_draft', [[mid]], {'context': CTX})
                print(f"  move {mid}: posted -> draft")
            try:
                o.execute_kw('account.move', 'unlink', [[mid]], {'context': CTX})
                print(f"  move {mid} DELETADO")
            except Exception as e:
                o.execute_kw('account.move', 'button_cancel', [[mid]], {'context': CTX})
                print(f"  move {mid} unlink falhou ({e}); CANCELADO")
        for jid in (ja, jb):
            try:
                nml = o.execute_kw('account.move.line', 'search_count', [[('journal_id', '=', jid)]],
                                   {'context': dict(CTX, active_test=False)})
                if nml == 0:
                    o.execute_kw('account.journal', 'unlink', [[jid]], {'context': CTX})
                    print(f"  journal {jid} DELETADO (0 linhas)")
                else:
                    w('account.journal', [jid], {'active': False})
                    print(f"  journal {jid} ARQUIVADO ({nml} linhas residuais)")
            except Exception as e:
                w('account.journal', [jid], {'active': False})
                print(f"  journal {jid} arquivado (unlink falhou: {e})")
        return

    # ---------- POSTAR ----------
    if args.postar:
        a_id, b_id = args.postar
        for mid, lbl in ((a_id, 'A=PA so-5124'), (b_id, 'B=INSUMOS so-5902 no_payment')):
            print(f"\nPOSTAR {lbl} move {mid} (action_post = SO CONTABIL, sem SEFAZ)")
            # garantir invoice_date (copy reseta)
            mv = rd('account.move', [mid], ['invoice_date', 'date'])
            if mv and not mv[0].get('invoice_date'):
                w('account.move', [mid], {'invoice_date': mv[0].get('date')})
            o.execute_kw('account.move', 'action_post', [[mid]], {'context': CTX})
            ler_linhas(mid, f"POS-POST {lbl}")
        print("\n  >>> cleanup: --cleanup A_ID B_ID JA JB")
        return

    # ---------- DRY-RUN: achar a NF + plano ----------
    nf = rd('account.move', [VND_MISTA_MENOR],
            ['id', 'name', 'state', 'amount_total', 'journal_id', 'l10n_br_tipo_pedido'])
    assert nf, f"VND {VND_MISTA_MENOR} nao encontrada"
    nf = nf[0]
    lines = rr('account.move.line', [('move_id', '=', VND_MISTA_MENOR), ('display_type', '=', 'product')],
               ['l10n_br_cfop_codigo', 'price_unit', 'price_subtotal'], limit=100)
    cfs = Counter(str(l.get('l10n_br_cfop_codigo')) for l in lines)
    print("=" * 88)
    print("GATE 0 — PLANO (separar NF mista em 2 docs; action_post=contabil, SEM SEFAZ)")
    print("=" * 88)
    print(f"  NF-modelo : move {nf['id']} {nf['name']} total={nf['amount_total']} tipo_pedido={nf.get('l10n_br_tipo_pedido')}")
    print(f"  linhas-produto: {dict(cfs)} (1x{CFOP_PA} servico/PA + Nx{CFOP_INSUMO} insumos)")
    print(f"  copia-A 'PA'      -> journal sale/LF no_payment VAZIO ; remove linhas {CFOP_INSUMO} -> so {CFOP_PA}")
    print(f"  copia-B 'INSUMOS' -> journal sale/LF no_payment={NO_PAY_PASSIVA} (PASSIVA 5101020001); remove {CFOP_PA} -> so {CFOP_INSUMO}")
    print(f"  passos: criar 2 journals teste -> 2 copies (draft) -> separa linhas -> recompute -> [postar] -> medir -> cleanup")
    print(f"  efeito: 0 SEFAZ, 0 stock.move; action_post so razao (reversivel via delete)")

    if not args.confirmar:
        print("\n  [DRY-RUN] nada escrito. Com 'go': rode --confirmar.")
        return

    # ---------- EXECUTAR: 2 journals + 2 copias + separa ----------
    print("\n  [1] criando 2 journals de teste (sale/LF)...")
    ja = o.execute_kw('account.journal', 'create',
                      [{'name': 'ZZ TESTE GATE0 PA — DELETAR', 'code': 'ZG0A', 'type': 'sale', 'company_id': 5}],
                      {'context': CTX})
    jb = o.execute_kw('account.journal', 'create',
                      [{'name': 'ZZ TESTE GATE0 INSUMOS — DELETAR', 'code': 'ZG0B', 'type': 'sale',
                        'company_id': 5, 'account_no_payment_id': NO_PAY_PASSIVA}], {'context': CTX})
    print(f"      journal A (PA, no_pay vazio)={ja} ; journal B (INSUMOS, no_pay {NO_PAY_PASSIVA})={jb}")

    def copia_e_separa(jid, remover_cfop, label):
        cid = o.execute_kw('account.move', 'copy', [VND_MISTA_MENOR, {'journal_id': jid}], {'context': CTX})
        if isinstance(cid, list):
            cid = cid[0]
        # remover as linhas-produto do cfop a remover
        rem = rr('account.move.line', [('move_id', '=', cid), ('display_type', '=', 'product'),
                                       ('l10n_br_cfop_codigo', '=', remover_cfop)], ['id'], limit=200)
        rem_ids = [l['id'] for l in rem]
        if rem_ids:
            o.execute_kw('account.move', 'write', [[cid], {'invoice_line_ids': [(2, rid) for rid in rem_ids]}],
                         {'context': CTX})
        # recompute fiscal nativo (como o robo)
        try:
            o.execute_kw('account.move', 'onchange_l10n_br_calcular_imposto_btn', [[cid]], {'context': CTX})
        except Exception as e:
            if "cannot marshal None" not in str(e):
                print(f"      ({label}) recompute aviso: {e}")
        print(f"      {label}: copia move {cid}; removidas {len(rem_ids)} linhas {remover_cfop}")
        return cid

    print(f"\n  [2] copia-A (PA, manter {CFOP_PA})...")
    a_id = copia_e_separa(ja, CFOP_INSUMO, 'A=PA')
    print(f"  [3] copia-B (INSUMOS, manter {CFOP_INSUMO})...")
    b_id = copia_e_separa(jb, CFOP_PA, 'B=INSUMOS')

    print(f"\n  [4] lendo as 2 copias em DRAFT:")
    ler_linhas(a_id, "COPIA-A (PA so-5124, draft)")
    ler_linhas(b_id, "COPIA-B (INSUMOS so-5902 no_payment, draft)")
    print(f"\n  >>> 2o go (postar contabil, sem SEFAZ): --postar {a_id} {b_id}")
    print(f"  >>> cleanup: --cleanup {a_id} {b_id} {ja} {jb}")


if __name__ == '__main__':
    main()
