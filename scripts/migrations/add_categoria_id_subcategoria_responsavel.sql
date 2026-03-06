-- Migration: Adicionar categoria_id em ocorrencia_subcategoria e ocorrencia_responsavel
-- =====================================================================================
-- Vincula subcategorias e responsaveis como filhos de categoria.
-- Registros existentes sao vinculados a COMERCIAL (id=2).
-- Registros "Teste"/"teste" sao removidos (sem referencias).
--
-- SQL idempotente para Render Shell
-- Criado em: 06/03/2026 | Corrigido: 06/03/2026

-- =====================================================================
-- PASSO 1: Limpar registros de teste (sem referencias em juncao)
-- =====================================================================
DELETE FROM ocorrencia_devolucao_subcategoria WHERE subcategoria_id = 1;
DELETE FROM ocorrencia_subcategoria WHERE id = 1 AND codigo = 'TESTE';

DELETE FROM ocorrencia_devolucao_categoria WHERE categoria_id = 1;
DELETE FROM ocorrencia_categoria WHERE id = 1 AND codigo = 'TESTE';

-- =====================================================================
-- PASSO 2: ocorrencia_subcategoria — ADD COLUMN nullable, UPDATE, SET NOT NULL
-- =====================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ocorrencia_subcategoria' AND column_name = 'categoria_id'
    ) THEN
        -- Adicionar como NULLABLE primeiro
        ALTER TABLE ocorrencia_subcategoria
            ADD COLUMN categoria_id INTEGER REFERENCES ocorrencia_categoria(id);

        -- Vincular registros existentes a COMERCIAL (id=2)
        UPDATE ocorrencia_subcategoria SET categoria_id = 2 WHERE categoria_id IS NULL;

        -- Agora aplicar NOT NULL
        ALTER TABLE ocorrencia_subcategoria
            ALTER COLUMN categoria_id SET NOT NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_subcategoria_categoria_id
    ON ocorrencia_subcategoria(categoria_id);

-- =====================================================================
-- PASSO 3: ocorrencia_responsavel — ADD COLUMN nullable, UPDATE, SET NOT NULL
-- =====================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ocorrencia_responsavel' AND column_name = 'categoria_id'
    ) THEN
        -- Adicionar como NULLABLE primeiro
        ALTER TABLE ocorrencia_responsavel
            ADD COLUMN categoria_id INTEGER REFERENCES ocorrencia_categoria(id);

        -- Vincular registros existentes a COMERCIAL (id=2)
        UPDATE ocorrencia_responsavel SET categoria_id = 2 WHERE categoria_id IS NULL;

        -- Agora aplicar NOT NULL
        ALTER TABLE ocorrencia_responsavel
            ALTER COLUMN categoria_id SET NOT NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_responsavel_categoria_id
    ON ocorrencia_responsavel(categoria_id);
