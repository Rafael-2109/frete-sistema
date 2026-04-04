-- ============================================================================
-- MIGRATION: Auditoria Supply Chain (Event Sourcing para ML)
-- ============================================================================
-- Cria tabela evento_supply_chain + trigger function + 6 triggers + indices.
-- Captura 100% dos writes em: carteira_principal, separacao, faturamento_produto,
-- movimentacao_estoque, programacao_producao, pedido_compras.
--
-- Uso: Executar via Render Shell ou psql
-- Data: 2026-04-04
-- ============================================================================

-- ============================================================================
-- 1. TABELA
-- ============================================================================
CREATE TABLE IF NOT EXISTS evento_supply_chain (
    id                  BIGSERIAL PRIMARY KEY,

    -- Evento
    tipo_evento         VARCHAR(10)   NOT NULL,  -- INSERT, UPDATE, DELETE
    entidade            VARCHAR(30)   NOT NULL,  -- carteira, separacao, faturamento, movimentacao, producao, compra
    entidade_id         INTEGER,                 -- PK do registro afetado

    -- Campos de negocio desnormalizados (query direta sem parsear JSONB)
    num_pedido          VARCHAR(50),
    cod_produto         VARCHAR(50),
    numero_nf           VARCHAR(20),
    separacao_lote_id   VARCHAR(50),

    -- Quantidade (campo principal de cada entidade)
    quantidade_anterior NUMERIC(15,3),  -- OLD.qtd_* (NULL em INSERT)
    quantidade_nova     NUMERIC(15,3),  -- NEW.qtd_* (NULL em DELETE)

    -- Projecao de estoque (preenchido por Python pos-commit)
    qtd_projetada_dia   NUMERIC(15,3),

    -- Snapshot completo
    dados_antes         JSONB,          -- row_to_json(OLD) — NULL em INSERT
    dados_depois        JSONB,          -- row_to_json(NEW) — NULL em DELETE
    campos_alterados    TEXT[],         -- Lista de campos que mudaram (so UPDATE)

    -- Contexto
    origem              VARCHAR(50),    -- current_setting('app.origin')
    session_id          VARCHAR(100),   -- current_setting('app.session_id')
    registrado_em       TIMESTAMP       NOT NULL DEFAULT NOW(),
    registrado_por      VARCHAR(100)    -- current_setting('app.current_user')
);

-- ============================================================================
-- 2. INDICES
-- ============================================================================

-- Series temporais por produto (ML)
CREATE INDEX IF NOT EXISTS idx_esc_produto_tempo
    ON evento_supply_chain (cod_produto, registrado_em DESC);

-- Historico do pedido (agente: "o que aconteceu com pedido X?")
CREATE INDEX IF NOT EXISTS idx_esc_pedido_tempo
    ON evento_supply_chain (num_pedido, registrado_em DESC);

-- Filtro por entidade + tempo
CREATE INDEX IF NOT EXISTS idx_esc_entidade_tempo
    ON evento_supply_chain (entidade, registrado_em DESC);

-- Busca por NF (parcial — so indexa quando preenchido)
CREATE INDEX IF NOT EXISTS idx_esc_nf
    ON evento_supply_chain (numero_nf) WHERE numero_nf IS NOT NULL;

-- Busca por lote de separacao (parcial)
CREATE INDEX IF NOT EXISTS idx_esc_lote
    ON evento_supply_chain (separacao_lote_id) WHERE separacao_lote_id IS NOT NULL;

-- Correlacao de sync (parcial)
CREATE INDEX IF NOT EXISTS idx_esc_session
    ON evento_supply_chain (session_id) WHERE session_id IS NOT NULL;

-- BRIN para range scans temporais (tabela append-only — ideal para BRIN)
CREATE INDEX IF NOT EXISTS idx_esc_brin
    ON evento_supply_chain USING BRIN (registrado_em);


-- ============================================================================
-- 3. TRIGGER FUNCTION
-- ============================================================================
-- Funcao generica reutilizada por todas as 6 tabelas.
-- Recebe campos monitorados via TG_ARGV[0] (CSV).
-- Para UPDATEs, so registra se campos monitorados mudaram.
-- NUNCA propaga excecoes (EXCEPTION WHEN OTHERS → RAISE WARNING).
-- ============================================================================

