-- Migration: Backfill prefixo SC-### → COTACAO-### em carvia_sessoes_cotacao
-- Executar no Render Shell: psql $DATABASE_URL -f backfill_prefixo_cotacao_carvia.sql

UPDATE carvia_sessoes_cotacao
SET numero_sessao = REPLACE(numero_sessao, 'SC-', 'COTACAO-')
WHERE numero_sessao LIKE 'SC-%';
