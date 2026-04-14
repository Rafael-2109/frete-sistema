-- ============================================================================
-- MIGRATION: Adiciona usuario_id + melhora trigger audit_supply_chain
-- ============================================================================
-- 1. Adiciona coluna usuario_id INTEGER (nullable) na tabela evento_supply_chain
-- 2. Cria indice parcial em usuario_id (so quando preenchido)
-- 3. Recria audit_supply_chain_trigger() com:
--    - Leitura de nova variavel PG app.current_user_id (com fallback seguro)
--    - TRIM defensivo em app.current_user (resolve trailing spaces de usuarios.nome)
--    - BEGIN/EXCEPTION no cast INTEGER (nao quebra se valor invalido)
--    - INSERT inclui usuario_id
--
-- Idempotente: pode ser executado multiplas vezes sem efeito colateral.
-- Compatibilidade: triggers existentes continuam funcionando sem mudanca
-- (CREATE OR REPLACE FUNCTION mantem os 6 triggers).
--
-- Uso: Executar via Render Shell ou psql
-- Data: 2026-04-14
-- ============================================================================

-- ============================================================================
-- 1. ADICIONAR COLUNA usuario_id
-- ============================================================================
ALTER TABLE evento_supply_chain
    ADD COLUMN IF NOT EXISTS usuario_id INTEGER;

-- Indice parcial (so indexa linhas com usuario_id preenchido)
CREATE INDEX IF NOT EXISTS idx_esc_usuario_id
    ON evento_supply_chain (usuario_id, registrado_em DESC)
    WHERE usuario_id IS NOT NULL;


-- ============================================================================
-- 2. RECRIAR TRIGGER FUNCTION
-- ============================================================================
-- Mudancas em relacao a versao original (criar_auditoria_supply_chain.sql):
--   - DECLARE: adiciona v_usuario_id INTEGER
--   - Secao 4 (contexto): TRIM em current_user, bloco BEGIN/EXCEPTION no cast INTEGER
--   - Secao 5 (INSERT): inclui usuario_id
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
    v_usuario_id       INTEGER;
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
    -- ========================================
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        v_dados_antes := row_to_json(OLD)::JSONB;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        v_dados_depois := row_to_json(NEW)::JSONB;
    END IF;

    -- ========================================
    -- 3. Para UPDATE: filtrar ruido
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

        IF array_length(v_campos_alterados, 1) IS NULL THEN
            RETURN NEW;
        END IF;
    END IF;

    -- ========================================
    -- 4. Ler contexto Flask (session variables)
    --    NOVO: TRIM defensivo + leitura de current_user_id com cast seguro
    -- ========================================
    v_usuario    := NULLIF(TRIM(COALESCE(current_setting('app.current_user', true), '')), '');
    v_origem     := current_setting('app.origin', true);
    v_session_id := NULLIF(current_setting('app.session_id', true), '');

    -- Cast seguro de current_user_id: se valor invalido, mantem NULL sem quebrar
    BEGIN
        v_usuario_id := NULLIF(current_setting('app.current_user_id', true), '')::INTEGER;
    EXCEPTION WHEN OTHERS THEN
        v_usuario_id := NULL;
    END;

    -- ========================================
    -- 5. Inserir evento (com LEFT para prevenir truncation)
    -- ========================================
    INSERT INTO evento_supply_chain (
        tipo_evento, entidade, entidade_id,
        num_pedido, cod_produto, numero_nf, separacao_lote_id,
        quantidade_anterior, quantidade_nova,
        dados_antes, dados_depois, campos_alterados,
        origem, session_id, registrado_por, usuario_id
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
        LEFT(COALESCE(v_usuario, 'SISTEMA'), 100),
        v_usuario_id
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;

EXCEPTION
    WHEN undefined_table THEN
        RAISE LOG '[AUDIT_SC] Tabela evento_supply_chain inexistente — migration pendente';
        IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    WHEN OTHERS THEN
        RAISE WARNING '[AUDIT_SC] Erro no trigger % (% on %): % (SQLSTATE: %)',
            TG_NAME, TG_OP, TG_TABLE_NAME, SQLERRM, SQLSTATE;
        IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- 3. VERIFICACAO
-- ============================================================================
DO $$
DECLARE
    v_col_exists BOOLEAN;
    v_idx_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'evento_supply_chain' AND column_name = 'usuario_id'
    ) INTO v_col_exists;

    SELECT EXISTS (
        SELECT FROM pg_indexes
        WHERE tablename = 'evento_supply_chain' AND indexname = 'idx_esc_usuario_id'
    ) INTO v_idx_exists;

    IF v_col_exists THEN
        RAISE NOTICE '[OK] Coluna usuario_id presente em evento_supply_chain';
    ELSE
        RAISE WARNING '[ERRO] Coluna usuario_id NAO encontrada';
    END IF;

    IF v_idx_exists THEN
        RAISE NOTICE '[OK] Indice idx_esc_usuario_id criado';
    ELSE
        RAISE WARNING '[ERRO] Indice idx_esc_usuario_id NAO encontrado';
    END IF;

    RAISE NOTICE '[OK] Funcao audit_supply_chain_trigger() atualizada (mantem 6 triggers existentes)';
END $$;
