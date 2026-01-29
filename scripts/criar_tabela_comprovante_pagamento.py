"""
Migration: Criar tabela comprovante_pagamento_boleto
=====================================================

Armazena comprovantes de pagamento de boleto extraídos de PDFs do SICOOB.
Chave única: numero_agendamento.

Uso local:
    python scripts/criar_tabela_comprovante_pagamento.py

Render Shell (SQL manual):
    python scripts/criar_tabela_comprovante_pagamento.py --sql
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


SQL_MIGRATION = """
-- =============================================
-- Criar tabela comprovante_pagamento_boleto
-- Data: 2026-01-29
-- =============================================

CREATE TABLE IF NOT EXISTS comprovante_pagamento_boleto (
    id                          SERIAL PRIMARY KEY,

    -- Chave única: número do agendamento bancário
    numero_agendamento          VARCHAR(50) NOT NULL UNIQUE,

    -- Cabeçalho
    data_comprovante            DATE,
    cooperativa                 VARCHAR(255),
    conta                       VARCHAR(50),
    cliente                     VARCHAR(255),
    linha_digitavel             VARCHAR(255),
    numero_documento            VARCHAR(100),
    nosso_numero                VARCHAR(50),
    instituicao_emissora        VARCHAR(50),
    tipo_documento              VARCHAR(50),

    -- Beneficiário
    beneficiario_razao_social   VARCHAR(255),
    beneficiario_nome_fantasia  VARCHAR(255),
    beneficiario_cnpj_cpf       VARCHAR(20),

    -- Pagador
    pagador_razao_social        VARCHAR(255),
    pagador_nome_fantasia       VARCHAR(255),
    pagador_cnpj_cpf            VARCHAR(20),

    -- Datas
    data_realizado              VARCHAR(50),
    data_pagamento              DATE,
    data_vencimento             DATE,

    -- Valores
    valor_documento             NUMERIC(15, 2),
    valor_desconto_abatimento   NUMERIC(15, 2),
    valor_juros_multa           NUMERIC(15, 2),
    valor_pago                  NUMERIC(15, 2),

    -- Status
    situacao                    VARCHAR(30),
    autenticacao                VARCHAR(100) UNIQUE,

    -- Metadados de importação
    arquivo_origem              VARCHAR(255),
    pagina_origem               INTEGER,
    importado_por               VARCHAR(100),
    importado_em                TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_comp_beneficiario_cnpj ON comprovante_pagamento_boleto(beneficiario_cnpj_cpf);
CREATE INDEX IF NOT EXISTS idx_comp_pagador_cnpj ON comprovante_pagamento_boleto(pagador_cnpj_cpf);
CREATE INDEX IF NOT EXISTS idx_comp_data_pagamento ON comprovante_pagamento_boleto(data_pagamento);
CREATE INDEX IF NOT EXISTS idx_comp_data_vencimento ON comprovante_pagamento_boleto(data_vencimento);
"""


def run_migration():
    """Executa a migration."""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRATION: Criar tabela comprovante_pagamento_boleto")
            print("=" * 60)

            commands = [
                ("Tabela comprovante_pagamento_boleto", """
                    CREATE TABLE IF NOT EXISTS comprovante_pagamento_boleto (
                        id                          SERIAL PRIMARY KEY,
                        numero_agendamento          VARCHAR(50) NOT NULL UNIQUE,
                        data_comprovante            DATE,
                        cooperativa                 VARCHAR(255),
                        conta                       VARCHAR(50),
                        cliente                     VARCHAR(255),
                        linha_digitavel             VARCHAR(255),
                        numero_documento            VARCHAR(100),
                        nosso_numero                VARCHAR(50),
                        instituicao_emissora        VARCHAR(50),
                        tipo_documento              VARCHAR(50),
                        beneficiario_razao_social   VARCHAR(255),
                        beneficiario_nome_fantasia  VARCHAR(255),
                        beneficiario_cnpj_cpf       VARCHAR(20),
                        pagador_razao_social        VARCHAR(255),
                        pagador_nome_fantasia       VARCHAR(255),
                        pagador_cnpj_cpf            VARCHAR(20),
                        data_realizado              VARCHAR(50),
                        data_pagamento              DATE,
                        data_vencimento             DATE,
                        valor_documento             NUMERIC(15, 2),
                        valor_desconto_abatimento   NUMERIC(15, 2),
                        valor_juros_multa           NUMERIC(15, 2),
                        valor_pago                  NUMERIC(15, 2),
                        situacao                    VARCHAR(30),
                        autenticacao                VARCHAR(100) UNIQUE,
                        arquivo_origem              VARCHAR(255),
                        pagina_origem               INTEGER,
                        importado_por               VARCHAR(100),
                        importado_em                TIMESTAMP DEFAULT NOW()
                    )
                """),
                ("idx_comp_beneficiario_cnpj",
                 "CREATE INDEX IF NOT EXISTS idx_comp_beneficiario_cnpj ON comprovante_pagamento_boleto(beneficiario_cnpj_cpf)"),
                ("idx_comp_pagador_cnpj",
                 "CREATE INDEX IF NOT EXISTS idx_comp_pagador_cnpj ON comprovante_pagamento_boleto(pagador_cnpj_cpf)"),
                ("idx_comp_data_pagamento",
                 "CREATE INDEX IF NOT EXISTS idx_comp_data_pagamento ON comprovante_pagamento_boleto(data_pagamento)"),
                ("idx_comp_data_vencimento",
                 "CREATE INDEX IF NOT EXISTS idx_comp_data_vencimento ON comprovante_pagamento_boleto(data_vencimento)"),
            ]

            for nome, sql_cmd in commands:
                try:
                    db.session.execute(text(sql_cmd))
                    print(f"  \u2705 {nome}")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        print(f"  \u23ed\ufe0f  {nome} (j\u00e1 existe)")
                    else:
                        print(f"  \u274c {nome}: {e}")

            db.session.commit()

            print()
            print("=" * 60)
            print("\u2705 Migration conclu\u00edda com sucesso!")
            print("=" * 60)

            # Verificar
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'comprovante_pagamento_boleto'
                ORDER BY ordinal_position
            """))
            columns = [row[0] for row in result]
            print(f"\nColunas criadas ({len(columns)}): {', '.join(columns)}")

        except Exception as e:
            print(f"\u274c Erro na migration: {e}")
            db.session.rollback()
            raise


def print_sql():
    """Imprime o SQL para execu\u00e7\u00e3o manual."""
    print("=" * 60)
    print("SQL PARA EXECU\u00c7\u00c3O MANUAL (Render Shell)")
    print("=" * 60)
    print(SQL_MIGRATION)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--sql':
        print_sql()
    else:
        run_migration()
