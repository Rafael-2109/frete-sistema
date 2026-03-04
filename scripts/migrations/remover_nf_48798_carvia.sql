-- ============================================================
-- Remocao one-off da NF 48798 do modulo CarVia
-- Executar no Render Shell (psql)
-- ============================================================
-- IMPORTANTE: Executar dentro de transacao para rollback seguro

BEGIN;

-- 1. Limpar FK nf_id em itens de fatura cliente (nullable, setar NULL)
UPDATE carvia_fatura_cliente_itens
SET nf_id = NULL
WHERE nf_id = (SELECT id FROM carvia_nfs WHERE numero_nf = '48816' LIMIT 1);

-- 2. Limpar FK nf_id em itens de fatura transportadora (nullable, setar NULL)
UPDATE carvia_fatura_transportadora_itens
SET nf_id = NULL
WHERE nf_id = (SELECT id FROM carvia_nfs WHERE numero_nf = '48816' LIMIT 1);

-- 3. Remover junctions operacao <-> NF
DELETE FROM carvia_operacao_nfs
WHERE nf_id = (SELECT id FROM carvia_nfs WHERE numero_nf = '48816' LIMIT 1);

-- 4. Remover itens de produto da NF
DELETE FROM carvia_nf_itens
WHERE nf_id = (SELECT id FROM carvia_nfs WHERE numero_nf = '48816' LIMIT 1);

-- 5. Remover a NF
DELETE FROM carvia_nfs WHERE numero_nf = '48816';

-- Verificar resultado
SELECT 'NFs restantes com numero 48816:' AS check,
       COUNT(*) AS total
FROM carvia_nfs WHERE numero_nf = '48816';

COMMIT;
