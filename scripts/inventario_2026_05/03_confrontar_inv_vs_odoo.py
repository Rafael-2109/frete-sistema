"""F7.3 — Confronto inventario fisico x estoque Odoo.

Aplica regras de lote:
- P6: prioridade de escolha de lote alvo = (1) lote inventariado,
      (2) MIGRACAO, (3) mais antigo (menor quant_id)
- P9: qty igual + lote diferente → APENAS_LOTE (caso de rename)

Inputs:
- /tmp/estoque_odoo_2026_05.json (gerado por 01)
- /tmp/inventario_fisico_2026_05.json (gerado por 02)

Outputs:
- docs/inventario-2026-05/07-relatorios/diff-inv-vs-odoo-{FB,CD,LF}.xlsx
- /tmp/diff_inventario_2026_05.json (consumido por 04_propor_ajustes)

Uso:
    python scripts/inventario_2026_05/03_confrontar_inv_vs_odoo.py [--dry-run]

Spec: docs/superpowers/plans/2026-05-17-ajuste-inventario-nacom-lf.md Task 7.3
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

# sys.path para `from app import ...`
_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

import openpyxl  # noqa: E402

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402
from app.utils.timezone import agora_utc_naive  # noqa: E402

OUTPUT_DIR = str(_THIS.parents[2] / 'docs' / 'inventario-2026-05' / '07-relatorios')
COMPANIES = {1: 'FB', 4: 'CD', 5: 'LF'}

INPUT_ESTOQUE = '/tmp/estoque_odoo_2026_05.json'
INPUT_INV = '/tmp/inventario_fisico_2026_05.json'
OUTPUT_JSON = '/tmp/diff_inventario_2026_05.json'


def escolher_lote_alvo(quants_produto: list, lote_inv: str) -> dict:
    """P6: escolhe lote para ajustar entre os quants do produto+company.

    Prioridade: (1) lote inventariado, (2) MIGRACAO, (3) mais antigo
    (menor quant_id).
    """
    if not quants_produto:
        return {}

    if lote_inv:
        for q in quants_produto:
            if (q.get('lote_nome') or '') == lote_inv:
                return q

    for q in quants_produto:
        if (q.get('lote_nome') or '').upper() == 'MIGRACAO':
            return q

    return sorted(quants_produto, key=lambda q: q['quant_id'])[0]


def confrontar_company(
    quants_odoo: list, linhas_inv: list, cid: int
) -> list:
    """Retorna lista de diffs por (cod_produto, lote)."""
    odoo_por_cod = defaultdict(list)
    for q in quants_odoo:
        if q.get('cod_produto'):
            odoo_por_cod[q['cod_produto']].append(q)

    inv_por_cod = defaultdict(list)
    for linha in linhas_inv:
        inv_por_cod[linha['cod_produto']].append(linha)

    diffs = []
    cods_processados = set()

    for cod in set(inv_por_cod.keys()) | set(odoo_por_cod.keys()):
        if cod in cods_processados:
            continue
        cods_processados.add(cod)

        total_odoo = sum(
            Decimal(str(q['quantity'])) for q in odoo_por_cod.get(cod, [])
        )
        total_inv = sum(
            Decimal(linha['qtd_inventario'])
            for linha in inv_por_cod.get(cod, [])
        )

        # P9: mesma quantidade total + lotes diferentes → APENAS_LOTE
        if total_odoo == total_inv and total_odoo > 0:
            lotes_odoo = {
                (q.get('lote_nome') or '')
                for q in odoo_por_cod.get(cod, [])
            }
            lotes_inv = {
                linha.get('lote_inventariado', '')
                for linha in inv_por_cod.get(cod, [])
            }
            if lotes_odoo != lotes_inv:
                diffs.append({
                    'cod_produto': cod,
                    'tipo_produto': int(cod[0]),
                    'company_id': cid,
                    'lote_inventariado': ','.join(sorted(lotes_inv)),
                    'lote_odoo': ','.join(sorted(lotes_odoo)),
                    'qtd_inventario': str(total_inv),
                    'qtd_odoo': str(total_odoo),
                    'qtd_ajuste': '0',
                    'tipo_divergencia': 'APENAS_LOTE',
                })
                continue
            else:
                continue  # sem divergencia

        # Quantidade divergente: 1 linha por lote_odoo + extras de inv
        for q in odoo_por_cod.get(cod, []):
            lote_odoo = q.get('lote_nome') or ''
            inv_match = next(
                (
                    linha for linha in inv_por_cod.get(cod, [])
                    if linha.get('lote_inventariado') == lote_odoo
                ),
                None,
            )
            qty_inv = (
                Decimal(inv_match['qtd_inventario'])
                if inv_match else Decimal('0')
            )
            qty_odoo = Decimal(str(q['quantity']))
            if qty_inv != qty_odoo:
                custo_medio = (
                    str(Decimal(str(q.get('value', 0) or 0)) / qty_odoo)
                    if qty_odoo else '0'
                )
                diffs.append({
                    'cod_produto': cod,
                    'tipo_produto': int(cod[0]),
                    'company_id': cid,
                    'lote_inventariado': (
                        (inv_match or {}).get('lote_inventariado', '')
                    ),
                    'lote_odoo': lote_odoo,
                    'qtd_inventario': str(qty_inv),
                    'qtd_odoo': str(qty_odoo),
                    'qtd_ajuste': str(qty_inv - qty_odoo),
                    'custo_medio': custo_medio,
                    'tipo_divergencia': 'QUANTIDADE',
                })

        # Inventario sem Odoo correspondente
        for linha in inv_por_cod.get(cod, []):
            lote_inv = linha.get('lote_inventariado', '')
            tem_match = any(
                (q.get('lote_nome') or '') == lote_inv
                for q in odoo_por_cod.get(cod, [])
            )
            if not tem_match:
                diffs.append({
                    'cod_produto': cod,
                    'tipo_produto': int(cod[0]),
                    'company_id': cid,
                    'lote_inventariado': lote_inv,
                    'lote_odoo': '',
                    'qtd_inventario': linha['qtd_inventario'],
                    'qtd_odoo': '0',
                    'qtd_ajuste': linha['qtd_inventario'],
                    'tipo_divergencia': 'INVENTARIO_SEM_ODOO',
                })

    return diffs


def main(dry_run: bool) -> None:
    app = create_app()
    with app.app_context():
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        for src in (INPUT_ESTOQUE, INPUT_INV):
            if not os.path.exists(src):
                raise FileNotFoundError(
                    f'Input ausente: {src}. Rode os scripts 01 e 02 antes.'
                )

        with open(INPUT_ESTOQUE) as f:
            estoque = json.load(f)
        with open(INPUT_INV) as f:
            inv = json.load(f)

        odoo = get_odoo_connection()
        total_diffs = []

        for cid_str, c_estoque in estoque['companies'].items():
            cid = int(cid_str)
            quants_raw = c_estoque.get('quants', [])

            # Batch read para resolver cod_produto + lote_nome (P4)
            product_ids = list({
                q['product_id'][0]
                for q in quants_raw if q.get('product_id')
            })
            lot_ids = list({
                q['lot_id'][0]
                for q in quants_raw if q.get('lot_id')
            })
            produtos = (
                {p['id']: p for p in odoo.read(
                    'product.product', product_ids, ['default_code']
                )}
                if product_ids else {}
            )
            lotes = (
                {lo['id']: lo for lo in odoo.read(
                    'stock.lot', lot_ids, ['name']
                )}
                if lot_ids else {}
            )

            quants_odoo = []
            for q in quants_raw:
                pid = q['product_id'][0] if q.get('product_id') else None
                lid = q['lot_id'][0] if q.get('lot_id') else None
                quants_odoo.append({
                    'quant_id': q['id'],
                    'cod_produto': (
                        produtos.get(pid, {}).get('default_code', '') or ''
                    ),
                    'lote_nome': (
                        lotes.get(lid, {}).get('name') if lid else ''
                    ),
                    'quantity': q['quantity'],
                    'value': q.get('value', 0),
                })

            linhas_inv = inv['companies'].get(
                str(cid), {}
            ).get('linhas', [])
            diffs = confrontar_company(quants_odoo, linhas_inv, cid)
            codigo = COMPANIES.get(cid, str(cid))
            print(
                f'\n{codigo} (company_id={cid}): {len(diffs)} divergencias'
            )
            total_diffs.extend(diffs)

            # Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = codigo
            ws.append([
                'cod_produto', 'tipo_produto', 'company_id',
                'lote_inventariado', 'lote_odoo',
                'qtd_inventario', 'qtd_odoo', 'qtd_ajuste',
                'custo_medio', 'tipo_divergencia',
            ])
            for d in diffs:
                ws.append([
                    d['cod_produto'], d['tipo_produto'], d['company_id'],
                    d['lote_inventariado'], d['lote_odoo'],
                    d['qtd_inventario'], d['qtd_odoo'], d['qtd_ajuste'],
                    d.get('custo_medio', ''), d['tipo_divergencia'],
                ])
            xlsx_path = os.path.join(
                OUTPUT_DIR, f'diff-inv-vs-odoo-{codigo}.xlsx'
            )
            wb.save(xlsx_path)
            print(f'  {xlsx_path}')

        if not dry_run:
            with open(OUTPUT_JSON, 'w') as f:
                json.dump(
                    {
                        'diffs': total_diffs,
                        'timestamp': agora_utc_naive().isoformat(),
                    },
                    f, default=str, indent=2,
                )
            print(
                f'\nTotal: {len(total_diffs)} divergencias salvas em '
                f'{OUTPUT_JSON}'
            )
        else:
            print(
                f'\n[DRY RUN] nao gravou {OUTPUT_JSON} '
                f'(total: {len(total_diffs)} divergencias)'
            )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    main(args.dry_run)
