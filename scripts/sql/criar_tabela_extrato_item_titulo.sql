-- ============================================================================
-- CRIAÇÃO: Tabela extrato_item_titulo (associação M:N)
-- ============================================================================
-- Permite vincular múltiplos títulos a uma única linha de extrato.
--
-- Cenários:
-- 1. Pagamento agrupado: Cliente paga 3 NFs de uma vez
-- 2. Alocação parcial: Extrato R$ 10.000, título R$ 12.000 (paga 83,3%)
--
-- Data: 2025-12-15
-- ============================================================================

-- 1. CRIAR TABELA
CREATE TABLE IF NOT EXISTS extrato_item_titulo (
    id SERIAL PRIMARY KEY,

    -- Relacionamentos
    extrato_item_id INTEGER NOT NULL REFERENCES extrato_item(id) ON DELETE CASCADE,
    titulo_receber_id INTEGER REFERENCES contas_a_receber(id),
    titulo_pagar_id INTEGER REFERENCES contas_a_pagar(id),

    -- Dados da alocação
    valor_alocado NUMERIC(15, 2) NOT NULL,
    valor_titulo_original NUMERIC(15, 2),
    percentual_alocado NUMERIC(5, 2),

    -- Cache (desnormalizado para performance)
    titulo_nf VARCHAR(50),
    titulo_parcela INTEGER,
    titulo_vencimento DATE,
    titulo_cliente VARCHAR(255),
    titulo_cnpj VARCHAR(20),
    match_score INTEGER,
    match_criterio VARCHAR(100),

    -- Controle de processamento
    status VARCHAR(30) DEFAULT 'PENDENTE' NOT NULL,
    aprovado BOOLEAN DEFAULT FALSE NOT NULL,
    aprovado_em TIMESTAMP,
    aprovado_por VARCHAR(100),

    -- Resultado da conciliação
    partial_reconcile_id INTEGER,
    full_reconcile_id INTEGER,
    payment_id INTEGER,
    titulo_saldo_antes NUMERIC(15, 2),
    titulo_saldo_depois NUMERIC(15, 2),
    mensagem TEXT,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processado_em TIMESTAMP,

    -- Constraint: título receber OU pagar, não ambos
    CONSTRAINT chk_titulo_receber_ou_pagar CHECK (
        (titulo_receber_id IS NOT NULL AND titulo_pagar_id IS NULL) OR
        (titulo_receber_id IS NULL AND titulo_pagar_id IS NOT NULL)
    )
);

-- 2. CRIAR ÍNDICES
CREATE INDEX IF NOT EXISTS idx_extrato_titulo_item ON extrato_item_titulo(extrato_item_id);
CREATE INDEX IF NOT EXISTS idx_extrato_titulo_receber ON extrato_item_titulo(titulo_receber_id);
CREATE INDEX IF NOT EXISTS idx_extrato_titulo_pagar ON extrato_item_titulo(titulo_pagar_id);
CREATE INDEX IF NOT EXISTS idx_extrato_titulo_status ON extrato_item_titulo(status);

-- 3. COMENTÁRIOS
COMMENT ON TABLE extrato_item_titulo IS 'Associação M:N entre linhas de extrato e títulos (receber/pagar)';
COMMENT ON COLUMN extrato_item_titulo.valor_alocado IS 'Valor deste título alocado ao pagamento';
COMMENT ON COLUMN extrato_item_titulo.percentual_alocado IS 'Percentual do título que está sendo pago';
COMMENT ON COLUMN extrato_item_titulo.status IS 'PENDENTE, APROVADO, CONCILIADO, ERRO';

-- ============================================================================
-- VERIFICAÇÃO
-- ============================================================================
SELECT
    'extrato_item_titulo' as tabela,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'extrato_item_titulo') as num_colunas,
    (SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'extrato_item_titulo') as num_indices;
