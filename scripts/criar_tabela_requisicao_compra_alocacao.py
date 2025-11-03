"""
Script para criar tabela requisicao_compra_alocacao
===================================================

Tabela intermediária N:N entre RequisicaoCompras e PedidoCompras
Mapeia purchase.request.allocation do Odoo

Autor: Sistema de Fretes
Data: 01/11/2025
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def criar_tabela_requisicao_compra_alocacao():
    """Cria a tabela requisicao_compra_alocacao no banco de dados"""

    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🔧 CRIANDO TABELA: requisicao_compra_alocacao")
            print("=" * 80)
            print()

            # Verificar se tabela já existe
            resultado = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'requisicao_compra_alocacao'
                );
            """))

            existe = resultado.scalar()

            if existe:
                print("⚠️  Tabela 'requisicao_compra_alocacao' JÁ EXISTE!")
                print()
                resposta = input("   Deseja DROPAR e RECRIAR? (s/N): ").strip().lower()

                if resposta == 's':
                    print()
                    print("🗑️  Dropando tabela existente...")
                    db.session.execute(text("DROP TABLE IF EXISTS requisicao_compra_alocacao CASCADE;"))
                    db.session.commit()
                    print("   ✅ Tabela dropada")
                else:
                    print()
                    print("❌ Operação cancelada pelo usuário")
                    return

            print()
            print("📋 Criando tabela requisicao_compra_alocacao...")
            print()

            # SQL de criação da tabela
            sql_create = text("""
                CREATE TABLE requisicao_compra_alocacao (
                    -- PK
                    id SERIAL PRIMARY KEY,

                    -- FKs para relacionamentos
                    requisicao_compra_id INTEGER NOT NULL,
                    pedido_compra_id INTEGER,

                    -- IDs do Odoo
                    odoo_allocation_id VARCHAR(50) UNIQUE,
                    purchase_request_line_odoo_id VARCHAR(50) NOT NULL,
                    purchase_order_line_odoo_id VARCHAR(50),

                    -- Produto (desnormalizado para queries rápidas)
                    cod_produto VARCHAR(50) NOT NULL,
                    nome_produto VARCHAR(255),

                    -- Quantidades
                    qtd_alocada NUMERIC(15, 3) NOT NULL,
                    qtd_requisitada NUMERIC(15, 3) NOT NULL,
                    qtd_aberta NUMERIC(15, 3) DEFAULT 0,

                    -- Status
                    purchase_state VARCHAR(20),
                    stock_move_odoo_id VARCHAR(50),

                    -- Controle
                    importado_odoo BOOLEAN DEFAULT TRUE,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    -- Datas Odoo
                    create_date_odoo TIMESTAMP,
                    write_date_odoo TIMESTAMP,

                    -- FK Constraints
                    CONSTRAINT fk_requisicao_compra
                        FOREIGN KEY (requisicao_compra_id)
                        REFERENCES requisicao_compras(id)
                        ON DELETE CASCADE,

                    CONSTRAINT fk_pedido_compra
                        FOREIGN KEY (pedido_compra_id)
                        REFERENCES pedido_compras(id)
                        ON DELETE SET NULL,

                    -- Unique Constraints
                    CONSTRAINT uq_allocation_request_order
                        UNIQUE (purchase_request_line_odoo_id, purchase_order_line_odoo_id)
                );
            """)

            db.session.execute(sql_create)
            db.session.commit()
            print("   ✅ Tabela criada")

            print()
            print("📊 Criando índices...")
            print()

            # Índices
            indices = [
                ("idx_alocacao_requisicao_compra_id", "requisicao_compra_id"),
                ("idx_alocacao_pedido_compra_id", "pedido_compra_id"),
                ("idx_alocacao_odoo_allocation_id", "odoo_allocation_id"),
                ("idx_alocacao_purchase_request_line", "purchase_request_line_odoo_id"),
                ("idx_alocacao_purchase_order_line", "purchase_order_line_odoo_id"),
                ("idx_alocacao_cod_produto", "cod_produto"),
                ("idx_alocacao_requisicao_pedido", "requisicao_compra_id, pedido_compra_id"),
                ("idx_alocacao_produto_estado", "cod_produto, purchase_state"),
                ("idx_alocacao_odoo_ids", "purchase_request_line_odoo_id, purchase_order_line_odoo_id"),
            ]

            for nome_indice, campos in indices:
                sql_index = text(f"""
                    CREATE INDEX {nome_indice}
                    ON requisicao_compra_alocacao ({campos});
                """)
                db.session.execute(sql_index)
                print(f"   ✅ Índice criado: {nome_indice}")

            db.session.commit()

            print()
            print("📊 Verificando estrutura criada...")
            print()

            # Verificar colunas
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'requisicao_compra_alocacao'
                ORDER BY ordinal_position;
            """))

            colunas = resultado.fetchall()
            print(f"   ✅ Total de colunas: {len(colunas)}")
            print()
            print("   Colunas criadas:")
            for col in colunas:
                nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col[3]}" if col[3] else ""
                print(f"      - {col[0]:<35} {col[1]:<20} {nullable}{default}")

            print()
            print("=" * 80)
            print("✅ TABELA CRIADA COM SUCESSO!")
            print("=" * 80)
            print()
            print("📝 Próximos passos:")
            print("   1. Executar script SQL no Render (ver arquivo .sql)")
            print("   2. Implementar serviço de importação do Odoo")
            print("   3. Testar relacionamentos")
            print()

        except Exception as e:
            db.session.rollback()
            print()
            print("=" * 80)
            print("❌ ERRO AO CRIAR TABELA")
            print("=" * 80)
            print(f"Erro: {e}")
            print()
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    criar_tabela_requisicao_compra_alocacao()
