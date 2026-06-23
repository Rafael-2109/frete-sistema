# Atualizacao CLAUDE.md — 2026-06-22-1

**Data**: 2026-06-22
**Arquivos auditados**: 9/9
**Arquivos modificados**: 7 (todos menos `app/seguranca/CLAUDE.md` e `app/teams/CLAUDE.md`)

## Resumo

Auditados os 9 CLAUDE.md contra o estado real do codigo (LOC, contagens de
arquivo/template, caminhos). 4 modulos tiveram drift estrutural desde 15/06:
`carvia` foi o maior — feature **Portal do Cliente + Coletas + Comprovantes**
adicionou rotas (31->35), services em `documentos/` (12->16), models (15->18) e
root `portal_cliente.py`; o header (126/~73.0K/127) ja batia. `carteira` ganhou
roteirizacao (50->53 arquivos, ~18.5K->~19.9K LOC; services 5->7). `agente`
+1 service (`upload_recovery_service.py`; 108->109, ~56.4K->~57.1K) e o
`conversa.md` legado foi removido (root volta a 7). `financeiro` +1 service
(`baixa_credores_lote_service.py`; 83->84, ~46.9K->~47.6K). `odoo` so' drift
organico de LOC (43436->43539, mantem ~43.4K; 72 arquivos / estoque 21 / services
21 / utils 13 sem mudanca) — apenas data. `agente/services` ja' fora corrigido
em 06-20 (26 arquivos / ~15.0K, body datado) — so' o frontmatter `atualizado`
seguia em 06-15, sincronizado. Raiz: SDK 0.2.101 / CLI 2.1.177 / anthropic
0.109.1 / MCP 1.26 conferem com `requirements.txt` — so' data. `seguranca`
(14/1953/8, 06/06) e `teams` (5/3703, 06/14) conferem 100% — intocados.

## Alteracoes por Arquivo

### `CLAUDE.md` (raiz)
- [x] doc:meta `atualizado`: 2026-06-08 -> 2026-06-22 (frontmatter seguia em 06-08;
  body ja estava em 06-15 desde a auditoria anterior — sincronizados)
- [x] body `Ultima Atualizacao`: 15/06/2026 -> 22/06/2026
- [x] Tech stack AI/Agente (SDK 0.2.101 / CLI 2.1.177 / anthropic 0.109.1 / MCP 1.26)
  conferido vs `requirements.txt` — sem mudanca de conteudo

### `app/agente/CLAUDE.md`
- [x] Header: 108 -> **109 arquivos**, ~56.4K -> **~57.1K LOC** (57072 real); data 15/06 -> 22/06
- [x] doc:meta `atualizado`: 2026-06-15 -> 2026-06-22
- [x] Tree `services/` 25 -> **26 arquivos** (+`upload_recovery_service.py` — dual-write
  `/tmp` + S3 `agente-uploads/{user_id}/`, recuperacao de uploads do chat)
