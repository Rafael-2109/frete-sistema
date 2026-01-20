-- ============================================================
-- INDICES DE OTIMIZACAO PARA MATCH NF x PO
-- ============================================================
-- Executar no Shell do Render para melhorar performance
-- das consultas de De-Para e Validacao
-- ============================================================

-- Indice para converter_lote() do DeparaService
-- Usado na busca batch de De-Para: WHERE cnpj + cod_produto IN (...)
CREATE INDEX IF NOT EXISTS idx_depara_cnpj_cod_ativo
ON produto_fornecedor_depara(cnpj_fornecedor, cod_produto_fornecedor, ativo);

-- Indice para busca de validacoes por DFE
CREATE INDEX IF NOT EXISTS idx_validacao_odoo_dfe
ON validacao_nf_po_dfe(odoo_dfe_id);

-- Indice para busca de matches por validacao
CREATE INDEX IF NOT EXISTS idx_match_validacao
ON match_nf_po_item(validacao_id);

-- Indice para busca de divergencias por validacao
CREATE INDEX IF NOT EXISTS idx_divergencia_validacao
ON divergencia_nf_po(validacao_id);

-- Indice para busca de alocacoes por match_item
CREATE INDEX IF NOT EXISTS idx_alocacao_match_item
ON match_nf_po_alocacao(match_item_id);

-- Verificar indices criados
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
