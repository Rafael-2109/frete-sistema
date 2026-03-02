-- ==========================================================================
-- Backfill: nfs_referenciadas_json em carvia_operacoes
-- ==========================================================================
--
-- Popula o campo nfs_referenciadas_json nas operacoes existentes que
-- JA TEM junctions (carvia_operacao_nfs) vinculadas.
--
-- Prerequisito: add_nfs_referenciadas_json_operacoes.sql ja executado.
--
-- Idempotente: so atualiza onde nfs_referenciadas_json IS NULL.
--
-- Execucao no Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/backfill_nfs_referenciadas_json.sql
-- ==========================================================================

BEGIN;

-- 1. Estado ANTES
SELECT 'ANTES' AS fase,
       count(*) AS total_operacoes,
       count(nfs_referenciadas_json) AS com_json,
       count(*) - count(nfs_referenciadas_json) AS sem_json
FROM carvia_operacoes;

-- 2. Popular JSON a partir das junctions existentes
UPDATE carvia_operacoes o
SET nfs_referenciadas_json = sub.refs_json
FROM (
    SELECT
        j.operacao_id,
        json_agg(json_build_object(
            'chave', nf.chave_acesso_nf,
            'numero_nf', nf.numero_nf,
            'cnpj_emitente', nf.cnpj_emitente
        )) AS refs_json
    FROM carvia_operacao_nfs j
    JOIN carvia_nfs nf ON nf.id = j.nf_id
    GROUP BY j.operacao_id
) sub
WHERE o.id = sub.operacao_id
  AND o.nfs_referenciadas_json IS NULL;

-- 3. Estado DEPOIS
SELECT 'DEPOIS' AS fase,
       count(*) AS total_operacoes,
       count(nfs_referenciadas_json) AS com_json,
       count(*) - count(nfs_referenciadas_json) AS sem_json
FROM carvia_operacoes;

-- 4. Operacoes orfas (sem JSON e sem junctions)
SELECT count(*) AS operacoes_orfas
FROM carvia_operacoes o
WHERE o.nfs_referenciadas_json IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM carvia_operacao_nfs j WHERE j.operacao_id = o.id
  );

COMMIT;
