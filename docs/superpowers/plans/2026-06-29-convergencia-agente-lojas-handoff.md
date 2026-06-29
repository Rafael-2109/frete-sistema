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

> ### ⚡ ATUALIZAÇÃO 2026-06-29 (sessão MOTOR ÚNICO — ETAPA 1+2+3a FEITAS, cutover PAUSADO)
>
> Esta sessão executou **ETAPA 1, ETAPA 2 e ETAPA 3a** do motor único (TDD por passo,
> web **byte-idêntico**). **+8 commits** sobre `main` (32 no total); worktree limpa;
> **gate `tests/agente/`+`tests/agente_lojas/` = 1691 passed, 40 skipped, 0 failed**.
> **SEM push/merge.** Commits desta sessão (do mais novo):
> ```
> baa70a9cd E3.8a — motor web serve perfil 'lojas' (loja_context + suprime hints Nacom)
> db68ca295 E2.7 — jobs de consolidacao gravam memoria pelo agente da sessao
> af941b9c3 E2.6 — memory_mcp_tool isola CRUD de memoria por agente
> 71892b4db E2.5 — rota web seta set_current_agent_id('web') no stream
> 1a2b0a77c E2.4 — build_hooks(agente_id) propaga aos 3 callers de injecao
> db7ae1bc0 E1.2 — AgentClient parametrizado por perfil (web byte-identico)
> da79b72e6 E1.1 — get_settings(agente_id) por perfil
> c9b1a38a2 fix(test): testes-guarda feature_flags reconhecem helper _env_bool (drift baseline)
> ```
> **O motor unificado está PRONTO para servir o perfil 'lojas'** (get_client('lojas')
> → settings/skills/agents/briefing/hooks/memória/loja_context isolados). Tudo INERTE
> em produção (default 'web'; nenhuma rota seta agente_id='lojas' ainda).
>
> **PAUSADO por decisão do dono (2026-06-29):** falta o **CUTOVER** (E3.8b: migrar a
> rota `/agente-lojas` p/ `get_client('lojas')` + aposentar o fork) e a **validação
> ponta a ponta** (E3.9). É a mudança de MAIOR risco (reescreve o path de stream do
> agente lojas em produção) — reservada p/ execução dedicada + revisão 4-mãos.
> **Plano detalhado do cutover: seção [## CUTOVER PENDENTE (E3.8b + E3.9)](#cutover-pendente-e38b--e39) abaixo.**

- **Worktree:** `.claude/worktrees/convergencia-agente-lojas` — branch
  `worktree-convergencia-agente-lojas`, rebaseada sobre `main` (2026-06-29,
  inclui Nubank OFX + `hora_recebimento_esperado`).
- **22 commits** sobre `main`; worktree limpa; **554 testes verdes + 1 skip** (suíte ampla).
- **SEM push, SEM merge** — aguarda revisão "4-mãos".
- **F2/M3 isolamento de LEITURA: COMPLETO** (fatia 1+2, 7 commits + 1 qualidade).
  Review adversarial 4-dim + code-review de completude app-wide (34 agentes):
  web-intacto ZERO achados; fontes PreToolUse fechadas; 2 itens de qualidade
  corrigidos (naming `agente_id`, `sid`/PK teste). Refutados: cache (session_id
  1:1 agente), hardcode 'web' (by-design).
- **Fase 1 (fundação de isolamento de ESCRITA + UI): PARCIAL — estrutural feito:**
  - `(user_id,path)` → `(user_id,path,agente)` (migration aplicada local; PROD
    seguro: 0 dup, 1019 mem todas 'web').
  - `create_file/create_directory/_ensure_parent_dirs(agente='web')` + ContextVar
    `_current_agent_id` (infra pronta; **wiring nas rotas/client é Fase 2/3**).
  - Rotas `/agente/api/sessions*` filtram `agente='web'` (corrige vazamento de
    VISUALIZAÇÃO p/ usuário dual admin — 11 sessões 'lojas' em PROD).
  - **MOVIDO p/ a sessão do motor único** (só ganham consumidor/wiring lá):
    `memory_mcp_tool` escrita+leitura por agente; jobs de consolidação
    (pattern_analyzer etc.) propagarem o agente da sessão de origem.

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

## PLANO DO MOTOR ÚNICO (próxima sessão — contexto cheio)

> Consolidado do design 2026-06-29 (workflow `design-convergencia-final`, 5 áreas
> mapeadas com file:line). É o "trocar o motor": fazer `app/agente_lojas/` reusar o
> `AgentClient` web por perfil e aposentar o fork. **Executar com contexto cheio**
> (toca o coração da produção: web/Teams/WhatsApp). Cada passo TDD, web byte-idêntico,
> sem push. Ordem por dependência:

**ETAPA 1 — Parametrizar o motor por perfil (web byte-idêntico, atrás de `agente_id='web'`):**
1. `config/settings.py` `get_settings()` `@lru_cache` → aceitar `agente_id` (chave de cache). `AgentLojasSettings` (`agente_lojas/config/settings.py`) já é o perfil pronto.
2. `sdk/client.py` `AgentClient.__init__(self, settings=None)` (fallback `get_settings()`); `get_client(agente_id='web')` com dict `_clients`; `_discover_skills_from_project(agente_id)` (web=deny-list, lojas=allow-list `SKILLS_PERMITIDAS`); `_build_options` `agents=` filtrado a `SUBAGENTS_PERMITIDOS` (lojas={orientador-loja}); label `empresa_briefing` por perfil.
3. **Provar: suíte `tests/agente/` 100% verde** (comportamento idêntico com default 'web').

**ETAPA 2 — Wiring de `agente_id` (liga o ContextVar + as fontes PreToolUse já preparadas):**
4. `sdk/hooks.py` `build_hooks(...)` recebe `agente_id`; propaga p/ `_load_user_memories_for_context` (hoje hardcoda 'web' em ~1528), `get_skill_reminders_for_session`, `_load_enforce_directives` (já filtram — só falta o valor).
5. Rotas setam `set_current_agent_id('web'|'lojas')` no início do stream (`permissions.py` ContextVar já existe).
6. `memory_mcp_tool` (13 ops): escrita (`save/update/delete/clear`) captura `get_current_agent_id()` → `create_file(..., agente=)`; leitura (`view/list/...`) usa `get_by_path_for_agent` / filtro `agente`. (Pré-req feito: `create_file(agente=)`, ContextVar, constraint.)
7. Jobs de consolidação (`pattern_analyzer.analyze_and_save/generate_and_save_profile`, `session_summarizer`, `memory_consolidator` agrupa por `(dir, agente)`) propagam o `AgentSession.agente` da sessão de origem p/ a memória gravada.

**ETAPA 3 — Migrar o fork e aposentar:**
8. `app/agente_lojas/` usa `get_client('lojas')` + `AgentLojasSettings`; injetar o `<loja_context>` (hoje no `scope_injector` do fork) como hook por perfil no motor unificado; aposentar `AgentLojasClient`/`client_pool` fork.
9. Validar contrato de isolamento (F2) + suíte `tests/agente_lojas/` + isolamento ponta a ponta (loja vê ZERO Nacom). Reforçar fail-closed no ponto de entrada.
10. **NÃO migrar Teams/WhatsApp** (continuam 'web' por default — fora do escopo do "final").

**Migration pendente (rodar em PROD no deploy):** `2026_06_30_constraint_agente_memoria.py` (constraint já aplicada no banco LOCAL; PROD aplica no deploy junto do código). Considerar tb migrations P2 de coluna `agente` em `agent_memory_embeddings`/`agent_memory_entities` (defesa do KG/embeddings na origem — hoje coberto por M06/materialização).

## CUTOVER PENDENTE (E3.8b + E3.9)

> **O QUE FALTA do motor único.** A INFRA (ETAPA 1+2+3a) está pronta, testada e
> byte-idêntica. Falta só LIGAR a rota lojas ao motor e aposentar o fork. É a
> mudança de MAIOR risco (path de stream do agente lojas em PRODUÇÃO). Recomendação:
> **fazer atrás de flag canary `AGENT_LOJAS_USA_MOTOR_UNICO` (default OFF)** para
> cutover reversível, validar em canary, e só então aposentar o fork.

### Pré-requisitos JÁ PRONTOS (não refazer)
- `get_client('lojas')` → `AgentClient` com `AgentLojasSettings` (model/prompts próprios,
  `empresa_briefing_path=''` ⇒ sem briefing Nacom), skills allow-list (`SKILLS_PERMITIDAS`),
  agents só `{orientador-loja}` (`client.py` E1.2).
- `build_hooks(agente_id='lojas')` injeta memória/skill-reminders/enforce isolados por
  `agente='lojas'` (E2.4) + `<loja_context>` via `_current_loja_scope` (E3.8a) + suprime
  hints SQL Nacom no PreToolUse (E3.8a).
- ContextVars em `app/agente/config/permissions.py`: `set_current_agent_id('lojas')`,
  `set_loja_scope(perfil, loja_hora_id)` (+ `clear_*` no finally).
- `memory_mcp_tool`/jobs gravam/leem por `get_current_agent_id()` (E2.6/E2.7).

### E3.8b — migrar `app/agente_lojas/routes/chat.py` ao motor unificado
1. No início do stream (dentro do worker, antes de chamar o motor), setar:
   `set_current_session_id(our_session_id)`, `set_current_user_id(user_id)`,
   `set_current_agent_id('lojas')`, `set_loja_scope(perfil, loja_hora_id)`,
   `set_event_queue(our_session_id, event_queue)`. No `finally`: `clear_current_agent_id()`,
   `clear_loja_scope()`, `cleanup_session_context`.
2. Trocar `stream_lojas_chat()` (`routes/chat.py:161`, `_drain_async_gen`) por
   `get_client('lojas').stream_response(prompt=..., user_id=..., user_name=...,
   our_session_id=..., sdk_session_id=..., can_use_tool=<lojas can_use_tool>,
   output_format=..., stderr_queue=...)` (assinatura web em `app/agente/sdk/client.py:1461`).
   - **`can_use_tool`**: passar o do fork (`app/agente_lojas/config/permissions.py:143`,
     preserva `_DANGEROUS_BASH_PATTERNS` HORA `delete from hora_*` + Write→/tmp). É param
     de `stream_response`/`_build_options` — NÃO precisa migrar para o motor (R4 do MAPA_A5).
3. **Serializar `StreamEvent` → SSE**: o motor web emite `StreamEvent` (dataclasses,
   `stream_parser.py`); o fork emitia dicts via `_parse_message`. Espelhar a serialização
   de `app/agente/routes/chat.py` (`async_stream`, ~:965+). Os frontends usam o MESMO
   pattern SSE (CLAUDE.md agente_lojas Gotcha 3) — type: text/tool_call/tool_result/
   thinking/done/error. VALIDAR campo a campo contra `templates/agente_lojas/chat.html`.
4. Persistência pós-stream: reusar o padrão do fork (`_persist_session_after_stream`,
   `routes/chat.py:414`) — custo delta via `turn_cost_from_cumulative`, cap 50 msgs,
   `agente='lojas'` já setado.
5. **Aposentar o fork** (só após canary validado): `sdk/client.py` (AgentLojasClient),
   `sdk/client_pool.py`, `sdk/hooks.py`, `sdk/__init__.py` (re-exports). **MANTER**:
   `services/scope_injector.py` (reusado pelo hook do motor), `config/{settings,
   skills_whitelist,permissions}.py` (config-do-perfil + can_use_tool), `routes/{sessions,
   health,user_answer}.py`, `decorators.py`, `templates/`, `prompts/`.

### E3.9 — validação ponta a ponta
- Suíte `tests/agente_lojas/` (34 testes) — alguns testam o fork direto (`test_resume_build_options`,
  `test_build_options_env`, `test_sdk_error_handling`): ATUALIZAR p/ o motor ou aposentar junto.
- Teste de isolamento ponta a ponta: sessão `'lojas'` → memória gravada `agente='lojas'`,
  `<loja_context>` presente, ZERO conteúdo Nacom (skills/agents/hints/memória). Reforçar
  fail-closed no ponto de entrada (perfil derivado da rota, não inferido).
- Revisão adversarial final (web-intacto + isolamento lojas).
- Migration `2026_06_30_constraint_agente_memoria` aplica em PROD no deploy (já no working tree).

### Riscos conhecidos (MAPA_A5 §11) — status
- R1 memória cross-agente: **RESOLVIDO** (E2.4/E2.6). R2 skills: **RESOLVIDO** (E1.2 allow-list).
  R3 briefing vazio: **RESOLVIDO** (E1.2 guard `empresa_briefing_path=''`). R5 enforce: **RESOLVIDO** (E2.4).
- R4 Bash patterns HORA: resolver passando o `can_use_tool` do fork ao `stream_response` (E3.8b passo 2).

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
Falta SÓ o CUTOVER da rota lojas — a INFRA do motor único já está pronta e testada.

GATILHO (leia PRIMEIRO, nesta ordem):
1. docs/superpowers/plans/2026-06-29-convergencia-agente-lojas-handoff.md
   — §"ATUALIZAÇÃO 2026-06-29" (estado) + §"CUTOVER PENDENTE (E3.8b + E3.9)" (plano com file:line).
2. app/agente_lojas/CLAUDE.md (Gotcha 0 + Fases) e app/agente/CLAUDE.md.

ESTADO: MOTOR ÚNICO ETAPA 1+2+3a ✅ (8 commits, gate tests/agente+tests/agente_lojas
= 1691 passed / 40 skip / 0 fail, web BYTE-IDÊNTICO). get_client('lojas') já produz
settings/skills/agents/briefing/hooks/memória/<loja_context> isolados; tudo INERTE em
produção (default 'web'). SEM push/merge (revisão 4-mãos).

OBJETIVO desta sessão: o CUTOVER (§CUTOVER PENDENTE do handoff). Recomendado atrás de
flag canary `AGENT_LOJAS_USA_MOTOR_UNICO` (default OFF): (E3.8b) rota /agente-lojas
(app/agente_lojas/routes/chat.py) seta set_current_agent_id('lojas')+set_loja_scope e
chama get_client('lojas').stream_response(...) com o can_use_tool do fork; serializa
StreamEvent→SSE espelhando app/agente/routes/chat.py; aposenta AgentLojasClient/
client_pool/hooks/__init__ do fork (MANTÉM scope_injector/config/sessions/health/
templates/prompts). (E3.9) suíte tests/agente_lojas/ + teste de isolamento ponta a ponta
(loja vê ZERO Nacom) + revisão adversarial. NÃO migrar Teams/WhatsApp (ficam 'web').

ANTES de codar: `git rebase main` (a main é ativa); rodar o baseline. É o coração da
produção — TDD por passo, commit TDD. NÃO push/merge sem aval (revisão 4-mãos). Migration
`2026_06_30_constraint_agente_memoria` aplica em PROD no deploy.
```
