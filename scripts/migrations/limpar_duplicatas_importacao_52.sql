-- Data fix: Remove duplicatas da importacao 52 (re-importacao Bradesco 10/05/2026)
-- Causa: documento com vs sem zero a esquerda gerou hashes distintos no dedup.
-- Pre-requisito: 0 compensacoes ATIVAS apontando para essas IDs (verificado via MCP).
-- Idempotente: rodar 2x e a 2a vez nao remove nada.

BEGIN;

-- 1. Verificar bloqueios
DO $$
DECLARE
    n_comp INT;
BEGIN
    SELECT COUNT(*) INTO n_comp
      FROM pessoal_compensacoes
     WHERE status='ATIVA'
       AND (saida_id   = ANY(ARRAY[3834,3835,3837,3840,3841,3842,3843,3844,3846,3848,3849,3850,3851,3852,3856,3857,3860,3861,3862,3863,3868,3870])
         OR entrada_id = ANY(ARRAY[3834,3835,3837,3840,3841,3842,3843,3844,3846,3848,3849,3850,3851,3852,3856,3857,3860,3861,3862,3863,3868,3870]));
    IF n_comp > 0 THEN
        RAISE EXCEPTION 'Abort: % compensacoes ATIVAS referenciam estas IDs', n_comp;
    END IF;
END $$;

-- 2. DELETE
DELETE FROM pessoal_transacoes
 WHERE id IN (3834,3835,3837,3840,3841,3842,3843,3844,3846,3848,3849,3850,3851,3852,3856,3857,3860,3861,3862,3863,3868,3870);

-- 3. Ajustar contadores da importacao 52 (so se houve DELETE)
UPDATE pessoal_importacoes
   SET linhas_importadas = GREATEST(linhas_importadas - 22, 0),
       linhas_duplicadas = linhas_duplicadas + 22
 WHERE id = 52
   AND linhas_importadas >= 22;  -- defensivo: roda so 1 vez

COMMIT;
