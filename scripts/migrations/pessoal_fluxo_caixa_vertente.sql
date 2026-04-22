-- Migration: vertente Fluxo de Caixa do modulo Pessoal
-- Idempotente — executar via Render Shell (psql -f ...)
-- Complementa: scripts/migrations/pessoal_fluxo_caixa_vertente.py

BEGIN;

-- =============================================================================
-- 1. pessoal_importacoes: data_pagamento + transacao_pagamento_id
-- =============================================================================
ALTER TABLE pessoal_importacoes
    ADD COLUMN IF NOT EXISTS data_pagamento DATE;

ALTER TABLE pessoal_importacoes
    ADD COLUMN IF NOT EXISTS transacao_pagamento_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_imp_transacao_pagamento'
          AND table_name = 'pessoal_importacoes'
    ) THEN
        ALTER TABLE pessoal_importacoes
        ADD CONSTRAINT fk_imp_transacao_pagamento
        FOREIGN KEY (transacao_pagamento_id)
        REFERENCES pessoal_transacoes(id) ON DELETE SET NULL;
    END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_pessoal_imp_data_pagamento
    ON pessoal_importacoes (data_pagamento)
    WHERE data_pagamento IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pessoal_imp_transacao_pagamento
    ON pessoal_importacoes (transacao_pagamento_id)
    WHERE transacao_pagamento_id IS NOT NULL;

-- =============================================================================
-- 2. pessoal_provisoes
-- =============================================================================
CREATE TABLE IF NOT EXISTS pessoal_provisoes (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(10) NOT NULL,
    data_prevista DATE NOT NULL,
    valor NUMERIC(15, 2) NOT NULL,
    descricao VARCHAR(300) NOT NULL,
    categoria_id INTEGER REFERENCES pessoal_categorias(id) ON DELETE SET NULL,
    membro_id INTEGER REFERENCES pessoal_membros(id) ON DELETE SET NULL,
    conta_id INTEGER REFERENCES pessoal_contas(id) ON DELETE SET NULL,
    orcamento_id INTEGER REFERENCES pessoal_orcamentos(id) ON DELETE SET NULL,
    transacao_id INTEGER REFERENCES pessoal_transacoes(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PROVISIONADA',
    recorrente BOOLEAN DEFAULT FALSE,
    recorrencia_tipo VARCHAR(20),
    recorrencia_ate DATE,
    observacao TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por VARCHAR(100),
    realizado_em TIMESTAMP,
    CONSTRAINT ck_provisoes_tipo CHECK (tipo IN ('entrada', 'saida')),
    CONSTRAINT ck_provisoes_status CHECK (
        status IN ('PROVISIONADA', 'REALIZADA', 'CANCELADA')
    ),
    CONSTRAINT ck_provisoes_valor_positivo CHECK (valor > 0),
    CONSTRAINT ck_provisoes_recorrencia_tipo CHECK (
        recorrencia_tipo IS NULL
        OR recorrencia_tipo IN ('mensal', 'semanal', 'anual')
    )
);

CREATE INDEX IF NOT EXISTS idx_pessoal_provisoes_data
    ON pessoal_provisoes (data_prevista);

CREATE INDEX IF NOT EXISTS idx_pessoal_provisoes_status
    ON pessoal_provisoes (status);

CREATE INDEX IF NOT EXISTS idx_pessoal_provisoes_tipo
    ON pessoal_provisoes (tipo);

-- =============================================================================
-- 3. Seed: categoria 'Cartao de Credito' (grupo Financeiro)
-- =============================================================================
INSERT INTO pessoal_categorias (nome, grupo, icone, ativa, criado_em)
VALUES ('Cartao de Credito', 'Financeiro', 'fa-credit-card', TRUE, NOW())
ON CONFLICT ON CONSTRAINT uq_pessoal_categorias_grupo_nome DO NOTHING;

COMMIT;

-- =============================================================================
-- Verificacao
-- =============================================================================
SELECT
    (SELECT COUNT(*) FROM information_schema.columns
     WHERE table_name='pessoal_importacoes' AND column_name='data_pagamento')
    AS data_pagamento_ok,
    (SELECT COUNT(*) FROM information_schema.columns
     WHERE table_name='pessoal_importacoes' AND column_name='transacao_pagamento_id')
    AS transacao_pagamento_id_ok,
    (SELECT COUNT(*) FROM information_schema.tables
     WHERE table_name='pessoal_provisoes')
    AS pessoal_provisoes_ok,
    (SELECT COUNT(*) FROM pessoal_categorias
     WHERE grupo='Financeiro' AND nome='Cartao de Credito')
    AS cartao_credito_categoria_ok;
