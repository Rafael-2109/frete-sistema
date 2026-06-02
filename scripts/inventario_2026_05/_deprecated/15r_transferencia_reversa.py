"""15r - Transferencia REVERSA: DE MIGRACAO PARA lote_planilha (2026-05-19).

Operacao INVERSA do script 15:
- Script 15: diff_qtd<0 → lote_planilha PERDE, MIGRACAO GANHA
- Script 15r: diff_qtd>0 → MIGRACAO PERDE, lote_planilha GANHA

Semantica do diff_qtd (origem: monitor/4_gerar_diffs.py:77):
    diff_qtd = qtd_teorica - qtd_odoo_atual
    diff_qtd>0: Odoo tem MENOS que o teorico → lote precisa GANHAR

Tratamento de lotes:
- LOTE ORIGEM normal (ex: '136/26'): cria/reusa lote e adiciona qty
- LOTE ORIGEM == 'P-15/05' (proxy vazio): destino = quant sem lote
  (lot_id=False) em FB/Estoque (ou cria se nao existe)

Casos:
1. lote real + sub-location: cria/reusa em FB/Estoque
2. P-15/05 (sem lote): quant sem lote em location de destino

Flags identicos ao script 15 (--xlsx, --shard X/Y, --confirmar, etc.)
"""
import argparse
import hashlib
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
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
logger = logging.getLogger('15r_transf_reversa')

FILIAL_TO_COMPANY = {'FB': 1, 'CD': 4, 'LF': 5}
LOTE_MIGRACAO = 'MIGRAÇÃO'
LOTES_PROXY_VAZIO = {'P-15/05'}
CASAS_DECIMAIS = 6
DEFAULT_XLSX = '/mnt/c/Users/rafael.nascimento/Downloads/TRANS PARA MIGRAÇÃO.xlsx'


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def _norm_lote(raw) -> Optional[str]:
    if pd.isna(raw):
        return None
    s = str(raw).strip()
    if not s or s.lower() == 'nan':
        return None
    return s


def carregar_planilha(path: str) -> List[Dict]:
    """Le XLSX, schema B (LOTE ORIGEM + LOTE DESTINO + diff_qtd)."""
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    if not {'LOTE ORIGEM', 'LOTE DESTINO'}.issubset(df.columns):
        raise ValueError('Planilha sem colunas LOTE ORIGEM/LOTE DESTINO')

    registros = []
    for idx, row in df.iterrows():
        diff_qtd = float(row['diff_qtd'])
        registros.append({
            'idx': int(idx) + 1,
            'filial': str(row['filial']).strip(),
            'cod': str(row['cod']).strip(),
            'lote_destino_op_nome': _norm_lote(row['LOTE ORIGEM']),
            'lote_origem_op_nome': _norm_lote(row['LOTE DESTINO']) or LOTE_MIGRACAO,
            'diff_qtd': diff_qtd,
        })
    return registros


def resolver_product_id(odoo, cod: str) -> Optional[int]:
    res = odoo.search_read(
        'product.product', [['default_code', '=', cod]],
        ['id', 'active'], limit=5,
    )
    if not res:
        return None
    ativos = [r for r in res if r.get('active')]
    if not ativos:
        return None
    return ativos[0]['id']


