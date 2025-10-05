-- ============================================================
-- MIGRAÇÃO: Adicionar campos sistema_logistica e sistema_motochefe
-- Tabela: usuarios
-- Data: Outubro 2025
-- ============================================================

-- Adicionar colunas
ALTER TABLE usuarios
ADD COLUMN IF NOT EXISTS sistema_logistica BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS sistema_motochefe BOOLEAN NOT NULL DEFAULT FALSE;

-- Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_usuarios_sistema_logistica ON usuarios(sistema_logistica) WHERE sistema_logistica = TRUE;
CREATE INDEX IF NOT EXISTS idx_usuarios_sistema_motochefe ON usuarios(sistema_motochefe) WHERE sistema_motochefe = TRUE;

-- Comentários
COMMENT ON COLUMN usuarios.sistema_logistica IS 'Usuário tem acesso ao sistema de logística';
COMMENT ON COLUMN usuarios.sistema_motochefe IS 'Usuário tem acesso ao sistema motochefe';

-- Atualizar usuários existentes para terem acesso à logística (manter compatibilidade)
UPDATE usuarios
SET sistema_logistica = TRUE
WHERE sistema_logistica = FALSE;

-- ============================================================
-- FIM DA MIGRAÇÃO
-- ============================================================
