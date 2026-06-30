-- ==============================================
-- Pessoal — Caso 1 (Pix no Credito) + Caso 2 (regra por conta)
--
-- C2: contas_ids como condicao por conta de destino na regra de categorizacao.
-- C1: eh_pix_credito + pix_credito_grupo para marcar/agrupar as pernas do trio.
--
-- Idempotente: ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS.
-- ==============================================

-- C2: condicao por conta de destino (JSON array de PessoalConta.id; NULL = qualquer conta)
ALTER TABLE pessoal_regras_categorizacao
    ADD COLUMN IF NOT EXISTS contas_ids TEXT;

-- C1: marcadores do "Pix no Credito" do Nubank
ALTER TABLE pessoal_transacoes
    ADD COLUMN IF NOT EXISTS eh_pix_credito BOOLEAN DEFAULT FALSE;

ALTER TABLE pessoal_transacoes
    ADD COLUMN IF NOT EXISTS pix_credito_grupo VARCHAR(40);

-- Agrupamento das pernas de uma operacao (auditoria/reversao do split)
CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_pix_credito_grupo
    ON pessoal_transacoes(pix_credito_grupo)
    WHERE pix_credito_grupo IS NOT NULL;

-- Verificar resultado
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE (table_name = 'pessoal_regras_categorizacao' AND column_name = 'contas_ids')
   OR (table_name = 'pessoal_transacoes' AND column_name IN ('eh_pix_credito', 'pix_credito_grupo'))
ORDER BY table_name, column_name;
