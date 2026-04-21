-- Migration: sistema de compensacao Saida <-> Entrada Empresa (pessoal)
-- Idempotente.

BEGIN;

-- 1. Tipo da categoria: 'S' saida compensavel / 'E' entrada compensavel / NULL
ALTER TABLE pessoal_categorias
    ADD COLUMN IF NOT EXISTS compensavel_tipo CHAR(1);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_pessoal_categorias_compensavel_tipo'
    ) THEN
        ALTER TABLE pessoal_categorias
            ADD CONSTRAINT ck_pessoal_categorias_compensavel_tipo
            CHECK (compensavel_tipo IS NULL OR compensavel_tipo IN ('S', 'E'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_pessoal_categorias_compensavel
    ON pessoal_categorias (compensavel_tipo)
    WHERE compensavel_tipo IS NOT NULL;

-- 2. Valor ja compensado em cada transacao (cache agregado de pessoal_compensacoes)
ALTER TABLE pessoal_transacoes
    ADD COLUMN IF NOT EXISTS valor_compensado NUMERIC(15, 2) NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_compensado
    ON pessoal_transacoes (valor_compensado)
    WHERE valor_compensado > 0;

-- 3. Tabela de compensacoes (N:M saida <-> entrada com valor consumido)
CREATE TABLE IF NOT EXISTS pessoal_compensacoes (
    id SERIAL PRIMARY KEY,
    saida_id INTEGER NOT NULL REFERENCES pessoal_transacoes(id) ON DELETE CASCADE,
    entrada_id INTEGER NOT NULL REFERENCES pessoal_transacoes(id) ON DELETE CASCADE,
    valor_compensado NUMERIC(15, 2) NOT NULL,
    residuo_saida NUMERIC(15, 2) NOT NULL,
    residuo_entrada NUMERIC(15, 2) NOT NULL,
    origem VARCHAR(10) NOT NULL DEFAULT 'manual',
    status VARCHAR(10) NOT NULL DEFAULT 'ATIVA',
    observacao TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por VARCHAR(100),
    revertido_em TIMESTAMP,
    revertido_por VARCHAR(100),
    CONSTRAINT ck_compensacoes_valor_positivo CHECK (valor_compensado > 0),
    CONSTRAINT ck_compensacoes_origem CHECK (origem IN ('auto', 'manual')),
    CONSTRAINT ck_compensacoes_status CHECK (status IN ('ATIVA', 'REVERTIDA')),
    CONSTRAINT ck_compensacoes_saida_diff_entrada CHECK (saida_id <> entrada_id)
);

CREATE INDEX IF NOT EXISTS idx_pessoal_compensacoes_saida
    ON pessoal_compensacoes (saida_id) WHERE status = 'ATIVA';
CREATE INDEX IF NOT EXISTS idx_pessoal_compensacoes_entrada
    ON pessoal_compensacoes (entrada_id) WHERE status = 'ATIVA';
CREATE INDEX IF NOT EXISTS idx_pessoal_compensacoes_status
    ON pessoal_compensacoes (status, criado_em DESC);

COMMIT;

-- Verificacao pos-execucao:
-- SELECT column_name FROM information_schema.columns
--  WHERE table_name='pessoal_categorias' AND column_name='compensavel_tipo';
-- SELECT column_name FROM information_schema.columns
--  WHERE table_name='pessoal_transacoes' AND column_name='valor_compensado';
-- SELECT table_name FROM information_schema.tables WHERE table_name='pessoal_compensacoes';
