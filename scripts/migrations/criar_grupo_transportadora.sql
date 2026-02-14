-- Migration: Criar tabela grupo_transportadora e FK em transportadoras
-- Data: 2026-02-14
-- Descricao: Permite agrupar transportadoras que operam com multiplos CNPJs
--            para matching correto de CTe -> Frete

-- 1. Tabela de grupos
CREATE TABLE IF NOT EXISTS grupo_transportadora (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW(),
    criado_por VARCHAR(100)
);

-- 2. FK em transportadoras
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'transportadoras'
        AND column_name = 'grupo_transportadora_id'
    ) THEN
        ALTER TABLE transportadoras
        ADD COLUMN grupo_transportadora_id INTEGER
        REFERENCES grupo_transportadora(id);
    END IF;
END $$;

-- 3. Indice na FK
CREATE INDEX IF NOT EXISTS idx_transportadoras_grupo
ON transportadoras(grupo_transportadora_id);