def buscar_quant_com_saldo(
    odoo, product_id: int, lot_id, company_id: int,
    location_id_preferido: int,
) -> Optional[Dict]:
    """Busca quant com saldo livre > 0 para (product, lot).
    `lot_id` pode ser int, None ou False.
    Prefere `location_id_preferido`; senao busca em qualquer location interna.
    """
    base_domain = [
        ['product_id', '=', product_id],
        ['company_id', '=', company_id],
    ]
    if lot_id is None or lot_id is False:
        base_domain.append(['lot_id', '=', False])
    else:
        base_domain.append(['lot_id', '=', lot_id])

    # Tenta location preferida primeiro
    domain = base_domain + [['location_id', '=', location_id_preferido]]
    quants = odoo.search_read(
        'stock.quant', domain,
        ['id', 'quantity', 'reserved_quantity', 'location_id'],
        limit=1,
    )
    if quants and (float(quants[0]['quantity']) - float(quants[0].get('reserved_quantity') or 0)) > 0:
        q = quants[0]
        return {
            'quant_id': q['id'],
            'location_id': q['location_id'][0],
            'quantity': float(q['quantity']),
            'reserved_quantity': float(q.get('reserved_quantity') or 0),
            'livre': float(q['quantity']) - float(q.get('reserved_quantity') or 0),
        }

    # Fallback: qualquer location interna
    quants = odoo.search_read(
        'stock.quant', base_domain + [['quantity', '>', 0]],
        ['id', 'quantity', 'reserved_quantity', 'location_id'],
        limit=20,
    )
    if not quants:
        return None
    loc_ids = list({q['location_id'][0] for q in quants if q['location_id']})
    locs = odoo.search_read(
        'stock.location',
        [['id', 'in', loc_ids], ['usage', '=', 'internal']],
        ['id'],
    )
    locs_internal = {loc['id'] for loc in locs}
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
                'quantity': qty,
                'reserved_quantity': res,
                'livre': livre,
            })
    if not candidatos:
        return None
    candidatos.sort(key=lambda x: -x['livre'])
    return candidatos[0]


