"""consultar_quants.py — skill `consultando-quant-odoo`: READ-only de stock.quant ao vivo.

Expõe StockQuantQueryService via CLI multi-modo. Sem --dry-run/--confirmar
(read-only, sempre exec).

Modos:
  - quants (default)             listar_quants — modo classico
  - move-lines                   listar_move_lines_por_quant (NOVO v7)
  - pickings                     listar_pickings_por_quant (NOVO v7)

Exemplos:
  # Saldo dos cods em loc !=Indisponivel (agregado)
  python consultar_quants.py --cods 4856125,105000025 --excluir-indisp --agregar
  # Quants em lote MIGRACAO em FB
  python consultar_quants.py --com-lote MIGRA --empresas FB
  # MLs reservando quants alvo (cross-ref reverso)
  python consultar_quants.py --modo move-lines --quant-ids 229937,217657766
  # Pickings reservando quants alvo (agrupado com metadados)
  python consultar_quants.py --modo pickings --quant-ids 229937,217657766
"""
import argparse
import json
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[4]))

from app.odoo.estoque._cli_utils import (  # noqa: E402
    adicionar_args_padrao, setup_cli_completo,
)
from app.odoo.estoque.scripts.consulta_quant import (  # noqa: E402
    INDISP, StockQuantQueryService,
)
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402


def _ints_from_csv(s):
    return [int(x.strip()) for x in s.split(',') if x.strip()] if s else None


def _strs_from_csv(s):
    return [x.strip() for x in s.split(',') if x.strip()] if s else None


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    ap.add_argument(
        '--modo', choices=['quants', 'move-lines', 'pickings'], default='quants',
        help='Modo de consulta. Default=quants (classico). NOVO v7: '
             'move-lines + pickings (cross-ref reverso via quant_id).',
    )
    # Modo quants
    ap.add_argument('--cods', help='[modo quants] Lista default_codes (csv)')
    ap.add_argument('--pids', help='[modo quants] Lista product_ids (csv)')
    ap.add_argument('--empresas', help='[modo quants] Empresas (csv): FB,CD,LF')
    ap.add_argument('--excluir-indisp', action='store_true',
                    help='[modo quants] Exclui locations Indisponivel')
    ap.add_argument('--com-lote', help='[modo quants] Padrao ilike no nome do lote')
    ap.add_argument('--incluir-qty-zero', action='store_true',
                    help='[modo quants] Incluir quants com quantity=0')
    ap.add_argument('--only-principal', action='store_true',
                    help='[modo quants] Apenas location principal')
    ap.add_argument('--agregar', action='store_true',
                    help='[modo quants] Agregar por (cod, empresa)')
    # Modos move-lines + pickings
    ap.add_argument('--quant-ids',
                    help='[modos move-lines/pickings] IDs de stock.quant (csv)')
    ap.add_argument('--states',
                    help='[modos move-lines/pickings] States de ML (csv). '
                         'Default=assigned,partially_available. '
                         'Use "todos" para sem filtro.')
    ap.add_argument('--incluir-move', action='store_true',
                    help='[modo move-lines] Enriquecer com move_id + production_id')
    # Comum
    ap.add_argument('--limit', type=int, default=20000)
    ap.add_argument('--formato', choices=['json', 'tabela'], default='tabela')
    adicionar_args_padrao(ap)  # --quiet + --forcar-concorrencia (v7)
    args = ap.parse_args()

    app = setup_cli_completo(__file__, args.quiet, args.forcar_concorrencia)
    with app.app_context():
        odoo = get_odoo_connection()
        svc = StockQuantQueryService(odoo=odoo)

        # =========================================================
        # MODO: quants (classico)
        # =========================================================
        if args.modo == 'quants':
            cods = _strs_from_csv(args.cods)
            pids = _ints_from_csv(args.pids)
            empresas = [s.upper() for s in (_strs_from_csv(args.empresas) or [])]
            empresas = empresas or None
            locations_excluir = list(INDISP.values()) if args.excluir_indisp else None
            res = svc.listar_quants(
                cods=cods, pids=pids, empresas=empresas,
                locations_excluir=locations_excluir, com_lote=args.com_lote,
                incluir_qty_zero=args.incluir_qty_zero,
                only_principal=args.only_principal,
                agregar=args.agregar, limit=args.limit,
            )
            return _print_quants(res, args)

        # =========================================================
        # MODO: move-lines (NOVO v7)
        # =========================================================
        if args.modo == 'move-lines':
            quant_ids = _ints_from_csv(args.quant_ids)
            if not quant_ids:
                print('ERRO: --quant-ids obrigatorio em modo move-lines',
                      file=sys.stderr)
                return 2
            states = _parse_states(args.states)
            res = svc.listar_move_lines_por_quant(
                quant_ids=quant_ids, states=states,
                incluir_move=args.incluir_move, limit=args.limit,
            )
            return _print_move_lines(res, args)

        # =========================================================
        # MODO: pickings (NOVO v7)
        # =========================================================
        if args.modo == 'pickings':
            quant_ids = _ints_from_csv(args.quant_ids)
            if not quant_ids:
                print('ERRO: --quant-ids obrigatorio em modo pickings',
                      file=sys.stderr)
                return 2
            states = _parse_states(args.states)
            res = svc.listar_pickings_por_quant(
                quant_ids=quant_ids, states=states, limit=args.limit,
            )
            return _print_pickings(res, args)

    return 0


