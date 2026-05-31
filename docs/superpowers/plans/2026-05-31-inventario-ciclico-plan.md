# Inventário Cíclico — Plano enxuto de implementação

Spec: `docs/superpowers/specs/2026-05-31-inventario-ciclico-contagem-ajustes-design.md`
Branch: `feat/inventario-ciclico` (worktree). Validação: Rafael em PROD.

## Fases (ordem + dependências)

1. **Modelos + Migration + Schemas** — `ContagemInventario`, `ContagemInventarioItem` em `models.py`; migration `.py`+`.sql`; 2 schemas JSON. Rodar migration local.
2. **`extracao_quant_service.py`** — porta a lógica de `extrair_estoque_locais_emp.py` (helpers + query `stock.quant` com `reserved_quantity`/`lot`/`location`); retorna lista de quants agregados por (location, cod, lote). Filtros: empresa + locais + códigos + incluir_indisponivel. (TDD com Odoo mockado.)
3. **`contagem_service.py`** — `criar_e_gerar_base`, `preview_reupload`, `confirmar_reupload`, `classificar`. Regras: presente+vazio⇒0, ausente⇒ignora, linha-nova⇒LOTE_NOVO; ajuste=contagem−qtd_esperada. (TDD — núcleo de regras.)
4. **`contagem_export_service.py`** — Excel da base (formato planilha 31-05) e do relatório/plano (com ajuste+classe). xlsxwriter.
5. **`confronto_service.py` (ALTERAÇÃO)** — `_agg_ajustes_ciclicos(ciclo)` soma `ContagemInventarioItem.ajuste` por (cod, empresa) no intervalo de data `[data_snapshot, próximo completo)`; somar em inv_fb/cd/lf. (TDD: Produto A=900 + regressão.)
6. **Routes + Templates + Menu** — `contagem_routes.py` (lista/criar+base/download/upload-preview/confirmar/relatório/export); `contagens.html`, `contagem_detalhe.html`; link no `_sidebar.html` (bloco admin, após Confronto); registrar em `routes/__init__.py`.
7. **Verificação** — `pytest tests/inventario/`; migration local; import OK.

## Checklist pré-entrega
- [ ] Migration 2 artefatos (.py + .sql idempotente)
- [ ] 2 schemas JSON em `.claude/skills/consultando-sql/schemas/tables/`
- [ ] Link no menu (`_sidebar.html`) — admin
- [ ] Routes registradas no blueprint (`routes/__init__.py`)
- [ ] `require_admin` em todas as rotas
- [ ] `sanitize_for_json` nos retornos JSON
- [ ] `agora_utc_naive` em timestamps
- [ ] Regra por-quant (3 casos) + classificação cobertas por teste
- [ ] Regressão do Confronto (sem cíclico ⇒ resultado atual)
- [ ] Sem `<style>` em template; usar tokens/CSS de módulo se necessário
