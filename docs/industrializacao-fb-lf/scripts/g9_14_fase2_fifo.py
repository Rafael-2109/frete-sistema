#!/usr/bin/env python3
"""G9 FASE 2 (FIFO) — concilia a conta corrente FB<->LF (conta CLIENTES 26085, partner FB=1).

Aplica os CREDITOS abertos (ajustes G9 + pagamentos soltos) aos DEBITOS abertos (a-receber),
por ordem cronologica (FIFO: credito mais antigo abate debito mais antigo).
DRY-RUN default. So efetiva com --confirmar. --limit N processa so N creditos (validacao).

NAO desconcilia nada (so reconcilia o que esta aberto). Idempotente por natureza (so toca aberto).
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
CTX_LF = {'allowed_company_ids': [5]}
ACC = 26085
PARTNER = 1
CONFIRMAR = '--confirmar' in sys.argv
LIMIT = None
for i, a in enumerate(sys.argv):
    if a == '--limit' and i + 1 < len(sys.argv):
        LIMIT = int(sys.argv[i + 1])


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid} | FASE 2 FIFO | MODO: {'CONFIRMAR' if CONFIRMAR else 'DRY-RUN'}{f' LIMIT={LIMIT}' if LIMIT else ''}\n")

    def rr(domain, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}
        kw2.update(kw)
        return o.execute_kw('account.move.line', 'search_read', [domain], kw2)

    base = [('account_id', '=', ACC), ('partner_id', '=', PARTNER),
            ('parent_state', '=', 'posted'), ('reconciled', '=', False), ('amount_residual', '!=', 0)]
    deb = rr(base + [('amount_residual', '>', 0)], ['amount_residual', 'date'], order='date, id', limit=20000)
    cre = rr(base + [('amount_residual', '<', 0)], ['amount_residual', 'date'], order='date, id', limit=20000)
    tot_d = sum(l['amount_residual'] for l in deb)
    tot_c = -sum(l['amount_residual'] for l in cre)
    print(f"DEBITOS (a receber): {len(deb)} ln = R$ {tot_d:,.2f}")
    print(f"CREDITOS (ajustes+pagtos): {len(cre)} ln = R$ {tot_c:,.2f}")
    print(f"=> apos FIFO: a receber liquido R$ {tot_d - tot_c:,.2f}\n")

    if LIMIT:
        cre = cre[:LIMIT]

    # fila de debitos (rastreamento local de residual)
    debq = [[l['id'], l['amount_residual'], l['date']] for l in deb]
    di = 0  # ponteiro do debito atual
    grupos = []  # (credito_id, [debito_ids], valor_compensado)
    for c in cre:
        falta = -c['amount_residual']
        grupo_deb = []
        while falta > 0.005 and di < len(debq):
            d = debq[di]
            grupo_deb.append(d[0])
            if d[1] <= falta + 0.005:
                falta -= d[1]
                d[1] = 0
                di += 1
            else:
                d[1] -= falta
                falta = 0
        if grupo_deb:
            grupos.append((c['id'], grupo_deb, -c['amount_residual'] - max(0, falta)))

    n_compensar = sum(g[2] for g in grupos)
    debs_tocados = len(set(d for g in grupos for d in g[1]))
    print(f"FIFO: {len(grupos)} creditos casam com {debs_tocados} debitos | compensa R$ {n_compensar:,.2f}")
    print("  amostra:")
    for cid, dids, val in grupos[:5]:
        print(f"    credito {cid} -> {len(dids)} debito(s), R$ {val:,.2f}")

    if not CONFIRMAR:
        print("\n[DRY-RUN] nada escrito. --confirmar para efetivar.")
        return

    print("\nEXECUTANDO FIFO...")
    ok = falhas = 0
    for i, (cid, dids, val) in enumerate(grupos, 1):
        try:
            o.execute_kw('account.move.line', 'reconcile', [[cid] + dids], {'context': CTX_LF})
            ok += 1
        except Exception as e:
            falhas += 1
            print(f"  FALHA credito {cid}: {str(e)[:60]}")
        if i % 50 == 0 or i == len(grupos):
            print(f"  {i}/{len(grupos)} ... ok={ok} falhas={falhas}")
    print(f"\n[OK FASE 2] {ok} creditos conciliados (FIFO), {falhas} falhas.")


if __name__ == '__main__':
    main()
