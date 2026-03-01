-- Migration: CarVia Linking v1 — Schema DDL
-- Execucao: colar no Render Shell (PostgreSQL)
-- Idempotente: IF NOT EXISTS em todas as operacoes

-- ============================================================
-- 1A. ALTER TABLE carvia_fatura_cliente_itens
-- ============================================================

-- Coluna operacao_id
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_fatura_cliente_itens' AND column_name = 'operacao_id'
    ) THEN
        ALTER TABLE carvia_fatura_cliente_itens ADD COLUMN operacao_id INTEGER;
    END IF;
END $$;

-- FK operacao_id
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_fat_cli_itens_operacao'
    ) THEN
        ALTER TABLE carvia_fatura_cliente_itens
        ADD CONSTRAINT fk_fat_cli_itens_operacao
        FOREIGN KEY (operacao_id) REFERENCES carvia_operacoes(id);
    END IF;
END $$;

-- Indice operacao_id
CREATE INDEX IF NOT EXISTS ix_carvia_fat_cli_itens_operacao_id
ON carvia_fatura_cliente_itens(operacao_id);

-- Coluna nf_id
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_fatura_cliente_itens' AND column_name = 'nf_id'
    ) THEN
        ALTER TABLE carvia_fatura_cliente_itens ADD COLUMN nf_id INTEGER;
    END IF;
END $$;

-- FK nf_id
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_fat_cli_itens_nf'
    ) THEN
        ALTER TABLE carvia_fatura_cliente_itens
        ADD CONSTRAINT fk_fat_cli_itens_nf
        FOREIGN KEY (nf_id) REFERENCES carvia_nfs(id);
    END IF;
END $$;

-- Indice nf_id
CREATE INDEX IF NOT EXISTS ix_carvia_fat_cli_itens_nf_id
ON carvia_fatura_cliente_itens(nf_id);

-- ============================================================
-- 1B. CREATE TABLE carvia_fatura_transportadora_itens
-- ============================================================

CREATE TABLE IF NOT EXISTS carvia_fatura_transportadora_itens (
    id SERIAL PRIMARY KEY,
    fatura_transportadora_id INTEGER NOT NULL
        REFERENCES carvia_faturas_transportadora(id) ON DELETE CASCADE,
    subcontrato_id INTEGER
        REFERENCES carvia_subcontratos(id),
    operacao_id INTEGER
        REFERENCES carvia_operacoes(id),
    nf_id INTEGER
        REFERENCES carvia_nfs(id),
    cte_numero VARCHAR(20),
    cte_data_emissao DATE,
    contraparte_cnpj VARCHAR(20),
    contraparte_nome VARCHAR(255),
    nf_numero VARCHAR(20),
    valor_mercadoria NUMERIC(15,2),
    peso_kg NUMERIC(15,3),
    valor_frete NUMERIC(15,2),
    valor_cotado NUMERIC(15,2),
    valor_acertado NUMERIC(15,2),
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_carvia_fat_transp_itens_fatura_id
ON carvia_fatura_transportadora_itens(fatura_transportadora_id);

CREATE INDEX IF NOT EXISTS ix_carvia_fat_transp_itens_subcontrato_id
ON carvia_fatura_transportadora_itens(subcontrato_id);

CREATE INDEX IF NOT EXISTS ix_carvia_fat_transp_itens_operacao_id
ON carvia_fatura_transportadora_itens(operacao_id);

CREATE INDEX IF NOT EXISTS ix_carvia_fat_transp_itens_nf_id
ON carvia_fatura_transportadora_itens(nf_id);
