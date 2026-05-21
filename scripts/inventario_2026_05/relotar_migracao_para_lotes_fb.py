"""Relotagem MIGRAÇÃO -> lotes reais + envio ao Estoque (FB, 2026-05-20).

Pedido do usuario: identificar parte do saldo hoje consolidado no lote generico
'MIGRAÇÃO' (FB/Indisponivel) com os lotes reais correspondentes e DEIXA-LOS
DISPONIVEIS no FB/Estoque.

Fluxo em 2 etapas (ambas via inventory adjustment em 2 passos —
stock.quant.action_apply_inventory; contraparte cai no Estoque Virtual/Ajuste de
Inventario; saldo TOTAL do produto preservado):

  --etapa relotar  (JA EXECUTADO 2026-05-20 16:07):
      FB/Indisponivel/MIGRAÇÃO  -> FB/Indisponivel/<lote real>
      reduz MIGRAÇÃO e cria o lote real na MESMA location (Indisponivel).

  --etapa enviar-estoque:
      FB/Indisponivel/<lote real> -> FB/Estoque/<lote real>
      reduz o lote real no Indisponivel (zera) e cria no Estoque (loc 8),
      onde o saldo volta a ser DISPONIVEL (stock.rule enxergam o WH/Estoque).

O efeito liquido das 2 etapas e' identico a um retorno direto
MIGRAÇÃO(Indisponivel) -> lote real(Estoque): mesmo saldo, mesma contraparte.

Itens (saldo/lote verificados no Odoo):
  205030410  113     ME138-086/26
  205130298  136,47  ME 257-175/25

NENHUMA etapa e' idempotente — NAO re-executar a mesma etapa com --confirmar.

Uso:
    python scripts/inventario_2026_05/relotar_migracao_para_lotes_fb.py --etapa enviar-estoque
    python scripts/inventario_2026_05/relotar_migracao_para_lotes_fb.py --etapa enviar-estoque --confirmar
"""
import argparse
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

from app import create_app  # noqa: E402
from app.odoo.constants.locations import get_local_indisponivel, get_location_id  # noqa: E402
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-7s | %(message)s')
logger = logging.getLogger('relotar_migracao_fb')

# ---- Constantes D011 (.claude/references/odoo/IDS_FIXOS.md, locations.py) ----
COMPANY = 1            # FB
LOC_INDISP = get_local_indisponivel(1)   # FB/Indisponivel (central)
LOC_ESTOQUE = get_location_id(1)         # FB/Estoque (central)
LOTE_MIGRACAO_VARIANTES = ['MIGRAÇÃO', 'MIGRACAO', 'MIGRAÇAO']
CASAS = 6
TOL = 0.001

ITENS = [
    {'cod': '205030410', 'qty': 113.0,   'lote_dest': 'ME138-086/26'},
    {'cod': '205130298', 'qty': 136.47,  'lote_dest': 'ME 257-175/25'},
]


def banner(t: str, c: str = '=') -> None:
    print('\n' + c * 96 + f'\n  {t}\n' + c * 96)


# ============================================================
# Helpers Odoo
# ============================================================
def resolver_product_id(odoo, cod: str) -> Optional[int]:
    res = odoo.search_read('product.product', [['default_code', '=', cod]],
                           ['id', 'active'], limit=5)
    if not res:
        return None
    ativos = [r for r in res if r.get('active')]
    return (ativos[0] if ativos else res[0])['id']


def melhor_lote_migracao_na_loc(odoo, pid: int, loc: int):
    """(lot_id, quant) do lote MIGRAÇÃO com MAIOR saldo livre na location `loc`."""
    lids = odoo.search('stock.lot', [
        ['name', 'in', LOTE_MIGRACAO_VARIANTES],
        ['product_id', '=', pid], ['company_id', '=', COMPANY],
    ])
    if not lids:
        return None, None
    quants = odoo.search_read('stock.quant', [
        ['product_id', '=', pid], ['company_id', '=', COMPANY],
        ['location_id', '=', loc], ['lot_id', 'in', lids],
    ], ['id', 'lot_id', 'quantity', 'reserved_quantity'])
    com_saldo = sorted(
        [q for q in quants
         if (float(q['quantity']) - float(q.get('reserved_quantity') or 0)) > 1e-9],
        key=lambda q: -(float(q['quantity']) - float(q.get('reserved_quantity') or 0)))
    return (com_saldo[0]['lot_id'][0], com_saldo[0]) if com_saldo else (lids[0], None)


