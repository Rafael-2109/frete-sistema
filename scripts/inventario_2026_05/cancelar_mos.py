"""Cancelar Ordens de Producao (mrp.production) por criterio parametrizavel,
liberando automaticamente as reservas dos componentes (action_cancel).

Caso 2026-05-20: cancelar MOs criadas em 2024-2025 NAO efetivadas e SEM consumo
de materia-prima (libera reservas fantasma em Pre-Producao sem furo contabil).
As MOs com consumo>0 sao preservadas (mesmo criterio do script 14).

Mecanismo de cancelamento: mrp.production.action_cancel (igual script 14).
Seguranca: por padrao SO cancela MOs com consumo efetivado = 0
(soma de stock.move.quantity dos componentes). --consumo qualquer remove o filtro.

Flags:
    --create-de YYYY-MM-DD   (default 2024-01-01)
    --create-ate YYYY-MM-DD  (default 2026-01-01, exclusivo)
    --states a,b,c           (default draft,confirmed,progress,to_close)
    --empresas 1,3,4,5       (default todas do grupo)
    --consumo {zero,qualquer} (default zero = so sem consumo; SEGURO)
    --dry-run                (default) so lista
    --confirmar              executa action_cancel real
    --limite N               limita N MOs (canary)
    --log-json PATH
"""
import argparse
import json
import logging
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s')
logger = logging.getLogger('cancelar_mos')

COMPANIES = {1: 'FB', 3: 'SC', 4: 'CD', 5: 'LF'}


def banner(t, c='='):
    print('\n' + c * 80)
    print(f'  {t}')
    print(c * 80)


