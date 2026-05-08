-- Migration HORA 38: campos de frete CIF em hora_venda
--
-- Adiciona duas colunas para apoiar a UI de calculo de frete em pedidos
-- com modalidade CIF (modalidade_frete='0'):
--   * valor_frete       — valor monetario do frete (R$).
--   * tipo_frete_calc   — 'INCLUSO' (frete embutido no valor da moto) ou
--                         'ADICIONAR' (frete somado ao valor da moto;
--                          rateado entre itens em pedidos multi-moto).
--
-- Ambas nullable: pedidos legados, FOB, sem ocorrencia ou DANFE importada
-- ficam com NULL e o template oculta os controles de frete.
--
-- Validacao da combinacao (tipo_frete_calc in ('INCLUSO','ADICIONAR') e
-- exclusividade com CIF) ocorre na camada de service para evitar bloquear
-- pedidos legados durante MIGRATION ou rollback.
--
-- Idempotente — pode rodar 2x sem efeito (IF NOT EXISTS).

ALTER TABLE hora_venda
    ADD COLUMN IF NOT EXISTS valor_frete NUMERIC(15, 2);

ALTER TABLE hora_venda
    ADD COLUMN IF NOT EXISTS tipo_frete_calc VARCHAR(10);
