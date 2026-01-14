"""
Script de Migracao - FASE 1: Validacao Fiscal de Recebimento
============================================================

Cria as tabelas:
- perfil_fiscal_produto_fornecedor (baseline fiscal)
- divergencia_fiscal (divergencias que bloqueiam recebimento)
- cadastro_primeira_compra (validacao manual de 1a compra)

Referencia: .claude/references/RECEBIMENTO_MATERIAIS.md

Criado em: 13/01/2025
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabelas_validacao_fiscal():
    """Cria todas as tabelas da validacao fiscal"""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se tabela ja existe
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'perfil_fiscal_produto_fornecedor'
                )
            """))
            if result.scalar():
                print("Tabela perfil_fiscal_produto_fornecedor ja existe. Pulando criacao...")
                return

            # =====================================================================
            # 1. Criar tabela perfil_fiscal_produto_fornecedor
            # =====================================================================
            print("Criando tabela perfil_fiscal_produto_fornecedor...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS perfil_fiscal_produto_fornecedor (
                    id SERIAL PRIMARY KEY,

                    -- Identificacao (chave composta)
                    cod_produto VARCHAR(50) NOT NULL,
                    cnpj_fornecedor VARCHAR(20) NOT NULL,

                    -- Dados fiscais esperados (baseline)
                    ncm_esperado VARCHAR(10),
                    cfop_esperados TEXT,
                    cst_icms_esperado VARCHAR(5),
                    aliquota_icms_esperada NUMERIC(5,2),
                    aliquota_icms_st_esperada NUMERIC(5,2),
                    aliquota_ipi_esperada NUMERIC(5,2),

                    -- Tolerancias especificas
                    tolerancia_bc_icms_pct NUMERIC(5,2) DEFAULT 2.0,
                    tolerancia_bc_icms_st_pct NUMERIC(5,2) DEFAULT 2.0,
                    tolerancia_tributos_pct NUMERIC(5,2) DEFAULT 5.0,

                    -- Historico
                    ultimas_nfs_ids TEXT,

                    -- Auditoria
                    criado_por VARCHAR(100),
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_por VARCHAR(100),
                    atualizado_em TIMESTAMP,
                    ativo BOOLEAN DEFAULT TRUE,

                    UNIQUE(cod_produto, cnpj_fornecedor)
                )
            """))
            print("  Tabela perfil_fiscal_produto_fornecedor criada!")

            # Indices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_perfil_fiscal_produto
                ON perfil_fiscal_produto_fornecedor(cod_produto)
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_perfil_fiscal_fornecedor
                ON perfil_fiscal_produto_fornecedor(cnpj_fornecedor)
            """))
            print("  Indices criados!")

            # =====================================================================
            # 2. Criar tabela divergencia_fiscal
            # =====================================================================
            print("Criando tabela divergencia_fiscal...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS divergencia_fiscal (
                    id SERIAL PRIMARY KEY,

                    -- Referencias Odoo
                    odoo_dfe_id VARCHAR(50) NOT NULL,
                    odoo_dfe_line_id VARCHAR(50),
                    perfil_fiscal_id INTEGER REFERENCES perfil_fiscal_produto_fornecedor(id) ON DELETE SET NULL,

                    -- Produto/Fornecedor
                    cod_produto VARCHAR(50) NOT NULL,
                    nome_produto VARCHAR(255),
                    cnpj_fornecedor VARCHAR(20) NOT NULL,
                    razao_fornecedor VARCHAR(255),

                    -- Divergencia
                    campo VARCHAR(50) NOT NULL,
                    campo_label VARCHAR(100),
                    valor_esperado VARCHAR(100),
                    valor_encontrado VARCHAR(100),
                    diferenca_percentual NUMERIC(10,2),

                    -- Analise IA
                    analise_ia TEXT,
                    contexto_ia TEXT,

                    -- Resolucao
                    status VARCHAR(20) DEFAULT 'pendente' NOT NULL,
                    resolucao VARCHAR(50),
                    atualizar_baseline BOOLEAN DEFAULT FALSE,
                    justificativa TEXT,
                    resolvido_por VARCHAR(100),
                    resolvido_em TIMESTAMP,

                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("  Tabela divergencia_fiscal criada!")

            # Indices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_divergencia_dfe
                ON divergencia_fiscal(odoo_dfe_id)
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_divergencia_status
                ON divergencia_fiscal(status)
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_divergencia_line
                ON divergencia_fiscal(odoo_dfe_line_id)
            """))
            print("  Indices criados!")

            # =====================================================================
            # 3. Criar tabela cadastro_primeira_compra
            # =====================================================================
            print("Criando tabela cadastro_primeira_compra...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS cadastro_primeira_compra (
                    id SERIAL PRIMARY KEY,

                    -- Referencias Odoo
                    odoo_dfe_id VARCHAR(50) NOT NULL,
                    odoo_dfe_line_id VARCHAR(50),

                    -- Identificacao
                    cod_produto VARCHAR(50) NOT NULL,
                    nome_produto VARCHAR(255),
                    cnpj_fornecedor VARCHAR(20) NOT NULL,
                    razao_fornecedor VARCHAR(255),

                    -- Dados fiscais da NF
                    ncm VARCHAR(10),
                    cfop VARCHAR(10),
                    cst_icms VARCHAR(5),
                    aliquota_icms NUMERIC(5,2),
                    aliquota_icms_st NUMERIC(5,2),
                    aliquota_ipi NUMERIC(5,2),
                    bc_icms NUMERIC(15,2),
                    bc_icms_st NUMERIC(15,2),
                    valor_tributos_aprox NUMERIC(15,2),
                    info_complementar TEXT,

                    -- Status
                    status VARCHAR(20) DEFAULT 'pendente' NOT NULL,
                    validado_por VARCHAR(100),
                    validado_em TIMESTAMP,
                    observacao TEXT,

                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("  Tabela cadastro_primeira_compra criada!")

            # Indices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_primeira_compra_dfe
                ON cadastro_primeira_compra(odoo_dfe_id)
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_primeira_compra_status
                ON cadastro_primeira_compra(status)
            """))
            print("  Indices criados!")

            # =====================================================================
            # 4. Criar tabela validacao_fiscal_dfe (controle do scheduler)
            # =====================================================================
            print("Criando tabela validacao_fiscal_dfe...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS validacao_fiscal_dfe (
                    id SERIAL PRIMARY KEY,

                    -- Identificacao DFE (Odoo)
                    odoo_dfe_id INTEGER NOT NULL UNIQUE,
                    numero_nf VARCHAR(20),
                    chave_nfe VARCHAR(44),

                    -- Fornecedor
                    cnpj_fornecedor VARCHAR(20),
                    razao_fornecedor VARCHAR(255),

                    -- Status da validacao
                    status VARCHAR(20) DEFAULT 'pendente' NOT NULL,

                    -- Contadores
                    total_linhas INTEGER DEFAULT 0,
                    linhas_aprovadas INTEGER DEFAULT 0,
                    linhas_divergentes INTEGER DEFAULT 0,
                    linhas_primeira_compra INTEGER DEFAULT 0,

                    -- Erro
                    erro_mensagem TEXT,

                    -- Auditoria
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    validado_em TIMESTAMP,
                    atualizado_em TIMESTAMP
                )
            """))
            print("  Tabela validacao_fiscal_dfe criada!")

            # Indices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_validacao_dfe_odoo
                ON validacao_fiscal_dfe(odoo_dfe_id)
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_validacao_dfe_status
                ON validacao_fiscal_dfe(status)
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_validacao_dfe_cnpj
                ON validacao_fiscal_dfe(cnpj_fornecedor)
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_validacao_dfe_chave
                ON validacao_fiscal_dfe(chave_nfe)
            """))
            print("  Indices criados!")

            # Commit
            db.session.commit()
            print("\n" + "="*60)
            print("SUCESSO: Todas as tabelas da validacao fiscal criadas!")
            print("  - perfil_fiscal_produto_fornecedor")
            print("  - divergencia_fiscal")
            print("  - cadastro_primeira_compra")
            print("  - validacao_fiscal_dfe")
            print("="*60)

        except Exception as e:
            db.session.rollback()
            print(f"\nERRO: {e}")
            raise


if __name__ == '__main__':
    criar_tabelas_validacao_fiscal()
