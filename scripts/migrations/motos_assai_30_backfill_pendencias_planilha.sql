-- Migration 30: backfill de eventos a partir da planilha "backfill pendencias.xlsx"
-- Data origem: 2026-05-17 (Rafael)
-- Operador: Claude Code (id=74, administrador, claude@local.com) — usuario ja existente
--
-- Dois blocos:
--   BLOCO 1 — DISPONIVEL backfill (5 chassis SOL, planilha=DISPONIVEL, banco=PENDENTE):
--     PENDENTE -> PENDENCIA_RESOLVIDA -> MONTADA -> DISPONIVEL (3 eventos x 5 = 15)
--
--   BLOCO 2 — PENDENTE backfill (3 chassis DOT PRETO, planilha=PENDENTE, banco=DISPONIVEL):
--     DISPONIVEL -> REVERTIDA_PARA_MONTADA -> PENDENTE (PLACA) (2 eventos x 3 = 6)
--
-- Total esperado: 21 eventos.
--
-- NAO TOCA:
--   - 126 chassis ja sincronizados
--   - 11 chassis planilha=FATURADAS, banco=PENDENTE (aguardar import NF Q.P.A. real)
--
-- Idempotente: tag em dados_extras impede re-insercao.
-- Tudo dentro de transacao para rollback em caso de erro.

BEGIN;

-- =====================================================
-- Validar usuario Claude Code (id=74) existe
-- =====================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM usuarios WHERE id = 74 AND nome = 'Claude Code') THEN
        RAISE EXCEPTION 'Usuario Claude Code (id=74) nao encontrado. Verifique antes de prosseguir.';
    END IF;
END $$;

-- =====================================================
-- BLOCO 1 — DISPONIVEL backfill
--   PENDENTE -> PENDENCIA_RESOLVIDA -> MONTADA -> DISPONIVEL
-- =====================================================
WITH chassis_alvo (chassi) AS (
    VALUES
        ('172922504673431'),
        ('172922504672472'),
        ('172922504672396'),
        ('172922504672366'),
        ('172922512170018')
),
base_ts AS (
    SELECT (NOW() AT TIME ZONE 'America/Sao_Paulo')::timestamp AS ts
),
elegivel AS (
    -- Pre-check: so processa quem ainda esta em PENDENTE (ultimo evento)
    SELECT ca.chassi
    FROM chassis_alvo ca
    JOIN LATERAL (
        SELECT tipo
        FROM assai_moto_evento e
        WHERE e.chassi = ca.chassi
        ORDER BY e.ocorrido_em DESC, e.id DESC
        LIMIT 1
    ) ultimo ON ultimo.tipo = 'PENDENTE'
),
eventos_a_inserir AS (
    SELECT
        e.chassi,
        v.tipo,
        (b.ts + (v.offset_s || ' seconds')::interval) AS ocorrido_em,
        v.observacao
    FROM elegivel e
    CROSS JOIN base_ts b
    CROSS JOIN (VALUES
        (0, 'PENDENCIA_RESOLVIDA', 'Backfill 2026-05-17: pendencia resolvida fora do sistema (planilha)'),
        (1, 'MONTADA',             'Backfill 2026-05-17: montagem registrada via planilha'),
        (2, 'DISPONIVEL',          'Backfill 2026-05-17: disponibilizada manualmente via planilha')
    ) AS v(offset_s, tipo, observacao)
)
INSERT INTO assai_moto_evento (chassi, tipo, ocorrido_em, operador_id, observacao, dados_extras)
SELECT
    ev.chassi, ev.tipo, ev.ocorrido_em, 74, ev.observacao,
    jsonb_build_object(
        'origem',      'backfill_planilha_2026_05_17',
        'arquivo',     'backfill pendencias.xlsx',
        'solicitante', 'Rafael',
        'bloco',       'disponivel'
    )
