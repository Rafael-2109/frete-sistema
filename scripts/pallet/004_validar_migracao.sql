-- ============================================================================
-- Script de validação de migração: Verifica integridade dos dados migrados
-- ============================================================================
--
-- Este script valida a integridade dos dados migrados pelos scripts 001, 002 e 003
--
-- Dependências (ordem de execução):
--    1. scripts/pallet/001_criar_tabelas_pallet_v2.sql
--    2. scripts/pallet/002_migrar_movimentacao_para_nf_remessa.sql
--    3. scripts/pallet/003_migrar_vale_pallet_para_documento.sql
--    4. scripts/pallet/004_validar_migracao.sql (ESTE SCRIPT)
--
-- Uso no Render Shell:
--    psql $DATABASE_URL < scripts/pallet/004_validar_migracao.sql
--
-- Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
-- IMPLEMENTATION_PLAN.md: Fase 1.3.3
-- ============================================================================

\echo ''
\echo '======================================================================'
\echo ' VALIDAÇÃO DE MIGRAÇÃO - PALLET V2'
\echo '======================================================================'
\echo ''

-- ============================================================================
-- VERIFICAÇÃO 1: TABELAS V2 EXISTEM
-- ============================================================================
\echo '📋 VERIFICAÇÃO 1: Tabelas V2 existem'
\echo '----------------------------------------------------------------------'

SELECT
    'pallet_nf_remessa' as tabela,
    CASE WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pallet_nf_remessa')
         THEN '✅ EXISTE' ELSE '❌ NÃO EXISTE' END as status,
    (SELECT COUNT(*) FROM pallet_nf_remessa) as registros
UNION ALL
SELECT
    'pallet_creditos',
    CASE WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pallet_creditos')
         THEN '✅ EXISTE' ELSE '❌ NÃO EXISTE' END,
    (SELECT COUNT(*) FROM pallet_creditos)
UNION ALL
SELECT
    'pallet_documentos',
    CASE WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pallet_documentos')
         THEN '✅ EXISTE' ELSE '❌ NÃO EXISTE' END,
    (SELECT COUNT(*) FROM pallet_documentos)
UNION ALL
SELECT
    'pallet_solucoes',
    CASE WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pallet_solucoes')
         THEN '✅ EXISTE' ELSE '❌ NÃO EXISTE' END,
    (SELECT COUNT(*) FROM pallet_solucoes)
UNION ALL
SELECT
    'pallet_nf_solucoes',
    CASE WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pallet_nf_solucoes')
         THEN '✅ EXISTE' ELSE '❌ NÃO EXISTE' END,
    (SELECT COUNT(*) FROM pallet_nf_solucoes);

\echo ''

-- ============================================================================
-- VERIFICAÇÃO 2: TABELAS LEGADO (FONTE)
-- ============================================================================
\echo '📋 VERIFICAÇÃO 2: Tabelas Legado (Fonte)'
\echo '----------------------------------------------------------------------'

SELECT
    'movimentacao_estoque' as tabela,
    CASE WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'movimentacao_estoque')
         THEN '✅ EXISTE' ELSE 'ℹ️ NÃO EXISTE (ok)' END as status,
    COALESCE((SELECT COUNT(*) FROM movimentacao_estoque WHERE local_movimentacao = 'PALLET' AND tipo_movimentacao = 'REMESSA'), 0) as registros
UNION ALL
SELECT
    'vale_pallets',
    CASE WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'vale_pallets')
         THEN '✅ EXISTE' ELSE 'ℹ️ NÃO EXISTE (ok)' END,
    COALESCE((SELECT COUNT(*) FROM vale_pallets WHERE ativo = TRUE), 0);

\echo ''

-- ============================================================================
-- VERIFICAÇÃO 3: FK CRÉDITOS → NF REMESSA
-- ============================================================================
\echo '📋 VERIFICAÇÃO 3: FK Créditos → NF Remessa'
\echo '----------------------------------------------------------------------'

SELECT
    COUNT(*) as creditos_sem_nf_remessa,
    CASE WHEN COUNT(*) = 0 THEN '✅ OK' ELSE '❌ ERRO' END as status
FROM pallet_creditos c
LEFT JOIN pallet_nf_remessa nfr ON c.nf_remessa_id = nfr.id
WHERE nfr.id IS NULL;

