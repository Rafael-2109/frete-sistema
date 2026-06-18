-- 2026-06-18: adiciona coluna `import_resumo` (JSONB) em assai_pedido_venda.
-- Origem: IMP-2026-06-18-001 (parser cortava lojas com parsing_confianca=1.00).
-- Guarda o balanço do import (lojas/itens extraídos vs gravados + lista de
-- pulados) tornando o silent data loss VISÍVEL na tela de detalhe, e marca
-- edicao_manual=True quando o operador edita o pedido (IMP-2026-06-18-003/-004).
--
-- Idempotente: ADD COLUMN IF NOT EXISTS.
-- Aplicada MANUALMENTE em produção via DATABASE_URL_PROD (2026-06-18) e no banco
-- local. NÃO consta no build.sh. Mantido como registro versionado do DDL.

ALTER TABLE assai_pedido_venda
    ADD COLUMN IF NOT EXISTS import_resumo JSONB;
