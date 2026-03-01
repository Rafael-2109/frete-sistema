"""
Migration: Linking de documentos CarVia — Schema DDL
=====================================================

1A. ALTER TABLE carvia_fatura_cliente_itens:
    - Adicionar operacao_id FK -> carvia_operacoes(id) nullable
    - Adicionar nf_id FK -> carvia_nfs(id) nullable
    - Indices para ambas FKs

1B. CREATE TABLE carvia_fatura_transportadora_itens:
    - Tabela de itens para faturas de transportadora
    - FKs para fatura_transportadora, subcontrato, operacao, nf
    - 4 indices

Execucao:
    source .venv/bin/activate
    python scripts/migrations/carvia_linking_v1_schema.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def verificar_coluna_existe(conn, tabela, coluna):
    """Verifica se coluna ja existe na tabela."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :tabela AND column_name = :coluna
        )
    """), {'tabela': tabela, 'coluna': coluna})
    return result.scalar()


def verificar_tabela_existe(conn, tabela):
    """Verifica se tabela ja existe."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = :tabela
        )
    """), {'tabela': tabela})
    return result.scalar()


def verificar_indice_existe(conn, nome_indice):
    """Verifica se indice ja existe."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = :nome
        )
    """), {'nome': nome_indice})
    return result.scalar()


def verificar_fk_existe(conn, nome_constraint):
    """Verifica se FK constraint ja existe."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = :nome AND constraint_type = 'FOREIGN KEY'
        )
    """), {'nome': nome_constraint})
    return result.scalar()


def run_migration():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()

        print("=" * 60)
        print("Migration: CarVia Linking v1 — Schema DDL")
        print("=" * 60)

        # ============================================================
        # 1A. ALTER TABLE carvia_fatura_cliente_itens
        # ============================================================
        print("\n--- 1A. ALTER TABLE carvia_fatura_cliente_itens ---")

        # Coluna operacao_id
        if not verificar_coluna_existe(conn, 'carvia_fatura_cliente_itens', 'operacao_id'):
            conn.execute(text("""
                ALTER TABLE carvia_fatura_cliente_itens
                ADD COLUMN operacao_id INTEGER
            """))
            print("  [OK] Coluna operacao_id adicionada")
        else:
            print("  [SKIP] Coluna operacao_id ja existe")

        # FK operacao_id
        if not verificar_fk_existe(conn, 'fk_fat_cli_itens_operacao'):
            conn.execute(text("""
                ALTER TABLE carvia_fatura_cliente_itens
                ADD CONSTRAINT fk_fat_cli_itens_operacao
                FOREIGN KEY (operacao_id) REFERENCES carvia_operacoes(id)
            """))
            print("  [OK] FK fk_fat_cli_itens_operacao criada")
        else:
            print("  [SKIP] FK fk_fat_cli_itens_operacao ja existe")

        # Indice operacao_id
        if not verificar_indice_existe(conn, 'ix_carvia_fat_cli_itens_operacao_id'):
            conn.execute(text("""
                CREATE INDEX ix_carvia_fat_cli_itens_operacao_id
                ON carvia_fatura_cliente_itens(operacao_id)
            """))
            print("  [OK] Indice ix_carvia_fat_cli_itens_operacao_id criado")
        else:
            print("  [SKIP] Indice ix_carvia_fat_cli_itens_operacao_id ja existe")

        # Coluna nf_id
        if not verificar_coluna_existe(conn, 'carvia_fatura_cliente_itens', 'nf_id'):
            conn.execute(text("""
                ALTER TABLE carvia_fatura_cliente_itens
                ADD COLUMN nf_id INTEGER
            """))
            print("  [OK] Coluna nf_id adicionada")
        else:
            print("  [SKIP] Coluna nf_id ja existe")

        # FK nf_id
        if not verificar_fk_existe(conn, 'fk_fat_cli_itens_nf'):
            conn.execute(text("""
                ALTER TABLE carvia_fatura_cliente_itens
                ADD CONSTRAINT fk_fat_cli_itens_nf
                FOREIGN KEY (nf_id) REFERENCES carvia_nfs(id)
            """))
            print("  [OK] FK fk_fat_cli_itens_nf criada")
        else:
            print("  [SKIP] FK fk_fat_cli_itens_nf ja existe")

        # Indice nf_id
        if not verificar_indice_existe(conn, 'ix_carvia_fat_cli_itens_nf_id'):
            conn.execute(text("""
                CREATE INDEX ix_carvia_fat_cli_itens_nf_id
                ON carvia_fatura_cliente_itens(nf_id)
            """))
            print("  [OK] Indice ix_carvia_fat_cli_itens_nf_id criado")
        else:
            print("  [SKIP] Indice ix_carvia_fat_cli_itens_nf_id ja existe")

        # ============================================================
        # 1B. CREATE TABLE carvia_fatura_transportadora_itens
        # ============================================================
        print("\n--- 1B. CREATE TABLE carvia_fatura_transportadora_itens ---")

        if not verificar_tabela_existe(conn, 'carvia_fatura_transportadora_itens'):
            conn.execute(text("""
                CREATE TABLE carvia_fatura_transportadora_itens (
                    id SERIAL PRIMARY KEY,
                    fatura_transportadora_id INTEGER NOT NULL
                        REFERENCES carvia_faturas_transportadora(id) ON DELETE CASCADE,
                    subcontrato_id INTEGER
                        REFERENCES carvia_subcontratos(id),
                    operacao_id INTEGER
                        REFERENCES carvia_operacoes(id),
                    nf_id INTEGER
                        REFERENCES carvia_nfs(id),
                    cte_numero VARCHAR(20),
                    cte_data_emissao DATE,
                    contraparte_cnpj VARCHAR(20),
                    contraparte_nome VARCHAR(255),
                    nf_numero VARCHAR(20),
                    valor_mercadoria NUMERIC(15,2),
                    peso_kg NUMERIC(15,3),
                    valor_frete NUMERIC(15,2),
                    valor_cotado NUMERIC(15,2),
                    valor_acertado NUMERIC(15,2),
                    criado_em TIMESTAMP DEFAULT NOW()
                )
            """))
            print("  [OK] Tabela carvia_fatura_transportadora_itens criada")

            # Indices
            for idx_name, idx_col in [
                ('ix_carvia_fat_transp_itens_fatura_id', 'fatura_transportadora_id'),
                ('ix_carvia_fat_transp_itens_subcontrato_id', 'subcontrato_id'),
                ('ix_carvia_fat_transp_itens_operacao_id', 'operacao_id'),
                ('ix_carvia_fat_transp_itens_nf_id', 'nf_id'),
            ]:
                conn.execute(text(f"""
                    CREATE INDEX {idx_name}
                    ON carvia_fatura_transportadora_itens({idx_col})
                """))
                print(f"  [OK] Indice {idx_name} criado")
        else:
            print("  [SKIP] Tabela carvia_fatura_transportadora_itens ja existe")

        # ============================================================
        # Verificacao final
        # ============================================================
        print("\n--- Verificacao final ---")

        # Verificar colunas em carvia_fatura_cliente_itens
        for col in ['operacao_id', 'nf_id']:
            existe = verificar_coluna_existe(conn, 'carvia_fatura_cliente_itens', col)
            status = 'OK' if existe else 'FALHA'
            print(f"  [{status}] carvia_fatura_cliente_itens.{col}")

        # Verificar tabela nova
        existe = verificar_tabela_existe(conn, 'carvia_fatura_transportadora_itens')
        status = 'OK' if existe else 'FALHA'
        print(f"  [{status}] carvia_fatura_transportadora_itens")

        # Contar colunas na tabela nova
        if existe:
            result = conn.execute(text("""
                SELECT count(*) FROM information_schema.columns
                WHERE table_name = 'carvia_fatura_transportadora_itens'
            """))
            qtd = result.scalar()
            print(f"  [INFO] carvia_fatura_transportadora_itens tem {qtd} colunas")

        db.session.commit()
        print("\n[SUCESSO] Migration concluida!")


if __name__ == '__main__':
    run_migration()
