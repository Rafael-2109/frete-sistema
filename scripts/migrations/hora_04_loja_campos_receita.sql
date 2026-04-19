-- Migration HORA 04: expande hora_loja com campos da Receita + apelido
-- Data: 2026-04-18
-- Descricao:
--   Autopreenchimento via ReceitaWS (https://receitaws.com.br/v1/cnpj/{cnpj}).
--   Campo `apelido` e rotulo interno ("Motochefe Bragança") separado da razao social.
--   `nome` existente vira redundante com `razao_social`; mantido por compat.
-- Idempotente: ADD COLUMN IF NOT EXISTS.
-- RISCO: baixo. Somente ADD COLUMN nullable.

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS apelido VARCHAR(100);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS razao_social VARCHAR(200);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS nome_fantasia VARCHAR(200);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS logradouro VARCHAR(255);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS numero VARCHAR(20);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS complemento VARCHAR(100);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS bairro VARCHAR(100);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS cep VARCHAR(9);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS telefone VARCHAR(50);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS email VARCHAR(120);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS inscricao_estadual VARCHAR(30);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS situacao_cadastral VARCHAR(30);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS data_abertura DATE;

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS porte VARCHAR(50);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS natureza_juridica VARCHAR(255);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS atividade_principal VARCHAR(500);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS receitaws_consultado_em TIMESTAMP;

CREATE INDEX IF NOT EXISTS ix_hora_loja_apelido ON hora_loja (apelido);
