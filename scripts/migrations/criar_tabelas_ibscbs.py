"""
Script de Migration para Tabelas IBS/CBS (Reforma Tributaria 2026)
==================================================================

Cria as tabelas:
- ncm_ibscbs_validado: NCMs validados pelo departamento fiscal
- pendencia_fiscal_ibscbs: Pendencias de fornecedores que nao destacaram IBS/CBS

Uso:
    source .venv/bin/activate
    python scripts/migrations/criar_tabelas_ibscbs.py

Autor: Sistema de Fretes
Data: 2026-01-14
"""

import sys
import os

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabela_ncm_ibscbs_validado():
    """Cria tabela ncm_ibscbs_validado"""
    sql = """
    CREATE TABLE IF NOT EXISTS ncm_ibscbs_validado (
        id SERIAL PRIMARY KEY,

        -- NCM (4 primeiros digitos)
        ncm_prefixo VARCHAR(4) NOT NULL UNIQUE,
        descricao_ncm VARCHAR(255),

        -- Aliquotas esperadas (para validacao)
        aliquota_ibs_uf NUMERIC(5,2),
        aliquota_ibs_mun NUMERIC(5,2),
        aliquota_cbs NUMERIC(5,2),

        -- Reducao de aliquota (se aplicavel)
        reducao_aliquota NUMERIC(5,2),

        -- CST esperado
        cst_esperado VARCHAR(10),

        -- Classificacao tributaria esperada (codigo do Odoo)
        class_trib_codigo VARCHAR(20),

        -- Observacoes
        observacao TEXT,

        -- Controle
        ativo BOOLEAN NOT NULL DEFAULT TRUE,
        validado_por VARCHAR(100),
        validado_em TIMESTAMP,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TIMESTAMP
    );

    -- Indice para busca rapida
    CREATE INDEX IF NOT EXISTS idx_ncm_ibscbs_validado_prefixo ON ncm_ibscbs_validado(ncm_prefixo);
    CREATE INDEX IF NOT EXISTS idx_ncm_ibscbs_validado_ativo ON ncm_ibscbs_validado(ativo);

    -- Comentario na tabela
    COMMENT ON TABLE ncm_ibscbs_validado IS 'NCMs validados pelo departamento fiscal para IBS/CBS (Reforma Tributaria 2026)';
    """

    print("🔄 Criando tabela ncm_ibscbs_validado...")
    db.session.execute(text(sql))
    db.session.commit()
    print("✅ Tabela ncm_ibscbs_validado criada com sucesso!")


def criar_tabela_pendencia_fiscal_ibscbs():
    """Cria tabela pendencia_fiscal_ibscbs"""
    sql = """
    CREATE TABLE IF NOT EXISTS pendencia_fiscal_ibscbs (
        id SERIAL PRIMARY KEY,

        -- Tipo de documento
        tipo_documento VARCHAR(10) NOT NULL,  -- 'CTe' ou 'NF-e'

        -- Identificacao do documento
        chave_acesso VARCHAR(44) NOT NULL UNIQUE,
        numero_documento VARCHAR(20),
        serie VARCHAR(5),
        data_emissao DATE,

        -- Referencia ao DFE do Odoo
        odoo_dfe_id INTEGER,

        -- Referencia ao CTe local (se for CTe)
        cte_id INTEGER REFERENCES conhecimento_transporte(id),

        -- Fornecedor
        cnpj_fornecedor VARCHAR(20) NOT NULL,
        razao_fornecedor VARCHAR(255),
        uf_fornecedor VARCHAR(2),

        -- Regime tributario do fornecedor
        regime_tributario VARCHAR(1),
        regime_tributario_descricao VARCHAR(50),

        -- NCM (apenas para NF-e)
        ncm VARCHAR(10),
        ncm_prefixo VARCHAR(4),

        -- Valores do documento
        valor_total NUMERIC(15,2),
        valor_base_calculo NUMERIC(15,2),

        -- Valores IBS/CBS encontrados
        ibscbs_cst VARCHAR(10),
        ibscbs_class_trib VARCHAR(20),
        ibscbs_base NUMERIC(15,2),
        ibs_uf_aliq NUMERIC(5,2),
        ibs_uf_valor NUMERIC(15,2),
        ibs_mun_aliq NUMERIC(5,2),
        ibs_mun_valor NUMERIC(15,2),
        ibs_total NUMERIC(15,2),
        cbs_aliq NUMERIC(5,2),
        cbs_valor NUMERIC(15,2),

        -- Motivo da pendencia
        motivo_pendencia VARCHAR(100) NOT NULL,
        detalhes_pendencia TEXT,

        -- Status da pendencia
        status VARCHAR(20) NOT NULL DEFAULT 'pendente',

        -- Resolucao
        resolucao VARCHAR(50),
        justificativa TEXT,
        resolvido_por VARCHAR(100),
        resolvido_em TIMESTAMP,

        -- Auditoria
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        criado_por VARCHAR(100) DEFAULT 'SISTEMA'
    );

    -- Indices
    CREATE INDEX IF NOT EXISTS idx_pendencia_ibscbs_tipo ON pendencia_fiscal_ibscbs(tipo_documento);
    CREATE INDEX IF NOT EXISTS idx_pendencia_ibscbs_chave ON pendencia_fiscal_ibscbs(chave_acesso);
    CREATE INDEX IF NOT EXISTS idx_pendencia_ibscbs_cnpj ON pendencia_fiscal_ibscbs(cnpj_fornecedor);
    CREATE INDEX IF NOT EXISTS idx_pendencia_ibscbs_status ON pendencia_fiscal_ibscbs(status);
    CREATE INDEX IF NOT EXISTS idx_pendencia_ibscbs_ncm ON pendencia_fiscal_ibscbs(ncm_prefixo);
    CREATE INDEX IF NOT EXISTS idx_pendencia_ibscbs_odoo ON pendencia_fiscal_ibscbs(odoo_dfe_id);
    CREATE INDEX IF NOT EXISTS idx_pendencia_ibscbs_cte ON pendencia_fiscal_ibscbs(cte_id);

    -- Comentario na tabela
    COMMENT ON TABLE pendencia_fiscal_ibscbs IS 'Pendencias fiscais de IBS/CBS - Documentos de fornecedores Regime Normal que nao destacaram IBS/CBS';
    """

    print("🔄 Criando tabela pendencia_fiscal_ibscbs...")
    db.session.execute(text(sql))
    db.session.commit()
    print("✅ Tabela pendencia_fiscal_ibscbs criada com sucesso!")


def executar_migration():
    """Executa todas as migrations"""
    app = create_app()

    with app.app_context():
        try:
            print("=" * 60)
            print("🚀 MIGRATION: Tabelas IBS/CBS (Reforma Tributaria 2026)")
            print("=" * 60)

            criar_tabela_ncm_ibscbs_validado()
            criar_tabela_pendencia_fiscal_ibscbs()

            print("=" * 60)
            print("✅ MIGRATION CONCLUIDA COM SUCESSO!")
            print("=" * 60)
            print()
            print("📋 Tabelas criadas:")
            print("   - ncm_ibscbs_validado")
            print("   - pendencia_fiscal_ibscbs")
            print()
            print("🔗 Proximos passos:")
            print("   1. Cadastrar NCMs que devem validar IBS/CBS")
            print("   2. Executar processamento de CTes pendentes")
            print()

        except Exception as e:
            print(f"❌ Erro na migration: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()
