-- ============================================================================
-- Migracao de DADOS: deprecar COTADO/CONFIRMADO de CarviaOperacao (CTe CarVia)
-- Data: 2026-06-16
-- ----------------------------------------------------------------------------
-- Contexto: o status da operacao deixou de espelhar o ciclo dos subcontratos.
--   A operacao agora segue RASCUNHO -> FATURADO -> CANCELADO. Os status COTADO
--   e CONFIRMADO foram removidos do codigo (operacao_routes, subcontrato_routes,
--   fatura_routes, admin_service, dashboard, templates).
--
-- Dados PROD (2026-06-16): COTADO = 0 registros; CONFIRMADO = 45 — TODAS com
--   fatura cliente PAGA e conciliada. O status ficou preso por regressao
--   (confirmar_subcontrato re-promovia a operacao a CONFIRMADO mesmo apos
--   faturada). Migrar CONFIRMADO->FATURADO CORRIGE a inconsistencia: uma
--   operacao com fatura_cliente_id deve estar FATURADO.
--
-- Idempotente: rodar 2x nao tem efeito adicional (nao resta COTADO/CONFIRMADO).
-- Atomico: roda em transacao. Revise o diagnostico (passo 1) e a verificacao
--   (passo 4) no output. Em caso de duvida, troque COMMIT por ROLLBACK.
-- ============================================================================

BEGIN;

-- 1. Diagnostico ANTES (esperado: CONFIRMADO com tem_fatura = true)
SELECT status,
       (fatura_cliente_id IS NOT NULL) AS tem_fatura,
       COUNT(*) AS qtd
FROM carvia_operacoes
WHERE status IN ('COTADO', 'CONFIRMADO')
GROUP BY status, tem_fatura
ORDER BY status, tem_fatura;

-- 2. COM fatura -> FATURADO (corrige a regressao; FK ja aponta para a fatura)
UPDATE carvia_operacoes
SET status = 'FATURADO'
WHERE status IN ('COTADO', 'CONFIRMADO')
  AND fatura_cliente_id IS NOT NULL;

-- 3. Salvaguarda: SEM fatura -> RASCUNHO (pre-fatura legitimo, sem inconsistencia)
UPDATE carvia_operacoes
SET status = 'RASCUNHO'
WHERE status IN ('COTADO', 'CONFIRMADO')
  AND fatura_cliente_id IS NULL;

-- 4. Verificacao DEPOIS (NAO deve restar COTADO/CONFIRMADO)
SELECT status, COUNT(*) AS qtd
FROM carvia_operacoes
GROUP BY status
ORDER BY status;

COMMIT;
