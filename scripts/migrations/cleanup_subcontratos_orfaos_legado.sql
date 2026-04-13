-- =============================================================================
-- cleanup_subcontratos_orfaos_legado.sql
-- =============================================================================
-- Remove CTes Subcontrato orfaos do fluxo legado (pre-CarviaFrete).
--
-- USO RECOMENDADO:
--   Prefira o script Python equivalente, que chama
--   AdminService.excluir_subcontrato_orfao() por sub — dessa forma cada
--   exclusao gera CarviaAdminAudit individual com snapshot completo dos
--   relacionados (movs CC, aprovacoes, compensacoes revertidas).
--
--   Este SQL e um "botao vermelho" para uso direto no Render Shell quando
--   a app nao esta acessivel. NAO gera registro por-sub em
--   CarviaAdminAudit — insere apenas UM registro agregado BULK_CLEANUP.
--
-- Criterio de orfao:
--   frete_id IS NULL
--   AND fatura_transportadora_id IS NULL
--   AND status NOT IN ('FATURADO', 'CONFERIDO')
--   AND sem referencias em FaturaTransportadoraItem, CustoEntrega, Frete (legado)
--   AND sem CarviaConciliacao(tipo_documento='subcontrato', documento_id=sub.id)
--
-- O criterio garante que o sub esta TOTALMENTE desconectado do extrato bancario:
-- 1) Sem fatura_transportadora_id -> nenhuma conciliacao 'fatura_transportadora'
-- 2) Sem CustoEntrega.subcontrato_id -> nenhuma conciliacao 'custo_entrega' indireta
-- 3) Sem CarviaConciliacao 'subcontrato' historica
--
-- Seguro porque:
--   1. CTE filtra candidatos primeiro (incluindo guard de conciliacao)
--   2. Tudo roda em BEGIN/COMMIT
--   3. Desconciliacao de extrato (defensivo): remove qualquer
--      CarviaConciliacao residual + CarviaContaMovimentacao com
--      tipo_documento/tipo_doc='subcontrato' + recalcula extrato_linha
--   4. Movs CC sao deletadas antes (FK NOT NULL)
--   5. Compensacoes apontando para os orfaos sao revertidas para ATIVO
--   6. Aprovacoes sao deletadas
--   7. Snapshot agregado em CarviaAdminAudit antes de deletar
--   8. Totalmente idempotente — rodar 2x nao faz nada se ja executado
--
-- Para rodar no Render Shell:
--   psql $DATABASE_URL -f cleanup_subcontratos_orfaos_legado.sql
-- =============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Identificar candidatos em TEMP TABLE (fonte unica durante a transacao)
-- ----------------------------------------------------------------------------
CREATE TEMP TABLE tmp_orfaos ON COMMIT DROP AS
SELECT s.id
FROM carvia_subcontratos s
WHERE s.frete_id IS NULL
  AND s.fatura_transportadora_id IS NULL
  AND s.status NOT IN ('FATURADO', 'CONFERIDO')
  AND NOT EXISTS (SELECT 1 FROM carvia_fatura_transportadora_itens i WHERE i.subcontrato_id = s.id)
  AND NOT EXISTS (SELECT 1 FROM carvia_custos_entrega ce WHERE ce.subcontrato_id = s.id)
  AND NOT EXISTS (SELECT 1 FROM carvia_fretes f WHERE f.subcontrato_id = s.id)
  -- Defesa em profundidade: sem conciliacao historica direta com extrato
  AND NOT EXISTS (
      SELECT 1 FROM carvia_conciliacoes c
      WHERE c.tipo_documento = 'subcontrato' AND c.documento_id = s.id
  )
  -- Defesa em profundidade: sem mov CC vinculada a Fatura (historico financeiro
  -- de fatura que pode estar conciliada com extrato)
  AND NOT EXISTS (
      SELECT 1 FROM carvia_conta_corrente_transportadoras cc
      WHERE cc.subcontrato_id = s.id
        AND cc.fatura_transportadora_id IS NOT NULL
  );

