-- ============================================================================
-- MIGRAÇÃO: ValePallet → PalletDocumento + PalletSolucao
-- ============================================================================
--
-- Este script migra os dados históricos de vales pallet do modelo antigo
-- (vale_pallets) para os novos modelos v2 (pallet_documentos + pallet_solucoes).
--
-- DEPENDÊNCIAS:
--   - Script 001 deve ter sido executado (tabelas existem)
--   - Script 002 deve ter sido executado (PalletNFRemessa e PalletCredito existem)
--
-- Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
-- IMPLEMENTATION_PLAN.md: Fase 1.3.2
--
-- Uso no Render Shell:
--   psql $DATABASE_URL < scripts/pallet/003_migrar_vale_pallet_para_documento.sql
-- ============================================================================

\echo '============================================================================'
\echo '  MIGRAÇÃO: ValePallet → PalletDocumento + PalletSolucao'
\echo '============================================================================'

-- Verificar tabelas existem
\echo ''
\echo '📋 Verificando tabelas...'

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vale_pallets') THEN
        RAISE EXCEPTION 'Tabela vale_pallets não existe!';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pallet_documentos') THEN
        RAISE EXCEPTION 'Tabela pallet_documentos não existe! Execute script 001 primeiro.';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pallet_creditos') THEN
        RAISE EXCEPTION 'Tabela pallet_creditos não existe! Execute scripts 001 e 002 primeiro.';
    END IF;
END $$;

\echo '  ✅ Todas as tabelas existem'

-- Contagem inicial
\echo ''
\echo '📊 Contagem de registros:'
SELECT 'Vale Pallets (origem)' as tabela, COUNT(*) as total FROM vale_pallets WHERE ativo = TRUE;
SELECT 'Documentos (já migrados)' as tabela, COUNT(*) as total FROM pallet_documentos WHERE vale_pallet_id IS NOT NULL;
SELECT 'Soluções (já migradas)' as tabela, COUNT(*) as total FROM pallet_solucoes WHERE vale_pallet_id IS NOT NULL;

-- ============================================================================
-- PASSO 1: Migrar para PalletDocumento
-- ============================================================================

\echo ''
\echo '🔄 Passo 1: Migrando ValePallet → PalletDocumento...'

INSERT INTO pallet_documentos (
    credito_id,
    tipo,
    numero_documento,
    data_emissao,
    data_validade,
    quantidade,
    cnpj_emissor,
    nome_emissor,
    recebido,
    recebido_em,
    recebido_por,
    pasta_arquivo,
    aba_arquivo,
    vale_pallet_id,
    observacao,
    criado_em,
    criado_por,
    ativo
)
SELECT
    c.id as credito_id,
    CASE
        WHEN v.tipo_vale = 'VALE_PALLET' THEN 'VALE_PALLET'
        ELSE 'CANHOTO'
    END as tipo,
    v.nf_pallet as numero_documento,
    v.data_emissao,
    v.data_validade,
    COALESCE(v.quantidade, 0) as quantidade,
    COALESCE(v.cnpj_cliente, v.cnpj_posse, '') as cnpj_emissor,
    COALESCE(v.nome_cliente, v.nome_posse, '') as nome_emissor,
    COALESCE(v.recebido, FALSE) as recebido,
    v.recebido_em,
    v.recebido_por,
    v.pasta_arquivo,
    v.aba_arquivo,
    v.id as vale_pallet_id,
    COALESCE(v.observacao, 'Migrado de ValePallet #' || v.id::TEXT) as observacao,
    COALESCE(v.criado_em, NOW()) as criado_em,
    COALESCE(v.criado_por, 'migracao_sql') as criado_por,
    TRUE as ativo
FROM vale_pallets v
JOIN pallet_nf_remessa nr ON nr.numero_nf = v.nf_pallet AND nr.ativo = TRUE
JOIN pallet_creditos c ON c.nf_remessa_id = nr.id AND c.ativo = TRUE
WHERE v.ativo = TRUE
  AND NOT EXISTS (
      SELECT 1 FROM pallet_documentos d WHERE d.vale_pallet_id = v.id
  )
ON CONFLICT DO NOTHING;

\echo '  ✅ Documentos migrados'

-- ============================================================================
-- PASSO 2: Criar Soluções para vales resolvidos por VENDA
-- ============================================================================

\echo ''
\echo '🔄 Passo 2: Criando soluções para vales resolvidos por VENDA...'

INSERT INTO pallet_solucoes (
    credito_id,
    tipo,
    quantidade,
    nf_venda,
    data_venda,
    valor_total,
    cnpj_comprador,
    nome_comprador,
    cnpj_responsavel,
    nome_responsavel,
    vale_pallet_id,
    observacao,
    criado_em,
    criado_por,
    ativo
)
SELECT
    c.id as credito_id,
    'VENDA' as tipo,
    COALESCE(v.quantidade, 0) as quantidade,
    v.nf_resolucao as nf_venda,
    COALESCE(v.resolvido_em::DATE, NULL) as data_venda,
    v.valor_resolucao as valor_total,
    v.cnpj_resolucao as cnpj_comprador,
    v.responsavel_resolucao as nome_comprador,
    v.cnpj_resolucao as cnpj_responsavel,
    v.responsavel_resolucao as nome_responsavel,
    v.id as vale_pallet_id,
    'Migrado de ValePallet #' || v.id::TEXT || ' (resolvido por venda)' as observacao,
    COALESCE(v.resolvido_em, NOW()) as criado_em,
    COALESCE(v.resolvido_por, 'migracao_sql') as criado_por,
    TRUE as ativo
