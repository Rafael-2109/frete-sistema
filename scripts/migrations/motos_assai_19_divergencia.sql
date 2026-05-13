-- Migration 19: Cria assai_divergencia (centraliza todas divergencias).
-- 8 tipos no CHECK: 4 novos (Carregamento×NF + cross-loja) + 4 legados de _calcular_match
-- (LOJA_DIVERGENTE, VALOR_DIVERGENTE, MODELO_DIVERGENTE, CHASSI_SEM_SEPARACAO).
-- 5 tipos de resolucao.

BEGIN;

CREATE TABLE IF NOT EXISTS assai_divergencia (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(40) NOT NULL,
    chassi VARCHAR(50),
    separacao_id INTEGER REFERENCES assai_separacao(id),
    carregamento_id INTEGER REFERENCES assai_carregamento(id),
    nf_id INTEGER REFERENCES assai_nf_qpa(id),
    detalhes JSONB DEFAULT '{}'::jsonb,
    criada_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    resolvida_em TIMESTAMP,
    resolvida_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    tipo_resolucao VARCHAR(40),
    observacao_resolucao TEXT,
    CONSTRAINT ck_assai_divergencia_tipo
        CHECK (tipo IN (
            'NF_CHASSI_FORA_CARREGAMENTO',
            'CARREGAMENTO_CHASSI_FORA_NF',
            'CHASSI_NAO_CADASTRADO',
            'CHASSI_OUTRA_LOJA',
            'LOJA_DIVERGENTE',
            'VALOR_DIVERGENTE',
            'MODELO_DIVERGENTE',
            'CHASSI_SEM_SEPARACAO'
        )),
    CONSTRAINT ck_assai_divergencia_resolucao
        CHECK (tipo_resolucao IS NULL OR tipo_resolucao IN (
            'CANCELAR_NF', 'CCE', 'ALTERAR_CARREGAMENTO',
            'SUBSTITUIR_CHASSI', 'IGNORAR'
        ))
);

CREATE INDEX IF NOT EXISTS ix_assai_divergencia_chassi
    ON assai_divergencia(chassi);
CREATE INDEX IF NOT EXISTS ix_assai_divergencia_pendentes
    ON assai_divergencia(criada_em DESC) WHERE resolvida_em IS NULL;
CREATE INDEX IF NOT EXISTS ix_assai_divergencia_sep
    ON assai_divergencia(separacao_id) WHERE separacao_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_assai_divergencia_nf
    ON assai_divergencia(nf_id) WHERE nf_id IS NOT NULL;

COMMIT;
