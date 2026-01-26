-- =============================================================================
-- MIGRAÇÃO: MovimentacaoEstoque → PalletNFRemessa + PalletCredito
-- =============================================================================
-- Este script migra os dados históricos de pallets do modelo antigo
-- (MovimentacaoEstoque) para o novo modelo estruturado v2.
--
-- Fonte: movimentacao_estoque
--        Filtro: local_movimentacao='PALLET' AND tipo_movimentacao='REMESSA'
--
-- Destino:
--   1. pallet_nf_remessa (uma por NF de remessa)
--   2. pallet_creditos (um por cada NF, vinculado à NFRemessa)
--
-- Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
-- IMPLEMENTATION_PLAN.md: Fase 1.3.1
--
-- Uso no Render Shell:
--   psql $DATABASE_URL < scripts/pallet/002_migrar_movimentacao_para_nf_remessa.sql
--
-- ATENÇÃO: Execute 001_criar_tabelas_pallet_v2.sql primeiro!
-- =============================================================================

-- Início da transação
BEGIN;

-- =============================================================================
-- 1. VERIFICAR PRÉ-REQUISITOS
-- =============================================================================

DO $$
BEGIN
    -- Verificar se tabela fonte existe
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'movimentacao_estoque') THEN
        RAISE EXCEPTION 'Tabela movimentacao_estoque não encontrada';
    END IF;

    -- Verificar se tabelas destino existem
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pallet_nf_remessa') THEN
        RAISE EXCEPTION 'Tabela pallet_nf_remessa não encontrada. Execute 001_criar_tabelas_pallet_v2.sql primeiro';
    END IF;

    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pallet_creditos') THEN
        RAISE EXCEPTION 'Tabela pallet_creditos não encontrada. Execute 001_criar_tabelas_pallet_v2.sql primeiro';
    END IF;

    RAISE NOTICE '✅ Pré-requisitos verificados';
END $$;

-- =============================================================================
-- 2. CONTAGEM INICIAL
-- =============================================================================

DO $$
DECLARE
    total_fonte INTEGER;
    total_destino_nf INTEGER;
    total_destino_cred INTEGER;
BEGIN
    -- Contar fonte
    SELECT COUNT(*) INTO total_fonte
    FROM movimentacao_estoque
    WHERE local_movimentacao = 'PALLET'
      AND tipo_movimentacao = 'REMESSA'
      AND ativo = TRUE;

    -- Contar destino (já migrados)
    SELECT COUNT(*) INTO total_destino_nf
    FROM pallet_nf_remessa
    WHERE movimentacao_estoque_id IS NOT NULL;

    SELECT COUNT(*) INTO total_destino_cred
    FROM pallet_creditos
    WHERE movimentacao_estoque_id IS NOT NULL;

    RAISE NOTICE '📊 Registros para migrar: %', total_fonte;
    RAISE NOTICE '📊 Já migrados - NFs: %, Créditos: %', total_destino_nf, total_destino_cred;
END $$;

-- =============================================================================
-- 3. MIGRAR PARA pallet_nf_remessa
-- =============================================================================

-- Inserir apenas registros que ainda não foram migrados
INSERT INTO pallet_nf_remessa (
    numero_nf,
    serie,
    data_emissao,
    empresa,
    tipo_destinatario,
    cnpj_destinatario,
    nome_destinatario,
    quantidade,
    status,
    qtd_resolvida,
    movimentacao_estoque_id,
    observacao,
    criado_em,
    criado_por,
    ativo
)
SELECT
    COALESCE(me.numero_nf, 'LEGADO-' || me.id::TEXT),
    '1',
    me.data_movimentacao,
    'CD',  -- Empresa padrão (ajustar manualmente se necessário)
    COALESCE(me.tipo_destinatario, 'TRANSPORTADORA'),
    COALESCE(me.cnpj_destinatario, ''),
    COALESCE(me.nome_destinatario, ''),
    me.qtd_movimentacao::INTEGER,
    CASE
        WHEN me.baixado = TRUE THEN 'RESOLVIDA'
        WHEN me.qtd_movimentacao - COALESCE(me.qtd_abatida, 0) <= 0 THEN 'RESOLVIDA'
        ELSE 'ATIVA'
    END,
    -- qtd_resolvida = quantidade - saldo
    (me.qtd_movimentacao - GREATEST(0, me.qtd_movimentacao - COALESCE(me.qtd_abatida, 0)))::INTEGER,
    me.id,
    COALESCE(me.observacao, 'Migrado de MovimentacaoEstoque #' || me.id::TEXT),
    COALESCE(me.criado_em, NOW()),
    COALESCE(me.criado_por, 'migracao_v2'),
    TRUE
