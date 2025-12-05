"""
Script para criar as tabelas do Importador de Pedidos de Redes de Atacarejo

Tabelas criadas:
- tabela_rede_precos: Preços por Rede/Região/Produto
- regiao_tabela_rede: Mapeamento UF → Região
- registro_pedido_odoo: Log de pedidos inseridos no Odoo

Executar localmente:
    source venv/bin/activate
    python scripts/migrations/criar_tabelas_importador_redes.py

Para Render Shell, usar o SQL puro no final deste arquivo.
"""

import sys
import os

# Adiciona o path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabelas():
    """Cria as tabelas usando SQLAlchemy"""
    app = create_app()
    with app.app_context():
        try:
            # Importa os modelos para registrá-los
            from app.pedidos.validacao.models import TabelaRede, RegiaoTabelaRede
            from app.pedidos.integracao_odoo.models import RegistroPedidoOdoo

            # Cria as tabelas
            db.create_all()

            print("✅ Tabelas criadas com sucesso!")
            print("   - tabela_rede_precos")
            print("   - regiao_tabela_rede")
            print("   - registro_pedido_odoo")

        except Exception as e:
            print(f"❌ Erro ao criar tabelas: {e}")
            db.session.rollback()
            raise


def criar_tabelas_sql():
    """Cria as tabelas usando SQL puro (para Render Shell)"""
    app = create_app()
    with app.app_context():
        try:
            # SQL para criar tabela_rede_precos
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS tabela_rede_precos (
                    id SERIAL PRIMARY KEY,
                    rede VARCHAR(50) NOT NULL,
                    regiao VARCHAR(50) NOT NULL,
                    cod_produto VARCHAR(50) NOT NULL,
                    preco NUMERIC(15, 2) NOT NULL,
                    ativo BOOLEAN DEFAULT TRUE NOT NULL,
                    vigencia_inicio DATE,
                    vigencia_fim DATE,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    atualizado_em TIMESTAMP,
                    criado_por VARCHAR(100),
                    atualizado_por VARCHAR(100),
                    CONSTRAINT uq_tabela_rede_produto UNIQUE (rede, regiao, cod_produto)
                );
            """))

            # Índices para tabela_rede_precos
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tabela_rede_precos_rede ON tabela_rede_precos (rede);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tabela_rede_precos_regiao ON tabela_rede_precos (regiao);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tabela_rede_precos_produto ON tabela_rede_precos (cod_produto);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tabela_rede_regiao ON tabela_rede_precos (rede, regiao);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tabela_rede_produto ON tabela_rede_precos (rede, cod_produto);
            """))

            print("✅ Tabela tabela_rede_precos criada")

            # SQL para criar regiao_tabela_rede
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS regiao_tabela_rede (
                    id SERIAL PRIMARY KEY,
                    rede VARCHAR(50) NOT NULL,
                    uf VARCHAR(2) NOT NULL,
                    regiao VARCHAR(50) NOT NULL,
                    ativo BOOLEAN DEFAULT TRUE NOT NULL,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    criado_por VARCHAR(100),
                    CONSTRAINT uq_regiao_rede_uf UNIQUE (rede, uf)
                );
            """))

            # Índices para regiao_tabela_rede
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_regiao_tabela_rede_rede ON regiao_tabela_rede (rede);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_regiao_tabela_rede_uf ON regiao_tabela_rede (uf);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_regiao_rede_uf ON regiao_tabela_rede (rede, uf);
            """))

            print("✅ Tabela regiao_tabela_rede criada")

            # SQL para criar registro_pedido_odoo
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS registro_pedido_odoo (
                    id SERIAL PRIMARY KEY,
                    rede VARCHAR(50) NOT NULL,
                    tipo_documento VARCHAR(50) NOT NULL,
                    numero_documento VARCHAR(100),
                    arquivo_pdf_s3 VARCHAR(500),
                    cnpj_cliente VARCHAR(20) NOT NULL,
                    nome_cliente VARCHAR(255),
                    uf_cliente VARCHAR(2),
                    cep_cliente VARCHAR(10),
                    endereco_cliente VARCHAR(500),
                    odoo_order_id INTEGER,
                    odoo_order_name VARCHAR(50),
                    status_odoo VARCHAR(50) DEFAULT 'PENDENTE' NOT NULL,
                    mensagem_erro TEXT,
                    dados_documento JSONB,
                    divergente BOOLEAN DEFAULT FALSE NOT NULL,
                    divergencias JSONB,
                    justificativa_aprovacao TEXT,
                    inserido_por VARCHAR(100) NOT NULL,
                    aprovado_por VARCHAR(100),
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    processado_em TIMESTAMP
                );
            """))

            # Índices para registro_pedido_odoo
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_registro_pedido_odoo_rede ON registro_pedido_odoo (rede);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_registro_pedido_odoo_cnpj ON registro_pedido_odoo (cnpj_cliente);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_registro_rede_cnpj ON registro_pedido_odoo (rede, cnpj_cliente);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_registro_odoo_order ON registro_pedido_odoo (odoo_order_id);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_registro_status ON registro_pedido_odoo (status_odoo);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_registro_criado_em ON registro_pedido_odoo (criado_em);
            """))

            print("✅ Tabela registro_pedido_odoo criada")

            db.session.commit()
            print("\n✅ Todas as tabelas criadas com sucesso!")

        except Exception as e:
            print(f"❌ Erro ao criar tabelas: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Criar tabelas do Importador de Redes')
    parser.add_argument('--sql', action='store_true', help='Usar SQL puro ao invés de SQLAlchemy')

    args = parser.parse_args()

    if args.sql:
        criar_tabelas_sql()
    else:
        criar_tabelas()


# ==============================================================================
# SQL PURO PARA RENDER SHELL
# ==============================================================================
# Copie e cole os comandos abaixo no Render Shell:
#
# -- 1. Criar tabela_rede_precos
# CREATE TABLE IF NOT EXISTS tabela_rede_precos (
#     id SERIAL PRIMARY KEY,
#     rede VARCHAR(50) NOT NULL,
#     regiao VARCHAR(50) NOT NULL,
#     cod_produto VARCHAR(50) NOT NULL,
#     preco NUMERIC(15, 2) NOT NULL,
#     ativo BOOLEAN DEFAULT TRUE NOT NULL,
#     vigencia_inicio DATE,
#     vigencia_fim DATE,
#     criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
#     atualizado_em TIMESTAMP,
#     criado_por VARCHAR(100),
#     atualizado_por VARCHAR(100),
#     CONSTRAINT uq_tabela_rede_produto UNIQUE (rede, regiao, cod_produto)
# );
# CREATE INDEX IF NOT EXISTS idx_tabela_rede_precos_rede ON tabela_rede_precos (rede);
# CREATE INDEX IF NOT EXISTS idx_tabela_rede_precos_regiao ON tabela_rede_precos (regiao);
# CREATE INDEX IF NOT EXISTS idx_tabela_rede_precos_produto ON tabela_rede_precos (cod_produto);
# CREATE INDEX IF NOT EXISTS idx_tabela_rede_regiao ON tabela_rede_precos (rede, regiao);
# CREATE INDEX IF NOT EXISTS idx_tabela_rede_produto ON tabela_rede_precos (rede, cod_produto);
#
# -- 2. Criar regiao_tabela_rede
# CREATE TABLE IF NOT EXISTS regiao_tabela_rede (
#     id SERIAL PRIMARY KEY,
#     rede VARCHAR(50) NOT NULL,
#     uf VARCHAR(2) NOT NULL,
#     regiao VARCHAR(50) NOT NULL,
#     ativo BOOLEAN DEFAULT TRUE NOT NULL,
#     criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
#     criado_por VARCHAR(100),
#     CONSTRAINT uq_regiao_rede_uf UNIQUE (rede, uf)
# );
# CREATE INDEX IF NOT EXISTS idx_regiao_tabela_rede_rede ON regiao_tabela_rede (rede);
# CREATE INDEX IF NOT EXISTS idx_regiao_tabela_rede_uf ON regiao_tabela_rede (uf);
# CREATE INDEX IF NOT EXISTS idx_regiao_rede_uf ON regiao_tabela_rede (rede, uf);
#
# -- 3. Criar registro_pedido_odoo
# CREATE TABLE IF NOT EXISTS registro_pedido_odoo (
#     id SERIAL PRIMARY KEY,
#     rede VARCHAR(50) NOT NULL,
#     tipo_documento VARCHAR(50) NOT NULL,
#     numero_documento VARCHAR(100),
#     arquivo_pdf_s3 VARCHAR(500),
#     cnpj_cliente VARCHAR(20) NOT NULL,
#     nome_cliente VARCHAR(255),
#     uf_cliente VARCHAR(2),
#     cep_cliente VARCHAR(10),
#     endereco_cliente VARCHAR(500),
#     odoo_order_id INTEGER,
#     odoo_order_name VARCHAR(50),
#     status_odoo VARCHAR(50) DEFAULT 'PENDENTE' NOT NULL,
#     mensagem_erro TEXT,
#     dados_documento JSONB,
#     divergente BOOLEAN DEFAULT FALSE NOT NULL,
#     divergencias JSONB,
#     justificativa_aprovacao TEXT,
#     inserido_por VARCHAR(100) NOT NULL,
#     aprovado_por VARCHAR(100),
#     criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
#     processado_em TIMESTAMP
# );
# CREATE INDEX IF NOT EXISTS idx_registro_pedido_odoo_rede ON registro_pedido_odoo (rede);
# CREATE INDEX IF NOT EXISTS idx_registro_pedido_odoo_cnpj ON registro_pedido_odoo (cnpj_cliente);
# CREATE INDEX IF NOT EXISTS idx_registro_rede_cnpj ON registro_pedido_odoo (rede, cnpj_cliente);
# CREATE INDEX IF NOT EXISTS idx_registro_odoo_order ON registro_pedido_odoo (odoo_order_id);
# CREATE INDEX IF NOT EXISTS idx_registro_status ON registro_pedido_odoo (status_odoo);
# CREATE INDEX IF NOT EXISTS idx_registro_criado_em ON registro_pedido_odoo (criado_em);
# ==============================================================================
