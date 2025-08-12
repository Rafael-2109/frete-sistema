-- =====================================================
-- MIGRAÇÃO: Melhorias no Módulo Manufatura/PCP
-- Data: 11/08/2025
-- Descrição: Adiciona campos necessários para atender processo completo
-- =====================================================

-- 1. ADICIONAR CAMPOS DE RELACIONAMENTO PAI-FILHO EM ORDENS
ALTER TABLE ordem_producao 
ADD COLUMN IF NOT EXISTS ordem_pai_id INTEGER REFERENCES ordem_producao(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS tipo_ordem VARCHAR(20) DEFAULT 'principal', -- 'principal', 'filha'
ADD COLUMN IF NOT EXISTS data_necessidade DATE,
ADD COLUMN IF NOT EXISTS nivel_bom INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS recalculo_automatico BOOLEAN DEFAULT TRUE;

-- Criar índice para melhor performance
CREATE INDEX IF NOT EXISTS idx_ordem_producao_pai ON ordem_producao(ordem_pai_id);
CREATE INDEX IF NOT EXISTS idx_ordem_producao_tipo ON ordem_producao(tipo_ordem);

-- 2. ADICIONAR CAMPOS DE VÍNCULO COM ODOO EM REQUISIÇÕES
ALTER TABLE requisicao_compras
ADD COLUMN IF NOT EXISTS requisicao_odoo_id VARCHAR(50),
ADD COLUMN IF NOT EXISTS status_requisicao VARCHAR(20) DEFAULT 'rascunho', -- 'rascunho', 'enviada_odoo', 'confirmada', 'cancelada'
ADD COLUMN IF NOT EXISTS data_envio_odoo TIMESTAMP,
ADD COLUMN IF NOT EXISTS data_confirmacao_odoo TIMESTAMP,
ADD COLUMN IF NOT EXISTS observacoes_odoo TEXT;

-- Criar índice para busca por ID Odoo
CREATE INDEX IF NOT EXISTS idx_requisicao_odoo_id ON requisicao_compras(requisicao_odoo_id);

-- 3. ADICIONAR CAMPOS DE SEQUENCIAMENTO EM ORDENS
ALTER TABLE ordem_producao
ADD COLUMN IF NOT EXISTS sequencia_producao INTEGER,
ADD COLUMN IF NOT EXISTS disponibilidade_componentes NUMERIC(5,2) DEFAULT 0, -- % disponível
ADD COLUMN IF NOT EXISTS data_disponibilidade_componentes DATE,
ADD COLUMN IF NOT EXISTS maquina_alocada VARCHAR(50),
ADD COLUMN IF NOT EXISTS tempo_setup_minutos INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS capacidade_maquina_hora NUMERIC(15,3);

-- 4. REMOVIDO - Lead time deve vir de LeadTimeFornecedor, não de ListaMateriais

-- 5. MELHORIAS NO PLANO MESTRE PARA VISUALIZAÇÃO
ALTER TABLE plano_mestre_producao
ADD COLUMN IF NOT EXISTS qtd_carteira_pedidos NUMERIC(15,3) DEFAULT 0,
ADD COLUMN IF NOT EXISTS qtd_ordens_abertas NUMERIC(15,3) DEFAULT 0,
ADD COLUMN IF NOT EXISTS ruptura_prevista BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS dias_cobertura INTEGER,
ADD COLUMN IF NOT EXISTS prioridade_producao INTEGER DEFAULT 5; -- 1-10

-- 6. ADICIONAR TABELA DE RECURSOS/MÁQUINAS (se não existe)
CREATE TABLE IF NOT EXISTS recursos_maquinas (
    id SERIAL PRIMARY KEY,
    codigo_maquina VARCHAR(50) UNIQUE NOT NULL,
    nome_maquina VARCHAR(200) NOT NULL,
    tipo_maquina VARCHAR(50),
    capacidade_hora NUMERIC(15,3),
    produtos_compativeis TEXT, -- JSON array de códigos
    tempo_setup_padrao INTEGER DEFAULT 30, -- minutos
    status_maquina VARCHAR(20) DEFAULT 'disponivel', -- 'disponivel', 'manutencao', 'ocupada'
    proxima_disponibilidade TIMESTAMP,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. ADICIONAR TABELA DE SEQUENCIAMENTO (para visualização Gantt)
CREATE TABLE IF NOT EXISTS sequenciamento_producao (
    id SERIAL PRIMARY KEY,
    ordem_producao_id INTEGER REFERENCES ordem_producao(id) ON DELETE CASCADE,
    maquina_id INTEGER REFERENCES recursos_maquinas(id),
    data_inicio_programado TIMESTAMP NOT NULL,
    data_fim_programado TIMESTAMP NOT NULL,
    sequencia INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'planejado', -- 'planejado', 'confirmado', 'em_producao', 'concluido'
    pode_quebrar BOOLEAN DEFAULT FALSE,
    qtd_quebra_sugerida NUMERIC(15,3),
    observacoes TEXT,
    criado_por VARCHAR(100),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(maquina_id, data_inicio_programado, data_fim_programado)
);

-- 8. ADICIONAR HISTÓRICO DE MUDANÇAS EM ORDENS (para rastreabilidade)
CREATE TABLE IF NOT EXISTS historico_ordem_producao (
    id SERIAL PRIMARY KEY,
    ordem_producao_id INTEGER REFERENCES ordem_producao(id),
    tipo_mudanca VARCHAR(50), -- 'criacao', 'alteracao_qtd', 'alteracao_data', 'cancelamento'
    valores_anteriores JSONB,
    valores_novos JSONB,
    motivo_mudanca TEXT,
    impacto_ordens_filhas BOOLEAN DEFAULT FALSE,
    usuario VARCHAR(100),
    data_mudanca TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. VIEW PARA VISUALIZAÇÃO DO PLANO MESTRE COMPLETO
CREATE OR REPLACE VIEW vw_plano_mestre_completo AS
SELECT 
    pmp.*,
    -- Cálculo de produção programada atualizado
    COALESCE((
        SELECT SUM(op.qtd_planejada)
        FROM ordem_producao op
        WHERE op.cod_produto = pmp.cod_produto
        AND op.status IN ('Planejada', 'Liberada', 'Em Produção')
        AND EXTRACT(MONTH FROM op.data_fim_prevista) = pmp.data_mes
        AND EXTRACT(YEAR FROM op.data_fim_prevista) = pmp.data_ano
    ), 0) as qtd_producao_programada_atual,
    -- Cálculo de necessidade líquida
    GREATEST(
        0,
        COALESCE(pmp.qtd_demanda_prevista, 0) + 
        COALESCE(pmp.qtd_estoque_seguranca, 0) - 
        COALESCE(pmp.qtd_estoque, 0) - 
        COALESCE((
            SELECT SUM(op.qtd_planejada)
            FROM ordem_producao op
            WHERE op.cod_produto = pmp.cod_produto
            AND op.status IN ('Planejada', 'Liberada', 'Em Produção')
            AND EXTRACT(MONTH FROM op.data_fim_prevista) = pmp.data_mes
            AND EXTRACT(YEAR FROM op.data_fim_prevista) = pmp.data_ano
        ), 0)
    ) as necessidade_liquida,
    -- Indicador de criticidade
    CASE 
        WHEN COALESCE(pmp.qtd_estoque, 0) < COALESCE(pmp.qtd_estoque_seguranca, 0) THEN 'CRÍTICO'
        WHEN COALESCE(pmp.qtd_estoque, 0) < (COALESCE(pmp.qtd_estoque_seguranca, 0) * 1.2) THEN 'ATENÇÃO'
        ELSE 'NORMAL'
    END as status_estoque
FROM plano_mestre_producao pmp;

-- 10. FUNÇÃO PARA CALCULAR DATA NECESSIDADE COM LEAD TIME
CREATE OR REPLACE FUNCTION calcular_data_necessidade(
    p_data_entrega DATE,
    p_lead_time INTEGER
) RETURNS DATE AS $$
DECLARE
    v_data_necessidade DATE;
    v_dias_uteis INTEGER := 0;
    v_data_atual DATE;
BEGIN
    v_data_atual := p_data_entrega;
    
    WHILE v_dias_uteis < p_lead_time LOOP
        v_data_atual := v_data_atual - INTERVAL '1 day';
        -- Pular fins de semana (sábado = 6, domingo = 0)
        IF EXTRACT(DOW FROM v_data_atual) NOT IN (0, 6) THEN
            v_dias_uteis := v_dias_uteis + 1;
        END IF;
    END LOOP;
    
    RETURN v_data_atual;
END;
$$ LANGUAGE plpgsql;

-- 11. TRIGGER PARA ATUALIZAR ORDENS FILHAS QUANDO PAI MUDA
CREATE OR REPLACE FUNCTION atualizar_ordens_filhas() RETURNS TRIGGER AS $$
BEGIN
    -- Se a ordem pai teve mudança de data ou quantidade
    IF (OLD.data_fim_prevista != NEW.data_fim_prevista OR 
        OLD.qtd_planejada != NEW.qtd_planejada) AND
        NEW.recalculo_automatico = TRUE THEN
        
        -- Atualizar datas das ordens filhas
        UPDATE ordem_producao
        SET data_necessidade = calcular_data_necessidade(NEW.data_inicio_prevista, 1),
            data_fim_prevista = NEW.data_inicio_prevista - INTERVAL '1 day',
            atualizado_em = CURRENT_TIMESTAMP
        WHERE ordem_pai_id = NEW.id;
        
        -- Registrar no histórico
        INSERT INTO historico_ordem_producao (
            ordem_producao_id, tipo_mudanca, valores_anteriores, valores_novos,
            motivo_mudanca, impacto_ordens_filhas, usuario
        ) VALUES (
            NEW.id, 'alteracao_data',
            jsonb_build_object('data_fim_prevista', OLD.data_fim_prevista, 'qtd_planejada', OLD.qtd_planejada),
            jsonb_build_object('data_fim_prevista', NEW.data_fim_prevista, 'qtd_planejada', NEW.qtd_planejada),
            'Alteração automática via trigger', TRUE, 'Sistema'
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Criar trigger
DROP TRIGGER IF EXISTS trigger_atualizar_ordens_filhas ON ordem_producao;
CREATE TRIGGER trigger_atualizar_ordens_filhas
    AFTER UPDATE ON ordem_producao
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_ordens_filhas();

-- 12. ÍNDICES PARA PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_ordem_producao_data_necessidade ON ordem_producao(data_necessidade);
CREATE INDEX IF NOT EXISTS idx_sequenciamento_maquina_data ON sequenciamento_producao(maquina_id, data_inicio_programado);
CREATE INDEX IF NOT EXISTS idx_historico_ordem ON historico_ordem_producao(ordem_producao_id, data_mudanca);

-- =====================================================
-- FIM DA MIGRAÇÃO
-- Execute com: psql -U seu_usuario -d seu_banco -f manufatura_melhorias_processo.sql
-- =====================================================