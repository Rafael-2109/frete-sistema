-- Migration 28: Cria tabela `assai_cce` (Carta de Correcao Eletronica como entidade).
--
-- Motivacao: CCe pode existir SEM NF correspondente importada ainda (chega antes
-- da NF). Precisa de persistencia propria + flag tem_nf + match reverso ao
-- importar NF Q.P.A.
--
-- Identidade SEFAZ: protocolo_cce (UNIQUE).
-- Match com NF: chave_44 == AssaiNfQpa.chave_44 (preferido) OU numero_nf_referenciada == AssaiNfQpa.numero.

BEGIN;

CREATE TABLE IF NOT EXISTS assai_cce (
    id SERIAL PRIMARY KEY,

    -- Identidade SEFAZ (UNIQUE garante idempotencia)
    protocolo_cce VARCHAR(30) UNIQUE NOT NULL,
    chave_nfe VARCHAR(44) NOT NULL,
    numero_nf_referenciada VARCHAR(20) NOT NULL,
    sequencia_cce INTEGER NOT NULL DEFAULT 1,

    -- Metadados do parser
    numero_cce VARCHAR(50),
    tipo_correcao VARCHAR(20) NOT NULL DEFAULT 'OUTRO',
    formato_detectado VARCHAR(30),
    parser_usado VARCHAR(40),
    confianca_parser NUMERIC(4, 3),
    dados_parsed JSONB,

    -- Arquivo
    pdf_s3_key VARCHAR(500),
    nome_arquivo_original VARCHAR(255),
    data_emissao_cce DATE,

    -- Estado de aplicacao
    tem_nf BOOLEAN NOT NULL DEFAULT FALSE,
    nf_id INTEGER REFERENCES assai_nf_qpa(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    -- Status: PENDENTE | APLICADA | IGNORADA (DUPLICATAS/ENDERECO) | ERRO

    aplicada_em TIMESTAMP,
    aplicada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,

    -- Auditoria de aplicacao
    chassis_aplicados JSONB,  -- [[antigo, novo], ...] efetivamente trocados
    observacao TEXT,

    -- Origem (se veio do botao CCe em uma divergencia)
    divergencia_origem_id INTEGER REFERENCES assai_divergencia(id) ON DELETE SET NULL,

    -- Auditoria de criacao
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);

-- Indexes para queries comuns
CREATE INDEX IF NOT EXISTS ix_assai_cce_tem_nf ON assai_cce(tem_nf) WHERE tem_nf = FALSE;
CREATE INDEX IF NOT EXISTS ix_assai_cce_chave_nfe ON assai_cce(chave_nfe);
CREATE INDEX IF NOT EXISTS ix_assai_cce_numero_nf ON assai_cce(numero_nf_referenciada);
CREATE INDEX IF NOT EXISTS ix_assai_cce_nf_id ON assai_cce(nf_id) WHERE nf_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_assai_cce_status ON assai_cce(status);
CREATE INDEX IF NOT EXISTS ix_assai_cce_divergencia_origem ON assai_cce(divergencia_origem_id) WHERE divergencia_origem_id IS NOT NULL;

-- Indice composto para o match reverso ao importar NF (filtro tem_nf=False + status=PENDENTE)
CREATE INDEX IF NOT EXISTS ix_assai_cce_match_reverso
    ON assai_cce(chave_nfe, numero_nf_referenciada)
    WHERE tem_nf = FALSE AND status = 'PENDENTE';

COMMIT;
