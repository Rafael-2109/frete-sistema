-- ============================================================================
-- TRIGGER: Atualizar totais do embarque automaticamente
-- ============================================================================
-- ✅ OBJETIVO:
--    Garantir que embarque.pallet_total, embarque.peso_total e embarque.valor_total
--    estejam sempre sincronizados com a soma dos EmbarqueItem ativos
--
-- ✅ QUANDO EXECUTA:
--    - Após INSERT em embarque_itens
--    - Após UPDATE em embarque_itens (pallets, peso, valor ou status)
--    - Após DELETE em embarque_itens
--
-- 📋 COMO EXECUTAR NO RENDER:
--    Copie todo o conteúdo deste arquivo e cole no Shell SQL do Render
-- ============================================================================

-- 1. Criar função trigger
CREATE OR REPLACE FUNCTION atualizar_totais_embarque()
RETURNS TRIGGER AS $$
DECLARE
    v_embarque_id INTEGER;
BEGIN
    -- Determina qual embarque_id atualizar
    IF (TG_OP = 'DELETE') THEN
        v_embarque_id := OLD.embarque_id;
    ELSE
        v_embarque_id := NEW.embarque_id;
    END IF;

    -- Atualiza totais do embarque com base nos itens ATIVOS
    UPDATE embarques
    SET
        pallet_total = (
            SELECT COALESCE(SUM(pallets), 0)
            FROM embarque_itens
            WHERE embarque_id = v_embarque_id
            AND status = 'ativo'
        ),
        peso_total = (
            SELECT COALESCE(SUM(peso), 0)
            FROM embarque_itens
            WHERE embarque_id = v_embarque_id
            AND status = 'ativo'
        ),
        valor_total = (
            SELECT COALESCE(SUM(valor), 0)
            FROM embarque_itens
            WHERE embarque_id = v_embarque_id
            AND status = 'ativo'
        )
    WHERE id = v_embarque_id;

    -- Log para debug
    RAISE NOTICE 'Totais do embarque % atualizados via trigger', v_embarque_id;

    RETURN NULL; -- Para trigger AFTER, o retorno é ignorado
END;
$$ LANGUAGE plpgsql;

-- 2. Remover trigger antigo se existir
DROP TRIGGER IF EXISTS trigger_atualizar_totais_embarque ON embarque_itens;

-- 3. Criar novo trigger
CREATE TRIGGER trigger_atualizar_totais_embarque
AFTER INSERT OR UPDATE OR DELETE ON embarque_itens
FOR EACH ROW
EXECUTE FUNCTION atualizar_totais_embarque();

-- 4. Verificar se foi criado
SELECT
    tgname AS trigger_name,
    tgtype AS trigger_type,
    tgenabled AS enabled
FROM pg_trigger
WHERE tgname = 'trigger_atualizar_totais_embarque';

-- ============================================================================
-- ✅ TRIGGER CRIADO COM SUCESSO!
-- ============================================================================
-- 📋 COMPORTAMENTO:
--   - Ao inserir EmbarqueItem: Recalcula totais do embarque
--   - Ao atualizar EmbarqueItem: Recalcula totais do embarque
--   - Ao deletar EmbarqueItem: Recalcula totais do embarque
--   - Considera APENAS itens com status='ativo'
--
-- 💡 CAMPOS ATUALIZADOS AUTOMATICAMENTE:
--   - embarque.pallet_total
--   - embarque.peso_total
--   - embarque.valor_total
--
-- 🔍 TESTE O TRIGGER:
--   UPDATE embarque_itens SET pallets = 5.0 WHERE id = 12345;
--   SELECT pallet_total FROM embarques WHERE id = 2316;
-- ============================================================================
