"""13 - Transferencia DE lote MIGRACAO PARA lotes canonicos em FB (2026-05-18).

Aplica transferencias internas no FB (company_id=1, location_id=8) via
INVENTORY ADJUSTMENT (`stock.quant.action_apply_inventory`). Reutiliza
`StockInternalTransferService.transferir_quantidade_para_lote` (D004/D005),
mesmo padrao dos emergenciais E01-E08 (script 10).

Origem: planilha "TRANSF DE MIGRAÇÃO.xlsx" enviada pelo usuario (446 linhas).

Hipotese de origem (DE) = lote `MIGRAÇÃO`:
- Nome do arquivo: "TRANSF DE MIGRACAO"
- Padrao identico aos emergenciais E01-E08 ja executados em producao
- Coluna `lote` na planilha eh o destino (PARA), nao a origem

Para cada linha:
1. Resolve product_id por default_code (active=True em FB)
2. Resolve lot_id_origem = busca lote 'MIGRAÇÃO' do produto em FB
3. Verifica saldo livre em FB/Estoque (loc=8) — desconta reservas
4. Chama transferir_quantidade_para_lote(qty, lot_origem, nome_lote_destino)
   - cria lote destino se nao existe (StockLotService.criar_se_nao_existe)
   - reduz quant origem via inventory_quantity + action_apply_inventory
   - cria/aumenta quant destino via inventory_quantity + action_apply_inventory

Gera 2 stock.move por transferencia (saida MIGRACAO + entrada lote destino),
auditavel em Inventory > Reporting > Stock Moves com origem "Physical Inventory".

Tratamento de 6 casas decimais identico aos scripts 11/12.

Flags:
    --dry-run             (default) so valida, nao escreve no Odoo
    --confirmar           executa real (sobrescreve --dry-run)
    --xlsx PATH           caminho do Excel
    --apenas-linhas N1,N2 executa subset (1-based) — debugging
    --limite N            executa so as primeiras N linhas (canary)
    --log-json PATH       salva log JSON estruturado

NAO toca `ajuste_estoque_inventario` na base local (mesmo principio dos
scripts 10/11/12 — sync das movimentacoes Odoo trara o resultado).
"""
import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

import pandas as pd  # noqa: E402

from app import create_app  # noqa: E402
from app.odoo.constants.locations import COMPANY_LOCATIONS  # noqa: E402
from app.odoo.services.stock_internal_transfer_service import (  # noqa: E402
    StockInternalTransferService,
)
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('13_transf_migr_fb')

COMPANY_ID = 1  # FB
LOCATION_ID = COMPANY_LOCATIONS[COMPANY_ID]  # 8
LOTE_ORIGEM = 'MIGRAÇÃO'  # com cedilha — padrao Nacom (script 10 emergenciais)
CASAS_DECIMAIS = 6
DEFAULT_XLSX = '/mnt/c/Users/rafael.nascimento/Downloads/TRANSF DE MIGRAÇÃO.xlsx'


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def resolver_product_id(odoo, cod: str) -> Optional[int]:
    """default_code -> product.product.id (active=True)."""
    res = odoo.search_read(
        'product.product', [['default_code', '=', cod]],
        ['id', 'name', 'active'], limit=5,
    )
    if not res:
        return None
    ativos = [r for r in res if r.get('active')]
    if not ativos:
        logger.warning(f'cod {cod}: encontrado mas TODOS inactive {res}')
        return None
    if len(ativos) > 1:
        logger.warning(
            f'cod {cod}: multiplos product.product ativos — usando primeiro'
        )
    return ativos[0]['id']


def saldo_quant_origem(
    odoo, product_id: int, lot_id: int,
) -> Dict[str, float]:
    """Soma quantity / reserved_quantity em FB/Estoque para o lote MIGRACAO.

    Retorna {quantity, reserved_quantity, livre}.
    """
    quants = odoo.search_read(
        'stock.quant',
        [
            ['product_id', '=', product_id],
            ['company_id', '=', COMPANY_ID],
            ['location_id', '=', LOCATION_ID],
            ['lot_id', '=', lot_id],
        ],
        ['id', 'quantity', 'reserved_quantity'],
    )
    qty = sum(float(q['quantity']) for q in quants)
    res = sum(float(q.get('reserved_quantity') or 0) for q in quants)
    return {
        'quantity': round(qty, CASAS_DECIMAIS),
        'reserved_quantity': round(res, CASAS_DECIMAIS),
        'livre': round(qty - res, CASAS_DECIMAIS),
        'n_quants': len(quants),
    }


def carregar_planilha(path: str) -> List[Dict]:
    """Le XLSX e retorna lista de dicts."""
    df = pd.read_excel(path, dtype={'cod': str, 'lote': str})
    df.columns = [c.strip() for c in df.columns]
    registros = []
    for idx, row in df.iterrows():
        registros.append({
            'idx': int(idx) + 1,
            'filial': str(row['filial']).strip(),
            'cod': str(row['cod']).strip(),
            'lote_destino': str(row['lote']).strip(),
            'diff_qtd': float(row['diff_qtd']),
        })
    return registros


