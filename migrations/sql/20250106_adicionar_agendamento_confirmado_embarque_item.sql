-- =====================================================
-- Migration: Adicionar agendamento_confirmado em EmbarqueItem
-- Data: 2025-01-06
-- Descrição: Campo para sincronizar status de confirmação
--            entre Separacao, EmbarqueItem e EntregaMonitorada
-- =====================================================

-- 1. Adicionar coluna com valor padrão
ALTER TABLE embarque_itens
ADD COLUMN agendamento_confirmado BOOLEAN DEFAULT false;

-- 2. Popular valores existentes baseado em Separacao
UPDATE embarque_itens ei
SET agendamento_confirmado = COALESCE(
    (
        SELECT s.agendamento_confirmado
        FROM separacao s
        WHERE s.separacao_lote_id = ei.separacao_lote_id
        LIMIT 1
    ),
    false
)
WHERE ei.separacao_lote_id IS NOT NULL;

-- 3. Verificar resultado
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN agendamento_confirmado = true THEN 1 ELSE 0 END) as confirmados,
    SUM(CASE WHEN agendamento_confirmado = false THEN 1 ELSE 0 END) as nao_confirmados
FROM embarque_itens;

-- =====================================================
-- ROLLBACK (se necessário):
-- ALTER TABLE embarque_itens DROP COLUMN agendamento_confirmado;
-- =====================================================
