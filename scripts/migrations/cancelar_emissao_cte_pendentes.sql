-- Migration: Cancelar emissões CTe pendentes órfãs
-- Motivo: Jobs foram enfileirados na queue 'ssw_carvia' que nenhum worker escuta.
--         Registros ficaram PENDENTE eternamente. Cancelar para desbloquear mutex.
-- Data: 2026-04-07

UPDATE carvia_emissao_cte
SET status = 'CANCELADO',
    erro_ssw = COALESCE(erro_ssw, '') || 'Cancelado: job enfileirado em queue sem consumidor (ssw_carvia)',
    atualizado_em = NOW()
WHERE status IN ('PENDENTE', 'EM_PROCESSAMENTO');
