-- Migration: Memoria Compartilhada por Escopo
-- Adiciona infraestrutura para memorias empresa (user_id=0)
-- Data: 2026-03-06
-- Ref: PRD v2.1 — Sistema de Memorias do Agent SDK

-- 1. Criar usuario Sistema (id=0) para memorias empresa
-- SERIAL em usuarios.id comeca em 1, id=0 nao conflita com sequencia
INSERT INTO usuarios (id, nome, email, senha_hash, perfil, status, criado_em)
SELECT 0, 'Sistema', 'sistema@nacom.com.br', 'NOLOGIN', 'sistema', 'ativo', NOW()
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE id = 0);

-- 2. Coluna escopo: 'pessoal' (default) ou 'empresa'
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agent_memories' AND column_name = 'escopo'
    ) THEN
        ALTER TABLE agent_memories ADD COLUMN escopo VARCHAR(20) NOT NULL DEFAULT 'pessoal';
    END IF;
END $$;

-- 3. Coluna created_by: quem originou a memoria empresa (auditoria)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agent_memories' AND column_name = 'created_by'
    ) THEN
        ALTER TABLE agent_memories ADD COLUMN created_by INTEGER;
    END IF;
END $$;

-- 4. FK para created_by (se nao existe)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_memory_created_by'
    ) THEN
        ALTER TABLE agent_memories
            ADD CONSTRAINT fk_memory_created_by
            FOREIGN KEY (created_by) REFERENCES usuarios(id) ON DELETE SET NULL;
    END IF;
END $$;

-- 5. Indice parcial para memorias empresa (otimiza busca user_id=0)
CREATE INDEX IF NOT EXISTS idx_agent_memories_escopo_empresa
    ON agent_memories (user_id, escopo) WHERE escopo = 'empresa';
