-- ============================================================================
-- Migration: Aumentar tamanho do campo num_pedido
-- ============================================================================
--
-- PROBLEMA:
--   Campo num_pedido na tabela movimentacao_estoque está com VARCHAR(30)
--   mas precisa ser VARCHAR(50) para acomodar strings como:
--   "Devolução de CD/CD/PALLET/03617" (33 caracteres)
--
-- SOLUÇÃO:
--   Alterar num_pedido de VARCHAR(30) para VARCHAR(50)
--
-- AUTOR: Sistema de Fretes
-- DATA: 13/11/2025
--
-- ============================================================================

-- 1. Verificar tamanho atual
SELECT
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'movimentacao_estoque'
  AND column_name = 'num_pedido';

-- 2. Alterar tamanho do campo
ALTER TABLE movimentacao_estoque
ALTER COLUMN num_pedido TYPE VARCHAR(50);

-- 3. Verificar alteração
SELECT
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'movimentacao_estoque'
  AND column_name = 'num_pedido';

-- ✅ Migration concluída!
