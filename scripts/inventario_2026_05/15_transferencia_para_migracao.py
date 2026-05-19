"""15 - Transferencia DE lote_atual PARA lote MIGRACAO em FB+CD (2026-05-18).

Operacao INVERSA do script 13_transferencia_migracao_fb.py:
- Script 13: DE MIGRACAO PARA lote canonico
- Script 15 (este): DE lote_atual PARA MIGRACAO

Planilha origem: 'transf para MIGRAÇÃO.xlsx' (4.888 linhas):
- Colunas: filial (FB/CD), cod (default_code), lote (lote ORIGEM), diff_qtd (sempre <0)
- qty efetiva = abs(diff_qtd) — diff_qtd negativo = saida do lote atual
- 4867 FB + 21 CD

Reutiliza StockInternalTransferService.transferir_quantidade_para_lote
(mesmo padrao dos scripts 10, 13). Cria lote MIGRACAO destino se nao existe.

Tratamento dos casos especiais:
1. lote=NaN (38 linhas): SKIP com status SKIP_LOTE_VAZIO (impossivel
   resolver lote de origem)
2. lote == 'MIGRAÇÃO' (0 linhas atualmente, defensivo): SKIP SELF_LOOP
3. lotes literais 'LF/Estoque - XXX' (4 linhas): aceita literal — Odoo
   tem esses lotes cadastrados com esse nome exato
4. filial CD: company_id=4, location_id=32 (resolvido via COMPANY_LOCATIONS)

Flags:
    --dry-run             (default) so valida, nao escreve no Odoo
    --confirmar           executa real (sobrescreve --dry-run)
    --xlsx PATH           caminho do Excel
    --apenas-linhas N1,N2 executa subset (1-based)
    --limite N            primeiras N linhas (canary)
    --log-json PATH       caminho do log JSON
    --filial FB|CD        executa so 1 filial
"""
import argparse
import hashlib
import json
import logging
import sys
import time
from collections import Counter
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
logger = logging.getLogger('15_transf_para_migr')

FILIAL_TO_COMPANY = {'FB': 1, 'CD': 4, 'LF': 5}
LOTE_DESTINO = 'MIGRAÇÃO'  # cedilha — padrao Nacom
CASAS_DECIMAIS = 6
DEFAULT_XLSX = '/mnt/c/Users/rafael.nascimento/Downloads/transf para MIGRAÇÃO.xlsx'

# Lotes "proxy vazio" — criados a partir de produtos sem lote.
# Tratamento especial: representam saldos negativos em sub-locations
# e exigem operacao customizada (origem GANHA + destino PERDE).
# Por ora skipados — serao tratados em script separado.
LOTES_PROXY_VAZIO = {'P-15/05'}


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


