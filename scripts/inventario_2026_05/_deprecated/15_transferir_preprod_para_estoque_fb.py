"""15 - Transferir saldo LIVRE de Pre-Producao -> {emp}/Estoque.

Origem (2026-05-18): apos cancelar as 149 MOs antigas (script 14), transferir
o saldo LIVRE de MIGRACAO das sub-locations de Pre-Producao FB -> FB/Estoque.
GENERALIZADO (2026-05-20): aceita args para company, estoque destino e locais
de origem; o filtro por lote (log do script 13) virou OPCIONAL. Sem
--lot-source-log, processa TODOS os lotes dos locais (transfere todo o livre).

Padrao: para cada quant em Pre-Prod com livre > 0:
1. Reduzir quant origem (Pre-Prod): write inventory_quantity = qty - livre
   + action_apply_inventory (gera stock.move Pre-Prod -> Virtual/Ajuste)
2. Aumentar/criar quant destino ({emp}/Estoque): write/create
   inventory_quantity = qty_atual + livre + action_apply_inventory
   (gera stock.move Virtual/Ajuste -> {emp}/Estoque)

Gera 2 stock.moves por quant transferido, ambos com origem 'Physical Inventory'.
NUNCA mexe em quantidade reservada (deixa exatamente o reservado na origem).

Flags:
    --company N           company_id (default 1=FB)
    --estoque N           location destino (default 8=FB/Estoque)
    --locs "a,b,c"        csv de location_ids de origem (sobrescreve default)
    --lot-source-log PATH log do script 13 p/ filtrar lotes (opcional)
    --dry-run             (default) so simula
    --confirmar           executa real
    --limite N            limite N quants (canary)
    --log-json PATH

Ex (transferir TODO livre FB): --locs 4068,4066,4067,27458,30718,48,20140 --confirmar
"""
import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('15_transf_preprod')

COMPANY_ID = 1  # FB
LOC_ESTOQUE = 8  # FB/Estoque (destino)
PRE_PROD_LOCS = {
    4066: 'FB/Pre-Producao/Linha Vidro',
    4067: 'FB/Pre-Producao/Linha Manual',
    4068: 'FB/Pre-Producao/Linha Balde',
    27458: 'FB/Pre-Producao/Linha Salmoura',
}
CASAS_DECIMAIS = 6


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def listar_quants_pre_prod(odoo, lot_ids=None):
    """Lista quants em Pre-Prod com saldo livre > 0.

    Se lot_ids for None/vazio, NAO filtra por lote (processa TODOS os quants
    dos PRE_PROD_LOCS). Se informado, filtra so' esses lotes (comportamento
    historico via --lot-source-log).
    """
    domain = [
        ['company_id', '=', COMPANY_ID],
        ['location_id', 'in', list(PRE_PROD_LOCS.keys())],
        ['quantity', '>', 0],
    ]
    if lot_ids:
        domain.insert(0, ['lot_id', 'in', lot_ids])
    quants = odoo.search_read(
        'stock.quant', domain,
        ['id', 'quantity', 'reserved_quantity', 'location_id', 'lot_id', 'product_id'],
    )
    out = []
    for q in quants:
        qty = round(float(q['quantity']), CASAS_DECIMAIS)
        res = round(float(q.get('reserved_quantity') or 0), CASAS_DECIMAIS)
        livre = round(qty - res, CASAS_DECIMAIS)
        if livre > 0:
            q['_qty'] = qty
            q['_reserved'] = res
            q['_livre'] = livre
            out.append(q)
    return out


def buscar_quant_destino(odoo, product_id: int, lot_id):
    """Quant em {LOC_ESTOQUE} para o mesmo (product, lot, company).

    Se lot_id for None/False, busca quant sem lote.
    """
    domain = [
        ['product_id', '=', product_id],
        ['company_id', '=', COMPANY_ID],
        ['location_id', '=', LOC_ESTOQUE],
    ]
    domain.append(['lot_id', '=', lot_id] if lot_id else ['lot_id', '=', False])
    quants = odoo.search_read('stock.quant', domain, ['id', 'quantity'], limit=1)
    return quants[0] if quants else None


