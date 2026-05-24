"""Limpa reservas FANTASMA (move.lines 'assigned' sem lastro fisico) das MOs que
reservam nos locais de Pre-Producao FB+LF, via action_unreserve + action_assign.

Para cada MO com move.line assigned nesses locais:
  - mrp.production.action_unreserve  -> solta TODAS as reservas de componentes
  - se MO ativa (confirmed/progress/to_close) e --re-assign:
      mrp.production.action_assign   -> re-reserva SO o que existe fisicamente
  - MO done: so unreserve (nao re-reserva).

Efeito: as ~790k un fantasma somem; os ~26k un reais sao re-reservados.
NAO toca em estoque fisico — so desfaz/refaz reserva.

Flags:
    --states a,b,c   (default todos: draft,confirmed,progress,to_close,done)
    --no-reassign    nao re-reservar (so soltar) — usar p/ limpeza pura
    --dry-run        (default) so lista
    --confirmar      executa
    --limite N       canary
    --log-json PATH
"""
import argparse
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

_THIS = Path(__file__).resolve()
# ARQUIVADO 2026-05-23 — movido para _validados/operando-reservas-odoo/ (2 niveis abaixo).
# parents[2] (era repo root) → parents[4] após o move. Skill substituta: operando-reservas-odoo.
sys.path.insert(0, str(_THIS.parents[4]))

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s')
logger = logging.getLogger('limpar_reservas')

PREPROD_LOCS = [4068, 4066, 4067, 27458, 30718, 48, 20140, 53, 54]
ATIVAS = {'draft', 'confirmed', 'progress', 'to_close'}

# Odoo CIEL IT nao tem 'action_unreserve' em mrp.production; tentar candidatos.
UNRESERVE_METHODS = ['do_unreserve', 'button_unreserve', 'action_unreserve']
ASSIGN_METHODS = ['action_assign', 'button_assign', 'do_assign']
_metodo_ok = {}


def chamar(odoo, candidatos, ids, tipo):
    """Chama o 1o metodo candidato que existe (cacheia). 'does not exist' -> tenta proximo."""
    if tipo in _metodo_ok:
        odoo.execute_kw('mrp.production', _metodo_ok[tipo], [ids])
        return _metodo_ok[tipo]
    last = None
    for m in candidatos:
        try:
            odoo.execute_kw('mrp.production', m, [ids])
            _metodo_ok[tipo] = m
            return m
        except Exception as e:
            if 'does not exist' in str(e):
                last = e
                continue
            raise
    raise last or RuntimeError(f'nenhum metodo {tipo} disponivel')


def banner(t, c='='):
    print('\n' + c * 80)
    print(f'  {t}')
    print(c * 80)


def chunks(lst, n=200):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def snapshot(odoo):
    """(n_move_lines_assigned, reserved_total) nos locais."""
    n = odoo.execute_kw('stock.move.line', 'search_count',
                        [[['location_id', 'in', PREPROD_LOCS],
                          ['state', 'in', ['assigned', 'partially_available']],
                          ['quantity', '>', 0]]])
    rg = odoo.execute_kw('stock.quant', 'read_group',
                         [[['location_id', 'in', PREPROD_LOCS], ['reserved_quantity', '>', 0]],
                          ['reserved_quantity:sum'], ['location_id']], {'lazy': False})
    resv = sum(g.get('reserved_quantity') or 0 for g in rg)
    return n, round(resv, 2)


