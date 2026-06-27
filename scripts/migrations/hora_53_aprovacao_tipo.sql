-- Idempotente. Generaliza a fila de aprovacao de desconto para 3 gatilhos
-- (DESCONTO/FRETE/BRINDE) — #5b (2026-06-26). Adiciona a coluna `tipo`; as
-- linhas legadas recebem DESCONTO via DEFAULT. Migration HORA 53.
ALTER TABLE hora_aprovacao_desconto
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'DESCONTO';

CREATE INDEX IF NOT EXISTS ix_hora_aprovacao_desconto_tipo
    ON hora_aprovacao_desconto (tipo);
