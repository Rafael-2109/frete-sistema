-- ================================================
-- MIGRATION: Adicionar Campos de CTe Complementar
-- ================================================
-- AUTOR: Sistema de Fretes
-- DATA: 15/11/2025
--
-- OBJETIVO: Adicionar campos para identificar e relacionar CTes complementares
--
-- CAMPOS:
--   - tipo_cte: Tipo do CTe (0=Normal, 1=Complementar, 2=Anulação, 3=Substituto)
--   - cte_complementa_chave: Chave do CTe que está sendo complementado
--   - cte_complementa_id: ID do CTe original (FK self-referencial)
--   - motivo_complemento: Motivo do complemento
-- ================================================

-- 1. Adicionar campos
ALTER TABLE conhecimento_transporte
ADD COLUMN IF NOT EXISTS tipo_cte VARCHAR(1) DEFAULT '0';

ALTER TABLE conhecimento_transporte
ADD COLUMN IF NOT EXISTS cte_complementa_chave VARCHAR(44);

ALTER TABLE conhecimento_transporte
ADD COLUMN IF NOT EXISTS cte_complementa_id INTEGER;

ALTER TABLE conhecimento_transporte
ADD COLUMN IF NOT EXISTS motivo_complemento TEXT;

-- 2. Criar índices
CREATE INDEX IF NOT EXISTS idx_cte_tipo
ON conhecimento_transporte(tipo_cte);

CREATE INDEX IF NOT EXISTS idx_cte_complementa_chave
ON conhecimento_transporte(cte_complementa_chave);

CREATE INDEX IF NOT EXISTS idx_cte_complementa_id
ON conhecimento_transporte(cte_complementa_id);

-- 3. Adicionar foreign key (self-referencial)
-- Nota: Em PostgreSQL, use ALTER TABLE ADD CONSTRAINT se ainda não existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_cte_complementa_id'
    ) THEN
        ALTER TABLE conhecimento_transporte
        ADD CONSTRAINT fk_cte_complementa_id
        FOREIGN KEY (cte_complementa_id)
        REFERENCES conhecimento_transporte(id)
        ON DELETE SET NULL;
    END IF;
END $$;

-- 4. Verificar campos adicionados
SELECT column_name, data_type, character_maximum_length, column_default
FROM information_schema.columns
WHERE table_name = 'conhecimento_transporte'
AND column_name IN ('tipo_cte', 'cte_complementa_chave', 'cte_complementa_id', 'motivo_complemento')
ORDER BY column_name;

-- ================================================
-- ✅ MIGRATION CONCLUÍDA
-- ================================================
-- Próximo passo: Executar sincronização de CTes para processar os XMLs
