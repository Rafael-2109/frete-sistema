-- Migration: Grupos de Analise customizados (selecao de categorias)
-- Idempotente — pode rodar multiplas vezes sem erro.

CREATE TABLE IF NOT EXISTS pessoal_grupos_analise (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    descricao VARCHAR(300),
    cor VARCHAR(20),
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pessoal_grupos_analise_categorias (
    grupo_id INTEGER NOT NULL
        REFERENCES pessoal_grupos_analise(id) ON DELETE CASCADE,
    categoria_id INTEGER NOT NULL
        REFERENCES pessoal_categorias(id) ON DELETE CASCADE,
    PRIMARY KEY (grupo_id, categoria_id)
);

CREATE INDEX IF NOT EXISTS idx_pessoal_gac_categoria
    ON pessoal_grupos_analise_categorias (categoria_id);
