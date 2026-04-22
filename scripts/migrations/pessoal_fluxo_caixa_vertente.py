"""Migration: vertente Fluxo de Caixa do modulo Pessoal.

Adiciona:
- pessoal_importacoes.data_pagamento (DATE, nullable) — data em que a fatura foi paga
- pessoal_importacoes.transacao_pagamento_id (FK -> pessoal_transacoes, nullable)
  Vinculo inverso: fatura PAGA -> transacao de pagamento na CC.
- Tabela pessoal_provisoes (forecast manual de entradas/saidas futuras)
- Seed: categoria 'Cartao de Credito' no grupo 'Financeiro' (agrupa pagamentos de fatura
  na vertente fluxo de caixa, com drilldown para compras)

Idempotente (usa IF NOT EXISTS).
"""
from app import create_app, db
from sqlalchemy import text


def main():
    app = create_app()
    with app.app_context():
        print('[*] Iniciando migration pessoal_fluxo_caixa_vertente...')

        # =====================================================================
        # 1. pessoal_importacoes: data_pagamento + transacao_pagamento_id
        # =====================================================================
        db.session.execute(text("""
            ALTER TABLE pessoal_importacoes
            ADD COLUMN IF NOT EXISTS data_pagamento DATE
        """))
        db.session.execute(text("""
            ALTER TABLE pessoal_importacoes
            ADD COLUMN IF NOT EXISTS transacao_pagamento_id INTEGER
        """))
        db.session.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE constraint_name = 'fk_imp_transacao_pagamento'
                      AND table_name = 'pessoal_importacoes'
                ) THEN
                    ALTER TABLE pessoal_importacoes
                    ADD CONSTRAINT fk_imp_transacao_pagamento
                    FOREIGN KEY (transacao_pagamento_id)
                    REFERENCES pessoal_transacoes(id) ON DELETE SET NULL;
                END IF;
            END$$;
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pessoal_imp_data_pagamento
            ON pessoal_importacoes (data_pagamento)
            WHERE data_pagamento IS NOT NULL
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pessoal_imp_transacao_pagamento
            ON pessoal_importacoes (transacao_pagamento_id)
            WHERE transacao_pagamento_id IS NOT NULL
        """))
        print('[OK] pessoal_importacoes.data_pagamento + transacao_pagamento_id')

        # =====================================================================
        # 2. Tabela pessoal_provisoes
        # =====================================================================
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS pessoal_provisoes (
                id SERIAL PRIMARY KEY,
                tipo VARCHAR(10) NOT NULL,
                data_prevista DATE NOT NULL,
                valor NUMERIC(15, 2) NOT NULL,
                descricao VARCHAR(300) NOT NULL,
                categoria_id INTEGER REFERENCES pessoal_categorias(id) ON DELETE SET NULL,
                membro_id INTEGER REFERENCES pessoal_membros(id) ON DELETE SET NULL,
                conta_id INTEGER REFERENCES pessoal_contas(id) ON DELETE SET NULL,
                orcamento_id INTEGER REFERENCES pessoal_orcamentos(id) ON DELETE SET NULL,
                transacao_id INTEGER REFERENCES pessoal_transacoes(id) ON DELETE SET NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'PROVISIONADA',
                recorrente BOOLEAN DEFAULT FALSE,
                recorrencia_tipo VARCHAR(20),
                recorrencia_ate DATE,
                observacao TEXT,
                criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                atualizado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                criado_por VARCHAR(100),
                realizado_em TIMESTAMP,
                CONSTRAINT ck_provisoes_tipo CHECK (tipo IN ('entrada', 'saida')),
                CONSTRAINT ck_provisoes_status CHECK (
                    status IN ('PROVISIONADA', 'REALIZADA', 'CANCELADA')
                ),
                CONSTRAINT ck_provisoes_valor_positivo CHECK (valor > 0),
                CONSTRAINT ck_provisoes_recorrencia_tipo CHECK (
                    recorrencia_tipo IS NULL
                    OR recorrencia_tipo IN ('mensal', 'semanal', 'anual')
                )
            )
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pessoal_provisoes_data
            ON pessoal_provisoes (data_prevista)
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pessoal_provisoes_status
            ON pessoal_provisoes (status)
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pessoal_provisoes_tipo
            ON pessoal_provisoes (tipo)
        """))
        print('[OK] pessoal_provisoes criada')

        # =====================================================================
        # 3. Seed: categoria 'Cartao de Credito' (grupo Financeiro)
        # =====================================================================
        db.session.execute(text("""
            INSERT INTO pessoal_categorias (nome, grupo, icone, ativa, criado_em)
            VALUES ('Cartao de Credito', 'Financeiro', 'fa-credit-card', TRUE, NOW())
            ON CONFLICT ON CONSTRAINT uq_pessoal_categorias_grupo_nome DO NOTHING
        """))
        print("[OK] Categoria 'Cartao de Credito' (grupo Financeiro) seed")

        db.session.commit()
        print('[OK] Migration concluida.')

        # =====================================================================
        # Verificacao
        # =====================================================================
        n_data = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name='pessoal_importacoes' AND column_name='data_pagamento'"
        )).scalar()
        n_fk = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name='pessoal_importacoes' AND column_name='transacao_pagamento_id'"
        )).scalar()
        n_prov = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name='pessoal_provisoes'"
        )).scalar()
        n_cat = db.session.execute(text(
            "SELECT COUNT(*) FROM pessoal_categorias "
            "WHERE grupo='Financeiro' AND nome='Cartao de Credito'"
        )).scalar()
        print(f'[VERIFY] importacoes.data_pagamento: {n_data}/1')
        print(f'[VERIFY] importacoes.transacao_pagamento_id: {n_fk}/1')
        print(f'[VERIFY] tabela pessoal_provisoes: {n_prov}/1')
        print(f"[VERIFY] categoria 'Cartao de Credito': {n_cat}/1")


if __name__ == '__main__':
    main()
