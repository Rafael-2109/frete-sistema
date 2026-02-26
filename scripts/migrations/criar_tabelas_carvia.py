"""
Migration: Criar tabelas do modulo CarVia
==========================================

Cria 6 tabelas:
1. carvia_nfs — NFs importadas (PDF/XML/manual)
2. carvia_operacoes — Operacao principal (CTe CarVia)
3. carvia_operacao_nfs — Junction N:N (Operacao <-> NFs)
4. carvia_subcontratos — Subcontratacoes (1 por transportadora)
5. carvia_faturas_cliente — Faturas CarVia ao cliente
6. carvia_faturas_transportadora — Faturas recebidas dos subcontratados

Executar: python scripts/migrations/criar_tabelas_carvia.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text, inspect


def verificar_tabela_existe(inspector, tabela):
    """Verifica se uma tabela ja existe no banco"""
    return tabela in inspector.get_table_names()


def criar_tabelas():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        tabelas_antes = set(inspector.get_table_names())
        tabelas_carvia = [
            'carvia_nfs',
            'carvia_operacoes',
            'carvia_operacao_nfs',
            'carvia_subcontratos',
            'carvia_faturas_cliente',
            'carvia_faturas_transportadora',
        ]

        existentes = [t for t in tabelas_carvia if t in tabelas_antes]
        if existentes:
            print(f"Tabelas ja existentes: {existentes}")
            print("Migration ja foi executada anteriormente.")
            return

        print("Criando tabelas CarVia...")

        # Faturas primeiro (sao referenciadas por operacoes e subcontratos)
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS carvia_faturas_cliente (
                id SERIAL PRIMARY KEY,
                cnpj_cliente VARCHAR(20) NOT NULL,
                nome_cliente VARCHAR(255),
                numero_fatura VARCHAR(50) NOT NULL,
                data_emissao DATE NOT NULL,
                valor_total NUMERIC(15,2) NOT NULL,
                vencimento DATE,
                arquivo_pdf_path VARCHAR(500),
                arquivo_nome_original VARCHAR(255),
                status VARCHAR(20) DEFAULT 'PENDENTE',
                observacoes TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                criado_por VARCHAR(100) NOT NULL
            );
        """))
        print("  [1/6] carvia_faturas_cliente criada")

        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS carvia_faturas_transportadora (
                id SERIAL PRIMARY KEY,
                transportadora_id INTEGER NOT NULL REFERENCES transportadoras(id),
                numero_fatura VARCHAR(50) NOT NULL,
                data_emissao DATE NOT NULL,
                valor_total NUMERIC(15,2) NOT NULL,
                vencimento DATE,
                arquivo_pdf_path VARCHAR(500),
                arquivo_nome_original VARCHAR(255),
                status_conferencia VARCHAR(20) DEFAULT 'PENDENTE',
                conferido_por VARCHAR(100),
                conferido_em TIMESTAMP,
                observacoes TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                criado_por VARCHAR(100) NOT NULL
            );
        """))
        print("  [2/6] carvia_faturas_transportadora criada")

        # NFs
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS carvia_nfs (
                id SERIAL PRIMARY KEY,
                numero_nf VARCHAR(20) NOT NULL,
                serie_nf VARCHAR(5),
                chave_acesso_nf VARCHAR(44),
                data_emissao DATE,
                cnpj_emitente VARCHAR(20) NOT NULL,
                nome_emitente VARCHAR(255),
                uf_emitente VARCHAR(2),
                cidade_emitente VARCHAR(100),
                cnpj_destinatario VARCHAR(20),
                nome_destinatario VARCHAR(255),
                uf_destinatario VARCHAR(2),
                cidade_destinatario VARCHAR(100),
                valor_total NUMERIC(15,2),
                peso_bruto NUMERIC(15,3),
                peso_liquido NUMERIC(15,3),
                quantidade_volumes INTEGER,
                arquivo_pdf_path VARCHAR(500),
                arquivo_xml_path VARCHAR(500),
                arquivo_nome_original VARCHAR(255),
                tipo_fonte VARCHAR(20) NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                criado_por VARCHAR(100) NOT NULL
            );
        """))
        print("  [3/6] carvia_nfs criada")

        # Operacoes
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS carvia_operacoes (
                id SERIAL PRIMARY KEY,
                cte_numero VARCHAR(20),
                cte_chave_acesso VARCHAR(44),
                cte_valor NUMERIC(15,2),
                cte_xml_path VARCHAR(500),
                cte_xml_nome_arquivo VARCHAR(255),
                cte_data_emissao DATE,
                cnpj_cliente VARCHAR(20) NOT NULL,
                nome_cliente VARCHAR(255),
                uf_origem VARCHAR(2),
                cidade_origem VARCHAR(100),
                uf_destino VARCHAR(2) NOT NULL,
                cidade_destino VARCHAR(100) NOT NULL,
                peso_bruto NUMERIC(15,3),
                peso_cubado NUMERIC(15,3),
                peso_utilizado NUMERIC(15,3),
                valor_mercadoria NUMERIC(15,2),
                cubagem_comprimento NUMERIC(10,2),
                cubagem_largura NUMERIC(10,2),
                cubagem_altura NUMERIC(10,2),
                cubagem_fator NUMERIC(10,2),
                cubagem_volumes INTEGER,
                tipo_entrada VARCHAR(30) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'RASCUNHO',
                fatura_cliente_id INTEGER REFERENCES carvia_faturas_cliente(id),
                observacoes TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                criado_por VARCHAR(100) NOT NULL,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("  [4/6] carvia_operacoes criada")

        # Junction N:N
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS carvia_operacao_nfs (
                id SERIAL PRIMARY KEY,
                operacao_id INTEGER NOT NULL REFERENCES carvia_operacoes(id),
                nf_id INTEGER NOT NULL REFERENCES carvia_nfs(id),
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_operacao_nf UNIQUE (operacao_id, nf_id)
            );
        """))
        print("  [5/6] carvia_operacao_nfs criada")

        # Subcontratos
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS carvia_subcontratos (
                id SERIAL PRIMARY KEY,
                operacao_id INTEGER NOT NULL REFERENCES carvia_operacoes(id),
                transportadora_id INTEGER NOT NULL REFERENCES transportadoras(id),
                cte_numero VARCHAR(20),
                cte_chave_acesso VARCHAR(44),
                cte_valor NUMERIC(15,2),
                cte_xml_path VARCHAR(500),
                cte_xml_nome_arquivo VARCHAR(255),
                cte_data_emissao DATE,
                valor_cotado NUMERIC(15,2),
                tabela_frete_id INTEGER REFERENCES tabelas_frete(id),
                valor_acertado NUMERIC(15,2),
                fatura_transportadora_id INTEGER REFERENCES carvia_faturas_transportadora(id),
                status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
                observacoes TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                criado_por VARCHAR(100) NOT NULL,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("  [6/6] carvia_subcontratos criada")

        # Indices
        print("\nCriando indices...")
        indices = [
            "CREATE INDEX IF NOT EXISTS ix_carvia_nfs_numero_nf ON carvia_nfs(numero_nf);",
            "CREATE INDEX IF NOT EXISTS ix_carvia_nfs_cnpj_emitente ON carvia_nfs(cnpj_emitente);",
            "CREATE INDEX IF NOT EXISTS ix_carvia_nfs_cnpj_destinatario ON carvia_nfs(cnpj_destinatario);",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_carvia_nfs_chave_acesso ON carvia_nfs(chave_acesso_nf) WHERE chave_acesso_nf IS NOT NULL;",
            "CREATE INDEX IF NOT EXISTS ix_carvia_operacoes_cte_numero ON carvia_operacoes(cte_numero);",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_carvia_operacoes_cte_chave ON carvia_operacoes(cte_chave_acesso) WHERE cte_chave_acesso IS NOT NULL;",
            "CREATE INDEX IF NOT EXISTS ix_carvia_operacoes_cnpj_cliente ON carvia_operacoes(cnpj_cliente);",
            "CREATE INDEX IF NOT EXISTS ix_carvia_operacoes_fatura_cliente ON carvia_operacoes(fatura_cliente_id);",
            "CREATE INDEX IF NOT EXISTS ix_carvia_operacao_nfs_operacao ON carvia_operacao_nfs(operacao_id);",
            "CREATE INDEX IF NOT EXISTS ix_carvia_operacao_nfs_nf ON carvia_operacao_nfs(nf_id);",
            "CREATE INDEX IF NOT EXISTS ix_carvia_subcontratos_operacao ON carvia_subcontratos(operacao_id);",
            "CREATE INDEX IF NOT EXISTS ix_carvia_subcontratos_transportadora ON carvia_subcontratos(transportadora_id);",
            "CREATE INDEX IF NOT EXISTS ix_carvia_subcontratos_cte_numero ON carvia_subcontratos(cte_numero);",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_carvia_subcontratos_cte_chave ON carvia_subcontratos(cte_chave_acesso) WHERE cte_chave_acesso IS NOT NULL;",
            "CREATE INDEX IF NOT EXISTS ix_carvia_subcontratos_fatura_transp ON carvia_subcontratos(fatura_transportadora_id);",
            "CREATE INDEX IF NOT EXISTS ix_carvia_faturas_cliente_cnpj ON carvia_faturas_cliente(cnpj_cliente);",
            "CREATE INDEX IF NOT EXISTS ix_carvia_faturas_cliente_numero ON carvia_faturas_cliente(numero_fatura);",
            "CREATE INDEX IF NOT EXISTS ix_carvia_faturas_transp_numero ON carvia_faturas_transportadora(numero_fatura);",
        ]
        for idx_sql in indices:
            db.session.execute(text(idx_sql))
        print(f"  {len(indices)} indices criados")

        db.session.commit()

        # Verificacao
        inspector = inspect(db.engine)
        tabelas_depois = set(inspector.get_table_names())
        novas = tabelas_depois - tabelas_antes
        print(f"\nTabelas criadas: {sorted(novas)}")
        print("Migration concluida com sucesso!")


if __name__ == '__main__':
    criar_tabelas()
