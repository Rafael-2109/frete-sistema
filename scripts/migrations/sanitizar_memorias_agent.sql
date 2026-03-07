-- Migration: Sanitizacao de Memorias do Agente Web
-- Ref: Auditoria Sistema de Memoria v5.0 — 07/03/2026
-- Uso: Render Shell (psql) — SQL idempotente, pode rodar multiplas vezes
--
-- IMPORTANTE: Rodar DENTRO de transacao (BEGIN/COMMIT)

BEGIN;

-- Contagem BEFORE
SELECT 'BEFORE' AS fase,
       (SELECT COUNT(*) FROM agent_memories) AS total,
       (SELECT COUNT(*) FROM agent_memories WHERE is_directory = true) AS dirs,
       (SELECT COUNT(*) FROM agent_memories WHERE user_id = 0) AS empresa;

-- 1. Deletar diretorios vazios
DELETE FROM agent_memories WHERE is_directory = true;

-- 2. Deletar meta-junk (IDs confirmados na auditoria)
DELETE FROM agent_memories WHERE id IN (
    113, 114, 116, 117, 118, 119, 120, 121,
    126, 127, 128, 130, 131, 132, 133, 134, 135, 140,
    144, 147, 148
);

-- 3. Deletar duplicatas
DELETE FROM agent_memories WHERE id IN (142, 143, 145, 146);

-- 4. Migrar admin corrections para escopo empresa
-- 4a. Preservar conteudo da primeira copia de cada correction
DO $$
DECLARE
    correction_path TEXT;
    correction_paths TEXT[] := ARRAY[
        '/memories/corrections/agent-sdk-production-scope.xml',
        '/memories/corrections/capacidade-caminhoes-consultar-veiculos.xml',
        '/memories/corrections/confirmar-para-pedido-odoo.xml'
    ];
    v_content TEXT;
    v_created_at TIMESTAMP;
BEGIN
    FOREACH correction_path IN ARRAY correction_paths LOOP
        -- Capturar conteudo de uma copia
        SELECT content, created_at INTO v_content, v_created_at
        FROM agent_memories
        WHERE path = correction_path
        ORDER BY id LIMIT 1;

        IF v_content IS NOT NULL THEN
            -- Deletar TODAS as copias
            DELETE FROM agent_memories WHERE path = correction_path;

            -- Criar versao empresa (user_id=0)
            INSERT INTO agent_memories (
                user_id, path, content, is_directory, escopo, created_by,
                importance_score, category, created_at, updated_at
            ) VALUES (
                0, correction_path, v_content, false, 'empresa', NULL,
                0.9, 'permanent', v_created_at, v_created_at
            );

            RAISE NOTICE 'Migrated: %', correction_path;
        END IF;
    END LOOP;
END $$;

-- 5. Limpar embeddings orfaos
DELETE FROM agent_memory_embeddings
WHERE memory_id IS NOT NULL
  AND memory_id NOT IN (SELECT id FROM agent_memories);

-- Contagem AFTER
SELECT 'AFTER' AS fase,
       (SELECT COUNT(*) FROM agent_memories) AS total,
       (SELECT COUNT(*) FROM agent_memories WHERE is_directory = true) AS dirs,
       (SELECT COUNT(*) FROM agent_memories WHERE user_id = 0) AS empresa;

COMMIT;
