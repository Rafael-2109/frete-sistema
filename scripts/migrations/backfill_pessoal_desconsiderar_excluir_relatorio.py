"""Backfill: transacoes categorizadas como grupo 'Desconsiderar' devem ter
excluir_relatorio=True para sair dos calculos/dashboard.

Data fix (nao altera DDL) — roda 1x.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def main():
    app = create_app()
    with app.app_context():
        # Before
        before = db.session.execute(text("""
            SELECT COUNT(*) FROM pessoal_transacoes t
            JOIN pessoal_categorias c ON c.id = t.categoria_id
            WHERE c.grupo = 'Desconsiderar' AND t.excluir_relatorio = FALSE
        """)).scalar()
        print(f'Transacoes a corrigir (Desconsiderar com excluir_relatorio=FALSE): {before}')

        if before == 0:
            print('Nada a fazer.')
            return

        # Update
        result = db.session.execute(text("""
            UPDATE pessoal_transacoes
            SET excluir_relatorio = TRUE
            WHERE excluir_relatorio = FALSE
              AND categoria_id IN (
                SELECT id FROM pessoal_categorias WHERE grupo = 'Desconsiderar'
              )
        """))
        db.session.commit()
        print(f'Transacoes atualizadas: {result.rowcount}')

        # After
        after = db.session.execute(text("""
            SELECT COUNT(*) FROM pessoal_transacoes t
            JOIN pessoal_categorias c ON c.id = t.categoria_id
            WHERE c.grupo = 'Desconsiderar' AND t.excluir_relatorio = FALSE
        """)).scalar()
        print(f'Pendentes apos update: {after}')
        assert after == 0, f'Ainda restam {after} transacoes sem excluir_relatorio!'
        print('OK.')


if __name__ == '__main__':
    main()
