-- Migration: indice parcial unique p/ evitar duplicacao de provisorio CARVIA
-- Idempotente (IF NOT EXISTS).
-- Aplica apenas a itens ativos com provisorio=TRUE.
-- ATENCAO: se houver duplicatas ATIVAS pendentes, postgres recusa a criacao.
-- Resolver dedup manualmente antes (UPDATE status='cancelado' nos duplicados).

CREATE UNIQUE INDEX IF NOT EXISTS uq_embarque_itens_provisorio_carvia_ativo
    ON embarque_itens (embarque_id, separacao_lote_id)
    WHERE status = 'ativo' AND provisorio = TRUE;
