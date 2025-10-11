"""
Migration: Adiciona sistema de confirmação de pedidos
- Adiciona campo 'status' em PedidoVendaMoto
- Cria tabela PedidoVendaAuditoria

Data: 2025-01-11
Autor: Claude AI
Contexto: Sistema de aprovação em duas etapas para inserção e cancelamento de pedidos

IMPORTANTE: Executar LOCALMENTE primeiro para testar
"""

import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text, inspect

def adicionar_campo_status():
    """Adiciona campo 'status' na tabela pedido_venda_moto"""
    app = create_app()

    with app.app_context():
        try:
            # Verificar se campo já existe
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('pedido_venda_moto')]

            if 'status' in columns:
                print("✅ Campo 'status' já existe em pedido_venda_moto")
                return

            print("🔧 Adicionando campo 'status' em pedido_venda_moto...")

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE pedido_venda_moto
                ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'APROVADO';
            """))

            # Criar índice
            db.session.execute(text("""
                CREATE INDEX idx_pedido_status ON pedido_venda_moto(status);
            """))

            db.session.commit()

            print("✅ Campo 'status' adicionado com sucesso!")
            print("✅ Índice idx_pedido_status criado com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao adicionar campo 'status': {e}")
            raise


def criar_tabela_auditoria():
    """Cria tabela pedido_venda_auditoria"""
    app = create_app()

    with app.app_context():
        try:
            # Verificar se tabela já existe
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            if 'pedido_venda_auditoria' in tables:
                print("✅ Tabela 'pedido_venda_auditoria' já existe")
                return

            print("🔧 Criando tabela 'pedido_venda_auditoria'...")

            # Criar tabela
            db.session.execute(text("""
                CREATE TABLE pedido_venda_auditoria (
                    id SERIAL PRIMARY KEY,
                    pedido_id INTEGER NOT NULL REFERENCES pedido_venda_moto(id),
                    acao VARCHAR(20) NOT NULL,
                    observacao TEXT,
                    solicitado_por VARCHAR(100) NOT NULL,
                    solicitado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    confirmado BOOLEAN NOT NULL DEFAULT FALSE,
                    rejeitado BOOLEAN NOT NULL DEFAULT FALSE,
                    motivo_rejeicao TEXT,
                    confirmado_por VARCHAR(100),
                    confirmado_em TIMESTAMP
                );
            """))

            # Criar índices
            db.session.execute(text("""
                CREATE INDEX idx_auditoria_pedido ON pedido_venda_auditoria(pedido_id);
            """))

            db.session.execute(text("""
                CREATE INDEX idx_auditoria_acao ON pedido_venda_auditoria(acao);
            """))

            db.session.execute(text("""
                CREATE INDEX idx_auditoria_confirmado ON pedido_venda_auditoria(confirmado);
            """))

            db.session.execute(text("""
                CREATE INDEX idx_auditoria_rejeitado ON pedido_venda_auditoria(rejeitado);
            """))

            db.session.execute(text("""
                CREATE INDEX idx_auditoria_pendente ON pedido_venda_auditoria(confirmado, rejeitado);
            """))

            db.session.execute(text("""
                CREATE INDEX idx_auditoria_acao_status ON pedido_venda_auditoria(acao, confirmado, rejeitado);
            """))

            db.session.commit()

            print("✅ Tabela 'pedido_venda_auditoria' criada com sucesso!")
            print("✅ Todos os índices criados com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao criar tabela de auditoria: {e}")
            raise


def executar_migration():
    """Executa migration completa"""
    print("=" * 60)
    print("MIGRATION: Sistema de Confirmação de Pedidos")
    print("=" * 60)
    print()

    # Passo 1: Adicionar campo status
    print("PASSO 1: Adicionar campo 'status' em PedidoVendaMoto")
    print("-" * 60)
    adicionar_campo_status()
    print()

    # Passo 2: Criar tabela de auditoria
    print("PASSO 2: Criar tabela PedidoVendaAuditoria")
    print("-" * 60)
    criar_tabela_auditoria()
    print()

    print("=" * 60)
    print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
    print("=" * 60)
    print()
    print("📋 PRÓXIMOS PASSOS:")
    print("1. Testar criação de novo pedido (deve ficar PENDENTE)")
    print("2. Testar cancelamento de pedido existente")
    print("3. Testar tela de Confirmação de Pedidos")
    print("4. Se tudo OK, executar script SQL no Render")
    print()


if __name__ == '__main__':
    executar_migration()
