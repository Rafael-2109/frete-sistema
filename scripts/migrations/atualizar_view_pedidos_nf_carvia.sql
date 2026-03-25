-- Migration: Atualizar VIEW pedidos — NF para CarVia Part 2B
-- Data: 2026-03-25
-- Descricao: Expor NF dos CarviaPedidoItens na VIEW pedidos Part 2B
-- RISCO: VIEW e backbone. Atualiza apenas Part 2B (NF subquery).
-- Uso: Executar alterar_view_pedidos_union_carvia.sql completo (DROP + CREATE)
--       Este arquivo e apenas documentacao da mudanca incremental.

-- A mudanca esta no arquivo principal alterar_view_pedidos_union_carvia.sql
-- Part 2B, coluna nf: NULL::text → subquery string_agg(DISTINCT pi.numero_nf)
-- Executar: \i scripts/migrations/alterar_view_pedidos_union_carvia.sql
