"""
Script para criar tabela historico_pedido_compras
SNAPSHOT COMPLETO: Mesmos campos da pedido_compras
Para ambiente de DESENVOLVIMENTO local

Uso:
    python scripts/criar_tabela_historico_pedidos_compras.py
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def verificar_tabela_existe():
    """Verifica se a tabela já existe"""
    try:
        resultado = db.session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'historico_pedido_compras'
            );
        """))
        existe = resultado.scalar()
        return existe
    except Exception as e:
        print(f"❌ Erro ao verificar tabela: {e}")
        return False


def criar_tabela_historico():
    """Cria a tabela historico_pedido_compras com snapshot completo"""
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🔄 CRIANDO TABELA historico_pedido_compras (SNAPSHOT COMPLETO)")
            print("=" * 80)

            # Verificar se já existe
            if verificar_tabela_existe():
                print("⚠️  Tabela historico_pedido_compras JÁ EXISTE")
                print("    A tabela será REMOVIDA e RECRIADA com a nova estrutura")
                resposta = input("    Confirma? (s/N): ").strip().lower()

                if resposta != 's':
                    print("❌ Operação cancelada")
                    return

                print("\n🗑️  Removendo tabela existente (CASCADE)...")
                db.session.execute(text("DROP TABLE IF EXISTS historico_pedido_compras CASCADE;"))
                db.session.commit()
                print("✅ Tabela antiga removida")

            # Criar tabela com snapshot completo
            print("\n📋 Criando tabela com TODOS os campos da pedido_compras...")

            sql_create = """
            CREATE TABLE historico_pedido_compras (
                id SERIAL PRIMARY KEY,

                -- ================================================
                -- CAMPOS DE CONTROLE DO HISTÓRICO
                -- ================================================
                pedido_compra_id INTEGER NOT NULL REFERENCES pedido_compras(id) ON DELETE CASCADE,
                operacao VARCHAR(20) NOT NULL,
                alterado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                alterado_por VARCHAR(100) NOT NULL,
                write_date_odoo TIMESTAMP,

                -- ================================================
                -- SNAPSHOT COMPLETO - MESMOS CAMPOS DO PEDIDOCOMPRAS
                -- ================================================

                -- Campos principais
                num_pedido VARCHAR(30) NOT NULL,
                num_requisicao VARCHAR(30),
                cnpj_fornecedor VARCHAR(20),
                raz_social VARCHAR(255),
                numero_nf VARCHAR(20),

                -- Datas
                data_pedido_criacao DATE,
                usuario_pedido_criacao VARCHAR(100),
                lead_time_pedido INTEGER,
                lead_time_previsto INTEGER,
                data_pedido_previsao DATE,
                data_pedido_entrega DATE,

                -- Produto
                cod_produto VARCHAR(50) NOT NULL,
                nome_produto VARCHAR(255),

                -- Quantidades e valores
                qtd_produto_pedido NUMERIC(15, 3) NOT NULL,
                qtd_recebida NUMERIC(15, 3) DEFAULT 0,
                preco_produto_pedido NUMERIC(15, 4),
                icms_produto_pedido NUMERIC(15, 2),
                pis_produto_pedido NUMERIC(15, 2),
                cofins_produto_pedido NUMERIC(15, 2),

                -- Confirmação
                confirmacao_pedido BOOLEAN DEFAULT FALSE,
                confirmado_por VARCHAR(100),
                confirmado_em TIMESTAMP,

                -- Status e tipo
                status_odoo VARCHAR(20),
                tipo_pedido VARCHAR(50),

                -- Vínculo com Odoo
                importado_odoo BOOLEAN DEFAULT FALSE,
                odoo_id VARCHAR(50),

                -- Datas originais
                criado_em TIMESTAMP,
                atualizado_em TIMESTAMP
            );
            """

            db.session.execute(text(sql_create))
            db.session.commit()
            print("✅ Tabela criada com sucesso!")

            # Criar índices
            print("\n📊 Criando índices...")

            indices = [
                "CREATE INDEX idx_hist_ped_pedido ON historico_pedido_compras(pedido_compra_id);",
                "CREATE INDEX idx_hist_ped_pedido_data ON historico_pedido_compras(pedido_compra_id, alterado_em DESC);",
                "CREATE INDEX idx_hist_ped_num_data ON historico_pedido_compras(num_pedido, alterado_em DESC);",
                "CREATE INDEX idx_hist_ped_produto ON historico_pedido_compras(cod_produto);",
                "CREATE INDEX idx_hist_ped_operacao ON historico_pedido_compras(operacao);",
                "CREATE INDEX idx_hist_ped_alterado_por ON historico_pedido_compras(alterado_por);",
            ]

            for i, sql_index in enumerate(indices, 1):
                db.session.execute(text(sql_index))
                print(f"   ✅ Índice {i}/{len(indices)} criado")

            db.session.commit()
            print("✅ Todos os índices criados com sucesso!")

            # Verificar criação
            print("\n🔍 Verificando estrutura...")

            resultado = db.session.execute(text("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = 'historico_pedido_compras'
                ORDER BY ordinal_position;
            """))

            colunas = resultado.fetchall()
            print(f"\n📋 Colunas criadas ({len(colunas)}):")

            # Separar por seção
            controle_campos = ['id', 'pedido_compra_id', 'operacao', 'alterado_em', 'alterado_por', 'write_date_odoo']

            print("\n   🔹 Campos de Controle:")
            for col in colunas:
                if col[0] in controle_campos:
                    nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                    print(f"      - {col[0]}: {col[1]} {nullable}")

            print("\n   🔹 Snapshot Completo (mesmos da pedido_compras):")
            for col in colunas:
                if col[0] not in controle_campos:
                    nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                    print(f"      - {col[0]}: {col[1]} {nullable}")

            # Verificar índices
            resultado = db.session.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'historico_pedido_compras'
                ORDER BY indexname;
            """))

            indices = resultado.fetchall()
            print(f"\n📊 Índices criados ({len(indices)}):")
            for idx in indices:
                print(f"   - {idx[0]}")

            print("\n" + "=" * 80)
            print("✅ TABELA historico_pedido_compras CRIADA COM SNAPSHOT COMPLETO!")
            print("=" * 80)
            print("\n💡 Agora a tabela grava TODOS os campos do pedido de compras")
            print("   Você pode comparar qualquer campo entre versões no modal!")
            print("\n📝 Próximos passos:")
            print("   1. Execute a sincronização de pedidos de compras")
            print("   2. Cada snapshot conterá TODOS os 27 campos")
            print("   3. Compare versões facilmente no modal\n")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO ao criar tabela: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    criar_tabela_historico()
