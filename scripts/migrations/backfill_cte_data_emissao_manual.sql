-- Backfill: cte_data_emissao para CTes CarVia criados manualmente
-- Idempotente: so atualiza WHERE cte_data_emissao IS NULL
-- Usar no Render Shell

UPDATE carvia_operacoes o
SET cte_data_emissao = sub.max_data_emissao
FROM (
    SELECT
        j.operacao_id,
        MAX(nf.data_emissao) AS max_data_emissao
    FROM carvia_operacao_nfs j
    JOIN carvia_nfs nf ON nf.id = j.nf_id
    WHERE nf.data_emissao IS NOT NULL
    GROUP BY j.operacao_id
) sub
WHERE o.id = sub.operacao_id
  AND o.cte_data_emissao IS NULL;