CREATE OR REPLACE FUNCTION audit_supply_chain_trigger()
RETURNS TRIGGER AS $$
DECLARE
    v_entidade         TEXT;
    v_num_pedido       TEXT;
    v_cod_produto      TEXT;
    v_numero_nf        TEXT;
    v_lote_id          TEXT;
    v_qtd_anterior     NUMERIC(15,3);
    v_qtd_nova         NUMERIC(15,3);
    v_campos_alterados TEXT[];
    v_dados_antes      JSONB;
    v_dados_depois     JSONB;
    v_usuario          TEXT;
    v_origem           TEXT;
    v_session_id       TEXT;
    v_campo            TEXT;
    v_old_val          TEXT;
    v_new_val          TEXT;
BEGIN
    -- ========================================
    -- 1. Determinar entidade e campos-chave
    -- ========================================
    CASE TG_TABLE_NAME
        WHEN 'carteira_principal' THEN
            v_entidade     := 'carteira';
            v_num_pedido   := COALESCE(NEW.num_pedido, OLD.num_pedido);
            v_cod_produto  := COALESCE(NEW.cod_produto, OLD.cod_produto);
            v_numero_nf    := NULL;
            v_lote_id      := NULL;
            v_qtd_anterior := CASE WHEN TG_OP IN ('UPDATE','DELETE') THEN OLD.qtd_saldo_produto_pedido ELSE NULL END;
            v_qtd_nova     := CASE WHEN TG_OP IN ('INSERT','UPDATE') THEN NEW.qtd_saldo_produto_pedido ELSE NULL END;

        WHEN 'separacao' THEN
            v_entidade     := 'separacao';
            v_num_pedido   := COALESCE(NEW.num_pedido, OLD.num_pedido);
            v_cod_produto  := COALESCE(NEW.cod_produto, OLD.cod_produto);
            v_numero_nf    := COALESCE(NEW.numero_nf, OLD.numero_nf);
            v_lote_id      := COALESCE(NEW.separacao_lote_id, OLD.separacao_lote_id);
            v_qtd_anterior := CASE WHEN TG_OP IN ('UPDATE','DELETE') THEN OLD.qtd_saldo ELSE NULL END;
            v_qtd_nova     := CASE WHEN TG_OP IN ('INSERT','UPDATE') THEN NEW.qtd_saldo ELSE NULL END;

        WHEN 'faturamento_produto' THEN
            v_entidade     := 'faturamento';
            v_num_pedido   := COALESCE(NEW.origem, OLD.origem);
            v_cod_produto  := COALESCE(NEW.cod_produto, OLD.cod_produto);
            v_numero_nf    := COALESCE(NEW.numero_nf, OLD.numero_nf);
            v_lote_id      := NULL;
            v_qtd_anterior := CASE WHEN TG_OP IN ('UPDATE','DELETE') THEN OLD.qtd_produto_faturado ELSE NULL END;
            v_qtd_nova     := CASE WHEN TG_OP IN ('INSERT','UPDATE') THEN NEW.qtd_produto_faturado ELSE NULL END;

        WHEN 'movimentacao_estoque' THEN
            v_entidade     := 'movimentacao';
            v_num_pedido   := COALESCE(NEW.num_pedido, OLD.num_pedido);
            v_cod_produto  := COALESCE(NEW.cod_produto, OLD.cod_produto);
            v_numero_nf    := COALESCE(NEW.numero_nf, OLD.numero_nf);
            v_lote_id      := COALESCE(NEW.separacao_lote_id, OLD.separacao_lote_id);
            v_qtd_anterior := CASE WHEN TG_OP IN ('UPDATE','DELETE') THEN OLD.qtd_movimentacao ELSE NULL END;
            v_qtd_nova     := CASE WHEN TG_OP IN ('INSERT','UPDATE') THEN NEW.qtd_movimentacao ELSE NULL END;

        WHEN 'programacao_producao' THEN
            v_entidade     := 'producao';
            v_num_pedido   := NULL;
            v_cod_produto  := COALESCE(NEW.cod_produto, OLD.cod_produto);
            v_numero_nf    := NULL;
            v_lote_id      := NULL;
            v_qtd_anterior := CASE WHEN TG_OP IN ('UPDATE','DELETE') THEN OLD.qtd_programada ELSE NULL END;
            v_qtd_nova     := CASE WHEN TG_OP IN ('INSERT','UPDATE') THEN NEW.qtd_programada ELSE NULL END;

        WHEN 'pedido_compras' THEN
            v_entidade     := 'compra';
            v_num_pedido   := COALESCE(NEW.num_pedido, OLD.num_pedido);
            v_cod_produto  := COALESCE(NEW.cod_produto, OLD.cod_produto);
            v_numero_nf    := COALESCE(NEW.nf_numero, OLD.nf_numero);
            v_lote_id      := NULL;
            v_qtd_anterior := CASE WHEN TG_OP IN ('UPDATE','DELETE') THEN OLD.qtd_produto_pedido ELSE NULL END;
            v_qtd_nova     := CASE WHEN TG_OP IN ('INSERT','UPDATE') THEN NEW.qtd_produto_pedido ELSE NULL END;

        ELSE
            -- Tabela desconhecida — registrar sem campos especificos
            v_entidade     := TG_TABLE_NAME;
            v_num_pedido   := NULL;
            v_cod_produto  := NULL;
            v_numero_nf    := NULL;
            v_lote_id      := NULL;
            v_qtd_anterior := NULL;
            v_qtd_nova     := NULL;
    END CASE;

    -- ========================================
    -- 2. Capturar snapshots JSONB (ANTES do filtro de UPDATE)
    --    Reutilizados para comparacao de campos E para dados_antes/depois
    -- ========================================
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        v_dados_antes := row_to_json(OLD)::JSONB;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        v_dados_depois := row_to_json(NEW)::JSONB;
    END IF;

    -- ========================================
    -- 3. Para UPDATE: filtrar ruido
    --    So registrar se campos MONITORADOS mudaram
    --    Usa operador JSONB ->> (sem EXECUTE, ~10x mais rapido)
    -- ========================================
    IF TG_OP = 'UPDATE' AND TG_NARGS > 0 THEN
        v_campos_alterados := ARRAY[]::TEXT[];

        FOREACH v_campo IN ARRAY string_to_array(TG_ARGV[0], ',')
        LOOP
            v_old_val := v_dados_antes ->> v_campo;
            v_new_val := v_dados_depois ->> v_campo;
            IF v_old_val IS DISTINCT FROM v_new_val THEN
                v_campos_alterados := array_append(v_campos_alterados, v_campo);
            END IF;
        END LOOP;

        -- Se nenhum campo monitorado mudou, nao registrar evento
        IF array_length(v_campos_alterados, 1) IS NULL THEN
            RETURN NEW;
        END IF;
    END IF;

    -- ========================================
    -- 4. Ler contexto Flask (session variables)
    --    current_setting(..., true) retorna NULL se nao setado
    -- ========================================
    v_usuario    := current_setting('app.current_user', true);
    v_origem     := current_setting('app.origin', true);
    v_session_id := NULLIF(current_setting('app.session_id', true), '');

    -- ========================================
    -- 5. Inserir evento (com LEFT para prevenir truncation)
    -- ========================================
    INSERT INTO evento_supply_chain (
        tipo_evento, entidade, entidade_id,
        num_pedido, cod_produto, numero_nf, separacao_lote_id,
        quantidade_anterior, quantidade_nova,
        dados_antes, dados_depois, campos_alterados,
        origem, session_id, registrado_por
    ) VALUES (
        TG_OP,
        v_entidade,
        CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END,
        LEFT(v_num_pedido, 50), LEFT(v_cod_produto, 50),
        LEFT(v_numero_nf, 20), LEFT(v_lote_id, 50),
        v_qtd_anterior, v_qtd_nova,
        v_dados_antes, v_dados_depois, v_campos_alterados,
        LEFT(COALESCE(v_origem, 'SISTEMA'), 50),
        LEFT(v_session_id, 100),
        LEFT(COALESCE(v_usuario, 'SISTEMA'), 100)
    );

    -- Retornar a row apropriada
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;

