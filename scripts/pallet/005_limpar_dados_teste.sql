-- ============================================================================
-- LIMPEZA DE DADOS DE TESTE - PALLET V2
-- ============================================================================
-- Execute este script no Shell do Render para limpar dados de teste.
-- Ordem de DELETE respeita Foreign Keys.
--
-- ATENÇÃO: Este script REMOVE TODOS os registros das tabelas v2!
-- Execute apenas se tiver certeza que os dados são de teste.
-- ============================================================================

-- Início da transação
BEGIN;

-- 1. pallet_nf_solucoes (FK: pallet_solucoes, pallet_nf_remessa)
DELETE FROM pallet_nf_solucoes;
-- Mostra quantos registros foram deletados
SELECT 'pallet_nf_solucoes' as tabela, COUNT(*) as restantes FROM pallet_nf_solucoes;

-- 2. pallet_solucoes (FK: pallet_creditos)
DELETE FROM pallet_solucoes;
SELECT 'pallet_solucoes' as tabela, COUNT(*) as restantes FROM pallet_solucoes;

-- 3. pallet_documentos (FK: pallet_creditos)
DELETE FROM pallet_documentos;
SELECT 'pallet_documentos' as tabela, COUNT(*) as restantes FROM pallet_documentos;

-- 4. pallet_creditos (FK: pallet_nf_remessa)
DELETE FROM pallet_creditos;
SELECT 'pallet_creditos' as tabela, COUNT(*) as restantes FROM pallet_creditos;

-- 5. pallet_nf_remessa (tabela base)
DELETE FROM pallet_nf_remessa;
SELECT 'pallet_nf_remessa' as tabela, COUNT(*) as restantes FROM pallet_nf_remessa;

-- Commit da transação
COMMIT;

-- Verificação final
SELECT
    'LIMPEZA CONCLUÍDA' as status,
    (SELECT COUNT(*) FROM pallet_nf_remessa) as nf_remessa,
    (SELECT COUNT(*) FROM pallet_creditos) as creditos,
    (SELECT COUNT(*) FROM pallet_solucoes) as solucoes,
    (SELECT COUNT(*) FROM pallet_documentos) as documentos,
    (SELECT COUNT(*) FROM pallet_nf_solucoes) as nf_solucoes;
