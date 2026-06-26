-- Idempotente. Adiciona inscricao_estadual (registro/exibicao; NAO vai para a
-- NFe) ao pedido de venda HORA. Preenchimento manual — a ReceitaWS (base
-- federal) nao retorna IE (estadual). Migration HORA 52 (2026-06-25).
ALTER TABLE hora_venda ADD COLUMN IF NOT EXISTS inscricao_estadual VARCHAR(20);
