# etapa: orquestrador
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""Zera todos os quants negativos da FB via inventory adjustment.

Estrategia (instrucao do usuario 2026-05-19 noite):
  1. Para cada quant negativo (qty<0): consumir saldo de OUTROS LOTES do
     mesmo produto na FB (lote != lote do negativo, lote != MIGRACAO),
     preferindo MESMA LOCATION antes de outras.
  2. Se ainda houver demanda residual, consumir do lote MIGRACAO do
     mesmo produto (pode ficar com saldo negativo — D005 permite isso
     como consolidador de fantasmas).
  3. Zerar o quant negativo (inventory_quantity=0).

Tecnica: 3 inventory adjustments compensatorios por quant negativo:
  - Reduz cada fonte usada (inventory_quantity = saldo - take)
  - Reduz/cria MIGRACAO (se necessario)
  - Aumenta quant negativo de -X para 0 (Δ=+X)

Os Δ se compensam: total consumido = qty_neg. Saldo total da FB
permanece (somente redistribuicao entre lotes/locations).

Excecoes:
  - Quant negativo CUJO lote ja e MIGRACAO: nao tem como compensar
    consigo mesmo — reporta e pula (exceto se houver outros lotes
    suficientes para cobrir totalmente).
  - Quant negativo cujo produto nao tem lote MIGRACAO ainda: cria via
    StockLotService.criar_se_nao_existe.

Uso:
    python scripts/inventario_2026_05/zerar_negativos_fb.py
    python scripts/inventario_2026_05/zerar_negativos_fb.py --confirmar
