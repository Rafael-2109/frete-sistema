"""Limpeza pontual: zerar 2 quants ghost do produto 210030005 em FB/Linha Industrializacao LF.

Resíduo de bug do motor de reservas Odoo CIEL IT em 22/07/2024 (picking
FB/SAI/IND/00006, Expedição Industrialização). Detalhes da investigação em
conversa com usuário 2026-05-19.

ESTADO (validado 2026-05-19):
    quant=12073  lot=[2539, '2207/24']  loc=30718  qty=+72000  reserved=+72000
    quant=12128  lot=False              loc=30718  qty=-72000  reserved=-72000

Soma líquida em loc 30718 = ZERO. Os 2 quants são ghost — não há
move.line aberta consumindo. Confirmado em pre-flight:
- ZERO stock.move.line em state IN ['assigned','confirmed','waiting']
  envolvendo loc=30718 deste produto.
- 4 move.lines abertas relevantes do produto tocam OUTRAS locations
  (LF/Parceiros->Clientes e Fornecedores->Estoque), NAO esses quants.

ESTRATEGIA:
    Inventory adjustment via stock.quant.action_apply_inventory:
      - quant 12073: inventory_quantity=0  -> Odoo cria stock.move
        loc 30718 (Linha Indust LF) -> Estoque Virtual/Ajuste de Inventario
        com qty=72000 (sai do estoque) e o quant fica quantity=0
      - quant 12128: inventory_quantity=0  -> Odoo cria stock.move
        Estoque Virtual/Ajuste -> loc 30718 com qty=72000 (entra) e o
        quant negativo fica quantity=0

    Soma das 2 operacoes = zero (valor contabil = R$ 23.932,40 - R$ 23.932,40)

POS-EXECUCAO: apos quantity=0, o Odoo recompute reserved_quantity baseado
em stock.move.line abertas. Como nenhuma toca esses quants, reserved deve
ir para 0. Se nao for, validar manualmente.

Uso:
    python scripts/inventario_2026_05/limpar_quants_ghost_210030005_fb.py            # dry-run
    python scripts/inventario_2026_05/limpar_quants_ghost_210030005_fb.py --confirmar # executar
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
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('limpar_ghost_210030005')

PID = 28052                # FRASCO INCOLOR 200G - MOLHO (210030005)
COMPANY_ID = 1             # FB
LOC = 30718                # FB/Pré-Produção/Linha Industrialização LF
LOTE_2207 = 2539           # stock.lot id do '2207/24'

QUANTS_GHOST = [
    {
        'quant_id': 12073,
        'lote_id': LOTE_2207,
        'lote_nome': '2207/24',
        'qty_esperado': 72000.0,
        'reserved_esperado': 72000.0,
    },
    {
        'quant_id': 12128,
        'lote_id': False,
        'lote_nome': '(SEM LOTE)',
        'qty_esperado': -72000.0,
        'reserved_esperado': -72000.0,
    },
]


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def safeguard_no_open_movelines(odoo) -> dict:
    """Verifica que NENHUMA stock.move.line aberta toca loc=30718
    deste produto. Se houver, abortar — significa que ha operacao
    legitima em curso e nao podemos limpar os ghosts.

    Returns: dict com 'safe': bool e 'mls': lista de move.lines encontradas.
    """
    mls = odoo.search_read('stock.move.line', [
        ['product_id', '=', PID],
        ['company_id', '=', COMPANY_ID],
        ['state', 'not in', ['done', 'cancel']],
        '|',
        ['location_id', '=', LOC],
        ['location_dest_id', '=', LOC],
    ], ['id', 'state', 'lot_id', 'quantity', 'move_id', 'picking_id'])
    return {'safe': len(mls) == 0, 'mls': mls}


def ler_quant(odoo, quant_id):
    qs = odoo.read('stock.quant', [quant_id], [
        'id', 'product_id', 'lot_id', 'location_id', 'quantity',
        'reserved_quantity', 'value', 'in_date', 'write_date',
    ])
    return qs[0] if qs else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--confirmar', action='store_true',
                        help='Executa (default = dry-run)')
    parser.add_argument('--log-json', type=str, default='')
    args = parser.parse_args()

    dry_run = not args.confirmar

    banner(
        f'LIMPEZA QUANTS GHOST — 210030005 FB Linha Indust LF — '
        f'{"DRY-RUN" if dry_run else "EXECUTAR REAL"}'
    )

    app = create_app()
    resultados = []
    with app.app_context():
        odoo = get_odoo_connection()

        # === 1. SAFEGUARD: nenhuma move.line viva pode tocar loc 30718 ===
        banner('1. SAFEGUARD — checar move.lines abertas em loc 30718', c='-')
        chk = safeguard_no_open_movelines(odoo)
        if not chk['safe']:
            print('  ❌ HA move.lines abertas tocando loc 30718:')
            for ml in chk['mls']:
                print(f'    {ml}')
            print('  ABORTANDO — pode haver operacao legitima em curso.')
            return 2
        print('  ✅ ZERO move.lines abertas em loc 30718 — seguro para limpar')

        # === 2. LER ESTADO ATUAL DOS QUANTS ===
        banner('2. ESTADO ATUAL', c='-')
        estados_iniciais = []
        for ghost in QUANTS_GHOST:
            q = ler_quant(odoo, ghost['quant_id'])
            if not q:
                print(f'  ❌ quant {ghost["quant_id"]} NAO existe mais — pular')
                continue
            print(f'  quant={q["id"]}  lot={q["lot_id"]}  '
                  f'qty={q["quantity"]}  reserved={q["reserved_quantity"]}  '
                  f'value={q["value"]}')
            # Sanidade: estado bate com o esperado?
            if abs(float(q['quantity']) - ghost['qty_esperado']) > 0.01:
                print(f'    ⚠️  qty divergiu do esperado '
                      f'({ghost["qty_esperado"]}). Continuar mesmo assim? '
                      f'Estado pode ter mudado — ABORTANDO.')
                return 3
            estados_iniciais.append((ghost, q))

        if dry_run:
            banner('DRY-RUN — sem execucao')
            for ghost, q in estados_iniciais:
                print(f'  WOULD: quant={q["id"]} inventory_quantity=0 + apply_inventory')
                print(f'         -> esperado quantity 0 e reserved 0')
            print('\n  Use --confirmar para executar.')
            return 0

        # === 3. EXECUTAR ===
        banner('3. EXECUTAR LIMPEZA', c='-')
        for ghost, q_antes in estados_iniciais:
            r = {
                'quant_id': ghost['quant_id'],
                'lote_nome': ghost['lote_nome'],
                'antes': {
                    'quantity': q_antes['quantity'],
                    'reserved_quantity': q_antes['reserved_quantity'],
                    'value': q_antes['value'],
                },
            }
            t0 = time.time()
            try:
                # Set inventory_quantity = 0
                odoo.write('stock.quant', [ghost['quant_id']],
                           {'inventory_quantity': 0.0})
                # Apply inventory adjustment
                odoo.execute_kw('stock.quant', 'action_apply_inventory',
                                [[ghost['quant_id']]])
                r['acao'] = 'inventory_quantity=0 + action_apply_inventory'
                r['status'] = 'EXECUTADO'
                r['tempo_ms'] = int((time.time() - t0) * 1000)
                # Re-ler quant pos-acao (pode ter sido auto-deletado pelo Odoo)
                q_pos = ler_quant(odoo, ghost['quant_id'])
                if q_pos:
                    r['depois'] = {
                        'quantity': q_pos['quantity'],
                        'reserved_quantity': q_pos['reserved_quantity'],
                        'value': q_pos['value'],
                    }
                else:
                    r['depois'] = 'quant deletado pelo Odoo (_unlink_zero_quants)'
                print(f'  ✅ quant={ghost["quant_id"]} ({ghost["lote_nome"]}) '
                      f'antes qty={q_antes["quantity"]} reserved={q_antes["reserved_quantity"]} '
                      f'-> depois {r["depois"]}')
            except Exception as exc:
                r['status'] = 'FALHA'
                r['erro'] = str(exc)
                r['tempo_ms'] = int((time.time() - t0) * 1000)
                logger.exception(f'quant {ghost["quant_id"]} falhou')
                print(f'  ❌ quant={ghost["quant_id"]} FALHA: {exc}')
            resultados.append(r)

        # === 4. VALIDACAO FINAL ===
        banner('4. VALIDACAO POS-EXECUCAO', c='-')
        # Re-buscar TODOS os quants do produto em loc 30718
        quants_pos = odoo.search_read('stock.quant', [
            ['product_id', '=', PID], ['company_id', '=', COMPANY_ID],
            ['location_id', '=', LOC],
        ], ['id', 'lot_id', 'quantity', 'reserved_quantity', 'value'])
        print(f'  Quants restantes em loc 30718 (produto 28052): {len(quants_pos)}')
        for q in quants_pos:
            lot = q['lot_id'][1] if q['lot_id'] else '(SEM LOTE)'
            print(f'    quant={q["id"]} lot={lot!r} qty={q["quantity"]} '
                  f'reserved={q["reserved_quantity"]} value={q.get("value")}')
        # Saldo total do produto na FB (sanidade — deve ter aumentado em 0)
        quants_fb_total = odoo.search_read('stock.quant', [
            ['product_id', '=', PID], ['company_id', '=', COMPANY_ID],
            ['location_id.usage', '=', 'internal'],
        ], ['id', 'lot_id', 'location_id', 'quantity'])
        soma_fb = sum(float(q['quantity']) for q in quants_fb_total)
        print(f'\n  Saldo total internal FB: {soma_fb:.3f}')
        print('  (esperado: 1601118.000 - mesmo de antes — soma ghost era zero)')

    # === 5. LOG JSON ===
    log_path = args.log_json
    if not log_path:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        modo = 'real' if not dry_run else 'dryrun'
        log_path = str(
            _THIS.parent / 'auditoria' /
            f'log_limpar_ghost_210030005_fb_{modo}_{ts}.json'
        )
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            'args': vars(args),
            'dry_run': dry_run,
            'quants_ghost': QUANTS_GHOST,
            'resultados': resultados,
        }, f, indent=2, default=str)
    print(f'\n  Log JSON: {log_path}')

    falhas = sum(1 for r in resultados if r.get('status') == 'FALHA')
    return 0 if falhas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
