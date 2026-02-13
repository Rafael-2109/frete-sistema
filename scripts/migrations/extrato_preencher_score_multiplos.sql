-- Migration: Preencher match_score em itens MULTIPLOS_MATCHES
-- ==========================================================
--
-- Itens com status_match='MULTIPLOS_MATCHES' e match_score IS NULL
-- recebem o score do melhor candidato extraído do JSON matches_candidatos.
--
-- Uso (Render Shell):
--   psql $DATABASE_URL -f scripts/migrations/extrato_preencher_score_multiplos.sql
--
-- Data: 2026-02-13

-- BEFORE: verificar quantidade de afetados
SELECT 'BEFORE' AS fase,
       COUNT(*) AS itens_sem_score
FROM extrato_item
WHERE status_match = 'MULTIPLOS_MATCHES'
  AND match_score IS NULL
  AND matches_candidatos IS NOT NULL;

-- EXECUTE: preencher score do melhor candidato (primeiro elemento do array JSON)
UPDATE extrato_item
SET match_score = (matches_candidatos::jsonb -> 0 ->> 'score')::integer,
    match_criterio = CONCAT(
        matches_candidatos::jsonb -> 0 ->> 'criterio',
        '+MULTIPLOS(',
        jsonb_array_length(matches_candidatos::jsonb),
        ')'
    )
WHERE status_match = 'MULTIPLOS_MATCHES'
  AND match_score IS NULL
  AND matches_candidatos IS NOT NULL
  AND matches_candidatos != ''
  AND matches_candidatos != '[]'
  AND (matches_candidatos::jsonb -> 0 ->> 'score') IS NOT NULL;

-- AFTER: verificar resultado
SELECT 'AFTER' AS fase,
       COUNT(*) AS itens_sem_score_restantes
FROM extrato_item
WHERE status_match = 'MULTIPLOS_MATCHES'
  AND match_score IS NULL;

-- Distribuição de scores em MULTIPLOS_MATCHES
SELECT
    CASE
        WHEN match_score >= 90 THEN 'alto (>=90)'
        WHEN match_score >= 70 THEN 'medio (70-89)'
        ELSE 'baixo (<70)'
    END AS faixa,
    COUNT(*) AS qtd
FROM extrato_item
WHERE status_match = 'MULTIPLOS_MATCHES'
  AND match_score IS NOT NULL
GROUP BY 1
ORDER BY 1;
