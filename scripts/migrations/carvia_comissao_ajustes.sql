-- CarVia — Comissoes: ajustes (debito/credito) + vinculo de vendedor
-- Idempotente. Spec: docs/superpowers/specs/2026-06-15-carvia-comissao-ajustes-design.md
--
-- (1) Colunas novas em carvia_comissao_fechamentos:
--       vendedor_usuario_id (FK usuarios) + total_ajustes
-- (2) Tabela carvia_comissao_ajustes (delta de comissao por CTe alterado/cancelado)
-- (3) Backfill vendedor_usuario_id por e-mail (lower-match)

-- (1) Colunas no fechamento
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='carvia_comissao_fechamentos' AND column_name='vendedor_usuario_id'
    ) THEN
        ALTER TABLE carvia_comissao_fechamentos
            ADD COLUMN vendedor_usuario_id INTEGER REFERENCES usuarios(id);
        CREATE INDEX IF NOT EXISTS ix_carvia_comissao_fechamentos_vendedor_usuario_id
            ON carvia_comissao_fechamentos (vendedor_usuario_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='carvia_comissao_fechamentos' AND column_name='total_ajustes'
    ) THEN
        ALTER TABLE carvia_comissao_fechamentos
            ADD COLUMN total_ajustes NUMERIC(15,2) NOT NULL DEFAULT 0;
    END IF;
END $$;

-- (2) Tabela de ajustes (idempotente)
CREATE TABLE IF NOT EXISTS carvia_comissao_ajustes (
    id SERIAL PRIMARY KEY,
    operacao_id INTEGER NOT NULL REFERENCES carvia_operacoes(id),
    fechamento_origem_id INTEGER NOT NULL REFERENCES carvia_comissao_fechamentos(id),
    vendedor_usuario_id INTEGER REFERENCES usuarios(id),
    vendedor_nome VARCHAR(100) NOT NULL,
    vendedor_email VARCHAR(150),
    motivo VARCHAR(20) NOT NULL,
    cte_numero VARCHAR(20) NOT NULL,
    valor_cte_anterior NUMERIC(15,2) NOT NULL,
    valor_cte_novo NUMERIC(15,2) NOT NULL,
    percentual_snapshot NUMERIC(10,8) NOT NULL,
    delta_comissao NUMERIC(15,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    fechamento_aplicado_id INTEGER REFERENCES carvia_comissao_fechamentos(id) ON DELETE SET NULL,
    criado_por VARCHAR(100) NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo'),
    aplicado_em TIMESTAMP,
    observacoes TEXT,
    CONSTRAINT ck_comissao_ajuste_status CHECK (status IN ('PENDENTE','APLICADO','CANCELADO')),
    CONSTRAINT ck_comissao_ajuste_motivo CHECK (motivo IN ('ALTERACAO_VALOR','CANCELAMENTO_CTE'))
);

CREATE INDEX IF NOT EXISTS ix_comissao_ajuste_vend_status
    ON carvia_comissao_ajustes (vendedor_usuario_id, status);
CREATE INDEX IF NOT EXISTS ix_carvia_comissao_ajustes_operacao_id
    ON carvia_comissao_ajustes (operacao_id);
CREATE INDEX IF NOT EXISTS ix_carvia_comissao_ajustes_fechamento_origem_id
    ON carvia_comissao_ajustes (fechamento_origem_id);
CREATE INDEX IF NOT EXISTS ix_carvia_comissao_ajustes_status
    ON carvia_comissao_ajustes (status);

-- (3) Backfill vendedor_usuario_id por e-mail (idempotente)
UPDATE carvia_comissao_fechamentos f
SET vendedor_usuario_id = u.id
FROM usuarios u
WHERE f.vendedor_email IS NOT NULL
  AND lower(f.vendedor_email) = lower(u.email)
  AND f.vendedor_usuario_id IS NULL;
