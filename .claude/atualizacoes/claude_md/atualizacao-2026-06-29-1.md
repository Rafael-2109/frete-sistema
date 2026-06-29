# Atualizacao CLAUDE.md — 2026-06-29-1

**Data**: 2026-06-29
**Arquivos auditados**: 9/9
**Arquivos modificados**: 6 (todos menos `carteira`, `seguranca` e `teams`)

## Resumo

Auditados os 9 CLAUDE.md contra o estado real do codigo (LOC, contagens de
arquivo/template, caminhos). 4 modulos tiveram drift estrutural desde 22/06:
`carvia` foi o maior — features **Carta de Correcao (CCe)** + **Cotacao Rapida/Publica**
+ **propagacao de endereco** adicionaram routes (36->37), services (51->57) com
documentos/ (16->19), models (18->19), utils (+`rate_limit.py`); header subiu
137->138 / ~75.0K->~76.7K / 127->132 templates. `financeiro` ganhou a feature
**Validador de Titulos** (+route `validador_titulos.py`, +subpacote `validador_titulos/`
com 7 modulos, +service `antecipacao_caixinhas.py`) — header (94/~49.1K) ja' batia,
mas o tree subcounts estavam parados (routes 19->20, services 29->30 root + novo
subpacote). `agente` +1 sdk (`subagent_checkpoint.py` — handoff de estado entre spawns;
ja' citado na nav table, faltava no count: 26->27; header 109->110 / ~57.1K->~57.4K).
`odoo` +1 script estoque (`reclassificacao.py` — Skill F2 #3 `reclassificando-amls-odoo`;
estoque 21->22 / ~20.8K->~21.1K, total 72->73 / ~43.4K->~43.9K; o `app/odoo/estoque/CLAUDE.md`
ja' catalogava a skill, faltava o arquivo no tree do guia do modulo). Raiz: tech stack
(SDK 0.2.101 / CLI 2.1.177 / anthropic 0.109.1 / MCP 1.26 / Flask 3.1.2 / SQLAlchemy 2.0 /
Pydantic 2.12 / FastAPI 0.129) confere com `requirements.txt` — so' data. `carteira`
(53/~19.9K/22 JS, 22/06), `seguranca` (14/1953/8, 06/06) e `teams` (5/~3.7K, 14/06)
conferem 100% — intocados.

## Alteracoes por Arquivo

### `CLAUDE.md` (raiz)
- [x] doc:meta `atualizado`: 2026-06-22 -> 2026-06-29
- [x] body `Ultima Atualizacao`: 22/06/2026 -> 29/06/2026
- [x] Tech stack (anthropic 0.109.1 / claude-agent-sdk 0.2.101 / CLI 2.1.177 / mcp 1.26 /
  Flask 3.1.2 / SQLAlchemy 2.0.46 / Pydantic 2.12.5 / FastAPI 0.129.0) conferido vs
  `requirements.txt` — sem mudanca de conteudo, so' data

### `app/agente/CLAUDE.md`
- [x] Header: 109 -> **110 arquivos**, ~57.1K -> **~57.4K LOC** (57438 real); data 22/06 -> 29/06
- [x] doc:meta `atualizado`: 2026-06-22 -> 2026-06-29
- [x] Tree `sdk/` 26 -> **27 arquivos** (+`subagent_checkpoint.py` — handoff de estado entre
  spawns de subagente, Rota B; flag `AGENT_SUBAGENT_CHECKPOINT` off/shadow/on). A linha
  do arquivo JA estava no bloco do tree e na nav table (linha 35) — so' o COUNT lagava

### `app/carvia/CLAUDE.md`
- [x] Header: 137 -> **138 arquivos**, ~75.0K -> **~76.7K LOC** (76718 real),
  127 -> **132 templates**; doc:meta + body 2026-06-26 -> 2026-06-29
- [x] Tree `routes/` 36 -> **37 sub-rotas** (+`carta_correcao` — CCe do CTe, R23)
- [x] Tree `services/` 51 -> **57**; `documentos/` 16 -> **19** (+`carta_correcao_service`,
  +`cce_render`, +`_cadeia_nf` — todos da CCe R23); `clientes/` 1 -> **2**
  (+`propagacao_endereco_service` — propaga endereco destino, R23)
- [x] Tree `models/` 18 -> **19 modulos** (+`carta_correcao`)
- [x] Tree `utils/` +`rate_limit.py` (rate limit da Cotacao Publica, R24)
- [x] `cotacao_publica.py` (root, R24) ja' estava no tree desde 06-22 — consistente

### `app/financeiro/CLAUDE.md`
- [x] doc:meta `atualizado`: 2026-06-22 -> 2026-06-29; body 24/06/2026 -> 29/06/2026
  (header `94 arquivos / ~49.1K LOC` JA batia o real 94/49073 — atualizado em 24/06)
- [x] Tree `routes/` "19 + __init__" -> **"20 + __init__"** (+`validador_titulos.py`)
- [x] Tree `services/` "29 services root" -> **"30 services root"** (+`antecipacao_caixinhas.py`);
  documentado novo subpacote **`validador_titulos/`** (7 modulos: comparador, cp_nacom,
  exportador, faturamento, normalizador, parsers_bancos, service) ao lado de `remessa_vortx/`

### `app/odoo/CLAUDE.md`
- [x] Header: 72 -> **73 arquivos**, ~43.4K -> **~43.9K LOC** (43854 real); data 22/06 -> 29/06
- [x] doc:meta `atualizado`: 2026-06-22 -> 2026-06-29
- [x] Subpacote `estoque/`: 21 -> **22 arquivos**, ~20.8K -> **~21.1K LOC** (21137 real) —
  atualizado nos 2 pontos (linha do contexto + bloco do tree)
- [x] Tree `estoque/scripts/` +`reclassificacao.py` (Skill F2 #3 `reclassificando-amls-odoo`,
  account.move.line conta_origem->destino). O `app/odoo/estoque/CLAUDE.md` (fora do escopo dos 9)
  JA catalogava a skill; faltava o arquivo no tree do guia do modulo odoo

## Sem Alteracoes (confere exatamente)
- `app/carteira/CLAUDE.md` — 53 arquivos / 19877 LOC (~19.9K) / 22 JS; services 7;
  doc:meta e body em 2026-06-22 — intocado (sem drift estrutural desde 22/06)
- `app/seguranca/CLAUDE.md` — 14 arquivos / 1953 LOC (~2K) / 8 templates; doc:meta e
  body em 2026-06-06 — intocado
- `app/teams/CLAUDE.md` — 5 arquivos / 3728 LOC (~3.7K); doc:meta e body em 2026-06-14;
  drift organico de LOC (3703 -> 3728) ainda dentro de ~3.7K, nenhum arquivo novo — intocado

## Verificacao de Caminhos
Todos os caminhos novos adicionados foram confirmados via `test -e`:
`carta_correcao_routes.py`, `carta_correcao_service.py`, `cce_render.py`, `_cadeia_nf.py`,
`propagacao_endereco_service.py`, `models/carta_correcao.py`, `utils/rate_limit.py`,
`cotacao_publica.py` (CarVia); `routes/validador_titulos.py`, `services/antecipacao_caixinhas.py`,
`services/validador_titulos/service.py` (financeiro); `sdk/subagent_checkpoint.py` (agente);
`estoque/scripts/reclassificacao.py` (odoo). Arquivos novos identificados via
`git log --diff-filter=A --since=2026-06-22`. Nenhum arquivo deletado no periodo.
As regras R23 (CCe) e R24 (Cotacao Publica) referenciadas nos comentarios do tree
CarVia foram confirmadas presentes (linhas 348 e 380). Nenhum caminho inexistente permaneceu.

## Notas
- Contagens LOC = `find -name "*.py" -not -path "*__pycache__*" -exec wc -l + | tail -1`
  (inclui blank/comments); templates HTML contados separadamente. Subcounts de pacote
  excluem `__init__.py` (convencao do tree); o header do modulo conta TODOS os `.py`.
- `app/odoo/estoque/CLAUDE.md` (auto-count proprio, ja' atualizado com `reclassificacao.py`)
  NAO esta no escopo dos 9; apenas a referencia a ele em `app/odoo/CLAUDE.md` (22 arquivos /
  ~21.1K) foi reconciliada.
- `financeiro`: o header (94/~49.1K) ja' refletia os arquivos novos desde 24/06; o trabalho
  desta auditoria foi reconciliar os SUBCOUNTS do tree (routes/services + subpacote novo) +
  sincronizar as 2 datas (doc:meta 06-22 e body 06-24 -> 06-29).
- `agente`/`odoo`: padrao identico — o item ja' aparecia em UM lugar (nav table / catalogo de
  skill) mas o COUNT do tree do modulo lagava; corrigido count + linha do tree.
