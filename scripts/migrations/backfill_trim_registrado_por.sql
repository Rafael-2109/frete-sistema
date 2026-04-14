-- ============================================================================
-- BACKFILL: Trim de registrado_por em evento_supply_chain
-- ============================================================================
-- Problema: usuarios.nome foi cadastrado com trailing spaces e typos
-- (ex: "Marcps Roberto Lehmann Prudencio ", "Stephanie Macena Rodrigues Chaves ").
-- O trigger antigo copiava literalmente, resultando em registrado_por inconsistente.
--
-- Este backfill aplica TRIM() apenas nos eventos ja existentes afetados.
-- Para novos eventos, o trigger ja faz TRIM defensivo via
-- add_usuario_id_evento_supply_chain.sql.
--
-- NAO altera usuarios.nome (decisao do usuario: evitar quebrar outras telas
-- que fazem match por string).
--
-- Idempotente: apos primeira execucao, WHERE clause nao encontra mais linhas.
-- Data: 2026-04-14
-- ============================================================================

-- Contagem BEFORE
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT count(*) INTO v_count
    FROM evento_supply_chain
    WHERE registrado_por IS NOT NULL AND registrado_por != TRIM(registrado_por);
    RAISE NOTICE '[BEFORE] Eventos com whitespace em registrado_por: %', v_count;
END $$;

-- Backfill TRIM
UPDATE evento_supply_chain
SET registrado_por = TRIM(registrado_por)
WHERE registrado_por IS NOT NULL
  AND registrado_por != TRIM(registrado_por);

-- Contagem AFTER
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT count(*) INTO v_count
    FROM evento_supply_chain
    WHERE registrado_por IS NOT NULL AND registrado_por != TRIM(registrado_por);
    RAISE NOTICE '[AFTER] Eventos com whitespace restante: %', v_count;

    IF v_count = 0 THEN
        RAISE NOTICE '[OK] Backfill concluido — todos eventos com registrado_por trimado';
    ELSE
        RAISE WARNING '[AVISO] % eventos ainda com whitespace (investigar)', v_count;
    END IF;
END $$;
