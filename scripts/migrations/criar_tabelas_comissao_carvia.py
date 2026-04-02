"""
Migration: Criar tabelas de comissao CarVia
===========================================
- carvia_comissao_fechamentos
- carvia_comissao_fechamento_ctes

Executar: python scripts/migrations/criar_tabelas_comissao_carvia.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def check_table_exists(table_name):
    """Verifica se tabela ja existe."""
    result = db.session.execute(
        db.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :t)"
        ),
        {'t': table_name},
    )
    return result.scalar()


def run_migration():
    app = create_app()
    with app.app_context():
        # ------ BEFORE ------
        t1_exists = check_table_exists('carvia_comissao_fechamentos')
        t2_exists = check_table_exists('carvia_comissao_fechamento_ctes')
        print(f"[BEFORE] carvia_comissao_fechamentos existe: {t1_exists}")
        print(f"[BEFORE] carvia_comissao_fechamento_ctes existe: {t2_exists}")

        if t1_exists and t2_exists:
            print("[SKIP] Ambas tabelas ja existem. Nada a fazer.")
            return

        # ------ DDL ------
        if not t1_exists:
            db.session.execute(db.text("""
                CREATE TABLE carvia_comissao_fechamentos (
                    id SERIAL PRIMARY KEY,
                    numero_fechamento VARCHAR(20) NOT NULL UNIQUE,
                    vendedor_nome VARCHAR(100) NOT NULL,
                    vendedor_email VARCHAR(150),
                    data_inicio DATE NOT NULL,
                    data_fim DATE NOT NULL,
                    percentual NUMERIC(5, 4) NOT NULL,
                    qtd_ctes INTEGER NOT NULL DEFAULT 0,
                    total_bruto NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    total_comissao NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
                    pago_por VARCHAR(100),
                    pago_em TIMESTAMP,
                    data_pagamento DATE,
                    observacoes TEXT,
                    criado_por VARCHAR(100) NOT NULL,
                    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                    atualizado_em TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT ck_comissao_periodo_valido CHECK (data_inicio <= data_fim),
                    CONSTRAINT ck_comissao_percentual_range CHECK (percentual > 0 AND percentual <= 1),
                    CONSTRAINT ck_comissao_status_valido CHECK (status IN ('PENDENTE', 'PAGO', 'CANCELADO'))
                )
            """))
            print("[OK] Tabela carvia_comissao_fechamentos criada.")

            # Indices
            db.session.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_comissao_fechamentos_status "
                "ON carvia_comissao_fechamentos (status)"
            ))
            db.session.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_comissao_fechamentos_data_inicio "
                "ON carvia_comissao_fechamentos (data_inicio)"
            ))
            db.session.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_comissao_fechamentos_vendedor "
                "ON carvia_comissao_fechamentos (vendedor_email)"
            ))
            print("[OK] Indices de carvia_comissao_fechamentos criados.")

        if not t2_exists:
            db.session.execute(db.text("""
                CREATE TABLE carvia_comissao_fechamento_ctes (
                    id SERIAL PRIMARY KEY,
                    fechamento_id INTEGER NOT NULL
                        REFERENCES carvia_comissao_fechamentos(id) ON DELETE CASCADE,
                    operacao_id INTEGER NOT NULL
                        REFERENCES carvia_operacoes(id),
                    cte_numero VARCHAR(20) NOT NULL,
                    cte_data_emissao DATE NOT NULL,
                    valor_cte_snapshot NUMERIC(15, 2) NOT NULL,
                    percentual_snapshot NUMERIC(5, 4) NOT NULL,
                    valor_comissao NUMERIC(15, 2) NOT NULL,
                    excluido BOOLEAN NOT NULL DEFAULT FALSE,
                    excluido_em TIMESTAMP,
                    excluido_por VARCHAR(100),
                    incluido_por VARCHAR(100) NOT NULL,
                    incluido_em TIMESTAMP NOT NULL DEFAULT NOW(),
                    CONSTRAINT uq_comissao_fechamento_operacao
                        UNIQUE (fechamento_id, operacao_id)
                )
            """))
            print("[OK] Tabela carvia_comissao_fechamento_ctes criada.")

            # Indices
            db.session.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_comissao_fctes_fechamento_id "
                "ON carvia_comissao_fechamento_ctes (fechamento_id)"
            ))
            db.session.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_comissao_fctes_operacao_id "
                "ON carvia_comissao_fechamento_ctes (operacao_id)"
            ))
            db.session.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_comissao_fctes_excluido "
                "ON carvia_comissao_fechamento_ctes (fechamento_id, excluido)"
            ))
            print("[OK] Indices de carvia_comissao_fechamento_ctes criados.")

        db.session.commit()

        # ------ AFTER ------
        t1_now = check_table_exists('carvia_comissao_fechamentos')
        t2_now = check_table_exists('carvia_comissao_fechamento_ctes')
        print(f"[AFTER] carvia_comissao_fechamentos existe: {t1_now}")
        print(f"[AFTER] carvia_comissao_fechamento_ctes existe: {t2_now}")
        print("[DONE] Migration concluida com sucesso.")


if __name__ == '__main__':
    run_migration()
