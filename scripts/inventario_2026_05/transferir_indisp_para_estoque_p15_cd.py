# etapa: orquestrador
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""Transferir 2 itens de CD/Indisponivel/MIGRACAO -> CD/Estoque/P-15/05.

Operacao pontual (nao planilha) — pedido do usuario 2026-05-19:
    Filial        : CD (company_id=4)
    Origem        : CD/Indisponivel (location_id=31090) + lote MIGRAÇÃO
    Destino       : CD/Estoque       (location_id=32)    + lote P-15/05
    Modo          : inventory adjustment em 2 passos
                    (1) reduzir quant origem (CD/Indisponivel/MIGRAÇÃO)
                    (2) criar/aumentar quant destino (CD/Estoque/P-15/05)
    Lote P-15/05  : sera criado por produto (nao existe ainda)

Itens (IDs Odoo validados em 2026-05-19):
    cod=4310141 pid=29704 lote_migracao_id=30899 quant_origem=254016
        qty livre=114372.128213 — solicitado 224.000
        produto: AZEITONA VERDE INTEIRA - SACHE 36X80 G - CAMPO BELO

    cod=4840103 pid=27844 lote_migracao_id=31024 quant_origem=254125
        qty livre=17602.75 — solicitado 8.000
        produto: MOSTARDA - GL 4X3,05 KG - CAMPO BELO

Filosofia (alinhamento com inventario 2026-05):
- Inventory adjustment direto (padrao usado nos scripts 11/12/13/14/15/15r)
- D011 referenciado (CD/Indisponivel id=31090 como contraparte)
- Picking interno NAO usado nesta operacao pontual (escopo: 2 itens)
- Tracking='lot' em ambos produtos exige lote real no destino — P-15/05
  sera criado (sem expiration_date)

Uso:
    python scripts/inventario_2026_05/transferir_indisp_para_estoque_p15_cd.py            # dry-run
    python scripts/inventario_2026_05/transferir_indisp_para_estoque_p15_cd.py --confirmar  # executar real
