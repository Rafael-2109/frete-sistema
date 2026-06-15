#!/usr/bin/env python3
"""G9 FASE 2 FIFO (robusto) — conclui a conciliacao dos creditos abertos restantes.

Diferente do g9_14: NAO rastreia residual localmente. Para CADA credito aberto, RE-LE os
debitos abertos frescos (order date asc) e reconcilia. Imune a divergencia de casamento do Odoo.
DRY-RUN default. --confirmar efetiva. Idempotente (so toca o que esta aberto).
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
CTX_LF = {'allowed_company_ids': [5]}
ACC, PARTNER = 26085, 1
CONFIRMAR = '--confirmar' in sys.argv
BASE = [('account_id', '=', ACC), ('partner_id', '=', PARTNER),
        ('parent_state', '=', 'posted'), ('reconciled', '=', False), ('amount_residual', '!=', 0)]


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid} | FIFO robusto | {'CONFIRMAR' if CONFIRMAR else 'DRY-RUN'}\n")

    def sr(domain, **kw):
        kw2 = {'context': CTX}
        kw2.update(kw)
        return o.execute_kw('account.move.line', 'search_read', [domain], kw2)

    creditos = sr(BASE + [('amount_residual', '<', 0)], fields=['amount_residual', 'date'], order='date, id', limit=20000)
    print(f"creditos abertos a processar: {len(creditos)} = R$ {-sum(c['amount_residual'] for c in creditos):,.2f}")
    if not CONFIRMAR:
        debs = sr(BASE + [('amount_residual', '>', 0)], fields=['amount_residual'], limit=20000)
        print(f"debitos abertos: {len(debs)} = R$ {sum(d['amount_residual'] for d in debs):,.2f}")
        print("\n[DRY-RUN] --confirmar para efetivar.")
        return

    ok = falhas = 0
    for i, c in enumerate(creditos, 1):
        # re-ler residual do credito (pode ter mudado)
        cf = o.execute_kw('account.move.line', 'read', [[c['id']], ['amount_residual', 'reconciled']], {'context': CTX_LF})
        if not cf or cf[0]['reconciled'] or abs(cf[0]['amount_residual']) < 0.005:
            continue
        falta = -cf[0]['amount_residual']
        debs = sr(BASE + [('amount_residual', '>', 0)], fields=['amount_residual'], order='date, id', limit=60)
        if not debs:
            print("  sem mais debitos abertos — parando.")
            break
        grupo = [c['id']]
        acc = 0.0
        for d in debs:
            grupo.append(d['id'])
            acc += d['amount_residual']
            if acc >= falta - 0.005:
                break
        try:
            o.execute_kw('account.move.line', 'reconcile', [grupo], {'context': CTX_LF})
            ok += 1
        except Exception as e:
            falhas += 1
            if falhas <= 5:
                print(f"  FALHA credito {c['id']}: {str(e)[:90]}")
        if i % 25 == 0 or i == len(creditos):
            print(f"  {i}/{len(creditos)} ... ok={ok} falhas={falhas}")
    print(f"\n[FIM] ok={ok} falhas={falhas}")


if __name__ == '__main__':
    main()
