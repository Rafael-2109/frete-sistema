"""fat_lf_03_prestage.py — Pre-estagia estoque FORA_ESTOQUE para a location principal.

Para os 37 produtos FORA_ESTOQUE (estoque existe na empresa mas em sub-locais
que o executor nao reserva): relocaliza o saldo livre dos sub-locais para a
location principal (LF/Estoque=42 ou FB/Estoque=8), preservando lote, via
inventory adjustment (mesmo padrao testado de 17_transferir_preprod_lf_para_estoque.py).

Fontes tipicas: LF 53 (Pre-Producao) / 54 (Pos-Producao) ; FB 31088 (FB/Indisponivel).
Apos isso, o executor (fat_lf_04) reserva normalmente de 42/8 via FIFO.

Le /tmp/fat_lf_classificacao.json (gerado por fat_lf_02). Idempotente: so move o
necessario (faltam) por produto; se principal ja cobre, pula.

Uso:
  python scripts/inventario_2026_05/fat_lf_03_prestage.py             # dry-run
  python scripts/inventario_2026_05/fat_lf_03_prestage.py --confirmar # executa
"""
import argparse
import json
import os
import sys
import time
import warnings

warnings.simplefilter('ignore')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

CLASSIF_JSON = '/tmp/fat_lf_classificacao.json'
PRINCIPAL = {1: 8, 5: 42}  # company -> location principal
DEC = 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true')
    args = ap.parse_args()
    dry = not args.confirmar

    d = json.load(open(CLASSIF_JSON))
    prestage = d['prestage']
    print(f'FORA_ESTOQUE a pre-estagiar: {len(prestage)} | modo={"DRY-RUN" if dry else "REAL"}')

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        # resolver pids
        cods = list(prestage.keys())
        prods = odoo.search_read('product.product', [['default_code', 'in', cods]],
                                 ['id', 'default_code'])
        cod_pid = {p['default_code']: p['id'] for p in prods}

        ok = falha = pulados = 0
        movido_total = 0.0
        for cod, info in prestage.items():
            comp = info['company']
            principal = PRINCIPAL[comp]
            faltam = float(info['faltam'])
            fontes_locs = [int(x) for x in info['fontes'].keys()]
            pid = cod_pid.get(cod)
            if not pid or faltam <= 0.5 or not fontes_locs:
                pulados += 1
                continue

            # quants livres nos sub-locais fonte (FIFO create_date)
            quants = odoo.search_read('stock.quant',
                                      [['product_id', '=', pid], ['company_id', '=', comp],
                                       ['location_id', 'in', fontes_locs], ['quantity', '>', 0]],
                                      ['id', 'lot_id', 'quantity', 'reserved_quantity', 'location_id'],
                                      order='create_date asc')
            restante = faltam
            movido_cod = 0.0
            for q in quants:
                if restante <= 0.01:
                    break
                livre = float(q['quantity']) - float(q.get('reserved_quantity') or 0)
                if livre <= 0:
                    continue
                mover = min(livre, restante)
                lid = q['lot_id'][0] if q.get('lot_id') else None
                lot_name = q['lot_id'][1] if q.get('lot_id') else '(sem)'
                print(f'  {cod} c{comp}: mover {mover:.2f} de loc{q["location_id"][0]} lote={lot_name} -> loc{principal}')
                if not dry:
                    try:
                        # 1. reduzir origem
                        nova_orig = round(float(q['quantity']) - mover, DEC)
                        odoo.write('stock.quant', [q['id']], {'inventory_quantity': nova_orig})
                        odoo.execute_kw('stock.quant', 'action_apply_inventory', [[q['id']]])
                        # 2. aumentar/criar destino (mesmo lote) na principal
                        ddomain = [['product_id', '=', pid], ['company_id', '=', comp],
                                   ['location_id', '=', principal],
                                   ['lot_id', '=', lid] if lid else ['lot_id', '=', False]]
                        dest = odoo.search_read('stock.quant', ddomain, ['id', 'quantity'], limit=1)
                        if dest:
                            nd = round(float(dest[0]['quantity']) + mover, DEC)
                            odoo.write('stock.quant', [dest[0]['id']], {'inventory_quantity': nd})
                            odoo.execute_kw('stock.quant', 'action_apply_inventory', [[dest[0]['id']]])
                        else:
                            payload = {'product_id': pid, 'company_id': comp,
                                       'location_id': principal, 'inventory_quantity': round(mover, DEC)}
                            if lid:
                                payload['lot_id'] = lid
                            nid = odoo.create('stock.quant', payload)
                            odoo.execute_kw('stock.quant', 'action_apply_inventory', [[nid]])
                        time.sleep(0.2)
                    except Exception as e:
                        print(f'    FALHA {cod}: {e}')
                        falha += 1
                        break
                restante -= mover
                movido_cod += mover
            if movido_cod > 0:
                ok += 1
                movido_total += movido_cod
            if restante > 0.5:
                print(f'    AVISO {cod}: ainda faltam {restante:.2f} apos mover fontes')

        print(f'\n  Produtos movidos: {ok} | falhas: {falha} | pulados: {pulados} | '
              f'qty total movida: {movido_total:.1f}')


if __name__ == '__main__':
    main()