def chunks(lst, n=200):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def medir_consumo(odoo, mo_ids):
    """Soma stock.move.quantity (feito) dos componentes por MO. {mo_id: consumo}."""
    consumo = defaultdict(float)
    for ch in chunks(mo_ids):
        mv = odoo.search_read(
            'stock.move',
            [['raw_material_production_id', 'in', ch], ['state', '!=', 'cancel']],
            ['raw_material_production_id', 'quantity'])
        for m in mv:
            rid = m.get('raw_material_production_id')
            if rid:
                consumo[rid[0]] += float(m.get('quantity') or 0)
    return consumo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--create-de', default='2024-01-01')
    ap.add_argument('--create-ate', default='2026-01-01')
    ap.add_argument('--states', default='draft,confirmed,progress,to_close')
    ap.add_argument('--empresas', default='1,3,4,5')
    ap.add_argument('--consumo', choices=['zero', 'qualquer'], default='zero')
    ap.add_argument('--dry-run', action='store_true', default=True)
    ap.add_argument('--confirmar', action='store_true', default=False)
    ap.add_argument('--limite', type=int, default=0)
    ap.add_argument('--log-json', default='')
    args = ap.parse_args()
    if args.confirmar:
        args.dry_run = False

    states = [s.strip() for s in args.states.split(',') if s.strip()]
    empresas = [int(x) for x in args.empresas.split(',') if x.strip()]

    banner(f'CANCELAR MOs — {"DRY-RUN" if args.dry_run else "EXECUCAO REAL"} | '
           f'criadas {args.create_de}..{args.create_ate} | states={states} | '
           f'empresas={empresas} | consumo={args.consumo}')

    app = create_app()
    resultados = []
    with app.app_context():
        odoo = get_odoo_connection()
        mos = odoo.search_read(
            'mrp.production',
            [['create_date', '>=', args.create_de], ['create_date', '<', args.create_ate],
             ['state', 'in', states], ['company_id', 'in', empresas]],
            ['id', 'name', 'state', 'create_date', 'company_id', 'product_id'])
        logger.info(f'MOs no criterio (antes do filtro de consumo): {len(mos)}')

        consumo = medir_consumo(odoo, [m['id'] for m in mos])
        if args.consumo == 'zero':
            candidatas = [m for m in mos if consumo.get(m['id'], 0) <= 0.0001]
            excluidas = len(mos) - len(candidatas)
            logger.info(f'Excluidas por consumo>0 (preservadas): {excluidas}')
        else:
            candidatas = mos
        candidatas.sort(key=lambda m: m.get('create_date') or '')
        if args.limite > 0:
            candidatas = candidatas[:args.limite]

        # Resumo por empresa x state
        por_cs = defaultdict(int)
        for m in candidatas:
            cid = m['company_id'][0] if m.get('company_id') else None
            por_cs[(cid, m['state'])] += 1
        banner('CANDIDATAS a cancelar', '-')
        print(f"    {'EMP':4} {'draft':>7} {'confirmed':>10} {'progress':>9} {'to_close':>9} {'TOTAL':>7}")
        for cid, sigla in COMPANIES.items():
            row = [por_cs.get((cid, s), 0) for s in ['draft', 'confirmed', 'progress', 'to_close']]
            if sum(row):
                print(f"    {sigla:4} {row[0]:>7} {row[1]:>10} {row[2]:>9} {row[3]:>9} {sum(row):>7}")
        print(f'  TOTAL candidatas: {len(candidatas)}')

        for i, mo in enumerate(candidatas, 1):
            r = {'mo_id': mo['id'], 'name': mo['name'], 'state_antes': mo['state'],
                 'create_date': mo.get('create_date'),
                 'company': COMPANIES.get(mo['company_id'][0] if mo.get('company_id') else None),
                 'consumo': round(consumo.get(mo['id'], 0), 3),
                 'inicio': datetime.now().isoformat(timespec='seconds')}
            if args.dry_run:
                r['status'] = 'DRY_RUN_OK'
            else:
                t0 = time.time()
                try:
                    odoo.execute_kw('mrp.production', 'action_cancel', [[mo['id']]])
                    atual = odoo.search_read('mrp.production', [['id', '=', mo['id']]], ['state'])
                    r['state_apos'] = atual[0]['state'] if atual else '?'
                    r['status'] = 'CANCELADA' if r['state_apos'] == 'cancel' else 'NAO_CANCELOU'
                    r['tempo_ms'] = int((time.time() - t0) * 1000)
                except Exception as exc:
                    r['status'] = 'FALHA'
                    r['erro'] = str(exc)[:300]
                    r['tempo_ms'] = int((time.time() - t0) * 1000)
            resultados.append(r)
            if not args.dry_run and (i <= 5 or i % 50 == 0 or i == len(candidatas)):
                logger.info(f'[{i:4}/{len(candidatas)}] {r["status"]} {r["name"]} '
                            f'({r["company"]}, {r["state_antes"]})')

    banner('RESUMO')
    cont = Counter(r['status'] for r in resultados)
    for s, n in cont.most_common():
        print(f'  {s:24s} {n:5d}')
    print(f'  {"TOTAL":24s} {len(resultados):5d}')
    if not args.dry_run:
        falhas = [r for r in resultados if r['status'] in ('FALHA', 'NAO_CANCELOU')]
        if falhas:
            print(f'\n  FALHAS/NAO_CANCELOU ({len(falhas)}) — amostra:')
            for r in falhas[:10]:
                print(f'    {r["name"]} ({r["company"]},{r["state_antes"]}): '
                      f'{r.get("erro") or r.get("status")}')

    log_path = args.log_json or str(
        _THIS.parent / 'auditoria' /
        f'log_cancelar_mos_{"dryrun" if args.dry_run else "real"}_{datetime.now():%Y%m%d_%H%M%S}.json')
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({'args': vars(args), 'total': len(resultados),
                   'contagem_status': dict(cont), 'resultados': resultados},
                  f, indent=2, default=str, ensure_ascii=False)
    print(f'\n  Log JSON: {log_path}')
    return 0 if not any(r['status'] in ('FALHA',) for r in resultados) else 1


if __name__ == '__main__':
    sys.exit(main())
