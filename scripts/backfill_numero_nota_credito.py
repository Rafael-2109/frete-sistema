"""
Backfill: Preencher numero_nota_credito em nf_devolucao
=======================================================
Para todas as NFDs que tem odoo_nota_credito_id mas nao tem numero_nota_credito,
busca o numero no Odoo e atualiza.

Uso:
    source .venv/bin/activate
    python scripts/backfill_numero_nota_credito.py [--dry-run]
"""
import sys
import os
import argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.devolucao.models import NFDevolucao
from app.odoo.utils.connection import get_odoo_connection

def backfill(dry_run=False):
    app = create_app()
    with app.app_context():
        # Buscar NFDs com odoo_nota_credito_id mas sem numero_nota_credito
        nfds = NFDevolucao.query.filter(
            NFDevolucao.odoo_nota_credito_id.isnot(None),
            db.or_(
                NFDevolucao.numero_nota_credito.is_(None),
                NFDevolucao.numero_nota_credito == ''
            )
        ).all()

        if not nfds:
            print("Nenhuma NFD para atualizar.")
            return

        print(f"Encontradas {len(nfds)} NFDs para backfill.")

        odoo = get_odoo_connection()

        # Coletar IDs para batch query
        nc_ids = [nfd.odoo_nota_credito_id for nfd in nfds]

        # Batch query no Odoo
        notas_credito = odoo.execute_kw(
            'account.move',
            'search_read',
            [[('id', 'in', nc_ids)]],
            {'fields': ['id', 'l10n_br_numero_nota_fiscal']}
        )

        nc_map = {nc['id']: nc.get('l10n_br_numero_nota_fiscal') for nc in notas_credito}

        atualizadas = 0
        for nfd in nfds:
            numero = nc_map.get(nfd.odoo_nota_credito_id)
            if numero:
                if dry_run:
                    print(f"  [DRY-RUN] NFD {nfd.id} (NC ID {nfd.odoo_nota_credito_id}): {numero}")
                else:
                    nfd.numero_nota_credito = str(numero)
                    atualizadas += 1
                    print(f"  Atualizada NFD {nfd.id}: NC {numero}")
            else:
                print(f"  NC ID {nfd.odoo_nota_credito_id} nao tem numero no Odoo")

        if not dry_run and atualizadas > 0:
            db.session.commit()
            print(f"\n{atualizadas} NFDs atualizadas com sucesso!")
        elif dry_run:
            print(f"\n[DRY-RUN] {len(nfds)} NFDs seriam atualizadas.")
        else:
            print("\nNenhuma atualizacao necessaria.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backfill numero_nota_credito')
    parser.add_argument('--dry-run', action='store_true', help='Simula sem alterar dados')
    args = parser.parse_args()
    backfill(dry_run=args.dry_run)