def saldo_quant(
    odoo, product_id: int, lot_id, company_id: int, location_id: int,
) -> Dict[str, float]:
    """Soma quantity / reserved_quantity para 1 lote/location.

    `lot_id` pode ser int, None ou False (quants sem lote).
    Retorna {quantity, reserved_quantity, livre, n_quants}.
    """
    lot_filter = ['lot_id', '=', False] if lot_id in (None, False) else ['lot_id', '=', lot_id]
    quants = odoo.search_read(
        'stock.quant',
        [
            ['product_id', '=', product_id],
            ['company_id', '=', company_id],
            ['location_id', '=', location_id],
            lot_filter,
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


def buscar_quant_livre_qualquer_location(
    odoo, product_id: int, lot_id, company_id: int,
    locations_excluir: List[int],
) -> Optional[Dict]:
    """Busca quants do lote em QUALQUER location interna da company,
    exceto as ja tentadas. Retorna o quant com mais saldo livre,
    ou None se nenhum tem saldo livre.

    `lot_id` pode ser int, None ou False (quants sem lote).
    Util quando saldo=0 em location principal — lote pode estar em
    sub-location (FB/Pre-Producao, FB/Linha Salmoura, etc.).
    """
    lot_filter = ['lot_id', '=', False] if lot_id in (None, False) else ['lot_id', '=', lot_id]
    domain = [
        ['product_id', '=', product_id],
        ['company_id', '=', company_id],
        lot_filter,
        ['quantity', '>', 0],
    ]
    if locations_excluir:
        domain.append(['location_id', 'not in', locations_excluir])

    quants = odoo.search_read(
        'stock.quant', domain,
        ['id', 'quantity', 'reserved_quantity', 'location_id'],
        limit=50,
    )
    if not quants:
        return None
    # Filtrar so locations INTERNAS (nao virtual, nao transit)
    # buscando o location.usage='internal'
    loc_ids = list({q['location_id'][0] for q in quants if q['location_id']})
    locs = odoo.search_read(
        'stock.location',
        [['id', 'in', loc_ids]],
        ['id', 'name', 'complete_name', 'usage'],
    )
    locs_internal = {
        loc['id']: loc for loc in locs if loc.get('usage') == 'internal'
    }
    candidatos = []
    for q in quants:
        loc_id = q['location_id'][0] if q['location_id'] else None
        if loc_id not in locs_internal:
            continue
        qty = float(q['quantity'])
        res = float(q.get('reserved_quantity') or 0)
        livre = qty - res
        if livre > 0:
            candidatos.append({
                'quant_id': q['id'],
                'location_id': loc_id,
                'location_name': locs_internal[loc_id].get('complete_name'),
                'quantity': qty,
                'reserved_quantity': res,
                'livre': livre,
            })
    if not candidatos:
        return None
    # Ordenar por livre DESC
    candidatos.sort(key=lambda x: -x['livre'])
    return candidatos[0]


def _norm_lote(raw) -> Optional[str]:
    if pd.isna(raw):
        return None
    s = str(raw).strip()
    if not s or s.lower() == 'nan':
        return None
    return s


def carregar_planilha(path: str) -> List[Dict]:
    """Le XLSX. Suporta 2 esquemas:

    Schema A (legado): filial, cod, lote, diff_qtd
       - lote = lote_origem; destino assumido = LOTE_DESTINO (MIGRAÇÃO)
    Schema B (novo): filial, cod, LOTE ORIGEM, LOTE DESTINO, diff_qtd
       - lote_origem e lote_destino vem da planilha

    Em ambos, qty = abs(diff_qtd).
    """
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    cols_set = set(df.columns)

    schema_b = {'LOTE ORIGEM', 'LOTE DESTINO'}.issubset(cols_set)
    if schema_b:
        col_lote_orig = 'LOTE ORIGEM'
        col_lote_dest = 'LOTE DESTINO'
    elif 'lote' in cols_set:
        col_lote_orig = 'lote'
        col_lote_dest = None
    else:
        raise ValueError(
            f'XLSX sem colunas reconhecidas: {df.columns.tolist()}'
        )

    registros = []
    for idx, row in df.iterrows():
        diff_qtd = float(row['diff_qtd'])
        lote_origem = _norm_lote(row[col_lote_orig])
        lote_destino = (
            _norm_lote(row[col_lote_dest]) if col_lote_dest else None
        ) or LOTE_DESTINO
        registros.append({
            'idx': int(idx) + 1,
            'filial': str(row['filial']).strip(),
            'cod': str(row['cod']).strip(),
            'lote_origem_nome': lote_origem,
            'lote_destino_nome': lote_destino,
            'diff_qtd': diff_qtd,
        })
    return registros


def processar_linha_inner(
    odoo,
    lot_svc: StockLotService,
    transfer_svc: StockInternalTransferService,
    item: Dict,
    dry_run: bool,
    saldo_consumido: Dict[tuple, float],
) -> Dict:
    """Resolve product/lotes/quant, valida, transfere para MIGRACAO.

    saldo_consumido: {(product_id, lot_id_origem): qty_acumulada} no run.

    Status:
      'DRY_RUN_OK', 'EXECUTADO',
      'SKIP_LOTE_VAZIO', 'SKIP_SELF_LOOP', 'SKIP_QTD_ZERO', 'SKIP_FILIAL',
      'FALHA_FILIAL', 'FALHA_PRODUCT', 'FALHA_LOTE_ORIGEM',
      'FALHA_SEM_SALDO', 'FALHA_ODOO'
    """
    r = {**item, 'inicio': datetime.now().isoformat(timespec='seconds')}

    # 1. Mapear filial -> company / location
    company_id = FILIAL_TO_COMPANY.get(item['filial'])
    if not company_id:
        r['status'] = 'FALHA_FILIAL'
        r['erro'] = f'filial {item["filial"]!r} fora de FB/CD/LF'
        return r
    location_id = COMPANY_LOCATIONS[company_id]
    r['company_id'] = company_id
    r['location_id'] = location_id

    # 2. Lote origem: NaN ou P-15/05 mapeia para "sem lote" (lot_id=False)
    lote_origem_raw = item['lote_origem_nome']
    is_proxy_vazio = (
        lote_origem_raw is None or
        (isinstance(lote_origem_raw, str) and lote_origem_raw in LOTES_PROXY_VAZIO)
    )
    r['is_proxy_vazio'] = is_proxy_vazio

    # 2.2 diff_qtd POSITIVO indica direcao inversa (origem ganha, destino perde)
    # — operacao especial NAO suportada neste script
    if item['diff_qtd'] > 0:
        r['status'] = 'SKIP_QTD_POSITIVA'
        r['erro'] = (
            f'diff_qtd={item["diff_qtd"]} positivo indica origem GANHA + '
            f'destino PERDE — operacao inversa nao suportada'
        )
        return r

    # 3. Self-loop (origem == destino) — so checar se lote real
    lote_origem = lote_origem_raw
    lote_destino = item.get('lote_destino_nome') or LOTE_DESTINO
    if not is_proxy_vazio and lote_origem.strip() == lote_destino.strip():
        r['status'] = 'SKIP_SELF_LOOP'
        r['erro'] = f'lote origem == destino ({lote_destino!r})'
        return r

    # 4. Quantidade
    qty_solicitada = abs(item['diff_qtd'])
    if qty_solicitada <= 0:
        r['status'] = 'SKIP_QTD_ZERO'
        r['erro'] = f'diff_qtd {item["diff_qtd"]} resulta em qty 0'
        return r
    qty = round(qty_solicitada, CASAS_DECIMAIS)
    if abs(qty - qty_solicitada) > 1e-9:
        r['qtd_truncada_em_6_casas'] = True
    r['qtd_solicitada'] = qty

    # 5. Resolver produto
    pid = resolver_product_id(odoo, item['cod'])
    if not pid:
        r['status'] = 'FALHA_PRODUCT'
        r['erro'] = f'default_code {item["cod"]!r} nao encontrado'
        return r
    r['product_id'] = pid

    # 6. Resolver lote origem (literal — '0909/24', 'LF/Estoque - 0909/24', etc.)
    # Se proxy vazio (NaN ou P-15/05), lot_id_origem = None (quant sem lote)
    if is_proxy_vazio:
        lot_id_origem = None  # "sem lote" no Odoo (lot_id=False)
    else:
        lot_id_origem = lot_svc.buscar_por_nome(lote_origem, pid, company_id)
        if not lot_id_origem:
            r['status'] = 'FALHA_LOTE_ORIGEM'
            r['erro'] = (
                f'lote {lote_origem!r} nao existe para product_id={pid} '
                f'em company_id={company_id}'
            )
            return r
    r['lot_id_origem'] = lot_id_origem

    # 7. Saldo livre no run — tenta location principal primeiro
    saldo = saldo_quant(odoo, pid, lot_id_origem, company_id, location_id)
    r['saldo_origem'] = saldo
    location_efetiva = location_id

    # 7.1. Se saldo=0 em location principal, busca em sub-locations
    if saldo['quantity'] == 0:
        alt = buscar_quant_livre_qualquer_location(
            odoo, pid, lot_id_origem, company_id,
            locations_excluir=[location_id],
        )
        if alt:
            location_efetiva = alt['location_id']
            saldo = {
                'quantity': alt['quantity'],
                'reserved_quantity': alt['reserved_quantity'],
                'livre': alt['livre'],
                'n_quants': 1,
            }
            r['saldo_origem'] = saldo
            r['location_alternativa'] = {
                'id': alt['location_id'],
                'name': alt['location_name'],
            }

    key = (pid, lot_id_origem, location_efetiva)
    ja_consumido = saldo_consumido.get(key, 0.0)
    disponivel = round(saldo['livre'] - ja_consumido, CASAS_DECIMAIS)
    r['saldo_livre_disponivel_apos_run'] = disponivel
    r['saldo_ja_consumido_run'] = round(ja_consumido, CASAS_DECIMAIS)
    r['location_efetiva'] = location_efetiva

    # Tolerancia de arredondamento — mesma do service (0.001 un)
    TOL = 0.001
    if qty > disponivel:
        if qty - disponivel <= TOL and disponivel > 0:
            qty_efetiva = disponivel
            r['clamp_arredondamento'] = {'de': qty, 'para': qty_efetiva}
            qty = qty_efetiva
        elif disponivel > 0:
            # CLAMP PARCIAL: transfere so o disponivel, marca delta
            r['clamp_parcial'] = {
                'pedido': qty, 'disponivel': disponivel,
                'delta_nao_transferido': round(qty - disponivel, CASAS_DECIMAIS),
            }
            qty = disponivel
        else:
            r['status'] = 'FALHA_SEM_SALDO'
            r['erro'] = (
                f'qty={qty} > disponivel={disponivel} '
                f'(saldo total lote={saldo["quantity"]} '
                f'reservado={saldo["reserved_quantity"]} '
                f'ja_consumido_run={ja_consumido})'
            )
            return r

    # 8. Resolver lote destino — read-only no dry-run
    lot_destino_existente = lot_svc.buscar_por_nome(
        lote_destino, pid, company_id,
    )
    r['lote_destino_acao'] = (
        'reused' if lot_destino_existente else
        ('create_pending' if dry_run else 'created')
    )
    if lot_destino_existente:
        r['lot_id_destino'] = lot_destino_existente

    # 9. DRY-RUN — apenas consumir saldo simulado
    if dry_run:
        saldo_consumido[key] = ja_consumido + qty
        r['qtd_efetiva'] = qty
        r['status'] = 'DRY_RUN_OK'
        return r

    # 10. EXECUTAR via service
    t0 = time.time()
    try:
        res = transfer_svc.transferir_quantidade_para_lote(
            product_id=pid,
            company_id=company_id,
            location_id=location_efetiva,
            qty=qty,
            lot_id_origem=lot_id_origem,
            nome_lote_destino=lote_destino,
        )
        r['status'] = 'EXECUTADO'
        r['qtd_efetiva'] = qty
        r['lot_id_destino'] = res['lot_id_destino']
        r['lote_destino_criado_agora'] = res['lote_destino_criado_agora']
        r['quant_origem_id'] = res['quant_origem_id']
        r['quant_origem_qty_apos'] = res['quant_origem_qty_apos']
        r['quant_destino_id'] = res['quant_destino_id']
        r['quant_destino_qty_apos'] = res['quant_destino_qty_apos']
        r['tempo_ms'] = int((time.time() - t0) * 1000)
        saldo_consumido[key] = ja_consumido + qty
    except Exception as exc:
        r['status'] = 'FALHA_ODOO'
        r['erro'] = str(exc)
        r['tempo_ms'] = int((time.time() - t0) * 1000)
        logger.exception(
            f'idx={item["idx"]} Falha transferir cod={item["cod"]} '
            f'lote={item["lote_origem_nome"]!r}: {exc}'
        )
    return r


def processar_linha(
    odoo, lot_svc, transfer_svc, item, dry_run, saldo_consumido,
    max_retries: int = 5,
):
    """Wrapper resiliente: captura ProtocolError 503/timeouts + retry com backoff."""
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            return processar_linha_inner(
                odoo, lot_svc, transfer_svc, item,
                dry_run, saldo_consumido,
            )
        except Exception as exc:
            last_exc = exc
            msg = str(exc)
            transitorio = (
                '503' in msg or
                'Service Unavailable' in msg or
                'timeout' in msg.lower() or
                'timed out' in msg.lower() or
                'connection refused' in msg.lower() or
                'connection reset' in msg.lower() or
                'ProtocolError' in str(type(exc))
            )
            if not transitorio:
                logger.exception(
                    f'idx={item["idx"]} erro NAO-transitorio (sem retry): {exc}'
                )
                return {
                    **item,
                    'status': 'FALHA_ODOO',
                    'erro': f'(no retry) {exc}',
                    'inicio': datetime.now().isoformat(timespec='seconds'),
                }
            backoff = min(2 ** attempt, 60)  # 2,4,8,16,32 s (max 60)
            logger.warning(
                f'idx={item["idx"]} erro transitorio tentativa {attempt}/{max_retries}: '
                f'{exc} — aguardando {backoff}s'
            )
            time.sleep(backoff)
    # Esgotou tentativas
    logger.error(
        f'idx={item["idx"]} ESGOTOU {max_retries} tentativas: {last_exc}'
    )
    return {
        **item,
        'status': 'FALHA_ODOO',
        'erro': f'(esgotou retries) {last_exc}',
        'inicio': datetime.now().isoformat(timespec='seconds'),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--confirmar', action='store_true', default=False)
    parser.add_argument('--xlsx', type=str, default=DEFAULT_XLSX)
    parser.add_argument('--apenas-linhas', type=str, default='')
    parser.add_argument('--limite', type=int, default=0)
    parser.add_argument(
        '--retomar-de', type=int, default=0,
        help='Skip primeiras N linhas (idx 1-based). 520 retoma da linha 520.',
    )
    parser.add_argument(
        '--shard', type=str, default='',
        help='X/Y: roda so linhas onde hash(cod) %% Y == X-1 (ex: 1/4, 2/4, 3/4, 4/4)',
    )
    parser.add_argument('--log-json', type=str, default='')
    parser.add_argument(
        '--filial', type=str, default='',
        help='FB ou CD — filtra so 1 filial',
    )
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

    if args.filial:
        registros = [r for r in registros if r['filial'] == args.filial.upper()]
    if apenas:
        registros = [r for r in registros if r['idx'] in apenas]
    if args.retomar_de > 0:
        registros = [r for r in registros if r['idx'] >= args.retomar_de]
        logger.info(
            f'--retomar-de={args.retomar_de}: '
            f'{len(registros)} registros restantes'
        )
    if args.shard:
        x_str, y_str = args.shard.split('/')
        shard_x, shard_y = int(x_str), int(y_str)
        if not (1 <= shard_x <= shard_y):
            raise ValueError(f'shard X/Y invalido: {args.shard}')
        # Hash determinista por cod — mesmo produto sempre no mesmo shard
        def shard_de(cod):
            h = int(hashlib.md5(cod.encode()).hexdigest(), 16)
            return h % shard_y

        registros = [
            r for r in registros
            if shard_de(r['cod']) == (shard_x - 1)
        ]
        logger.info(
            f'--shard={args.shard}: {len(registros)} registros nesta shard'
        )
    if args.limite > 0:
        registros = registros[: args.limite]

    banner(
        f'TRANSFERENCIA lote_atual -> MIGRACAO — '
        f'{"DRY-RUN" if args.dry_run else "EXECUCAO REAL"} '
        f'({len(registros)} linhas)'
    )
    logger.info(f'XLSX: {args.xlsx}')
    logger.info(
        f'FILIAL_TO_COMPANY={FILIAL_TO_COMPANY} '
        f'LOTE_DESTINO={LOTE_DESTINO!r}'
    )

    app = create_app()
    resultados = []
    saldo_consumido: Dict[tuple, float] = {}
    t_global = time.time()
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        transfer_svc = StockInternalTransferService(odoo=odoo, lot_svc=lot_svc)

        for item in registros:
            r = processar_linha(
                odoo, lot_svc, transfer_svc, item,
                args.dry_run, saldo_consumido,
            )
            resultados.append(r)
            status = r['status']
            lt = r.get('lote_destino_acao', '?')
            if status in ('EXECUTADO', 'DRY_RUN_OK'):
                logger.info(
                    f'[{r["idx"]:4}/{len(registros)}] {status} '
                    f'{item["filial"]} cod={r["cod"]} '
                    f'{r["lote_origem_nome"]!r:>22} -> {LOTE_DESTINO!r} '
                    f'qtd={r.get("qtd_efetiva", r.get("qtd_solicitada"))} '
                    f'lote_dest={lt}'
                )
            elif status.startswith('SKIP'):
                logger.info(
                    f'[{r["idx"]:4}/{len(registros)}] {status} '
                    f'cod={r["cod"]} lote={r["lote_origem_nome"]!r}: '
                    f'{r.get("erro")}'
                )
            else:
                logger.warning(
                    f'[{r["idx"]:4}/{len(registros)}] {status} '
                    f'cod={r["cod"]} lote={r["lote_origem_nome"]!r}: '
                    f'{r.get("erro")}'
                )

    banner('RESUMO')
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

    # Estatistica por filial
    print('\n  Por filial:')
    for filial in sorted({r['filial'] for r in resultados}):
        sub = [r for r in resultados if r['filial'] == filial]
        ok = sum(1 for r in sub if r['status'] in ('EXECUTADO', 'DRY_RUN_OK'))
        soma = sum(
            r.get('qtd_efetiva', r.get('qtd_solicitada', 0))
            for r in sub if r['status'] in ('EXECUTADO', 'DRY_RUN_OK')
        )
        print(f'    {filial}: {ok}/{len(sub)} OK | soma {soma:,.6f} un')

    soma_total = sum(
        r.get('qtd_efetiva', r.get('qtd_solicitada', 0))
        for r in resultados
        if r['status'] in ('EXECUTADO', 'DRY_RUN_OK')
    )
    print(
        f'\n  Soma qtd transferida '
        f'{"executada" if not args.dry_run else "DRY-RUN OK"}: '
        f'{soma_total:,.6f} un'
    )
    print(f'  Tempo total: {time.time() - t_global:.1f}s')

    log_path = args.log_json
    if not log_path:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        modo = 'real' if not args.dry_run else 'dryrun'
        log_path = str(
            _THIS.parent / 'auditoria' /
            f'log_15_transf_para_migr_{modo}_{ts}.json'
        )
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            'args': vars(args),
            'filial_to_company': FILIAL_TO_COMPANY,
            'company_locations': COMPANY_LOCATIONS,
            'lote_destino': LOTE_DESTINO,
            'casas_decimais': CASAS_DECIMAIS,
            'xlsx': args.xlsx,
            'total': total,
            'contagem_status': dict(cont),
            'contagem_lote_destino_acao': dict(cont_lote),
            'soma_transferida': soma_total,
            'inicio_run': resultados[0]['inicio'] if resultados else None,
            'fim_run': datetime.now().isoformat(timespec='seconds'),
            'resultados': resultados,
        }, f, indent=2, default=str)
    print(f'\n  Log JSON: {log_path}')

    falhas = sum(1 for r in resultados if r['status'].startswith('FALHA'))
    return 0 if falhas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
