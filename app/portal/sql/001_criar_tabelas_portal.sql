-- ============================================================
-- Script SQL para criar tabelas do módulo Portal
-- Data: 20/08/2025
-- Sistema: Integração com Portais de Agendamento
-- ============================================================

-- Criar schema se não existir (opcional)
-- CREATE SCHEMA IF NOT EXISTS portal;

-- ============================================================
-- TABELA: portal_integracoes
-- Descrição: Registra todas as integrações com portais
-- ============================================================
CREATE TABLE IF NOT EXISTS portal_integracoes (
    id SERIAL PRIMARY KEY,
    portal VARCHAR(50) NOT NULL,
    lote_id VARCHAR(50) NOT NULL,
    tipo_lote VARCHAR(20) NOT NULL,
    
    -- Protocolo pode ser NULL inicialmente, UNIQUE permite múltiplos NULL
    protocolo_portal VARCHAR(100) UNIQUE,
    status VARCHAR(50) DEFAULT 'aguardando',
    data_solicitacao TIMESTAMP,
    data_confirmacao TIMESTAMP,
    data_agendamento DATE,
    hora_agendamento TIME,
    
    -- Controle
    usuario_solicitante VARCHAR(100),
    navegador_sessao_id VARCHAR(100),
    tentativas INTEGER DEFAULT 0,
    ultimo_erro TEXT,
    
    -- JSON logs para PostgreSQL
    dados_enviados JSONB,
    resposta_portal JSONB,
    
    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_portal_lote ON portal_integracoes(lote_id);
CREATE INDEX IF NOT EXISTS idx_portal_status ON portal_integracoes(status);
CREATE INDEX IF NOT EXISTS idx_portal_protocolo ON portal_integracoes(protocolo_portal);
CREATE INDEX IF NOT EXISTS idx_portal_data_solicitacao ON portal_integracoes(data_solicitacao);
CREATE INDEX IF NOT EXISTS idx_portal_criado_em ON portal_integracoes(criado_em);

-- ============================================================
-- TABELA: portal_configuracoes
-- Descrição: Configurações de acesso aos portais
-- ============================================================
CREATE TABLE IF NOT EXISTS portal_configuracoes (
    id SERIAL PRIMARY KEY,
    portal VARCHAR(50) NOT NULL,
    cnpj_cliente VARCHAR(20),
    url_portal VARCHAR(255),
    url_login VARCHAR(255),
    usuario VARCHAR(100),
    senha_criptografada VARCHAR(255),
    totp_secret VARCHAR(100),  -- Para 2FA automático
    instrucoes_acesso TEXT,
    seletores_css JSONB,
    login_indicators JSONB,    -- Seletores para detectar página de login
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT portal_cliente_unique UNIQUE(portal, cnpj_cliente)
);

CREATE INDEX IF NOT EXISTS idx_portal_config_ativo ON portal_configuracoes(portal, ativo);

-- ============================================================
-- TABELA: portal_logs
-- Descrição: Log detalhado de todas as operações
-- ============================================================
CREATE TABLE IF NOT EXISTS portal_logs (
    id SERIAL PRIMARY KEY,
    integracao_id INTEGER REFERENCES portal_integracoes(id) ON DELETE CASCADE,
    acao VARCHAR(100),
    sucesso BOOLEAN,
    mensagem TEXT,
    screenshot_path VARCHAR(500),
    dados_contexto JSONB,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_portal_logs_integracao ON portal_logs(integracao_id);
CREATE INDEX IF NOT EXISTS idx_portal_logs_criado ON portal_logs(criado_em);

-- ============================================================
-- TABELA: portal_sessoes
-- Descrição: Gerenciamento de sessões e cookies
-- ============================================================
CREATE TABLE IF NOT EXISTS portal_sessoes (
    id SERIAL PRIMARY KEY,
    portal VARCHAR(50) NOT NULL,
    usuario VARCHAR(100),
    cookies_criptografados TEXT,
    storage_state JSONB,
    valido_ate TIMESTAMP,
    ultima_utilizacao TIMESTAMP,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_portal_sessoes_portal ON portal_sessoes(portal, valido_ate);

-- ============================================================
-- TABELA: portal_atacadao_produto_depara
-- Descrição: DE-PARA de produtos específico do Atacadão
-- ============================================================
CREATE TABLE IF NOT EXISTS portal_atacadao_produto_depara (
    id SERIAL PRIMARY KEY,
    
    -- Nosso código e descrição
    codigo_nosso VARCHAR(50) NOT NULL,
    descricao_nosso VARCHAR(255),
    
    -- Código e descrição do Atacadão
    codigo_atacadao VARCHAR(50) NOT NULL,
    descricao_atacadao VARCHAR(255),
    
    -- CNPJ do cliente (caso o mapeamento seja específico por cliente)
    cnpj_cliente VARCHAR(20),
    
    -- Fator de conversão (se houver diferença de unidade de medida)
    fator_conversao NUMERIC(10, 4) DEFAULT 1.0,
    observacoes TEXT,
    
    -- Controle
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    
    -- Índice único para evitar duplicatas
    CONSTRAINT unique_depara_atacadao UNIQUE(codigo_nosso, codigo_atacadao, cnpj_cliente)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_atacadao_codigo_nosso ON portal_atacadao_produto_depara(codigo_nosso);
CREATE INDEX IF NOT EXISTS idx_atacadao_codigo_atacadao ON portal_atacadao_produto_depara(codigo_atacadao);
CREATE INDEX IF NOT EXISTS idx_atacadao_cnpj ON portal_atacadao_produto_depara(cnpj_cliente);
CREATE INDEX IF NOT EXISTS idx_atacadao_ativo ON portal_atacadao_produto_depara(ativo);

-- ============================================================
-- ALTERAÇÕES EM TABELAS EXISTENTES
-- ============================================================

-- Adicionar coluna na tabela agendamentos_entrega (se existir)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'agendamentos_entrega') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'agendamentos_entrega' 
                      AND column_name = 'portal_integracao_id') THEN
            ALTER TABLE agendamentos_entrega 
            ADD COLUMN portal_integracao_id INTEGER REFERENCES portal_integracoes(id);
            
            CREATE INDEX idx_agendamentos_portal ON agendamentos_entrega(portal_integracao_id);
        END IF;
    END IF;
END $$;

-- Adicionar coluna na tabela separacao (se existir)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'separacao') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'separacao' 
                      AND column_name = 'agendamento_portal_solicitado') THEN
            ALTER TABLE separacao 
            ADD COLUMN agendamento_portal_solicitado BOOLEAN DEFAULT FALSE;
            
            CREATE INDEX idx_separacao_portal_solicitado ON separacao(agendamento_portal_solicitado) 
            WHERE agendamento_portal_solicitado = TRUE;
        END IF;
    END IF;