FROM vale_pallets v
JOIN pallet_nf_remessa nr ON nr.numero_nf = v.nf_pallet AND nr.ativo = TRUE
JOIN pallet_creditos c ON c.nf_remessa_id = nr.id AND c.ativo = TRUE
WHERE v.ativo = TRUE
  AND v.resolvido = TRUE
  AND v.tipo_resolucao = 'VENDA'
  AND NOT EXISTS (
      SELECT 1 FROM pallet_solucoes s WHERE s.vale_pallet_id = v.id
  )
ON CONFLICT DO NOTHING;

\echo '  ✅ Soluções VENDA migradas'

-- ============================================================================
-- PASSO 3: Criar Soluções para vales resolvidos por COLETA (RECEBIMENTO)
-- ============================================================================

\echo ''
\echo '🔄 Passo 3: Criando soluções para vales resolvidos por COLETA...'

INSERT INTO pallet_solucoes (
    credito_id,
    tipo,
    quantidade,
    data_recebimento,
    local_recebimento,
    recebido_de,
    cnpj_entregador,
    cnpj_responsavel,
    nome_responsavel,
    vale_pallet_id,
    observacao,
    criado_em,
    criado_por,
    ativo
)
SELECT
    c.id as credito_id,
    'RECEBIMENTO' as tipo,
    COALESCE(v.quantidade, 0) as quantidade,
    COALESCE(v.resolvido_em::DATE, NULL) as data_recebimento,
    'Nacom' as local_recebimento,
    COALESCE(v.responsavel_resolucao, v.nome_transportadora) as recebido_de,
    COALESCE(v.cnpj_resolucao, v.cnpj_transportadora) as cnpj_entregador,
    COALESCE(v.cnpj_resolucao, v.cnpj_transportadora) as cnpj_responsavel,
    COALESCE(v.responsavel_resolucao, v.nome_transportadora) as nome_responsavel,
    v.id as vale_pallet_id,
    'Migrado de ValePallet #' || v.id::TEXT || ' (resolvido por coleta)' as observacao,
    COALESCE(v.resolvido_em, NOW()) as criado_em,
    COALESCE(v.resolvido_por, 'migracao_sql') as criado_por,
    TRUE as ativo
FROM vale_pallets v
JOIN pallet_nf_remessa nr ON nr.numero_nf = v.nf_pallet AND nr.ativo = TRUE
JOIN pallet_creditos c ON c.nf_remessa_id = nr.id AND c.ativo = TRUE
WHERE v.ativo = TRUE
  AND v.resolvido = TRUE
  AND v.tipo_resolucao = 'COLETA'
  AND NOT EXISTS (
      SELECT 1 FROM pallet_solucoes s WHERE s.vale_pallet_id = v.id
  )
ON CONFLICT DO NOTHING;

\echo '  ✅ Soluções RECEBIMENTO migradas'

-- ============================================================================
-- RELATÓRIO FINAL
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo '  RELATÓRIO DE MIGRAÇÃO'
\echo '============================================================================'

SELECT 'Total de Vale Pallets' as metrica, COUNT(*) as valor
FROM vale_pallets WHERE ativo = TRUE;

SELECT 'Documentos criados' as metrica, COUNT(*) as valor
FROM pallet_documentos WHERE vale_pallet_id IS NOT NULL;

SELECT 'Soluções criadas' as metrica, COUNT(*) as valor
FROM pallet_solucoes WHERE vale_pallet_id IS NOT NULL;

SELECT 'Soluções VENDA' as metrica, COUNT(*) as valor
FROM pallet_solucoes WHERE vale_pallet_id IS NOT NULL AND tipo = 'VENDA';

SELECT 'Soluções RECEBIMENTO' as metrica, COUNT(*) as valor
FROM pallet_solucoes WHERE vale_pallet_id IS NOT NULL AND tipo = 'RECEBIMENTO';

-- Vales sem crédito correspondente
\echo ''
\echo '⚠️  Vales sem crédito correspondente (NF não migrada):'
SELECT COUNT(*) as vales_sem_credito
FROM vale_pallets v
WHERE v.ativo = TRUE
  AND NOT EXISTS (
      SELECT 1
      FROM pallet_nf_remessa nr
      JOIN pallet_creditos c ON c.nf_remessa_id = nr.id
      WHERE nr.numero_nf = v.nf_pallet
        AND nr.ativo = TRUE
        AND c.ativo = TRUE
  );

\echo ''
\echo '============================================================================'
\echo '  ✅ Migração concluída!'
\echo '============================================================================'
