"""
Script de Migração: Criar Tabela lancamento_frete_odoo_auditoria
==================================================================

OBJETIVO:
    Criar tabela de auditoria para lançamentos de frete no Odoo
    Registra todas as 16 etapas do processo de lançamento

AUTOR: Sistema de Fretes
DATA: 14/11/2025

USO:
    python3 scripts/criar_tabela_auditoria_lancamento_frete.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def criar_tabela_auditoria():
    """
    Cria a tabela lancamento_frete_odoo_auditoria
    """
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🔧 CRIANDO TABELA lancamento_frete_odoo_auditoria")
            print("=" * 80)
            print()

            # Verificar se tabela já existe
            print("1️⃣ Verificando se tabela já existe...")
            resultado = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'lancamento_frete_odoo_auditoria'
                )
            """))
            tabela_existe = resultado.scalar()

            if tabela_existe:
                print("⚠️  Tabela 'lancamento_frete_odoo_auditoria' já existe!")
                resposta = input("   Deseja recriar a tabela? (s/n): ")
                if resposta.lower() != 's':
                    print("❌ Operação cancelada.")
                    return

                print("🗑️  Removendo tabela antiga...")
                db.session.execute(text("DROP TABLE IF EXISTS lancamento_frete_odoo_auditoria CASCADE"))
                db.session.commit()
                print("✅ Tabela antiga removida!")
                print()

            # Criar tabela
            print("2️⃣ Criando tabela lancamento_frete_odoo_auditoria...")

            db.session.execute(text("""
                CREATE TABLE lancamento_frete_odoo_auditoria (
                    id SERIAL PRIMARY KEY,

                    -- Identificação do lançamento
                    frete_id INTEGER REFERENCES fretes(id),
                    cte_id INTEGER REFERENCES conhecimento_transporte(id),
                    chave_cte VARCHAR(44) NOT NULL,

                    -- IDs do Odoo gerados
                    dfe_id INTEGER,
                    purchase_order_id INTEGER,
                    invoice_id INTEGER,

                    -- Etapa do processo (1-16)
                    etapa INTEGER NOT NULL,
                    etapa_descricao VARCHAR(255) NOT NULL,

                    -- Modelo e ação Odoo
                    modelo_odoo VARCHAR(100) NOT NULL,
                    metodo_odoo VARCHAR(100),
                    acao VARCHAR(50) NOT NULL,

                    -- Dados ANTES e DEPOIS (JSON)
                    dados_antes TEXT,
                    dados_depois TEXT,

                    -- Campos alterados
                    campos_alterados TEXT,

                    -- Status da etapa
                    status VARCHAR(20) NOT NULL DEFAULT 'SUCESSO',
                    mensagem TEXT,
                    erro_detalhado TEXT,

                    -- Contexto adicional
                    contexto_odoo TEXT,

                    -- Tempo de execução
                    tempo_execucao_ms INTEGER,

                    -- Auditoria
                    executado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                    executado_por VARCHAR(100) NOT NULL,
                    ip_usuario VARCHAR(50)
                )
            """))

            db.session.commit()
            print("✅ Tabela criada com sucesso!")
            print()

            # Criar índices
            print("3️⃣ Criando índices...")

            indices = [
                "CREATE INDEX idx_auditoria_frete_id ON lancamento_frete_odoo_auditoria(frete_id)",
                "CREATE INDEX idx_auditoria_cte_id ON lancamento_frete_odoo_auditoria(cte_id)",
                "CREATE INDEX idx_auditoria_chave_cte ON lancamento_frete_odoo_auditoria(chave_cte)",
                "CREATE INDEX idx_auditoria_etapa ON lancamento_frete_odoo_auditoria(etapa)",
                "CREATE INDEX idx_auditoria_executado_em ON lancamento_frete_odoo_auditoria(executado_em)",
                "CREATE INDEX idx_auditoria_status ON lancamento_frete_odoo_auditoria(status)",
            ]

            for idx_sql in indices:
                db.session.execute(text(idx_sql))
                print(f"   ✅ {idx_sql.split()[2]}")

            db.session.commit()
            print("✅ Índices criados com sucesso!")
            print()

            # Verificar estrutura criada
            print("4️⃣ Verificando estrutura da tabela...")
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'lancamento_frete_odoo_auditoria'
                ORDER BY ordinal_position
            """))

            colunas = resultado.fetchall()
            print(f"   Total de colunas: {len(colunas)}")
            print()
            print("   Colunas criadas:")
            for col in colunas:
                nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                print(f"      - {col[0]:<30} {col[1]:<20} {nullable}")
            print()

            print("=" * 80)
            print("✅ TABELA CRIADA COM SUCESSO!")
            print("=" * 80)
            print()
            print("📋 Informações:")
            print(f"   - Total de colunas: {len(colunas)}")
            print(f"   - Total de índices: {len(indices)}")
            print()
            print("🚀 Próximos passos:")
            print("   1. Adicionar campos odoo_purchase_order_id e odoo_invoice_id na tabela fretes")
            print("   2. Criar service de lançamento com auditoria")
            print("   3. Integrar na interface web")
            print()

        except Exception as e:
            db.session.rollback()
            print(f"❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    criar_tabela_auditoria()
