-- Migration: Adicionar numero_sequencial_transportadora em carvia_subcontratos
-- Execucao: Render Shell (SQL idempotente)

-- 1. Adicionar coluna
ALTER TABLE carvia_subcontratos
ADD COLUMN IF NOT EXISTS numero_sequencial_transportadora INTEGER;

-- 2. Criar indice unico composto (partial — ignora NULLs)
CREATE UNIQUE INDEX IF NOT EXISTS uq_sub_transportadora_seq
ON carvia_subcontratos(transportadora_id, numero_sequencial_transportadora)
WHERE numero_sequencial_transportadora IS NOT NULL;

-- 3. Preencher sequencial para subcontratos existentes
WITH numbered AS (
    SELECT id,
           ROW_NUMBER() OVER (
               PARTITION BY transportadora_id
               ORDER BY criado_em, id
           ) AS seq
    FROM carvia_subcontratos
    WHERE numero_sequencial_transportadora IS NULL
)
UPDATE carvia_subcontratos
SET numero_sequencial_transportadora = numbered.seq
FROM numbered
WHERE carvia_subcontratos.id = numbered.id;
