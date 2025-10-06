-- =====================================================
-- AUMENTAR TAMANHO DO CAMPO numero_chassi DE 17 PARA 30
-- =====================================================
-- Database: PostgreSQL (Render)
-- Tabela: moto
-- Campo: numero_chassi (PRIMARY KEY)
-- Data: 06/10/2025
-- Motivo: Suportar variações de VIN com caracteres extras
-- =====================================================

-- =====================================================
-- 1. VERIFICAR ESTADO ATUAL DA COLUNA
-- =====================================================
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'moto'
AND column_name = 'numero_chassi';

-- Resultado esperado ANTES:
-- column_name   | data_type         | character_maximum_length | is_nullable
-- numero_chassi | character varying | 17                       | NO

-- =====================================================
-- 2. VERIFICAR TAMANHO MÁXIMO DOS CHASSI EXISTENTES
-- =====================================================
SELECT
    MAX(LENGTH(numero_chassi)) as tamanho_maximo_atual,
    MIN(LENGTH(numero_chassi)) as tamanho_minimo_atual,
    COUNT(*) as total_registros
FROM moto;

-- Verificar se algum chassi tem mais de 17 caracteres (causaria erro)
SELECT
    numero_chassi,
    LENGTH(numero_chassi) as tamanho,
    modelo_id,
    cor
FROM moto
WHERE LENGTH(numero_chassi) > 17
ORDER BY LENGTH(numero_chassi) DESC;

-- =====================================================
-- 3. AUMENTAR TAMANHO DA COLUNA DE 17 PARA 30
-- =====================================================
-- ⚠️ Esta operação é SEGURA mesmo com dados existentes
-- ⚠️ PostgreSQL permite aumentar VARCHAR sem perda de dados
-- ⚠️ Operação é rápida pois não reescreve os dados

ALTER TABLE moto
ALTER COLUMN numero_chassi TYPE VARCHAR(30);

-- =====================================================
-- 4. VERIFICAR ALTERAÇÃO APLICADA
-- =====================================================
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'moto'
AND column_name = 'numero_chassi';

-- Resultado esperado APÓS:
-- column_name   | data_type         | character_maximum_length | is_nullable
-- numero_chassi | character varying | 30                       | NO

-- =====================================================
-- 5. VERIFICAR CONSTRAINT DE PRIMARY KEY
-- =====================================================
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    tc.table_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_name = 'moto'
AND tc.constraint_type = 'PRIMARY KEY';

-- =====================================================
-- 6. VERIFICAR INTEGRIDADE DOS DADOS
-- =====================================================
-- Confirmar que todos os registros continuam acessíveis
SELECT
    COUNT(*) as total_motos,
    COUNT(DISTINCT numero_chassi) as chassi_unicos,
    COUNT(DISTINCT modelo_id) as modelos_diferentes
FROM moto
WHERE ativo = true;

-- =====================================================
-- ROLLBACK (SE NECESSÁRIO)
-- =====================================================
-- ⚠️ APENAS EXECUTAR EM CASO DE PROBLEMA
-- ⚠️ ISSO REDUZIRÁ O TAMANHO DE VOLTA PARA 17
-- ⚠️ FALHARÁ SE EXISTIR ALGUM CHASSI COM MAIS DE 17 CHARS

-- ALTER TABLE moto
-- ALTER COLUMN numero_chassi TYPE VARCHAR(17);

-- =====================================================
-- NOTAS IMPORTANTES
-- =====================================================
-- ✅ Operação é SEGURA e RÁPIDA
-- ✅ NÃO causa downtime
-- ✅ NÃO perde dados existentes
-- ✅ NÃO afeta índices ou constraints
-- ✅ PRIMARY KEY continua funcionando normalmente
-- ✅ Compatível com PostgreSQL 9.6+

-- ⚠️ IMPORTANTE: Após executar, atualizar o modelo Python:
--    db.Column(db.String(30), primary_key=True)

-- =====================================================
-- FIM DO SCRIPT
-- =====================================================