def processar_quant(odoo, q: Dict, dry_run: bool) -> Dict:
    """Transfere o saldo livre do quant Pre-Prod para FB/Estoque (mesmo lote)."""
    livre = q['_livre']
    qty_apos_origem = round(q['_qty'] - livre, CASAS_DECIMAIS)
    pid = q['product_id'][0]
    lid = q['lot_id'][0] if q.get('lot_id') else None
    loc_orig_id = q['location_id'][0]
    loc_orig_name = q['location_id'][1]

    r = {
        'quant_origem_id': q['id'],
        'product_id': pid,
        'product_name': (q['product_id'][1] or '')[:60],
        'lot_id': lid,
        'lot_name': (q['lot_id'][1] if q.get('lot_id') else None),
        'location_origem_id': loc_orig_id,
        'location_origem_name': loc_orig_name,
        'qty_origem_antes': q['_qty'],
        'reservada_origem': q['_reserved'],
        'livre_a_transferir': livre,
        'qty_origem_apos': qty_apos_origem,
        'inicio': datetime.now().isoformat(timespec='seconds'),
    }

    # Buscar/preparar destino (mesmo lote — ou sem lote, se origem sem lote)
    dest = buscar_quant_destino(odoo, pid, lid)
    if dest:
        r['quant_destino_id'] = dest['id']
        r['quant_destino_qty_antes'] = round(float(dest['quantity']), CASAS_DECIMAIS)
        r['quant_destino_acao'] = 'updated'
        nova_dest = round(r['quant_destino_qty_antes'] + livre, CASAS_DECIMAIS)
    else:
        r['quant_destino_id'] = None
        r['quant_destino_qty_antes'] = 0.0
        r['quant_destino_acao'] = 'create_pending' if dry_run else 'created'
        nova_dest = livre
    r['quant_destino_qty_apos'] = nova_dest

    if dry_run:
        r['status'] = 'DRY_RUN_OK'
        return r

    t0 = time.time()
    try:
        # 1. Reduzir quant origem
        odoo.write('stock.quant', [q['id']], {'inventory_quantity': qty_apos_origem})
        odoo.execute_kw('stock.quant', 'action_apply_inventory', [[q['id']]])

        # 2. Aumentar/criar quant destino
        if dest:
            odoo.write('stock.quant', [dest['id']], {'inventory_quantity': nova_dest})
            odoo.execute_kw('stock.quant', 'action_apply_inventory', [[dest['id']]])
        else:
            payload = {
                'product_id': pid,
                'company_id': COMPANY_ID,
                'location_id': LOC_ESTOQUE,
                'inventory_quantity': nova_dest,
            }
            if lid:
                payload['lot_id'] = lid
            novo_id = odoo.create('stock.quant', payload)
            r['quant_destino_id'] = novo_id
            odoo.execute_kw('stock.quant', 'action_apply_inventory', [[novo_id]])
        r['status'] = 'EXECUTADO'
        r['tempo_ms'] = int((time.time() - t0) * 1000)
    except Exception as exc:
        r['status'] = 'FALHA'
        r['erro'] = str(exc)
        r['tempo_ms'] = int((time.time() - t0) * 1000)
        logger.exception(f'Falha transferindo quant {q["id"]}: {exc}')
    return r


