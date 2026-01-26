"""
Migration: Adicionar campos de rastreabilidade Recebimento Fisico

Este script adiciona campos em movimentacao_estoque para vincular com
RecebimentoFisico e RecebimentoLote, permitindo rastrear qual processo
de recebimento gerou cada entrada de material.

Campos adicionados:
- recebimento_fisico_id: FK para recebimento_fisico.id
- recebimento_lote_id: FK para recebimento_lote.id
- lote_nome: Nome do lote (ex: LOTE-2024-001)
- data_validade: Data de validade do lote

Contexto:
- Antes: RecebimentoFisicoOdooService validava picking mas NAO criava MovimentacaoEstoque
- Depois: Apos validacao, cria MovimentacaoEstoque com rastreabilidade completa
- EntradaMaterialService continua funcionando como fallback (nao duplica por odoo_move_id)

Uso:
    python scripts/add_rastreabilidade_recebimento_fisico.py

Ou no Render Shell:
    Execute o SQL diretamente (use --sql para ver o SQL).

Data: 2026-01-26
"""
# flake8: noqa: E402
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_MIGRATION = """
-- Migration: Adicionar campos de rastreabilidade Recebimento Fisico
-- Data: 2026-01-26

-- 1. Adicionar FK para recebimento_fisico
ALTER TABLE movimentacao_estoque
    ADD COLUMN IF NOT EXISTS recebimento_fisico_id INTEGER REFERENCES recebimento_fisico(id) ON DELETE SET NULL;

-- 2. Adicionar FK para recebimento_lote
ALTER TABLE movimentacao_estoque
    ADD COLUMN IF NOT EXISTS recebimento_lote_id INTEGER REFERENCES recebimento_lote(id) ON DELETE SET NULL;

-- 3. Adicionar campo para nome do lote
ALTER TABLE movimentacao_estoque
    ADD COLUMN IF NOT EXISTS lote_nome VARCHAR(100);

-- 4. Adicionar campo para data de validade
ALTER TABLE movimentacao_estoque
    ADD COLUMN IF NOT EXISTS data_validade DATE;

-- 5. Criar indice para recebimento_fisico_id
CREATE INDEX IF NOT EXISTS idx_movimentacao_recebimento_fisico ON movimentacao_estoque(recebimento_fisico_id);

-- 6. Criar indice para recebimento_lote_id
CREATE INDEX IF NOT EXISTS idx_movimentacao_recebimento_lote ON movimentacao_estoque(recebimento_lote_id);
"""


def run_migration():
    """Executa a migration"""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 70)
            print("MIGRATION: Adicionando campos de rastreabilidade Recebimento Fisico")
            print("=" * 70)

            # Executar cada comando separadamente para melhor controle de erros
            commands = [
                ("recebimento_fisico_id", """
                    ALTER TABLE movimentacao_estoque
                    ADD COLUMN IF NOT EXISTS recebimento_fisico_id INTEGER
                    REFERENCES recebimento_fisico(id) ON DELETE SET NULL
                """),
                ("recebimento_lote_id", """
                    ALTER TABLE movimentacao_estoque
                    ADD COLUMN IF NOT EXISTS recebimento_lote_id INTEGER
                    REFERENCES recebimento_lote(id) ON DELETE SET NULL
                """),
                ("lote_nome", """
                    ALTER TABLE movimentacao_estoque
                    ADD COLUMN IF NOT EXISTS lote_nome VARCHAR(100)
                """),
                ("data_validade", """
                    ALTER TABLE movimentacao_estoque
                    ADD COLUMN IF NOT EXISTS data_validade DATE
                """),
                ("idx_recebimento_fisico", """
                    CREATE INDEX IF NOT EXISTS idx_movimentacao_recebimento_fisico
                    ON movimentacao_estoque(recebimento_fisico_id)
                """),
                ("idx_recebimento_lote", """
                    CREATE INDEX IF NOT EXISTS idx_movimentacao_recebimento_lote
                    ON movimentacao_estoque(recebimento_lote_id)
                """),
            ]

            for nome, sql in commands:
                try:
                    db.session.execute(text(sql))
                    print(f"  ✅ {nome}")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        print(f"  ⏭️  {nome} (ja existe)")
                    else:
                        print(f"  ❌ {nome}: {e}")

            db.session.commit()
            print()
            print("=" * 70)
            print("✅ Migration concluida com sucesso!")
            print("=" * 70)

            # Verificar se campos foram criados
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'movimentacao_estoque'
                AND column_name IN ('recebimento_fisico_id', 'recebimento_lote_id', 'lote_nome', 'data_validade')
            """))
            columns = [row[0] for row in result]
            print(f"\nCampos verificados: {columns}")

            if len(columns) == 4:
                print("✅ Todos os 4 campos foram criados corretamente!")
            else:
                print(f"⚠️  Apenas {len(columns)} de 4 campos encontrados")

        except Exception as e:
            print(f"❌ Erro na migration: {e}")
            db.session.rollback()
            raise


def print_sql():
    """Imprime o SQL para execução manual"""
    print("=" * 70)
    print("SQL PARA EXECUCAO MANUAL (Render Shell)")
    print("=" * 70)
    print(SQL_MIGRATION)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--sql':
        print_sql()
    else:
        run_migration()