-- Report
SELECT COUNT(*) AS qtd_orfaos_encontrados FROM tmp_orfaos;

-- ----------------------------------------------------------------------------
-- 2. Snapshot agregado em CarviaAdminAudit (UM registro descrevendo o lote)
--    Executado ANTES dos deletes para preservar dados em JSONB.
-- ----------------------------------------------------------------------------
INSERT INTO carvia_admin_audit (
    acao,
    entidade_tipo,
    entidade_id,
    dados_snapshot,
    dados_relacionados,
    motivo,
    executado_por,
    executado_em,
    detalhes
)
SELECT
    'BULK_CLEANUP',
    'CarviaSubcontrato',
    0,  -- 0 sinaliza operacao em lote (nao aponta 1 entidade)
    jsonb_build_object(
        'subcontratos',
        (SELECT COALESCE(jsonb_agg(row_to_json(s.*)), '[]'::jsonb)
         FROM carvia_subcontratos s
         WHERE s.id IN (SELECT id FROM tmp_orfaos))
    ),
    jsonb_build_object(
        'conciliacoes_extrato',
        (SELECT COALESCE(jsonb_agg(row_to_json(c.*)), '[]'::jsonb)
         FROM carvia_conciliacoes c
         WHERE c.tipo_documento = 'subcontrato'
           AND c.documento_id IN (SELECT id FROM tmp_orfaos)),
        'movimentacoes_financeiras',
        (SELECT COALESCE(jsonb_agg(row_to_json(m.*)), '[]'::jsonb)
         FROM carvia_conta_movimentacoes m
         WHERE m.tipo_doc = 'subcontrato'
           AND m.doc_id IN (SELECT id FROM tmp_orfaos)),
        'movimentacoes_cc',
        (SELECT COALESCE(jsonb_agg(row_to_json(cc.*)), '[]'::jsonb)
         FROM carvia_conta_corrente_transportadoras cc
         WHERE cc.subcontrato_id IN (SELECT id FROM tmp_orfaos)),
        'aprovacoes',
        (SELECT COALESCE(jsonb_agg(row_to_json(a.*)), '[]'::jsonb)
         FROM carvia_aprovacoes_subcontrato a
         WHERE a.subcontrato_id IN (SELECT id FROM tmp_orfaos)),
        'compensacoes_revertidas',
        (SELECT COALESCE(jsonb_agg(row_to_json(cc2.*)), '[]'::jsonb)
         FROM carvia_conta_corrente_transportadoras cc2
         WHERE cc2.compensacao_subcontrato_id IN (SELECT id FROM tmp_orfaos)
           AND cc2.status = 'COMPENSADO')
    ),
    'Bulk cleanup via SQL: CTes Subcontrato orfaos do fluxo legado pre-CarviaFrete',
    'script:cleanup_subcontratos_orfaos_legado.sql',
    NOW() AT TIME ZONE 'UTC',
    jsonb_build_object(
        'origem', 'orfao_legado_pre_carviafrete',
        'qtd_orfaos', (SELECT COUNT(*) FROM tmp_orfaos),
        'sub_ids', (SELECT COALESCE(jsonb_agg(id), '[]'::jsonb) FROM tmp_orfaos)
    )
WHERE EXISTS (SELECT 1 FROM tmp_orfaos);

-- ----------------------------------------------------------------------------
-- 3a. DESCONCILIACAO DE EXTRATO (defensivo)
--     Captura linhas de extrato afetadas para recalcular APOS o delete.
--     Mesmo que tmp_orfaos exclua candidatos com conciliacao 'subcontrato',
--     limpamos para garantir idempotencia (rodar 2x = 0 conciliacoes).
-- ----------------------------------------------------------------------------
CREATE TEMP TABLE tmp_extrato_afetadas ON COMMIT DROP AS
SELECT DISTINCT extrato_linha_id
FROM carvia_conciliacoes
WHERE tipo_documento = 'subcontrato'
  AND documento_id IN (SELECT id FROM tmp_orfaos);

DELETE FROM carvia_conciliacoes
WHERE tipo_documento = 'subcontrato'
  AND documento_id IN (SELECT id FROM tmp_orfaos);

