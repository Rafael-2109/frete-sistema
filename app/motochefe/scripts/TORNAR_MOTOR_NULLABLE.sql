-- =====================================================
-- SQL PARA RENDER (PostgreSQL Production)
-- Tornar numero_motor NULLABLE mantendo UNIQUE
-- =====================================================
-- Data: 2025-10-05
-- Descrição: Permite que numero_motor seja NULL, mas se preenchido deve ser único
-- =====================================================

-- 1. Verificar estado atual da coluna
SELECT
    column_name,
    data_type,
    is_nullable,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'moto'
AND column_name = 'numero_motor';

-- Resultado esperado ANTES:
-- column_name  | data_type         | is_nullable | character_maximum_length
-- numero_motor | character varying | NO          | 50

-- =====================================================
-- 2. ALTERAR COLUNA PARA NULLABLE
-- =====================================================
ALTER TABLE moto
ALTER COLUMN numero_motor DROP NOT NULL;

-- ⚠️ IMPORTANTE: A constraint UNIQUE é mantida automaticamente!
-- PostgreSQL permite múltiplos NULLs em colunas UNIQUE, mas valores não-NULL devem ser únicos

-- =====================================================
-- 3. VALIDAR ALTERAÇÃO
-- =====================================================
SELECT
    column_name,
    data_type,
    is_nullable,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'moto'
AND column_name = 'numero_motor';

-- Resultado esperado DEPOIS:
-- column_name  | data_type         | is_nullable | character_maximum_length
-- numero_motor | character varying | YES         | 50

-- =====================================================
-- 4. VERIFICAR CONSTRAINT UNIQUE (deve estar presente)
-- =====================================================
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_name = 'moto'
AND kcu.column_name = 'numero_motor'
AND tc.constraint_type = 'UNIQUE';

-- Deve retornar algo como:
-- constraint_name           | constraint_type | column_name
-- moto_numero_motor_key     | UNIQUE         | numero_motor

-- =====================================================
-- 5. TESTAR COMPORTAMENTO (OPCIONAL)
-- =====================================================

-- Teste 1: Múltiplos NULLs são permitidos ✅
-- INSERT INTO moto (..., numero_motor, ...) VALUES (..., NULL, ...);
-- INSERT INTO moto (..., numero_motor, ...) VALUES (..., NULL, ...);
-- Ambos devem funcionar!

-- Teste 2: Valores duplicados NÃO são permitidos ❌
-- INSERT INTO moto (..., numero_motor, ...) VALUES (..., 'MOT123', ...);
-- INSERT INTO moto (..., numero_motor, ...) VALUES (..., 'MOT123', ...);
-- Segundo deve falhar com: ERROR: duplicate key value violates unique constraint

-- =====================================================
-- ROLLBACK (caso necessário desfazer)
-- =====================================================
-- ⚠️ ATENÇÃO: Só execute se precisar REVERTER a alteração!

-- ALTER TABLE moto
-- ALTER COLUMN numero_motor SET NOT NULL;

-- ⚠️ CUIDADO: Isso vai FALHAR se já existirem registros com numero_motor NULL!
-- Você teria que preencher todos os NULLs antes de reverter.

-- =====================================================
-- EXPLICAÇÃO TÉCNICA
-- =====================================================

-- PostgreSQL permite múltiplos valores NULL em colunas UNIQUE porque:
-- - NULL significa "valor desconhecido"
-- - NULL != NULL (dois valores desconhecidos não são comparáveis)
-- - Portanto, múltiplos NULLs não violam a constraint UNIQUE

-- Comportamento:
-- ✅ numero_motor = NULL         → PERMITIDO (múltiplos)
-- ✅ numero_motor = 'MOT123'     → PERMITIDO (se único)
-- ❌ numero_motor = 'MOT123'     → BLOQUEADO (se já existe outro 'MOT123')

-- =====================================================
-- FIM DO SCRIPT
-- =====================================================