def buscar_quant(odoo, pid: int, loc: int, lot_id: int):
    qs = odoo.search_read('stock.quant', [
        ['product_id', '=', pid], ['company_id', '=', COMPANY],
        ['location_id', '=', loc], ['lot_id', '=', lot_id],
    ], ['id', 'quantity', 'reserved_quantity'], limit=1)
    return qs[0] if qs else None


def aplicar_ajuste(odoo, quant_id: int, nova_qty: float):
    odoo.write('stock.quant', [quant_id], {'inventory_quantity': nova_qty})
    odoo.execute_kw('stock.quant', 'action_apply_inventory', [[quant_id]])


def aumentar_ou_criar(odoo, pid: int, loc: int, lot_id: int, qty: float):
    """Aumenta (ou cria) quant na loc/lote em qty. Retorna (quant_id, antes, apos)."""
    q = buscar_quant(odoo, pid, loc, lot_id)
    if q:
        antes = float(q['quantity'])
        aplicar_ajuste(odoo, q['id'], antes + qty)
        return q['id'], antes, round(antes + qty, CASAS)
    novo = odoo.create('stock.quant', {
        'product_id': pid, 'company_id': COMPANY,
        'location_id': loc, 'lot_id': lot_id,
        'inventory_quantity': qty,
    })
    odoo.execute_kw('stock.quant', 'action_apply_inventory', [[novo]])
    return novo, 0.0, qty


def _clamp(r: Dict, qty: float, livre: float) -> Optional[float]:
    """Aplica clamp de arredondamento; retorna qty_efetiva ou None (SEM_SALDO)."""
    if qty <= livre:
        return qty
    if qty - livre <= TOL:
        r['clamp_arredondamento'] = {'de': qty, 'para': livre}
        return livre
    r['status'] = 'SEM_SALDO'
    r['erro'] = f'qty={qty} > livre={livre}'
    return None


# ============================================================
# ETAPA 1 — relotar MIGRAÇÃO -> lote real (DENTRO de FB/Indisponivel)
# ============================================================
def processar_relotar(odoo, lot_svc, item, dry_run) -> Dict:
    r = {**item, 'etapa': 'relotar', 'inicio': datetime.now().isoformat(timespec='seconds')}
    qty = round(float(item['qty']), CASAS)
    if qty <= 0:
        r['status'] = 'SKIP_QTD_ZERO'
        return r

    pid = resolver_product_id(odoo, item['cod'])
    if not pid:
        r['status'] = 'PRODUTO_NAO_ENCONTRADO'
        r['erro'] = f'default_code {item["cod"]!r} nao existe'
        return r
    r['product_id'] = pid

    lot_org_id, quant_org = melhor_lote_migracao_na_loc(odoo, pid, LOC_INDISP)
    if not lot_org_id or not quant_org:
        r['status'] = 'SEM_SALDO_MIGRACAO'
        r['erro'] = 'lote MIGRAÇÃO sem saldo em FB/Indisponivel'
        return r
    qtd_org = float(quant_org['quantity'])
    livre = round(qtd_org - float(quant_org.get('reserved_quantity') or 0), CASAS)
    r['saldo_origem'] = {'quant_id': quant_org['id'], 'quantity': qtd_org, 'livre': livre}

    qty_efetiva = _clamp(r, qty, livre)
    if qty_efetiva is None:
        return r
    r['qty_efetiva'] = round(qty_efetiva, CASAS)

    dest_existente = lot_svc.buscar_por_nome(item['lote_dest'], pid, COMPANY)
    r['lote_destino_acao'] = 'reused' if dest_existente else 'will_create'
    if dry_run:
        r['origem_apos_simulado'] = round(qtd_org - qty_efetiva, CASAS)
        r['status'] = 'DRY_RUN_OK'
        return r

    t0 = time.time()
    try:
        aplicar_ajuste(odoo, quant_org['id'], qtd_org - qty_efetiva)
        r['origem_antes'], r['origem_apos'] = qtd_org, round(qtd_org - qty_efetiva, CASAS)
        lot_dest_id, criado = lot_svc.criar_se_nao_existe(item['lote_dest'], pid, COMPANY)
        r['lot_destino_id'], r['lote_destino_criado'] = lot_dest_id, criado
        qid, antes, apos = aumentar_ou_criar(odoo, pid, LOC_INDISP, lot_dest_id, qty_efetiva)
        r['quant_destino_id'], r['destino_antes'], r['destino_apos'] = qid, antes, apos
        r['status'] = 'EXECUTADO'
        r['tempo_ms'] = int((time.time() - t0) * 1000)
    except Exception as exc:
        r['status'] = 'FALHA_ODOO'
        r['erro'] = str(exc)
        logger.exception(f'relotar cod={item["cod"]} falha')
    return r


