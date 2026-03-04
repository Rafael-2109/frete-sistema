"""
GAP-10: Alterar UNIQUE(tipo_doc, doc_id) para partial unique index.

Exclui tipo_doc IN ('ajuste', 'saldo_inicial') para permitir multiplos
ajustes e saldo_inicial sem violar a constraint.

Idempotente: verifica existencia antes de criar/remover.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def run():
    from app import create_app, db

    app = create_app()
    with app.app_context():
        # 1. Verificar se constraint antiga existe
        result = db.session.execute(db.text("""
            SELECT COUNT(*) FROM pg_constraint
            WHERE conname = 'uq_carvia_mov_tipo_doc'
        """))
        tem_constraint_antiga = (result.scalar() or 0) > 0

        # 2. Verificar se indice parcial novo ja existe
        result = db.session.execute(db.text("""
            SELECT COUNT(*) FROM pg_indexes
            WHERE indexname = 'uq_carvia_mov_tipo_doc_parcial'
        """))
        tem_indice_novo = (result.scalar() or 0) > 0

        if tem_indice_novo and not tem_constraint_antiga:
            print("[OK] Indice parcial ja existe e constraint antiga ja removida. Nada a fazer.")
            return

        # 3. Remover constraint antiga
        if tem_constraint_antiga:
            print("[ANTES] Removendo UNIQUE constraint antiga 'uq_carvia_mov_tipo_doc'...")
            db.session.execute(db.text(
                "ALTER TABLE carvia_conta_movimentacoes DROP CONSTRAINT uq_carvia_mov_tipo_doc"
            ))
            print("[OK] Constraint removida.")

        # 4. Criar indice parcial novo
        if not tem_indice_novo:
            print("[ANTES] Criando partial unique index 'uq_carvia_mov_tipo_doc_parcial'...")
            db.session.execute(db.text("""
                CREATE UNIQUE INDEX uq_carvia_mov_tipo_doc_parcial
                ON carvia_conta_movimentacoes (tipo_doc, doc_id)
                WHERE tipo_doc NOT IN ('ajuste', 'saldo_inicial')
            """))
            print("[OK] Partial unique index criado.")

        db.session.commit()
        print("[CONCLUIDO] GAP-10 aplicado com sucesso.")


if __name__ == '__main__':
    run()
