"""
Migration: Alterar UNIQUE de pessoal_categorias.
DE: nome (sozinho) → PARA: (grupo, nome) composto.

Permite mesmo nome em grupos diferentes.
Ex: "Salario" em "Receitas" e "Salario" em "Funcionarios".
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def migrate():
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        # Verificar estado antes
        result = conn.execute(db.text("""
            SELECT conname, contype
            FROM pg_constraint
            WHERE conrelid = 'pessoal_categorias'::regclass
            AND contype = 'u'
        """))
        constraints_before = result.fetchall()
        print('Constraints UNIQUE antes:')
        for c in constraints_before:
            print(f'  {c[0]} (type={c[1]})')

        # Verificar se já tem o composto
        has_composite = any(c[0] == 'uq_pessoal_categorias_grupo_nome' for c in constraints_before)
        if has_composite:
            print('\n✅ Constraint composto já existe. Nada a fazer.')
            conn.close()
            return

        # Remover constraint antiga (nome sozinho)
        try:
            conn.execute(db.text(
                'ALTER TABLE pessoal_categorias DROP CONSTRAINT IF EXISTS pessoal_categorias_nome_key'
            ))
            conn.execute(db.text(
                'DROP INDEX IF EXISTS pessoal_categorias_nome_key'
            ))
            print('\n✅ Constraint antigo (nome sozinho) removido.')
        except Exception as e:
            print(f'\n⚠️ Erro ao remover constraint antigo: {e}')

        # Criar novo unique composto
        try:
            conn.execute(db.text(
                'ALTER TABLE pessoal_categorias '
                'ADD CONSTRAINT uq_pessoal_categorias_grupo_nome UNIQUE (grupo, nome)'
            ))
            conn.commit()
            print('✅ Constraint composto (grupo, nome) criado.')
        except Exception as e:
            print(f'❌ Erro ao criar constraint composto: {e}')
            conn.rollback()
            conn.close()
            return

        # Verificar estado depois
        result = conn.execute(db.text("""
            SELECT conname, contype
            FROM pg_constraint
            WHERE conrelid = 'pessoal_categorias'::regclass
            AND contype = 'u'
        """))
        constraints_after = result.fetchall()
        print('\nConstraints UNIQUE depois:')
        for c in constraints_after:
            print(f'  {c[0]} (type={c[1]})')

        conn.close()
        print('\n✅ Migration concluída com sucesso.')


if __name__ == '__main__':
    migrate()
