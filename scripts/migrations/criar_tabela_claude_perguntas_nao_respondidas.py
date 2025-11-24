"""
Script de migração para criar tabela claude_perguntas_nao_respondidas.

Uso:
    python scripts/migrations/criar_tabela_claude_perguntas_nao_respondidas.py

Criado em: 23/11/2025
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabela():
    """Cria a tabela claude_perguntas_nao_respondidas."""
    app = create_app()

    with app.app_context():
        try:
            # Verifica se tabela já existe
            resultado = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'claude_perguntas_nao_respondidas'
                );
            """))
            existe = resultado.scalar()

            if existe:
                print("✓ Tabela claude_perguntas_nao_respondidas já existe.")
                return True

            # Cria a tabela
            db.session.execute(text("""
                CREATE TABLE claude_perguntas_nao_respondidas (
                    id SERIAL PRIMARY KEY,

                    -- Vínculo com usuário
                    usuario_id INTEGER REFERENCES usuarios(id),

                    -- Pergunta original
                    consulta TEXT NOT NULL,

                    -- Classificação detectada
                    intencao_detectada VARCHAR(50),
                    dominio_detectado VARCHAR(50),
                    confianca FLOAT,

                    -- Entidades extraídas (JSON)
                    entidades JSONB,

                    -- Motivo da falha
                    motivo_falha VARCHAR(100) NOT NULL,

                    -- Análise da complexidade
                    tipo_pergunta VARCHAR(20) DEFAULT 'simples',
                    dimensoes_detectadas JSONB,

                    -- Sugestão oferecida ao usuário
                    sugestao_gerada TEXT,

                    -- Status de tratamento
                    status VARCHAR(20) DEFAULT 'pendente',

                    -- Notas de análise
                    notas_analise TEXT,
                    capacidade_sugerida VARCHAR(100),

                    -- Timestamps
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    analisado_em TIMESTAMP,
                    analisado_por VARCHAR(100)
                );
            """))

            # Cria índices
            db.session.execute(text("""
                CREATE INDEX idx_claude_nao_resp_usuario
                ON claude_perguntas_nao_respondidas(usuario_id);
            """))

            db.session.execute(text("""
                CREATE INDEX idx_claude_nao_resp_motivo_data
                ON claude_perguntas_nao_respondidas(motivo_falha, criado_em);
            """))

            db.session.execute(text("""
                CREATE INDEX idx_claude_nao_resp_status
                ON claude_perguntas_nao_respondidas(status, criado_em);
            """))

            db.session.execute(text("""
                CREATE INDEX idx_claude_nao_resp_tipo
                ON claude_perguntas_nao_respondidas(tipo_pergunta);
            """))

            db.session.execute(text("""
                CREATE INDEX idx_claude_nao_resp_criado
                ON claude_perguntas_nao_respondidas(criado_em);
            """))

            db.session.commit()
            print("✓ Tabela claude_perguntas_nao_respondidas criada com sucesso!")
            print("✓ Índices criados com sucesso!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"✗ Erro ao criar tabela: {e}")
            return False


def verificar_estrutura():
    """Verifica a estrutura da tabela criada."""
    app = create_app()

    with app.app_context():
        try:
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'claude_perguntas_nao_respondidas'
                ORDER BY ordinal_position;
            """))

            colunas = resultado.fetchall()

            if colunas:
                print("\nEstrutura da tabela:")
                print("-" * 50)
                for col in colunas:
                    nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                    print(f"  {col[0]}: {col[1]} {nullable}")
                print("-" * 50)
            else:
                print("Tabela não encontrada.")

        except Exception as e:
            print(f"Erro ao verificar estrutura: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Migração: Criar tabela claude_perguntas_nao_respondidas")
    print("=" * 60)

    sucesso = criar_tabela()

    if sucesso:
        verificar_estrutura()

    print("\nMigração finalizada.")
