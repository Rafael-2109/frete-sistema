-- Migration: Corrigir invariante CONCILIADO => aprovado=True
-- Executar via Render Shell se necessario
--
-- Problema: Itens com status='CONCILIADO' mas aprovado=NULL ou FALSE.
-- Fix: Setar aprovado=True para manter invariante.

-- Verificar ANTES
SELECT count(*) as "itens_conciliado_sem_aprovado"
FROM extrato_item
WHERE status = 'CONCILIADO'
  AND (aprovado IS NULL OR aprovado = FALSE);

-- Executar fix
UPDATE extrato_item
SET aprovado = TRUE,
    aprovado_em = COALESCE(processado_em, NOW()),
    aprovado_por = 'MIGRATION_FIX'
WHERE status = 'CONCILIADO'
  AND (aprovado IS NULL OR aprovado = FALSE);

-- Verificar DEPOIS (deve retornar 0)
SELECT count(*) as "itens_conciliado_sem_aprovado"
FROM extrato_item
WHERE status = 'CONCILIADO'
  AND (aprovado IS NULL OR aprovado = FALSE);
