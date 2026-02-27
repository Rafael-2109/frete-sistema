-- Migration: Criar tabela carvia_nf_itens
-- Itens de produto das NFs importadas (DANFE PDF ou XML NF-e)
-- Executar via Render Shell: psql $DATABASE_URL < criar_tabela_carvia_nf_itens.sql

CREATE TABLE IF NOT EXISTS carvia_nf_itens (
    id SERIAL PRIMARY KEY,
    nf_id INTEGER NOT NULL REFERENCES carvia_nfs(id),

    -- Produto
    codigo_produto VARCHAR(60),
    descricao VARCHAR(255),
    ncm VARCHAR(10),
    cfop VARCHAR(10),

    -- Quantidades e valores
    unidade VARCHAR(10),
    quantidade NUMERIC(15, 4),
    valor_unitario NUMERIC(15, 4),
    valor_total_item NUMERIC(15, 2),

    -- Auditoria (Brasil naive — sem timezone)
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_carvia_nf_itens_nf_id
ON carvia_nf_itens(nf_id);