EXCEPTION
    WHEN undefined_table THEN
        -- Tabela evento_supply_chain nao existe (migration pendente)
        -- Log minimo para nao gerar flood
        RAISE LOG '[AUDIT_SC] Tabela evento_supply_chain inexistente — migration pendente';
        IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    WHEN OTHERS THEN
        -- Qualquer outro erro — nunca quebrar a operacao principal
        RAISE WARNING '[AUDIT_SC] Erro no trigger % (% on %): % (SQLSTATE: %)',
            TG_NAME, TG_OP, TG_TABLE_NAME, SQLERRM, SQLSTATE;
        IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- 4. TRIGGERS (1 por tabela, com campos monitorados como argumento)
-- ============================================================================

-- CarteiraPrincipal
DROP TRIGGER IF EXISTS trg_audit_carteira ON carteira_principal;
CREATE TRIGGER trg_audit_carteira
    AFTER INSERT OR UPDATE OR DELETE ON carteira_principal
    FOR EACH ROW EXECUTE FUNCTION audit_supply_chain_trigger(
        'qtd_produto_pedido,qtd_saldo_produto_pedido,qtd_cancelada_produto_pedido,data_entrega_pedido,status_pedido,observ_ped_1,preco_produto_pedido,ativo'
    );

-- Separacao
DROP TRIGGER IF EXISTS trg_audit_separacao ON separacao;
CREATE TRIGGER trg_audit_separacao
    AFTER INSERT OR UPDATE OR DELETE ON separacao
    FOR EACH ROW EXECUTE FUNCTION audit_supply_chain_trigger(
        'qtd_saldo,expedicao,agendamento,agendamento_confirmado,status,sincronizado_nf,numero_nf,cotacao_id,nf_cd,falta_item,falta_pagamento,data_embarque,protocolo,obs_separacao'
    );