-- Limpa CarviaContaMovimentacao com tipo_doc='subcontrato' (caso historico)
DELETE FROM carvia_conta_movimentacoes
WHERE tipo_doc = 'subcontrato'
  AND doc_id IN (SELECT id FROM tmp_orfaos);

-- Recalcula total_conciliado e status_conciliacao das linhas de extrato
-- afetadas (espelha _limpar_movimentacao_financeira do AdminService Python)
UPDATE carvia_extrato_linhas el
SET
    total_conciliado = sub.total,
    status_conciliacao = CASE
        WHEN sub.total >= ABS(COALESCE(el.valor, 0)) THEN 'CONCILIADO'
        WHEN sub.total > 0 THEN 'PARCIAL'
        ELSE 'PENDENTE'
    END
FROM (
    SELECT
        ext.id AS extrato_id,
        COALESCE((
            SELECT SUM(c.valor_alocado)
            FROM carvia_conciliacoes c
            WHERE c.extrato_linha_id = ext.id
        ), 0) AS total
    FROM carvia_extrato_linhas ext
    WHERE ext.id IN (SELECT extrato_linha_id FROM tmp_extrato_afetadas)
) sub
WHERE el.id = sub.extrato_id;

-- ----------------------------------------------------------------------------
-- 3b. Reverter compensacoes apontando para orfaos
--    (outro sub foi "compensado" por um dos orfaos — volta para ATIVO)
-- ----------------------------------------------------------------------------
UPDATE carvia_conta_corrente_transportadoras
SET
    status = 'ATIVO',
    compensado_em = NULL,
    compensado_por = NULL,
    compensacao_subcontrato_id = NULL,
    observacoes = COALESCE(observacoes, '')
        || E'\n[AUTO ' || (NOW() AT TIME ZONE 'UTC')::text
        || '] Compensacao revertida: sub compensador (orfao legado) excluido via bulk SQL.'
WHERE compensacao_subcontrato_id IN (SELECT id FROM tmp_orfaos)
  AND status = 'COMPENSADO';

-- ----------------------------------------------------------------------------
-- 4. Delete movs CC apontando para os orfaos (FK NOT NULL exige antes do sub)
-- ----------------------------------------------------------------------------
DELETE FROM carvia_conta_corrente_transportadoras
WHERE subcontrato_id IN (SELECT id FROM tmp_orfaos);

-- ----------------------------------------------------------------------------
-- 5. Delete aprovacoes apontando para os orfaos
-- ----------------------------------------------------------------------------
DELETE FROM carvia_aprovacoes_subcontrato
WHERE subcontrato_id IN (SELECT id FROM tmp_orfaos);

-- ----------------------------------------------------------------------------
-- 6. CarviaCustoEntrega.subcontrato_id: FK tem ondelete='SET NULL', mas
--    garantimos explicito para evitar qualquer ambiguidade e aparecer no log.
--    (OBS: o WHERE do tmp_orfaos ja excluiu orfaos com CE vinculado — este
--    UPDATE eh belt-and-suspenders)
-- ----------------------------------------------------------------------------
UPDATE carvia_custos_entrega
SET subcontrato_id = NULL
WHERE subcontrato_id IN (SELECT id FROM tmp_orfaos);

-- ----------------------------------------------------------------------------
-- 7. Delete final dos subcontratos orfaos
-- ----------------------------------------------------------------------------
DELETE FROM carvia_subcontratos
WHERE id IN (SELECT id FROM tmp_orfaos);

-- ----------------------------------------------------------------------------
-- 8. Report final
-- ----------------------------------------------------------------------------
SELECT
    (SELECT COUNT(*) FROM carvia_subcontratos) AS total_subcontratos_restantes,
    (SELECT COUNT(*) FROM carvia_subcontratos
       WHERE frete_id IS NULL
         AND fatura_transportadora_id IS NULL
         AND status NOT IN ('FATURADO', 'CONFERIDO')) AS orfaos_restantes;

COMMIT;
