-- Migration: Refatorar SELECTs da Area Comercial - Ocorrencias
-- SQL idempotente para Render Shell
-- Criado em: 21/02/2026

-- =============================================================================
-- 1. TABELAS LOOKUP (5 tabelas com mesmo padrao)
-- =============================================================================

CREATE TABLE IF NOT EXISTS ocorrencia_categoria (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    descricao VARCHAR(255) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por VARCHAR(100) DEFAULT 'migration',
    atualizado_em TIMESTAMP DEFAULT NOW(),
    atualizado_por VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS ocorrencia_subcategoria (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    descricao VARCHAR(255) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por VARCHAR(100) DEFAULT 'migration',
    atualizado_em TIMESTAMP DEFAULT NOW(),
    atualizado_por VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS ocorrencia_responsavel (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    descricao VARCHAR(255) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por VARCHAR(100) DEFAULT 'migration',
    atualizado_em TIMESTAMP DEFAULT NOW(),
    atualizado_por VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS ocorrencia_origem (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    descricao VARCHAR(255) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por VARCHAR(100) DEFAULT 'migration',
    atualizado_em TIMESTAMP DEFAULT NOW(),
    atualizado_por VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS ocorrencia_autorizado_por (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    descricao VARCHAR(255) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por VARCHAR(100) DEFAULT 'migration',
    atualizado_em TIMESTAMP DEFAULT NOW(),
    atualizado_por VARCHAR(100)
);

-- =============================================================================
-- 2. TABELAS DE JUNCAO (N:M)
-- =============================================================================

CREATE TABLE IF NOT EXISTS ocorrencia_devolucao_categoria (
    id SERIAL PRIMARY KEY,
    ocorrencia_devolucao_id INTEGER NOT NULL REFERENCES ocorrencia_devolucao(id) ON DELETE CASCADE,
    categoria_id INTEGER NOT NULL REFERENCES ocorrencia_categoria(id) ON DELETE CASCADE,
    UNIQUE(ocorrencia_devolucao_id, categoria_id)
);
CREATE INDEX IF NOT EXISTS idx_odc_ocorrencia ON ocorrencia_devolucao_categoria(ocorrencia_devolucao_id);
CREATE INDEX IF NOT EXISTS idx_odc_categoria ON ocorrencia_devolucao_categoria(categoria_id);

CREATE TABLE IF NOT EXISTS ocorrencia_devolucao_subcategoria (
    id SERIAL PRIMARY KEY,
    ocorrencia_devolucao_id INTEGER NOT NULL REFERENCES ocorrencia_devolucao(id) ON DELETE CASCADE,
    subcategoria_id INTEGER NOT NULL REFERENCES ocorrencia_subcategoria(id) ON DELETE CASCADE,
    UNIQUE(ocorrencia_devolucao_id, subcategoria_id)
);
CREATE INDEX IF NOT EXISTS idx_ods_ocorrencia ON ocorrencia_devolucao_subcategoria(ocorrencia_devolucao_id);
CREATE INDEX IF NOT EXISTS idx_ods_subcategoria ON ocorrencia_devolucao_subcategoria(subcategoria_id);

-- =============================================================================
-- 3. FK COLUMNS em ocorrencia_devolucao
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'ocorrencia_devolucao' AND column_name = 'responsavel_id'
    ) THEN
        ALTER TABLE ocorrencia_devolucao ADD COLUMN responsavel_id INTEGER REFERENCES ocorrencia_responsavel(id);
        CREATE INDEX idx_ocorrencia_responsavel_id ON ocorrencia_devolucao(responsavel_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'ocorrencia_devolucao' AND column_name = 'origem_id'
    ) THEN
        ALTER TABLE ocorrencia_devolucao ADD COLUMN origem_id INTEGER REFERENCES ocorrencia_origem(id);
        CREATE INDEX idx_ocorrencia_origem_id ON ocorrencia_devolucao(origem_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'ocorrencia_devolucao' AND column_name = 'autorizado_por_id'
    ) THEN
        ALTER TABLE ocorrencia_devolucao ADD COLUMN autorizado_por_id INTEGER REFERENCES ocorrencia_autorizado_por(id);
        CREATE INDEX idx_ocorrencia_autorizado_por_id ON ocorrencia_devolucao(autorizado_por_id);
    END IF;
END $$;

-- =============================================================================
-- 4. MIGRAR DADOS EXISTENTES (sem seed — usuario popula via CRUD modal)
-- =============================================================================

-- Categoria varchar -> junction (so funciona se ja existir o registro na lookup)
INSERT INTO ocorrencia_devolucao_categoria (ocorrencia_devolucao_id, categoria_id)
SELECT od.id, oc.id
FROM ocorrencia_devolucao od
JOIN ocorrencia_categoria oc ON od.categoria = oc.codigo
WHERE od.categoria IS NOT NULL AND TRIM(od.categoria) != ''
ON CONFLICT DO NOTHING;

-- Subcategoria varchar -> junction
INSERT INTO ocorrencia_devolucao_subcategoria (ocorrencia_devolucao_id, subcategoria_id)
SELECT od.id, os.id
FROM ocorrencia_devolucao od
JOIN ocorrencia_subcategoria os ON od.subcategoria = os.codigo
WHERE od.subcategoria IS NOT NULL AND TRIM(od.subcategoria) != ''
ON CONFLICT DO NOTHING;

-- Responsavel varchar -> FK
UPDATE ocorrencia_devolucao od
SET responsavel_id = or2.id
FROM ocorrencia_responsavel or2
WHERE od.responsavel = or2.codigo
AND od.responsavel_id IS NULL
AND od.responsavel IS NOT NULL AND TRIM(od.responsavel) != '';

-- Origem varchar -> FK
UPDATE ocorrencia_devolucao od
SET origem_id = oo.id
FROM ocorrencia_origem oo
WHERE od.origem = oo.codigo
AND od.origem_id IS NULL
AND od.origem IS NOT NULL AND TRIM(od.origem) != '';

-- Autorizado por varchar -> FK
UPDATE ocorrencia_devolucao od
SET autorizado_por_id = oap.id
FROM ocorrencia_autorizado_por oap
WHERE LOWER(TRIM(od.autorizado_por)) = LOWER(oap.descricao)
AND od.autorizado_por_id IS NULL
AND od.autorizado_por IS NOT NULL AND TRIM(od.autorizado_por) != '';
