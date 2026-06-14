#!/usr/bin/env python3
"""G9 LEVANTAMENTO (READ-ONLY) — TODOS os casos de retorno de industrializacao desde 01/2025.

Gera a base p/ planejar o rollout das correcoes. Para cada NF de retorno (j847, com 5902):
  - data, valor dos insumos 5902 (= montante a regularizar por documento);
  - entrada FB pareada (pela chave NFe);
  - status do periodo p/ cada perna (LF aberto >=2026-01-01 ; FB aberto >=2025-05-01).
Exporta CSV + imprime sumario (por ano, por status aberto/fechado, valor total).
NAO escreve no Odoo.
"""
import sys
import csv
from collections import defaultdict
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
OPS_5902 = [2864, 2710]
LF_LOCK = '2025-12-31'   # LF aberto a partir de 2026-01-01
FB_LOCK = '2025-04-30'   # FB aberto a partir de 2025-05-01
OUT_CSV = '/home/rafaelnascimento/projetos/frete_sistema/docs/industrializacao-fb-lf/g9_universo_desde_2025.csv'


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}\n")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    # 1) NFs de retorno LF desde 2025-01-01
    moves = rr('account.move',
               [('journal_id', '=', 847), ('company_id', '=', 5), ('state', '=', 'posted'),
                ('move_type', '=', 'out_invoice'), ('date', '>=', '2025-01-01')],
               ['id', 'name', 'date', 'l10n_br_chave_nf', 'amount_total'], limit=5000, order='date')
    print(f"NFs retorno LF (j847) desde 2025-01-01: {len(moves)}")
    move_ids = [m['id'] for m in moves]

    # 2) valor insumos 5902 por move (chunked read_group)
    val5902 = defaultdict(float)
    CH = 300
    for i in range(0, len(move_ids), CH):
        chunk = move_ids[i:i + CH]
        g = o.execute_kw('account.move.line', 'read_group',
                         [[('move_id', 'in', chunk), ('l10n_br_operacao_id', 'in', OPS_5902)],
                          ['credit:sum'], ['move_id']], {'context': CTX, 'lazy': False})
        for row in g:
            mid = row['move_id'][0] if isinstance(row.get('move_id'), list) else None
            if mid:
                val5902[mid] = row.get('credit', 0) or 0

    # 3) entradas FB pareadas pela chave
    chaves = [m['l10n_br_chave_nf'] for m in moves if m.get('l10n_br_chave_nf')]
    fb_by_chave = {}
    for i in range(0, len(chaves), CH):
        chunk = chaves[i:i + CH]
        fbs = rr('account.move',
                 [('company_id', '=', 1), ('l10n_br_chave_nf', 'in', chunk), ('move_type', '=', 'in_invoice')],
                 ['id', 'name', 'date', 'l10n_br_chave_nf', 'state'], limit=5000)
        for fb in fbs:
            fb_by_chave[fb['l10n_br_chave_nf']] = fb

    # 4) montar linhas + classificar
    rows = []
    for m in moves:
        chave = m.get('l10n_br_chave_nf')
        fb = fb_by_chave.get(chave)
        v = round(val5902.get(m['id'], 0), 2)
        lf_aberto = m['date'] > LF_LOCK
        fb_date = fb['date'] if fb else m['date']
        fb_aberto = fb_date > FB_LOCK
        rows.append({
            'lf_move_id': m['id'], 'lf_nome': m['name'], 'data': m['date'],
            'valor_insumos_5902': v, 'chave': chave,
            'fb_move_id': fb['id'] if fb else '', 'fb_nome': fb['name'] if fb else 'NAO_ACHADA',
            'fb_data': fb_date,
            'lf_periodo': 'ABERTO' if lf_aberto else 'FECHADO',
            'fb_periodo': 'ABERTO' if fb_aberto else 'FECHADO',
        })

    # 5) CSV
    with open(OUT_CSV, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"CSV gravado: {OUT_CSV} ({len(rows)} linhas)\n")

    # 6) sumarios
    def ano(d):
        return d[:4]

    print("=== por ANO: nº NFs / valor insumos a regularizar ===")
    by_year = defaultdict(lambda: [0, 0.0])
    for r in rows:
        by_year[ano(r['data'])][0] += 1
        by_year[ano(r['data'])][1] += r['valor_insumos_5902']
    tot_n = tot_v = 0
    for y in sorted(by_year):
        n, v = by_year[y]
        tot_n += n; tot_v += v
        print(f"   {y}: {n:5} NFs   R$ {v:>16,.2f}")
    print(f"   TOTAL: {tot_n} NFs   R$ {tot_v:,.2f}")

    print("\n=== perna LF (baixa PASSIVA) — por status de periodo ===")
    lf_stat = defaultdict(lambda: [0, 0.0])
    for r in rows:
        lf_stat[r['lf_periodo']][0] += 1
        lf_stat[r['lf_periodo']][1] += r['valor_insumos_5902']
    for s, (n, v) in lf_stat.items():
        print(f"   {s}: {n:5} NFs   R$ {v:>16,.2f}   ({'per-documento direto' if s=='ABERTO' else 'ajuste agregado / reabrir'})")

    print("\n=== perna FB (baixa ATIVA) — por status de periodo ===")
    fb_stat = defaultdict(lambda: [0, 0.0])
    for r in rows:
        fb_stat[r['fb_periodo']][0] += 1
        fb_stat[r['fb_periodo']][1] += r['valor_insumos_5902']
    for s, (n, v) in fb_stat.items():
        print(f"   {s}: {n:5} NFs   R$ {v:>16,.2f}   ({'per-documento direto' if s=='ABERTO' else 'ajuste agregado / reabrir'})")

    sem_fb = sum(1 for r in rows if r['fb_nome'] == 'NAO_ACHADA')
    print(f"\n   NFs sem entrada FB localizada (pela chave): {sem_fb}/{len(rows)}")

    print("\n[FIM G9 LEVANTAMENTO — nada escrito no Odoo]")


if __name__ == '__main__':
    main()
