"""
Migration: Criar tabela conhecimento_transporte
================================================

OBJETIVO: Criar tabela para armazenar CTes do Odoo e vincular com fretes

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402

def criar_tabela_cte():
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🔧 MIGRATION: Criar tabela conhecimento_transporte")
            print("=" * 80)

            # Verificar se tabela já existe
            print("\n1️⃣ Verificando se tabela já existe...")

            resultado = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'conhecimento_transporte'
                )
            """))

            existe = resultado.scalar()

            if existe:
                print("⚠️  Tabela já existe! Nada a fazer.")
                return

            print("✅ Tabela não existe. Criando...")

            # Criar tabela
            print("\n2️⃣ Criando tabela conhecimento_transporte...")

            db.session.execute(text("""
                CREATE TABLE conhecimento_transporte (
                    id SERIAL PRIMARY KEY,

                    -- Vínculo Odoo
                    dfe_id VARCHAR(50) NOT NULL UNIQUE,
                    odoo_ativo BOOLEAN DEFAULT TRUE,
                    odoo_name VARCHAR(100),
                    odoo_status_codigo VARCHAR(2),
                    odoo_status_descricao VARCHAR(50),

                    -- Dados CTe (chave e numeração)
                    chave_acesso VARCHAR(44) UNIQUE,
                    numero_cte VARCHAR(20),
                    serie_cte VARCHAR(10),

                    -- Datas
                    data_emissao DATE,
                    data_entrada DATE,

                    -- Valores
                    valor_total NUMERIC(15, 2),
                    valor_frete NUMERIC(15, 2),
                    valor_icms NUMERIC(15, 2),
                    vencimento DATE,

                    -- Emissor (Transportadora)
                    cnpj_emitente VARCHAR(20),
                    nome_emitente VARCHAR(255),
                    ie_emitente VARCHAR(20),

                    -- Partes envolvidas
                    cnpj_destinatario VARCHAR(20),
                    cnpj_remetente VARCHAR(20),
                    cnpj_expedidor VARCHAR(20),

                    -- Municípios
                    municipio_inicio VARCHAR(10),
                    municipio_fim VARCHAR(10),

                    -- Tomador
                    tomador VARCHAR(1),

                    -- Dados adicionais
                    informacoes_complementares TEXT,
                    tipo_pedido VARCHAR(20),

                    -- Arquivos
                    cte_pdf_path VARCHAR(500),
                    cte_xml_path VARCHAR(500),
                    cte_pdf_nome_arquivo VARCHAR(255),
                    cte_xml_nome_arquivo VARCHAR(255),

                    -- Relacionamentos Odoo
                    odoo_partner_id INTEGER,
                    odoo_invoice_ids TEXT,
                    odoo_purchase_fiscal_id INTEGER,

                    -- Vínculo com frete
                    frete_id INTEGER REFERENCES fretes(id) ON DELETE SET NULL,
                    vinculado_manualmente BOOLEAN DEFAULT FALSE,
                    vinculado_em TIMESTAMP,
                    vinculado_por VARCHAR(100),

                    -- Auditoria
                    importado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    importado_por VARCHAR(100) DEFAULT 'Sistema Odoo',
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_por VARCHAR(100),
                    ativo BOOLEAN DEFAULT TRUE
                )
            """))

            db.session.commit()
            print("✅ Tabela criada com sucesso!")

            # Criar índices
            print("\n3️⃣ Criando índices...")

            indices = [
                ("idx_cte_dfe_id", "dfe_id"),
                ("idx_cte_chave_acesso", "chave_acesso"),
                ("idx_cte_numero_serie", "numero_cte, serie_cte"),
                ("idx_cte_cnpj_emitente", "cnpj_emitente"),
                ("idx_cte_cnpj_remetente", "cnpj_remetente"),
                ("idx_cte_cnpj_destinatario", "cnpj_destinatario"),
                ("idx_cte_data_emissao", "data_emissao"),
                ("idx_cte_frete", "frete_id"),
                ("idx_cte_status", "odoo_status_codigo"),
                ("idx_cte_ativo", "ativo"),
            ]

            for nome_indice, campos in indices:
                print(f"   📊 Criando índice {nome_indice}...")
                db.session.execute(text(f"""
                    CREATE INDEX {nome_indice} ON conhecimento_transporte ({campos})
                """))

            db.session.commit()
            print("✅ Índices criados com sucesso!")

            # Verificar estrutura
            print("\n4️⃣ Verificando estrutura criada...")
            resultado = db.session.execute(text("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns
                WHERE table_name = 'conhecimento_transporte'
                ORDER BY ordinal_position
            """))

            colunas = resultado.fetchall()
            print(f"✅ Total de colunas criadas: {len(colunas)}")

            print("\n" + "=" * 80)
            print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    criar_tabela_cte()