-- FaturamentoProduto
DROP TRIGGER IF EXISTS trg_audit_faturamento ON faturamento_produto;
CREATE TRIGGER trg_audit_faturamento
    AFTER INSERT OR UPDATE OR DELETE ON faturamento_produto
    FOR EACH ROW EXECUTE FUNCTION audit_supply_chain_trigger(
        'qtd_produto_faturado,status_nf,revertida,nota_credito_id'
    );

-- MovimentacaoEstoque
DROP TRIGGER IF EXISTS trg_audit_movimentacao ON movimentacao_estoque;
CREATE TRIGGER trg_audit_movimentacao
    AFTER INSERT OR UPDATE OR DELETE ON movimentacao_estoque
    FOR EACH ROW EXECUTE FUNCTION audit_supply_chain_trigger(
        'qtd_movimentacao,tipo_movimentacao,local_movimentacao,ativo,baixado,status_nf'
    );

-- ProgramacaoProducao
DROP TRIGGER IF EXISTS trg_audit_producao ON programacao_producao;
CREATE TRIGGER trg_audit_producao
    AFTER INSERT OR UPDATE OR DELETE ON programacao_producao
    FOR EACH ROW EXECUTE FUNCTION audit_supply_chain_trigger(
        'qtd_programada,data_programacao,linha_producao,ordem_producao'
    );

-- PedidoCompras
DROP TRIGGER IF EXISTS trg_audit_compras ON pedido_compras;
CREATE TRIGGER trg_audit_compras
    AFTER INSERT OR UPDATE OR DELETE ON pedido_compras
    FOR EACH ROW EXECUTE FUNCTION audit_supply_chain_trigger(
        'qtd_produto_pedido,qtd_recebida,status_odoo,data_pedido_previsao,data_pedido_entrega,tipo_pedido,nf_numero,nf_chave_acesso'
    );


-- ============================================================================
-- 5. VERIFICACAO
-- ============================================================================
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Verificar tabela
    SELECT count(*) INTO v_count
    FROM information_schema.tables
    WHERE table_name = 'evento_supply_chain';

    IF v_count = 1 THEN
        RAISE NOTICE '[OK] Tabela evento_supply_chain criada';
    ELSE
        RAISE WARNING '[ERRO] Tabela evento_supply_chain NAO encontrada';
    END IF;

    -- Verificar triggers
    SELECT count(*) INTO v_count
    FROM information_schema.triggers
    WHERE trigger_name LIKE 'trg_audit_%';

    RAISE NOTICE '[OK] % triggers de auditoria criados', v_count;

    -- Verificar indices
    SELECT count(*) INTO v_count
    FROM pg_indexes
    WHERE tablename = 'evento_supply_chain';

    RAISE NOTICE '[OK] % indices criados na tabela', v_count;
END $$;
