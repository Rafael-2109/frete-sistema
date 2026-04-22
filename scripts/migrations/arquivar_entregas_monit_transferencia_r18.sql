-- Migration one-shot (R18): REVERTER arquivamento 'Cancelada por Transferencia'
--
-- A abordagem final R18 controla visibilidade por FILTRO na query de
-- /monitoramento/listar_entregas (nao altera status). Esta migration
-- desfaz o arquivamento equivocado da versao anterior (se aplicada).
--
-- Idempotente: WHERE status_finalizacao='Cancelada por Transferencia'
-- so afeta linhas ja marcadas por essa versao descartada.

-- Verificacao BEFORE
SELECT 'BEFORE: a reverter' AS stage, COUNT(*) AS total
FROM entregas_monitoradas
WHERE origem = 'CARVIA'
  AND status_finalizacao = 'Cancelada por Transferencia';

-- Execucao
UPDATE entregas_monitoradas
SET status_finalizacao = NULL,
    finalizado_por = NULL,
    finalizado_em = NULL
WHERE origem = 'CARVIA'
  AND status_finalizacao = 'Cancelada por Transferencia';

-- Verificacao AFTER
SELECT 'AFTER: restantes (esperado: 0)' AS stage, COUNT(*) AS total
FROM entregas_monitoradas
WHERE status_finalizacao = 'Cancelada por Transferencia';
