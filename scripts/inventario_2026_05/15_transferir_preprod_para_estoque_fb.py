"""15 - Transferir saldo MIGRACAO LIVRE Pre-Producao -> FB/Estoque (2026-05-18).

Apos cancelamento das 149 MOs antigas (script 14), as reservas em Pre-Prod
foram liberadas. Este script transfere o saldo LIVRE de MIGRACAO de cada
sub-location de Pre-Producao (Linha Balde/Vidro/Manual/Salmoura) para
FB/Estoque (loc=8) via inventory adjustment, MANTENDO o lote MIGRACAO.

Padrao: para cada quant em Pre-Prod com livre > 0:
1. Reduzir quant origem (Pre-Prod): write inventory_quantity = qty - livre
   + action_apply_inventory (gera stock.move Pre-Prod -> Virtual/Ajuste)
2. Aumentar/criar quant destino (FB/Estoque): write/create
   inventory_quantity = qty_atual + livre + action_apply_inventory
   (gera stock.move Virtual/Ajuste -> FB/Estoque)

Gera 2 stock.moves por quant transferido, ambos com origem 'Physical Inventory'.

NUNCA mexe em quantidade reservada (147k un ainda reservadas pelas 70 MOs
preservadas — 63 confirmed recentes + 7 em progress/to_close).

Flags:
    --dry-run             (default) so simula
    --confirmar           executa real
    --limite N            limite N quants (canary)
    --log-json PATH
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
LOG_SCRIPT_13 = (
    '/home/rafaelnascimento/projetos/frete_sistema/scripts/'
    'inventario_2026_05/auditoria/log_13_transf_migr_fb_20260518_224352.json'
)


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def listar_quants_pre_prod(odoo, lot_ids):
    """Lista quants MIGRACAO em Pre-Prod com saldo livre > 0."""
    quants = odoo.search_read(
        'stock.quant',
        [
            ['lot_id', 'in', lot_ids],
            ['company_id', '=', COMPANY_ID],
            ['location_id', 'in', list(PRE_PROD_LOCS.keys())],
            ['quantity', '>', 0],
        ],
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


def buscar_quant_destino(odoo, product_id: int, lot_id: int):
    """Quant em FB/Estoque (loc=8) para o mesmo (product, lot, company=1)."""
    quants = odoo.search_read(
        'stock.quant',
        [
            ['product_id', '=', product_id],
            ['company_id', '=', COMPANY_ID],
            ['location_id', '=', LOC_ESTOQUE],
            ['lot_id', '=', lot_id],
        ],
        ['id', 'quantity'], limit=1,
    )
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

    if not lid:
        r['status'] = 'FALHA'
        r['erro'] = 'quant sem lot_id (inesperado)'
        return r

    # Buscar/preparar destino
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
            novo_id = odoo.create('stock.quant', {
                'product_id': pid,
                'company_id': COMPANY_ID,
                'location_id': LOC_ESTOQUE,
                'lot_id': lid,
                'inventory_quantity': nova_dest,
            })
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--confirmar', action='store_true', default=False)
    parser.add_argument('--limite', type=int, default=0)
    parser.add_argument('--log-json', type=str, default='')
    args = parser.parse_args()
    if args.confirmar:
        args.dry_run = False

    banner(
        f'TRANSFERIR MIGRACAO Pre-Prod -> FB/Estoque — '
        f'{"DRY-RUN" if args.dry_run else "EXECUCAO REAL"}'
    )

    app = create_app()
    resultados = []
    with app.app_context():
        odoo = get_odoo_connection()
        with open(LOG_SCRIPT_13) as f:
            d_log = json.load(f)
        lot_ids = list(set(
            r['lot_id_origem'] for r in d_log['resultados']
            if r['status'] == 'FALHA_SEM_SALDO' and r.get('lot_id_origem')
        ))

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
