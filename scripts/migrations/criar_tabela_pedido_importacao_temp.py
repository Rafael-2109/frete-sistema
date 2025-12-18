"""
Script para criar a tabela pedido_importacao_temp

Armazena dados temporários de importação de PDF para lançamento no Odoo.
Substitui o uso de session HTTP para evitar perda de dados em operações longas.

Executar localmente:
    source .venv/bin/activate
    python scripts/migrations/criar_tabela_pedido_importacao_temp.py

Para Render Shell, usar o SQL puro no final deste arquivo.
"""

import sys
import os

# Adiciona o path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabela():
    """Cria a tabela usando SQLAlchemy"""
    app = create_app()
    with app.app_context():
        try:
            # Importa o modelo para registrá-lo
            from app.pedidos.integracao_odoo.models import PedidoImportacaoTemp

            # Cria a tabela
            db.create_all()

            print("✅ Tabela pedido_importacao_temp criada com sucesso!")

        except Exception as e:
            print(f"❌ Erro ao criar tabela: {e}")
            db.session.rollback()
            raise


def criar_tabela_sql():
    """Cria a tabela usando SQL puro (para Render Shell)"""
    app = create_app()
    with app.app_context():
        try:
            # SQL para criar tabela pedido_importacao_temp
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS pedido_importacao_temp (
                    id SERIAL PRIMARY KEY,

                    -- Chave de identificação
                    chave_importacao VARCHAR(100) UNIQUE NOT NULL,

                    -- Status
                    status VARCHAR(20) DEFAULT 'PROCESSADO' NOT NULL,

                    -- Origem do documento
                    rede VARCHAR(50) NOT NULL,
                    tipo_documento VARCHAR(50) NOT NULL,
                    numero_documento VARCHAR(100),
                    numero_pedido_cliente VARCHAR(100),
                    arquivo_pdf_s3 VARCHAR(500),
                    filename_original VARCHAR(255),

                    -- Dados completos (JSON)
                    dados_brutos JSONB,
                    identificacao JSONB,
                    summary JSONB,
                    validacao_precos JSONB,
                    itens_sem_depara JSONB,

                    -- Dados por filial (JSON editável)
                    dados_filiais JSONB,

                    -- Justificativa global
                    justificativa_global TEXT,

                    -- Flags
                    tem_divergencia BOOLEAN DEFAULT FALSE NOT NULL,
                    pode_inserir BOOLEAN DEFAULT FALSE NOT NULL,

                    -- Auditoria
                    usuario VARCHAR(100) NOT NULL,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expira_em TIMESTAMP,

                    -- Resultado do lançamento
                    resultados_lancamento JSONB
                );
            """))

            print("✅ Tabela pedido_importacao_temp criada")

            # Índices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_pedido_imp_temp_chave
                ON pedido_importacao_temp (chave_importacao);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_importacao_temp_status
                ON pedido_importacao_temp (status);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_importacao_temp_criado
                ON pedido_importacao_temp (criado_em);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_importacao_temp_expira
                ON pedido_importacao_temp (expira_em);
            """))

            print("✅ Índices criados")

            db.session.commit()
            print("\n✅ Tabela e índices criados com sucesso!")

        except Exception as e:
            print(f"❌ Erro ao criar tabela: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Criar tabela pedido_importacao_temp')
    parser.add_argument('--sql', action='store_true', help='Usar SQL puro ao invés de SQLAlchemy')

    args = parser.parse_args()

    if args.sql:
        criar_tabela_sql()
    else:
        criar_tabela()

"""
 ==============================================================================
 SQL PURO PARA RENDER SHELL
 ==============================================================================
 Copie e cole os comandos abaixo no Render Shell:

 CREATE TABLE IF NOT EXISTS pedido_importacao_temp (
     id SERIAL PRIMARY KEY,
     chave_importacao VARCHAR(100) UNIQUE NOT NULL,
     status VARCHAR(20) DEFAULT 'PROCESSADO' NOT NULL,
     rede VARCHAR(50) NOT NULL,
     tipo_documento VARCHAR(50) NOT NULL,
     numero_documento VARCHAR(100),
     numero_pedido_cliente VARCHAR(100),
     arquivo_pdf_s3 VARCHAR(500),
     filename_original VARCHAR(255),
     dados_brutos JSONB,
     identificacao JSONB,
     summary JSONB,
     validacao_precos JSONB,
     itens_sem_depara JSONB,
     dados_filiais JSONB,
     justificativa_global TEXT,
     tem_divergencia BOOLEAN DEFAULT FALSE NOT NULL,
     pode_inserir BOOLEAN DEFAULT FALSE NOT NULL,
     usuario VARCHAR(100) NOT NULL,
     criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
     atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     expira_em TIMESTAMP,
     resultados_lancamento JSONB
 );

 CREATE INDEX IF NOT EXISTS idx_pedido_imp_temp_chave ON pedido_importacao_temp (chave_importacao);
 CREATE INDEX IF NOT EXISTS idx_importacao_temp_status ON pedido_importacao_temp (status);
 CREATE INDEX IF NOT EXISTS idx_importacao_temp_criado ON pedido_importacao_temp (criado_em);
 CREATE INDEX IF NOT EXISTS idx_importacao_temp_expira ON pedido_importacao_temp (expira_em);
 ==============================================================================
"""