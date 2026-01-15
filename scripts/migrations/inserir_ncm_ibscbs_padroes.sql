-- ============================================================================
-- Script SQL: Cadastro de Padrões NCM IBS/CBS
-- ============================================================================
-- Data: 2026-01-15
-- Descrição: Insere os padrões de NCM validados para IBS/CBS na tabela
--            ncm_ibscbs_validado, usados para validação fiscal de NF-e
--
-- Classificações Tributárias:
--   000001 = Tributação integral (CST 000)
--   200034 = Fornecimento dos alimentos destinados ao consumo humano (CST 200)
--   200038 = Fornecimento dos insumos agropecuários e aquícolas (CST 200)
--
-- Executar no Shell do Render ou localmente
-- ============================================================================

-- Limpar registros existentes (opcional - descomente se necessário)
-- DELETE FROM ncm_ibscbs_validado;

-- ============================================================================
-- GRUPO 1: Alimentos (CST 200, ClassTrib 200034, Redução 60%)
-- ============================================================================

-- Prefixo 0711 - Produtos hortícolas, cogumelos
INSERT INTO ncm_ibscbs_validado (
    ncm_prefixo, descricao_ncm, cst_esperado, class_trib_codigo,
    aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs, reducao_aliquota,
    ativo, validado_por, validado_em, criado_em
) VALUES (
    '0711', 'Produtos hortícolas, cogumelos - conservados provisoriamente',
    '200', '200034', 0.10, 0.00, 0.90, 60.00,
    true, 'SISTEMA', NOW(), NOW()
) ON CONFLICT (ncm_prefixo) DO UPDATE SET
    descricao_ncm = EXCLUDED.descricao_ncm,
    cst_esperado = EXCLUDED.cst_esperado,
    class_trib_codigo = EXCLUDED.class_trib_codigo,
    aliquota_ibs_uf = EXCLUDED.aliquota_ibs_uf,
    aliquota_ibs_mun = EXCLUDED.aliquota_ibs_mun,
    aliquota_cbs = EXCLUDED.aliquota_cbs,
    reducao_aliquota = EXCLUDED.reducao_aliquota,
    ativo = EXCLUDED.ativo,
    validado_por = EXCLUDED.validado_por,
    validado_em = EXCLUDED.validado_em,
    atualizado_em = NOW();

-- Prefixo 1507 - Óleo de soja
INSERT INTO ncm_ibscbs_validado (
    ncm_prefixo, descricao_ncm, cst_esperado, class_trib_codigo,
    aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs, reducao_aliquota,
    ativo, validado_por, validado_em, criado_em
) VALUES (
    '1507', 'Óleo de soja e suas frações',
    '200', '200034', 0.10, 0.00, 0.90, 60.00,
    true, 'SISTEMA', NOW(), NOW()
) ON CONFLICT (ncm_prefixo) DO UPDATE SET
    descricao_ncm = EXCLUDED.descricao_ncm,
    cst_esperado = EXCLUDED.cst_esperado,
    class_trib_codigo = EXCLUDED.class_trib_codigo,
    aliquota_ibs_uf = EXCLUDED.aliquota_ibs_uf,
    aliquota_ibs_mun = EXCLUDED.aliquota_ibs_mun,
    aliquota_cbs = EXCLUDED.aliquota_cbs,
    reducao_aliquota = EXCLUDED.reducao_aliquota,
    ativo = EXCLUDED.ativo,
    validado_por = EXCLUDED.validado_por,
    validado_em = EXCLUDED.validado_em,
    atualizado_em = NOW();

-- Prefixo 2002 - Tomates preparados ou conservados
INSERT INTO ncm_ibscbs_validado (
    ncm_prefixo, descricao_ncm, cst_esperado, class_trib_codigo,
    aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs, reducao_aliquota,
    ativo, validado_por, validado_em, criado_em
) VALUES (
    '2002', 'Tomates preparados ou conservados',
    '200', '200034', 0.10, 0.00, 0.90, 60.00,
    true, 'SISTEMA', NOW(), NOW()
) ON CONFLICT (ncm_prefixo) DO UPDATE SET
    descricao_ncm = EXCLUDED.descricao_ncm,
    cst_esperado = EXCLUDED.cst_esperado,
    class_trib_codigo = EXCLUDED.class_trib_codigo,
    aliquota_ibs_uf = EXCLUDED.aliquota_ibs_uf,
    aliquota_ibs_mun = EXCLUDED.aliquota_ibs_mun,
    aliquota_cbs = EXCLUDED.aliquota_cbs,
    reducao_aliquota = EXCLUDED.reducao_aliquota,
    ativo = EXCLUDED.ativo,
    validado_por = EXCLUDED.validado_por,
    validado_em = EXCLUDED.validado_em,
    atualizado_em = NOW();