# ============================================================
# ETAPA 2 — enviar lote real do FB/Indisponivel -> FB/Estoque (disponivel)
# ============================================================
def processar_enviar_estoque(odoo, lot_svc, item, dry_run) -> Dict:
    r = {**item, 'etapa': 'enviar-estoque', 'inicio': datetime.now().isoformat(timespec='seconds')}
    qty = round(float(item['qty']), CASAS)
    if qty <= 0:
        r['status'] = 'SKIP_QTD_ZERO'
        return r

    pid = resolver_product_id(odoo, item['cod'])
    if not pid:
        r['status'] = 'PRODUTO_NAO_ENCONTRADO'
        r['erro'] = f'default_code {item["cod"]!r} nao existe'
        return r
    r['product_id'] = pid

    lote_id = lot_svc.buscar_por_nome(item['lote_dest'], pid, COMPANY)
    if not lote_id:
        r['status'] = 'LOTE_INEXISTENTE'
        r['erro'] = f'lote {item["lote_dest"]!r} nao existe (rodar etapa relotar antes)'
        return r
    r['lot_id'] = lote_id

    # saldo do lote real no Indisponivel (origem)
    q_ind = buscar_quant(odoo, pid, LOC_INDISP, lote_id)
    if not q_ind:
        r['status'] = 'SEM_SALDO_INDISP'
        r['erro'] = f'lote {item["lote_dest"]!r} sem quant em FB/Indisponivel'
        return r
    qtd_ind = float(q_ind['quantity'])
    reserv = float(q_ind.get('reserved_quantity') or 0)
    livre = round(qtd_ind - reserv, CASAS)
    r['saldo_indisp'] = {'quant_id': q_ind['id'], 'quantity': qtd_ind,
                         'reserved': reserv, 'livre': livre}
    if livre <= 0:
        r['status'] = 'SEM_SALDO'
        r['erro'] = f'lote sem saldo livre no Indisponivel (livre={livre})'
        return r

    qty_efetiva = _clamp(r, qty, livre)
    if qty_efetiva is None:
        return r
    r['qty_efetiva'] = round(qty_efetiva, CASAS)

    if dry_run:
        q_est = buscar_quant(odoo, pid, LOC_ESTOQUE, lote_id)
        r['estoque_antes'] = float(q_est['quantity']) if q_est else 0.0
        r['indisp_apos_simulado'] = round(qtd_ind - qty_efetiva, CASAS)
        r['status'] = 'DRY_RUN_OK'
        return r

    t0 = time.time()
    try:
        # reduzir Indisponivel
        aplicar_ajuste(odoo, q_ind['id'], qtd_ind - qty_efetiva)
        r['indisp_antes'], r['indisp_apos'] = qtd_ind, round(qtd_ind - qty_efetiva, CASAS)
        # aumentar/criar no Estoque (mesmo lote)
        qid, antes, apos = aumentar_ou_criar(odoo, pid, LOC_ESTOQUE, lote_id, qty_efetiva)
        r['quant_estoque_id'], r['estoque_antes'], r['estoque_apos'] = qid, antes, apos
        r['status'] = 'EXECUTADO'
        r['tempo_ms'] = int((time.time() - t0) * 1000)
    except Exception as exc:
        r['status'] = 'FALHA_ODOO'
        r['erro'] = str(exc)
        logger.exception(f'enviar-estoque cod={item["cod"]} falha')
    return r


