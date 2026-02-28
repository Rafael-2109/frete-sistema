-- Migration: Novos campos em carvia_faturas_cliente + tabela carvia_fatura_cliente_itens
-- ======================================================================================
--
-- Execucao (Render Shell):
--   psql $DATABASE_URL -f scripts/migrations/adicionar_campos_fatura_cliente_v2.sql
--
-- Idempotente: IF NOT EXISTS em todas as operacoes.

-- 1. Novos campos em carvia_faturas_cliente
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS tipo_frete VARCHAR(10);
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS quantidade_documentos INTEGER;
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS valor_mercadoria NUMERIC(15,2);
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS valor_icms NUMERIC(15,2);
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS aliquota_icms VARCHAR(20);
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS valor_pedagio NUMERIC(15,2);
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS vencimento_original DATE;
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS cancelada BOOLEAN DEFAULT FALSE;
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS pagador_endereco VARCHAR(500);
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS pagador_cep VARCHAR(10);
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS pagador_cidade VARCHAR(100);
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS pagador_uf VARCHAR(2);
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS pagador_ie VARCHAR(20);
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS pagador_telefone VARCHAR(30);

-- 2. Nova tabela carvia_fatura_cliente_itens
CREATE TABLE IF NOT EXISTS carvia_fatura_cliente_itens (
    id SERIAL PRIMARY KEY,
    fatura_cliente_id INTEGER NOT NULL REFERENCES carvia_faturas_cliente(id) ON DELETE CASCADE,
    cte_numero VARCHAR(20),
    cte_data_emissao DATE,
    contraparte_cnpj VARCHAR(20),
    contraparte_nome VARCHAR(255),
    nf_numero VARCHAR(20),
    valor_mercadoria NUMERIC(15,2),
    peso_kg NUMERIC(15,3),
    base_calculo NUMERIC(15,2),
    icms NUMERIC(15,2),
    iss NUMERIC(15,2),
    st NUMERIC(15,2),
    frete NUMERIC(15,2),
    criado_em TIMESTAMP DEFAULT NOW()
);

-- 3. Indice
CREATE INDEX IF NOT EXISTS idx_fatura_cliente_itens_fatura
ON carvia_fatura_cliente_itens(fatura_cliente_id);
