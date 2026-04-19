-- ==============================================
-- Features F1 (CPF/CNPJ), F2 (parcela), F4 (valor como condicao)
-- em regras de categorizacao do modulo Pessoal.
--
-- Idempotente: usa IF NOT EXISTS / DO $$ blocks para ALTER TABLE.
-- ==============================================

-- F1: CPF/CNPJ extraido do historico (so digitos, sem pontuacao)
ALTER TABLE pessoal_transacoes
    ADD COLUMN IF NOT EXISTS cpf_cnpj_parte VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_cpf_cnpj
    ON pessoal_transacoes(cpf_cnpj_parte)
    WHERE cpf_cnpj_parte IS NOT NULL;

-- F1: CPF/CNPJ como padrao de match alternativo na regra
ALTER TABLE pessoal_regras_categorizacao
    ADD COLUMN IF NOT EXISTS cpf_cnpj_padrao VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_pessoal_regras_cpf_cnpj
    ON pessoal_regras_categorizacao(cpf_cnpj_padrao)
    WHERE cpf_cnpj_padrao IS NOT NULL;

-- F4: Condicao por valor (NULL = sem restricao)
ALTER TABLE pessoal_regras_categorizacao
    ADD COLUMN IF NOT EXISTS valor_min NUMERIC(15, 2);

ALTER TABLE pessoal_regras_categorizacao
    ADD COLUMN IF NOT EXISTS valor_max NUMERIC(15, 2);

-- Verificar resultado
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name IN ('pessoal_transacoes', 'pessoal_regras_categorizacao')
  AND column_name IN ('cpf_cnpj_parte', 'cpf_cnpj_padrao', 'valor_min', 'valor_max')
ORDER BY table_name, column_name;
