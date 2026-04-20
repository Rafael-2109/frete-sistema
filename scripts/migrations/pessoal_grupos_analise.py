"""
Migration: Grupos de Analise customizados (selecao de categorias).

Cria duas tabelas:
- pessoal_grupos_analise: grupo nomeado salvo pelo usuario.
- pessoal_grupos_analise_categorias: ligacao N:N com pessoal_categorias.

Executar: python scripts/migrations/pessoal_grupos_analise.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text, inspect


def migrar():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        tabelas = inspector.get_table_names()

        print("=" * 60)
        print("MIGRATION: PESSOAL GRUPOS ANALISE")
        print("=" * 60)

        tem_grupo = 'pessoal_grupos_analise' in tabelas
        tem_ligacao = 'pessoal_grupos_analise_categorias' in tabelas

        print(f"\n[BEFORE] pessoal_grupos_analise existe: {tem_grupo}")
        print(f"[BEFORE] pessoal_grupos_analise_categorias existe: {tem_ligacao}")

        # 1. Tabela principal
        if not tem_grupo:
            print("\n[1/2] Criando pessoal_grupos_analise...")
            db.session.execute(text("""
                CREATE TABLE pessoal_grupos_analise (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(100) NOT NULL UNIQUE,
                    descricao VARCHAR(300),
                    cor VARCHAR(20),
                    criado_em TIMESTAMP DEFAULT NOW(),
                    atualizado_em TIMESTAMP DEFAULT NOW()
                );
            """))
            print("   OK")
        else:
            print("\n[1/2] pessoal_grupos_analise ja existe — pulando.")

        # 2. Tabela de ligacao N:N
        if not tem_ligacao:
            print("\n[2/2] Criando pessoal_grupos_analise_categorias...")
            db.session.execute(text("""
                CREATE TABLE pessoal_grupos_analise_categorias (
                    grupo_id INTEGER NOT NULL
                        REFERENCES pessoal_grupos_analise(id) ON DELETE CASCADE,
                    categoria_id INTEGER NOT NULL
                        REFERENCES pessoal_categorias(id) ON DELETE CASCADE,
                    PRIMARY KEY (grupo_id, categoria_id)
                );
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_pessoal_gac_categoria
                    ON pessoal_grupos_analise_categorias (categoria_id);
            """))
            print("   OK")
        else:
            print("\n[2/2] pessoal_grupos_analise_categorias ja existe — pulando.")

        db.session.commit()

        # AFTER
        inspector = inspect(db.engine)
        tabelas_pos = inspector.get_table_names()
        print("\n" + "=" * 60)
        print("[AFTER] pessoal_grupos_analise existe:",
              'pessoal_grupos_analise' in tabelas_pos)
        print("[AFTER] pessoal_grupos_analise_categorias existe:",
              'pessoal_grupos_analise_categorias' in tabelas_pos)
        print("=" * 60)
        print("\nMigration concluida!")


if __name__ == '__main__':
    migrar()
