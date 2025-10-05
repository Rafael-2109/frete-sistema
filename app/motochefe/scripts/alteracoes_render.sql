-- ============================================================
-- MIGRAÇÃO COMPLETA - ADICIONAR CAMPOS FALTANTES
-- Sistema: MotoCHEFE
-- Data: 2025-01-04
-- Descrição: Adiciona todos os campos que faltam no Render
-- ============================================================

-- ============================================================
-- 1. CRIAR TABELA empresa_venda_moto (NÃO EXISTE)
-- ============================================================

CREATE TABLE IF NOT EXISTS empresa_venda_moto (
    id SERIAL PRIMARY KEY,
    cnpj_empresa VARCHAR(20) NOT NULL UNIQUE,
    empresa VARCHAR(255) NOT NULL,

    -- Dados bancários
    chave_pix VARCHAR(100),
    banco VARCHAR(100),
    cod_banco VARCHAR(10),
    agencia VARCHAR(20),
    conta VARCHAR(20),

    -- Auditoria
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_empresa_venda_moto_ativo ON empresa_venda_moto(ativo) WHERE ativo = TRUE;
CREATE INDEX IF NOT EXISTS idx_empresa_venda_moto_cnpj ON empresa_venda_moto(cnpj_empresa);

COMMENT ON TABLE empresa_venda_moto IS 'Empresas emissoras de NF para faturamento';


-- ============================================================
-- 2. TRANSPORTADORA_MOTO - Adicionar dados bancários
-- ============================================================

ALTER TABLE transportadora_moto
ADD COLUMN IF NOT EXISTS chave_pix VARCHAR(100),
ADD COLUMN IF NOT EXISTS agencia VARCHAR(20),
ADD COLUMN IF NOT EXISTS conta VARCHAR(20),
ADD COLUMN IF NOT EXISTS banco VARCHAR(100),
ADD COLUMN IF NOT EXISTS cod_banco VARCHAR(10);

COMMENT ON COLUMN transportadora_moto.chave_pix IS 'Chave PIX para pagamento de frete';


-- ============================================================
-- 3. PEDIDO_VENDA_MOTO - Adicionar empresa_venda_id
-- ============================================================

ALTER TABLE pedido_venda_moto
ADD COLUMN IF NOT EXISTS empresa_venda_id INTEGER REFERENCES empresa_venda_moto(id);

CREATE INDEX IF NOT EXISTS idx_pedido_venda_empresa ON pedido_venda_moto(empresa_venda_id);

COMMENT ON COLUMN pedido_venda_moto.empresa_venda_id IS 'Empresa que emitiu a NF (preenchido no faturamento)';


-- ============================================================
-- 4. TITULO_FINANCEIRO - Adicionar prazo_dias e tornar data_vencimento nullable
-- ============================================================

ALTER TABLE titulo_financeiro
ADD COLUMN IF NOT EXISTS prazo_dias INTEGER;

ALTER TABLE titulo_financeiro
ALTER COLUMN data_vencimento DROP NOT NULL;

COMMENT ON COLUMN titulo_financeiro.prazo_dias IS 'Prazo em dias (30, 60, 90). Usado para calcular data_vencimento no faturamento';
COMMENT ON COLUMN titulo_financeiro.data_vencimento IS 'Calculado no faturamento: data_nf + prazo_dias';


-- ============================================================
-- 5. EMBARQUE_MOTO - Adicionar campos de frete e alterar valor_frete_pago
-- ============================================================

-- Adicionar novos campos
ALTER TABLE embarque_moto
ADD COLUMN IF NOT EXISTS valor_frete_contratado NUMERIC(15, 2),
ADD COLUMN IF NOT EXISTS data_pagamento_frete DATE,
ADD COLUMN IF NOT EXISTS status_pagamento_frete VARCHAR(20) DEFAULT 'PENDENTE';

-- Tornar valor_frete_pago nullable (era NOT NULL)
ALTER TABLE embarque_moto
ALTER COLUMN valor_frete_pago DROP NOT NULL;

-- Atualizar registros existentes (se houver)
UPDATE embarque_moto
SET valor_frete_contratado = valor_frete_pago
WHERE valor_frete_contratado IS NULL AND valor_frete_pago IS NOT NULL;

UPDATE embarque_moto
SET status_pagamento_frete = 'PAGO'
WHERE valor_frete_pago IS NOT NULL AND valor_frete_pago > 0;

-- Criar índice
CREATE INDEX IF NOT EXISTS idx_embarque_status_pagamento ON embarque_moto(status_pagamento_frete);

COMMENT ON COLUMN embarque_moto.valor_frete_contratado IS 'Valor acordado com transportadora (usado no rateio)';
COMMENT ON COLUMN embarque_moto.valor_frete_pago IS 'Valor efetivamente pago';
COMMENT ON COLUMN embarque_moto.status_pagamento_frete IS 'PENDENTE, PAGO, ATRASADO';


-- ============================================================
-- 6. EMBARQUE_PEDIDO - Adicionar campo enviado
-- ============================================================

ALTER TABLE embarque_pedido
ADD COLUMN IF NOT EXISTS enviado BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_embarque_pedido_enviado ON embarque_pedido(enviado);

COMMENT ON COLUMN embarque_pedido.enviado IS 'Trigger: ao marcar TRUE, calcula rateio e marca PedidoVendaMoto.enviado=True';


-- ============================================================
-- 7. COMISSAO_VENDEDOR - Adicionar atualizado_por (faltava)
-- ============================================================

ALTER TABLE comissao_vendedor
ADD COLUMN IF NOT EXISTS atualizado_por VARCHAR(100);


-- ============================================================
-- VERIFICAÇÕES FINAIS
-- ============================================================

-- Verificar tabelas e colunas
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name IN (
    'empresa_venda_moto',
    'transportadora_moto',
    'pedido_venda_moto',
    'titulo_financeiro',
    'embarque_moto',
    'embarque_pedido',
    'comissao_vendedor'
)
AND table_schema = 'public'
ORDER BY table_name, ordinal_position;


-- ============================================================
-- FIM DA MIGRAÇÃO
-- ============================================================
-- IMPORTANTE: Após executar, reiniciar aplicação Flask
-- ============================================================
