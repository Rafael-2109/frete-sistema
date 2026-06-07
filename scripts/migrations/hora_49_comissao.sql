-- Migration HORA 49: Comissao de vendas (roadmap #28, Fatia 1 — cadastro).
-- Idempotente. Rodar no Render Shell.

-- 1) Config global (singleton id=1): comissao base por moto (valor unico).
CREATE TABLE IF NOT EXISTS hora_comissao_config (
    id                  SERIAL PRIMARY KEY,
    comissao_base_moto  NUMERIC(15, 2) NOT NULL DEFAULT 0,
    atualizado_em       TIMESTAMP NOT NULL,
    atualizado_por      VARCHAR(100)
);

-- 2) Faixas de valor de desconto (R$) na moto -> reducao da comissao (R$).
CREATE TABLE IF NOT EXISTS hora_comissao_faixa_desconto (
    id                  SERIAL PRIMARY KEY,
    desconto_min        NUMERIC(15, 2) NOT NULL DEFAULT 0,
    desconto_max        NUMERIC(15, 2),
    reducao_comissao    NUMERIC(15, 2) NOT NULL DEFAULT 0,
    ativo               BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em           TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hora_comissao_faixa_ativo ON hora_comissao_faixa_desconto (ativo);

-- 3) Comissao por peca (por unidade vendida).
ALTER TABLE hora_peca
    ADD COLUMN IF NOT EXISTS valor_comissao NUMERIC(15, 2) NOT NULL DEFAULT 0;

-- 4) Teto de desconto (R$) por modelo. NULL = sem teto.
ALTER TABLE hora_modelo
    ADD COLUMN IF NOT EXISTS desconto_maximo NUMERIC(15, 2);
