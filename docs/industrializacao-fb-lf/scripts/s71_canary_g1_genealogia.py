#!/usr/bin/env python3
"""s71 — CANARY READ-ONLY do body G1 (genealogia safe_eval) contra o ORÁCULO.

Roda APENAS a seção de genealogia + resolução de chave do `SA_BODY_G1` via uma server
action EFÊMERA com `log` no fim (ZERO `account.move` criado) e compara o resultado com
`DescobertaIndustrializacaoService.descobrir_fonte_nf2` (oráculo, Python testado).

Cria só um `ir.actions.server` transitório (create→run→unlink), padrão do s49 — NÃO
escreve NF nem posta nada. O corpo do canary é DERIVADO do próprio `SA_BODY_G1` (truncado
antes da montagem) para validar o código REAL, sem cópia/drift.

Uso: python docs/industrializacao-fb-lf/scripts/s71_canary_g1_genealogia.py [NF1_ID]
     (default NF1 = 791437, piloto VND/2026/00384)
"""
import os
import sys
import re
# raiz da worktree onde este script vive (NÃO o checkout principal — provisioning/ só existe aqui)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.estoque.provisioning.sa_retorno_industrializacao import SA_BODY_G1
from app.odoo.estoque.scripts.descoberta_industrializacao import DescobertaIndustrializacaoService

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
CHAVE_REMESSA_ESPERADA = '35260661724241000178550010000946041007356795'


def main():
    nf1 = int(sys.argv[1]) if len(sys.argv) > 1 else 791437
    o = get_odoo_connection(); assert o.authenticate(), 'FALHA AUTH'

    # 1) ORÁCULO (Python testado) — READ
    oracle = DescobertaIndustrializacaoService(o).descobrir_fonte_nf2(nf1)
    exp_comps = sorted([(c['product_id'], round(c['qty'], 4)) for c in oracle['componentes']])
    print(f"ORÁCULO: ncomp={len(oracle['componentes'])} total={oracle['total']:.5f} "
          f"remessa_pick={oracle['remessa']['picking_id']}")

    # 2) corpo do canary = genealogia do SA_BODY_G1 (truncada antes da montagem) + log
    head = SA_BODY_G1.split('# === MONTAGEM')[0].rstrip()
    canary = head + (
        "\n        _total = sum(acc[p.id] * precos.get(p.id, p.standard_price) for p in comps)"
        "\n        _comps = sorted([(p.id, round(acc[p.id], 4)) for p in comps])"
        "\n        log('CANARY-G1 ncomp=%s total=%s chave=%s comps=%s' % "
        "(len(comps), round(_total, 5), chave_remessa or 'FALTA', str(_comps)))\n")

    # 3) SA EFÊMERA read-only (NADA de account.move) — create → run(active_id=nf1) → unlink
    mid = o.execute_kw('ir.model', 'search', [[('model', '=', 'account.move')]], {'context': CTX})[0]
    sa = o.execute_kw('ir.actions.server', 'create',
                      [{'name': 'ZZ CANARY G1 READONLY - DELETAR', 'model_id': mid,
                        'state': 'code', 'code': canary}], {'context': CTX})
    print(f"SA canary {sa} criada (read-only, NÃO cria NF); rodando active_id={nf1}...")
    try:
        o.execute_kw('ir.actions.server', 'run', [[sa]],
                     {'context': dict(CTX, active_model='account.move', active_id=nf1, active_ids=[nf1])},
                     timeout_override=180)
    except Exception as e:
        print('  run aviso:', str(e)[:240])
    lg = o.execute_kw('ir.logging', 'search_read', [[('message', '=like', 'CANARY-G1%')]],
                      {'fields': ['message'], 'order': 'id desc', 'limit': 1, 'context': CTX})
    o.execute_kw('ir.actions.server', 'unlink', [[sa]], {'context': CTX})
    print(f"SA canary {sa} DELETADA")
    if not lg:
        print('❌ sem log CANARY-G1 — a SA não chegou ao log (genealogia errou OU pulou; ver run aviso)')
        return

    msg = lg[0]['message']
    print('\nLOG:', msg[:700])
    m = re.search(r'ncomp=(\d+) total=([\d.]+) chave=(\S+) comps=(\[.*\])', msg)
    if not m:
        print('❌ log não parseável'); return
    sa_n, sa_total, sa_chave = int(m.group(1)), float(m.group(2)), m.group(3)
    sa_comps = sorted(eval(m.group(4)))

    print('\n=== COMPARAÇÃO body(safe_eval) vs ORÁCULO ===')
    ok_n = sa_n == len(oracle['componentes'])
    ok_t = abs(sa_total - oracle['total']) < 0.01
    ok_c = sa_chave == CHAVE_REMESSA_ESPERADA
    ok_comps = sa_comps == exp_comps
    print(f"  ncomp:  body={sa_n} oráculo={len(oracle['componentes'])}  {'✅' if ok_n else '❌ DIVERGE'}")
    print(f"  total:  body={sa_total:.5f} oráculo={oracle['total']:.5f}  {'✅' if ok_t else '❌ DIVERGE'}")
    print(f"  chave:  body={sa_chave[:20]}...  {'✅' if ok_c else '❌ DIVERGE'}")
    print(f"  comps:  {'✅ idênticos (product_id+qty)' if ok_comps else '❌ DIVERGE'}")
    if not ok_comps:
        print('    body :', sa_comps)
        print('    orácl:', exp_comps)
    print('\n' + ('✅✅ CANARY G1 GENEALOGIA OK — safe_eval == oráculo'
                  if all([ok_n, ok_t, ok_c, ok_comps]) else '❌ CANARY G1 FALHOU — corrigir antes de prosseguir'))


if __name__ == '__main__':
    main()