-- Detalhes dos órfãos (se houver)
\echo 'Detalhes (primeiros 10 órfãos):'
SELECT c.id, c.nf_remessa_id, c.cnpj_responsavel, c.qtd_original
FROM pallet_creditos c
LEFT JOIN pallet_nf_remessa nfr ON c.nf_remessa_id = nfr.id
WHERE nfr.id IS NULL
LIMIT 10;

\echo ''

-- ============================================================================
-- VERIFICAÇÃO 4: FK DOCUMENTOS → CRÉDITOS
-- ============================================================================
\echo '📋 VERIFICAÇÃO 4: FK Documentos → Créditos'
\echo '----------------------------------------------------------------------'

SELECT
    COUNT(*) as documentos_sem_credito,
    CASE WHEN COUNT(*) = 0 THEN '✅ OK' ELSE '❌ ERRO' END as status
FROM pallet_documentos d
LEFT JOIN pallet_creditos c ON d.credito_id = c.id
WHERE c.id IS NULL;

\echo ''

-- ============================================================================
-- VERIFICAÇÃO 5: FK SOLUÇÕES → CRÉDITOS
-- ============================================================================
\echo '📋 VERIFICAÇÃO 5: FK Soluções → Créditos'
\echo '----------------------------------------------------------------------'

SELECT
    COUNT(*) as solucoes_sem_credito,
    CASE WHEN COUNT(*) = 0 THEN '✅ OK' ELSE '❌ ERRO' END as status
FROM pallet_solucoes s
LEFT JOIN pallet_creditos c ON s.credito_id = c.id
WHERE c.id IS NULL;

\echo ''

-- ============================================================================
-- VERIFICAÇÃO 6: FK SOLUÇÕES NF → NF REMESSA
-- ============================================================================
\echo '📋 VERIFICAÇÃO 6: FK Soluções NF → NF Remessa'
\echo '----------------------------------------------------------------------'

SELECT
    COUNT(*) as solucoes_nf_sem_nf_remessa,
    CASE WHEN COUNT(*) = 0 THEN '✅ OK' ELSE '❌ ERRO' END as status
FROM pallet_nf_solucoes ns
LEFT JOIN pallet_nf_remessa nfr ON ns.nf_remessa_id = nfr.id
WHERE nfr.id IS NULL;

\echo ''

-- ============================================================================
-- VERIFICAÇÃO 7: SALDO <= ORIGINAL (CRÉDITOS)
-- ============================================================================
\echo '📋 VERIFICAÇÃO 7: Saldo <= Original (Créditos)'
\echo '----------------------------------------------------------------------'

SELECT
    COUNT(*) as creditos_saldo_invalido,
    CASE WHEN COUNT(*) = 0 THEN '✅ OK' ELSE '❌ ERRO' END as status
FROM pallet_creditos
WHERE qtd_saldo > qtd_original;

-- Detalhes (se houver)
\echo 'Detalhes (saldo > original):'
SELECT id, cnpj_responsavel, qtd_original, qtd_saldo, status
FROM pallet_creditos
WHERE qtd_saldo > qtd_original
LIMIT 10;

\echo ''

-- ============================================================================
-- VERIFICAÇÃO 8: STATUS VS SALDO
-- ============================================================================
\echo '📋 VERIFICAÇÃO 8: Status vs Saldo'
\echo '----------------------------------------------------------------------'

-- RESOLVIDO com saldo > 0
SELECT
    'RESOLVIDO com saldo > 0' as problema,
    COUNT(*) as quantidade,
    CASE WHEN COUNT(*) = 0 THEN '✅ OK' ELSE '⚠️ AVISO' END as status
FROM pallet_creditos
WHERE status = 'RESOLVIDO' AND qtd_saldo > 0;

-- PENDENTE que deveria ser PARCIAL
SELECT
    'PENDENTE deveria ser PARCIAL' as problema,
    COUNT(*) as quantidade,
    CASE WHEN COUNT(*) = 0 THEN '✅ OK' ELSE '⚠️ AVISO' END as status
FROM pallet_creditos
WHERE status = 'PENDENTE' AND qtd_saldo < qtd_original AND qtd_saldo > 0;

\echo ''

-- ============================================================================
-- VERIFICAÇÃO 9: SOMA SOLUÇÕES <= ORIGINAL
-- ============================================================================
\echo '📋 VERIFICAÇÃO 9: Soma Soluções <= Original'
\echo '----------------------------------------------------------------------'

SELECT
    COUNT(*) as creditos_soma_excedente,
    CASE WHEN COUNT(*) = 0 THEN '✅ OK' ELSE '❌ ERRO' END as status