PROCESSADORES = {'relotar': processar_relotar, 'enviar-estoque': processar_enviar_estoque}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--etapa', choices=list(PROCESSADORES), required=True,
                    help='relotar (MIGRAÇÃO->lote em Indisp) | enviar-estoque (lote Indisp->Estoque)')
    ap.add_argument('--confirmar', action='store_true', help='executa real (default dry-run)')
    args = ap.parse_args()
    dry_run = not args.confirmar
    proc = PROCESSADORES[args.etapa]

    banner(f'ETAPA {args.etapa.upper()} — {"DRY-RUN" if dry_run else "EXECUCAO REAL"} '
           f'({len(ITENS)} itens, FB company=1)')

    app = create_app()
    resultados: List[Dict] = []
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        for i, item in enumerate(ITENS, 1):
            r = proc(odoo, lot_svc, item, dry_run)
            resultados.append(r)
            st = r['status']
            if st in ('EXECUTADO', 'DRY_RUN_OK'):
                logger.info(f'[{i}/{len(ITENS)}] {st} cod={item["cod"]} '
                            f'{item["lote_dest"]!r} qty={r.get("qty_efetiva")}')
            else:
                logger.warning(f'[{i}/{len(ITENS)}] {st} cod={item["cod"]}: {r.get("erro")}')

    banner('RESUMO')
    cont = Counter(r['status'] for r in resultados)
    for st, n in cont.most_common():
        print(f'  {st:24s} {n}')
    for r in resultados:
        print(f'\n  cod={r["cod"]} -> {r["lote_dest"]!r} | status={r["status"]}')
        if r['status'] == 'EXECUTADO' and args.etapa == 'enviar-estoque':
            print(f'    FB/Indisponivel {r["indisp_antes"]} -> {r["indisp_apos"]} | '
                  f'FB/Estoque {r["estoque_antes"]} -> {r["estoque_apos"]}')
        elif r['status'] == 'EXECUTADO':
            print(f'    MIGRAÇÃO {r["origem_antes"]} -> {r["origem_apos"]} | '
                  f'{r["lote_dest"]} {r["destino_antes"]} -> {r["destino_apos"]}')
        elif r['status'] == 'DRY_RUN_OK' and args.etapa == 'enviar-estoque':
            print(f'    [DRY] Indisp {r["saldo_indisp"]["livre"]} -> '
                  f'{r.get("indisp_apos_simulado")} | Estoque {r.get("estoque_antes")} '
                  f'-> {round(r.get("estoque_antes",0)+r.get("qty_efetiva",0),CASAS)}')
        elif r['status'] == 'DRY_RUN_OK':
            print(f'    [DRY] MIGRAÇÃO ficaria {r.get("origem_apos_simulado")} | '
                  f'destino {r.get("lote_destino_acao")}')

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    modo = 'dryrun' if dry_run else 'real'
    log_path = _THIS.parent / 'auditoria' / f'log_relotar_migracao_fb_{args.etapa}_{modo}_{ts}.json'
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as fh:
        json.dump({'etapa': args.etapa, 'dry_run': dry_run, 'total': len(resultados),
                   'contagem': dict(cont), 'resultados': resultados},
                  fh, indent=2, default=str, ensure_ascii=False)
    print(f'\n  Log JSON: {log_path}')
    if dry_run:
        print('\n  DRY-RUN — nada gravado. Use --confirmar para executar.')

    return 0 if not any(r['status'].startswith('FALHA') for r in resultados) else 1


if __name__ == '__main__':
    sys.exit(main())
