-- ============================================================================
-- Backfill CarviaFrete + EntregaMonitorada para embarques afetados pelo bug
-- de gatilho ausente no form manual de edicao de embarque.
--
-- Contexto: app/embarques/routes.py nao chamava CarviaFreteService.lancar_frete_carvia
-- nem sincronizar_entrega_carvia_por_nf ao preencher NF em item CarVia via form
-- manual. Fix aplicado em 2026-04-20 (hook CarVia apos loop sync Nacom).
--
-- Embarques afetados (portaria ja deu saida, NF CarVia preenchida via form manual):
--   4584 (NF 36278), 4901 (NF 1652), 4902 (NFs 4819+36879), 4855 (NFs 1->1630, 1->1631)
--
-- Idempotencia: INSERT guardado por NOT EXISTS; UPDATEs filtram por valores-alvo.
-- Rodar em transacao unica.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- PARTE 1: Corrigir NF invalida no embarque 4855 (itens tinham NF='1')
-- Pareamento por CNPJ destinatario + datas coerentes (NF 14/04 -> embarque 15/04)
-- Divergencia de valor (~9%) = IPI/comissao pos-cotacao.
-- ----------------------------------------------------------------------------

UPDATE embarque_itens
SET nota_fiscal = '1630'
WHERE id = 12040 AND nota_fiscal = '1' AND cnpj_cliente = '27032137000184';

UPDATE embarque_itens
SET nota_fiscal = '1631'
WHERE id = 12041 AND nota_fiscal = '1' AND cnpj_cliente = '52922844000193';

-- ----------------------------------------------------------------------------
-- PARTE 2: Criar CarviaFrete para cada (embarque, item CarVia, NF real)
-- Vincula operacao_id + fatura_cliente_id ja existentes.
-- valor_venda = cte_valor da operacao. valor_cotado/considerado ficam 0
-- (sem CarviaSubcontrato criado; esse sera vinculado quando CTe subcontrato
-- for emitido/recebido, como no fluxo normal).
-- ----------------------------------------------------------------------------

WITH backfill_itens AS (
    SELECT * FROM (VALUES
        -- (embarque_id, item_id, numero_nf, operacao_id, fatura_cliente_id, cte_valor)
        (4584, 11248, '36278', 103,  99,  750.00),
        (4901, 12173, '1652',  190, 182,  750.00),
        (4902, 12163, '4819',  187, 180, 4800.00),
        (4902, 12164, '36879', 186, 179, 1200.00),
        (4855, 12040, '1630',  167, 165,  500.00),
        (4855, 12041, '1631',  168, 164, 1200.00)
    ) AS t(embarque_id, item_id, numero_nf, operacao_id, fatura_cliente_id, cte_valor)
)
INSERT INTO carvia_fretes (
    embarque_id, transportadora_id,
    cnpj_emitente, nome_emitente,
    cnpj_destino, nome_destino,
    uf_destino, cidade_destino, tipo_carga,
    peso_total, valor_total_nfs, quantidade_nfs, numeros_nfs,
    valor_cotado, valor_considerado, valor_venda,
    operacao_id, fatura_cliente_id,
    status, status_conferencia, requer_aprovacao,
    criado_em, criado_por
)
SELECT
    e.id,
    e.transportadora_id,
    nf.cnpj_emitente,
    nf.nome_emitente,
    nf.cnpj_destinatario,
    ei.cliente,
    ei.uf_destino,
    ei.cidade_destino,
    COALESCE(e.tipo_carga, 'DIRETA'),
    COALESCE(ei.peso, 0),
    COALESCE(ei.valor, 0),
    1,
    bf.numero_nf,
    0, 0,
    bf.cte_valor,
    bf.operacao_id,
    bf.fatura_cliente_id,
    'PENDENTE', 'PENDENTE', false,
    NOW(),
    'backfill-bug-gatilho-form-embarque-2026-04-20'
FROM backfill_itens bf
JOIN embarques e ON e.id = bf.embarque_id
JOIN embarque_itens ei ON ei.id = bf.item_id
JOIN carvia_nfs nf ON nf.numero_nf = bf.numero_nf AND nf.status = 'ATIVA'
WHERE ei.nota_fiscal = bf.numero_nf  -- garante que Parte 1 ja atualizou 4855
  AND NOT EXISTS (
      SELECT 1 FROM carvia_fretes cf2
      WHERE cf2.embarque_id = bf.embarque_id
        AND cf2.numeros_nfs = bf.numero_nf
  );

-- ----------------------------------------------------------------------------
-- PARTE 3: Sincronizar entregas_monitoradas (origem='CARVIA')
-- Preenche transportadora e data_embarque onde estao vazios.
-- Replica campos tecnicos de sincronizar_entrega_carvia_por_nf (linha 129-137).
-- ----------------------------------------------------------------------------

UPDATE entregas_monitoradas em
SET
    transportadora = COALESCE(t.razao_social, '-'),
    data_embarque = e.data_embarque
FROM embarque_itens ei
JOIN embarques e ON e.id = ei.embarque_id
LEFT JOIN transportadoras t ON t.id = e.transportadora_id
WHERE em.numero_nf = ei.nota_fiscal
  AND em.origem = 'CARVIA'
  AND em.numero_nf IN ('36278', '1652', '4819', '36879', '1630', '1631')
  AND e.id IN (4584, 4901, 4902, 4855)
  AND ei.separacao_lote_id LIKE 'CARVIA-%'
  AND ei.status = 'ativo'
  AND (em.transportadora IS NULL OR em.transportadora = '-' OR em.data_embarque IS NULL);

-- ----------------------------------------------------------------------------
-- VERIFICACOES (rodar SELECT antes do COMMIT para validar)
-- ----------------------------------------------------------------------------

-- Quantos CarviaFrete criados? (esperado: 6)
SELECT COUNT(*) AS fretes_criados_backfill
FROM carvia_fretes
WHERE criado_por = 'backfill-bug-gatilho-form-embarque-2026-04-20';

-- Estado final das EntregaMonitorada afetadas
SELECT
    em.numero_nf, em.origem, em.cliente,
    em.transportadora, em.data_embarque, em.status_finalizacao
FROM entregas_monitoradas em
WHERE em.numero_nf IN ('36278', '1652', '4819', '36879', '1630', '1631')
  AND em.origem = 'CARVIA'
ORDER BY em.numero_nf;

-- Se tudo OK:
COMMIT;

-- Se algo errado:
-- ROLLBACK;
