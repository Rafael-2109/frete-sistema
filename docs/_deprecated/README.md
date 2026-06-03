# docs/_deprecated/ — legado morto arquivado

> Zona **fora da auditoria PAD-A** (`ignore_globs: **/_deprecated/**`). Conteudo
> mantido apenas para historico. **NAO seguir** — descreve features nunca
> construidas ou ja superseded.

Arquivados na PAD-A Onda 4g (2026-06-03) apos avaliacao vivo/morto contra o
codebase (13 docs/raiz; 8 vivos carimbados, estes 5 mortos arquivados):

| Arquivo | Motivo (evidencia verificada) |
|---------|-------------------------------|
| `CAMPOS_CRIAR_PEDIDO_ODOO.md` | Rascunho com placeholders `_____`; superseded por `docs/ESTUDO_CRIAR_PEDIDO_VENDA_ODOO.md` (citado pelo codigo em `app/pedidos/integracao_odoo/service.py:4`). |
| `ESPECIFICACAO_IMPORTADOR_PEDIDOS_TENDA.md` | Status "Aguardando Implementacao"; extractores comentados como futuros (`app/pedidos/leitura/processor.py:53-54`); tabela `portal_tenda_produto_depara` nunca criada. |
| `IMPLEMENTATION_PLAN_SENDAS.md` | Arquivos-alvo deletados no commit `e81146c5c` (transicao p/ export manual); endpoint proposto nunca criado. |
| `IMPORTACAO_DADOS.md` | Scripts-nucleo inexistentes; `ProcessadorFaturamentoTagPlus` descartado (`app/integracoes/tagplus/FLUXO_REAL_IMPORTACAO_TAGPLUS.md:217`). |
| `ROADMAP_LICITACAO_FRETE.md` | Auto-declara "Planejado (nao iniciado)"; zero codigo (`app/despacho/` inexistente; `LoteDespacho`/`OfertaFreteiro` = 0 hits). |