FROM eventos_a_inserir ev
WHERE NOT EXISTS (
    SELECT 1 FROM assai_moto_evento e2
    WHERE e2.chassi = ev.chassi
      AND e2.tipo = ev.tipo
      AND (e2.dados_extras->>'origem') = 'backfill_planilha_2026_05_17'
      AND (e2.dados_extras->>'bloco')  = 'disponivel'
);

-- =====================================================
-- BLOCO 2 — PENDENTE backfill
--   DISPONIVEL -> REVERTIDA_PARA_MONTADA -> PENDENTE (PLACA)
-- =====================================================
WITH chassis_alvo (chassi) AS (
    VALUES
        ('LA2025SA110004615'),
        ('LA2025SA110004682'),
        ('LA2025SA110009008')
),
base_ts AS (
    SELECT (NOW() AT TIME ZONE 'America/Sao_Paulo')::timestamp + INTERVAL '10 seconds' AS ts
),
elegivel AS (
    -- Pre-check: so processa quem ainda esta em DISPONIVEL (ultimo evento)
    SELECT ca.chassi
    FROM chassis_alvo ca
    JOIN LATERAL (
        SELECT tipo
        FROM assai_moto_evento e
        WHERE e.chassi = ca.chassi
        ORDER BY e.ocorrido_em DESC, e.id DESC
        LIMIT 1
    ) ultimo ON ultimo.tipo = 'DISPONIVEL'
),
eventos_a_inserir AS (
    SELECT
        e.chassi,
        v.tipo,
        (b.ts + (v.offset_s || ' seconds')::interval) AS ocorrido_em,
        v.observacao
    FROM elegivel e
    CROSS JOIN base_ts b
    CROSS JOIN (VALUES
        (0, 'REVERTIDA_PARA_MONTADA', 'PLACA — reverter DISPONIVEL para registrar pendencia conforme planilha 2026-05-17'),
        (1, 'PENDENTE',               'PLACA')
    ) AS v(offset_s, tipo, observacao)
)
INSERT INTO assai_moto_evento (chassi, tipo, ocorrido_em, operador_id, observacao, dados_extras)
SELECT
    ev.chassi, ev.tipo, ev.ocorrido_em, 74, ev.observacao,
    jsonb_build_object(
        'origem',      'backfill_planilha_2026_05_17',
        'arquivo',     'backfill pendencias.xlsx',
        'solicitante', 'Rafael',
        'bloco',       'pendente',
        'motivo',      'PLACA'
    )
FROM eventos_a_inserir ev
WHERE NOT EXISTS (
    SELECT 1 FROM assai_moto_evento e2
    WHERE e2.chassi = ev.chassi
      AND e2.tipo = ev.tipo
      AND (e2.dados_extras->>'origem') = 'backfill_planilha_2026_05_17'
      AND (e2.dados_extras->>'bloco')  = 'pendente'
);

-- =====================================================
-- Verificacao
-- =====================================================
SELECT
    chassi,
    string_agg(tipo, ' -> ' ORDER BY ocorrido_em, id) AS sequencia_completa
FROM assai_moto_evento
WHERE chassi IN (
    -- bloco 1
    '172922504673431','172922504672472','172922504672396','172922504672366','172922512170018',
    -- bloco 2
    'LA2025SA110004615','LA2025SA110004682','LA2025SA110009008'
)
GROUP BY chassi
ORDER BY chassi;

SELECT
    e.chassi,
    e.tipo AS status_efetivo,
    e.ocorrido_em
FROM assai_moto_evento e
WHERE e.chassi IN (
    '172922504673431','172922504672472','172922504672396','172922504672366','172922512170018',
    'LA2025SA110004615','LA2025SA110004682','LA2025SA110009008'
)
  AND e.id = (
      SELECT id FROM assai_moto_evento e2
      WHERE e2.chassi = e.chassi
      ORDER BY ocorrido_em DESC, id DESC
      LIMIT 1
  )
ORDER BY e.chassi;

COMMIT;
