-- Backfill: vincular operacoes a faturas cliente via itens existentes
-- ===================================================================
--
-- Problema: faturas importadas via PDF nunca setavam fatura_cliente_id
-- nas operacoes, deixando 100% das operacoes com fatura_cliente_id=NULL.
--
-- Solucao: para cada operacao com fatura_cliente_id IS NULL, buscar
-- o item de fatura mais antigo que referencia esta operacao e setar
-- fatura_cliente_id + status=FATURADO.
--
-- IDEMPOTENTE: so atualiza operacoes com fatura_cliente_id IS NULL.
-- Pode ser executado multiplas vezes sem efeito colateral.

-- Diagnostico ANTES
SELECT
    COUNT(*) AS total_operacoes,
    COUNT(fatura_cliente_id) AS com_fatura,
    COUNT(*) - COUNT(fatura_cliente_id) AS sem_fatura,
    COUNT(CASE WHEN status = 'FATURADO' THEN 1 END) AS status_faturado
FROM carvia_operacoes;

-- Backfill: setar fatura_cliente_id e status nas operacoes
-- DISTINCT ON (operacao_id) garante 1 fatura por operacao (primeira ganha)
UPDATE carvia_operacoes op
SET fatura_cliente_id = sub.fatura_cliente_id,
    status = 'FATURADO'
FROM (
    SELECT DISTINCT ON (fci.operacao_id)
        fci.operacao_id,
        fci.fatura_cliente_id
    FROM carvia_fatura_cliente_itens fci
    WHERE fci.operacao_id IS NOT NULL
      AND fci.fatura_cliente_id IS NOT NULL
    ORDER BY fci.operacao_id, fci.id
) sub
WHERE sub.operacao_id = op.id
  AND op.fatura_cliente_id IS NULL;

-- Diagnostico DEPOIS
SELECT
    COUNT(*) AS total_operacoes,
    COUNT(fatura_cliente_id) AS com_fatura,
    COUNT(*) - COUNT(fatura_cliente_id) AS sem_fatura,
    COUNT(CASE WHEN status = 'FATURADO' THEN 1 END) AS status_faturado
FROM carvia_operacoes;
