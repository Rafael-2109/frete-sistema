-- Migration: criar tabela carvia_anexos (anexos polimorficos Frete + Subcontrato)
-- ============================================================================
-- Paridade Nacom (DespesaExtra.comprovante + EmailAnexado). Polimorfico via
-- (entidade_tipo, entidade_id). Despesas mantem carvia_custo_entrega_anexos.
-- Idempotente: seguro rodar multiplas vezes (Render Shell).

CREATE TABLE IF NOT EXISTS carvia_anexos (
    id SERIAL PRIMARY KEY,
    entidade_tipo VARCHAR(30) NOT NULL,
    entidade_id INTEGER NOT NULL,
    nome_original VARCHAR(255) NOT NULL,
    nome_arquivo VARCHAR(255) NOT NULL,
    caminho_s3 VARCHAR(500) NOT NULL,
    tamanho_bytes INTEGER,
    content_type VARCHAR(100),
    descricao TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por VARCHAR(100) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    email_remetente VARCHAR(255),
    email_assunto VARCHAR(500),
    email_data_envio TIMESTAMP,
    email_conteudo_preview VARCHAR(500)
);

-- Indices
CREATE INDEX IF NOT EXISTS ix_carvia_anexo_entidade_tipo ON carvia_anexos(entidade_tipo);
CREATE INDEX IF NOT EXISTS ix_carvia_anexo_entidade_id ON carvia_anexos(entidade_id);
CREATE INDEX IF NOT EXISTS ix_carvia_anexo_ativo ON carvia_anexos(ativo);
CREATE INDEX IF NOT EXISTS ix_carvia_anexo_entidade ON carvia_anexos(entidade_tipo, entidade_id);