FROM (
    SELECT c.id, c.qtd_original, COALESCE(SUM(s.quantidade), 0) as total_solucoes
    FROM pallet_creditos c
    LEFT JOIN pallet_solucoes s ON s.credito_id = c.id
    GROUP BY c.id, c.qtd_original
    HAVING COALESCE(SUM(s.quantidade), 0) > c.qtd_original
) sub;

\echo ''

-- ============================================================================
-- VERIFICAÇÃO 10: MIGRAÇÃO MOVIMENTAÇÃOESTOQUE
-- ============================================================================
\echo '📋 VERIFICAÇÃO 10: Migração MovimentacaoEstoque → NF Remessa'
\echo '----------------------------------------------------------------------'

SELECT
    (SELECT COUNT(*) FROM movimentacao_estoque
     WHERE local_movimentacao = 'PALLET' AND tipo_movimentacao = 'REMESSA' AND ativo = TRUE) as fonte,
    (SELECT COUNT(*) FROM pallet_nf_remessa WHERE movimentacao_estoque_id IS NOT NULL) as migrados,
    (SELECT COUNT(*) FROM pallet_nf_remessa) as total_destino;

-- Percentual
SELECT
    ROUND(
        (SELECT COUNT(*)::numeric FROM pallet_nf_remessa WHERE movimentacao_estoque_id IS NOT NULL) /
        NULLIF((SELECT COUNT(*)::numeric FROM movimentacao_estoque
                WHERE local_movimentacao = 'PALLET' AND tipo_movimentacao = 'REMESSA' AND ativo = TRUE), 0) * 100,
        1
    ) as percentual_migrado;

\echo ''

-- ============================================================================
-- VERIFICAÇÃO 11: MIGRAÇÃO VALEPALLET
-- ============================================================================
\echo '📋 VERIFICAÇÃO 11: Migração ValePallet → Documentos'
\echo '----------------------------------------------------------------------'

SELECT
    (SELECT COUNT(*) FROM vale_pallets WHERE ativo = TRUE) as fonte,
    (SELECT COUNT(*) FROM pallet_documentos WHERE vale_pallet_id IS NOT NULL) as migrados,
    (SELECT COUNT(*) FROM pallet_documentos) as total_destino;

-- Sem crédito correspondente
SELECT
    COUNT(*) as vales_sem_credito
FROM vale_pallets vp
WHERE vp.ativo = TRUE
  AND NOT EXISTS (
      SELECT 1 FROM pallet_nf_remessa nfr
      WHERE nfr.numero_nf = vp.nf_pallet
  );

\echo ''

-- ============================================================================
-- VERIFICAÇÃO 12: TOTAIS DE QUANTIDADES
-- ============================================================================
\echo '📋 VERIFICAÇÃO 12: Totais de Quantidades'
\echo '----------------------------------------------------------------------'

SELECT
    'NF Remessa (quantidade)' as origem,
    COALESCE(SUM(quantidade), 0) as total
FROM pallet_nf_remessa WHERE ativo = TRUE
UNION ALL
SELECT
    'Créditos (original)',
    COALESCE(SUM(qtd_original), 0)
FROM pallet_creditos WHERE ativo = TRUE
UNION ALL
SELECT
    'Créditos (saldo)',
    COALESCE(SUM(qtd_saldo), 0)
FROM pallet_creditos WHERE ativo = TRUE
UNION ALL
SELECT
    'Soluções (quantidade)',
    COALESCE(SUM(quantidade), 0)
FROM pallet_solucoes WHERE ativo = TRUE;

-- Consistência: Original - Soluções = Saldo?
SELECT
    (SELECT COALESCE(SUM(qtd_original), 0) FROM pallet_creditos WHERE ativo = TRUE) as original,
    (SELECT COALESCE(SUM(quantidade), 0) FROM pallet_solucoes WHERE ativo = TRUE) as solucoes,
    (SELECT COALESCE(SUM(qtd_original), 0) FROM pallet_creditos WHERE ativo = TRUE) -
    (SELECT COALESCE(SUM(quantidade), 0) FROM pallet_solucoes WHERE ativo = TRUE) as saldo_esperado,
    (SELECT COALESCE(SUM(qtd_saldo), 0) FROM pallet_creditos WHERE ativo = TRUE) as saldo_atual,
    CASE
        WHEN (SELECT COALESCE(SUM(qtd_original), 0) FROM pallet_creditos WHERE ativo = TRUE) -
             (SELECT COALESCE(SUM(quantidade), 0) FROM pallet_solucoes WHERE ativo = TRUE) =
             (SELECT COALESCE(SUM(qtd_saldo), 0) FROM pallet_creditos WHERE ativo = TRUE)
        THEN '✅ OK'
        ELSE '⚠️ DIVERGÊNCIA'
    END as status;

