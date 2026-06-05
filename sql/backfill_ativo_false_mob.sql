-- ========================================================================
-- SOFT DELETE: MovimentacaoEstoque indevidas do fluxo Recebimento LF
-- (producao/industrializacao — o controle deve ser SO o lancamento manual PRODUCAO)
--
-- Criterio: data_movimentacao >= 2026-05-18 | tipo_origem='ODOO' | ativo=TRUE
-- Padroes:
--   (A) COMPRA        + observacao LIKE '%Recebimento LF%'          -> 15 registros
--   (B) TRANSFERENCIA + observacao LIKE '%Transfer FB->CD via LF%'  -> 80 registros
--   Universo total: 15 + 80 = 95
-- Salvaguardas: ignora registro vinculado a separacao/embarque/recebimento/
--   pedido_compras/producao-pai/abatido/baixado (validado em PROD: nenhum dos 95 viola).
--
-- ESTADO (verificado em PROD 2026-06-05):
--   - Os 15 COMPRA JA estao ativo=FALSE (execucao anterior 'UPDATE 15').
--   - Os 80 TRANSFERENCIA ainda estao ativo=TRUE (faltam soft-delete).
--   => Rodar este arquivo agora resulta em "UPDATE 80" (idempotente: nao
--      reverte nem retoca os 15 ja desativados, por causa do filtro ativo=TRUE).
--
-- POR QUE A EXECUCAO ANTERIOR PEGOU SO 15:
--   Ao COLAR o UPDATE no terminal interativo (pgcli/psql), a string longa da
--   TRANSFERENCIA quebrou no meio -> 'Transfer\nFB->CD via LF%' (newline literal),
--   que NAO casa com o texto real (que tem espaco). Resultado: 0 TRANSFERENCIA.
--
-- *** COMO EXECUTAR (IMPORTANTE) ***
--   Rode via arquivo, NUNCA cole linha a linha:
--       psql "$DATABASE_URL_PROD" -f sql/backfill_ativo_false_mob.sql
--   (Os literais LIKE estao cada um em UMA linha de proposito — nao quebre.)
-- ========================================================================

-- PASSO 0 — FOTO DO UNIVERSO (deve mostrar COMPRA/FALSE=15 e TRANSFERENCIA/TRUE=80)
SELECT local_movimentacao, ativo, COUNT(*) AS n
FROM movimentacao_estoque
WHERE tipo_origem = 'ODOO'
  AND data_movimentacao >= '2026-05-18'
  AND ( (local_movimentacao = 'COMPRA'        AND observacao LIKE '%Recebimento LF%')
     OR (local_movimentacao = 'TRANSFERENCIA' AND observacao LIKE '%Transfer FB->CD via LF%') )
GROUP BY local_movimentacao, ativo
ORDER BY local_movimentacao, ativo;

-- PASSO 1 — PREVIEW dos que serao tocados agora (deve listar 80 — os TRANSFERENCIA ativos)
SELECT id, cod_produto, data_movimentacao, tipo_movimentacao, local_movimentacao,
       qtd_movimentacao, lote_nome, numero_nf, observacao
FROM movimentacao_estoque
WHERE ativo = TRUE AND tipo_origem = 'ODOO'
  AND data_movimentacao >= '2026-05-18'
  AND ( (local_movimentacao = 'COMPRA'        AND observacao LIKE '%Recebimento LF%')
     OR (local_movimentacao = 'TRANSFERENCIA' AND observacao LIKE '%Transfer FB->CD via LF%') )
  AND separacao_lote_id     IS NULL AND codigo_embarque   IS NULL
  AND recebimento_fisico_id IS NULL AND recebimento_lote_id IS NULL
  AND pedido_compras_id     IS NULL AND producao_pai_id    IS NULL
  AND (qtd_abatida IS NULL OR qtd_abatida = 0)
  AND (baixado IS NULL OR baixado IS FALSE)
ORDER BY data_movimentacao, cod_produto;

-- PASSO 2 — EXECUTA (soft delete). Deve retornar "UPDATE 80"
-- (15 COMPRA ja estavam ativo=FALSE; 15 + 80 = 95 no total acumulado)
UPDATE movimentacao_estoque
SET ativo = FALSE,
    atualizado_em  = (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    atualizado_por = 'soft-delete movs LF indevidas'
WHERE ativo = TRUE AND tipo_origem = 'ODOO'
  AND data_movimentacao >= '2026-05-18'
  AND ( (local_movimentacao = 'COMPRA'        AND observacao LIKE '%Recebimento LF%')
     OR (local_movimentacao = 'TRANSFERENCIA' AND observacao LIKE '%Transfer FB->CD via LF%') )
  AND separacao_lote_id     IS NULL AND codigo_embarque   IS NULL
  AND recebimento_fisico_id IS NULL AND recebimento_lote_id IS NULL
  AND pedido_compras_id     IS NULL AND producao_pai_id    IS NULL
  AND (qtd_abatida IS NULL OR qtd_abatida = 0)
  AND (baixado IS NULL OR baixado IS FALSE);

-- PASSO 3 — POS-CHECK (deve retornar 0)
SELECT COUNT(*) AS restantes
FROM movimentacao_estoque
WHERE ativo = TRUE AND tipo_origem = 'ODOO'
  AND data_movimentacao >= '2026-05-18'
  AND ( (local_movimentacao = 'COMPRA'        AND observacao LIKE '%Recebimento LF%')
     OR (local_movimentacao = 'TRANSFERENCIA' AND observacao LIKE '%Transfer FB->CD via LF%') );
