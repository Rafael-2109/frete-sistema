"""Ajuste pontual de UM stock.quant por delta, via primitiva oficial
StockQuantAdjustmentService.ajustar_quant (inventory adjustment, gera stock.move).

Generico e reutilizavel (substitui scripts pontuais por quant). Para quants
conhecidos, valida a identidade (produto/lote/local) antes de mexer — defesa
contra ajustar o quant errado.

Uso:
  python scripts/inventario_2026_05/ajuste_quant_cd.py --quant-id 255902 --delta 21            # dry-run
  python scripts/inventario_2026_05/ajuste_quant_cd.py --quant-id 255902 --delta 21 --confirmar

Historico deste quant 255902 (AZEITE 4729098, lote 139/26, CD/Estoque):
  21/05 +10.000 (paliativo)  ->  21/05 -6.956 (reversao parcial)  ->  22/05 +21 (fechar conjunto em 967)
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app  # noqa: E402
from app.odoo.services.stock_quant_adjustment_service import (  # noqa: E402
    StockQuantAdjustmentService,
)
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

# Invariantes de quants conhecidos -> validacao defensiva de identidade
INVARIANTES = {
    255902: dict(product_id=27748, company_id=4, location_id=32,
                 lote_substr='139/26', desc='AZEITE 4729098 / lote 139/26 / CD/Estoque'),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    ap.add_argument('--quant-id', required=True, type=int)
    ap.add_argument('--delta', required=True, type=float)
    ap.add_argument('--confirmar', action='store_true', default=False)
    args = ap.parse_args()
    confirmar = args.confirmar

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        svc = StockQuantAdjustmentService(odoo=odoo)

        rows = odoo.read('stock.quant', [args.quant_id],
                         ['id', 'product_id', 'company_id', 'location_id', 'lot_id',
                          'quantity', 'reserved_quantity'])
        if not rows:
            print(f'ABORT: quant_id={args.quant_id} nao encontrado.')
            return 1
        q = rows[0]

        inv = INVARIANTES.get(args.quant_id)
        if inv:
            probs = []
            if (q.get('product_id') or [None])[0] != inv['product_id']:
                probs.append(f"product_id={q.get('product_id')} != {inv['product_id']}")
            if (q.get('company_id') or [None])[0] != inv['company_id']:
                probs.append(f"company_id={q.get('company_id')} != {inv['company_id']}")
            if (q.get('location_id') or [None])[0] != inv['location_id']:
                probs.append(f"location_id={q.get('location_id')} != {inv['location_id']}")
            if not q.get('lot_id') or str(inv['lote_substr']) not in str(q['lot_id'][1]):
                probs.append(f"lot_id={q.get('lot_id')} nao contem {inv['lote_substr']!r}")
            if probs:
                print('ABORT: identidade do quant diverge do esperado:')
                for p in probs:
                    print(f'  - {p}')
                return 1

        qa = float(q['quantity'])
        res = float(q['reserved_quantity'] or 0)
        print('=' * 78)
        print(f"  quant {args.quant_id} | {(q.get('product_id') or [None, '?'])[1]}")
        print(f"  {(q.get('location_id') or [None, '?'])[1]} | lote {(q.get('lot_id') or [None, '(sem)'])[1]}")
        print(f"  qty_antes={qa:,.4f}  reservada={res:,.4f}  livre={qa - res:,.4f}")
        print(f"  DELTA={args.delta:+,.4f}  ->  qty_apos_esperada={qa + args.delta:,.4f}")
        print(f"  MODO: {'EXEC REAL' if confirmar else 'DRY-RUN'}")
        print('=' * 78)

        r = svc.ajustar_quant(
            quant_id=args.quant_id, delta=args.delta,
            validar_nao_negativar=True, validar_nao_abaixo_reserva=True,
            dry_run=not confirmar,
        )
        print('\nRESULTADO:')
        print(json.dumps(r, indent=2, default=str, ensure_ascii=False))

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        modo = 'real' if confirmar else 'dryrun'
        log_dir = _THIS.parent / 'auditoria'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f'log_ajuste_quant_{args.quant_id}_{modo}_{ts}.json'
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump({'quant_id': args.quant_id, 'delta': args.delta, 'modo': modo,
                       'identidade': q, 'resultado': r}, f, indent=2, default=str, ensure_ascii=False)
        print(f'\nLog: {log_path}')

        ok = r.get('status') in ('DRY_RUN_OK', 'EXECUTADO', 'NOOP')
        if not confirmar and ok:
            print('\nDRY-RUN — nada gravado. Use --confirmar para aplicar.')
        return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
