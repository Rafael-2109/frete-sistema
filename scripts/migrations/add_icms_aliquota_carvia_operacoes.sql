-- Migration: adicionar icms_aliquota a carvia_operacoes
-- e criar tabela carvia_emissao_cte_complementar
-- Idempotente — seguro para executar multiplas vezes

-- 1. Coluna icms_aliquota em carvia_operacoes
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_operacoes'
        AND column_name = 'icms_aliquota'
    ) THEN
        ALTER TABLE carvia_operacoes
        ADD COLUMN icms_aliquota NUMERIC(5, 2);
    END IF;
END $$;

-- 2. Tabela de tracking de emissao CTe Complementar
CREATE TABLE IF NOT EXISTS carvia_emissao_cte_complementar (
    id SERIAL PRIMARY KEY,
    custo_entrega_id INTEGER NOT NULL REFERENCES carvia_custos_entrega(id),
    cte_complementar_id INTEGER NOT NULL REFERENCES carvia_cte_complementares(id),
    operacao_id INTEGER NOT NULL REFERENCES carvia_operacoes(id),
    ctrc_pai VARCHAR(30) NOT NULL,
    motivo_ssw VARCHAR(5) NOT NULL,
    filial_ssw VARCHAR(10) NOT NULL DEFAULT 'CAR',
    valor_calculado NUMERIC(15, 2) NOT NULL,
    icms_aliquota_usada NUMERIC(5, 2),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    etapa VARCHAR(30),
    job_id VARCHAR(100),
    erro_ssw TEXT,
    resultado_json JSONB,
    criado_por VARCHAR(100) NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Indices
CREATE INDEX IF NOT EXISTS ix_emissao_cte_comp_custo
    ON carvia_emissao_cte_complementar(custo_entrega_id);
CREATE INDEX IF NOT EXISTS ix_emissao_cte_comp_cte
    ON carvia_emissao_cte_complementar(cte_complementar_id);
CREATE INDEX IF NOT EXISTS ix_emissao_cte_comp_operacao
    ON carvia_emissao_cte_complementar(operacao_id);
CREATE INDEX IF NOT EXISTS ix_emissao_cte_comp_status
    ON carvia_emissao_cte_complementar(status);
