# etapa: validado
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""14 - Ajuste positivo CD V2 (2026-05-18).

Aplica ajustes POSITIVOS de saldo no CD (company_id=4) via inventory
adjustment puro (`stock.quant.inventory_quantity` + `action_apply_inventory`).

Origem: planilha "AJUSTE SALDO CD.xlsx" (versao 4 enviada pelo usuario com
15 linhas, todos filial=CD e qtd > 0).

NOTA: V2 vs script 12:
- Schema NOVO: filial, cod, lote, qtd (era EMP, COD, LOTE, AJUSTE)
- filial em vez de EMP (V3 schema do script 13)
- Coluna `qtd` em vez de `diff_qtd` do script 13

Cria stock.lot e/ou stock.quant se nao existirem (padrao herdado scripts 12/13).
Gera 1 stock.move automatico por quant ajustado (origem "Physical Inventory"
em Inventory > Reporting > Stock Moves).

Tratamento de 6 casas decimais identico aos scripts anteriores.

Flags:
    --dry-run             (default) so valida, nao escreve no Odoo
    --confirmar           executa real (sobrescreve --dry-run)
    --xlsx PATH           caminho do Excel (default: AJUSTE SALDO CD.xlsx)
    --apenas-linhas N1,N2 executa subset de indices (1-based) — debugging
    --log-json PATH       salva log JSON estruturado

NAO toca `ajuste_estoque_inventario` na base local (mesmo principio dos
scripts 10, 11, 12 e 13).
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
# ARQUIVADO 2026-05-23 — movido para _validados/ajustando-quant-odoo/ (2 niveis abaixo).
# parents[2] (era repo root) → parents[4] após o move. Skill substituta: ajustando-quant-odoo.
sys.path.insert(0, str(_THIS.parents[4]))

import pandas as pd  # noqa: E402

from app import create_app  # noqa: E402
from app.odoo.constants.locations import COMPANY_LOCATIONS  # noqa: E402
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('14_ajuste_pos_cd_v2')

COMPANY_ID = 4  # CD
LOCATION_ID = COMPANY_LOCATIONS[COMPANY_ID]  # 32
CASAS_DECIMAIS = 6
DEFAULT_XLSX = '/mnt/c/Users/rafael.nascimento/Downloads/AJUSTE SALDO CD.xlsx'

