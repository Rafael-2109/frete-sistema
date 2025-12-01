-- ============================================================================
-- Script SQL para corrigir inconsistências na flag nf_cd
--
-- PROBLEMAS CORRIGIDOS:
-- 1. EntregaMonitorada com status_finalizacao preenchido E nf_cd=True
-- 2. EntregaMonitorada com nf_cd=True mas sem evento "NF no CD"
-- 3. Separacao com nf_cd diferente de EntregaMonitorada para mesmo lote/NF
--
-- Autor: Sistema
-- Data: 01/12/2025
-- ============================================================================

-- Verificar antes de executar (apenas contagem):
SELECT 'PROBLEMA 1: Entregas finalizadas com nf_cd=True' as problema,
       COUNT(*) as quantidade
FROM entregas_monitoradas
WHERE status_finalizacao IS NOT NULL AND nf_cd = true;

SELECT 'PROBLEMA 2: Entregas com nf_cd=True sem evento NF no CD' as problema,
       COUNT(*) as quantidade
FROM entregas_monitoradas em
WHERE em.nf_cd = true
  AND NOT EXISTS (
    SELECT 1 FROM eventos_entrega ev
    WHERE ev.entrega_id = em.id AND ev.tipo_evento = 'NF no CD'
  );


-- ============================================================================
-- CORREÇÃO 1: Resetar nf_cd em entregas finalizadas
-- ============================================================================

-- Atualizar EntregaMonitorada
UPDATE entregas_monitoradas
SET nf_cd = false
WHERE status_finalizacao IS NOT NULL AND nf_cd = true;

-- Sincronizar Separacao (por separacao_lote_id)
UPDATE separacao s
SET nf_cd = false
FROM entregas_monitoradas em
WHERE em.separacao_lote_id = s.separacao_lote_id
  AND em.status_finalizacao IS NOT NULL
  AND s.nf_cd = true;

-- Sincronizar Separacao (por numero_nf, fallback)
UPDATE separacao s
SET nf_cd = false
FROM entregas_monitoradas em
WHERE em.numero_nf = s.numero_nf
  AND em.status_finalizacao IS NOT NULL
  AND s.nf_cd = true
  AND s.separacao_lote_id NOT IN (
    SELECT DISTINCT separacao_lote_id
    FROM entregas_monitoradas
    WHERE separacao_lote_id IS NOT NULL
  );


-- ============================================================================
-- CORREÇÃO 2: Resetar nf_cd em entregas sem evento "NF no CD"
-- ============================================================================

-- Atualizar EntregaMonitorada
UPDATE entregas_monitoradas em
SET nf_cd = false
WHERE em.nf_cd = true
  AND NOT EXISTS (
    SELECT 1 FROM eventos_entrega ev
    WHERE ev.entrega_id = em.id AND ev.tipo_evento = 'NF no CD'
  );

-- Sincronizar Separacao (por separacao_lote_id)
UPDATE separacao s
SET nf_cd = false
FROM entregas_monitoradas em
WHERE em.separacao_lote_id = s.separacao_lote_id
  AND em.nf_cd = false
  AND s.nf_cd = true;

-- Sincronizar Separacao (por numero_nf, fallback)
UPDATE separacao s
SET nf_cd = false
FROM entregas_monitoradas em
WHERE em.numero_nf = s.numero_nf
  AND em.nf_cd = false
  AND s.nf_cd = true;


-- ============================================================================
-- VERIFICAÇÃO FINAL
-- ============================================================================

SELECT 'Após correção - Entregas finalizadas com nf_cd=True' as verificacao,
       COUNT(*) as quantidade
FROM entregas_monitoradas
WHERE status_finalizacao IS NOT NULL AND nf_cd = true;

SELECT 'Após correção - Entregas com nf_cd=True sem evento' as verificacao,
       COUNT(*) as quantidade
FROM entregas_monitoradas em
WHERE em.nf_cd = true
  AND NOT EXISTS (
    SELECT 1 FROM eventos_entrega ev
    WHERE ev.entrega_id = em.id AND ev.tipo_evento = 'NF no CD'
  );
