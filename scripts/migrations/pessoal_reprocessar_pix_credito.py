"""Reprocessamento historico — "Pix no Credito" do Nubank (Caso 1).

Casa os trios ja importados (funding + pix-saida + compra cartao) e aplica:
- funding -> excluido
- compra do cartao -> split principal (excluido) + linha de juros (Juros & Multa)

detectar_e_processar() e idempotente (so toca pernas ainda nao vinculadas), entao pode
rodar quantas vezes precisar. Use --dry-run (default) para ver o impacto sem gravar.

Executar (apos deploy do codigo):
    python scripts/migrations/pessoal_reprocessar_pix_credito.py --dry-run   # preview
    python scripts/migrations/pessoal_reprocessar_pix_credito.py --apply     # grava
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.pessoal.services.pix_credito_service import detectar_e_processar


def main(apply: bool):
    app = create_app()
    with app.app_context():
        res = detectar_e_processar(commit=apply)
        print("=== Reprocessamento Pix no Credito ===")
        print(f"  Trios processados : {res['trios_processados']}")
        print(f"  Splits (com cartao): {res['splits']}")
        print(f"  Parciais (sem cartao importado): {res['parciais']}")
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
