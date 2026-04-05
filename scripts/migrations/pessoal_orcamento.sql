-- Migration: Adicionar tabela pessoal_orcamentos + remover coluna ordem_exibicao
-- Executar via Render Shell (SQL idempotente)

-- 1. Criar tabela pessoal_orcamentos
CREATE TABLE IF NOT EXISTS pessoal_orcamentos (
    id SERIAL PRIMARY KEY,
    ano_mes DATE NOT NULL,
    categoria_id INTEGER REFERENCES pessoal_categorias(id),
    valor_limite NUMERIC(15,2) NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Unique constraint: um registro por mes/categoria (NULL = global)
-- Postgres trata NULLs como distintos em UNIQUE, entao usamos partial indexes
CREATE UNIQUE INDEX IF NOT EXISTS uq_pessoal_orcamentos_mes_categoria
    ON pessoal_orcamentos (ano_mes, categoria_id)
    WHERE categoria_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_pessoal_orcamentos_mes_global
    ON pessoal_orcamentos (ano_mes)
    WHERE categoria_id IS NULL;

-- 2. Remover coluna ordem_exibicao de pessoal_categorias
ALTER TABLE pessoal_categorias DROP COLUMN IF EXISTS ordem_exibicao;
