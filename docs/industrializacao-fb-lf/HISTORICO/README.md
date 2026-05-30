# HISTÓRICO — execução-piloto revertida (Opção 2 / inter-company)

> ⚠️ **NÃO SEGUIR o fluxo descrito aqui.** Esta pasta guarda a execução-piloto da **"Opção 2" (inter-company automático: `rule_type=sale_purchase`, PO→SO, DFe→PO, subcontratação)**, **abandonada e revertida em 2026-05-29**.

## Por que foi abandonada
- `rule_type='sale_purchase'` é company-wide → disparou SO espelho em toda transferência inter-company (inclusive CD↔FB). Revertido para `not_synchronize`.
- Odoo bloqueia `stock.rule` cross-company (`_check_company`).
- O piloto (PO 42659, SO 73424, MO 20154/20155, NF 725676, DFe 43689) foi revertido.

## O que AINDA é válido aqui (referência)
- **IDs, locations, picking types, BoMs, operações fiscais, contas** — corretos (consolidados em `../ACHADOS_TECNICOS.md`).
- **Decisões fiscais/de produto** (CFOPs, estrutura BoM 3695→3646, água=insumo LF, R$35/cx, 16 componentes) — em `DECISOES.md` (D01-D09, D17).
- `scripts/setup_s0.py` criou a infra (locations 31092/31093, pt 98, BoMs strict, desativou 14833) — essa infra permanece.

## Fonte do fluxo CORRETO
`../README.md` → `../DIRETRIZ.md` → `../00_FLUXO_ATUAL_VS_IDEAL.md` (§3) → `../PLANO_EXECUCAO.md`.

## Conteúdo
- `CONTEXTO.md`, `DECISOES.md`, `ABERTOS.md`, `STATUS.md` — docs do piloto (fluxo abandonado; fatos de cadastro válidos).
- `testes/` — resultados T02-T33 da montagem/execução da Opção 2.
- `scripts/` — `setup_s0.py` (multi-task de setup) + README.