def coletar_mos(odoo, states):
    """MOs (id->state) que tem move.line assigned nos locais."""
    mls = odoo.search_read(
        'stock.move.line',
        [['location_id', 'in', PREPROD_LOCS],
         ['state', 'in', ['assigned', 'partially_available']], ['quantity', '>', 0]],
        ['move_id'])
    move_ids = list({m['move_id'][0] for m in mls if m.get('move_id')})
    mo_ids = set()
    for ch in chunks(move_ids):
        for mv in odoo.read('stock.move', ch, ['raw_material_production_id']):
            if mv.get('raw_material_production_id'):
                mo_ids.add(mv['raw_material_production_id'][0])
    mo_state = {}
    for ch in chunks(list(mo_ids)):
        for mo in odoo.read('mrp.production', ch, ['name', 'state']):
            if mo['state'] in states:
                mo_state[mo['id']] = (mo['name'], mo['state'])
    return mo_state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--states', default='draft,confirmed,progress,to_close,done')
    ap.add_argument('--no-reassign', action='store_true', default=False)
    ap.add_argument('--dry-run', action='store_true', default=True)
    ap.add_argument('--confirmar', action='store_true', default=False)
    ap.add_argument('--limite', type=int, default=0)
    ap.add_argument('--log-json', default='')
    args = ap.parse_args()
    if args.confirmar:
        args.dry_run = False
    states = [s.strip() for s in args.states.split(',') if s.strip()]
    re_assign = not args.no_reassign

    banner(f'LIMPAR RESERVAS FANTASMA — {"DRY-RUN" if args.dry_run else "EXECUCAO REAL"} | '
           f'states={states} | re-assign={re_assign}')

    app = create_app()
    resultados = []
    with app.app_context():
        odoo = get_odoo_connection()
        before = snapshot(odoo)
        logger.info(f'ANTES: move.lines assigned={before[0]} | reserved_total={before[1]:,.2f} un')

        mo_state = coletar_mos(odoo, states)
        ids = list(mo_state.keys())
        if args.limite > 0:
            ids = ids[:args.limite]
        # contagem por state
        cnt_st = Counter(mo_state[i][1] for i in ids)
        logger.info(f'MOs a processar: {len(ids)} -> {dict(cnt_st)}')

        for i, mid in enumerate(ids, 1):
            nome, st = mo_state[mid]
            r = {'mo_id': mid, 'name': nome, 'state': st}
            if args.dry_run:
                r['acao'] = 'unreserve' + ('+assign' if (st in ATIVAS and re_assign) else '')
                r['status'] = 'DRY_RUN_OK'
            else:
                t0 = time.time()
                try:
                    r['unreserve'] = chamar(odoo, UNRESERVE_METHODS, [mid], 'unreserve')
                    if st in ATIVAS and re_assign:
                        try:
                            r['assign'] = chamar(odoo, ASSIGN_METHODS, [mid], 'assign')
                        except Exception as e2:
                            r['assign'] = f'ERRO: {str(e2)[:120]}'
                    r['status'] = 'OK'
                    r['ms'] = int((time.time() - t0) * 1000)
                except Exception as exc:
                    r['status'] = 'FALHA'
                    r['erro'] = str(exc)[:200]
                    r['ms'] = int((time.time() - t0) * 1000)
            resultados.append(r)
            if not args.dry_run and (i <= 5 or i % 50 == 0 or i == len(ids)):
                logger.info(f'[{i:4}/{len(ids)}] {r["status"]} {nome} ({st})')

        if not args.dry_run:
            after = snapshot(odoo)
            logger.info(f'DEPOIS: move.lines assigned={after[0]} | reserved_total={after[1]:,.2f} un')

    banner('RESUMO')
    cont = Counter(r['status'] for r in resultados)
    for s, n in cont.most_common():
        print(f'  {s:20s} {n:5d}')
    print(f'  {"TOTAL MOs":20s} {len(resultados):5d}')
    if not args.dry_run:
        print(f'\n  move.lines assigned: {before[0]} -> {after[0]} (delta {after[0] - before[0]})')
        print(f'  reserved_total: {before[1]:,.2f} -> {after[1]:,.2f} un (delta {after[1] - before[1]:+,.2f})')
        falhas = [r for r in resultados if r['status'] == 'FALHA' or r.get('assign', '').startswith('ERRO')]
        if falhas:
            print(f'\n  FALHAS/ERROS ({len(falhas)}) — amostra:')
            for r in falhas[:10]:
                print(f'    {r["name"]} ({r["state"]}): {r.get("erro") or r.get("assign")}')

    log_path = args.log_json or str(
        _THIS.parent / 'auditoria' /
        f'log_limpar_reservas_{"dryrun" if args.dry_run else "real"}_{datetime.now():%Y%m%d_%H%M%S}.json')
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({'args': vars(args), 'before': before,
                   'after': after if not args.dry_run else None,
                   'contagem': dict(cont), 'resultados': resultados},
                  f, indent=2, default=str, ensure_ascii=False)
    print(f'\n  Log JSON: {log_path}')
    return 0 if not any(r['status'] == 'FALHA' for r in resultados) else 1


if __name__ == '__main__':
    sys.exit(main())
