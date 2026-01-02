-- =====================================================================
-- FASE 4: Criar tabela nf_devolucao_nf_referenciada
-- =====================================================================
-- Copiar e colar no Render Shell

-- 1. Criar tabela nf_devolucao_nf_referenciada
CREATE TABLE IF NOT EXISTS nf_devolucao_nf_referenciada (
    id SERIAL PRIMARY KEY,

    -- Vinculo com NFDevolucao
    nf_devolucao_id INTEGER NOT NULL REFERENCES nf_devolucao(id) ON DELETE CASCADE,

    -- Dados da NF de venda referenciada
    numero_nf VARCHAR(20) NOT NULL,
    serie_nf VARCHAR(10),
    chave_nf VARCHAR(44),
    data_emissao_nf DATE,

    -- Origem do dado
    origem VARCHAR(20) DEFAULT 'MANUAL' NOT NULL,

    -- Vinculo com entrega monitorada (se disponivel)
    entrega_monitorada_id INTEGER REFERENCES entregas_monitoradas(id),

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    criado_por VARCHAR(100),

    -- Constraint unica (NFD + numero + serie)
    CONSTRAINT uq_nfd_nf_ref UNIQUE (nf_devolucao_id, numero_nf, serie_nf)
);

-- 2. Criar indices
CREATE INDEX IF NOT EXISTS idx_nf_ref_nfd ON nf_devolucao_nf_referenciada(nf_devolucao_id);
CREATE INDEX IF NOT EXISTS idx_nf_ref_numero ON nf_devolucao_nf_referenciada(numero_nf);
CREATE INDEX IF NOT EXISTS idx_nf_ref_chave ON nf_devolucao_nf_referenciada(chave_nf);
CREATE INDEX IF NOT EXISTS idx_nf_ref_entrega ON nf_devolucao_nf_referenciada(entrega_monitorada_id);

-- 3. Adicionar coluna origem_registro em nf_devolucao
ALTER TABLE nf_devolucao
ADD COLUMN IF NOT EXISTS origem_registro VARCHAR(20) DEFAULT 'MONITORAMENTO' NOT NULL;

-- 4. Criar indice para origem_registro
CREATE INDEX IF NOT EXISTS idx_nfd_origem_registro ON nf_devolucao(origem_registro);

-- 5. Migrar dados existentes de numero_nf_venda
INSERT INTO nf_devolucao_nf_referenciada (
    nf_devolucao_id,
    numero_nf,
    origem,
    entrega_monitorada_id,
    criado_em,
    criado_por
)
SELECT
    id,
    numero_nf_venda,
    'MONITORAMENTO',
    entrega_monitorada_id,
    criado_em,
    criado_por
FROM nf_devolucao
WHERE numero_nf_venda IS NOT NULL
AND numero_nf_venda != ''
AND NOT EXISTS (
    SELECT 1 FROM nf_devolucao_nf_referenciada r
    WHERE r.nf_devolucao_id = nf_devolucao.id
    AND r.numero_nf = nf_devolucao.numero_nf_venda
);

-- Verificar resultado
SELECT 'Tabela criada com sucesso!' AS status;
SELECT COUNT(*) AS registros_migrados FROM nf_devolucao_nf_referenciada;
