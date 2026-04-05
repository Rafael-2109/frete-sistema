"""
Migration: Adicionar tabela pessoal_orcamentos + remover coluna ordem_exibicao
Executar localmente: python scripts/migrations/pessoal_orcamento.py
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
        tabelas_existentes = inspector.get_table_names()

        print("=" * 60)
        print("MIGRATION: PESSOAL ORCAMENTO")
        print("=" * 60)

        # ============================================
        # BEFORE: verificar estado atual
        # ============================================
        tem_orcamentos = 'pessoal_orcamentos' in tabelas_existentes
        tem_ordem = False
        if 'pessoal_categorias' in tabelas_existentes:
            colunas = [c['name'] for c in inspector.get_columns('pessoal_categorias')]
            tem_ordem = 'ordem_exibicao' in colunas

        print(f"\n[BEFORE] Tabela pessoal_orcamentos existe: {tem_orcamentos}")
        print(f"[BEFORE] Coluna ordem_exibicao existe: {tem_ordem}")

        # ============================================
        # 1. Criar tabela pessoal_orcamentos
        # ============================================
        if not tem_orcamentos:
            print("\n[1/2] Criando tabela pessoal_orcamentos...")
            db.session.execute(text("""
                CREATE TABLE pessoal_orcamentos (
                    id SERIAL PRIMARY KEY,
                    ano_mes DATE NOT NULL,
                    categoria_id INTEGER REFERENCES pessoal_categorias(id),
                    valor_limite NUMERIC(15,2) NOT NULL,
                    criado_em TIMESTAMP DEFAULT NOW(),
                    atualizado_em TIMESTAMP DEFAULT NOW()
                );
            """))

            # Partial indexes para UNIQUE com NULL
            db.session.execute(text("""
                CREATE UNIQUE INDEX uq_pessoal_orcamentos_mes_categoria
                    ON pessoal_orcamentos (ano_mes, categoria_id)
                    WHERE categoria_id IS NOT NULL;
            """))
            db.session.execute(text("""
                CREATE UNIQUE INDEX uq_pessoal_orcamentos_mes_global
                    ON pessoal_orcamentos (ano_mes)
                    WHERE categoria_id IS NULL;
            """))
            print("   Tabela pessoal_orcamentos criada com sucesso!")
        else:
            print("\n[1/2] Tabela pessoal_orcamentos ja existe — pulando.")

        # ============================================
        # 2. Remover coluna ordem_exibicao
        # ============================================
        if tem_ordem:
            print("\n[2/2] Removendo coluna ordem_exibicao de pessoal_categorias...")
            db.session.execute(text("""
                ALTER TABLE pessoal_categorias DROP COLUMN ordem_exibicao;
            """))
            print("   Coluna ordem_exibicao removida com sucesso!")
        else:
            print("\n[2/2] Coluna ordem_exibicao ja removida — pulando.")

        db.session.commit()

        # ============================================
        # AFTER: verificar resultado
        # ============================================
        inspector = inspect(db.engine)
        tabelas = inspector.get_table_names()
        colunas = [c['name'] for c in inspector.get_columns('pessoal_categorias')]

        print("\n" + "=" * 60)
        print("[AFTER] Tabela pessoal_orcamentos existe:", 'pessoal_orcamentos' in tabelas)
        print("[AFTER] Coluna ordem_exibicao existe:", 'ordem_exibicao' in colunas)
        print("=" * 60)
        print("\nMigration concluida com sucesso!")


if __name__ == '__main__':
    migrar()
