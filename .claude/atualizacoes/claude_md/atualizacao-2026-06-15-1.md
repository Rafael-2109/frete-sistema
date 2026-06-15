# Atualizacao CLAUDE.md — 2026-06-15-1

**Data**: 2026-06-15
**Arquivos auditados**: 9/9
**Arquivos modificados**: 8 (todos menos `app/seguranca/CLAUDE.md`)

## Resumo

Auditados os 9 CLAUDE.md contra o estado real do codigo (LOC, contagens de
arquivo/template, caminhos). 4 modulos tiveram drift estrutural desde 08/06:
`agente` (104 -> 108 arquivos, ~53.5K -> ~56.4K LOC), `carvia` (107 -> 108,
~67.4K -> ~67.7K, +1 template), `financeiro` (80 -> 83, ~46.2K -> ~46.9K,
feature SRM Bank PDF->OFX) e `odoo` (70 -> 72, ~42.5K -> ~43.4K; subpacote
`estoque/` 19 -> 21 scripts, ~19.9K -> ~20.8K). `carteira` e a raiz conferem
em conteudo (so data). `teams` ja estava com o body em 14/06 (LOC ~3.7K/5
conferem) — apenas o doc:meta de frontmatter seguia em 06-11, sincronizado.
`seguranca` confere 100% (14/1953/8, doc:meta 06/06) — intocado. SDK na raiz
(0.2.101 / CLI 2.1.177 / anthropic 0.109.1 / mcp 1.26) bate com `requirements.txt`.

## Alteracoes por Arquivo

### `CLAUDE.md` (raiz)
- [x] doc:meta + body `Ultima Atualizacao`: 2026-06-08 -> 2026-06-15
- [x] Tech stack SDK (0.2.101 / CLI 2.1.177 / anthropic 0.109.1 / mcp 1.26)
  conferido vs `requirements.txt` — sem mudanca de conteudo

### `app/agente/CLAUDE.md`
- [x] Header: 104 -> **108 arquivos**, ~53.5K -> **~56.4K LOC**; data 08/06 -> 15/06
- [x] doc:meta `atualizado`: 2026-06-08 -> 2026-06-15
- [x] Tree Root: 7 -> **8 arquivos** (+`conversa.md`, legado 16K)
- [x] SDK_CHANGELOG.md: historico `0.1.49 -> 0.2.89` -> `0.1.49 -> 0.2.101`
- [x] `sdk/` 24 -> **26 arquivos**: +`turn_context_registry.py` (falante do turno
  em grupos Teams, Fase B), +`vincular_teams_fastpath.py` (fast-path pareamento)
- [x] `services/` 23 -> **25 arquivos**: +`adhoc_capture_service.py`, +`memory_format.py`
- [x] Secao "### Services (23 arquivos, ~13.8K LOC)" -> "(25 arquivos, ~14.9K LOC)"
- [x] Conferidos e corretos: routes 21, config 7, tools 15 (14 + __init__),
  workers 8, templates 7, prompts 4, utils 2, hooks 2

### `app/agente/services/CLAUDE.md`
- [x] Header: 23 -> **25 arquivos**, ~13.8K -> **~14.9K LOC** (14881 real); data -> 2026-06-15
- [x] doc:meta `atualizado`: 2026-06-08 -> 2026-06-15
- [x] Arvore de Estrutura: +`adhoc_capture_service.py` (`memory_format.py` ja listado)

### `app/carvia/CLAUDE.md`
- [x] Header: 107 -> **108 arquivos**, ~67.4K -> **~67.7K LOC** (67701 real),
  109 -> **110 templates** (+`simulador/_pack_controls.html`)
- [x] doc:meta `atualizado`: 2026-06-12 -> 2026-06-15; body 2026-06-08 -> 2026-06-15
- [x] Conferidos e corretos: routes 30, services 43 (admin 1 + clientes 1 +
  documentos 10 + financeiro 16 + parsers 7 + pricing 6 + 2 root — `lancamento_freteiro`
  ja documentado), 4 workers, 14 models. O +1 py = `services/financeiro/lancamento_freteiro_service.py`

### `app/financeiro/CLAUDE.md`
- [x] Header: 80 -> **83 arquivos**, ~46.2K -> **~46.9K LOC** (46931 real); data 08/06 -> 15/06
- [x] doc:meta `atualizado`: 2026-06-08 -> 2026-06-15
- [x] `routes/` 18 -> **19 arquivos** (+`conversor_extrato_srm.py`)
- [x] `services/` 27 -> **28 root** (+`extrato_pdf_srm_service.py`)
- [x] Feature SRM Bank PDF->OFX (3 arquivos novos: route + service + script ja citado)

### `app/odoo/CLAUDE.md`
- [x] Header: 70 -> **72 arquivos**, ~42.5K -> **~43.4K LOC** (43436 real); data 08/06 -> 15/06
- [x] doc:meta `atualizado`: 2026-06-08 -> 2026-06-15
- [x] Subpacote `estoque/`: 19 -> **21 arquivos**, ~19.9K -> **~20.8K LOC** (20789 real)
  — 2 ocorrencias (linha 42 + tree linha 106)
- [x] Tree `estoque/scripts/`: +`descoberta_industrializacao.py` (descoberta ciclo
  industrializacao FB-LF), +`revaloracao.py` (revalorar_custo AVCO)
- [x] Conferidos: services 21, utils 13, constants 4, jobs 0 — sem mudanca

### `app/teams/CLAUDE.md`
- [x] doc:meta `atualizado`: 2026-06-11 -> 2026-06-14 (sincronizado ao body — gotcha
  de telemetria por-turno datado 2026-06-14)
- [x] LOC ~3.7K / 5 arquivos (3701 real) conferem — sem mudanca estrutural

### `app/carteira/CLAUDE.md`
- [x] doc:meta + body `Atualizado`: 2026-06-08 -> 2026-06-15
- [x] Contagens conferem exatamente: 50 arquivos / 18516 LOC (~18.5K) / 22 JS / 13 html

## Sem Alteracoes (confere exatamente)
- `app/seguranca/CLAUDE.md` — 14 arquivos / 1953 LOC (~2K) / 8 templates: confere;
  doc:meta e body ja em 2026-06-06 — intocado

## Verificacao de Caminhos
Todos os caminhos citados nos arquivos modificados foram confirmados como
existentes. Arquivos novos identificados via `git log --diff-filter=A --since=2026-06-08`:
`conversa.md`, `turn_context_registry.py`, `vincular_teams_fastpath.py`,
`adhoc_capture_service.py`, `memory_format.py`, `regression_gate.py` (ja no tree),
`lancamento_freteiro_service.py`, `conversor_extrato_srm.py`, `importar_extrato_pdf_srm.py`,
`extrato_pdf_srm_service.py`, `descoberta_industrializacao.py`, `revaloracao.py`,
`_pack_controls.html`. Nenhum caminho inexistente encontrado.

## Notas
- Contagens LOC = `find -name "*.py" -not -path "*__pycache__*" -exec wc -l + | tail -1`
  (inclui blank/comments); templates HTML contados separadamente.
- `app/odoo/estoque/CLAUDE.md` (auto-count proprio, header "snapshot v18") NAO esta
  no escopo dos 9; apenas a referencia a ele em `app/odoo/CLAUDE.md` foi sincronizada.
- `templates/agente/` ficam em `app/agente/templates/agente/` (module-local), 7 html — conferem.
