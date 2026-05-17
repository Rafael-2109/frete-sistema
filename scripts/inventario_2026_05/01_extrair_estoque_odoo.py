"""F7.1 — Extrai estoque atual de FB, CD, LF via stock.quant (Odoo).

Output:
- docs/inventario-2026-05/07-relatorios/estoque-odoo-{FB,CD,LF}.xlsx
- /tmp/estoque_odoo_2026_05.json (consumido por 03_confrontar)

Uso:
    python scripts/inventario_2026_05/01_extrair_estoque_odoo.py [--dry-run]

Spec: docs/superpowers/plans/2026-05-17-ajuste-inventario-nacom-lf.md Task 7.1
"""
import argparse
import json
import os
import sys
from pathlib import Path

# sys.path para imports `from app import ...` (regra CLAUDE.md global)
_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

import openpyxl  # noqa: E402

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402
from app.utils.timezone import agora_utc_naive  # noqa: E402

# Output dir relativo ao projeto (portavel entre maquinas)
OUTPUT_DIR = str(_THIS.parents[2] / 'docs' / 'inventario-2026-05' / '07-relatorios')
COMPANIES = {1: 'FB', 4: 'CD', 5: 'LF'}


def extrair_company(odoo, company_id: int) -> list:
    """Extrai stock.quant para todos os produtos com saldo != 0 da company.

    Filtra somente locations internas (usage='internal') — exclui virtuais
    como Parceiros/Clientes (id=5).
    """
    quants = []
    offset = 0
    page = 500
    while True:
        batch = odoo.search_read(
            'stock.quant',
            [
                ['company_id', '=', company_id],
                ['quantity', '!=', 0],
                ['location_id.usage', '=', 'internal'],
            ],
            ['id', 'product_id', 'lot_id', 'location_id', 'quantity', 'value'],
            offset=offset,
            limit=page,
        )
        if not batch:
            break
        quants.extend(batch)
        offset += page
    return quants


def main(dry_run: bool) -> None:
    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        total = {
            'timestamp': agora_utc_naive().isoformat(),
            'companies': {},
        }

        for cid, codigo in COMPANIES.items():
            print(f'\n=== {codigo} (company_id={cid}) ===')
            quants = extrair_company(odoo, cid)
            print(f'  stock.quant rows: {len(quants)}')

            # Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = f'Estoque {codigo}'
            ws.append([
                'quant_id', 'product_id', 'product_name', 'cod_produto',
                'lot_id', 'lot_name', 'location_id', 'location_name',
                'quantity', 'value', 'custo_unit',
            ])

            # Batch read produtos / lotes / locations (P4 — N+1 → 3 queries)
            product_ids = list({
                q['product_id'][0] for q in quants if q.get('product_id')
            })
            lot_ids = list({
                q['lot_id'][0] for q in quants if q.get('lot_id')
            })
            loc_ids = list({
                q['location_id'][0] for q in quants if q.get('location_id')
            })

            produtos = (
                {p['id']: p for p in odoo.read(
                    'product.product', product_ids, ['default_code', 'name']
                )}
                if product_ids else {}
            )
            lotes = (
                {lo['id']: lo for lo in odoo.read(
                    'stock.lot', lot_ids, ['name']
                )}
                if lot_ids else {}
            )
            locs = (
                {lc['id']: lc for lc in odoo.read(
                    'stock.location', loc_ids, ['complete_name']
                )}
                if loc_ids else {}
            )

            for q in quants:
                pid = q['product_id'][0] if q.get('product_id') else None
                lid = q['lot_id'][0] if q.get('lot_id') else None
                loid = q['location_id'][0] if q.get('location_id') else None
                p = produtos.get(pid, {}) if pid else {}
                cod = p.get('default_code', '')
                qty = q.get('quantity', 0) or 0
                val = q.get('value', 0) or 0
                custo_unit = (val / qty) if qty else 0
                ws.append([
                    q['id'], pid, p.get('name', ''), cod,
                    lid, lotes.get(lid, {}).get('name') if lid else '',
                    loid,
                    locs.get(loid, {}).get('complete_name') if loid else '',
                    qty, val, round(custo_unit, 4),
                ])

            xlsx_path = os.path.join(OUTPUT_DIR, f'estoque-odoo-{codigo}.xlsx')
            wb.save(xlsx_path)
            print(f'  Excel: {xlsx_path}')

            total['companies'][cid] = {'codigo': codigo, 'quants': quants}

        if not dry_run:
            json_path = '/tmp/estoque_odoo_2026_05.json'
            with open(json_path, 'w') as f:
                json.dump(total, f, default=str)
            print(f'\nSnapshot JSON: {json_path}')
        else:
            print('\n[DRY RUN] nao gravou /tmp/estoque_odoo_2026_05.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true',
                        help='nao grava JSON snapshot (apenas Excels)')
    args = parser.parse_args()
    main(args.dry_run)
