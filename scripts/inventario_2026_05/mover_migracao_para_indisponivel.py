# etapa: orquestrador
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""Mover quants do lote MIGRAÇÃO para os locais Indisponivel (D011).

OPERA 3 FILIAIS (SC excluida intencionalmente):

  CD: quants com lote MIGRACAO em CD/Estoque, CD/Estoque/DEVOLUÇÃO
      -> transferir para CD/Indisponivel (loc_id=31090, lote MIGRACAO mantido)

  FB: quants com lote MIGRACAO em FB/Estoque, FB/Pré-Produção/*, FB/Pós-Produção, etc.
      -> transferir para FB/Indisponivel (loc_id=31088, lote MIGRACAO mantido)

  LF: quants com lote MIGRAÇÃO/MIGRAÇAO/MIGRACAO em LF/Estoque, LF/Pré-Produção
      -> mesma location, lote vira P-15/05 (LOTES_PROXY_VAZIO de monitor/_comum.py)

Operacao: inventory adjustment em 2 passos via stock.quant.action_apply_inventory.
Mesma tecnica usada por StockInternalTransferService.transferir_entre_lotes,
mas trocando location_id em vez de lot_id (para FB/CD).

Quants com reserved_quantity > 0 sao PULADOS e listados em CSV separado.

Idempotente: re-executar e seguro (busca quants ATUAIS antes de cada
operacao, nao usa snapshot).

Uso:
    # dry-run (default) — apenas mostra o plano
    python scripts/inventario_2026_05/mover_migracao_para_indisponivel.py

    # executa de verdade
    python scripts/inventario_2026_05/mover_migracao_para_indisponivel.py --confirmar

    # filtrar uma filial so
    python scripts/inventario_2026_05/mover_migracao_para_indisponivel.py --so-filial=CD --confirmar
"""
import argparse
import csv
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))
sys.path.insert(0, str(_THIS.parent / 'monitor'))

from _comum import (  # type: ignore  # noqa: E402
    LOTES_MIGRACAO, m2o_id, m2o_name,
)

from app import create_app  # noqa: E402  # type: ignore
from app.odoo.constants.locations import get_local_indisponivel  # noqa: E402  # type: ignore
from app.odoo.services.stock_internal_transfer_service import (  # noqa: E402  # type: ignore
    StockInternalTransferService,
)
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('mover_migracao')

# LOCAIS_INDISPONIVEL (D011) derivado do modulo central; subset {1,4,5} — SC fora de escopo
LOCAIS_INDISPONIVEL = {c: get_local_indisponivel(c) for c in (1, 4, 5)}
COMPANY_NAME = {1: 'FB', 4: 'CD', 5: 'LF'}
LOTE_DESTINO_LF = 'P-15/05'

CSV_AUDITORIA_PADRAO = '/tmp/migracao_mover_resultado.csv'
CSV_PULADOS_PADRAO = '/tmp/migracao_mover_pulados.csv'


def banner(t, c='='):
    print()
    print(c * 90)
    print(f'  {t}')
    print(c * 90)


# ============================================================
# Coleta dos quants alvo (busca FRESCO do Odoo, nao usa snapshot)
# ============================================================
def coletar_quants_alvo(odoo, filiais: List[int]) -> List[Dict[str, Any]]:
    """Busca todos os quants com lote MIGRACAO* fora de Indisponivel.

    Retorna lista de dicts {id, product_id, product_name, default_code,
    company_id, location_id, location_name, lot_id, lot_name, qty, reservada}.
    """
    # 1. lots MIGRACAO* das filiais alvo
    lot_ids = odoo.search('stock.lot', [
        ('name', 'in', list(LOTES_MIGRACAO)),
        ('company_id', 'in', filiais),
    ])
    if not lot_ids:
        return []
    logger.info(f'lots MIGRACAO* encontrados: {len(lot_ids)} (filiais {filiais})')

    # 2. quants destes lots, fora de Indisponivel, internal
    excluir = [LOCAIS_INDISPONIVEL[c] for c in filiais if c in LOCAIS_INDISPONIVEL]
    quants = odoo.search_read('stock.quant', [
        ('lot_id', 'in', lot_ids),
        ('location_id', 'not in', excluir),
        ('location_id.usage', '=', 'internal'),
        ('company_id', 'in', filiais),
    ], ['id', 'company_id', 'product_id', 'lot_id',
        'location_id', 'quantity', 'reserved_quantity'])
    logger.info(f'quants encontrados: {len(quants)}')

    # 3. Resolver default_code dos produtos
    pids = list({m2o_id(q['product_id']) for q in quants if q.get('product_id')})
    pmap: Dict[int, str] = {}
    for i in range(0, len(pids), 200):
        b = pids[i:i + 200]
        d = odoo.read('product.product', list(b), ['default_code'])
        for p in d:
            pmap[p['id']] = p.get('default_code') or ''

    out: List[Dict[str, Any]] = []
    for q in quants:
        pid = m2o_id(q['product_id'])
        lid = m2o_id(q['lot_id'])
        loc = m2o_id(q['location_id'])
        cid = m2o_id(q['company_id'])
        out.append({
            'quant_id': q['id'],
            'company_id': cid,
            'filial': COMPANY_NAME.get(cid, f'cid={cid}'),
            'product_id': pid,
            'default_code': pmap.get(pid, ''),
            'product_name': m2o_name(q['product_id']),
            'lot_id': lid,
            'lot_name': m2o_name(q['lot_id']),
            'location_id': loc,
            'location_name': m2o_name(q['location_id']),
            'qty': float(q.get('quantity') or 0),
            'reservada': float(q.get('reserved_quantity') or 0),
        })
    return out


# ============================================================
# Transferencia FB/CD: muda location, mantem lote MIGRACAO
# ============================================================
def transferir_entre_locations(
    odoo,
    product_id: int,
    company_id: int,
    lot_id: int,
    qty: float,
    loc_origem: int,
    loc_destino: int,
) -> Dict[str, Any]:
    """Move qty do (loc_origem, lot_id) -> (loc_destino, lot_id) via inventory adjustment.

    Mesma estrategia do StockInternalTransferService.transferir_entre_lotes,
    mas trocando location_id no lugar de lot_id.
    """
    if qty <= 0:
        raise ValueError(f'qty deve ser > 0 (recebido {qty})')
    if loc_origem == loc_destino:
        raise ValueError(f'loc_origem==loc_destino ({loc_origem})')

    t0 = time.time()
    # 1. Quant origem
    qo = odoo.search_read('stock.quant', [
        ('product_id', '=', product_id),
        ('company_id', '=', company_id),
        ('location_id', '=', loc_origem),
        ('lot_id', '=', lot_id),
    ], ['id', 'quantity', 'reserved_quantity'], limit=1)
    if not qo:
        raise ValueError(
            f'quant origem nao encontrado: prod={product_id} cid={company_id} '
            f'loc={loc_origem} lot={lot_id}'
        )
    qo = qo[0]
    qty_origem_antes = float(qo['quantity'])
    reservada = float(qo.get('reserved_quantity') or 0)

    TOL = 0.001
    if qty > qty_origem_antes:
        if qty - qty_origem_antes <= TOL:
            qty = qty_origem_antes
        else:
            raise RuntimeError(f'qty {qty} > saldo {qty_origem_antes}')
    if (qty_origem_antes - qty) < reservada:
        raise RuntimeError(
            f'reserved {reservada} > saldo restante apos transferencia '
            f'({qty_origem_antes - qty})'
        )

    # 2. Quant destino
    qd = odoo.search_read('stock.quant', [
        ('product_id', '=', product_id),
        ('company_id', '=', company_id),
        ('location_id', '=', loc_destino),
        ('lot_id', '=', lot_id),
    ], ['id', 'quantity'], limit=1)
    qty_destino_antes = float(qd[0]['quantity']) if qd else 0.0

    # 3. Reduzir origem
    nova_qty_origem = qty_origem_antes - qty
    odoo.write('stock.quant', [qo['id']], {'inventory_quantity': nova_qty_origem})
    odoo.execute_kw('stock.quant', 'action_apply_inventory', [[qo['id']]])

    # 4. Aumentar/criar destino
    nova_qty_destino = qty_destino_antes + qty
    if qd:
        odoo.write('stock.quant', [qd[0]['id']], {'inventory_quantity': nova_qty_destino})
        odoo.execute_kw('stock.quant', 'action_apply_inventory', [[qd[0]['id']]])
        quant_destino_id = qd[0]['id']
    else:
        quant_destino_id = odoo.create('stock.quant', {
            'product_id': product_id,
            'company_id': company_id,
            'location_id': loc_destino,
            'lot_id': lot_id,
            'inventory_quantity': nova_qty_destino,
        })
        odoo.execute_kw('stock.quant', 'action_apply_inventory', [[quant_destino_id]])

    return {
        'quant_origem_id': qo['id'],
        'quant_destino_id': quant_destino_id,
        'qty_origem_antes': qty_origem_antes,
        'qty_origem_apos': nova_qty_origem,
        'qty_destino_antes': qty_destino_antes,
        'qty_destino_apos': nova_qty_destino,
        'qty_transferida': qty,
        'tempo_ms': int((time.time() - t0) * 1000),
    }


# ============================================================
# Processamento em lote
# ============================================================
def processar_filial_fb_cd(
    odoo,
    quants: List[Dict[str, Any]],
    filial: int,
    dry_run: bool,
    csv_audit: List[Dict[str, Any]],
    csv_pulados: List[Dict[str, Any]],
):
    """Processa CD ou FB — transfere para {emp}/Indisponivel."""
    loc_dest = LOCAIS_INDISPONIVEL[filial]
    sub = [q for q in quants if q['company_id'] == filial]
    if not sub:
        print(f'  {COMPANY_NAME[filial]}: nada a fazer.')
        return

    # Resumo por origem
    print(f'\n  --- {COMPANY_NAME[filial]} ({len(sub)} quants) → loc_dest={loc_dest} '
          f'({COMPANY_NAME[filial]}/Indisponivel) ---')
    por_loc: Dict[Tuple[int, str], List[Dict[str, Any]]] = {}
    for q in sub:
        k = (q['location_id'], q['location_name'])
        por_loc.setdefault(k, []).append(q)
    for (loc_id, loc_name), items in sorted(por_loc.items(), key=lambda x: -sum(i['qty'] for i in x[1])):
        qty_total = sum(i['qty'] for i in items)
        n_res = sum(1 for i in items if i['reservada'] > 0)
        print(f'    {loc_name:<40} loc_id={loc_id:>6}  '
              f'{len(items):>3} quants  {qty_total:>14,.2f} un  '
              f'reservados={n_res}')

    if dry_run:
        print('  [DRY-RUN] nao executa.')
        # mesmo em dry-run, marca os reservados em csv_pulados (para visibilidade)
        for q in sub:
            if q['reservada'] > 0:
                csv_pulados.append({**q, 'motivo': 'reserved_quantity>0', 'acao': 'TRANSFER_LOC'})
        return

    print(f'  Executando {len(sub)} transferencias FB/CD...')
    for idx, q in enumerate(sub, 1):
        if q['reservada'] > 0:
            csv_pulados.append({**q, 'motivo': 'reserved_quantity>0', 'acao': 'TRANSFER_LOC'})
            logger.warning(
                f'[{idx}/{len(sub)}] PULA quant={q["quant_id"]} '
                f'prod={q["default_code"]} reservada={q["reservada"]}'
            )
            continue
        if q['qty'] <= 0:
            continue
        try:
            res = transferir_entre_locations(
                odoo,
                product_id=q['product_id'],
                company_id=q['company_id'],
                lot_id=q['lot_id'],
                qty=q['qty'],
                loc_origem=q['location_id'],
                loc_destino=loc_dest,
            )
            csv_audit.append({
                'filial': q['filial'],
                'acao': 'TRANSFER_LOC',
                'product_id': q['product_id'],
                'default_code': q['default_code'],
                'product_name': q['product_name'],
                'lot_id': q['lot_id'],
                'lot_name': q['lot_name'],
                'loc_origem': q['location_id'],
                'loc_origem_name': q['location_name'],
                'loc_destino': loc_dest,
                'qty_transferida': res['qty_transferida'],
                'quant_origem_id': res['quant_origem_id'],
                'quant_destino_id': res['quant_destino_id'],
                'qty_origem_antes': res['qty_origem_antes'],
                'qty_origem_apos': res['qty_origem_apos'],
                'qty_destino_antes': res['qty_destino_antes'],
                'qty_destino_apos': res['qty_destino_apos'],
                'tempo_ms': res['tempo_ms'],
                'erro': '',
            })
            if idx % 20 == 0 or idx == len(sub):
                print(f'    [{idx}/{len(sub)}] OK  prod={q["default_code"]:<10} '
                      f'qty={q["qty"]:>10,.2f}  '
                      f'tempo={res["tempo_ms"]}ms')
        except Exception as e:
            logger.error(
                f'[{idx}/{len(sub)}] FALHA quant={q["quant_id"]} '
                f'prod={q["default_code"]}: {e}'
            )
            csv_pulados.append({**q, 'motivo': f'erro: {e}', 'acao': 'TRANSFER_LOC'})


def processar_filial_lf(
    odoo,
    quants: List[Dict[str, Any]],
    dry_run: bool,
    csv_audit: List[Dict[str, Any]],
    csv_pulados: List[Dict[str, Any]],
):
    """LF: transfere quants de lote MIGRACAO -> lote P-15/05 (mesma location)."""
    sub = [q for q in quants if q['company_id'] == 5]
    if not sub:
        print('  LF: nada a fazer.')
        return

    print(f'\n  --- LF ({len(sub)} quants) lote MIGRA* → lote {LOTE_DESTINO_LF!r} '
          '(mesma location) ---')
    por_loc: Dict[Tuple[int, str], List[Dict[str, Any]]] = {}
    for q in sub:
        k = (q['location_id'], q['location_name'])
        por_loc.setdefault(k, []).append(q)
    for (loc_id, loc_name), items in sorted(por_loc.items(), key=lambda x: -sum(i['qty'] for i in x[1])):
        qty_total = sum(i['qty'] for i in items)
        n_res = sum(1 for i in items if i['reservada'] > 0)
        print(f'    {loc_name:<40} loc_id={loc_id:>6}  '
              f'{len(items):>3} quants  {qty_total:>14,.2f} un  '
              f'reservados={n_res}')

    if dry_run:
        print('  [DRY-RUN] nao executa.')
        for q in sub:
            if q['reservada'] > 0:
                csv_pulados.append({**q, 'motivo': 'reserved_quantity>0', 'acao': 'TRANSFER_LOT'})
        return

    svc = StockInternalTransferService(odoo=odoo)
    print(f'  Executando {len(sub)} transferencias LF (lote MIGRA* -> {LOTE_DESTINO_LF})...')
    for idx, q in enumerate(sub, 1):
        if q['reservada'] > 0:
            csv_pulados.append({**q, 'motivo': 'reserved_quantity>0', 'acao': 'TRANSFER_LOT'})
            logger.warning(
                f'[{idx}/{len(sub)}] PULA quant={q["quant_id"]} '
                f'prod={q["default_code"]} reservada={q["reservada"]}'
            )
            continue
        if q['qty'] <= 0:
            continue
        try:
            res = svc.transferir_quantidade_para_lote(
                product_id=q['product_id'],
                company_id=q['company_id'],
                location_id=q['location_id'],
                qty=q['qty'],
                lot_id_origem=q['lot_id'],
                nome_lote_destino=LOTE_DESTINO_LF,
            )
            csv_audit.append({
                'filial': q['filial'],
                'acao': 'TRANSFER_LOT',
                'product_id': q['product_id'],
                'default_code': q['default_code'],
                'product_name': q['product_name'],
                'lot_id': q['lot_id'],
                'lot_name': q['lot_name'],
                'loc_origem': q['location_id'],
                'loc_origem_name': q['location_name'],
                'loc_destino': q['location_id'],
                'qty_transferida': res['qty_transferida'],
                'quant_origem_id': res['quant_origem_id'],
                'quant_destino_id': res['quant_destino_id'],
                'qty_origem_antes': res['quant_origem_qty_antes'],
                'qty_origem_apos': res['quant_origem_qty_apos'],
                'qty_destino_antes': res['quant_destino_qty_antes'],
                'qty_destino_apos': res['quant_destino_qty_apos'],
                'tempo_ms': res['tempo_ms'],
                'erro': '',
            })
            if idx % 20 == 0 or idx == len(sub):
                print(f'    [{idx}/{len(sub)}] OK  prod={q["default_code"]:<10} '
                      f'qty={q["qty"]:>10,.2f}  '
                      f'lot_destino={res.get("lot_id_destino")}  '
                      f'tempo={res["tempo_ms"]}ms')
        except Exception as e:
            logger.error(
                f'[{idx}/{len(sub)}] FALHA quant={q["quant_id"]} '
                f'prod={q["default_code"]}: {e}'
            )
            csv_pulados.append({**q, 'motivo': f'erro: {e}', 'acao': 'TRANSFER_LOT'})


# ============================================================
# Main
# ============================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--confirmar', action='store_true',
                    help='Executa de verdade. Sem flag, roda dry-run.')
    ap.add_argument('--so-filial', choices=['FB', 'CD', 'LF'], default=None,
                    help='Limita a 1 filial (default: FB+CD+LF).')
    ap.add_argument('--csv-audit', default=CSV_AUDITORIA_PADRAO,
                    help='Caminho do CSV de auditoria (somente em --confirmar)')
    ap.add_argument('--csv-pulados', default=CSV_PULADOS_PADRAO,
                    help='Caminho do CSV de pulados')
    args = ap.parse_args()
    dry_run = not args.confirmar

    filiais_alvo = {1, 4, 5}
    if args.so_filial:
        nome_para_cid = {'FB': 1, 'CD': 4, 'LF': 5}
        filiais_alvo = {nome_para_cid[args.so_filial]}

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        banner(f'MOVER LOTE MIGRACAO → INDISPONIVEL  '
               f'(modo={"DRY-RUN" if dry_run else "EXECUCAO REAL"})')
        print(f'  Filiais alvo: {sorted(filiais_alvo)} '
              f'({[COMPANY_NAME[c] for c in sorted(filiais_alvo)]})')

        banner('1. Coletando quants alvo (busca FRESCO no Odoo)', '-')
        quants = coletar_quants_alvo(odoo, sorted(filiais_alvo))
        # filtra qtd 0 (D011 nao precisa mexer em vestigios)
        quants = [q for q in quants if abs(q['qty']) > 1e-6]
        if not quants:
            print('Nenhum quant com saldo nao-zero encontrado. Nada a fazer.')
            return

        # Resumo geral
        banner('2. Resumo geral', '-')
        by_filial: Dict[int, Dict[str, float]] = {}
        for q in quants:
            d = by_filial.setdefault(q['company_id'], {
                'n': 0, 'qty': 0.0, 'reservada': 0.0, 'n_reservados': 0,
            })
            d['n'] += 1
            d['qty'] += q['qty']
            d['reservada'] += q['reservada']
            if q['reservada'] > 0:
                d['n_reservados'] += 1
        for cid in sorted(by_filial.keys()):
            d = by_filial[cid]
            print(f'  {COMPANY_NAME[cid]:>3}: {d["n"]:>4} quants  '
                  f'qty_total={d["qty"]:>14,.2f}  '
                  f'reservados={d["n_reservados"]:>3}  '
                  f'reservada_total={d["reservada"]:>12,.2f}')

        banner('3. Plano detalhado por filial', '-')
        csv_audit: List[Dict[str, Any]] = []
        csv_pulados: List[Dict[str, Any]] = []
        if 4 in filiais_alvo:
            processar_filial_fb_cd(odoo, quants, 4, dry_run, csv_audit, csv_pulados)
        if 1 in filiais_alvo:
            processar_filial_fb_cd(odoo, quants, 1, dry_run, csv_audit, csv_pulados)
        if 5 in filiais_alvo:
            processar_filial_lf(odoo, quants, dry_run, csv_audit, csv_pulados)

        # CSVs
        if csv_audit and not dry_run:
            cols = ['filial', 'acao', 'product_id', 'default_code', 'product_name',
                    'lot_id', 'lot_name', 'loc_origem', 'loc_origem_name',
                    'loc_destino', 'qty_transferida', 'quant_origem_id',
                    'quant_destino_id', 'qty_origem_antes', 'qty_origem_apos',
                    'qty_destino_antes', 'qty_destino_apos', 'tempo_ms', 'erro']
            with open(args.csv_audit, 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                w.writerows(csv_audit)
            print(f'\n  CSV auditoria: {args.csv_audit} ({len(csv_audit)} linhas)')

        if csv_pulados:
            cols = ['filial', 'acao', 'motivo', 'quant_id', 'company_id',
                    'product_id', 'default_code', 'product_name', 'lot_id',
                    'lot_name', 'location_id', 'location_name', 'qty', 'reservada']
            with open(args.csv_pulados, 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                w.writerows(csv_pulados)
            print(f'  CSV pulados: {args.csv_pulados} ({len(csv_pulados)} linhas)')

        if dry_run:
            print('\n  [DRY-RUN] nada foi alterado no Odoo. Use --confirmar para executar.')


if __name__ == '__main__':
    main()
