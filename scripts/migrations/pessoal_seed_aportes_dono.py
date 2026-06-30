"""Seed + reprocessamento — aportes do dono (Rafael) por conta (Caso 2).

Wrapper CLI fino sobre app.pessoal.services.aportes_dono_service.

  - Deposito do dono na conta-mae Bradesco -> RECEBIMENTO (Salario, visivel)
  - Deposito do dono na NuConta Nubank      -> TRANSFERENCIA entre contas (excluido)

Executar (apos deploy + migration da coluna contas_ids):
    python scripts/migrations/pessoal_seed_aportes_dono.py --dry-run
    python scripts/migrations/pessoal_seed_aportes_dono.py --apply
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.pessoal.services.aportes_dono_service import seed_regras_dono, reprocessar_dono


def main(apply: bool):
    app = create_app()
    with app.app_context():
        seed = seed_regras_dono(commit=apply)
        print("=== Seed regras do dono (Caso 2) ===")
        print(f"  Bradesco={seed['bradesco_cc_id']} Nubank={seed['nubank_cc_id']} "
              f"Salario={seed['cat_salario_id']} Transf={seed['cat_transf_id']}")
        print(f"  Genericas desativadas: {seed['desativadas']}")
        print(f"  Regras criadas: {len(seed['criadas'])}  atualizadas: {len(seed['atualizadas'])}")
        rep = reprocessar_dono(commit=apply)
        print(f"  Entradas reprocessadas: {rep['reprocessadas']}/{rep['total']}")
        if apply:
            print("APLICADO (commit).")
        else:
            db.session.rollback()
            print("DRY-RUN (rollback) — rode com --apply para gravar.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--dry-run', action='store_true', help='Preview sem gravar (default)')
    g.add_argument('--apply', action='store_true', help='Grava as alteracoes')
    args = ap.parse_args()
    main(apply=args.apply)
