"""
GAP-08: Adicionar ON DELETE CASCADE na FK nf_id da junction carvia_operacao_nfs.

Ao deletar uma NF (carvia_nfs), as junctions N:N sao removidas automaticamente
pelo banco, alinhando com o comportamento esperado do ORM (delete-orphan).

Idempotente: verifica constraint existente antes de alterar.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def run():
    from app import create_app, db

    app = create_app()
    with app.app_context():
        # Descobrir nome da FK atual em nf_id
        result = db.session.execute(db.text("""
            SELECT conname FROM pg_constraint
            WHERE conrelid = 'carvia_operacao_nfs'::regclass
              AND confrelid = 'carvia_nfs'::regclass
              AND contype = 'f'
        """))
        row = result.fetchone()

        if not row:
            print("[AVISO] FK de nf_id nao encontrada em carvia_operacao_nfs. Nada a fazer.")
            return

        fk_name = row[0]

        # Verificar se ja tem ON DELETE CASCADE
        result = db.session.execute(db.text("""
            SELECT confdeltype FROM pg_constraint
            WHERE conname = :fk_name
        """), {'fk_name': fk_name})
        del_type = result.scalar()

        if del_type == 'c':
            print(f"[OK] FK '{fk_name}' ja tem ON DELETE CASCADE. Nada a fazer.")
            return

        print(f"[ANTES] FK '{fk_name}' tem confdeltype='{del_type}' (esperado: 'c' CASCADE)")
        print(f"[ALTERANDO] Removendo FK antiga '{fk_name}'...")
        db.session.execute(db.text(
            f"ALTER TABLE carvia_operacao_nfs DROP CONSTRAINT {fk_name}"
        ))

        print("[ALTERANDO] Criando FK com ON DELETE CASCADE...")
        db.session.execute(db.text("""
            ALTER TABLE carvia_operacao_nfs
            ADD CONSTRAINT carvia_operacao_nfs_nf_id_fkey
            FOREIGN KEY (nf_id) REFERENCES carvia_nfs(id) ON DELETE CASCADE
        """))

        db.session.commit()
        print("[OK] FK nf_id agora tem ON DELETE CASCADE.")


if __name__ == '__main__':
    run()
