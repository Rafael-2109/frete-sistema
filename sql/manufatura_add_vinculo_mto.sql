-- =====================================================
-- Migração: Adicionar campos de vínculo MTO em ordem_producao
-- Data: 2025-01-10
-- Descrição: Adiciona campos para vincular ordens MTO com pedidos
--            via separacao_lote_id, evitando perda com atualizações
-- =====================================================

BEGIN;

-- Adicionar campos de vínculo MTO na tabela ordem_producao
ALTER TABLE ordem_producao 
ADD COLUMN IF NOT EXISTS separacao_lote_id VARCHAR(50),
ADD COLUMN IF NOT EXISTS num_pedido_origem VARCHAR(50),
ADD COLUMN IF NOT EXISTS raz_social_red VARCHAR(255),
ADD COLUMN IF NOT EXISTS qtd_pedido_atual NUMERIC(15,3);

-- Criar índice para busca rápida por separacao_lote_id
CREATE INDEX IF NOT EXISTS idx_op_separacao_lote 
ON ordem_producao(separacao_lote_id);

-- Comentários nos campos
COMMENT ON COLUMN ordem_producao.separacao_lote_id IS 'Vínculo principal com pedido MTO via separacao_lote_id';
COMMENT ON COLUMN ordem_producao.num_pedido_origem IS 'Número do pedido de origem para referência';
COMMENT ON COLUMN ordem_producao.raz_social_red IS 'Razão social reduzida do cliente';
COMMENT ON COLUMN ordem_producao.qtd_pedido_atual IS 'Quantidade atual do pedido para validação';

-- Remover campo antigo de vínculo se existir (estava em CarteiraPrincipal)
-- Não vamos mais usar ordem_producao_id em CarteiraPrincipal
-- pois a carteira é substituída nas atualizações

COMMIT;

-- =====================================================
-- Função para validar quantidade MTO
-- =====================================================

CREATE OR REPLACE FUNCTION validar_quantidade_mto(p_separacao_lote_id VARCHAR(50))
RETURNS TABLE(
    qtd_separacao NUMERIC,
    qtd_pre_separacao NUMERIC,
    qtd_final NUMERIC,
    fonte VARCHAR(20)
) AS $$
BEGIN
    -- Verificar primeiro em Separacao (prioridade)
    SELECT 
        s.qtd_saldo,
        NULL::NUMERIC,
        s.qtd_saldo,
        'Separacao'::VARCHAR(20)
    INTO qtd_separacao, qtd_pre_separacao, qtd_final, fonte
    FROM separacao s
    JOIN pedido p ON s.separacao_lote_id = p.separacao_lote_id
    WHERE s.separacao_lote_id = p_separacao_lote_id
    AND p.status != 'FATURADO'
    LIMIT 1;
    
    -- Se encontrou em Separacao, retorna
    IF qtd_separacao IS NOT NULL THEN
        RETURN NEXT;
        RETURN;
    END IF;
    
    -- Se não encontrou, buscar em PreSeparacaoItem
    SELECT 
        NULL::NUMERIC,
        psi.qtd_selecionada_usuario,
        psi.qtd_selecionada_usuario,
        'PreSeparacaoItem'::VARCHAR(20)
    INTO qtd_separacao, qtd_pre_separacao, qtd_final, fonte
    FROM pre_separacao_item psi
    WHERE psi.separacao_lote_id = p_separacao_lote_id
    AND NOT EXISTS (
        SELECT 1 FROM separacao s
        WHERE s.separacao_lote_id = psi.separacao_lote_id
    )
    LIMIT 1;
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- View para monitorar ordens MTO e suas quantidades
-- =====================================================

CREATE OR REPLACE VIEW v_ordens_mto_monitoramento AS
SELECT 
    op.id,
    op.numero_ordem,
    op.separacao_lote_id,
    op.num_pedido_origem,
    op.raz_social_red,
    op.cod_produto,
    op.nome_produto,
    op.qtd_planejada,
    op.qtd_pedido_atual as qtd_pedido_vinculo,
    v.qtd_final as qtd_pedido_atual_real,
    v.fonte as fonte_quantidade,
    CASE 
        WHEN v.qtd_final IS NULL THEN 'Pedido não encontrado'
        WHEN v.qtd_final != op.qtd_pedido_atual THEN 'Quantidade alterada'
        ELSE 'OK'
    END as status_validacao,
    op.status as status_ordem
FROM ordem_producao op
LEFT JOIN LATERAL validar_quantidade_mto(op.separacao_lote_id) v ON true
WHERE op.origem_ordem = 'MTO'
AND op.separacao_lote_id IS NOT NULL;

-- =====================================================
-- Trigger para atualizar quantidade ao criar/atualizar ordem MTO
-- =====================================================

CREATE OR REPLACE FUNCTION atualizar_qtd_pedido_mto()
RETURNS TRIGGER AS $$
DECLARE
    v_qtd_atual NUMERIC;
    v_fonte VARCHAR(20);
BEGIN
    -- Só executa para ordens MTO com separacao_lote_id
    IF NEW.origem_ordem = 'MTO' AND NEW.separacao_lote_id IS NOT NULL THEN
        -- Buscar quantidade atual
        SELECT qtd_final, fonte 
        INTO v_qtd_atual, v_fonte
        FROM validar_quantidade_mto(NEW.separacao_lote_id);
        
        -- Atualizar quantidade
        NEW.qtd_pedido_atual = v_qtd_atual;
        
        -- Log se quantidade mudou
        IF TG_OP = 'UPDATE' AND OLD.qtd_pedido_atual != NEW.qtd_pedido_atual THEN
            RAISE NOTICE 'Quantidade MTO alterada: Ordem %, de % para % (fonte: %)', 
                NEW.numero_ordem, OLD.qtd_pedido_atual, NEW.qtd_pedido_atual, v_fonte;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Criar trigger
DROP TRIGGER IF EXISTS trg_atualizar_qtd_mto ON ordem_producao;
CREATE TRIGGER trg_atualizar_qtd_mto
BEFORE INSERT OR UPDATE ON ordem_producao
FOR EACH ROW
EXECUTE FUNCTION atualizar_qtd_pedido_mto();

-- =====================================================
-- Atualizar ordens MTO existentes (se houver)
-- =====================================================

-- Este update seria executado apenas se já existirem ordens MTO
-- com dados em materiais_necessarios (campo JSON antigo)
UPDATE ordem_producao op
SET qtd_pedido_atual = v.qtd_final
FROM validar_quantidade_mto(op.separacao_lote_id) v
WHERE op.origem_ordem = 'MTO'
AND op.separacao_lote_id IS NOT NULL
AND op.qtd_pedido_atual IS NULL;