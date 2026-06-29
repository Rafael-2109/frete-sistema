<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-29
-->
# Convergência Agente Lojas ↔ Web — HANDOFF (F2 COMPLETA → retomar F3)

> **Papel:** guia para retomar, em sessão limpa, a convergência do `app/agente_lojas/`
> (fork) com o `app/agente/` (web). Par do plano
> `docs/superpowers/plans/2026-06-28-convergencia-agente-lojas.md` (LER a
> `§REVISÃO DE ESCOPO` e o `Apêndice A`). Origem: avaliação A vs B + execução
> faseada 2026-06-28/29.

## Indice
- [Contexto](#contexto)
- [Estado atual](#estado-atual)
- [O que foi entregue](#o-que-foi-entregue)
- [O que falta (acionável)](#o-que-falta-acionável)
- [Decisões travadas](#decisões-travadas)
- [Comandos de retomada](#comandos-de-retomada)
- [PROMPT + GATILHO para a nova sessão](#prompt--gatilho-para-a-nova-sessão)

## Contexto

O fork `AgentLojasClient` (`app/agente_lojas/sdk/`) driftou para trás do agente
web e a memória nunca foi isolada por agente (pré-requisito de qualquer reuso).
A convergência híbrida (plano `2026-06-28`) ataca isso em fases: F0/F1 (drift +
crash, ✅) → F2/M3 (isolar memória por `agente_id`, fail-closed, ✅) → F3 (client
parametrizado por perfil). Esta sessão (2026-06-29) entregou F0+F1 + **F2
COMPLETA** (fatia 1 + fatia 2); este doc é o estado vivo para retomar F3.

## Estado atual

- **Worktree:** `.claude/worktrees/convergencia-agente-lojas` — branch
  `worktree-convergencia-agente-lojas`, rebaseada sobre `main` (2026-06-29,
  inclui Nubank OFX + `hora_recebimento_esperado`).
- **17 commits** sobre `main`; worktree limpa; **145 testes verdes + 1 skip**
  (baseline do handoff; suíte ampla F2: 534+ passed, 2 skip).
- **SEM push, SEM merge** — aguarda revisão "4-mãos".
- **Review adversarial** do diff da fatia 2 (4 dims × verificação): web-intacto
  ZERO achados; fail-closed apontou 2 fontes residuais via PreToolUse hook
  (`get_skill_reminders`, `_load_enforce_directives`) — **FECHADAS no commit
  e79411f98**; demais achados são F3/P2 (build_hooks wiring, KG-na-origem) ou
  refutados (cache por session_id já é 1:1 com agente; hardcode 'web' é by-design).

```
# fatia 2 (esta sessão):
e79411f98 feat(agente-mem): F2 fatia2 — sela fontes residuais via PreToolUse (M13 + enforce)
88db8be2c feat(agente-mem): F2 fatia2/E01 — isola busca semantica (pgvector+fallback) por agente
a019beebf feat(agente-mem): F2 fatia2/B01-B03 — isola intersession_briefing por agente
a2521fd3e feat(agente-mem): F2 fatia2/R01 — isola canal L1 user_rules por agente
4a362276b feat(agente-mem): F2 fatia2/M11+M12 — isola routing_context (armadilhas+dominio) por agente
58c7f92a7 feat(agente-mem): F2 fatia2/M08+M09 — isola session_window + resolved_pendencias por agente
472e0cf74 feat(agente-mem): F2 fatia2/M10 — isola operational_directives empresa por agente
# fatia 1 + F0/F1 (sessão anterior, hashes pós-rebase):
3bbdc62f6 docs(convergencia): handoff F2 fatia2 → F3
88ee4157b feat(agente-mem): F2/M3 fatia 1 — isola memória injetada por agente (6 queries)
...  (F0/F1: env dict, sdk_runtime, sdk_compat, erro SDK, QUIET_BOOT, session_id turno1)
```

## O que foi entregue

| Fase | Estado | Resumo |
|---|---|---|
| **F0** env dict | ✅ | `HOME=/tmp` + `STREAM_CLOSE_TIMEOUT=240s` no fork — corrige risco de crash no Render. |
| **F1** infra compartilhada | ✅ | Extrai `sdk_runtime.build_subprocess_env` + `sdk_compat.check_skills_option` (web+lojas, sem copiar); handlers de erro SDK; `NACOM_QUIET_BOOT`; `session_id` turno-1 aditivo; `empresa_briefing_path` morto limpo. **F1.5(b)** `agents=` explícito ADIADO p/ F3 (será via `agent_loader` parametrizado; `setting_sources=['project']` cobre `orientador-loja` hoje). |
| **F2/M3** memória | ✅ COMPLETA | **Fatia 1**: `_load_user_memories_for_context(..., agente_id='web')` + filtro em 6 queries (Tier 1/1.5/1.6/materialização Tier 2/KG/fallback). **Fatia 2** (esta sessão, 6 commits TDD): M10 directives empresa, M08 session_window + M09/H01 `get_by_path_for_agent`, M11/M12 routing_context+domínio, R01 user_rules (L1), B01-B03 intersession_briefing, E01 busca semântica (pgvector JOIN + fallback). Teste-contrato `test_memory_isolation_por_agente.py` (7 casos) + `tests/embeddings/test_memory_search_agente_isolation.py`. **Zero-migration.** `default='web'` ⇒ web inalterado (review adversarial: 3 dims zero achados). |

## O que falta (acionável)

### F2/M3 — P1/P2 (só pós-F3 — o fork tem air gap, não usa memória nem memory tools)
- **P1:** `memory_mcp_tool` (13 ops, gravar/filtrar por agente) + 7 jobs de consolidação (`insights_service`, `pattern_analyzer`, `directive_promotion`, `memory_consolidator`...) — particionar na escrita.
- **P2 (defesa extra):** migrations de coluna `agente` em `agent_memory_embeddings` + KG entities; `world_model`/`ontology_query` (N05) por perfil.

### Achados desta sessão (dívidas registradas — NÃO bloqueiam F3, mas F3 deve tratá-las)
1. **UNIQUE(`user_id`, `path`) sem `agente`** (`agent_memories`, constraint `uq_user_memory_path`).
   Consequência: um mesmo `(user_id, path)` só existe para UM agente. O isolamento de
   **retrieval** da fatia 2 é fail-closed (lojas não vê a memória 'web' nesse path → `None`).
   Mas quando o **lojas começar a GRAVAR** memórias (F3/P1), web e lojas não poderão
   coexistir no mesmo path (ex.: ambos `/memories/user.xml`). F3/P1 deve: namespacejar paths
   por agente OU migrar a constraint p/ `(user_id, path, agente)` (par `.sql`+`.py`).
2. **Fontes via PreToolUse hook (NÃO `_load`) — FILTRO já aplicado (commit e79411f98); falta só o WIRING do caller (F3):**
   - `get_skill_reminders_for_session(user_id, session_id, agente_id='web')` (`memory_injection.py`, M13) — query JÁ filtra; caller `hooks.py:185` ainda chama sem `agente_id` (usa default `'web'`).
   - `_load_enforce_directives(user_id, agente_id='web')` (`hooks.py:55`) — query JÁ filtra; cache key JÁ inclui agente (`(user_id, agente_id, bucket)`, prune `k[2]`); caller `hooks.py:425` ainda usa default `'web'`.
   Hoje seguras por **air gap** (o fork tem `hooks.py` próprio). Em F3, quando `build_hooks`
   receber `agente_id` (ver item de F3 abaixo), basta o caller passar o agente do perfil —
   o filtro e o cache já estão prontos.
3. **`_check_recurring_errors`** (`intersession_briefing.py:~505`, query `AgentSkillEffectiveness`)
   é GLOBAL e a tabela **não tem coluna `agente`** — ficou fora da fatia 2 (P2/defesa). Se
   for isolar, exige migration de coluna ou JOIN herdando agente da sessão.
4. **Cobertura do fallback de embeddings** (baixa): `test_fallback_isola_por_agente` faz
   `skip` em banco com pgvector (json.loads de objeto Vector falha por design — padrão
   herdado de `test_memory_search_cold_filter.py`). O filtro do fallback ESTÁ correto
   (idêntico em padrão ao pgvector, que é coberto); só não é exercitado no CI com pgvector.
5. **Isolamento de LISTAGEM/UI de sessão — superfície NOVA (achado do code-review app-wide).**
   A fatia 2 cobriu o caminho de **injeção no LLM**. As **rotas de UI** do agente WEB que
   LISTAM/operam sessões NÃO filtram por `agente` (`routes/sessions.py` list/messages/
   delete/rename/summaries; `routes/chat.py` get_or_create/idle-rotation; `routes/subagents.py`;
   `routes/feedback.py`). Hoje **mitigado**: (a) o fork lojas usa rotas próprias
   `/agente-lojas/*` que JÁ filtram `agente='lojas'` (air gap); (b) `session_id` é UNIQUE
   global → queries `filter_by(session_id=...)` (subagents/feedback/chat-rotation) pegam a
   sessão certa, agente é redundante ali. **Risco real**: um usuário DUAL (admin) abrindo
   a TELA web `/agente` veria também sessões `'lojas'` na listagem (`sessions.py` list/summaries).
   Não é injeção no LLM; é isolamento de visualização. Decidir com o dono: tratar junto de
   F3 (cliente unificado) OU item próprio de "isolamento de UI". NÃO corrigido nesta fatia
   (fora do escopo de injeção; muda comportamento de UI).
6. **Jobs de consolidação (pattern_analyzer) leem corpus cross-agente** — confirma o **P1**
   (escrita): `analyze_and_save`/`generate_and_save_profile` carregam sessões+correções do
   user sem filtrar agente e gravam padrões (default `'web'`). Seguro hoje (air gap; e a
   materialização M06 filtra na leitura). É o "particionar a ESCRITA" do P1.

### F3 — `AgentClient` parametrizado por perfil (GATED por F2 completo)
Ver `## FASE 3` do plano. Destravar 6 singletons (`get_settings` `@lru_cache`,
`AgentClient.__init__` injeção de settings, `get_client(agente_id)`, label do
briefing, `_discover_skills_from_project` allow-list, `agents=` filtrado a
`SUBAGENTS_PERMITIDOS`). Migrar `app/agente_lojas/` p/ `get_client('lojas')`;
aposentar o fork. **Reforçar D3 (fail-closed) no ponto de entrada do fork.**
Blast: 7 callsites em 3 produtos (web/Teams/WhatsApp) — por subsistema, nunca big-bang.

**Wiring de `agente_id` nos hooks (7º ponto, confirmado pelo review da fatia 2):**
`build_hooks(...)` (`hooks.py:~209`) NÃO recebe `agente_id` — por isso o
UserPromptSubmit hardcoda `agente_id='web'` ao chamar `_load_user_memories_for_context`
(`hooks.py:~1528`, by-design em F2) e os PreToolUse usam o default `'web'` de
`get_skill_reminders_for_session` / `_load_enforce_directives`. Em F3: `build_hooks`
recebe `agente_id` (do perfil), o UserPromptSubmit passa-o ao `_load`, e os 2 callers
PreToolUse (`hooks.py:185` skill reminders, `hooks.py:~425` enforce) passam-no também.
As FUNÇÕES já filtram e cacheiam por agente (fatia 2) — só falta a injeção do valor.

**KG na origem (P2/K01, não-bloqueante):** `query_graph_memories` (`knowledge_graph_service.py`)
filtra por `user_id` mas não por `agente` na busca primária (entities não têm coluna
`agente`). O vazamento prático JÁ é fechado fail-closed pela materialização M06
(`memory_injection.py:~1509`, fatia 1). Filtrar na origem exige migration de coluna em
`agent_memory_entities` = P2 (defesa em profundidade), conforme REVISÃO DE ESCOPO do plano.

## Decisões travadas
- **Corpus `user_id=0` por-agente, fail-closed** (memória empresa não vaza entre agentes).
- **Gate = identidade do agente (`AGENTE_ID`)**, não flag do `Usuario` (flag só autoriza endpoint; admin tem ambas).
- **`agente_id='web'` default em F2** (aditivo, não quebra os ~14 callers); fail-closed reforçado no ponto de entrada do fork em F3.
- **Núcleo P0 é zero-migration** (filtrar na materialização cobre embeddings+KG).

## Comandos de retomada
```bash
cd /home/rafaelnascimento/projetos/frete_sistema/.claude/worktrees/convergencia-agente-lojas
git rebase main                      # se a main avançou (integrar antes de tocar o web)
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
# baseline (rodar A PARTIR da worktree — caminhos: test_hook_budget esta em tests/agente/sdk/):
python -m pytest tests/agente_lojas/ tests/agente/sdk/test_memory_isolation_por_agente.py \
  tests/agente/test_memory_injection_fase3.py tests/agente/sdk/test_hook_budget.py \
  tests/embeddings/test_memory_search_agente_isolation.py -q   # 143 passed + 1 skip
```

## PROMPT + GATILHO para a nova sessão
> Cole o bloco abaixo ao iniciar a sessão limpa (Claude Code).

```
Continue a convergência agente_lojas ↔ agente web, na worktree dedicada
.claude/worktrees/convergencia-agente-lojas (branch worktree-convergencia-agente-lojas).

GATILHO (leia PRIMEIRO, nesta ordem):
1. docs/superpowers/plans/2026-06-29-convergencia-agente-lojas-handoff.md  (este handoff — estado + o que falta)
2. docs/superpowers/plans/2026-06-28-convergencia-agente-lojas.md  (plano; foco em §REVISÃO DE ESCOPO + Apêndice A)
3. app/agente_lojas/CLAUDE.md  (Gotcha 0 + Fases de evolução) e app/agente/CLAUDE.md

ESTADO: F0+F1 + **F2/M3 COMPLETA** (fatia 1 + fatia 2). TODAS as queries de memória
empresa/user do módulo isoladas por agente_id (default='web' aditivo): no caminho do
_load (M08-M12, R01, B01-B03, E01) E nos PreToolUse hooks (M13 skill_reminders +
_load_enforce_directives). 17 commits, 145 testes verdes + 1 skip. Review adversarial
4-dim feito. SEM push/merge (aguarda revisão 4-mãos).

OBJETIVO desta sessão: F2 P1/P2 (memory_mcp_tool + 7 jobs particionam a ESCRITA por
agente; migrations de defesa) e/ou F3 (AgentClient por perfil — destravar singletons +
WIRING de agente_id em build_hooks; migrar app/agente_lojas/ p/ get_client('lojas');
aposentar o fork). Ver "O que falta" + "Achados desta sessão" (UNIQUE constraint na
escrita, KG na origem P2). GATED: F3 só com F2 verde (está).

ANTES de codar: `git rebase main` (a main é ativa); rodar o baseline do handoff. NÃO
push/merge sem aval (revisão 4-mãos). Cada vetor = um commit TDD; default='web' mantém
o agente WEB (produção) intacto.
```
