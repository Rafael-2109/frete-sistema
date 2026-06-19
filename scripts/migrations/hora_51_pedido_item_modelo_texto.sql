-- Migration HORA 51: coluna modelo_texto_original em hora_pedido_item.
--
-- Espelha hora_nf_entrada_item.modelo_texto_original. Sem ela, a retroatividade
-- (modelo_retroatividade_service.propagar_resolucao) NAO conseguia correlacionar
-- item de pedido x pendencia de modelo, e o item ficava com o modelo sentinela
-- DESCONHECIDO ate o operador editar manualmente.
--
-- Idempotente (ADD COLUMN IF NOT EXISTS).

ALTER TABLE hora_pedido_item
    ADD COLUMN IF NOT EXISTS modelo_texto_original VARCHAR(255);
