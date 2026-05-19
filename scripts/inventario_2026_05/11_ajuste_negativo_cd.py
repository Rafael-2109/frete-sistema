"""11 - Ajuste negativo residual CD (2026-05-18).

Aplica ajustes NEGATIVOS de saldo no CD (company_id=4) via inventory
adjustment puro (`stock.quant.inventory_quantity` + `action_apply_inventory`).
Mesmo padrao usado em scripts/inventario_2026_05/10_executar_emergenciais_fb.py
(E09/E10) e em app/odoo/services/stock_internal_transfer_service.py.

Origem: planilha "AJUSTE SALDO CD.xlsx" enviada pelo usuario com 182 linhas
(COD, LOTE, AJUSTE). Todos AJUSTE < 0 e |AJUSTE| < 0.0001 (residuos de
arredondamento 6 casas decimais entre Odoo e fontes externas).

NAO emite NF (saldo residual nao justifica). Gera 1 stock.move automatico
por quant ajustada (origem "Physical Inventory" em Inventory > Reporting >
Stock Moves).

Tratamento de 6 casas decimais:
- Le AJUSTE como float (pode vir em notacao cientifica e-05)
- Calcula nova_qty = round(quantity_atual + ajuste, 6)
- Se ajuste cair fora de 6 casas (ex: e-08), reporta WARN mas mantem

Flags:
    --dry-run             (default) so valida, nao escreve no Odoo
    --confirmar           executa real (sobrescreve --dry-run)
    --xlsx PATH           caminho do Excel (default: AJUSTE SALDO CD.xlsx em Downloads WSL)
    --apenas-linhas N1,N2 executa subset de indices (1-based) — debugging
    --log-json PATH       salva log JSON estruturado (default: scripts/inventario_2026_05/auditoria/log_11_ajuste_cd_<ts>.json)

NAO toca `ajuste_estoque_inventario` na base local (mesmo principio do
script 10 emergenciais — sync das movimentacoes Odoo trara o resultado).
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
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('11_ajuste_cd')

COMPANY_ID = 4  # CD
LOCATION_ID = COMPANY_LOCATIONS[COMPANY_ID]  # 32
CASAS_DECIMAIS = 6
DEFAULT_XLSX = '/mnt/c/Users/rafael.nascimento/Downloads/AJUSTE SALDO CD.xlsx'


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def resolver_product_id(odoo, cod: str) -> Optional[int]:
    """Resolve default_code -> product.product.id (active=True)."""
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
            f'cod {cod}: multiplos product.product ativos '
            f'{[(r["id"], r["name"]) for r in ativos]} — usando primeiro'
        )
    return ativos[0]['id']


def saldo_quant_lote(
    odoo, product_id: int, lot_id: int
) -> List[Dict]:
    """Retorna TODOS os quants do (product, CD, location_id=32, lot).

    Pode haver multiplos quants em sub-locations (CD/Estoque, CD/Pre-Producao,
    etc) — para ajuste residual, focamos APENAS em LOCATION_ID=32 (estoque
    interno principal). Caller filtra.
    """
    return odoo.search_read(
        'stock.quant',
        [
            ['product_id', '=', product_id],
            ['company_id', '=', COMPANY_ID],
            ['location_id', '=', LOCATION_ID],
            ['lot_id', '=', lot_id],
        ],
        ['id', 'quantity', 'reserved_quantity', 'location_id'],
    )


def carregar_planilha(path: str) -> List[Dict]:
    """Le XLSX e retorna lista de dicts {idx, EMP, COD, LOTE, AJUSTE}."""
    df = pd.read_excel(path, dtype={'COD': str, 'LOTE': str})
    df.columns = [c.strip() for c in df.columns]
    registros = []
    for idx, row in df.iterrows():
        registros.append({
            'idx': int(idx) + 1,  # 1-based para humano
            'EMP': str(row['EMP']).strip(),
            'COD': str(row['COD']).strip(),
            'LOTE': str(row['LOTE']).strip(),
            'AJUSTE': float(row['AJUSTE']),
        })
    return registros


def processar_linha(
    odoo,
    lot_svc: StockLotService,
    item: Dict,
    dry_run: bool,
) -> Dict:
    """Resolve product/lote/quant, valida, aplica ajuste (se !dry_run).

    Returns dict com status:
      'DRY_RUN_OK', 'EXECUTADO', 'SKIP_EMP', 'SKIP_AJUSTE_POSITIVO',
      'FALHA_PRODUCT', 'FALHA_LOTE', 'FALHA_QUANT_VAZIO',
      'FALHA_QUANT_NEGATIVO', 'FALHA_RESERVADO', 'FALHA_ODOO'
    """
    r = {**item, 'inicio': datetime.now().isoformat(timespec='seconds')}

    # 1. Filtro EMP=CD
    if item['EMP'] != 'CD':
        r['status'] = 'SKIP_EMP'
        r['erro'] = f'EMP {item["EMP"]!r} != CD (esperado)'
        return r

    # 2. Filtro: AJUSTE deve ser negativo (escopo do script)
    if item['AJUSTE'] >= 0:
        r['status'] = 'SKIP_AJUSTE_POSITIVO'
        r['erro'] = f'AJUSTE {item["AJUSTE"]} >= 0 (escopo: somente negativos)'
        return r

    # 3. Resolver product
    pid = resolver_product_id(odoo, item['COD'])
    if not pid:
        r['status'] = 'FALHA_PRODUCT'
        r['erro'] = f'default_code {item["COD"]!r} nao encontrado em CD'
        return r
    r['product_id'] = pid

    # 4. Resolver lote (via service com fallback =like)
    lot_id = lot_svc.buscar_por_nome(item['LOTE'], pid, COMPANY_ID)
    if not lot_id:
        r['status'] = 'FALHA_LOTE'
        r['erro'] = (
            f'lote {item["LOTE"]!r} nao encontrado para '
            f'product_id={pid} company={COMPANY_ID}'
        )
        return r
    r['lot_id'] = lot_id

    # 5. Buscar quants (pode ter +1 quant em sub-locations diferentes
    # do LOCATION_ID padrao). Aqui filtramos so LOCATION_ID=32.
    quants = saldo_quant_lote(odoo, pid, lot_id)
    if not quants:
        r['status'] = 'FALHA_QUANT_VAZIO'
        r['erro'] = (
            f'sem quants em CD/Estoque (loc={LOCATION_ID}) para '
            f'product={pid} lot={lot_id}'
        )
        return r
    if len(quants) > 1:
        # Defensivo: nao deveria ocorrer (chave UK stock_quant_unique
        # cobre product+company+location+lot). Logar para visibilidade.
        logger.warning(
            f'idx={item["idx"]} cod={item["COD"]} lote={item["LOTE"]}: '
            f'{len(quants)} quants no mesmo location — usando primeiro {quants}'
        )
    quant = quants[0]
    qty_atual = round(float(quant['quantity']), CASAS_DECIMAIS)
    reservada = round(float(quant.get('reserved_quantity') or 0), CASAS_DECIMAIS)
    r['quant_id'] = quant['id']
    r['qty_antes'] = qty_atual
    r['reservada'] = reservada

    # 6. Calcular nova quantidade (6 casas decimais)
    ajuste = round(item['AJUSTE'], CASAS_DECIMAIS)
    # Se o ajuste excede 6 casas (improvavel mas defensivo), reportar
    if abs(ajuste - item['AJUSTE']) > 1e-9:
        r['ajuste_truncado_em_6_casas'] = True
        logger.warning(
            f'idx={item["idx"]} AJUSTE {item["AJUSTE"]} truncado para {ajuste} '
            f'(6 casas decimais)'
        )
    r['ajuste_aplicado'] = ajuste

    nova_qty = round(qty_atual + ajuste, CASAS_DECIMAIS)
    r['qty_apos'] = nova_qty

    # 7. Validacoes anti-negativacao
    if nova_qty < 0:
        r['status'] = 'FALHA_QUANT_NEGATIVO'
        r['erro'] = (
            f'qty_apos={nova_qty} < 0 (atual={qty_atual} ajuste={ajuste})'
        )
        return r
    # Saldo apos NAO pode ficar abaixo da reserva (gera reserva orfa)
    if nova_qty < reservada:
        r['status'] = 'FALHA_RESERVADO'
        r['erro'] = (
            f'qty_apos={nova_qty} < reservada={reservada} '
            f'(atual={qty_atual} ajuste={ajuste})'
        )
        return r

    # 8. DRY-RUN -> parar aqui
    if dry_run:
        r['status'] = 'DRY_RUN_OK'
        return r

    # 9. EXECUTAR: write inventory_quantity + action_apply_inventory
    t0 = time.time()
    try:
        odoo.write(
            'stock.quant', [quant['id']],
            {'inventory_quantity': nova_qty},
        )
        odoo.execute_kw(
            'stock.quant', 'action_apply_inventory', [[quant['id']]],
        )
        r['status'] = 'EXECUTADO'
        r['tempo_ms'] = int((time.time() - t0) * 1000)
    except Exception as exc:
        r['status'] = 'FALHA_ODOO'
        r['erro'] = str(exc)
        r['tempo_ms'] = int((time.time() - t0) * 1000)
        logger.exception(
            f'idx={item["idx"]} Falha ao aplicar inventory_quantity: {exc}'
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

    banner(
        f'AJUSTE NEGATIVO CD — {"DRY-RUN" if args.dry_run else "EXECUCAO REAL"} '
        f'({len(registros)} linhas)'
    )
    logger.info(f'XLSX: {args.xlsx}')
    logger.info(f'COMPANY_ID={COMPANY_ID} LOCATION_ID={LOCATION_ID}')

    app = create_app()
    resultados = []
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)

        for item in registros:
            r = processar_linha(odoo, lot_svc, item, args.dry_run)
            resultados.append(r)
            status = r['status']
            if status in ('EXECUTADO', 'DRY_RUN_OK'):
                logger.info(
                    f'[{r["idx"]:3}] {status} cod={r["COD"]} lote={r["LOTE"]!r:>14} '
                    f'qty {r.get("qty_antes")} -> {r.get("qty_apos")} '
                    f'(aj {r.get("ajuste_aplicado")})'
                )
            else:
                logger.warning(
                    f'[{r["idx"]:3}] {status} cod={r["COD"]} lote={r["LOTE"]!r}: '
                    f'{r.get("erro")}'
                )

    # Resumo
    banner('RESUMO')
    from collections import Counter
    cont = Counter(r['status'] for r in resultados)
    total = len(resultados)
    for status, n in cont.most_common():
        pct = n / total * 100
        print(f'  {status:30s} {n:4d}  ({pct:5.1f}%)')
    print(f'  {"TOTAL":30s} {total:4d}  (100.0%)')

    soma_ajustada = sum(
        r['ajuste_aplicado'] for r in resultados
        if 'ajuste_aplicado' in r and r['status'] in ('EXECUTADO', 'DRY_RUN_OK')
    )
    print(f'\n  Soma absoluta ajustes {"executados" if not args.dry_run else "DRY-RUN OK"}: '
          f'{abs(soma_ajustada):.6f} un')

    # Log JSON
    log_path = args.log_json
    if not log_path:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_path = str(
            _THIS.parent / 'auditoria' / f'log_11_ajuste_cd_{ts}.json'
        )
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            'args': vars(args),
            'company_id': COMPANY_ID,
            'location_id': LOCATION_ID,
            'casas_decimais': CASAS_DECIMAIS,
            'xlsx': args.xlsx,
            'total': total,
            'contagem_status': dict(cont),
            'soma_ajustada': soma_ajustada,
            'inicio_run': resultados[0]['inicio'] if resultados else None,
            'fim_run': datetime.now().isoformat(timespec='seconds'),
            'resultados': resultados,
        }, f, indent=2, default=str)
    print(f'\n  Log JSON: {log_path}')

    falhas = sum(1 for r in resultados if r['status'].startswith('FALHA'))
    return 0 if falhas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
