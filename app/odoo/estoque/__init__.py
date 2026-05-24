"""app/odoo/estoque — operações de ESCRITA de estoque no Odoo.

Pacote-destino da consolidação dos ~105 scripts ad-hoc de inventário
(scripts/inventario_2026_05/) em ÁTOMOS versáteis e auto-seguros, consumidos
por skills (.claude/skills/) + subagente `gestor-estoque-odoo`.

Constituição: app/odoo/estoque/CLAUDE.md. Camadas:
  scripts/        átomos C1/C2 (StockQuantAdjustmentService, StockLotService, ...)
  orchestrators/  átomos C3 macro já-codificados (InventarioPipelineService)
  fluxos/         folhas da árvore de fluxos (L3, progressive disclosure)
  _utils.py       helpers de estoque (buscar_quant unificado, _registrar_op, norm_lote)

Migração INCREMENTAL via SHIMS em app/odoo/services/<nome>_service.py (re-export):
preserva os scripts/testes ativos da operação viva. Mover 1 service por skill,
nunca em bloco. Roadmap: app/odoo/estoque/ROADMAP_SKILLS.md.
"""
