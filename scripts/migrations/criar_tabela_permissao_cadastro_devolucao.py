"""
Migration: Criar tabela permissao_cadastro_devolucao
====================================================
Controle granular de permissoes para CRUD de Categorias/Subcategorias/
Responsaveis/Origens do modulo de devolucoes.

Uso:
    source .venv/bin/activate
    python scripts/migrations/criar_tabela_permissao_cadastro_devolucao.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text

def run_migration():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # Verificar se tabela ja existe
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name = 'permissao_cadastro_devolucao'
            """))
            if result.fetchone():
                print("Tabela permissao_cadastro_devolucao ja existe. Nada a fazer.")
                return

            conn.execute(text("""
                CREATE TABLE permissao_cadastro_devolucao (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
                    tipo_cadastro VARCHAR(30) NOT NULL,
                    pode_criar BOOLEAN DEFAULT FALSE,
                    pode_editar BOOLEAN DEFAULT FALSE,
                    pode_excluir BOOLEAN DEFAULT FALSE,
                    concedido_por VARCHAR(100),
                    concedido_em TIMESTAMP DEFAULT NOW(),
                    ativo BOOLEAN DEFAULT TRUE,
                    CONSTRAINT uq_perm_cad_dev_usuario_tipo UNIQUE (usuario_id, tipo_cadastro)
                )
            """))
            print("Tabela permissao_cadastro_devolucao criada.")

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_perm_cad_dev_usuario
                ON permissao_cadastro_devolucao(usuario_id)
            """))
            print("Indice idx_perm_cad_dev_usuario criado.")

            conn.commit()
            print("Migration concluida com sucesso!")

if __name__ == '__main__':
    run_migration()
