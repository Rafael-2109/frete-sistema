-- ============================================================================
-- BACKFILL: Session_id proxy para eventos origem=USUARIO
-- ============================================================================
-- Problema: eventos origem=USUARIO historicos (antes do deploy 2026-04-14)
-- tem session_id NULL porque context_middleware.py:58 zerava deliberadamente.
-- Impacto: impossivel correlacionar operacoes cross-entidade feitas por usuarios.
--
-- Solucao: atribuir session_id PROXY TEMPORAL baseado em:
--   USUARIO_{YYYYMMDDHHMI}_{usuario_id OU hash de registrado_por}
--
-- Agrupa eventos do mesmo usuario na mesma JANELA DE 1 MINUTO em um mesmo
-- session_id. Nao e o session_id real do request original (impossivel de
-- reconstruir), mas e suficiente para:
--   - Detectar operacoes batch ("usuario X alterou 50 linhas em 1 clique")
--   - Correlacionar mudancas cross-entidade da mesma transacao
--   - ML de padroes de uso
--
-- Idempotente: WHERE session_id IS NULL limita a primeira execucao.
-- Apos o deploy da correcao, novos eventos USUARIO vem com session_id
-- gerado por set_pg_audit_context() — este backfill so afeta historicos.
--
-- Data: 2026-04-14
-- ============================================================================

-- Contagem BEFORE
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT count(*) INTO v_count
    FROM evento_supply_chain
    WHERE session_id IS NULL AND origem = 'USUARIO';
    RAISE NOTICE '[BEFORE] Eventos USUARIO sem session_id: %', v_count;
END $$;

-- Backfill: proxy temporal
-- Formato: USUARIO_YYYYMMDDHHMI_<registrado_por normalizado>
-- LEFT 100 chars para respeitar VARCHAR(100) do schema.
UPDATE evento_supply_chain
SET session_id = LEFT(
    'USUARIO_' ||
    to_char(date_trunc('minute', registrado_em), 'YYYYMMDDHH24MI') ||
    '_' ||
    COALESCE(regexp_replace(TRIM(registrado_por), '[^a-zA-Z0-9]', '', 'g'), 'ANON'),
    100
)
WHERE session_id IS NULL
  AND origem = 'USUARIO';

-- Contagem AFTER
DO $$
DECLARE
    v_nulos     INTEGER;
    v_sessoes   INTEGER;
BEGIN
    SELECT count(*) INTO v_nulos
    FROM evento_supply_chain
    WHERE session_id IS NULL AND origem = 'USUARIO';

    SELECT count(DISTINCT session_id) INTO v_sessoes
    FROM evento_supply_chain
    WHERE session_id LIKE 'USUARIO_%';

    RAISE NOTICE '[AFTER] Eventos USUARIO sem session_id: %', v_nulos;
    RAISE NOTICE '[OK] Sessoes USUARIO geradas: %', v_sessoes;

    IF v_nulos = 0 THEN
        RAISE NOTICE '[OK] Backfill concluido';
    ELSE
        RAISE WARNING '[AVISO] % eventos USUARIO ainda sem session_id', v_nulos;
    END IF;
END $$;
