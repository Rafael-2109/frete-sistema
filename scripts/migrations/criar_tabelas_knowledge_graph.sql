-- ==========================================================================
-- T3-3: Knowledge Graph Simplificado — SQL idempotente para Render Shell
--
-- Cria 3 tabelas + índices para o knowledge graph de memórias do agente.
-- Executar via Render Shell: psql -f criar_tabelas_knowledge_graph.sql
-- ==========================================================================

-- 1. Tabela de entidades (nós do grafo)
CREATE TABLE IF NOT EXISTS agent_memory_entities (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    entity_type VARCHAR(30) NOT NULL,    -- 'cliente', 'transportadora', 'produto', 'uf', 'pedido', etc.
    entity_name VARCHAR(200) NOT NULL,   -- Nome normalizado (uppercase, sem acentos)
    entity_key VARCHAR(100),             -- ID canônico opcional (CNPJ raiz, cod_produto, UF)
    mention_count INTEGER NOT NULL DEFAULT 1,
    first_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_entity UNIQUE(user_id, entity_type, entity_name)
);

-- 2. Tabela de links (entidade <-> memória)
CREATE TABLE IF NOT EXISTS agent_memory_entity_links (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES agent_memory_entities(id) ON DELETE CASCADE,
    memory_id INTEGER NOT NULL REFERENCES agent_memories(id) ON DELETE CASCADE,
    relation_type VARCHAR(30) NOT NULL DEFAULT 'mentions',  -- 'mentions', 'corrects', 'prefers'
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_entity_memory_link UNIQUE(entity_id, memory_id, relation_type)
);

-- 3. Tabela de relações (entidade <-> entidade)
CREATE TABLE IF NOT EXISTS agent_memory_entity_relations (
    id SERIAL PRIMARY KEY,
    source_entity_id INTEGER NOT NULL REFERENCES agent_memory_entities(id) ON DELETE CASCADE,
    target_entity_id INTEGER NOT NULL REFERENCES agent_memory_entities(id) ON DELETE CASCADE,
    relation_type VARCHAR(50) NOT NULL DEFAULT 'co_occurs',  -- 'co_occurs', 'atrasa_para', 'melhor_para', etc.
    weight FLOAT NOT NULL DEFAULT 1.0,
    memory_id INTEGER REFERENCES agent_memories(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_entity_relation UNIQUE(source_entity_id, target_entity_id, relation_type)
);

-- 4. Índices
CREATE INDEX IF NOT EXISTS idx_ame_user_type ON agent_memory_entities(user_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_ame_entity_key ON agent_memory_entities(entity_key) WHERE entity_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_amel_entity ON agent_memory_entity_links(entity_id);
CREATE INDEX IF NOT EXISTS idx_amel_memory ON agent_memory_entity_links(memory_id);
CREATE INDEX IF NOT EXISTS idx_amer_source ON agent_memory_entity_relations(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_amer_target ON agent_memory_entity_relations(target_entity_id);