"""
import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app  # noqa: E402
from app.odoo.constants.locations import get_local_indisponivel, get_location_id  # noqa: E402
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('transf_indisp_p15_cd')

COMPANY_ID = 4              # CD
LOC_INDISPONIVEL = get_local_indisponivel(4)   # CD/Indisponivel (central)
LOC_ESTOQUE = get_location_id(4)               # CD/Estoque (central)
LOTE_DESTINO_NOME = 'P-15/05'

ITENS = [
    {
        'cod': '4310141',
        'pid': 29704,
        'lote_origem_id': 30899,        # 'MIGRAÇÃO' (com acento)
        'lote_origem_nome': 'MIGRAÇÃO',
        'quant_origem_id_esperado': 254016,
        'qty_total_origem_esperado': 114372.128213,
        'qty': 224.0,
        'produto_desc': 'AZEITONA VERDE INTEIRA - SACHE 36X80 G - CAMPO BELO',
    },
    {
        'cod': '4840103',
        'pid': 27844,
        'lote_origem_id': 31024,        # 'MIGRAÇÃO' (com acento)
        'lote_origem_nome': 'MIGRAÇÃO',
        'quant_origem_id_esperado': 254125,
        'qty_total_origem_esperado': 17602.75,
        'qty': 8.0,
        'produto_desc': 'MOSTARDA - GL 4X3,05 KG - CAMPO BELO',
    },
]


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def buscar_quant_origem(odoo, pid, lote_id):
    qs = odoo.search_read('stock.quant', [
        ['product_id', '=', pid],
        ['company_id', '=', COMPANY_ID],
        ['location_id', '=', LOC_INDISPONIVEL],
        ['lot_id', '=', lote_id],
    ], ['id', 'quantity', 'reserved_quantity'], limit=1)
    return qs[0] if qs else None


def buscar_quant_destino(odoo, pid, lote_id):
    qs = odoo.search_read('stock.quant', [
        ['product_id', '=', pid],
        ['company_id', '=', COMPANY_ID],
        ['location_id', '=', LOC_ESTOQUE],
        ['lot_id', '=', lote_id],
    ], ['id', 'quantity', 'reserved_quantity'], limit=1)
    return qs[0] if qs else None


def processar_item(odoo, lot_svc, item, dry_run):
    r = {
        **item,
        'inicio': datetime.now().isoformat(timespec='seconds'),
    }
    pid = item['pid']
    qty = item['qty']

    # 1. Quant origem
    q_org = buscar_quant_origem(odoo, pid, item['lote_origem_id'])
    if not q_org:
        r['status'] = 'FALHA_QUANT_ORIGEM_NAO_ENCONTRADO'
        r['erro'] = (
            f'Quant origem nao encontrado: pid={pid} '
            f'loc={LOC_INDISPONIVEL} lote={item["lote_origem_id"]}'
        )
        return r
    r['quant_origem'] = q_org
    livre = float(q_org['quantity']) - float(q_org.get('reserved_quantity') or 0)
    r['origem_qty_livre'] = livre

    # Validar saldo
    TOL = 0.001
    if qty > livre + TOL:
        r['status'] = 'FALHA_SEM_SALDO'
        r['erro'] = (
            f'qty={qty} > livre={livre} (total {q_org["quantity"]}, '
            f'reservada {q_org["reserved_quantity"]})'
        )
        return r

    # Sanidade: ID do quant bate com o esperado?
    if q_org['id'] != item['quant_origem_id_esperado']:
        r['warning_quant_id_diferente'] = {
            'esperado': item['quant_origem_id_esperado'],
            'atual': q_org['id'],
        }

    # 2. Lote destino (P-15/05) — criar ou reusar
    lote_destino_existente = lot_svc.buscar_por_nome(
        LOTE_DESTINO_NOME, pid, COMPANY_ID,
    )
    if dry_run:
        if lote_destino_existente:
            r['lote_destino_id'] = lote_destino_existente
            r['lote_destino_acao'] = 'reused'
        else:
            r['lote_destino_id'] = None
            r['lote_destino_acao'] = 'will_create'
    else:
        if lote_destino_existente:
            r['lote_destino_id'] = lote_destino_existente
            r['lote_destino_acao'] = 'reused'
        else:
            try:
                novo_id = lot_svc.criar(
                    LOTE_DESTINO_NOME, pid, COMPANY_ID,
                    expiration_date=None,
                )
            except Exception as exc:
                r['status'] = 'FALHA_CRIAR_LOTE_DESTINO'
                r['erro'] = f'criar P-15/05: {exc}'
                return r
            r['lote_destino_id'] = novo_id
            r['lote_destino_acao'] = 'created'

    # 3. Quant destino (verificar se ja existe — informativo)
    if r.get('lote_destino_id'):
        q_dst = buscar_quant_destino(odoo, pid, r['lote_destino_id'])
        r['quant_destino_existente'] = q_dst
    else:
        q_dst = None
        r['quant_destino_existente'] = None

    if dry_run:
        r['status'] = 'DRY_RUN_OK'
        r['qty_efetiva'] = qty
        return r

    # ============================================================
    # EXECUCAO
    # ============================================================
    t0 = time.time()
    try:
        # 3a. Reduzir quant origem (CD/Indisponivel/MIGRAÇÃO)
        nova_qty_origem = float(q_org['quantity']) - qty
        odoo.write('stock.quant', [q_org['id']],
                   {'inventory_quantity': nova_qty_origem})
        odoo.execute_kw('stock.quant', 'action_apply_inventory',
                        [[q_org['id']]])
        r['origem_qty_antes'] = float(q_org['quantity'])
        r['origem_qty_apos'] = nova_qty_origem

        # 3b. Aumentar quant destino (CD/Estoque/P-15/05)
        if q_dst:
            # Reusar quant existente
            qty_d_antes = float(q_dst['quantity'])
            nova_qty_dest = qty_d_antes + qty
            odoo.write('stock.quant', [q_dst['id']],
                       {'inventory_quantity': nova_qty_dest})
            odoo.execute_kw('stock.quant', 'action_apply_inventory',
                            [[q_dst['id']]])
            r['quant_destino_id'] = q_dst['id']
            r['destino_qty_antes'] = qty_d_antes
            r['destino_qty_apos'] = nova_qty_dest
        else:
            # Criar quant novo
            quant_dest_id = odoo.create('stock.quant', {
                'product_id': pid,
                'company_id': COMPANY_ID,
                'location_id': LOC_ESTOQUE,
                'lot_id': r['lote_destino_id'],
                'inventory_quantity': qty,
            })
            odoo.execute_kw('stock.quant', 'action_apply_inventory',
                            [[quant_dest_id]])
            r['quant_destino_id'] = quant_dest_id
            r['destino_qty_antes'] = 0.0
            r['destino_qty_apos'] = qty

        r['status'] = 'EXECUTADO'
        r['qty_efetiva'] = qty
        r['tempo_ms'] = int((time.time() - t0) * 1000)
    except Exception as exc:
        r['status'] = 'FALHA_ODOO'
        r['erro'] = str(exc)
        r['tempo_ms'] = int((time.time() - t0) * 1000)
        logger.exception(f'cod={item["cod"]} falha')

    return r


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--confirmar', action='store_true',
                        help='Executa de fato (default = dry-run)')
    parser.add_argument('--log-json', type=str, default='')
    args = parser.parse_args()

    dry_run = not args.confirmar

    banner(
        f'TRANSF CD/Indisp/MIGRAÇÃO -> CD/Estoque/P-15/05 — '
        f'{"DRY-RUN" if dry_run else "EXECUTAR REAL"}'
    )
    for it in ITENS:
        print(
            f'  cod={it["cod"]:>8}  pid={it["pid"]:>6}  '
            f'qty={it["qty"]:>10.3f}  — {it["produto_desc"]}'
        )

    app = create_app()
    resultados = []
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        for item in ITENS:
            banner(f'cod={item["cod"]}  pid={item["pid"]}  qty={item["qty"]}',
                   c='-')
            r = processar_item(odoo, lot_svc, item, dry_run)
            resultados.append(r)
            print(f'  status: {r["status"]}')
            if 'erro' in r:
                print(f'  erro:   {r["erro"]}')
            if 'warning_quant_id_diferente' in r:
                print(f'  WARN: quant_id divergiu — {r["warning_quant_id_diferente"]}')
            if r.get('quant_origem'):
                qo = r['quant_origem']
                print(f'  origem:  quant_id={qo["id"]}  qty_total={qo["quantity"]}  '
                      f'reservada={qo.get("reserved_quantity")}  '
                      f'livre={r.get("origem_qty_livre")}')
            print(f'  lote_destino: id={r.get("lote_destino_id")}  '
                  f'acao={r.get("lote_destino_acao")}')
            if r.get('quant_destino_existente'):
                print(f'  destino_existente: {r["quant_destino_existente"]}')
            else:
                print('  destino_existente: nenhum (sera criado)')
            if r['status'] == 'EXECUTADO':
                print(f'  origem  antes={r["origem_qty_antes"]} apos={r["origem_qty_apos"]}')
                print(f'  destino antes={r["destino_qty_antes"]} apos={r["destino_qty_apos"]}')
                print(f'  tempo: {r["tempo_ms"]} ms')

    banner('RESUMO')
    cnt = {}
    for r in resultados:
        cnt[r['status']] = cnt.get(r['status'], 0) + 1
    for status, n in cnt.items():
        print(f'  {status:35s} {n}')

    soma = sum(r.get('qty_efetiva', 0) for r in resultados
               if r['status'] in ('EXECUTADO', 'DRY_RUN_OK'))
    print(f'\n  Soma qtd transferida: {soma}')

    # Log JSON
    log_path = args.log_json
    if not log_path:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        modo = 'real' if not dry_run else 'dryrun'
        log_path = str(
            _THIS.parent / 'auditoria' /
            f'log_transf_indisp_p15_cd_{modo}_{ts}.json'
        )
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            'args': vars(args),
            'dry_run': dry_run,
            'itens': ITENS,
            'resultados': resultados,
        }, f, indent=2, default=str)
    print(f'\n  Log JSON: {log_path}')

    if dry_run:
        print('\n  DRY-RUN — nada gravado. Use --confirmar para executar.')

    falhas = sum(1 for r in resultados if r['status'].startswith('FALHA'))
    return 0 if falhas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
