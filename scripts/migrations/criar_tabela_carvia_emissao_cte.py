#!/usr/bin/env python3
"""
Migration: Criar tabela carvia_emissao_cte

Controle de emissoes automaticas de CTe no SSW via Playwright.
Funcoes: mutex (evita dupla emissao), log de progresso, auditoria.

Uso:
    source .venv/bin/activate
    python scripts/migrations/criar_tabela_carvia_emissao_cte.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes():
    """Verifica estado antes da migration."""
    result = db.session.execute(db.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'carvia_emissao_cte'
        )
    """))
    existe = result.scalar()
    print(f"  Tabela carvia_emissao_cte existe: {existe}")
    return existe


def executar_migration():
    """Cria tabela carvia_emissao_cte."""
    db.session.execute(db.text("""
        CREATE TABLE carvia_emissao_cte (
            id SERIAL PRIMARY KEY,
            nf_id INTEGER NOT NULL REFERENCES carvia_nfs(id),
            operacao_id INTEGER REFERENCES carvia_operacoes(id),
            status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
            etapa VARCHAR(30),
            job_id VARCHAR(100),
            ctrc_numero VARCHAR(20),
            placa VARCHAR(20) NOT NULL DEFAULT 'ARMAZEM',
            cnpj_tomador VARCHAR(20),
            frete_valor NUMERIC(15,2),
            data_vencimento DATE,
            medidas_json JSONB,
            erro_ssw TEXT,
            resultado_json JSONB,
            fatura_numero VARCHAR(20),
            fatura_pdf_path VARCHAR(500),
            xml_path VARCHAR(500),
            dacte_path VARCHAR(500),
            criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
            criado_por VARCHAR(100) NOT NULL,
            atualizado_em TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_carvia_emissao_cte_status CHECK (
                status IN ('PENDENTE', 'EM_PROCESSAMENTO', 'SUCESSO', 'ERRO', 'CANCELADO')
            )
        )
    """))

    db.session.execute(db.text(
        "CREATE INDEX ix_carvia_emissao_cte_status ON carvia_emissao_cte(status)"
    ))
    db.session.execute(db.text(
        "CREATE INDEX ix_carvia_emissao_cte_nf_id ON carvia_emissao_cte(nf_id)"
    ))
    db.session.execute(db.text(
        "CREATE INDEX ix_carvia_emissao_cte_job_id ON carvia_emissao_cte(job_id)"
    ))

    db.session.commit()
    print("  Tabela carvia_emissao_cte criada com sucesso")


def verificar_depois():
    """Verifica estado apos a migration."""
    result = db.session.execute(db.text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'carvia_emissao_cte'
        ORDER BY ordinal_position
    """))
    colunas = result.fetchall()
    print(f"  Colunas criadas: {len(colunas)}")
    for col in colunas:
        print(f"    {col[0]}: {col[1]} (nullable={col[2]})")

    result_idx = db.session.execute(db.text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'carvia_emissao_cte'
    """))
    indices = result_idx.fetchall()
    print(f"  Indices: {len(indices)}")
    for idx in indices:
        print(f"    {idx[0]}")


def main():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("MIGRATION: Criar tabela carvia_emissao_cte")
        print("=" * 60)

        print("\n[BEFORE]")
        ja_existe = verificar_antes()

        if ja_existe:
            print("\n  Tabela ja existe — nada a fazer")
            print("=" * 60)
            return

        print("\n[EXECUTING]")
        executar_migration()

        print("\n[AFTER]")
        verificar_depois()

        print("\n" + "=" * 60)
        print("MIGRATION CONCLUIDA")
        print("=" * 60)


if __name__ == '__main__':
    main()
