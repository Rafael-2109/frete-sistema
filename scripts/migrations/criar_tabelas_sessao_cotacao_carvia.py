"""
Migration: Criar tabelas carvia_sessoes_cotacao e carvia_sessao_demandas
=========================================================================

Sessao de cotacao CarVia — ferramenta comercial para cotar frete
subcontratado antes de fechar negocio com o cliente.

Executar: python scripts/migrations/criar_tabelas_sessao_cotacao_carvia.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def verificar_tabela_existe(conn, nome_tabela):
    """Verifica se tabela existe no banco"""
    result = conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :nome)"
    ), {'nome': nome_tabela})
    return result.scalar()


def verificar_indice_existe(conn, nome_indice):
    """Verifica se indice existe no banco"""
    result = conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM pg_indexes "
        "WHERE indexname = :nome)"
    ), {'nome': nome_indice})
    return result.scalar()


def verificar_constraint_existe(conn, nome_constraint):
    """Verifica se constraint existe no banco"""
    result = conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.table_constraints "
        "WHERE constraint_name = :nome)"
    ), {'nome': nome_constraint})
    return result.scalar()


def contar_registros(conn, tabela):
    """Conta registros de uma tabela"""
    result = conn.execute(text(f"SELECT COUNT(*) FROM {tabela}"))
    return result.scalar()


def executar_migration():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()

        # ===== BEFORE: verificar estado atual =====
        print("=" * 60)
        print("BEFORE — Estado atual do banco")
        print("=" * 60)

        sessoes_existe = verificar_tabela_existe(conn, 'carvia_sessoes_cotacao')
        demandas_existe = verificar_tabela_existe(conn, 'carvia_sessao_demandas')

        print(f"  carvia_sessoes_cotacao existe: {sessoes_existe}")
        print(f"  carvia_sessao_demandas existe: {demandas_existe}")

        if sessoes_existe and demandas_existe:
            print("\n  Tabelas ja existem. Migration ja foi executada.")
            print("  Nenhuma alteracao necessaria.")
            return

        # ===== EXECUTAR DDL =====
        print("\n" + "=" * 60)
        print("EXECUTANDO — Criando tabelas")
        print("=" * 60)

        # 1. Tabela carvia_sessoes_cotacao
        if not sessoes_existe:
            print("  Criando carvia_sessoes_cotacao...")
            conn.execute(text("""
                CREATE TABLE carvia_sessoes_cotacao (
                    id SERIAL PRIMARY KEY,
                    numero_sessao VARCHAR(20) NOT NULL,
                    nome_sessao VARCHAR(255) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'RASCUNHO',
                    valor_contra_proposta NUMERIC(15, 2),
                    resposta_cliente_obs TEXT,
                    respondido_em TIMESTAMP,
                    respondido_por VARCHAR(100),
                    enviado_em TIMESTAMP,
                    enviado_por VARCHAR(100),
                    observacoes TEXT,
                    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    criado_por VARCHAR(100) NOT NULL,
                    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

                    CONSTRAINT ck_carvia_sessao_status
                        CHECK (status IN ('RASCUNHO', 'ENVIADO', 'APROVADO', 'CONTRA_PROPOSTA', 'CANCELADO'))
                )
            """))

            # Indices
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_carvia_sessao_numero "
                "ON carvia_sessoes_cotacao (numero_sessao)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_carvia_sessao_status "
                "ON carvia_sessoes_cotacao (status)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_carvia_sessao_criado_em "
                "ON carvia_sessoes_cotacao (criado_em)"
            ))
            print("    OK — tabela + 3 indices criados")

        # 2. Tabela carvia_sessao_demandas
        if not demandas_existe:
            print("  Criando carvia_sessao_demandas...")
            conn.execute(text("""
                CREATE TABLE carvia_sessao_demandas (
                    id SERIAL PRIMARY KEY,
                    sessao_id INTEGER NOT NULL
                        REFERENCES carvia_sessoes_cotacao(id) ON DELETE CASCADE,
                    ordem INTEGER NOT NULL DEFAULT 1,
                    origem_empresa VARCHAR(255) NOT NULL,
                    origem_uf VARCHAR(2) NOT NULL,
                    origem_cidade VARCHAR(100) NOT NULL,
                    destino_empresa VARCHAR(255) NOT NULL,
                    destino_uf VARCHAR(2) NOT NULL,
                    destino_cidade VARCHAR(100) NOT NULL,
                    tipo_carga VARCHAR(100),
                    peso NUMERIC(15, 3) NOT NULL,
                    valor_mercadoria NUMERIC(15, 2) NOT NULL,
                    volume INTEGER,
                    data_coleta DATE,
                    data_entrega_prevista DATE,
                    data_agendamento DATE,
                    transportadora_id INTEGER REFERENCES transportadoras(id),
                    tabela_frete_id INTEGER REFERENCES tabelas_frete(id),
                    valor_frete_calculado NUMERIC(15, 2),
                    detalhes_calculo JSON,
                    observacoes TEXT,
                    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

                    CONSTRAINT uq_carvia_sessao_demanda_ordem
                        UNIQUE (sessao_id, ordem)
                )
            """))

            # Indices
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_carvia_sessao_demanda_sessao "
                "ON carvia_sessao_demandas (sessao_id)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_carvia_sessao_demanda_destino_uf "
                "ON carvia_sessao_demandas (destino_uf)"
            ))
            print("    OK — tabela + 2 indices + 1 unique criados")

        db.session.commit()

        # ===== AFTER: verificar resultado =====
        print("\n" + "=" * 60)
        print("AFTER — Verificando resultado")
        print("=" * 60)

        # Nova conexao apos commit
        conn = db.session.connection()

        sessoes_ok = verificar_tabela_existe(conn, 'carvia_sessoes_cotacao')
        demandas_ok = verificar_tabela_existe(conn, 'carvia_sessao_demandas')

        print(f"  carvia_sessoes_cotacao existe: {sessoes_ok}")
        print(f"  carvia_sessao_demandas existe: {demandas_ok}")

        # Verificar indices
        indices = [
            'ix_carvia_sessao_numero',
            'ix_carvia_sessao_status',
            'ix_carvia_sessao_criado_em',
            'ix_carvia_sessao_demanda_sessao',
            'ix_carvia_sessao_demanda_destino_uf',
        ]
        for idx in indices:
            existe = verificar_indice_existe(conn, idx)
            print(f"  Indice {idx}: {'OK' if existe else 'FALTANDO'}")

        # Verificar constraints
        constraints = [
            'ck_carvia_sessao_status',
            'uq_carvia_sessao_demanda_ordem',
        ]
        for cst in constraints:
            existe = verificar_constraint_existe(conn, cst)
            print(f"  Constraint {cst}: {'OK' if existe else 'FALTANDO'}")

        # Contagem
        if sessoes_ok:
            print(f"  Registros carvia_sessoes_cotacao: {contar_registros(conn, 'carvia_sessoes_cotacao')}")
        if demandas_ok:
            print(f"  Registros carvia_sessao_demandas: {contar_registros(conn, 'carvia_sessao_demandas')}")

        if sessoes_ok and demandas_ok:
            print("\n  Migration executada com SUCESSO!")
        else:
            print("\n  ERRO: Alguma tabela nao foi criada!")


if __name__ == '__main__':
    executar_migration()