def main():
    global COMPANY_ID, LOC_ESTOQUE, PRE_PROD_LOCS
    parser = argparse.ArgumentParser()
    parser.add_argument('--company', type=int, default=COMPANY_ID,
                        help='company_id (default 1=FB)')
    parser.add_argument('--estoque', type=int, default=LOC_ESTOQUE,
                        help='location destino (default 8=FB/Estoque)')
    parser.add_argument('--locs', type=str, default='',
                        help='csv de location_ids de origem (sobrescreve PRE_PROD_LOCS default)')
    parser.add_argument('--lot-source-log', type=str, default='',
                        help='log do script 13 p/ filtrar so lotes FALHA_SEM_SALDO '
                             '(opcional; sem ele processa TODOS os lotes dos locais)')
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--confirmar', action='store_true', default=False)
    parser.add_argument('--limite', type=int, default=0)
    parser.add_argument('--log-json', type=str, default='')
    args = parser.parse_args()
    if args.confirmar:
        args.dry_run = False

    COMPANY_ID = args.company
    LOC_ESTOQUE = args.estoque
    if args.locs:
        PRE_PROD_LOCS = {int(x): f'loc_{int(x)}' for x in args.locs.split(',') if x.strip()}

    banner(
        f'TRANSFERIR Pre-Prod -> Estoque(loc={LOC_ESTOQUE}, company={COMPANY_ID}) — '
        f'{"DRY-RUN" if args.dry_run else "EXECUCAO REAL"} | origens={list(PRE_PROD_LOCS.keys())}'
    )

    app = create_app()
    resultados = []
    with app.app_context():
        odoo = get_odoo_connection()
        lot_ids = None
        if args.lot_source_log:
            with open(args.lot_source_log) as f:
                d_log = json.load(f)
            lot_ids = list(set(
                r['lot_id_origem'] for r in d_log['resultados']
                if r['status'] == 'FALHA_SEM_SALDO' and r.get('lot_id_origem')
            ))
            logger.info(f'Filtro de lote ativo (--lot-source-log): {len(lot_ids)} lotes')

        quants = listar_quants_pre_prod(odoo, lot_ids)
        if args.limite > 0:
            quants = quants[: args.limite]

        logger.info(f'Quants em Pre-Prod com livre > 0: {len(quants)}')
        total_livre = sum(q['_livre'] for q in quants)
        logger.info(f'Total livre a transferir: {total_livre:,.3f} un')
        print()

        for i, q in enumerate(quants, 1):
            r = processar_quant(odoo, q, args.dry_run)
            resultados.append(r)
            tag = r['status']
            if i <= 5 or i > len(quants) - 3 or i % 20 == 0:
                logger.info(
                    f'[{i:3}/{len(quants)}] {tag} '
                    f'quant={r["quant_origem_id"]} prod={r["product_name"][:30]} '
                    f'loc={r["location_origem_name"][-25:]} '
                    f'livre={r["livre_a_transferir"]:>10}'
                )

    banner('RESUMO')
    from collections import Counter
    cont = Counter(r['status'] for r in resultados)
    for s, n in cont.most_common():
        print(f'  {s:30s} {n:5d}')
    print(f'  {"TOTAL":30s} {len(resultados):5d}')
    print()
    cont_dest = Counter(r.get('quant_destino_acao') for r in resultados if 'quant_destino_acao' in r)
    print(f'  Sub-acoes destino: {dict(cont_dest)}')
    soma_transferida = sum(
        r['livre_a_transferir'] for r in resultados
        if r['status'] in ('EXECUTADO', 'DRY_RUN_OK')
    )
    print(f'\n  Soma transferida {"executada" if not args.dry_run else "DRY-RUN OK"}: '
          f'{soma_transferida:,.6f} un')

    log_path = args.log_json
    if not log_path:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_path = str(_THIS.parent / 'auditoria' / f'log_15_preprod_estoque_{ts}.json')
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            'args': vars(args),
            'company_id': COMPANY_ID,
            'pre_prod_locs': list(PRE_PROD_LOCS.keys()),
            'loc_destino': LOC_ESTOQUE,
            'total_quants': len(resultados),
            'contagem_status': dict(cont),
            'contagem_destino': dict(cont_dest),
            'soma_transferida': soma_transferida,
            'inicio_run': resultados[0]['inicio'] if resultados else None,
            'fim_run': datetime.now().isoformat(timespec='seconds'),
            'resultados': resultados,
        }, f, indent=2, default=str)
    print(f'\n  Log JSON: {log_path}')

    falhas = sum(1 for r in resultados if r['status'].startswith('FALHA'))
    return 0 if falhas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
