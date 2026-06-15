#!/usr/bin/env python3
"""G9 CONCILIA extrato SANTANDER da LF (j1030) — pagamentos FB->LF nao-conciliados.

O extrato Santander registra os PIX da FB com memo 'PIX RECEBIDO 61724241000178' (CNPJ FB),
sem a palavra NACOM — por isso o g9_35 (filtro NACOM/SICOOB) nao os pegou. Mesma mecanica:
reaponta a linha TRANSITORIA (1110100003, suspense) -> CLIENTES (26085, partner FB) e reconcilia
FIFO com os debitos das NFs VND a receber.

FILTRO DE INCLUSAO (so FB->LF):
  EXCLUI 'RESGATE'/'CONTAMAX'/'APLICA' (resgate de aplicacao, nao e pagamento de terceiro)
  EXCLUI PIX da propria LF (CNPJ 18467441000163 / 'FAMIGLIA' SEM CNPJ FB)
  INCLUI o resto (PIX com CNPJ FB + PIX RECEBIDO sem CNPJ)

DRY-RUN default (lista incluidas/excluidas + simula FIFO). --confirmar efetiva. Idempotente.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
ACC_LF, P_FB = 26085, 1
J_SANTANDER = 1030
CNPJ_FB, CNPJ_LF = '61724241000178', '18467441000163'
CONFIRMAR = '--confirmar' in sys.argv


def eh_fb(memo):
    """True se a entrada e pagamento FB->LF (nao resgate, nao PIX da propria LF)."""
    u = (memo or '').upper()
    if any(t in u for t in ('RESGATE', 'CONTAMAX', 'APLICA')):
        return False, 'RESGATE/aplicacao'
    if (CNPJ_LF in u or 'FAMIGLIA' in u) and CNPJ_FB not in u:
        return False, 'PIX da propria LF'
    return True, 'FB->LF'


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid} | {'CONFIRMAR' if CONFIRMAR else 'DRY-RUN'} | journal SANTANDER {J_SANTANDER}\n")

    def sr(m, d, f, **k):
        kw = {'fields': f, 'context': CTX}; kw.update(k)
        return o.execute_kw(m, 'search_read', [d], kw)

    ent = sr('account.bank.statement.line',
             [('journal_id', '=', J_SANTANDER), ('company_id', '=', 5), ('date', '>=', '2026-01-01'),
              ('amount', '>', 0), ('is_reconciled', '=', False)],
             ['date', 'amount', 'payment_ref', 'move_id'], order='date, id')

    # multiset dos pagamentos FB->LF (debito FORNECEDORES partner LF) por transacao/move:
    # so concilia entrada cujo valor corresponde a um pagamento que a FB efetivamente fez.
    from collections import defaultdict, Counter
    pag = sr('account.move.line', [('account_id', '=', 11038), ('partner_id', '=', 35),
             ('parent_state', '=', 'posted'), ('debit', '>', 0), ('date', '>=', '2026-01-01')],
             ['debit', 'move_id'])
    tr = defaultdict(float)
    for p in pag:
        tr[p['move_id'][0]] += p['debit']
    pagset = Counter(round(v, 2) for v in tr.values())

    incl, excl = [], []
    for e in ent:
        ok, _ = eh_fb(e['payment_ref'])
        if not ok:
            excl.append((e, 'resgate/propria-LF')); continue
        k = round(e['amount'], 2)
        if pagset.get(k, 0) > 0:
            pagset[k] -= 1; incl.append((e, 'FB->LF'))
        else:
            excl.append((e, 'sem par no pagto FB (revisar)'))

    print(f"entradas Santander nao-conciliadas: {len(ent)} = R$ {sum(e['amount'] for e in ent):,.2f}")
    print(f"  INCLUIR (FB->LF):  {len(incl)} = R$ {sum(e['amount'] for e, _ in incl):,.2f}")
    print(f"  EXCLUIR:           {len(excl)} = R$ {sum(e['amount'] for e, _ in excl):,.2f}")
    print("\n  --- EXCLUIDAS (ficam nao-conciliadas p/ o financeiro tratar) ---")
    for e, m in excl:
        print(f"    {e['date']} R$ {e['amount']:>10,.2f} [{m}] {(e['payment_ref'] or '')[:48]}")

    def vnd_frescas(limit=400):
        fat = sr('account.move.line', [('account_id', '=', ACC_LF), ('partner_id', '=', P_FB),
                 ('parent_state', '=', 'posted'), ('debit', '>', 0), ('amount_residual', '>', 0)],
                 ['move_id', 'amount_residual'], order='date, id', limit=limit)
        mids = list({f['move_id'][0] for f in fat})
        nm = {}
        for i in range(0, len(mids), 300):
            for m in o.execute_kw('account.move', 'read', [mids[i:i + 300]], {'fields': ['name'], 'context': CTX}):
                nm[m['id']] = m['name']
        return [(f['id'], f['amount_residual']) for f in fat if nm.get(f['move_id'][0], '').startswith('VND')]

    if not CONFIRMAR:
        fat = vnd_frescas()
        print(f"\n  NFs VND a receber (FIFO): {len(fat)} = R$ {sum(r for _, r in fat):,.2f}")
        print("\n  --- INCLUIDAS (serao conciliadas FIFO) ---")
        # simula FIFO sem alterar (copia residuais)
        pilha = [list(x) for x in fat]
        for e, _ in incl:
            falta = e['amount']; usa = 0
            for p in pilha:
                if p[1] <= 0.005:
                    continue
                u = min(falta, p[1]); p[1] -= u; falta -= u; usa += 1
                if falta <= 0.005:
                    break
            print(f"    {e['date']} R$ {e['amount']:>10,.2f} -> {usa} NF(s) VND | {(e['payment_ref'] or '')[:34]}")
        print("\n[DRY-RUN] --confirmar efetiva (reaponta TRANSITORIA->CLIENTES + reconcilia FIFO).")
        return

    ok = fail = 0
    for e, _ in incl:
        mls = sr('account.move.line', [('move_id', '=', e['move_id'][0]), ('credit', '>', 0)], ['reconciled'])
        if len(mls) != 1 or mls[0]['reconciled']:
            print(f"  SKIP {e['date']} R$ {e['amount']:,.2f}: contrapartida inesperada ({len(mls)} cred / reconciliada)"); continue
        trans_id = mls[0]['id']; amt = e['amount']
        fat = vnd_frescas()
        alvo = []; falta = amt
        for fid, fr in fat:
            u = min(falta, fr); falta -= u; alvo.append(fid)
            if falta <= 0.005:
                break
        try:
            o.execute_kw('account.move.line', 'write', [[trans_id], {'account_id': ACC_LF, 'partner_id': P_FB}], {'context': CTX})
            o.execute_kw('account.move.line', 'reconcile', [[trans_id] + alvo], {'context': CTX})
            ok += 1
            print(f"  OK {e['date']} R$ {amt:,.2f} -> {len(alvo)} NF(s)")
        except Exception as ex:
            fail += 1
            print(f"  FALHA {e['date']} R$ {amt:,.2f}: {str(ex)[:120]}")
    print(f"\n[FIM] ok={ok} fail={fail}")


if __name__ == '__main__':
    main()