"""
import argparse
import csv
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app  # noqa: E402  # type: ignore
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402  # type: ignore
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('zerar_negativos')

COMPANY_FB = 1
LOTES_MIGRACAO_NOMES = ['MIGRACAO', 'MIGRAÇÃO', 'MIGRAÇAO', 'MIGRACÃO']
NOME_LOTE_MIGRACAO_PREFERIDO = 'MIGRAÇÃO'  # padronizacao D005 (com cedilha+til)

CSV_PLANO = '/tmp/zerar_negativos_fb_plano.csv'
CSV_AUDIT = '/tmp/zerar_negativos_fb_audit.csv'


def banner(t, c='='):
    print()
    print(c * 90)
    print(f'  {t}')
    print(c * 90)


def coletar_dados(odoo):
    """Carrega negativos + positivos + lotes MIGRACAO."""
    # 1. Quants negativos FB
    nids = odoo.search('stock.quant', [
        ('company_id', '=', COMPANY_FB),
        ('location_id.usage', '=', 'internal'),
        ('quantity', '<', 0),
    ])
    negativos = odoo.read('stock.quant', nids, [
        'id', 'product_id', 'lot_id', 'location_id',
        'quantity', 'reserved_quantity',
    ])
    negativos = [d for d in negativos if abs(d['quantity']) > 0.001]
    print(f'Quants negativos FB: {len(negativos)}')

    pids = list({d['product_id'][0] for d in negativos})

    # 2. Quants positivos dos mesmos produtos
    positivos = odoo.search_read('stock.quant', [
        ('company_id', '=', COMPANY_FB),
        ('location_id.usage', '=', 'internal'),
        ('product_id', 'in', pids),
        ('quantity', '>', 0),
    ], ['id', 'product_id', 'lot_id', 'location_id',
        'quantity', 'reserved_quantity'])
    print(f'Quants positivos FB: {len(positivos)}')

    # 3. Lots MIGRACAO da FB indexados por product_id
    lot_mig_ids = odoo.search('stock.lot', [
        ('company_id', '=', COMPANY_FB),
        ('name', 'in', LOTES_MIGRACAO_NOMES),
    ])
    if lot_mig_ids:
        lots_mig = odoo.read('stock.lot', lot_mig_ids, ['id', 'name', 'product_id'])
        lot_migracao_set = set(lot_mig_ids)
        lot_migracao_por_produto = {}
        for l in lots_mig:
            pid = l['product_id'][0] if l.get('product_id') else None
            if pid and pid not in lot_migracao_por_produto:
                lot_migracao_por_produto[pid] = l['id']
        print(f'Lots MIGRACAO FB: {len(lot_mig_ids)} (cobrem {len(lot_migracao_por_produto)} produtos)')
    else:
        lot_migracao_set = set()
        lot_migracao_por_produto = {}

    # 4. default_code dos produtos
    pmap = {}
    for i in range(0, len(pids), 200):
        b = pids[i:i + 200]
        d = odoo.read('product.product', list(b), ['default_code'])
        for p in d:
            pmap[p['id']] = p.get('default_code') or ''

    return negativos, positivos, lot_migracao_set, lot_migracao_por_produto, pmap


def montar_plano(negativos, positivos, lot_migracao_set):
    """Aloca fontes para cada negativo. Atualiza `pos_consumed` em memoria."""
    pos_por_prod: Dict[int, List[Dict[str, Any]]] = {}
    for q in positivos:
        pos_por_prod.setdefault(q['product_id'][0], []).append(q)

    pos_consumed: Dict[int, float] = {q['id']: 0.0 for q in positivos}
    plano: List[Dict[str, Any]] = []

    for n in sorted(negativos, key=lambda x: -abs(x['quantity'])):
        pid = n['product_id'][0]
        lid_neg = n['lot_id'][0] if n.get('lot_id') else None
        loc_neg = n['location_id'][0]
        demanda = abs(n['quantity'])
        is_negativo_em_migracao = (lid_neg is not None and lid_neg in lot_migracao_set)

        # Fontes validas: lote != lid_neg, lote not in MIGRACAO
        fontes_validas = []
        for q in pos_por_prod.get(pid, []):
            qlid = q['lot_id'][0] if q.get('lot_id') else None
            if qlid == lid_neg:
                continue
            if qlid is not None and qlid in lot_migracao_set:
                continue
            disp = q['quantity'] - (q.get('reserved_quantity') or 0) - pos_consumed[q['id']]
            if disp <= 0:
                continue
            fontes_validas.append((q, disp))

        # Ordena: mesma location primeiro, maior disponibilidade primeiro
        fontes_validas.sort(key=lambda x: (
            0 if x[0]['location_id'][0] == loc_neg else 1, -x[1]
        ))

        fontes_usadas = []
        consumido = 0.0
        for q, disp in fontes_validas:
            if demanda <= 0:
                break
            take = min(disp, demanda)
            pos_consumed[q['id']] += take
            fontes_usadas.append({
                'quant_id': q['id'],
                'lot_id': q['lot_id'][0] if q.get('lot_id') else None,
                'lot_name': q['lot_id'][1] if q.get('lot_id') else '(sem lote)',
                'location_id': q['location_id'][0],
                'location_name': q['location_id'][1],
                'qty_antes': q['quantity'],
                'reserved': q.get('reserved_quantity') or 0,
                'take': take,
            })
            consumido += take
            demanda -= take

        residual = demanda
        usa_migracao = residual > 0 and not is_negativo_em_migracao
        plano.append({
            'quant_neg': n,
            'pid': pid,
            'lid_neg': lid_neg,
            'loc_neg': loc_neg,
            'qty_neg_orig': abs(n['quantity']),
            'fontes_usadas': fontes_usadas,
            'consumido_outros': consumido,
            'residual_migracao': residual if usa_migracao else 0.0,
            'is_negativo_em_migracao': is_negativo_em_migracao,
            'residual_sem_acao': residual if not usa_migracao else 0.0,
        })
    return plano


def imprimir_resumo_plano(plano, pmap):
    n_full = sum(1 for p in plano if p['residual_migracao'] == 0 and p['residual_sem_acao'] == 0)
    n_with_mig = sum(1 for p in plano if p['residual_migracao'] > 0)
    n_sem_acao = sum(1 for p in plano if p['residual_sem_acao'] > 0)
    sum_outros = sum(p['consumido_outros'] for p in plano)
    sum_migracao = sum(p['residual_migracao'] for p in plano)
    sum_sem_acao = sum(p['residual_sem_acao'] for p in plano)

    print(f'\n=== Resumo do plano ===')
    print(f'  Total negativos: {len(plano)}  '
          f'(qty_neg_total={sum(p["qty_neg_orig"] for p in plano):,.2f})')
    print(f'  Zerados apenas com outros lotes:      {n_full}')
    print(f'  Zerados com outros lotes + MIGRACAO:  {n_with_mig}')
    print(f'  Nao tratados (lote ja e MIGRACAO):    {n_sem_acao}')
    print(f'')
    print(f'  qty consumida de outros lotes:    {sum_outros:>14,.2f}')
    print(f'  qty residual para MIGRACAO:       {sum_migracao:>14,.2f}')
    print(f'  qty nao tratada:                  {sum_sem_acao:>14,.2f}')

    if n_sem_acao > 0:
        print(f'\n  --- Top 10 nao tratados (lote ja e MIGRACAO sem outras fontes) ---')
        not_tr = [p for p in plano if p['residual_sem_acao'] > 0]
        not_tr.sort(key=lambda x: -x['residual_sem_acao'])
        for p in not_tr[:10]:
            cod = pmap.get(p['pid'], '?')
            print(f"    cod={cod:<10} qty_neg={p['qty_neg_orig']:>12,.2f}  consumido_outros={p['consumido_outros']:>12,.2f}  residual={p['residual_sem_acao']:>12,.2f}")


def salvar_plano_csv(plano, pmap, path):
    cols = ['quant_id_neg', 'cod', 'product_id', 'lot_id_neg', 'lot_name_neg',
            'location_id', 'qty_neg_orig', 'consumido_outros',
            'residual_migracao', 'residual_sem_acao', 'n_fontes',
            'fontes_detalhe']
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for p in plano:
            n = p['quant_neg']
            fontes_str = '; '.join(
                f"q{x['quant_id']}/{x['lot_name']}/loc{x['location_id']}={x['take']:.2f}"
                for x in p['fontes_usadas']
            )
            w.writerow({
                'quant_id_neg': n['id'],
                'cod': pmap.get(p['pid'], ''),
                'product_id': p['pid'],
                'lot_id_neg': p['lid_neg'],
                'lot_name_neg': n['lot_id'][1] if n.get('lot_id') else '(sem lote)',
                'location_id': p['loc_neg'],
                'qty_neg_orig': p['qty_neg_orig'],
                'consumido_outros': p['consumido_outros'],
                'residual_migracao': p['residual_migracao'],
                'residual_sem_acao': p['residual_sem_acao'],
                'n_fontes': len(p['fontes_usadas']),
                'fontes_detalhe': fontes_str,
            })


def aplicar_inventory(odoo, quant_id: int, nova_qty: float) -> Dict[str, Any]:
    """Aplica inventory adjustment: write inventory_quantity + action_apply_inventory."""
    odoo.write('stock.quant', [quant_id], {'inventory_quantity': nova_qty})
    odoo.execute_kw('stock.quant', 'action_apply_inventory', [[quant_id]])
    return {'quant_id': quant_id, 'nova_qty': nova_qty}


def buscar_ou_criar_quant_migracao(
    odoo, product_id, location_id, lot_id_migracao,
) -> Optional[int]:
    """Retorna ID do quant MIGRACAO em (product, location). Cria se nao existir.

    Cria com inventory_quantity=0 inicial — caller deve ajustar depois.
    """
    qs = odoo.search('stock.quant', [
        ('product_id', '=', product_id),
        ('company_id', '=', COMPANY_FB),
        ('location_id', '=', location_id),
        ('lot_id', '=', lot_id_migracao),
    ])
    if qs:
        return qs[0]
    # criar com 0 (inventory_quantity sera ajustado em seguida)
    return odoo.create('stock.quant', {
        'product_id': product_id,
        'company_id': COMPANY_FB,
        'location_id': location_id,
        'lot_id': lot_id_migracao,
        'inventory_quantity': 0,
    })


def executar_plano(odoo, plano, lot_migracao_por_produto, pmap, csv_path):
    lot_svc = StockLotService(odoo=odoo)
    audit_rows = []
    falhas = []
    t0 = time.time()
    total = len(plano)

    for idx, p in enumerate(plano, 1):
        if p['residual_sem_acao'] > 0 and not p['fontes_usadas']:
            audit_rows.append({
                'idx': idx,
                'quant_id_neg': p['quant_neg']['id'],
                'cod': pmap.get(p['pid'], ''),
                'status': 'SKIP_NEG_EH_MIGRACAO',
                'qty_neg_orig': p['qty_neg_orig'],
                'consumido_outros': 0,
                'residual_migracao': 0,
                'tempo_ms': 0,
                'erro': 'lote do quant_neg ja eh MIGRACAO e sem fontes alternativas',
            })
            continue

        t1 = time.time()
        try:
            # 1. Reduz cada fonte usada
            for f in p['fontes_usadas']:
                # busca FRESCO o quant para evitar usar valor stale
                cur = odoo.read('stock.quant', [f['quant_id']], ['quantity', 'reserved_quantity'])[0]
                cur_qty = cur['quantity']
                cur_reserv = cur.get('reserved_quantity') or 0
                disp_atual = cur_qty - cur_reserv
                take = min(f['take'], disp_atual)
                if take <= 0:
                    logger.warning(
                        f'[{idx}/{total}] fonte {f["quant_id"]} sem saldo disponivel agora '
                        f'(cur={cur_qty} reserved={cur_reserv}); pulando.'
                    )
                    continue
                nova = cur_qty - take
                aplicar_inventory(odoo, f['quant_id'], nova)

            # 2. MIGRACAO se necessario
            mig_qty_aplicada = 0.0
            mig_quant_id = None
            if p['residual_migracao'] > 0:
                lot_mig = lot_migracao_por_produto.get(p['pid'])
                if not lot_mig:
                    # criar lote MIGRACAO para o produto
                    lot_mig, _ = lot_svc.criar_se_nao_existe(
                        NOME_LOTE_MIGRACAO_PREFERIDO, p['pid'], COMPANY_FB,
                    )
                    lot_migracao_por_produto[p['pid']] = lot_mig
                mig_quant_id = buscar_ou_criar_quant_migracao(
                    odoo, p['pid'], p['loc_neg'], lot_mig,
                )
                cur_mig = odoo.read('stock.quant', [mig_quant_id],
                                    ['quantity', 'reserved_quantity'])[0]
                # nao bloqueia em reserved_quantity (MIGRACAO costuma nao ter reserva)
                nova_mig = cur_mig['quantity'] - p['residual_migracao']
                aplicar_inventory(odoo, mig_quant_id, nova_mig)
                mig_qty_aplicada = p['residual_migracao']

            # 3. Zera o quant negativo
            aplicar_inventory(odoo, p['quant_neg']['id'], 0)

            audit_rows.append({
                'idx': idx,
                'quant_id_neg': p['quant_neg']['id'],
                'cod': pmap.get(p['pid'], ''),
                'status': 'OK',
                'qty_neg_orig': p['qty_neg_orig'],
                'consumido_outros': p['consumido_outros'],
                'residual_migracao': mig_qty_aplicada,
                'mig_quant_id': mig_quant_id or '',
                'tempo_ms': int((time.time() - t1) * 1000),
                'erro': '',
            })
            if idx % 10 == 0 or idx == total:
                print(f'  [{idx}/{total}] OK  cod={pmap.get(p["pid"], "?"):<10} '
                      f'qty_neg={p["qty_neg_orig"]:>10,.2f}  '
                      f'outros={p["consumido_outros"]:>10,.2f}  mig={mig_qty_aplicada:>10,.2f}  '
                      f'tempo={int((time.time() - t1) * 1000)}ms')
        except Exception as e:
            logger.error(f'[{idx}/{total}] FALHA quant_neg={p["quant_neg"]["id"]}: {e}')
            audit_rows.append({
                'idx': idx,
                'quant_id_neg': p['quant_neg']['id'],
                'cod': pmap.get(p['pid'], ''),
                'status': 'FALHA',
                'qty_neg_orig': p['qty_neg_orig'],
                'consumido_outros': 0,
                'residual_migracao': 0,
                'tempo_ms': int((time.time() - t1) * 1000),
                'erro': str(e)[:300],
            })
            falhas.append((p['quant_neg']['id'], str(e)))

    # Salva CSV
    cols = ['idx', 'quant_id_neg', 'cod', 'status', 'qty_neg_orig',
            'consumido_outros', 'residual_migracao', 'mig_quant_id',
            'tempo_ms', 'erro']
    with open(csv_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in audit_rows:
            w.writerow({c: r.get(c, '') for c in cols})

    print(f'\n  Tempo total: {int((time.time() - t0))}s')
    print(f'  OK: {sum(1 for r in audit_rows if r["status"] == "OK")}')
    print(f'  SKIP: {sum(1 for r in audit_rows if r["status"].startswith("SKIP"))}')
    print(f'  FALHA: {sum(1 for r in audit_rows if r["status"] == "FALHA")}')
    print(f'  CSV audit: {csv_path}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--confirmar', action='store_true')
    ap.add_argument('--csv-plano', default=CSV_PLANO)
    ap.add_argument('--csv-audit', default=CSV_AUDIT)
    args = ap.parse_args()
    dry_run = not args.confirmar

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        banner(f'ZERAR NEGATIVOS FB  (modo={"DRY-RUN" if dry_run else "EXECUCAO REAL"})')

        banner('1. Coletando dados frescos do Odoo', '-')
        negativos, positivos, lot_migracao_set, lot_migracao_por_produto, pmap = (
            coletar_dados(odoo)
        )

        banner('2. Montando plano de alocacao', '-')
        plano = montar_plano(negativos, positivos, lot_migracao_set)
        imprimir_resumo_plano(plano, pmap)
        salvar_plano_csv(plano, pmap, args.csv_plano)
        print(f'\n  Plano detalhado em {args.csv_plano}')

        if dry_run:
            print('\n  [DRY-RUN] Nada alterado. Use --confirmar para executar.')
            return

        banner('3. Executando inventory adjustments', '-')
        executar_plano(odoo, plano, lot_migracao_por_produto, pmap, args.csv_audit)


if __name__ == '__main__':
    main()
