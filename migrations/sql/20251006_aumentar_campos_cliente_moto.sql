-- =====================================================
-- Migration: Aumentar limites de campos em ClienteMoto
-- Data: 2025-10-06
-- Descrição: Aumenta telefone_cliente (20→100) e cep_cliente (10→15)
--            para suportar múltiplos telefones e formatos diversos de CEP
-- =====================================================

-- VERIFICAR TAMANHOS ATUAIS
-- =====================================================
SELECT
    column_name,
    character_maximum_length as tamanho_atual
FROM information_schema.columns
WHERE table_name = 'cliente_moto'
AND column_name IN ('telefone_cliente', 'cep_cliente')
ORDER BY column_name;


-- VERIFICAR DADOS QUE SERIAM AFETADOS
-- =====================================================
SELECT
    COUNT(*) as total_clientes,
    SUM(CASE WHEN LENGTH(telefone_cliente) > 20 THEN 1 ELSE 0 END) as telefones_acima_20_chars,
    SUM(CASE WHEN LENGTH(cep_cliente) > 10 THEN 1 ELSE 0 END) as ceps_acima_10_chars,
    MAX(LENGTH(telefone_cliente)) as telefone_mais_longo,
    MAX(LENGTH(cep_cliente)) as cep_mais_longo
FROM cliente_moto
WHERE telefone_cliente IS NOT NULL OR cep_cliente IS NOT NULL;


-- EXECUTAR MIGRATION
-- =====================================================

-- 1. Aumentar campo telefone_cliente (20 → 100)
ALTER TABLE cliente_moto
ALTER COLUMN telefone_cliente TYPE VARCHAR(100);

-- 2. Aumentar campo cep_cliente (10 → 15)
ALTER TABLE cliente_moto
ALTER COLUMN cep_cliente TYPE VARCHAR(15);


-- VERIFICAR RESULTADO
-- =====================================================
SELECT
    column_name,
    character_maximum_length as novo_tamanho
FROM information_schema.columns
WHERE table_name = 'cliente_moto'
AND column_name IN ('telefone_cliente', 'cep_cliente')
ORDER BY column_name;


-- =====================================================
-- ROLLBACK (se necessário):
-- ⚠️ ATENÇÃO: Dados que excederem os limites originais
--             serão TRUNCADOS automaticamente!
-- =====================================================
-- ALTER TABLE cliente_moto
-- ALTER COLUMN telefone_cliente TYPE VARCHAR(20);
--
-- ALTER TABLE cliente_moto
-- ALTER COLUMN cep_cliente TYPE VARCHAR(10);
-- =====================================================