\echo ''

-- ============================================================================
-- VERIFICAÇÃO 13: NFS DUPLICADAS
-- ============================================================================
\echo '📋 VERIFICAÇÃO 13: NFs Remessa Duplicadas'
\echo '----------------------------------------------------------------------'

SELECT
    numero_nf,
    serie,
    COUNT(*) as qtd,
    '❌ DUPLICADA' as status
FROM pallet_nf_remessa
WHERE ativo = TRUE
GROUP BY numero_nf, serie
HAVING COUNT(*) > 1
LIMIT 20;

SELECT
    COUNT(DISTINCT numero_nf) as nfs_unicas,
    COUNT(*) as total_registros,
    CASE
        WHEN COUNT(DISTINCT numero_nf) = COUNT(*) THEN '✅ SEM DUPLICATAS'
        ELSE '❌ HÁ DUPLICATAS'
    END as status
FROM pallet_nf_remessa
WHERE ativo = TRUE;

\echo ''

-- ============================================================================
-- VERIFICAÇÃO 14: FORMATO CNPJ
-- ============================================================================
\echo '📋 VERIFICAÇÃO 14: Formato de CNPJs'
\echo '----------------------------------------------------------------------'

SELECT
    'NF Remessa' as tabela,
    COUNT(*) as cnpjs_invalidos,
    CASE WHEN COUNT(*) = 0 THEN '✅ OK' ELSE '⚠️ AVISO' END as status
FROM pallet_nf_remessa
WHERE cnpj_destinatario IS NOT NULL
  AND LENGTH(REGEXP_REPLACE(cnpj_destinatario, '[^0-9]', '', 'g')) NOT IN (11, 14)
  AND cnpj_destinatario != ''
UNION ALL
SELECT
    'Créditos',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN '✅ OK' ELSE '⚠️ AVISO' END
FROM pallet_creditos
WHERE cnpj_responsavel IS NOT NULL
  AND LENGTH(REGEXP_REPLACE(cnpj_responsavel, '[^0-9]', '', 'g')) NOT IN (11, 14)
  AND cnpj_responsavel != '';

\echo ''

-- ============================================================================
-- RESUMO FINAL
-- ============================================================================
\echo '======================================================================'
\echo ' RESUMO DA VALIDAÇÃO'
\echo '======================================================================'

WITH checks AS (
    -- FK Créditos → NF Remessa
    SELECT 'FK Créditos → NF Remessa' as check_name,
           CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'ERRO' END as resultado
    FROM pallet_creditos c
    LEFT JOIN pallet_nf_remessa nfr ON c.nf_remessa_id = nfr.id
    WHERE nfr.id IS NULL

    UNION ALL

    -- FK Documentos → Créditos
    SELECT 'FK Documentos → Créditos',
           CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'ERRO' END
    FROM pallet_documentos d
    LEFT JOIN pallet_creditos c ON d.credito_id = c.id
    WHERE c.id IS NULL

    UNION ALL

    -- FK Soluções → Créditos
    SELECT 'FK Soluções → Créditos',
           CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'ERRO' END
    FROM pallet_solucoes s
    LEFT JOIN pallet_creditos c ON s.credito_id = c.id
    WHERE c.id IS NULL

    UNION ALL

    -- Saldo <= Original
    SELECT 'Saldo <= Original',
           CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'ERRO' END
    FROM pallet_creditos
    WHERE qtd_saldo > qtd_original

    UNION ALL

    -- NFs Duplicadas
    SELECT 'NFs Duplicadas',
           CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'ERRO' END
    FROM (
        SELECT numero_nf, serie
        FROM pallet_nf_remessa
        WHERE ativo = TRUE
        GROUP BY numero_nf, serie
        HAVING COUNT(*) > 1
    ) sub
)
SELECT
    check_name as verificacao,
    CASE resultado
        WHEN 'OK' THEN '✅ OK'
        WHEN 'ERRO' THEN '❌ ERRO'
        ELSE '⚠️ ' || resultado
    END as status
FROM checks;

\echo ''
\echo '======================================================================'
\echo ' FIM DA VALIDAÇÃO'
\echo '======================================================================'
\echo ''
