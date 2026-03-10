-- Migration: Criar tabela permissao_cadastro_devolucao
-- Controle granular de permissoes para CRUD de cadastros de devolucao.

CREATE TABLE IF NOT EXISTS permissao_cadastro_devolucao (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    tipo_cadastro VARCHAR(30) NOT NULL,
    pode_criar BOOLEAN DEFAULT FALSE,
    pode_editar BOOLEAN DEFAULT FALSE,
    pode_excluir BOOLEAN DEFAULT FALSE,
    concedido_por VARCHAR(100),
    concedido_em TIMESTAMP DEFAULT NOW(),
    ativo BOOLEAN DEFAULT TRUE,
    CONSTRAINT uq_perm_cad_dev_usuario_tipo UNIQUE (usuario_id, tipo_cadastro)
);

CREATE INDEX IF NOT EXISTS idx_perm_cad_dev_usuario
ON permissao_cadastro_devolucao(usuario_id);