def _parse_states(s):
    """Parse --states. None default = ['assigned','partially_available']. 'todos' = []."""
    if not s:
        return None
    if s.strip().lower() == 'todos':
        return []
    return _strs_from_csv(s)


def _print_quants(res, args):
    if args.formato == 'json':
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
        return 0
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


def _print_move_lines(res, args):
    if args.formato == 'json':
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
        return 0
    print(f'Total MLs: {res["total_mls"]}')
    print()
    if not res['mls']:
        print('(nenhuma ML encontrada para os quants alvo nos states alvo)')
        return 0
    print('=== MOVE LINES por quant (cross-ref reverso) ===')
    print(f'{"ml_id":>10} {"quant_id":>8} {"emp":<3} {"state":<22} {"qty":>10} '
          f'{"lote":<24} {"location":<22} {"->dest":<22} {"picking":<22}')
    for ml in res['mls'][:200]:
        prod_id_name = ml['product_name'][:18] if ml.get('product_name') else ''
        prod_id_str = f'[{prod_id_name}]'
        prod_id_str = prod_id_str[:20]
        picking_info = (
            f'{ml["picking_name"][:18]} ({ml["picking_state"]})'
            if ml['picking_id'] else 'NO_PICKING'
        )[:22]
        print(f'{ml["id"]:>10} {ml["quant_id"] or 0:>8} {ml["empresa"]:<3} '
              f'{ml["state"]:<22} {ml["quantity"]:>10.4f} '
              f'{ml["lot_name"][:24]:<24} {ml["location_name"][:22]:<22} '
              f'{ml["location_dest_name"][:22]:<22} {picking_info:<22}')
    if res['total_mls'] > 200:
        print(f'  ... ({res["total_mls"] - 200} MLs nao exibidas)')
    return 0


def _print_pickings(res, args):
    if args.formato == 'json':
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
        return 0
    print(f'Total pickings: {res["total_pickings"]} | Total MLs: {res["total_mls"]}')
    if res['mls_sem_picking']:
        print(f'  MLs sem picking (de MO/draft): {len(res["mls_sem_picking"])}')
    print()
    if not res['pickings']:
        print('(nenhum picking encontrado para os quants alvo nos states alvo)')
        return 0
    print('=== PICKINGS por quant (cross-ref reverso agrupado) ===')
    for p in res['pickings']:
        print(f'\n  pkg_id={p["id"]:7d} {p["name"]:25s} state={p["state"]:8s} emp={p["empresa"]}')
        print(f'    type={p["picking_type_name"][:40]:40s} origin={p["origin"][:30]:30s} partner={p["partner_name"][:30]:30s}')
        print(f'    scheduled={p["scheduled_date"][:19]:19s} created={p["create_date"][:19]:19s}')
        print(f'    {p["n_mls"]} MLs, qty_total={p["qty_total"]:.4f}, lotes={p["lotes_envolvidos"]}, produtos={len(p["produtos_envolvidos"])}')
        for ml in p['mls'][:5]:
            print(f'      ml_id={ml["id"]:7d} quant_id={ml["quant_id"] or 0:7d} '
                  f'lot={ml["lot_name"][:20]:20s} qty={ml["quantity"]:.4f} '
                  f'{ml["product_name"]:30s} (state={ml["state"]})')
        if len(p['mls']) > 5:
            print(f'      ... ({len(p["mls"]) - 5} MLs nao exibidas)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