-- Prefixo 2005 - Outros produtos hortícolas preparados ou conservados
INSERT INTO ncm_ibscbs_validado (
    ncm_prefixo, descricao_ncm, cst_esperado, class_trib_codigo,
    aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs, reducao_aliquota,
    ativo, validado_por, validado_em, criado_em
) VALUES (
    '2005', 'Outros produtos hortícolas preparados ou conservados',
    '200', '200034', 0.10, 0.00, 0.90, 60.00,
    true, 'SISTEMA', NOW(), NOW()
) ON CONFLICT (ncm_prefixo) DO UPDATE SET
    descricao_ncm = EXCLUDED.descricao_ncm,
    cst_esperado = EXCLUDED.cst_esperado,
    class_trib_codigo = EXCLUDED.class_trib_codigo,
    aliquota_ibs_uf = EXCLUDED.aliquota_ibs_uf,
    aliquota_ibs_mun = EXCLUDED.aliquota_ibs_mun,
    aliquota_cbs = EXCLUDED.aliquota_cbs,
    reducao_aliquota = EXCLUDED.reducao_aliquota,
    ativo = EXCLUDED.ativo,
    validado_por = EXCLUDED.validado_por,
    validado_em = EXCLUDED.validado_em,
    atualizado_em = NOW();

-- Prefixo 2008 - Frutas e outras partes de plantas preparadas ou conservadas
INSERT INTO ncm_ibscbs_validado (
    ncm_prefixo, descricao_ncm, cst_esperado, class_trib_codigo,
    aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs, reducao_aliquota,
    ativo, validado_por, validado_em, criado_em
) VALUES (
    '2008', 'Frutas e outras partes de plantas preparadas ou conservadas',
    '200', '200034', 0.10, 0.00, 0.90, 60.00,
    true, 'SISTEMA', NOW(), NOW()
) ON CONFLICT (ncm_prefixo) DO UPDATE SET
    descricao_ncm = EXCLUDED.descricao_ncm,
    cst_esperado = EXCLUDED.cst_esperado,
    class_trib_codigo = EXCLUDED.class_trib_codigo,
    aliquota_ibs_uf = EXCLUDED.aliquota_ibs_uf,
    aliquota_ibs_mun = EXCLUDED.aliquota_ibs_mun,
    aliquota_cbs = EXCLUDED.aliquota_cbs,
    reducao_aliquota = EXCLUDED.reducao_aliquota,
    ativo = EXCLUDED.ativo,
    validado_por = EXCLUDED.validado_por,
    validado_em = EXCLUDED.validado_em,
    atualizado_em = NOW();

-- ============================================================================
-- GRUPO 2: Tributação Integral (CST 000, ClassTrib 000001, Sem Redução)
-- ============================================================================

-- Prefixo 1509 - Azeite de oliva e suas frações
INSERT INTO ncm_ibscbs_validado (
    ncm_prefixo, descricao_ncm, cst_esperado, class_trib_codigo,
    aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs, reducao_aliquota,
    ativo, validado_por, validado_em, criado_em
) VALUES (
    '1509', 'Azeite de oliva e suas frações',
    '000', '000001', 0.10, 0.00, 0.90, 0.00,
    true, 'SISTEMA', NOW(), NOW()
) ON CONFLICT (ncm_prefixo) DO UPDATE SET
    descricao_ncm = EXCLUDED.descricao_ncm,
    cst_esperado = EXCLUDED.cst_esperado,
    class_trib_codigo = EXCLUDED.class_trib_codigo,
    aliquota_ibs_uf = EXCLUDED.aliquota_ibs_uf,
    aliquota_ibs_mun = EXCLUDED.aliquota_ibs_mun,
    aliquota_cbs = EXCLUDED.aliquota_cbs,
    reducao_aliquota = EXCLUDED.reducao_aliquota,
    ativo = EXCLUDED.ativo,
    validado_por = EXCLUDED.validado_por,
    validado_em = EXCLUDED.validado_em,
    atualizado_em = NOW();

