-- Migration: Migrar status de ocorrencia_devolucao para novo modelo auto-computado
-- ============================================================================
-- Status antigos: ABERTA, EM_ANALISE, AGUARDANDO_RETORNO, RETORNADA, RESOLVIDA, CANCELADA
-- Status novos: PENDENTE, EM_ANDAMENTO, RESOLVIDO
--
-- NOTA: Esta versao SQL e um mapeamento simplificado.
-- A versao Python (migrar_status_ocorrencia_devolucao.py) usa calcular_status()
-- que e mais precisa pois avalia os 7 campos comerciais individualmente.
-- Executar preferencialmente a versao Python.
--
-- Criado em: 22/03/2026

-- Mapeamento direto:
-- ABERTA, CANCELADA -> PENDENTE (campos provavelmente incompletos)
-- EM_ANALISE, AGUARDANDO_RETORNO, RETORNADA -> EM_ANDAMENTO (campos em preenchimento)
-- RESOLVIDA -> RESOLVIDO

DO $$
DECLARE
    migrados INTEGER;
BEGIN
    -- Mapear status antigos para novos
    UPDATE ocorrencia_devolucao
    SET status = CASE
        WHEN status IN ('ABERTA', 'CANCELADA') THEN 'PENDENTE'
        WHEN status IN ('EM_ANALISE', 'AGUARDANDO_RETORNO', 'RETORNADA') THEN 'EM_ANDAMENTO'
        WHEN status = 'RESOLVIDA' THEN 'RESOLVIDO'
        ELSE status  -- Manter se ja esta no formato novo
    END
    WHERE status NOT IN ('PENDENTE', 'EM_ANDAMENTO', 'RESOLVIDO')
      AND ativo = TRUE;

    GET DIAGNOSTICS migrados = ROW_COUNT;

    RAISE NOTICE 'Migrados % registros de status antigo para novo formato', migrados;
END
$$;

-- Verificar resultado
SELECT status, COUNT(*) as total
FROM ocorrencia_devolucao
WHERE ativo = TRUE
GROUP BY status
ORDER BY status;
