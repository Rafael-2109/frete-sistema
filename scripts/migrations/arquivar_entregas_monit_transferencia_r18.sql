-- Migration one-shot (R18): arquivar EntregaMonitorada de NF transferencia efetiva
-- Idempotente: WHERE status_finalizacao IS NULL impede re-execucao pisando em linhas ja arquivadas
-- Execucao: Render Shell: psql $DATABASE_URL -f arquivar_entregas_monit_transferencia_r18.sql

-- Verificacao BEFORE
SELECT 'BEFORE: a arquivar' AS stage, COUNT(*) AS total
FROM entregas_monitoradas em
JOIN carvia_nfs cn ON cn.numero_nf = em.numero_nf AND cn.status = 'ATIVA'
JOIN carvia_nf_vinculos_transferencia vt ON vt.nf_transferencia_id = cn.id
WHERE em.origem = 'CARVIA'
  AND em.status_finalizacao IS NULL;

SELECT 'BEFORE: ja finalizadas (preservadas)' AS stage, COUNT(*) AS total
FROM entregas_monitoradas em
JOIN carvia_nfs cn ON cn.numero_nf = em.numero_nf AND cn.status = 'ATIVA'
JOIN carvia_nf_vinculos_transferencia vt ON vt.nf_transferencia_id = cn.id
WHERE em.origem = 'CARVIA'
  AND em.status_finalizacao IS NOT NULL;

-- Execucao
UPDATE entregas_monitoradas em
SET status_finalizacao = 'Cancelada por Transferencia',
    finalizado_por = 'Sistema CarVia (R18 migration)',
    finalizado_em = NOW()
FROM carvia_nfs cn
JOIN carvia_nf_vinculos_transferencia vt
  ON vt.nf_transferencia_id = cn.id
WHERE em.origem = 'CARVIA'
  AND em.status_finalizacao IS NULL
  AND cn.numero_nf = em.numero_nf
  AND cn.status = 'ATIVA';

-- Verificacao AFTER
SELECT 'AFTER: transferencias efetivas ainda ATIVAS (esperado: 0)' AS stage,
       COUNT(*) AS total
FROM entregas_monitoradas em
JOIN carvia_nfs cn ON cn.numero_nf = em.numero_nf AND cn.status = 'ATIVA'
JOIN carvia_nf_vinculos_transferencia vt ON vt.nf_transferencia_id = cn.id
WHERE em.origem = 'CARVIA'
  AND em.status_finalizacao IS NULL;

SELECT 'AFTER: arquivadas por esta migration' AS stage,
       COUNT(*) AS total
FROM entregas_monitoradas
WHERE origem = 'CARVIA'
  AND status_finalizacao = 'Cancelada por Transferencia';
