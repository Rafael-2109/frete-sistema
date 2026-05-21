"""fat_lf_06_consolidar_validos.py — Garante estoque VALIDO (lote nao-vencido) >= QTD por produto.

Problema: action_assign do CIEL IT pula lotes VENCIDOS e exige lote em produtos
lot-tracked. Resultado: reserva parcial OU falha "necessario fornecer lote".

Solucao (generaliza G014): para cada produto cujo estoque livre em lotes VALIDOS
(nao-vencidos, com lote) na location principal < QTD, migra a diferenca de quants
VENCIDOS + SEM-LOTE para um lote fresco FAT-{cod}-YYYYMMDD (exp +1 ano) na principal,
via inventory adjustment. Depois action_assign reserva QTD com lotes validos.

Le ajustes do ciclo FATURAMENTO_LF_2026_05_20 (pendentes: fase None/F5c nao-done).
Idempotente (lote fresco reutilizado; so migra o que falta).

Uso:
  python scripts/inventario_2026_05/fat_lf_06_consolidar_validos.py            # dry-run
  python scripts/inventario_2026_05/fat_lf_06_consolidar_validos.py --confirmar
  python ... --filtro 104000033   # so um cod (teste)
"""
import argparse
import os
import sys
import warnings
from datetime import datetime, timedelta

warnings.simplefilter('ignore')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

