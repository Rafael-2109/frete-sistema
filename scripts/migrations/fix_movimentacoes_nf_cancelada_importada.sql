-- Fix: NFs importadas já canceladas que criaram movimentações ativas indevidamente
-- NFs afetadas: 140886 e 145463
-- Causa: Bug no INSERT path de faturamento_service.py que adicionava NFs canceladas a nfs_reprocessar
-- Data: 2026-03-05

-- Verificação ANTES (deve retornar 4 registros):
-- SELECT id, numero_nf, cod_produto, status_nf, ativo, quantidade
-- FROM movimentacao_estoque
-- WHERE numero_nf IN ('140886', '145463')
--   AND status_nf = 'FATURADO'
--   AND ativo = true;

UPDATE movimentacao_estoque
SET status_nf = 'CANCELADO',
    ativo = false,
    atualizado_em = NOW(),
    atualizado_por = 'Fix - NF importada cancelada sem processar cancelamento'
WHERE numero_nf IN ('140886', '145463')
  AND status_nf = 'FATURADO'
  AND ativo = true;

-- Verificação DEPOIS (deve retornar 0):
-- SELECT id, numero_nf, status_nf, ativo
-- FROM movimentacao_estoque
-- WHERE numero_nf IN ('140886', '145463')
--   AND status_nf = 'FATURADO'
--   AND ativo = true;
