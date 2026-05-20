"""Corrige quants FB com quantity<0 que tem reserved_quantity NEGATIVO.

CONTEXTO: apos cancelar_reservas_migracao.py usar unlink direto em
stock.move.line de MOs, alguns quants ficaram com reserved_quantity
NEGATIVO (estado impossivel na semantica Odoo — reservas sao sempre >=0).
Isso bloqueia action_apply_inventory: o script zerar_negativos_fb.py
reportou OK mas o quantity nao mudou porque o apply foi ignorado.

CORRECAO (autorizada pelo usuario 2026-05-19):
  1. write reserved_quantity=0 (reset do cache inconsistente — NAO cancela
     picking real; reserved<0 nao representa reserva legitima)
  2. write inventory_quantity=0 + action_apply_inventory (zera o saldo)

reserved_quantity<0 NAO corresponde a nenhum picking ativo — as move.line
originais (MOs) ja estavam em state='done' quando foram unlinked.

Uso:
    python scripts/inventario_2026_05/corrigir_reserved_negativo_fb.py
    python scripts/inventario_2026_05/corrigir_reserved_negativo_fb.py --confirmar
"""
import argparse
import csv
import logging
import sys
import time
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app  # noqa: E402  # type: ignore
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402  # type: ignore

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s')
logger = logging.getLogger('corrigir_reserved_neg')

COMPANY_FB = 1
CSV_AUDIT = '/tmp/corrigir_reserved_negativo_fb_audit.csv'


def banner(t, c='='):
    print()
    print(c * 90)
    print(f'  {t}')
    print(c * 90)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--confirmar', action='store_true')
    ap.add_argument('--csv-audit', default=CSV_AUDIT)
    args = ap.parse_args()
    dry_run = not args.confirmar

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        banner(f'CORRIGIR RESERVED NEGATIVO FB  (modo={"DRY-RUN" if dry_run else "EXECUCAO"})')

        qids = odoo.search('stock.quant', [
            ('company_id', '=', COMPANY_FB),
            ('location_id.usage', '=', 'internal'),
            ('quantity', '<', -0.001),
        ])
        print(f'Quants negativos FB: {len(qids)}')
        if not qids:
            print('Nada a fazer — 0 negativos.')
            return

        data = odoo.read('stock.quant', qids, [
            'id', 'product_id', 'location_id', 'quantity', 'reserved_quantity',
        ])
        soma_qty = sum(d['quantity'] for d in data)
        soma_res = sum(d['reserved_quantity'] for d in data)
        n_res_neg = sum(1 for d in data if d['reserved_quantity'] < -0.001)
        print(f'  soma quantity:  {soma_qty:>14,.2f}')
        print(f'  soma reserved:  {soma_res:>14,.2f}')
        print(f'  com reserved<0: {n_res_neg}/{len(data)}')

        # amostra
        print('\n  Amostra (top 10 por |qty|):')
        for d in sorted(data, key=lambda x: x['quantity'])[:10]:
            print(f"    {d['id']:>6}  {d['product_id'][1][:40]:<40} "
                  f"loc={d['location_id'][1]:<32} qty={d['quantity']:>12,.2f} "
                  f"reserved={d['reserved_quantity']:>12,.2f}")

        if dry_run:
            print('\n  [DRY-RUN] nada alterado. Use --confirmar.')
            return

        # 1. Reset reserved em massa
        banner('Executando correcao', '-')
        print(f'[1/2] write reserved_quantity=0 em {len(qids)} quants...')
        odoo.write('stock.quant', qids, {'reserved_quantity': 0})

        # 2. inventory_quantity=0 + apply (loop — apply nao aceita batch)
        print(f'[2/2] inventory_quantity=0 + action_apply_inventory...')
        t0 = time.time()
        audit = []
        ok, fail = 0, []
        for i, qid in enumerate(qids, 1):
            d = next(x for x in data if x['id'] == qid)
            try:
                odoo.write('stock.quant', [qid], {'inventory_quantity': 0})
                odoo.execute_kw('stock.quant', 'action_apply_inventory', [[qid]])
                ok += 1
                audit.append({
                    'quant_id': qid, 'cod': d['product_id'][1],
                    'location': d['location_id'][1],
                    'qty_antes': d['quantity'],
                    'reserved_antes': d['reserved_quantity'],
                    'status': 'OK', 'erro': '',
                })
                if i % 10 == 0 or i == len(qids):
                    print(f'  [{i}/{len(qids)}] tempo={int(time.time() - t0)}s')
            except Exception as e:
                fail.append((qid, str(e)))
                audit.append({
                    'quant_id': qid, 'cod': d['product_id'][1],
                    'location': d['location_id'][1],
                    'qty_antes': d['quantity'],
                    'reserved_antes': d['reserved_quantity'],
                    'status': 'FALHA', 'erro': str(e)[:200],
                })
                logger.error(f'FALHA {qid}: {e}')

        # CSV
        with open(args.csv_audit, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=[
                'quant_id', 'cod', 'location', 'qty_antes',
                'reserved_antes', 'status', 'erro'])
            w.writeheader()
            w.writerows(audit)

        print(f'\n  OK={ok}  FALHAS={len(fail)}  tempo={int(time.time() - t0)}s')
        for qid, err in fail[:5]:
            print(f'    FALHA {qid}: {err[:150]}')

        # Auditoria final
        banner('Validacao final', '=')
        qids_fim = odoo.search('stock.quant', [
            ('company_id', '=', COMPANY_FB),
            ('location_id.usage', '=', 'internal'),
            ('quantity', '<', -0.001),
        ])
        print(f'  NEGATIVOS RESIDUAIS FB: {len(qids_fim)}')
        print(f'  CSV audit: {args.csv_audit}')


if __name__ == '__main__':
    main()