- [x] Secao "### Services (25 arquivos, ~14.9K LOC)" -> "(26 arquivos, ~15.1K LOC)"
- [x] `conversa.md` (legado 16K) foi DELETADO do modulo — root volta a **7 arquivos**
  (header ja em 7); nao era referenciado no tree (estava so' no INDEX, ja consistente)
- [x] Conferidos e corretos: routes 21, config 7 (8 no header conta __init__), sdk 26,
  tools 15, workers 8, hooks 1 (__init__; README.md = doc, nao py), prompts 4, utils 2,
  templates module-local 7

### `app/agente/services/CLAUDE.md`
- [x] doc:meta `atualizado`: 2026-06-15 -> 2026-06-20 (sincronizado ao body — conteudo
  ja' fora corrigido em 06-20 com `upload_recovery_service.py` no tree)
- [x] Header (26 arquivos / ~15.0K LOC / 14998 real) confere — sem mudanca de body

### `app/carvia/CLAUDE.md`
- [x] doc:meta `atualizado`: 2026-06-19 -> 2026-06-22; body 2026-06-21 -> 2026-06-22
- [x] Header (126 arquivos / ~73.0K LOC / 127 templates) **ja' batia** com o real —
  o drift estava nos subcounts do tree
- [x] Tree `routes/` 31 -> **35 sub-rotas** (+`coleta`, +`portal_admin`, +`portal_operacional`)
- [x] Tree `services/` 44 -> **51**; `documentos/` 12 -> **16** (+`coleta`, +`coleta_recebimento`,
  +`portal_auth`, +`portal_status`)
- [x] Tree `models/` 15 -> **18 modulos** (+`coleta`, +`coleta_recebimento`, +`portal`)
- [x] Tree root: +`portal_cliente.py` (Blueprint do portal do cliente)
- [x] Sub-docs `COMPROVANTES.md` e `RESULTADO_FRETE.md` (novos no modulo) ja' referenciados
  na nav table (linhas 60, 72) — consistente

### `app/carteira/CLAUDE.md`
- [x] Header: 50 -> **53 arquivos**, ~18.5K -> **~19.9K LOC** (19877 real); data 19/06 -> 22/06
- [x] doc:meta `atualizado`: 2026-06-18 -> 2026-06-22 (frontmatter lagava o body 06-19)
- [x] Tree `services/` 5 -> **7** (+`roteirizacao_service` + `roteirizacao_backends` — custo
  parametrico, selecao de veiculo, motor de otimizacao com abstracao de backend);
  nomes corrigidos para `importacao_nao_odoo` / `atualizar_dados`
- [x] Conferidos: routes 25 (root), JS 22 (21 templates + 1 static), templates 13 HTML

### `app/financeiro/CLAUDE.md`
- [x] Header: 83 -> **84 arquivos**, ~46.9K -> **~47.6K LOC** (47585 real); data 15/06 -> 22/06
- [x] doc:meta `atualizado`: 2026-06-15 -> 2026-06-22
- [x] Tree `services/` 28 -> **29 root** (+`baixa_credores_lote_service.py` — baixa de
  pagamentos em lote SICOOB/DESAGIO); subpacote `remessa_vortx/` 8 sem mudanca

### `app/odoo/CLAUDE.md`
- [x] doc:meta + body `Atualizado`: 2026-06-15 -> 2026-06-22
- [x] Sem mudanca estrutural: 72 arquivos / estoque 21 (~20.8K, 20822 real) / services 21 /
  utils 13 / constants 4 conferem. LOC total drift organico 43436 -> 43539 (mantem ~43.4K)

## Sem Alteracoes (confere exatamente)
- `app/seguranca/CLAUDE.md` — 14 arquivos / 1953 LOC (~2K) / 8 templates; doc:meta e
  body em 2026-06-06 — intocado
- `app/teams/CLAUDE.md` — 5 arquivos / 3703 LOC (~3.7K); doc:meta e body em 2026-06-14;
  nenhum arquivo novo desde 06-14 — intocado

## Verificacao de Caminhos
Todos os caminhos citados (existentes e os novos adicionados) foram confirmados como
existentes via `test -e`. Arquivos novos identificados via
`git log --diff-filter=A --since=2026-06-15`:
`upload_recovery_service.py`, `palletizacao_service.py` (ja documentado),
`roteirizacao_backends.py`, `roteirizacao_service.py`, `baixa_credores_lote_service.py`,
e a leva CarVia (`coleta.py`, `coleta_recebimento.py`, `comprovante.py`, `portal.py`,
`portal_cliente.py`, `coleta_routes.py`, `comprovante_routes.py`, `portal_admin_routes.py`,
`portal_operacional_routes.py`, `resultado_frete_routes.py`, `coleta_service.py`,
`coleta_recebimento_service.py`, `comprovante_service.py`, `motos_lote_service.py`,
`portal_auth_service.py`, `portal_status_service.py`, `resultado_frete_service.py`,
`viabilidade_service.py`, `COMPROVANTES.md`, `RESULTADO_FRETE.md`). Deletado e confirmado
ausente: `app/agente/conversa.md` (nao referenciado no tree). Nenhum caminho inexistente
permaneceu nos arquivos.

## Notas
- Contagens LOC = `find -name "*.py" -not -path "*__pycache__*" -exec wc -l + | tail -1`
  (inclui blank/comments); templates HTML contados separadamente.
- `app/agente/templates/agente/` (module-local, 7 html) NAO aparece em `app/templates/`
  — por isso `find app/templates/agente` da 0; conferido via `app/agente/templates/`.
- `app/odoo/estoque/CLAUDE.md` (auto-count proprio) NAO esta no escopo dos 9; apenas a
  referencia a ele em `app/odoo/CLAUDE.md` (21 arquivos / ~20.8K) foi conferida — confere.
- CarVia: o header (126/127) ja' refletia os arquivos novos; o trabalho desta auditoria
  foi reconciliar os SUBCOUNTS do tree (routes/services/models), que tinham ficado para tras.