-- Prefixo 1517 - Margarina e misturas de óleos
INSERT INTO ncm_ibscbs_validado (
    ncm_prefixo, descricao_ncm, cst_esperado, class_trib_codigo,
    aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs, reducao_aliquota,
    ativo, validado_por, validado_em, criado_em
) VALUES (
    '1517', 'Margarina e misturas de óleos ou gorduras',
    '000', '000001', 0.10, 0.00, 0.90, 0.00,
    true, 'SISTEMA', NOW(), NOW()
) ON CONFLICT (ncm_prefixo) DO UPDATE SET
    descricao_ncm = EXCLUDED.descricao_ncm,
    cst_esperado = EXCLUDED.cst_esperado,
    class_trib_codigo = EXCLUDED.class_trib_codigo,
    aliquota_ibs_uf = EXCLUDED.aliquota_ibs_uf,
    aliquota_ibs_mun = EXCLUDED.aliquota_ibs_mun,
    aliquota_cbs = EXCLUDED.aliquota_cbs,
    reducao_aliquota = EXCLUDED.reducao_aliquota,
    ativo = EXCLUDED.ativo,
    validado_por = EXCLUDED.validado_por,
    validado_em = EXCLUDED.validado_em,
    atualizado_em = NOW();

-- Prefixo 2003 - Cogumelos e trufas preparados ou conservados
INSERT INTO ncm_ibscbs_validado (
    ncm_prefixo, descricao_ncm, cst_esperado, class_trib_codigo,
    aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs, reducao_aliquota,
    ativo, validado_por, validado_em, criado_em
) VALUES (
    '2003', 'Cogumelos e trufas preparados ou conservados',
    '000', '000001', 0.10, 0.00, 0.90, 0.00,
    true, 'SISTEMA', NOW(), NOW()
) ON CONFLICT (ncm_prefixo) DO UPDATE SET
    descricao_ncm = EXCLUDED.descricao_ncm,
    cst_esperado = EXCLUDED.cst_esperado,
    class_trib_codigo = EXCLUDED.class_trib_codigo,
    aliquota_ibs_uf = EXCLUDED.aliquota_ibs_uf,
    aliquota_ibs_mun = EXCLUDED.aliquota_ibs_mun,
    aliquota_cbs = EXCLUDED.aliquota_cbs,
    reducao_aliquota = EXCLUDED.reducao_aliquota,
    ativo = EXCLUDED.ativo,
    validado_por = EXCLUDED.validado_por,
    validado_em = EXCLUDED.validado_em,
    atualizado_em = NOW();

-- Prefixo 2007 - Doces, geleias, marmelades e purês de frutas
INSERT INTO ncm_ibscbs_validado (
    ncm_prefixo, descricao_ncm, cst_esperado, class_trib_codigo,
    aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs, reducao_aliquota,
    ativo, validado_por, validado_em, criado_em
) VALUES (
    '2007', 'Doces, geleias, marmelades e purês de frutas',
    '000', '000001', 0.10, 0.00, 0.90, 0.00,
    true, 'SISTEMA', NOW(), NOW()
) ON CONFLICT (ncm_prefixo) DO UPDATE SET
    descricao_ncm = EXCLUDED.descricao_ncm,
    cst_esperado = EXCLUDED.cst_esperado,
    class_trib_codigo = EXCLUDED.class_trib_codigo,
    aliquota_ibs_uf = EXCLUDED.aliquota_ibs_uf,
    aliquota_ibs_mun = EXCLUDED.aliquota_ibs_mun,
    aliquota_cbs = EXCLUDED.aliquota_cbs,
    reducao_aliquota = EXCLUDED.reducao_aliquota,
    ativo = EXCLUDED.ativo,
    validado_por = EXCLUDED.validado_por,
    validado_em = EXCLUDED.validado_em,
    atualizado_em = NOW();

-- Prefixo 2103 - Preparações para molhos, molhos preparados, condimentos
INSERT INTO ncm_ibscbs_validado (
    ncm_prefixo, descricao_ncm, cst_esperado, class_trib_codigo,
    aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs, reducao_aliquota,
    ativo, validado_por, validado_em, criado_em
) VALUES (
    '2103', 'Preparações para molhos, molhos preparados, condimentos',
    '000', '000001', 0.10, 0.00, 0.90, 0.00,
    true, 'SISTEMA', NOW(), NOW()
) ON CONFLICT (ncm_prefixo) DO UPDATE SET
    descricao_ncm = EXCLUDED.descricao_ncm,
    cst_esperado = EXCLUDED.cst_esperado,
    class_trib_codigo = EXCLUDED.class_trib_codigo,
    aliquota_ibs_uf = EXCLUDED.aliquota_ibs_uf,
    aliquota_ibs_mun = EXCLUDED.aliquota_ibs_mun,
    aliquota_cbs = EXCLUDED.aliquota_cbs,
    reducao_aliquota = EXCLUDED.reducao_aliquota,
    ativo = EXCLUDED.ativo,
    validado_por = EXCLUDED.validado_por,
    validado_em = EXCLUDED.validado_em,
    atualizado_em = NOW();

