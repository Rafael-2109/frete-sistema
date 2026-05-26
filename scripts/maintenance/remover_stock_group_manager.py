"""Remove stock.group_stock_manager (id=42) de usuarios Odoo.

Operacao admin — bloqueia ajuste de inventario (button "Inventory Adjustment"
em stock.quant). Usuarios afetados perdem capacidade de:
  - action_apply_inventory (inventory adjustment wizard)
  - _set_inventory_quantity (botao Aplicar)
  - Configurar parametros de estoque (locations, picking_types, etc.)

MANTEM:
  - stock.group_stock_user (operacional): validar picking, criar MO, ver estoque
  - Outras permissoes (fiscal, financeiro, etc.) inalteradas

Idempotente (Odoo nao reclama se o grupo ja foi removido).

Uso:
    # Dry-run: lista quem perderia o grupo (default — nao escreve)
    python scripts/maintenance/remover_stock_group_manager.py

    # Preservar uids especificos (sempre Rafael uid=42 + extras)
    python scripts/maintenance/remover_stock_group_manager.py --whitelist-uids 6,1239

    # Limitar a uids especificos (apenas estes serao processados)
    python scripts/maintenance/remover_stock_group_manager.py --apenas-uids 1257,75

    # Executar real (apos validacao dry-run)
    python scripts/maintenance/remover_stock_group_manager.py --whitelist-uids 6,1239 --confirmar

Saida JSON com:
  - antes: snapshot de quem tem o grupo
  - alvos: uids que serao processados (excluindo whitelist e Rafael)
  - resultado: por uid, status (REMOVIDO / JA_NAO_TINHA / FALHA)
  - depois: snapshot pos-WRITE
"""
import argparse
import json
import logging
import sys
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
log = logging.getLogger('remover_stock_group_manager')

# stock.group_stock_manager (resolvido via ir.model.data — verificado 2026-05-26)
GROUP_ID_STOCK_MANAGER = 42

# Rafael (uid=42) — admin do sistema, NUNCA remover
RAFAEL_UID = 42


def _parse_uids(s):
    if not s:
        return set()
    return {int(x.strip()) for x in s.split(',') if x.strip()}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--whitelist-uids', type=str, default='',
                        help='CSV de uids a preservar (alem de Rafael uid=42). Ex: "6,1239" para preservar suporte CIEL IT + SMTP.')
    parser.add_argument('--apenas-uids', type=str, default='',
                        help='CSV de uids a processar (limitar escopo). Se omitido, processa TODOS exceto whitelist.')
    parser.add_argument('--confirmar', action='store_true',
                        help='EFETIVA no Odoo. Sem isso = dry-run.')
    parser.add_argument('--quiet', action='store_true', help='Suprime Flask boot stdout.')
    args = parser.parse_args()

    whitelist = _parse_uids(args.whitelist_uids) | {RAFAEL_UID}
    apenas = _parse_uids(args.apenas_uids)

    if args.quiet:
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            app = create_app()
    else:
        app = create_app()

    with app.app_context():
        o = get_odoo_connection()

        # 1) SNAPSHOT ANTES
        antes = o.search_read('res.users',
            [('groups_id', 'in', [GROUP_ID_STOCK_MANAGER]), ('active', '=', True)],
            ['id', 'login', 'name'])
        antes_uids = {u['id'] for u in antes}
        log.info(f'Antes: {len(antes)} usuarios ativos com group {GROUP_ID_STOCK_MANAGER}')

        # 2) DETERMINAR ALVOS
        if apenas:
            alvos = {u['id']: u for u in antes if u['id'] in apenas and u['id'] not in whitelist}
        else:
            alvos = {u['id']: u for u in antes if u['id'] not in whitelist}

        log.info(f'Alvos: {len(alvos)} usuarios (whitelist preservada: {sorted(whitelist)})')

        # 3) DRY-RUN ou EXECUTAR
        resultado = []
        for uid, u in sorted(alvos.items()):
            entry = {'uid': uid, 'login': u['login'], 'name': u['name']}
            if args.confirmar:
                try:
                    # Odoo command (3, id) = remove relacionamento M2M sem deletar grupo
                    o.execute_kw('res.users', 'write', [[uid], {'groups_id': [(3, GROUP_ID_STOCK_MANAGER)]}])
                    entry['status'] = 'REMOVIDO'
                except Exception as e:
                    entry['status'] = 'FALHA'
                    entry['erro'] = str(e)[:200]
                    log.error(f'FALHA uid={uid} login={u["login"]}: {e}')
            else:
                entry['status'] = 'DRY_RUN_REMOVERIA'
            resultado.append(entry)

        # 4) SNAPSHOT DEPOIS (so se confirmou)
        depois = None
        depois_uids = None
        if args.confirmar:
            depois = o.search_read('res.users',
                [('groups_id', 'in', [GROUP_ID_STOCK_MANAGER]), ('active', '=', True)],
                ['id', 'login', 'name'])
            depois_uids = {u['id'] for u in depois}
            log.info(f'Depois: {len(depois)} usuarios ativos com group {GROUP_ID_STOCK_MANAGER}')

        # 5) OUTPUT JSON
        output = {
            'modo': 'confirmado' if args.confirmar else 'dry-run',
            'group_id': GROUP_ID_STOCK_MANAGER,
            'whitelist_uids': sorted(whitelist),
            'apenas_uids': sorted(apenas) if apenas else None,
            'antes': {
                'count': len(antes_uids),
                'uids': sorted(antes_uids),
            },
            'alvos': {
                'count': len(alvos),
                'uids': sorted(alvos.keys()),
            },
            'resultado': resultado,
            'depois': {
                'count': len(depois_uids) if depois_uids else None,
                'uids': sorted(depois_uids) if depois_uids else None,
            } if args.confirmar else None,
            'timestamp': datetime.now().isoformat(),
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
