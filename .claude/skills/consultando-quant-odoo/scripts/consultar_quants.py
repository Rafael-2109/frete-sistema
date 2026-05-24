"""consultar_quants.py — skill `consultando-quant-odoo`: READ-only de stock.quant ao vivo.

Expõe StockQuantQueryService.listar_quants via CLI. Sem --dry-run/--confirmar
(read-only, sempre exec).

Exemplos:
  # Saldo dos cods em loc !=Indisponivel (agregado)
  python consultar_quants.py --cods 4856125,105000025 --excluir-indisp --agregar
  # Quants em lote MIGRACAO em FB
  python consultar_quants.py --com-lote MIGRA --empresas FB
"""
import argparse
import json
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[4]))

from app import create_app  # noqa: E402
from app.odoo.estoque.scripts.consulta_quant import (  # noqa: E402
    INDISP, StockQuantQueryService,
)
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    ap.add_argument('--cods', help='Lista de default_codes (csv)')
    ap.add_argument('--pids', help='Lista de product_ids (csv)')
    ap.add_argument('--empresas', help='Empresas (csv): FB,CD,LF')
    ap.add_argument('--excluir-indisp', action='store_true',
                    help='Exclui locations Indisponivel (FB=31088, CD=31090, LF=31091)')
    ap.add_argument('--com-lote', help='Padrao ilike no nome do lote (ex.: "MIGRA")')
    ap.add_argument('--incluir-qty-zero', action='store_true',
                    help='Incluir quants com quantity=0 (default: excluir)')
    ap.add_argument('--only-principal', action='store_true',
                    help='Apenas location principal (FB=8, CD=32, LF=42)')
    ap.add_argument('--agregar', action='store_true',
                    help='Agregar por (cod, empresa)')
    ap.add_argument('--limit', type=int, default=20000)
    ap.add_argument('--formato', choices=['json', 'tabela'], default='tabela')
    args = ap.parse_args()

    cods = [s.strip() for s in args.cods.split(',') if s.strip()] if args.cods else None
    pids = [int(s) for s in args.pids.split(',') if s.strip()] if args.pids else None
    empresas = [s.strip().upper() for s in args.empresas.split(',') if s.strip()] if args.empresas else None
    locations_excluir = list(INDISP.values()) if args.excluir_indisp else None

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        svc = StockQuantQueryService(odoo=odoo)
        res = svc.listar_quants(
            cods=cods, pids=pids, empresas=empresas,
            locations_excluir=locations_excluir, com_lote=args.com_lote,
            incluir_qty_zero=args.incluir_qty_zero,
            only_principal=args.only_principal,
            agregar=args.agregar, limit=args.limit,
        )

        if args.formato == 'json':
            print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
            return 0

        # Tabela legivel
        print(f'Total quants: {res["total_quants"]}')
        print()
        if args.agregar and res.get('agregado'):
            print('=== AGREGADO por (cod, empresa) ===')
            print(f'{"cod":<12} {"emp":<3} {"qty_total":>12} {"reserved":>10} {"avail":>10} {"n_quants":>4}  produto')
            for (cod, emp), v in sorted(res['agregado'].items()):
                print(f'{cod:<12} {emp:<3} {v["qty_total"]:>12.4f} {v["reserved_total"]:>10.4f} '
                      f'{v["available_total"]:>10.4f} {v["n_quants"]:>4}  {v["product_name"][:50]}')
        else:
            print('=== QUANTS (detalhado) ===')
            print(f'{"id":>8} {"cod":<11} {"emp":<3} {"qty":>10} {"reserved":>10} '
                  f'{"available":>10} {"lote":<24} {"location":<35}')
            for q in res['quants'][:200]:
                print(f'{q["id"]:>8} {q["cod"]:<11} {q["empresa"]:<3} {q["quantity"]:>10.4f} '
                      f'{q["reserved_quantity"]:>10.4f} {q["available"]:>10.4f} '
                      f'{q["lote"][:24]:<24} {q["location_name"][:35]:<35}')
            if res['total_quants'] > 200:
                print(f'  ... ({res["total_quants"] - 200} quants nao exibidos)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