END $$;

-- Adicionar coluna na tabela pre_separacao_items (se existir)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pre_separacao_items') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'pre_separacao_items' 
                      AND column_name = 'agendamento_portal_solicitado') THEN
            ALTER TABLE pre_separacao_items 
            ADD COLUMN agendamento_portal_solicitado BOOLEAN DEFAULT FALSE;
            
            CREATE INDEX idx_pre_separacao_portal_solicitado ON pre_separacao_items(agendamento_portal_solicitado) 
            WHERE agendamento_portal_solicitado = TRUE;
        END IF;
    END IF;
END $$;

-- ============================================================
-- TRIGGERS para atualizar timestamp
-- ============================================================

-- Função genérica para atualizar timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Aplicar trigger nas tabelas que têm campo atualizado_em
CREATE TRIGGER update_portal_integracoes_updated_at 
    BEFORE UPDATE ON portal_integracoes 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_portal_configuracoes_updated_at 
    BEFORE UPDATE ON portal_configuracoes 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_portal_sessoes_updated_at 
    BEFORE UPDATE ON portal_sessoes 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_portal_atacadao_produto_depara_updated_at 
    BEFORE UPDATE ON portal_atacadao_produto_depara 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- DADOS INICIAIS (OPCIONAL)
-- ============================================================

-- Inserir configuração padrão para Atacadão (exemplo)
INSERT INTO portal_configuracoes (
    portal, 
    url_portal, 
    url_login,
    seletores_css,
    login_indicators,
    ativo
) VALUES (
    'atacadao',
    'https://atacadao.hodiebooking.com.br',
    'https://atacadao.hodiebooking.com.br/',
    '{"campo_pedido": "#nr_pedido", "botao_filtrar": "#enviarFiltros"}'::jsonb,
    '["input[name=\"username\"]", "input[name=\"password\"]", ".login-form"]'::jsonb,
    true
) ON CONFLICT (portal, cnpj_cliente) DO NOTHING;

-- ============================================================
-- COMENTÁRIOS NAS TABELAS
-- ============================================================
COMMENT ON TABLE portal_integracoes IS 'Registra todas as integrações com portais de agendamento';
COMMENT ON TABLE portal_configuracoes IS 'Configurações de acesso e automação dos portais';
COMMENT ON TABLE portal_logs IS 'Log detalhado de todas as operações realizadas nos portais';
COMMENT ON TABLE portal_sessoes IS 'Gerenciamento de sessões e cookies dos portais';
COMMENT ON TABLE portal_atacadao_produto_depara IS 'Mapeamento DE-PARA de códigos de produtos para o portal Atacadão';

-- ============================================================
-- FIM DO SCRIPT
-- ============================================================