def processar_linha(
    odoo,
    lot_svc: StockLotService,
    transfer_svc: StockInternalTransferService,
    item: Dict,
    dry_run: bool,
    saldo_consumido: Dict[int, float],
) -> Dict:
    """Resolve product/lotes/quant, valida, transfere.

    saldo_consumido: {product_id: qty ja transferida nesta execucao}
                     usado para validar saldos cumulativos no mesmo run.

    Status:
      'DRY_RUN_OK', 'EXECUTADO', 'SKIP_FILIAL', 'SKIP_QTD',
      'FALHA_PRODUCT', 'FALHA_LOTE_ORIGEM', 'FALHA_SEM_SALDO',
      'FALHA_LOTE_IGUAL', 'FALHA_ODOO'
    """
    r = {**item, 'inicio': datetime.now().isoformat(timespec='seconds')}

    # 1. Filtro filial=FB
    if item['filial'] != 'FB':
        r['status'] = 'SKIP_FILIAL'
        r['erro'] = f'filial {item["filial"]!r} != FB'
        return r

    # 2. Filtro: qtd deve ser positiva
    if item['diff_qtd'] <= 0:
        r['status'] = 'SKIP_QTD'
        r['erro'] = f'diff_qtd {item["diff_qtd"]} <= 0'
        return r

    # 3. Resolver product
    pid = resolver_product_id(odoo, item['cod'])
    if not pid:
        r['status'] = 'FALHA_PRODUCT'
        r['erro'] = f'default_code {item["cod"]!r} nao encontrado em FB'
        return r
    r['product_id'] = pid

    # 4. Validar: lote destino == 'MIGRACAO'? (no-op, evita auto-transferencia)
    if item['lote_destino'].upper().strip() in ('MIGRACAO', 'MIGRAÇÃO'):
        r['status'] = 'FALHA_LOTE_IGUAL'
        r['erro'] = f'lote destino == origem ({LOTE_ORIGEM!r})'
        return r

    # 5. Resolver lote ORIGEM (MIGRACAO)
    lot_origem = lot_svc.buscar_por_nome(LOTE_ORIGEM, pid, COMPANY_ID)
    if not lot_origem:
        r['status'] = 'FALHA_LOTE_ORIGEM'
        r['erro'] = (
            f'lote {LOTE_ORIGEM!r} nao existe para product_id={pid} em FB'
        )
        return r
    r['lot_id_origem'] = lot_origem

    # 6. Saldo em FB/Estoque
    saldo = saldo_quant_origem(odoo, pid, lot_origem)
    r['saldo_origem'] = saldo

    qtd = round(item['diff_qtd'], CASAS_DECIMAIS)
    if abs(qtd - item['diff_qtd']) > 1e-9:
        r['qtd_truncada_em_6_casas'] = True
    r['qtd_solicitada'] = qtd

    ja_consumido = saldo_consumido.get(pid, 0.0)
    disponivel = round(saldo['livre'] - ja_consumido, CASAS_DECIMAIS)
    r['saldo_livre_disponivel_apos_run'] = disponivel
    r['saldo_ja_consumido_run'] = round(ja_consumido, CASAS_DECIMAIS)

    if qtd > disponivel:
        r['status'] = 'FALHA_SEM_SALDO'
        r['erro'] = (
            f'qtd={qtd} > disponivel={disponivel} '
            f'(saldo total MIGRACAO={saldo["quantity"]} '
            f'reservado={saldo["reserved_quantity"]} '
            f'ja_consumido_run={ja_consumido})'
        )
        return r

    # 7. Resolver lote destino (read-only no dry-run, criar no execute)
    lot_destino_existente = lot_svc.buscar_por_nome(
        item['lote_destino'], pid, COMPANY_ID,
    )
    r['lote_destino_acao'] = (
        'reused' if lot_destino_existente else
        ('create_pending' if dry_run else 'created')
    )
    if lot_destino_existente:
        r['lot_id_destino'] = lot_destino_existente

    # 8. DRY-RUN -> consumir saldo simulado e sair
    if dry_run:
        saldo_consumido[pid] = ja_consumido + qtd
        r['status'] = 'DRY_RUN_OK'
        return r

    # 9. EXECUTAR via service (cria lote destino se preciso + transfere)
    t0 = time.time()
    try:
        res = transfer_svc.transferir_quantidade_para_lote(
            product_id=pid,
            company_id=COMPANY_ID,
            location_id=LOCATION_ID,
            qty=qtd,
            lot_id_origem=lot_origem,
            nome_lote_destino=item['lote_destino'],
        )
        r['status'] = 'EXECUTADO'
        r['lot_id_destino'] = res['lot_id_destino']
        r['lote_destino_criado_agora'] = res['lote_destino_criado_agora']
        r['quant_origem_id'] = res['quant_origem_id']
        r['quant_origem_qty_apos'] = res['quant_origem_qty_apos']
        r['quant_destino_id'] = res['quant_destino_id']
        r['quant_destino_qty_apos'] = res['quant_destino_qty_apos']
        r['tempo_ms'] = int((time.time() - t0) * 1000)
        saldo_consumido[pid] = ja_consumido + qtd
    except Exception as exc:
        r['status'] = 'FALHA_ODOO'
        r['erro'] = str(exc)
        r['tempo_ms'] = int((time.time() - t0) * 1000)
        logger.exception(
            f'idx={item["idx"]} Falha na transferencia: {exc}'
        )
    return r


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--confirmar', action='store_true', default=False)
    parser.add_argument('--xlsx', type=str, default=DEFAULT_XLSX)
    parser.add_argument(
        '--apenas-linhas', type=str, default='',
        help='Lista CSV de indices 1-based: 1,2,5,10',
    )
    parser.add_argument(
        '--limite', type=int, default=0,
        help='Limite N primeiras linhas (canary). 0=todas',
    )
    parser.add_argument('--log-json', type=str, default='')
    args = parser.parse_args()

    if args.confirmar:
        args.dry_run = False

    apenas = set()
    if args.apenas_linhas:
        apenas = {int(s.strip()) for s in args.apenas_linhas.split(',') if s.strip()}

    if not Path(args.xlsx).exists():
        logger.error(f'XLSX nao encontrado: {args.xlsx}')
        return 2

    registros = carregar_planilha(args.xlsx)
    if apenas:
        registros = [r for r in registros if r['idx'] in apenas]
    if args.limite > 0:
        registros = registros[: args.limite]

    banner(
        f'TRANSFERENCIA MIGRACAO -> LOTE FB — '
        f'{"DRY-RUN" if args.dry_run else "EXECUCAO REAL"} ({len(registros)} linhas)'
    )
    logger.info(f'XLSX: {args.xlsx}')
    logger.info(
        f'COMPANY_ID={COMPANY_ID} LOCATION_ID={LOCATION_ID} '
        f'LOTE_ORIGEM={LOTE_ORIGEM!r}'
    )

    app = create_app()
    resultados = []
    saldo_consumido: Dict[int, float] = {}
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        transfer_svc = StockInternalTransferService(odoo=odoo, lot_svc=lot_svc)

        for item in registros:
            r = processar_linha(
                odoo, lot_svc, transfer_svc, item, args.dry_run, saldo_consumido,
            )
            resultados.append(r)
            status = r['status']
            lt = r.get('lote_destino_acao', '?')
            if status in ('EXECUTADO', 'DRY_RUN_OK'):
                logger.info(
                    f'[{r["idx"]:4}/{len(registros)}] {status} '
                    f'cod={r["cod"]} {LOTE_ORIGEM!r}-> '
                    f'{r["lote_destino"]!r:>14} qtd={r["qtd_solicitada"]} '
                    f'lote={lt}'
                )
            else:
                logger.warning(
                    f'[{r["idx"]:4}/{len(registros)}] {status} cod={r["cod"]} '
                    f'-> {r["lote_destino"]!r}: {r.get("erro")}'
                )

    banner('RESUMO')
    from collections import Counter
    cont = Counter(r['status'] for r in resultados)
    total = len(resultados)
    for status, n in cont.most_common():
        pct = n / total * 100 if total else 0
        print(f'  {status:30s} {n:5d}  ({pct:5.1f}%)')
    print(f'  {"TOTAL":30s} {total:5d}  (100.0%)')

    cont_lote = Counter(
        r.get('lote_destino_acao') for r in resultados
        if 'lote_destino_acao' in r
    )
    print('\n  Sub-acoes lote destino:', dict(cont_lote))

    soma_ajustada = sum(
        r['qtd_solicitada'] for r in resultados
        if r['status'] in ('EXECUTADO', 'DRY_RUN_OK')
    )
    print(f'\n  Soma qtd transferida {"executada" if not args.dry_run else "DRY-RUN OK"}: '
          f'{soma_ajustada:,.6f} un')

    log_path = args.log_json
    if not log_path:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_path = str(
            _THIS.parent / 'auditoria' / f'log_13_transf_migr_fb_{ts}.json'
        )
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            'args': vars(args),
            'company_id': COMPANY_ID,
            'location_id': LOCATION_ID,
            'lote_origem': LOTE_ORIGEM,
            'casas_decimais': CASAS_DECIMAIS,
            'xlsx': args.xlsx,
            'total': total,
            'contagem_status': dict(cont),
            'contagem_lote_destino_acao': dict(cont_lote),
            'soma_transferida': soma_ajustada,
            'inicio_run': resultados[0]['inicio'] if resultados else None,
            'fim_run': datetime.now().isoformat(timespec='seconds'),
            'resultados': resultados,
        }, f, indent=2, default=str)
    print(f'\n  Log JSON: {log_path}')

    falhas = sum(1 for r in resultados if r['status'].startswith('FALHA'))
    return 0 if falhas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
