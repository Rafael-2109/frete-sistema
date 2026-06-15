#!/usr/bin/env python3
"""G9 EFETIVA realocacao FIFO dos adiantamentos FB contra faturas ENTSI em aberto.

Robusto (re-le estado fresco por adiantamento, padrao g9_15). DRY-RUN default.
--confirmar efetiva o reconcile no Odoo PROD. --incluir-duplicata inclui os 8 X~=S
(default EXCLUI, pois recomendados a estornar). Reconciliacao e REVERSIVEL no Odoo.
"""
import sys
import re
from collections import defaultdict
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
ACC_FB, P_LF = 11038, 35
RE_FAT = re.compile(r'[A-Z]{3,6}/\d{4}/\d{2}/\d{4}')
CONFIRMAR = '--confirmar' in sys.argv
INCLUIR_DUP = '--incluir-duplicata' in sys.argv
base_fb = [('account_id', '=', ACC_FB), ('partner_id', '=', P_LF), ('parent_state', '=', 'posted')]


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid} | {'CONFIRMAR (EFETIVA PROD)' if CONFIRMAR else 'DRY-RUN'} | duplicata: {'INCLUI' if INCLUIR_DUP else 'EXCLUI'}\n")

    def sr(m, d, f, **k):
        kw = {'fields': f, 'context': CTX}; kw.update(k)
        return o.execute_kw(m, 'search_read', [d], kw)

    adi = sr('account.move.line', base_fb + [('debit', '>', 0), ('reconciled', '=', False), ('amount_residual', '>', 0)],
             ['date', 'amount_residual', 'ref', 'move_id'], order='date')
    # S por adiantamento (flag duplicata X~=S)
    alvo = set()
    for l in adi:
        alvo |= set(RE_FAT.findall(l.get('ref') or ''))
    fm = sr('account.move', [('name', 'in', list(alvo)), ('company_id', '=', 1)], ['name'])
    mid2n = {m['id']: m['name'] for m in fm}
    fl = sr('account.move.line', [('move_id', 'in', list(mid2n)), ('account_id', '=', ACC_FB), ('credit', '>', 0)], ['move_id', 'credit'])
    fcred = defaultdict(float)
    for l in fl:
        fcred[mid2n[l['move_id'][0]]] += l['credit'] or 0

    alvos = []
    for l in adi:
        X = l['amount_residual']
        S = sum(fcred.get(a, 0) for a in RE_FAT.findall(l.get('ref') or ''))
        dup = S > 0 and abs(S - X) <= max(1.0, 0.01 * X)
        if dup and not INCLUIR_DUP:
            continue
        alvos.append(l)
    print(f"adiantamentos a realocar: {len(alvos)} de {len(adi)} | R$ {sum(a['amount_residual'] for a in alvos):,.2f}")

    if not CONFIRMAR:
        # plano: simular FIFO sobre pilha fresca
        ab = sr('account.move.line', base_fb + [('credit', '>', 0), ('reconciled', '=', False), ('amount_residual', '<', 0)],
                ['move_id', 'amount_residual', 'date'], order='date, id')
        pilha = [{'n': a['move_id'][1], 'r': -(a['amount_residual'] or 0)} for a in ab]
        cobre = 0.0
        for l in alvos:
            X = l['amount_residual']; aplica = 0.0
            for f in pilha:
                if f['r'] <= 0.005:
                    continue
                u = min(X - aplica, f['r']); f['r'] -= u; aplica += u
                if aplica >= X - 0.005:
                    break
            cobre += aplica
        print(f"faturas em aberto disponiveis: {len(ab)} = R$ {sum(-(a['amount_residual'] or 0) for a in ab):,.2f}")
        print(f"cobertura FIFO simulada: R$ {cobre:,.2f}")
        print("\n[DRY-RUN] --confirmar efetiva (somente com 'go' explicito).")
        return

    # EFETIVAR — robusto: re-le faturas frescas por adiantamento
    ok = fail = 0; realoc = 0.0
    for i, l in enumerate(alvos, 1):
        cf = o.execute_kw('account.move.line', 'read', [[l['id']], ['amount_residual', 'reconciled']], {'context': CTX})
        if not cf or cf[0]['reconciled'] or abs(cf[0]['amount_residual']) < 0.005:
            continue
        X = cf[0]['amount_residual']
        ab = sr('account.move.line', base_fb + [('credit', '>', 0), ('reconciled', '=', False), ('amount_residual', '<', 0)],
                ['amount_residual'], order='date, id', limit=80)
        if not ab:
            print("  sem faturas abertas — parando."); break
        grupo = [l['id']]; acc = 0.0
        for f in ab:
            grupo.append(f['id']); acc += -(f['amount_residual'] or 0)
            if acc >= X - 0.005:
                break
        try:
            o.execute_kw('account.move.line', 'reconcile', [grupo], {'context': CTX})
            ok += 1; realoc += X
        except Exception as e:
            fail += 1
            if fail <= 8:
                print(f"  FALHA {l['move_id'][1]}: {str(e)[:90]}")
        if i % 10 == 0 or i == len(alvos):
            print(f"  {i}/{len(alvos)} ok={ok} fail={fail}")
    print(f"\n[FIM] reconciliados ok={ok} fail={fail} | realocado R$ {realoc:,.2f}")


if __name__ == '__main__':
    main()