-- Prefixo 3923 - Artigos de transporte ou embalagem de plásticos
INSERT INTO ncm_ibscbs_validado (
    ncm_prefixo, descricao_ncm, cst_esperado, class_trib_codigo,
    aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs, reducao_aliquota,
    ativo, validado_por, validado_em, criado_em
) VALUES (
    '3923', 'Artigos de transporte ou embalagem de plásticos',
    '000', '000001', 0.10, 0.00, 0.90, 0.00,
    true, 'SISTEMA', NOW(), NOW()
) ON CONFLICT (ncm_prefixo) DO UPDATE SET
    descricao_ncm = EXCLUDED.descricao_ncm,
    cst_esperado = EXCLUDED.cst_esperado,
    class_trib_codigo = EXCLUDED.class_trib_codigo,
    aliquota_ibs_uf = EXCLUDED.aliquota_ibs_uf,
    aliquota_ibs_mun = EXCLUDED.aliquota_ibs_mun,
    aliquota_cbs = EXCLUDED.aliquota_cbs,
    reducao_aliquota = EXCLUDED.reducao_aliquota,
    ativo = EXCLUDED.ativo,
    validado_por = EXCLUDED.validado_por,
    validado_em = EXCLUDED.validado_em,
    atualizado_em = NOW();

-- Prefixo 4411 - Painéis de fibras de madeira
INSERT INTO ncm_ibscbs_validado (
    ncm_prefixo, descricao_ncm, cst_esperado, class_trib_codigo,
    aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs, reducao_aliquota,
    ativo, validado_por, validado_em, criado_em
) VALUES (
    '4411', 'Painéis de fibras de madeira ou outras matérias lenhosas',
    '000', '000001', 0.10, 0.00, 0.90, 0.00,
    true, 'SISTEMA', NOW(), NOW()
) ON CONFLICT (ncm_prefixo) DO UPDATE SET
    descricao_ncm = EXCLUDED.descricao_ncm,
    cst_esperado = EXCLUDED.cst_esperado,
    class_trib_codigo = EXCLUDED.class_trib_codigo,
    aliquota_ibs_uf = EXCLUDED.aliquota_ibs_uf,
    aliquota_ibs_mun = EXCLUDED.aliquota_ibs_mun,
    aliquota_cbs = EXCLUDED.aliquota_cbs,
    reducao_aliquota = EXCLUDED.reducao_aliquota,
    ativo = EXCLUDED.ativo,
    validado_por = EXCLUDED.validado_por,
    validado_em = EXCLUDED.validado_em,
    atualizado_em = NOW();

-- Prefixo 7010 - Garrafões, garrafas, frascos de vidro
INSERT INTO ncm_ibscbs_validado (
    ncm_prefixo, descricao_ncm, cst_esperado, class_trib_codigo,
    aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs, reducao_aliquota,
    ativo, validado_por, validado_em, criado_em
) VALUES (
    '7010', 'Garrafões, garrafas, frascos e outros recipientes de vidro',
    '000', '000001', 0.10, 0.00, 0.90, 0.00,
    true, 'SISTEMA', NOW(), NOW()
) ON CONFLICT (ncm_prefixo) DO UPDATE SET
    descricao_ncm = EXCLUDED.descricao_ncm,
    cst_esperado = EXCLUDED.cst_esperado,
    class_trib_codigo = EXCLUDED.class_trib_codigo,
    aliquota_ibs_uf = EXCLUDED.aliquota_ibs_uf,
    aliquota_ibs_mun = EXCLUDED.aliquota_ibs_mun,
    aliquota_cbs = EXCLUDED.aliquota_cbs,
    reducao_aliquota = EXCLUDED.reducao_aliquota,
    ativo = EXCLUDED.ativo,
    validado_por = EXCLUDED.validado_por,
    validado_em = EXCLUDED.validado_em,
    atualizado_em = NOW();

-- ============================================================================
-- Verificação
-- ============================================================================
SELECT
    ncm_prefixo,
    descricao_ncm,
    cst_esperado,
    class_trib_codigo,
    aliquota_ibs_uf,
    aliquota_ibs_mun,
    aliquota_cbs,
    reducao_aliquota,
    ativo
FROM ncm_ibscbs_validado
ORDER BY ncm_prefixo;
