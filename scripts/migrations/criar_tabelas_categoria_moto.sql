-- Migration: Criar tabelas de categoria de moto para precificacao por unidade
-- Data: 2026-03-15
-- Descricao: Tabela de categorias de moto + precos por categoria por tabela + FK em modelos_moto
-- NOTA: Cada bloco verifica existencia da tabela-alvo antes de operar (idempotente)

-- 1. Tabela de categorias de moto
CREATE TABLE IF NOT EXISTS carvia_categorias_moto (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(50) NOT NULL UNIQUE,
    descricao TEXT,
    ordem INTEGER NOT NULL DEFAULT 0,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100) NOT NULL
);

-- 2. FK categoria em modelos de moto (somente se tabela carvia_modelos_moto existe)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'carvia_modelos_moto'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_modelos_moto'
        AND column_name = 'categoria_moto_id'
    ) THEN
        ALTER TABLE carvia_modelos_moto
            ADD COLUMN categoria_moto_id INTEGER
            REFERENCES carvia_categorias_moto(id);
    END IF;
END $$;

-- 3. Tabela de precos (somente se carvia_tabelas_frete existe)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'carvia_tabelas_frete'
    ) THEN
        CREATE TABLE IF NOT EXISTS carvia_precos_categoria_moto (
            id SERIAL PRIMARY KEY,
            tabela_frete_id INTEGER NOT NULL REFERENCES carvia_tabelas_frete(id) ON DELETE CASCADE,
            categoria_moto_id INTEGER NOT NULL REFERENCES carvia_categorias_moto(id) ON DELETE CASCADE,
            valor_unitario NUMERIC(15,2) NOT NULL,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            criado_por VARCHAR(100) NOT NULL,
            CONSTRAINT uq_carvia_preco_cat_moto UNIQUE (tabela_frete_id, categoria_moto_id)
        );
    END IF;
END $$;

-- 4. Indices (somente se tabelas existem)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'carvia_precos_categoria_moto') THEN
        CREATE INDEX IF NOT EXISTS ix_carvia_preco_cat_moto_tabela
            ON carvia_precos_categoria_moto(tabela_frete_id);
        CREATE INDEX IF NOT EXISTS ix_carvia_preco_cat_moto_cat
            ON carvia_precos_categoria_moto(categoria_moto_id);
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_modelos_moto' AND column_name = 'categoria_moto_id'
    ) THEN
        CREATE INDEX IF NOT EXISTS ix_carvia_modelos_moto_cat
            ON carvia_modelos_moto(categoria_moto_id);
    END IF;
END $$;
