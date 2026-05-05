-- Migration: Unifica DACTE PDF do CTe Complementar em coluna direta.
--
-- Adiciona `cte_pdf_path` em carvia_cte_complementares (alinhando com
-- carvia_operacoes e carvia_subcontratos — SOT do PDF) e faz backfill
-- a partir da emissao SUCESSO mais recente vinculada a cada CTe Comp,
-- copiando `resultado_json->>'dacte_s3_path'` para o campo direto.
--
-- Antes desta unificacao havia 2 locais para o mesmo PDF:
--   - CarviaEmissaoCteComplementar.resultado_json['dacte_s3_path']
--   - (campo cte_pdf_path nao existia → AttributeError no worker
--      verificar_ctrc_cte_comp_job)
--
-- Agora: SOT = carvia_cte_complementares.cte_pdf_path. resultado_json
-- mantem o path como audit log da emissao.
--
-- Executar no Render Shell.

-- 1) Adicionar coluna (idempotente).
ALTER TABLE carvia_cte_complementares
ADD COLUMN IF NOT EXISTS cte_pdf_path VARCHAR(500);

-- 2) Backfill: copia dacte_s3_path da emissao SUCESSO mais recente para
--    o campo direto, apenas onde ainda nao foi populado.
UPDATE carvia_cte_complementares cc
SET cte_pdf_path = sub.dacte_s3_path
FROM (
    SELECT DISTINCT ON (e.cte_complementar_id)
        e.cte_complementar_id,
        e.resultado_json->>'dacte_s3_path' AS dacte_s3_path
    FROM carvia_emissao_cte_complementar e
    WHERE e.status = 'SUCESSO'
      AND e.resultado_json->>'dacte_s3_path' IS NOT NULL
      AND e.resultado_json->>'dacte_s3_path' <> ''
    ORDER BY e.cte_complementar_id, e.criado_em DESC
) sub
WHERE cc.id = sub.cte_complementar_id
  AND (cc.cte_pdf_path IS NULL OR cc.cte_pdf_path = '');
