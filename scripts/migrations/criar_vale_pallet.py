"""
Migration: Cria tabela vale_pallets

A tabela vale_pallets armazena os vale pallets emitidos por clientes
que não aceitam NF de remessa de pallet.

Data: 04/01/2026
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("Migration: Criando tabela vale_pallets")
            print("=" * 60)

            # Criar tabela vale_pallets
            print("\n[1/1] Criando tabela vale_pallets...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS vale_pallets (
                    id SERIAL PRIMARY KEY,

                    -- Referência à NF de remessa/pallet
                    nf_pallet VARCHAR(20) NOT NULL,

                    -- Dados do vale
                    data_emissao DATE NOT NULL,
                    data_validade DATE NOT NULL,
                    quantidade INTEGER NOT NULL,

                    -- Cliente que emitiu o vale
                    cnpj_cliente VARCHAR(20),
                    nome_cliente VARCHAR(255),

                    -- Posse e rastreamento
                    posse_atual VARCHAR(50) DEFAULT 'TRANSPORTADORA',
                    cnpj_posse VARCHAR(20),
                    nome_posse VARCHAR(255),

                    -- Transportadora responsável
                    cnpj_transportadora VARCHAR(20),
                    nome_transportadora VARCHAR(255),

                    -- Arquivamento físico
                    pasta_arquivo VARCHAR(100),
                    aba_arquivo VARCHAR(50),

                    -- Resolução
                    tipo_resolucao VARCHAR(20) DEFAULT 'PENDENTE',
                    responsavel_resolucao VARCHAR(255),
                    cnpj_resolucao VARCHAR(20),
                    valor_resolucao NUMERIC(15, 2),
                    nf_resolucao VARCHAR(20),

                    -- Status
                    recebido BOOLEAN DEFAULT FALSE,
                    recebido_em TIMESTAMP,
                    recebido_por VARCHAR(100),

                    enviado_coleta BOOLEAN DEFAULT FALSE,
                    enviado_coleta_em TIMESTAMP,
                    enviado_coleta_por VARCHAR(100),

                    resolvido BOOLEAN DEFAULT FALSE,
                    resolvido_em TIMESTAMP,
                    resolvido_por VARCHAR(100),

                    -- Observações
                    observacao TEXT,

                    -- Auditoria
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    criado_por VARCHAR(100),
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_por VARCHAR(100),

                    -- Soft delete
                    ativo BOOLEAN DEFAULT TRUE
                )
            """))
            print("  ✓ Tabela vale_pallets criada")

            # Criar índices
            print("\n[2/3] Criando índices...")

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_vale_pallets_nf_pallet
                ON vale_pallets(nf_pallet)
            """))
            print("  ✓ Índice idx_vale_pallets_nf_pallet criado")

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_vale_pallets_cnpj_cliente
                ON vale_pallets(cnpj_cliente)
            """))
            print("  ✓ Índice idx_vale_pallets_cnpj_cliente criado")

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_vale_pallets_cnpj_transportadora
                ON vale_pallets(cnpj_transportadora)
            """))
            print("  ✓ Índice idx_vale_pallets_cnpj_transportadora criado")

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_vale_pallets_data_validade
                ON vale_pallets(data_validade)
            """))
            print("  ✓ Índice idx_vale_pallets_data_validade criado")

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_vale_pallets_resolvido
                ON vale_pallets(resolvido)
            """))
            print("  ✓ Índice idx_vale_pallets_resolvido criado")

            db.session.commit()
            print("\n" + "=" * 60)
            print("Migration concluída com sucesso!")
            print("=" * 60)

        except Exception as e:
            print(f"\n[ERRO] Falha na migration: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()
