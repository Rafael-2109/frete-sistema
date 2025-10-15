-- =============================================================================
-- Script SQL para adicionar novos campos
-- Data: 2025-10-14
-- Executar no Shell do Render (psql)
-- =============================================================================
--
-- NOVOS CAMPOS:
-- - carteira_principal.motivo_exclusao (TEXT): Motivo do cancelamento/exclusão
-- - separacao.obs_separacao (TEXT): Observações sobre a separação
-- - separacao.falta_item (BOOLEAN): Indica se falta item no estoque
-- - separacao.falta_pagamento (BOOLEAN): Indica se pagamento está pendente
--
-- =============================================================================

-- 1. Adicionar motivo_exclusao em CarteiraPrincipal
ALTER TABLE carteira_principal
ADD COLUMN IF NOT EXISTS motivo_exclusao TEXT NULL;

-- 2. Adicionar obs_separacao em Separacao
ALTER TABLE separacao
ADD COLUMN IF NOT EXISTS obs_separacao TEXT NULL;

-- 3. Adicionar falta_item em Separacao
ALTER TABLE separacao
ADD COLUMN IF NOT EXISTS falta_item BOOLEAN NOT NULL DEFAULT FALSE;

-- 4. Adicionar falta_pagamento em Separacao
ALTER TABLE separacao
ADD COLUMN IF NOT EXISTS falta_pagamento BOOLEAN NOT NULL DEFAULT FALSE;

-- Verificar campos adicionados
SELECT
    'carteira_principal' as tabela,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'carteira_principal'
  AND column_name = 'motivo_exclusao'
UNION ALL
SELECT
    'separacao' as tabela,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'separacao'
  AND column_name IN ('obs_separacao', 'falta_item', 'falta_pagamento')
ORDER BY tabela, column_name;