FROM movimentacao_estoque me
WHERE me.local_movimentacao = 'PALLET'
  AND me.tipo_movimentacao = 'REMESSA'
  AND me.ativo = TRUE
  -- Evitar duplicatas
  AND NOT EXISTS (
      SELECT 1 FROM pallet_nf_remessa nfr
      WHERE nfr.movimentacao_estoque_id = me.id
  );

-- Relatar quantos foram inseridos
DO $$
DECLARE
    inseridos INTEGER;
BEGIN
    GET DIAGNOSTICS inseridos = ROW_COUNT;
    RAISE NOTICE '✅ Inseridos em pallet_nf_remessa: %', inseridos;
END $$;

-- =============================================================================
-- 4. MIGRAR PARA pallet_creditos (vinculado às NFs criadas)
-- =============================================================================

INSERT INTO pallet_creditos (
    nf_remessa_id,
    qtd_original,
    qtd_saldo,
    tipo_responsavel,
    cnpj_responsavel,
    nome_responsavel,
    prazo_dias,
    status,
    movimentacao_estoque_id,
    observacao,
    criado_em,
    criado_por,
    ativo
)
SELECT
    nfr.id,
    nfr.quantidade,
    -- Saldo = quantidade - resolvida
    GREATEST(0, nfr.quantidade - nfr.qtd_resolvida),
    nfr.tipo_destinatario,
    nfr.cnpj_destinatario,
    nfr.nome_destinatario,
    30,  -- Prazo padrão (ajustar baseado em UF se necessário)
    CASE
        WHEN nfr.status = 'RESOLVIDA' THEN 'RESOLVIDO'
        WHEN nfr.quantidade - nfr.qtd_resolvida < nfr.quantidade AND nfr.quantidade - nfr.qtd_resolvida > 0 THEN 'PARCIAL'
        ELSE 'PENDENTE'
    END,
    nfr.movimentacao_estoque_id,
    -- Guardar nf_remessa_origem se existia (para substituições)
    me.nf_remessa_origem,
    nfr.criado_em,
    nfr.criado_por,
    TRUE
FROM pallet_nf_remessa nfr
JOIN movimentacao_estoque me ON me.id = nfr.movimentacao_estoque_id
WHERE nfr.movimentacao_estoque_id IS NOT NULL
  -- Evitar duplicatas
  AND NOT EXISTS (
      SELECT 1 FROM pallet_creditos pc
      WHERE pc.movimentacao_estoque_id = nfr.movimentacao_estoque_id
  );

-- Relatar quantos foram inseridos
DO $$
DECLARE
    inseridos INTEGER;
BEGIN
    GET DIAGNOSTICS inseridos = ROW_COUNT;
    RAISE NOTICE '✅ Inseridos em pallet_creditos: %', inseridos;
END $$;

-- =============================================================================
-- 5. RELATÓRIO FINAL
-- =============================================================================

DO $$
DECLARE
    total_nf INTEGER;
    total_cred INTEGER;
    total_fonte INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_nf FROM pallet_nf_remessa WHERE movimentacao_estoque_id IS NOT NULL;
    SELECT COUNT(*) INTO total_cred FROM pallet_creditos WHERE movimentacao_estoque_id IS NOT NULL;
    SELECT COUNT(*) INTO total_fonte FROM movimentacao_estoque
        WHERE local_movimentacao = 'PALLET' AND tipo_movimentacao = 'REMESSA' AND ativo = TRUE;

    RAISE NOTICE '=============================================================================';
    RAISE NOTICE '  RELATÓRIO FINAL DE MIGRAÇÃO';
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE '  Total na fonte (movimentacao_estoque): %', total_fonte;
    RAISE NOTICE '  Migrados para pallet_nf_remessa:       %', total_nf;
    RAISE NOTICE '  Migrados para pallet_creditos:         %', total_cred;
    RAISE NOTICE '=============================================================================';

    IF total_nf = total_fonte AND total_cred = total_fonte THEN
        RAISE NOTICE '✅ Migração completa e consistente!';
    ELSE
        RAISE NOTICE '⚠️  Verificar: contagens divergentes';
    END IF;
END $$;

-- Commit da transação
COMMIT;

-- =============================================================================
-- FIM DO SCRIPT
-- =============================================================================
