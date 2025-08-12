-- =====================================================
-- MIGRAÇÃO SIMPLIFICADA: Módulo Manufatura/PCP
-- Data: 11/08/2025
-- Descrição: Adiciona apenas os campos essenciais
-- =====================================================

-- 1. CAMPOS DE RELACIONAMENTO PAI-FILHO EM ORDENS
ALTER TABLE ordem_producao 
ADD COLUMN IF NOT EXISTS ordem_pai_id INTEGER REFERENCES ordem_producao(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS tipo_ordem VARCHAR(20) DEFAULT 'principal',
ADD COLUMN IF NOT EXISTS data_necessidade DATE,
ADD COLUMN IF NOT EXISTS nivel_bom INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS recalculo_automatico BOOLEAN DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS idx_ordem_producao_pai ON ordem_producao(ordem_pai_id);
CREATE INDEX IF NOT EXISTS idx_ordem_producao_tipo ON ordem_producao(tipo_ordem);

-- 2. CAMPOS DE VÍNCULO COM ODOO EM REQUISIÇÕES
ALTER TABLE requisicao_compras
ADD COLUMN IF NOT EXISTS requisicao_odoo_id VARCHAR(50),
ADD COLUMN IF NOT EXISTS status_requisicao VARCHAR(20) DEFAULT 'rascunho',
ADD COLUMN IF NOT EXISTS data_envio_odoo TIMESTAMP,
ADD COLUMN IF NOT EXISTS data_confirmacao_odoo TIMESTAMP,
ADD COLUMN IF NOT EXISTS observacoes_odoo TEXT;

CREATE INDEX IF NOT EXISTS idx_requisicao_odoo_id ON requisicao_compras(requisicao_odoo_id);

-- 3. CAMPOS DE SEQUENCIAMENTO JÁ EXISTENTES EM ORDENS
-- Apenas adicionar os que faltam
ALTER TABLE ordem_producao
ADD COLUMN IF NOT EXISTS sequencia_producao INTEGER,
ADD COLUMN IF NOT EXISTS disponibilidade_componentes NUMERIC(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS data_disponibilidade_componentes DATE,
ADD COLUMN IF NOT EXISTS maquina_alocada VARCHAR(50),
ADD COLUMN IF NOT EXISTS tempo_setup_minutos INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS capacidade_maquina_hora NUMERIC(15,3);

-- 4. CAMPOS EXTRAS NO PLANO MESTRE PARA VISUALIZAÇÃO
ALTER TABLE plano_mestre_producao
ADD COLUMN IF NOT EXISTS qtd_carteira_pedidos NUMERIC(15,3) DEFAULT 0,
ADD COLUMN IF NOT EXISTS qtd_ordens_abertas NUMERIC(15,3) DEFAULT 0,
ADD COLUMN IF NOT EXISTS ruptura_prevista BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS dias_cobertura INTEGER,
ADD COLUMN IF NOT EXISTS prioridade_producao INTEGER DEFAULT 5;

-- 5. TABELA DE HISTÓRICO (GERENCIADA POR TRIGGER)
CREATE TABLE IF NOT EXISTS historico_ordem_producao (
    id SERIAL PRIMARY KEY,
    ordem_producao_id INTEGER REFERENCES ordem_producao(id),
    tipo_mudanca VARCHAR(50),
    valores_anteriores JSONB,
    valores_novos JSONB,
    motivo_mudanca TEXT,
    impacto_ordens_filhas BOOLEAN DEFAULT FALSE,
    usuario VARCHAR(100),
    data_mudanca TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. VIEW SIMPLIFICADA DO PLANO MESTRE
CREATE OR REPLACE VIEW vw_plano_mestre_completo AS
SELECT 
    pmp.*,
    COALESCE((
        SELECT SUM(op.qtd_planejada)
        FROM ordem_producao op
        WHERE op.cod_produto = pmp.cod_produto
        AND op.status IN ('Planejada', 'Liberada', 'Em Produção')
        AND EXTRACT(MONTH FROM op.data_fim_prevista) = pmp.data_mes
        AND EXTRACT(YEAR FROM op.data_fim_prevista) = pmp.data_ano
    ), 0) as qtd_producao_programada_atual,
    GREATEST(
        0,
        COALESCE(pmp.qtd_demanda_prevista, 0) + 
        COALESCE(pmp.qtd_estoque_seguranca, 0) - 
        COALESCE(pmp.qtd_estoque, 0)
    ) as necessidade_liquida,
    CASE 
        WHEN COALESCE(pmp.qtd_estoque, 0) < COALESCE(pmp.qtd_estoque_seguranca, 0) THEN 'CRÍTICO'
        WHEN COALESCE(pmp.qtd_estoque, 0) < (COALESCE(pmp.qtd_estoque_seguranca, 0) * 1.2) THEN 'ATENÇÃO'
        ELSE 'NORMAL'
    END as status_estoque
FROM plano_mestre_producao pmp;

-- 7. FUNÇÃO PARA CALCULAR DATA COM LEAD TIME
CREATE OR REPLACE FUNCTION calcular_data_necessidade(
    p_data_entrega DATE,
    p_lead_time INTEGER
) RETURNS DATE AS $$
DECLARE
    v_data_atual DATE;
    v_dias_uteis INTEGER := 0;
BEGIN
    v_data_atual := p_data_entrega;
    
    WHILE v_dias_uteis < p_lead_time LOOP
        v_data_atual := v_data_atual - INTERVAL '1 day';
        IF EXTRACT(DOW FROM v_data_atual) NOT IN (0, 6) THEN
            v_dias_uteis := v_dias_uteis + 1;
        END IF;
    END LOOP;
    
    RETURN v_data_atual;
END;
$$ LANGUAGE plpgsql;

-- 8. TRIGGER PARA ATUALIZAR ORDENS FILHAS
CREATE OR REPLACE FUNCTION atualizar_ordens_filhas() RETURNS TRIGGER AS $$
BEGIN
    IF (OLD.data_fim_prevista != NEW.data_fim_prevista OR 
        OLD.qtd_planejada != NEW.qtd_planejada) AND
        NEW.recalculo_automatico = TRUE THEN
        
        UPDATE ordem_producao
        SET data_necessidade = calcular_data_necessidade(NEW.data_inicio_prevista, 1),
            data_fim_prevista = NEW.data_inicio_prevista - INTERVAL '1 day',
            atualizado_em = CURRENT_TIMESTAMP
        WHERE ordem_pai_id = NEW.id;
        
        INSERT INTO historico_ordem_producao (
            ordem_producao_id, tipo_mudanca, valores_anteriores, valores_novos,
            motivo_mudanca, impacto_ordens_filhas, usuario
        ) VALUES (
            NEW.id, 'alteracao_automatica',
            jsonb_build_object('data_fim_prevista', OLD.data_fim_prevista, 'qtd_planejada', OLD.qtd_planejada),
            jsonb_build_object('data_fim_prevista', NEW.data_fim_prevista, 'qtd_planejada', NEW.qtd_planejada),
            'Alteração automática via trigger', TRUE, 'Sistema'
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_atualizar_ordens_filhas ON ordem_producao;
CREATE TRIGGER trigger_atualizar_ordens_filhas
    AFTER UPDATE ON ordem_producao
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_ordens_filhas();

-- 9. ÍNDICES PARA PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_ordem_producao_data_necessidade ON ordem_producao(data_necessidade);
CREATE INDEX IF NOT EXISTS idx_ordem_sequencia ON ordem_producao(sequencia_producao, linha_producao);
CREATE INDEX IF NOT EXISTS idx_historico_ordem ON historico_ordem_producao(ordem_producao_id, data_mudanca);

-- =====================================================
-- FIM DA MIGRAÇÃO SIMPLIFICADA
-- Execute com: psql -U seu_usuario -d seu_banco -f manufatura_melhorias_simplificadas.sql
-- =====================================================