"""10 — Executar ajustes emergenciais FB (2026-05-18).

Aplica 9 transferências internas no Odoo FB (company_id=1):
- DE: lote consolidador `MIGRAÇÃO` (8 casos) ou `1012/24` (104000003)
- PARA: lote canônico parcial `MI ###-###/AA` ou `T20241014` (104000016)
- QTD: lista informada por Rafael em 2026-05-18

Não emite NF. Usa `StockInternalTransferService` (D006) — gera 1 stock.move
automático via inventory adjustment (auditável em Inventory > Reporting >
Stock Moves com origem "Physical Inventory").

NÃO toca `ajuste_estoque_inventario` na base local (decisão usuário:
corrigir base depois via sync das movimentações que aparecerão no Odoo).

Reversão: ver `docs/inventario-2026-05/PENDENCIAS.md` P2 (pendente).

Flags:
    --dry-run             (default) só valida, não escreve no Odoo
    --confirmar           executa real
    --apenas=E01,E02,...  executa subset (default: todos os 9)

Spec: docs/inventario-2026-05/AJUSTES_EMERGENCIAIS_FB.md
"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

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
logger = logging.getLogger('10_emergenciais')

COMPANY_ID = 1  # FB
LOCATION_ID = COMPANY_LOCATIONS[COMPANY_ID]  # 8


EMERGENCIAIS: List[Dict] = [
    {'id': 'E01', 'cod': '104000015', 'lote_de': 'MIGRAÇÃO',
     'lote_para': 'MI 027-098/26', 'qtd': 1175.0},
    {'id': 'E02', 'cod': '104000002', 'lote_de': 'MIGRAÇÃO',
     'lote_para': 'MI 036-124/26', 'qtd': 143.5},
    {'id': 'E03', 'cod': '104000004', 'lote_de': 'MIGRAÇÃO',
     'lote_para': 'MI 025-091/26', 'qtd': 53.0},
    {'id': 'E04', 'cod': '104000018', 'lote_de': 'MIGRAÇÃO',
     'lote_para': 'MI 168-349/25', 'qtd': 35.4},
    {'id': 'E05', 'cod': '104000006', 'lote_de': 'MIGRAÇÃO',
     'lote_para': 'MI 138-311/25', 'qtd': 6.4},
    {'id': 'E06', 'cod': '104000016', 'lote_de': 'MIGRAÇÃO',
     'lote_para': 'T20241014', 'qtd': 280.1},
    {'id': 'E07', 'cod': '104000001', 'lote_de': 'MIGRAÇÃO',
     'lote_para': 'MI 031-092/25', 'qtd': 6.635},
    {'id': 'E08', 'cod': '104000037', 'lote_de': 'MIGRAÇÃO',
     'lote_para': 'MI 074-177/25', 'qtd': 5.0},
    # E09: lote_de original '1012/24' (id=23189) tem saldo em FB/Pré-Produção/Linha Salmoura
    # (loc 27458), NÃO em FB/Estoque (loc 8). Trocado para '0909' (id=39223, 697 un em loc 8).
    # EXECUTADO 2026-05-18 14:38 via inventory adjustment puro (todos os lotes em loc 8
    # estavam 100% reservados em 19 pickings antigos — ver AJUSTES_EMERGENCIAIS_FB.md §5.1).
    {'id': 'E09', 'cod': '104000003', 'lote_de': '0909',
     'lote_para': 'MI 021-065/26', 'qtd': 30.0},
    # E10: adicionado 2026-05-18 15:00 — MIGRAÇÃO desse cod fora de FB/Estoque (em Virtual/Linhas).
    # DE = '0004/2025' (id=34910, 179.241 livres). Lote PARA '135/26' não bate padrão MI ###-###/AA.
    # EXECUTADO 2026-05-18 15:00 (lot_id_destino=57351 criado, quant=229248, tempo 1453ms).
    {'id': 'E10', 'cod': '102030201', 'lote_de': '0004/2025',
     'lote_para': '135/26', 'qtd': 2700.0},
]


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def resolver_product_id(odoo, cod: str) -> Optional[int]:
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
        logger.warning(f'cod {cod}: múltiplos product.product ativos {ativos}')
    return ativos[0]['id']


def buscar_lot_id_por_nome(odoo, nome: str, product_id: int) -> Optional[int]:
    """Busca stock.lot por nome exato. Em FB pode haver homônimos cross-product
    — filtramos por product_id E company_id=1."""
    res = odoo.search_read(
        'stock.lot',
        [['name', '=', nome],
         ['product_id', '=', product_id],
         ['company_id', '=', COMPANY_ID]],
        ['id', 'name'], limit=2,
    )
    if not res:
        return None
    if len(res) > 1:
        logger.warning(
            f'Lote {nome!r} cod product_id={product_id}: {len(res)} matches '
            f'{res}. Usando o primeiro.'
        )
    return res[0]['id']


def saldo_quant(odoo, product_id: int, lot_id: int) -> float:
    """Soma quant.quantity para (product, company=1, location=8, lot)."""
    quants = odoo.search_read(
        'stock.quant',
        [['product_id', '=', product_id],
         ['company_id', '=', COMPANY_ID],
         ['location_id', '=', LOCATION_ID],
         ['lot_id', '=', lot_id]],
        ['quantity', 'reserved_quantity'],
    )
    return sum(float(q['quantity']) for q in quants)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--confirmar', action='store_true', default=False)
    parser.add_argument('--apenas', type=str, default='',
                        help='Lista CSV de IDs: E01,E02,...')
    args = parser.parse_args()

    if args.confirmar:
        args.dry_run = False

    apenas = set(s.strip() for s in args.apenas.split(',') if s.strip())
    itens = [e for e in EMERGENCIAIS if not apenas or e['id'] in apenas]

    banner(
        f'EMERGENCIAIS FB — {"DRY-RUN" if args.dry_run else "EXECUÇÃO REAL"} '
        f'({len(itens)}/{len(EMERGENCIAIS)} itens)'
    )

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        transfer_svc = StockInternalTransferService(
            odoo=odoo, lot_svc=StockLotService(odoo=odoo)
        )

        resultados = []

        for e in itens:
            banner(f'{e["id"]} — cod {e["cod"]} → {e["lote_para"]} ({e["qtd"]})', '-')
            r = {**e, 'inicio': datetime.now().isoformat(timespec='seconds')}

            # 1. Resolver product_id
            pid = resolver_product_id(odoo, e['cod'])
            if not pid:
                r['status'] = 'FALHA'
                r['erro'] = f'cod {e["cod"]} não encontrado (active=True)'
                logger.error(r['erro'])
                resultados.append(r)
                continue
            r['product_id'] = pid
            logger.info(f'product_id={pid}')

            # 2. Resolver lot DE
            lot_de = buscar_lot_id_por_nome(odoo, e['lote_de'], pid)
            if not lot_de:
                r['status'] = 'FALHA'
                r['erro'] = f'lote DE {e["lote_de"]!r} não existe para product_id={pid}'
                logger.error(r['erro'])
                resultados.append(r)
                continue
            r['lot_id_de'] = lot_de

            # 3. Saldo origem
            saldo = saldo_quant(odoo, pid, lot_de)
            r['saldo_de_antes'] = saldo
            logger.info(f'lot DE id={lot_de} saldo={saldo}')
            if saldo < e['qtd']:
                r['status'] = 'FALHA'
                r['erro'] = (f'saldo DE={saldo} < qtd={e["qtd"]} '
                             f'(falta {e["qtd"] - saldo:.4f})')
                logger.error(r['erro'])
                resultados.append(r)
                continue

            # 4. Saldo destino atual (informativo)
            lot_para_existente = buscar_lot_id_por_nome(odoo, e['lote_para'], pid)
            r['lot_para_existia'] = lot_para_existente is not None
            if lot_para_existente:
                r['lot_id_para_pre'] = lot_para_existente
                r['saldo_para_antes'] = saldo_quant(odoo, pid, lot_para_existente)
                logger.info(
                    f'lote PARA já existe id={lot_para_existente} '
                    f'saldo_antes={r["saldo_para_antes"]}'
                )
            else:
                r['saldo_para_antes'] = 0.0
                logger.info(f'lote PARA {e["lote_para"]!r} será CRIADO')

            if args.dry_run:
                r['status'] = 'DRY_RUN_OK'
                logger.info('[DRY-RUN] não executado')
                resultados.append(r)
                continue

            # 5. Executar transferência (cria lote destino se preciso)
            try:
                res = transfer_svc.transferir_quantidade_para_lote(
                    product_id=pid,
                    company_id=COMPANY_ID,
                    location_id=LOCATION_ID,
                    qty=e['qtd'],
                    lot_id_origem=lot_de,
                    nome_lote_destino=e['lote_para'],
                )
                r.update({
                    'status': 'EXECUTADO',
                    'lot_id_para': res['lot_id_destino'],
                    'lote_para_criado_agora': res['lote_destino_criado_agora'],
                    'quant_origem_id': res['quant_origem_id'],
                    'quant_origem_qty_apos': res['quant_origem_qty_apos'],
                    'quant_destino_id': res['quant_destino_id'],
                    'quant_destino_qty_apos': res['quant_destino_qty_apos'],
                    'tempo_ms': res['tempo_ms'],
                })
                logger.info(
                    f'OK lote_id_destino={res["lot_id_destino"]} '
                    f'(criado_agora={res["lote_destino_criado_agora"]}) '
                    f'destino_apos={res["quant_destino_qty_apos"]} '
                    f'tempo={res["tempo_ms"]}ms'
                )
            except Exception as exc:
                r['status'] = 'FALHA'
                r['erro'] = str(exc)
                logger.exception(f'Falha em {e["id"]}: {exc}')
            resultados.append(r)

        # Resumo
        banner('RESUMO')
        for r in resultados:
            tag = r.get('status', '?')
            extra = (f' lot_para={r.get("lot_id_para")}' if 'lot_id_para' in r else '')
            erro = f' erro={r["erro"]!r}' if 'erro' in r else ''
            print(f'  {r["id"]} {tag} cod={r["cod"]} qtd={r["qtd"]}{extra}{erro}')

    return 0 if all(r.get('status') in ('EXECUTADO', 'DRY_RUN_OK') for r in resultados) else 1


if __name__ == '__main__':
    sys.exit(main())
