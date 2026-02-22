-- Migration: Criar tabela route_template_embeddings
-- Indexação semântica de rotas e templates do sistema
--
-- Executar no Render Shell:
--   psql $DATABASE_URL -f criar_tabela_route_template_embeddings.sql

-- Extensão pgvector (já deve existir)
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabela principal
CREATE TABLE IF NOT EXISTS route_template_embeddings (
    id SERIAL PRIMARY KEY,

    -- Identificação
    tipo VARCHAR(20) NOT NULL,              -- 'rota_template', 'rota_api'
    blueprint_name VARCHAR(100) NOT NULL,
    function_name VARCHAR(200) NOT NULL,

    -- Rota
    url_path VARCHAR(500) NOT NULL,
    http_methods VARCHAR(50) NOT NULL,      -- "GET,POST"

    -- Template (nullable para rotas API)
    template_path VARCHAR(500),

    -- Navegação
    menu_path TEXT,                          -- "Financeiro > Contas a Pagar"
    permission_decorator VARCHAR(200),

    -- Metadados
    source_file VARCHAR(500) NOT NULL,
    source_line INTEGER,
    docstring TEXT,
    ajax_endpoints TEXT,                    -- JSON: URLs AJAX consumidas pelo template

    -- Embedding
    texto_embedado TEXT NOT NULL,
    embedding vector(1024),
    model_used VARCHAR(50),
    content_hash VARCHAR(32),               -- MD5 para detectar mudanças

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraint única: um blueprint não pode ter duas funções com mesmo nome
    CONSTRAINT uq_route_blueprint_function UNIQUE (blueprint_name, function_name)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_rte_tipo ON route_template_embeddings (tipo);
CREATE INDEX IF NOT EXISTS idx_rte_template_path ON route_template_embeddings (template_path);
CREATE INDEX IF NOT EXISTS idx_rte_content_hash ON route_template_embeddings (content_hash);

-- Índice HNSW para busca semântica por similaridade de cosseno
CREATE INDEX IF NOT EXISTS idx_rte_embedding_hnsw
    ON route_template_embeddings USING hnsw (embedding vector_cosine_ops);