# Schema esperado do XLSX (versao 4 — lowercase, qtd)
COL_FILIAL = 'filial'
COL_COD = 'cod'
COL_LOTE = 'lote'
COL_QTD = 'qtd'


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def resolver_product_id(odoo, cod: str) -> Optional[Dict]:
    """Resolve default_code -> dict com id/name/active/detailed_type
    (active=True). Retorna detailed_type para detectar produtos consumiveis
    (que falham em stock.quant.create — ver script 13 cod 104000085)."""
    res = odoo.search_read(
        'product.product', [['default_code', '=', cod]],
        ['id', 'name', 'active', 'detailed_type'], limit=5,
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
    return ativos[0]  # retorna dict completo (id + detailed_type)


def buscar_quant(
    odoo, product_id: int, lot_id: int,
) -> Optional[Dict]:
    """Retorna o quant em (product, CD, location=32, lot) ou None."""
    quants = odoo.search_read(
        'stock.quant',
        [
            ['product_id', '=', product_id],
            ['company_id', '=', COMPANY_ID],
            ['location_id', '=', LOCATION_ID],
            ['lot_id', '=', lot_id],
        ],
        ['id', 'quantity', 'reserved_quantity', 'location_id'],
        limit=2,
    )
    if not quants:
        return None
    if len(quants) > 1:
        logger.warning(
            f'product={product_id} lot={lot_id}: {len(quants)} quants no '
            f'mesmo location — usando primeiro {quants}'
        )
    return quants[0]


def carregar_planilha(path: str) -> List[Dict]:
    """Le XLSX e retorna lista de dicts {idx, filial, cod, lote, qtd}."""
    df = pd.read_excel(path, dtype={COL_COD: str, COL_LOTE: str})
    df.columns = [c.strip() for c in df.columns]
    obrig = {COL_FILIAL, COL_COD, COL_LOTE, COL_QTD}
    faltam = obrig - set(df.columns)
    if faltam:
        raise ValueError(
            f'XLSX sem colunas obrigatorias: {faltam}. Colunas presentes: {list(df.columns)}'
        )
    registros = []
    for idx, row in df.iterrows():
        registros.append({
            'idx': int(idx) + 1,
            'filial': str(row[COL_FILIAL]).strip(),
            'cod': str(row[COL_COD]).strip(),
            'lote': str(row[COL_LOTE]).strip(),
            'qtd': float(row[COL_QTD]),
        })
    return registros


def processar_linha(
    odoo,
    lot_svc: StockLotService,
    item: Dict,
    dry_run: bool,
) -> Dict:
    """Resolve product/lote/quant, valida, aplica ajuste positivo.

    Status possiveis:
      'DRY_RUN_OK', 'EXECUTADO', 'SKIP_FILIAL', 'SKIP_AJUSTE_NEGATIVO',
      'FALHA_PRODUCT', 'FALHA_PRODUTO_CONSUMIVEL', 'FALHA_LOTE', 'FALHA_ODOO'
    """
    r = {**item, 'inicio': datetime.now().isoformat(timespec='seconds')}

    # 1. Filtro filial=CD
    if item['filial'] != 'CD':
        r['status'] = 'SKIP_FILIAL'
        r['erro'] = f'filial {item["filial"]!r} != CD'
        return r

    # 2. Filtro: qtd deve ser positivo (escopo do script)
    if item['qtd'] <= 0:
        r['status'] = 'SKIP_AJUSTE_NEGATIVO'
        r['erro'] = f'qtd {item["qtd"]} <= 0 (escopo: somente positivos)'
        return r

    # 3. Resolver product
    prod = resolver_product_id(odoo, item['cod'])
    if not prod:
        r['status'] = 'FALHA_PRODUCT'
        r['erro'] = f'default_code {item["cod"]!r} nao encontrado em CD'
        return r
    pid = prod['id']
    r['product_id'] = pid
    r['detailed_type'] = prod.get('detailed_type')
    r['product_name'] = prod.get('name')

    # 3b. Validar que o produto eh armazenavel ('product') — consumivel
    # ('consu') e servico ('service') falham em stock.quant.create.
    # (Aprendizado script 13 — cod 104000085 AMOSTRA MANJERICAO consu)
    if prod.get('detailed_type') not in ('product',):
        r['status'] = 'FALHA_PRODUTO_CONSUMIVEL'
        r['erro'] = (
            f'detailed_type={prod.get("detailed_type")!r} '
            f'(somente armazenaveis aceitam stock.quant). '
            f'Alterar produto para detailed_type=product no Odoo antes.'
        )
        return r

    # 4. Resolver/criar lote
    lot_id_existente = lot_svc.buscar_por_nome(item['lote'], pid, COMPANY_ID)
    if lot_id_existente:
        r['lot_id'] = lot_id_existente
        r['lote_acao'] = 'reused'
    else:
        if dry_run:
            r['lote_acao'] = 'create_pending'
            r['lot_id'] = None
        else:
            try:
                novo_lot, criado_agora = lot_svc.criar_se_nao_existe(
                    item['lote'], pid, COMPANY_ID,
                )
                r['lot_id'] = novo_lot
                r['lote_acao'] = 'created' if criado_agora else 'reused'
            except Exception as exc:
                r['status'] = 'FALHA_LOTE'
                r['erro'] = f'falha criar lote {item["lote"]!r}: {exc}'
                return r

    # 5. Calcular ajuste em 6 casas decimais
    ajuste = round(item['qtd'], CASAS_DECIMAIS)
    if abs(ajuste - item['qtd']) > 1e-9:
        r['ajuste_truncado_em_6_casas'] = True
        logger.warning(
            f'idx={item["idx"]} qtd {item["qtd"]} truncado para {ajuste}'
        )
    r['ajuste_aplicado'] = ajuste

    # 6. Buscar quant
    if r.get('lot_id'):
        quant = buscar_quant(odoo, pid, r['lot_id'])
    else:
        quant = None

    if quant:
        r['quant_id'] = quant['id']
        r['quant_acao'] = 'updated'
        r['qty_antes'] = round(float(quant['quantity']), CASAS_DECIMAIS)
        r['reservada'] = round(
            float(quant.get('reserved_quantity') or 0), CASAS_DECIMAIS
        )
        r['qty_apos'] = round(r['qty_antes'] + ajuste, CASAS_DECIMAIS)
    else:
        r['quant_id'] = None
        r['quant_acao'] = 'create_pending' if dry_run else 'created'
        r['qty_antes'] = 0.0
        r['reservada'] = 0.0
        r['qty_apos'] = ajuste

    # 7. DRY-RUN -> parar
    if dry_run:
        r['status'] = 'DRY_RUN_OK'
        return r

    # 8. EXECUTAR
    t0 = time.time()
    try:
        if quant:
            odoo.write(
                'stock.quant', [quant['id']],
                {'inventory_quantity': r['qty_apos']},
            )
            odoo.execute_kw(
                'stock.quant', 'action_apply_inventory', [[quant['id']]],
            )
        else:
            quant_id = odoo.create('stock.quant', {
                'product_id': pid,
                'company_id': COMPANY_ID,
                'location_id': LOCATION_ID,
                'lot_id': r['lot_id'],
                'inventory_quantity': r['qty_apos'],
            })
            r['quant_id'] = quant_id
            odoo.execute_kw(
                'stock.quant', 'action_apply_inventory', [[quant_id]],
            )
        r['status'] = 'EXECUTADO'
        r['tempo_ms'] = int((time.time() - t0) * 1000)
    except Exception as exc:
        r['status'] = 'FALHA_ODOO'
        r['erro'] = str(exc)
        r['tempo_ms'] = int((time.time() - t0) * 1000)
        logger.exception(
            f'idx={item["idx"]} Falha ao aplicar ajuste positivo: {exc}'
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
        f'AJUSTE POSITIVO CD V2 — {"DRY-RUN" if args.dry_run else "EXECUCAO REAL"} '
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
            lt = r.get('lote_acao', '?')
            qt = r.get('quant_acao', '?')
            if status in ('EXECUTADO', 'DRY_RUN_OK'):
                logger.info(
                    f'[{r["idx"]:3}] {status} cod={r["cod"]} lote={r["lote"]!r:>14} '
                    f'lote={lt} quant={qt} {r.get("qty_antes")} '
                    f'-> {r.get("qty_apos")} (aj +{r.get("ajuste_aplicado")})'
                )
            else:
                logger.warning(
                    f'[{r["idx"]:3}] {status} cod={r["cod"]} lote={r["lote"]!r}: '
                    f'{r.get("erro")}'
                )

    banner('RESUMO')
    from collections import Counter
    cont = Counter(r['status'] for r in resultados)
    total = len(resultados)
    for status, n in cont.most_common():
        pct = n / total * 100
        print(f'  {status:30s} {n:4d}  ({pct:5.1f}%)')
    print(f'  {"TOTAL":30s} {total:4d}  (100.0%)')

    cont_lote = Counter(
        r.get('lote_acao') for r in resultados if 'lote_acao' in r
    )
    cont_quant = Counter(
        r.get('quant_acao') for r in resultados if 'quant_acao' in r
    )
    print('\n  Sub-acoes lote :', dict(cont_lote))
    print('  Sub-acoes quant:', dict(cont_quant))

    soma_ajustada = sum(
        r['ajuste_aplicado'] for r in resultados
        if 'ajuste_aplicado' in r and r['status'] in ('EXECUTADO', 'DRY_RUN_OK')
    )
    print(f'\n  Soma absoluta ajustes {"executados" if not args.dry_run else "DRY-RUN OK"}: '
          f'{soma_ajustada:.6f} un')

    log_path = args.log_json
    if not log_path:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_path = str(
            _THIS.parent / 'auditoria' / f'log_14_ajuste_pos_cd_v2_{ts}.json'
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
            'contagem_lote_acao': dict(cont_lote),
            'contagem_quant_acao': dict(cont_quant),
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
