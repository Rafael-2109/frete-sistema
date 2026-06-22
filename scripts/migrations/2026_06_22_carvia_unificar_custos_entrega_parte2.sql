-- Migration de DADOS (one-shot, idempotente) PARTE 2: unifica Custos de Entrega
-- CarVia duplicados onde AMBOS os lados ja tem vinculo financeiro fechado.
--
-- Diferente da Parte 1: aqui o lado RAFAEL (ids 1, 7, criados em abril) carrega o
-- CTe Complementar FATURADO (cobranca ao cliente) + emissao SSW + a operacao CORRETA
-- e status PAGO. O lado THALITA (ids 52, 53, criados em 19/05 ao conferir a FT 51)
-- so' tem a Fatura Transportadora 51 (PAGA, transportadora 128) e nada mais (sem
-- cte_comp/emissao/anexo); alem disso o 53 esta na operacao/frete ERRADOS (op 9/frete
-- 135 em vez de op 21/frete 115 = NF 48690).
--
-- Estrategia: MANTER 1 e 7 (mais vinculos + operacao correta) e TRANSFERIR o vinculo
-- de FT do lado Thalita para eles; depois deletar 52 e 53. A FT 51 mantem o valor
-- (50+130=180): so' troca quais custos a compoem (ambos da mesma transportadora 128).
-- Tambem reclassifica o custo 21 (GNRE lancada como OUTROS) -> GNRE_ICMS.
--
-- Idempotente: UPDATEs guardados por estado-origem; DELETE so' apos a FT ter sido movida.

-- 1) Par 1 <- 52 (op 9, R$50, descarga): move FT 51 + frete 135 para o custo 1.
UPDATE carvia_custos_entrega
   SET fatura_transportadora_id = 51, frete_id = 135
 WHERE id = 1 AND fatura_transportadora_id IS NULL;

-- 2) Par 7 <- 53 (op 21, R$130, descarga): move FT 51 + frete 115 (NF 48690) para o
--    custo 7. O 7 ja esta na operacao 21 CORRETA -> resolve o "frete errado" do 53.
UPDATE carvia_custos_entrega
   SET fatura_transportadora_id = 51, frete_id = 115
 WHERE id = 7 AND fatura_transportadora_id IS NULL;

-- 3) Reclassificar custo 21: OUTROS -> GNRE_ICMS (mesmo padrao dos demais GNRE).
UPDATE carvia_custos_entrega
   SET tipo_custo = 'GNRE_ICMS'
 WHERE id = 21 AND tipo_custo = 'OUTROS';

-- 4) Deletar as duplicatas 52, 53. Trava dupla: (a) sem conciliacao propria; (b) so'
--    deleta se 1 e 7 JA estao na FT 51 (a FT nao pode perder itens / mudar de total).
DELETE FROM carvia_custos_entrega
 WHERE id IN (52, 53)
   AND conciliado = false
   AND COALESCE(total_conciliado, 0) = 0
   AND (SELECT count(*) FROM carvia_custos_entrega s
          WHERE s.id IN (1, 7) AND s.fatura_transportadora_id = 51) = 2;