CICLO = 'FATURAMENTO_LF_2026_05_20'
PRINCIPAL = {1: 8, 5: 42}
DEC = 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true')
    ap.add_argument('--filtro', default=None, help='CSV de cods')
    args = ap.parse_args()
    dry = not args.confirmar
    filtro = [c.strip() for c in args.filtro.split(',')] if args.filtro else None

    app = create_app()
    with app.app_context():
        from app.odoo.models.ajuste_estoque_inventario import AjusteEstoqueInventario
        o = get_odoo_connection()
        HOJE = datetime.utcnow()
        EXP_NOVO = (HOJE + timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')

        q = (AjusteEstoqueInventario.query.filter_by(ciclo=CICLO)
             .filter(AjusteEstoqueInventario.fase_pipeline.is_(None)))
        if filtro:
            q = q.filter(AjusteEstoqueInventario.cod_produto.in_(filtro))
        ajustes = q.all()
        # agregacao por (cod, company_origem) — company_origem do acao
        from app.odoo.services.inventario_pipeline_service import ACAO_PARA_DIRECAO
        need_por = {}  # (cod, comp) -> qtd
        for a in ajustes:
            if a.acao_decidida not in ACAO_PARA_DIRECAO:
                continue
            _, origem, _ = ACAO_PARA_DIRECAO[a.acao_decidida]
            key = (a.cod_produto, origem)
            need_por[key] = need_por.get(key, 0) + float(abs(a.qtd_ajuste or 0))

        print(f'{len(need_por)} (cod,empresa) a verificar | modo={"DRY" if dry else "REAL"}')
        consolidados = pulados = falhas = 0
        for (cod, comp), qtd in sorted(need_por.items()):
            principal = PRINCIPAL[comp]
            prod = o.search_read('product.product', [['default_code', '=', cod]],
                                 ['id', 'tracking'], limit=1)
            if not prod:
                continue
            pid = prod[0]['id']
            quants = o.search_read('stock.quant',
                                   [['product_id', '=', pid], ['company_id', '=', comp],
                                    ['location_id', 'child_of', principal], ['quantity', '>', 0]],
                                   ['id', 'lot_id', 'quantity', 'reserved_quantity', 'location_id', 'create_date'],
                                   order='create_date asc')
            # expiracao dos lotes
            lot_ids = [x['lot_id'][0] for x in quants if x.get('lot_id')]
            exp = {}
            if lot_ids:
                for l in o.read('stock.lot', lot_ids, ['expiration_date']):
                    exp[l['id']] = l.get('expiration_date')

            def vencido(qd):
                if not qd.get('lot_id'):
                    return False
                e = exp.get(qd['lot_id'][0])
                if not e:
                    return False
                try:
                    return datetime.strptime(e.split(' ')[0], '%Y-%m-%d') < HOJE
                except Exception:
                    return False

            tracking = prod[0]['tracking']
            valido_free = sum(float(x['quantity']) - float(x.get('reserved_quantity') or 0)
                              for x in quants if x.get('lot_id') and not vencido(x))
            # fontes: vencidos + sem-lote (livres)
            fontes = [x for x in quants if (not x.get('lot_id')) or vencido(x)]
            fonte_free = sum(float(x['quantity']) - float(x.get('reserved_quantity') or 0) for x in fontes)
            # REGRA: produto lot-tracked -> eliminar TODAS as fontes (no-lot/expired) migrando
            # para lote fresco valido (action_assign nunca pega no-lot/expired -> sem erro de lote
            # e sem parcial). Produto non-tracked -> no-lot eh OK, nao migra.
            if tracking in ('lot', 'serial') and fonte_free > 0.01:
                migrar_total = round(fonte_free, DEC)
            elif valido_free < qtd - 0.5 and fonte_free > 0.01:
                migrar_total = round(min(qtd - valido_free, fonte_free), DEC)
            else:
                pulados += 1
                continue
            print(f'  {cod} c{comp}: valido={valido_free:.1f} QTD={qtd:.1f} tracking={tracking} '
                  f'-> migrar {migrar_total:.1f} (fontes venc/sem-lote livre={fonte_free:.1f})')
            if dry:
                continue
            # criar lote fresco
            lname = f'FAT-{cod}-{HOJE.strftime("%Y%m%d")}'
            existing = o.search_read('stock.lot', [['name', '=', lname], ['product_id', '=', pid]], ['id'], limit=1)
            if existing:
                fresh_lot = existing[0]['id']
            else:
                fresh_lot = o.create('stock.lot', {'name': lname, 'product_id': pid,
                                                    'company_id': comp, 'expiration_date': EXP_NOVO})
            restante = migrar_total
            try:
                for x in fontes:
                    if restante <= 0.01:
                        break
                    livre = float(x['quantity']) - float(x.get('reserved_quantity') or 0)
                    if livre <= 0:
                        continue
                    mover = min(livre, restante)
                    # reduzir origem
                    o.write('stock.quant', [x['id']], {'inventory_quantity': round(float(x['quantity']) - mover, DEC)})
                    o.execute_kw('stock.quant', 'action_apply_inventory', [[x['id']]])
                    # aumentar/criar destino (lote fresco) na principal
                    dq = o.search_read('stock.quant', [['product_id', '=', pid], ['company_id', '=', comp],
                                                       ['location_id', '=', principal], ['lot_id', '=', fresh_lot]],
                                       ['id', 'quantity'], limit=1)
                    if dq:
                        o.write('stock.quant', [dq[0]['id']], {'inventory_quantity': round(float(dq[0]['quantity']) + mover, DEC)})
                        o.execute_kw('stock.quant', 'action_apply_inventory', [[dq[0]['id']]])
                    else:
                        nid = o.create('stock.quant', {'product_id': pid, 'company_id': comp,
                                                       'location_id': principal, 'lot_id': fresh_lot,
                                                       'inventory_quantity': round(mover, DEC)})
                        o.execute_kw('stock.quant', 'action_apply_inventory', [[nid]])
                    restante -= mover
                if restante > 0.5:
                    print(f'    AVISO {cod}: faltou {restante:.1f} (sem fonte venc/sem-lote suficiente)')
                consolidados += 1
            except Exception as e:
                falhas += 1
                print(f'    FALHA {cod}: {str(e)[:120]}')

        print(f'\n  consolidados={consolidados} pulados(ja validos)={pulados} falhas={falhas}')


if __name__ == '__main__':
    main()