def transferencia_reversa(
    odoo, lot_svc, item, dry_run: bool,
    saldo_consumido: Dict,
    criar_lote_migracao: bool = False,
) -> Dict:
    """Transfere DE MIGRACAO PARA lote_planilha.

    Status:
      'DRY_RUN_OK', 'EXECUTADO',
      'SKIP_QTD_NAO_POSITIVA', 'SKIP_FILIAL',
      'FALHA_PRODUCT', 'FALHA_MIGRACAO_SEM_SALDO', 'FALHA_ODOO'
    """
    r = {**item, 'inicio': datetime.now().isoformat(timespec='seconds')}

    company_id = FILIAL_TO_COMPANY.get(item['filial'])
    if not company_id:
        r['status'] = 'SKIP_FILIAL'
        r['erro'] = f'filial {item["filial"]!r} desconhecida'
        return r
    location_id = COMPANY_LOCATIONS[company_id]
    r['company_id'] = company_id

    # Filtro: SO opera em diff_qtd > 0
    if item['diff_qtd'] <= 0:
        r['status'] = 'SKIP_QTD_NAO_POSITIVA'
        r['erro'] = f'diff_qtd={item["diff_qtd"]} <=0 (este script so faz reversa)'
        return r

    qty = round(item['diff_qtd'], CASAS_DECIMAIS)
    r['qty_solicitada'] = qty

    pid = resolver_product_id(odoo, item['cod'])
    if not pid:
        r['status'] = 'FALHA_PRODUCT'
        r['erro'] = f'cod {item["cod"]!r} nao encontrado'
        return r
    r['product_id'] = pid

    # Lote da planilha (destino da operacao = "alvo")
    lote_destino_nome = item['lote_destino_op_nome']  # LOTE ORIGEM da planilha
    # Tratamento "sem lote": LOTE ORIGEM=NaN ou P-15/05 mapeia para lot_id=False
    is_proxy_vazio = (
        lote_destino_nome is None or
        lote_destino_nome in LOTES_PROXY_VAZIO
    )

    # Resolver lote MIGRACAO (origem da operacao)
    lot_id_migracao = lot_svc.buscar_por_nome(
        item['lote_origem_op_nome'], pid, company_id,
    )
    if not lot_id_migracao:
        if criar_lote_migracao:
            # Criar lote MIGRACAO com vencimento amanha
            amanha = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            if dry_run:
                r['lote_migracao_acao'] = f'create_pending_exp={amanha}'
                r['status'] = 'DRY_RUN_OK_SEM_LOTE'
                r['erro'] = (
                    f'lote {item["lote_origem_op_nome"]!r} sera criado '
                    f'com expiration={amanha} (dry-run)'
                )
                return r
            try:
                lot_id_migracao, criado = lot_svc.criar_se_nao_existe(
                    item['lote_origem_op_nome'], pid, company_id,
                    expiration_date=amanha,
                )
                r['lote_migracao_acao'] = (
                    f'created_exp={amanha}' if criado else 'reused'
                )
            except Exception as exc:
                r['status'] = 'FALHA_CRIAR_LOTE_MIGRACAO'
                r['erro'] = str(exc)
                return r
        else:
            r['status'] = 'FALHA_LOTE_MIGRACAO'
            r['erro'] = f'lote {item["lote_origem_op_nome"]!r} nao existe'
            return r
    r['lot_id_migracao'] = lot_id_migracao

    # Buscar quant MIGRACAO com saldo livre
    quant_mig = buscar_quant_com_saldo(
        odoo, pid, lot_id_migracao, company_id, location_id,
    )
    if not quant_mig:
        # Se criamos o lote agora, ainda nao tem quant — criar virtual
        # com qty=0 e deixar transferencia gerar saldo negativo
        if criar_lote_migracao:
            r['quant_origem_criada_zero'] = True
            quant_mig = {
                'quant_id': None,  # sera criado abaixo
                'location_id': location_id,
                'quantity': 0.0,
                'reserved_quantity': 0.0,
                'livre': 0.0,
            }
        else:
            r['status'] = 'FALHA_MIGRACAO_SEM_SALDO'
            r['erro'] = f'lote MIGRACAO sem saldo livre para cod {item["cod"]}'
            return r
    r['quant_origem'] = quant_mig

    # Validar saldo cumulativo
    key = (pid, lot_id_migracao, quant_mig['location_id'])
    ja_consumido = saldo_consumido.get(key, 0.0)
    disponivel = round(quant_mig['livre'] - ja_consumido, CASAS_DECIMAIS)
    r['ja_consumido_run'] = round(ja_consumido, CASAS_DECIMAIS)
    r['saldo_livre_disponivel'] = disponivel

    TOL = 0.001
    permitir_negativo = criar_lote_migracao and r.get('quant_origem_criada_zero')
    if qty > disponivel and not permitir_negativo:
        if qty - disponivel <= TOL and disponivel > 0:
            r['clamp_arredondamento'] = {'de': qty, 'para': disponivel}
            qty = disponivel
        elif disponivel > 0:
            r['clamp_parcial'] = {
                'pedido': qty, 'disponivel': disponivel,
                'delta_nao_transferido': round(qty - disponivel, CASAS_DECIMAIS),
            }
            qty = disponivel
        else:
            r['status'] = 'FALHA_MIGRACAO_SEM_SALDO'
            r['erro'] = (
                f'qty={qty} > disponivel={disponivel} (saldo total '
                f'{quant_mig["quantity"]} reservado {quant_mig["reserved_quantity"]} '
                f'consumido_run {ja_consumido})'
            )
            return r

    r['qty_efetiva'] = qty

    # Resolver lote destino — se P-15/05, eh lot_id=False (sem lote)
    if is_proxy_vazio:
        lot_id_destino = False
        r['destino_tipo'] = 'sem_lote (P-15/05 proxy)'
    else:
        if dry_run:
            lot_id_destino = lot_svc.buscar_por_nome(
                lote_destino_nome, pid, company_id,
            )
            r['destino_tipo'] = 'lote_existente' if lot_id_destino else 'lote_a_criar'
        else:
            lot_id_destino, criado = lot_svc.criar_se_nao_existe(
                lote_destino_nome, pid, company_id,
            )
            r['destino_tipo'] = 'lote_criado' if criado else 'lote_reusado'
        r['lot_id_destino'] = lot_id_destino

    if dry_run:
        saldo_consumido[key] = ja_consumido + qty
        r['status'] = 'DRY_RUN_OK'
        return r

    # EXECUTAR: inventory adjustment em 2 passos
    t0 = time.time()
    try:
        location_op = quant_mig['location_id']
        nova_qty_origem = quant_mig['quantity'] - qty

        # Passo 1: reduzir MIGRACAO (ou criar quant se nao existe)
        if quant_mig['quant_id'] is None:
            # quant MIGRACAO nao existia — criar com saldo negativo
            quant_origem_id = odoo.create('stock.quant', {
                'product_id': pid,
                'company_id': company_id,
                'location_id': location_op,
                'lot_id': lot_id_migracao,
                'inventory_quantity': nova_qty_origem,
            })
            odoo.execute_kw(
                'stock.quant', 'action_apply_inventory', [[quant_origem_id]],
            )
            quant_mig['quant_id'] = quant_origem_id
        else:
            odoo.write(
                'stock.quant', [quant_mig['quant_id']],
                {'inventory_quantity': nova_qty_origem},
            )
            odoo.execute_kw(
                'stock.quant', 'action_apply_inventory',
                [[quant_mig['quant_id']]],
            )

        # Passo 2: aumentar destino
        # Buscar quant destino na mesma location
        domain_d = [
            ['product_id', '=', pid],
            ['company_id', '=', company_id],
            ['location_id', '=', location_op],
        ]
        if lot_id_destino is False:
            domain_d.append(['lot_id', '=', False])
        else:
            domain_d.append(['lot_id', '=', lot_id_destino])
        quants_d = odoo.search_read(
            'stock.quant', domain_d,
            ['id', 'quantity'], limit=1,
        )
        if quants_d:
            qty_d_antes = float(quants_d[0]['quantity'])
            nova_qty_dest = qty_d_antes + qty
            odoo.write(
                'stock.quant', [quants_d[0]['id']],
                {'inventory_quantity': nova_qty_dest},
            )
            odoo.execute_kw(
                'stock.quant', 'action_apply_inventory',
                [[quants_d[0]['id']]],
            )
            quant_dest_id = quants_d[0]['id']
        else:
            payload = {
                'product_id': pid,
                'company_id': company_id,
                'location_id': location_op,
                'inventory_quantity': qty,
            }
            if lot_id_destino:
                payload['lot_id'] = lot_id_destino
            quant_dest_id = odoo.create('stock.quant', payload)
            odoo.execute_kw(
                'stock.quant', 'action_apply_inventory',
                [[quant_dest_id]],
            )
            qty_d_antes = 0.0
            nova_qty_dest = qty

        r['status'] = 'EXECUTADO'
        r['quant_destino_id'] = quant_dest_id
        r['qty_destino_antes'] = qty_d_antes
        r['qty_destino_apos'] = nova_qty_dest
        r['qty_origem_antes'] = quant_mig['quantity']
        r['qty_origem_apos'] = nova_qty_origem
        r['location_op'] = location_op
        r['tempo_ms'] = int((time.time() - t0) * 1000)
        saldo_consumido[key] = ja_consumido + qty
    except Exception as exc:
        r['status'] = 'FALHA_ODOO'
        r['erro'] = str(exc)
        r['tempo_ms'] = int((time.time() - t0) * 1000)
        logger.exception(f'idx={item["idx"]} falha: {exc}')

    return r


