"""17 - Transferir saldo LF/Pre-Producao -> LF/Estoque (2026-05-19).

Adaptado do script 15 (FB) para LF. Necessario antes de faturar PERDA_LF_FB
porque varios cods do Excel 'LF - FB MIGRAÇÃO' tem saldo distribuido entre
LF/Estoque (42) e LF/Pré-Produção (53) + LF/Pré-Produção/Intermediário (30710).
A NF de PERDA precisa partir do LF/Estoque.

Para cada cod do Excel (filtro --xlsx):
1. Buscar quants em LF/Pre-Producao com quantity > 0
2. Para cada quant com livre > 0: transferir livre para LF/Estoque mantendo
   lote_id

Mecanismo: inventory adjustment via stock.quant.write({inventory_quantity})
+ action_apply_inventory. Gera stock.move Pre-Prod -> Virtual/Ajuste +
Virtual/Ajuste -> LF/Estoque.

Flags:
    --xlsx PATH           planilha com cods a processar (col 'cod')
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
from typing import Dict, List

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('17_transf_preprod_lf')

COMPANY_ID = 5  # LF
LOC_ESTOQUE = 42  # LF/Estoque
PRE_PROD_LOCS = {
    53: 'LF/Pré-Produção',
    30710: 'LF/Pré-Produção/Intermediário',
}
CASAS_DECIMAIS = 6


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def carregar_cods(xlsx_path: str) -> List[str]:
    import pandas as pd
    df = pd.read_excel(xlsx_path)
    return [str(int(c)) if isinstance(c, (int, float)) else str(c) for c in df['cod'].tolist()]


def listar_quants_pre_prod(odoo, product_ids: List[int]):
    """Lista quants em Pre-Prod LF dos product_ids com saldo livre > 0."""
    quants = odoo.search_read(
        'stock.quant',
        [
            ['product_id', 'in', product_ids],
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


def buscar_quant_destino(odoo, product_id: int, lot_id):
    """Quant em LF/Estoque (loc=42) para o mesmo (product, lot, company=5).

    Se lot_id for None/False, busca quant sem lote.
    """
    domain = [
        ['product_id', '=', product_id],
        ['company_id', '=', COMPANY_ID],
        ['location_id', '=', LOC_ESTOQUE],
    ]
    if lot_id:
        domain.append(['lot_id', '=', lot_id])
    else:
        domain.append(['lot_id', '=', False])
    quants = odoo.search_read('stock.quant', domain, ['id', 'quantity'], limit=1)
    return quants[0] if quants else None


def processar_quant(odoo, q: Dict, dry_run: bool) -> Dict:
    """Transfere o saldo livre do quant Pre-Prod para LF/Estoque (mesmo lote)."""
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

    # Buscar/preparar destino (mesmo lot — ou sem lote, se origem sem lote)
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--xlsx', type=str, required=True,
                        help='Planilha com coluna cod')
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--confirmar', action='store_true', default=False)
    parser.add_argument('--limite', type=int, default=0)
    parser.add_argument('--log-json', type=str, default='')
    args = parser.parse_args()
    if args.confirmar:
        args.dry_run = False

    banner(
        f'TRANSFERIR LF Pre-Prod -> LF/Estoque — '
        f'{"DRY-RUN" if args.dry_run else "EXECUCAO REAL"}'
    )

    cods = carregar_cods(args.xlsx)
    print(f'Cods do Excel: {len(cods)}')

    app = create_app()
    resultados = []
    with app.app_context():
        odoo = get_odoo_connection()
        prods = odoo.search_read('product.product',
            [['default_code', 'in', cods]], ['id', 'default_code'])
        pid_to_cod = {p['id']: p['default_code'] for p in prods}
        pids = list(pid_to_cod.keys())
        print(f'Produtos resolvidos no Odoo: {len(pids)}/{len(cods)}')

        quants = listar_quants_pre_prod(odoo, pids)
        if args.limite > 0:
            quants = quants[: args.limite]

        logger.info(f'Quants em LF/Pre-Prod com livre > 0: {len(quants)}')
        total_livre = sum(q['_livre'] for q in quants)
        logger.info(f'Total livre a transferir: {total_livre:,.3f} un')
        print()

        for i, q in enumerate(quants, 1):
            r = processar_quant(odoo, q, args.dry_run)
            # Adicionar default_code para auditoria
            r['cod_produto'] = pid_to_cod.get(r['product_id'])
            resultados.append(r)
            tag = r['status']
            if i <= 5 or i > len(quants) - 3 or i % 25 == 0:
                logger.info(
                    f'[{i:3}/{len(quants)}] {tag} '
                    f'quant={r["quant_origem_id"]} cod={r["cod_produto"]} '
                    f'loc={r["location_origem_name"][-25:]} '
                    f'livre={r["livre_a_transferir"]:>12}'
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
        modo = 'real' if not args.dry_run else 'dryrun'
        log_path = str(_THIS.parent / 'auditoria' / f'log_17_preprod_lf_estoque_{modo}_{ts}.json')
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            'args': vars(args),
            'company_id': COMPANY_ID,
            'pre_prod_locs': list(PRE_PROD_LOCS.keys()),
            'loc_destino': LOC_ESTOQUE,
            'cods_input': cods,
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
