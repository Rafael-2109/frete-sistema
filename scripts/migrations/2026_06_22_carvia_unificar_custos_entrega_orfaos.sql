-- Migration de DADOS (one-shot, idempotente): unifica Custos de Entrega CarVia
-- duplicados. Em 19/05 a usuaria thalita criou 5 custos pela tela "por frete";
-- como os fretes 65/67/68 ainda tinham operacao_id=NULL (backfill frete->operacao
-- so' rodou em 22/06), esses custos nasceram ORFAOS de operacao (sem NF/Tomador/
-- Destino/CTE na tela). Em 22/06 foram RECRIADOS (ids 78-82) com operacao+fornecedor,
-- gerando duplicatas. Os ANTIGOS (54-58) carregam o vinculo financeiro IRREVERSIVEL
-- (FT 63 PAGA+conciliada; FT 64 CONFERIDA, soma 711,53 = valor_total) -> SOBREVIVEM
-- e recebem operacao+fornecedor; os NOVOS sao deletados.
--
-- Pares (antigo<-novo): 54<-79 (frete65/DISTRIMAX/op200), 57<-78 (frete67/VITALY/op199),
-- 55<-81, 58<-80, 56<-82 (frete68/NAOMI ROYAL/op198).
-- Caso 77 (CTe Comp, op213 sem frete): re-vincula do CTe Comp 30 (CANCELADO, deu erro)
-- para o 31 (EMITIDO, CTe 478) e amarra a emissao de sucesso (id 23, hoje orfa).
--
-- Decisoes do usuario (22/06): tipo do custo R$60 = TAXA_DESCARGA (mantido); duplicados = DELETE.
-- Idempotente: UPDATEs guardados por estado-origem; DELETE por id + trava financeira.

-- 1) Migrar anexos dos duplicados novos para os antigos sobreviventes (ANTES do delete)
UPDATE carvia_custo_entrega_anexos SET custo_entrega_id = 57 WHERE custo_entrega_id = 78;
UPDATE carvia_custo_entrega_anexos SET custo_entrega_id = 54 WHERE custo_entrega_id = 79;

-- 2) Enriquecer custos antigos (que carregam o vinculo de FT) com operacao + fornecedor.
--    Guard `operacao_id IS NULL` => no-op apos a 1a aplicacao.
UPDATE carvia_custos_entrega
   SET operacao_id = 200,
       fornecedor_nome = 'DISTRIMAX LTDA',
       fornecedor_cnpj = '39392246000191'
 WHERE id = 54 AND operacao_id IS NULL;

UPDATE carvia_custos_entrega
   SET operacao_id = 199,
       fornecedor_nome = 'VITALY DISTRIBUIDORA DE PRODUTOS HOSPITALARES, ALIMENTOS E COSMETICOS LTDA',
       fornecedor_cnpj = '38221229000129'
 WHERE id = 57 AND operacao_id IS NULL;

UPDATE carvia_custos_entrega
   SET operacao_id = 198,
       fornecedor_nome = 'NAOMI COMERCIO DE ALIMENTOS LT ROYAL',
       fornecedor_cnpj = '39553144001425'
 WHERE id IN (55, 56, 58) AND operacao_id IS NULL;

-- 3) Custo 77: re-vincular do CTe Comp 30 (CANCELADO) para o 31 (EMITIDO)
--    + amarrar a emissao de SUCESSO (id 23) que hoje esta sem custo_entrega_id.
UPDATE carvia_custos_entrega
   SET cte_complementar_id = 31
 WHERE id = 77 AND cte_complementar_id = 30;

UPDATE carvia_emissao_cte_complementar
   SET custo_entrega_id = 77
 WHERE id = 23 AND custo_entrega_id IS NULL AND cte_complementar_id = 31;

-- 4) Deletar os 5 duplicados novos. Trava financeira: nunca apaga custo com FT/conciliacao.
DELETE FROM carvia_custos_entrega
 WHERE id IN (78, 79, 80, 81, 82)
   AND fatura_transportadora_id IS NULL
   AND conciliado = false
   AND COALESCE(total_conciliado, 0) = 0;
