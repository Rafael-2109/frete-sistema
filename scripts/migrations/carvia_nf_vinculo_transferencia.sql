-- Migration (2026-04-20) — CarviaNfVinculoTransferencia
-- Vinculo entre NF de Transferencia (intercompany, mesma raiz CNPJ) e
-- NF de Venda ao cliente final, para operacoes triangulares.
-- 1 NF transf pode alimentar N NFs venda (1:N). Cada NF venda tem no
-- maximo 1 NF transf vinculada (UNIQUE em nf_venda_id).
--
-- Uso Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/carvia_nf_vinculo_transferencia.sql

BEGIN;

CREATE TABLE IF NOT EXISTS carvia_nf_vinculos_transferencia (
    id                          SERIAL PRIMARY KEY,
    nf_transferencia_id         INTEGER NOT NULL
                                REFERENCES carvia_nfs(id) ON DELETE RESTRICT,
    nf_venda_id                 INTEGER NOT NULL
                                REFERENCES carvia_nfs(id) ON DELETE CASCADE,
    peso_bruto_venda_snapshot   NUMERIC(15, 3),
    peso_bruto_transf_snapshot  NUMERIC(15, 3),
    vinculado_retroativamente   BOOLEAN NOT NULL DEFAULT FALSE,
    contexto_retroativo         TEXT,
    criado_em                   TIMESTAMP NOT NULL
                                DEFAULT (NOW() AT TIME ZONE 'UTC'),
    criado_por                  VARCHAR(100) NOT NULL,
    CONSTRAINT uq_nfvt_venda_unico     UNIQUE (nf_venda_id),
    CONSTRAINT ck_nfvt_nf_distintas    CHECK (nf_transferencia_id != nf_venda_id)
);

CREATE INDEX IF NOT EXISTS ix_nfvt_transf
    ON carvia_nf_vinculos_transferencia (nf_transferencia_id);
CREATE INDEX IF NOT EXISTS ix_nfvt_venda
    ON carvia_nf_vinculos_transferencia (nf_venda_id);
CREATE INDEX IF NOT EXISTS ix_nfvt_criado_em
    ON carvia_nf_vinculos_transferencia (criado_em);

COMMIT;
