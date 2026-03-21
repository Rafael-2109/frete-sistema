"""
Migration: Criar tabelas carvia_clientes + carvia_cliente_enderecos
Data: 2026-03-20
Descricao:
  - carvia_clientes: cadastro de clientes CarVia
  - carvia_cliente_enderecos: enderecos (Receita + fisico) com UNIQUE(cliente_id, cnpj, tipo)
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes(conn):
    """Verifica estado antes da migration"""
    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables "
        "  WHERE table_name = 'carvia_clientes'"
        ")"
    ))
    existe_clientes = result.scalar()

    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables "
        "  WHERE table_name = 'carvia_cliente_enderecos'"
        ")"
    ))
    existe_enderecos = result.scalar()

    print(f"[ANTES] carvia_clientes existe: {existe_clientes}")
    print(f"[ANTES] carvia_cliente_enderecos existe: {existe_enderecos}")
    return existe_clientes, existe_enderecos


def executar_migration(conn):
    """Executa DDL"""
    # 1. Tabela carvia_clientes
    conn.execute(db.text("""
        CREATE TABLE IF NOT EXISTS carvia_clientes (
            id SERIAL PRIMARY KEY,
            nome_comercial VARCHAR(255) NOT NULL,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            observacoes TEXT,
            criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            criado_por VARCHAR(100) NOT NULL,
            atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))
    print("[OK] carvia_clientes criada")

    # 2. Tabela carvia_cliente_enderecos
    conn.execute(db.text("""
        CREATE TABLE IF NOT EXISTS carvia_cliente_enderecos (
            id SERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL
                REFERENCES carvia_clientes(id) ON DELETE CASCADE,
            cnpj VARCHAR(20) NOT NULL,
            razao_social VARCHAR(255),

            -- Dados da Receita Federal (readonly)
            receita_uf VARCHAR(2),
            receita_cidade VARCHAR(100),
            receita_logradouro VARCHAR(255),
            receita_numero VARCHAR(20),
            receita_bairro VARCHAR(100),
            receita_cep VARCHAR(10),
            receita_complemento VARCHAR(255),

            -- Endereco fisico (editavel, pre-preenchido da Receita)
            fisico_uf VARCHAR(2),
            fisico_cidade VARCHAR(100),
            fisico_logradouro VARCHAR(255),
            fisico_numero VARCHAR(20),
            fisico_bairro VARCHAR(100),
            fisico_cep VARCHAR(10),
            fisico_complemento VARCHAR(255),

            -- Tipo e flags
            tipo VARCHAR(20) NOT NULL,
            principal BOOLEAN NOT NULL DEFAULT FALSE,
            criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            criado_por VARCHAR(100) NOT NULL,

            -- Constraints
            CONSTRAINT uq_carvia_cliente_endereco UNIQUE (cliente_id, cnpj, tipo),
            CONSTRAINT ck_carvia_endereco_tipo CHECK (tipo IN ('ORIGEM', 'DESTINO'))
        )
    """))
    print("[OK] carvia_cliente_enderecos criada")

    # 3. Indices
    conn.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_cliente_end_cliente
            ON carvia_cliente_enderecos(cliente_id)
    """))
    conn.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_cliente_end_cnpj
            ON carvia_cliente_enderecos(cnpj)
    """))
    conn.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_cliente_end_tipo
            ON carvia_cliente_enderecos(tipo)
    """))
    print("[OK] Indices criados")


def verificar_depois(conn):
    """Verifica estado apos migration"""
    for tabela in ['carvia_clientes', 'carvia_cliente_enderecos']:
        result = conn.execute(db.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables "
            f"  WHERE table_name = '{tabela}'"
            ")"
        ))
        print(f"[DEPOIS] {tabela} existe: {result.scalar()}")

    result = conn.execute(db.text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'carvia_cliente_enderecos'
        ORDER BY indexname
    """))
    for row in result:
        print(f"  indice: {row[0]}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            print("=" * 60)
            print("Migration: Criar tabelas carvia_clientes + enderecos")
            print("=" * 60)

            verificar_antes(conn)
            print("-" * 60)
            executar_migration(conn)
            print("-" * 60)
            verificar_depois(conn)

            print("=" * 60)
            print("Migration concluida com sucesso!")
