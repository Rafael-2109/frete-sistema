-- =========================================================
-- MIGRATION: Adicionar campo empresa_pagadora_id em despesa_mensal
-- Data: 2025-10-09
-- Descrição: Adiciona FK para rastrear qual empresa pagou a despesa
-- =========================================================

-- 1. Adicionar coluna empresa_pagadora_id
ALTER TABLE despesa_mensal
ADD COLUMN IF NOT EXISTS empresa_pagadora_id INTEGER;

-- 2. Adicionar comentário
COMMENT ON COLUMN despesa_mensal.empresa_pagadora_id IS 'Empresa que pagou a despesa (FK para empresa_venda_moto)';

-- 3. Criar índice para performance
CREATE INDEX IF NOT EXISTS idx_despesa_mensal_empresa_pagadora
ON despesa_mensal(empresa_pagadora_id);

-- 4. Adicionar Foreign Key constraint
ALTER TABLE despesa_mensal
ADD CONSTRAINT fk_despesa_mensal_empresa_pagadora
FOREIGN KEY (empresa_pagadora_id) REFERENCES empresa_venda_moto(id)
ON DELETE SET NULL;

-- 5. Verificar resultado
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'despesa_mensal'
  AND column_name = 'empresa_pagadora_id';

-- Mensagem de sucesso
DO $$
BEGIN
    RAISE NOTICE '✅ Migration concluída com sucesso!';
    RAISE NOTICE '   Campo empresa_pagadora_id adicionado em despesa_mensal';
    RAISE NOTICE '   Foreign Key para empresa_venda_moto criada';
END $$;
