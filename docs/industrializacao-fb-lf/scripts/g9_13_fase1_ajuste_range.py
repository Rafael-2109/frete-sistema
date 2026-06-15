#!/usr/bin/env python3
"""G9 FASE 1 (ajuste contabil) — range de meses. Baixa PASSIVA (LF) + ATIVA (FB) por NF.

DRY-RUN default. So efetiva com --confirmar.
Para cada NF de retorno (j847, com 5902) no range:
  entry LF: D 5101020001 PASSIVA (26667) / C <conta recebivel da NF>
  entry FB: D 3201000001 CPV (22527) / C 5101010001 ATIVA (22800)
NAO desconcilia, NAO reconcilia (isso e a FASE 2 - FIFO).
Idempotente por REF. Lock guard. Uso: python g9_13_fase1_ajuste_range.py --de 2025-02-01 --ate 2026-06-30 [--confirmar]
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX_BOTH = {'allowed_company_ids': [1, 5]}
CTX_LF = {'allowed_company_ids': [5]}
CTX_FB = {'allowed_company_ids': [1]}
OPS_5902 = [2864, 2710]
ACC_PASSIVA_LF = 26667
ACC_CPV_FB = 22527
ACC_ATIVA_FB = 22800
J_DIV_LF = 894
J_DIV_FB = 893

DE, ATE = '2025-02-01', '2026-06-30'
for i, a in enumerate(sys.argv):
    if a == '--de' and i + 1 < len(sys.argv):
        DE = sys.argv[i + 1]
    if a == '--ate' and i + 1 < len(sys.argv):
        ATE = sys.argv[i + 1]
CONFIRMAR = '--confirmar' in sys.argv


def ref_of(name):
    return f"G9-REGULARIZACAO IND. {name} (reversao pura per-doc)"


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid} | FASE 1 ajuste {DE}..{ATE} | MODO: {'CONFIRMAR' if CONFIRMAR else 'DRY-RUN'}\n")

    def rr(model, domain, fields, ctx=CTX_BOTH, **kw):
        kw2 = {'fields': fields, 'context': ctx}
        kw2.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kw2)

    # lock guard
    comps = rr('res.company', [('id', 'in', [1, 5])], ['id', 'fiscalyear_lock_date'])
    lock = {c['id']: (c.get('fiscalyear_lock_date') or '') for c in comps}
    if lock.get(1, '') >= DE or lock.get(5, '') >= DE:
        print(f"[ABORT] periodo pode estar FECHADO (lock FB {lock.get(1)} / LF {lock.get(5)} vs DE {DE}).")
        return
    print(f"Lock OK: FB={lock.get(1)} / LF={lock.get(5)}\n")

    moves = rr('account.move',
               [('journal_id', '=', 847), ('company_id', '=', 5), ('state', '=', 'posted'),
                ('move_type', '=', 'out_invoice'), ('date', '>=', DE), ('date', '<=', ATE)],
               ['id', 'name', 'date'], order='date, id', limit=5000)
    print(f"NFs j847 no range: {len(moves)}")

    # ja feitas (REF existe)
    refs = [ref_of(m['name']) for m in moves]
    feitos = set()
    CH = 200
    for i in range(0, len(refs), CH):
        ex = rr('account.move', [('ref', 'in', refs[i:i + CH]), ('company_id', '=', 5)], ['ref'])
        feitos.update(x['ref'] for x in ex)

    plan = []
    for m in moves:
        if ref_of(m['name']) in feitos:
            plan.append({**m, 'status': 'JA FEITA', 'valor': 0})
            continue
        l5902 = rr('account.move.line', [('move_id', '=', m['id']), ('l10n_br_operacao_id', 'in', OPS_5902)], ['credit'])
        valor = round(sum(l.get('credit') or 0 for l in l5902), 2)
        if valor <= 0:
            plan.append({**m, 'status': 'SEM 5902', 'valor': 0})
            continue
        recv = rr('account.move.line',
                  [('move_id', '=', m['id']), ('account_id.account_type', '=', 'asset_receivable'), ('debit', '>', 0)],
                  ['account_id', 'partner_id'])
        if len(recv) != 1:
            plan.append({**m, 'status': f'RECEBIVEL x{len(recv)}', 'valor': valor})
            continue
        plan.append({**m, 'status': 'ELEGIVEL', 'valor': valor,
                     'acc_cli': recv[0]['account_id'][0],
                     'partner': recv[0]['partner_id'][0] if recv[0]['partner_id'] else False})

    eleg = [p for p in plan if p['status'] == 'ELEGIVEL']
    jafeita = sum(1 for p in plan if p['status'] == 'JA FEITA')
    outros = [p for p in plan if p['status'] not in ('ELEGIVEL', 'JA FEITA')]
    print(f"  ELEGIVEIS (a lancar): {len(eleg)} | R$ {sum(p['valor'] for p in eleg):,.2f}")
    print(f"  ja feitas: {jafeita} | outros(pula): {len(outros)}")
    for p in outros[:10]:
        print(f"     {p['name']}: {p['status']}")

    if not CONFIRMAR:
        print("\n[DRY-RUN] nada escrito. --confirmar para efetivar.")
        return

    print("\nEXECUTANDO FASE 1...")
    feitas = 0
    for i, p in enumerate(eleg, 1):
        ref = ref_of(p['name'])
        lf_id = o.execute_kw('account.move', 'create', [{
            'move_type': 'entry', 'journal_id': J_DIV_LF, 'company_id': 5, 'date': p['date'], 'ref': ref,
            'line_ids': [
                (0, 0, {'account_id': ACC_PASSIVA_LF, 'partner_id': p['partner'], 'name': ref, 'debit': p['valor'], 'credit': 0.0}),
                (0, 0, {'account_id': p['acc_cli'], 'partner_id': p['partner'], 'name': ref, 'debit': 0.0, 'credit': p['valor']}),
            ]}], {'context': CTX_LF})
        o.execute_kw('account.move', 'action_post', [[lf_id]], {'context': CTX_LF})
        fb_id = o.execute_kw('account.move', 'create', [{
            'move_type': 'entry', 'journal_id': J_DIV_FB, 'company_id': 1, 'date': p['date'], 'ref': ref,
            'line_ids': [
                (0, 0, {'account_id': ACC_CPV_FB, 'name': ref, 'debit': p['valor'], 'credit': 0.0}),
                (0, 0, {'account_id': ACC_ATIVA_FB, 'name': ref, 'debit': 0.0, 'credit': p['valor']}),
            ]}], {'context': CTX_FB})
        o.execute_kw('account.move', 'action_post', [[fb_id]], {'context': CTX_FB})
        feitas += 1
        if i % 25 == 0 or i == len(eleg):
            print(f"  {i}/{len(eleg)} ... {p['name']} ({p['date']})")
    print(f"\n[OK FASE 1] {feitas} NFs ajustadas no range {DE}..{ATE}.")


if __name__ == '__main__':
    main()
