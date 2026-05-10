-- Migration: Partial UNIQUE INDEX em custo_considerado(cod_produto) WHERE custo_atual=TRUE
-- Objetivo: previne race condition que poderia gerar 2 versoes ativas para o mesmo produto.
-- A invariante "exatamente 1 registro custo_atual=TRUE por cod_produto" passa a ser
-- garantida pelo banco, nao apenas pela logica do service.
-- Data: 2026-05-10 (Sprint 2 - C8)

CREATE UNIQUE INDEX IF NOT EXISTS uq_custo_considerado_atual_unico
  ON custo_considerado(cod_produto)
  WHERE custo_atual = TRUE;