def processar(odoo, lot_svc, item, dry_run, saldo_consumido,
              criar_lote_migracao=False, max_retries=5):
    """Wrapper retry."""
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            return transferencia_reversa(
                odoo, lot_svc, item, dry_run, saldo_consumido,
                criar_lote_migracao=criar_lote_migracao,
            )
        except Exception as exc:
            last_exc = exc
            msg = str(exc)
            transitorio = (
                '503' in msg or 'Service Unavailable' in msg or
                'timeout' in msg.lower() or 'timed out' in msg.lower() or
                'connection refused' in msg.lower() or
                'connection reset' in msg.lower() or
                'ProtocolError' in str(type(exc))
            )
            if not transitorio:
                return {
                    **item, 'status': 'FALHA_ODOO',
                    'erro': f'(no retry) {exc}',
                    'inicio': datetime.now().isoformat(timespec='seconds'),
                }
            backoff = min(2 ** attempt, 60)
            logger.warning(
                f'idx={item["idx"]} transitorio {attempt}/{max_retries}: '
                f'{exc} — aguardando {backoff}s'
            )
            time.sleep(backoff)
    return {
        **item, 'status': 'FALHA_ODOO',
        'erro': f'(esgotou retries) {last_exc}',
        'inicio': datetime.now().isoformat(timespec='seconds'),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--confirmar', action='store_true', default=False)
    parser.add_argument('--xlsx', type=str, default=DEFAULT_XLSX)
    parser.add_argument('--limite', type=int, default=0)
    parser.add_argument('--retomar-de', type=int, default=0)
    parser.add_argument('--shard', type=str, default='')
    parser.add_argument(
        '--apenas-linhas', type=str, default='',
        help='CSV de idx 1-based: 24,28,35',
    )
    parser.add_argument(
        '--criar-lote-migracao', action='store_true', default=False,
        help='Cria lote MIGRACAO com expiration=amanha se nao existir',
    )
    parser.add_argument('--log-json', type=str, default='')
    args = parser.parse_args()

    if args.confirmar:
        args.dry_run = False

    if not Path(args.xlsx).exists():
        logger.error(f'XLSX nao encontrado: {args.xlsx}')
        return 2

    registros = carregar_planilha(args.xlsx)
    # FILTRO: apenas diff_qtd>0
    registros = [r for r in registros if r['diff_qtd'] > 0]
    logger.info(f'Registros com diff_qtd>0: {len(registros)}')

    apenas_idx = set()
    if args.apenas_linhas:
        apenas_idx = {
            int(s.strip()) for s in args.apenas_linhas.split(',') if s.strip()
        }
        registros = [r for r in registros if r['idx'] in apenas_idx]
        logger.info(f'--apenas-linhas: {len(registros)} registros')
    if args.retomar_de > 0:
        registros = [r for r in registros if r['idx'] >= args.retomar_de]
    if args.shard:
        x_str, y_str = args.shard.split('/')
        sx, sy = int(x_str), int(y_str)
        def shard_de(cod):
            return int(hashlib.md5(cod.encode()).hexdigest(), 16) % sy
        registros = [r for r in registros if shard_de(r['cod']) == sx - 1]
        logger.info(f'--shard={args.shard}: {len(registros)} nesta shard')
    if args.limite > 0:
        registros = registros[: args.limite]

    banner(
        f'TRANSF REVERSA MIGRACAO -> lote_planilha — '
        f'{"DRY-RUN" if args.dry_run else "EXEC REAL"} ({len(registros)} linhas)'
    )

    app = create_app()
    resultados = []
    saldo_consumido: Dict = {}
    t_global = time.time()
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        for item in registros:
            r = processar(
                odoo, lot_svc, item, args.dry_run, saldo_consumido,
                criar_lote_migracao=args.criar_lote_migracao,
            )
            resultados.append(r)
            s = r['status']
            if s in ('EXECUTADO', 'DRY_RUN_OK'):
                logger.info(
                    f'[{r["idx"]:5}/{len(registros)}] {s} {item["filial"]} '
                    f'cod={r["cod"]} MIGRACAO -> '
                    f'{r["lote_destino_op_nome"]!r:>22} qty={r.get("qty_efetiva")}'
                )
            else:
                logger.warning(
                    f'[{r["idx"]:5}/{len(registros)}] {s} cod={r["cod"]}: '
                    f'{r.get("erro")}'
                )

    banner('RESUMO')
    cont = Counter(r['status'] for r in resultados)
    for status, n in cont.most_common():
        pct = n * 100 / len(resultados) if resultados else 0
        print(f'  {status:30s} {n:5d}  ({pct:5.1f}%)')
    print(f'  {"TOTAL":30s} {len(resultados):5d}')

    soma = sum(
        r.get('qty_efetiva', 0) for r in resultados
        if r['status'] in ('EXECUTADO', 'DRY_RUN_OK')
    )
    print(f'\n  Soma qtd transferida: {soma:,.6f} un')
    print(f'  Tempo total: {time.time() - t_global:.1f}s')

    log_path = args.log_json
    if not log_path:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        modo = 'real' if not args.dry_run else 'dryrun'
        log_path = str(
            _THIS.parent / 'auditoria' /
            f'log_15r_reversa_{modo}_{ts}.json'
        )
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            'args': vars(args),
            'total': len(resultados),
            'contagem_status': dict(cont),
            'soma_transferida': soma,
            'resultados': resultados,
        }, f, indent=2, default=str)
    print(f'\n  Log JSON: {log_path}')

    falhas = sum(1 for r in resultados if r['status'].startswith('FALHA'))
    return 0 if falhas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
