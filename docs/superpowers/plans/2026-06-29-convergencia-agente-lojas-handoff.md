<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-29
-->
# Convergência Agente Lojas ↔ Web — HANDOFF (retomar F2 fatia 2 → F3)

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
crash, ✅) → F2/M3 (isolar memória por `agente_id`, fail-closed) → F3 (client
parametrizado por perfil). Esta sessão (2026-06-29) entregou F0+F1 + a fatia 1
de F2; este doc é o estado vivo para retomar a fatia 2 e F3.

## Estado atual

- **Worktree:** `.claude/worktrees/convergencia-agente-lojas` — branch
  `worktree-convergencia-agente-lojas`, rebaseada sobre `main` (2026-06-29).
- **9 commits** sobre `main`; worktree limpa; **96 testes verdes** (F0+F1+F2-fatia1).
- **SEM push, SEM merge** — aguarda revisão "4-mãos".

```
000fcee7d feat(agente-mem): F2/M3 fatia 1 — isola memória injetada por agente (6 queries)
802efbbe1 docs(plano): Task 2.0 executada — revisão de escopo de F2 (gate disparou)
df90c0d1e feat(agente-lojas): session_id no turno 1 (aditivo) + limpa briefing morto
44faf1473 fix(agente-lojas): NACOM_QUIET_BOOT no PreToolUse
5f250cae9 fix(agente-lojas): handlers de erro SDK especializados
72ee57cad refactor(agente-sdk): extrai sdk_compat.check_skills_option (web + lojas)
864dccfeb refactor(agente-sdk): extrai sdk_runtime.build_subprocess_env (web + lojas)
17fe669b4 fix(agente-lojas): env dict (HOME=/tmp + STREAM_CLOSE_TIMEOUT=240s)
8fa5163d7 docs(plano): convergência agente_lojas ↔ agente web (híbrido faseado F0-F3)
```

## O que foi entregue

| Fase | Estado | Resumo |
|---|---|---|
| **F0** env dict | ✅ | `HOME=/tmp` + `STREAM_CLOSE_TIMEOUT=240s` no fork — corrige risco de crash no Render. |
| **F1** infra compartilhada | ✅ | Extrai `sdk_runtime.build_subprocess_env` + `sdk_compat.check_skills_option` (web+lojas, sem copiar); handlers de erro SDK; `NACOM_QUIET_BOOT`; `session_id` turno-1 aditivo; `empresa_briefing_path` morto limpo. **F1.5(b)** `agents=` explícito ADIADO p/ F3 (será via `agent_loader` parametrizado; `setting_sources=['project']` cobre `orientador-loja` hoje). |
| **F2/M3** memória | 🟡 fatia 1 | `_load_user_memories_for_context(..., agente_id='web')` + filtro `AgentMemory.agente == agente_id` em **6 queries**: Tier 1 (M01), 1.5 (M02), 1.6 (M03), materialização Tier 2 (M05), KG (M06), fallback (M07). Hook web (`hooks.py`) passa `'web'` explícito. Teste-contrato `tests/agente/sdk/test_memory_isolation_por_agente.py` (via IDs injetados). **Zero-migration.** `default='web'` ⇒ web inalterado. |

## O que falta (acionável)

### F2/M3 — fatia 2 (mesmo padrão da fatia 1: propagar `agente_id`, filtrar, `default='web'`)
Funções que ainda **não** filtram por agente (ver `Apêndice A` do plano; confirmar
file:line com `grep -n "AgentMemory.query\|AgentSession.query" app/agente/sdk/memory_injection.py`,
pois as linhas deslocaram após a fatia 1):

1. **`_build_operational_directives_parts`** (M10, memória empresa `user_id=0` — **fonte crítica de heurística Nacom**). Recebe `agente_id`, filtra.
2. **`_build_session_window`** (M08/M12, `AgentSession.agente == agente_id`).
3. **`_load_resolved_pendencias`** → **`AgentMemory.get_by_path`** (M09/H01) — criar `get_by_path_for_agent(user_id, path, agente)` (NÃO quebrar a assinatura atual — há outros callers).
4. **`_build_user_rules`** / `_get_user_rule_ids` (R01, `app/agente/sdk/memory_injection_rules.py`).
5. **`build_intersession_briefing`** (B01-B03, `app/agente/services/intersession_briefing.py`) — propagar `agente_id` (default `'web'`); 3 callers extras (route `briefing.py`, testes).
6. **`buscar_memorias_semantica`** / `_search_memories_pgvector` (E01, `app/embeddings/service.py:855` JOIN) — `AND m.agente = :agente_id`. (M05 já cobre por defesa na materialização; o JOIN é otimização + 2ª camada.)
7. Queries restantes M11/M13 no `_load()`.

**Aceite:** estender `test_memory_isolation_por_agente.py` com casos de directives + session_window + briefing; provar que sessão `lojas` vê ZERO conteúdo `web` em cada fonte.

### F2/M3 — P1/P2 (só pós-F3 — o fork tem air gap, não usa memória nem memory tools)
- **P1:** `memory_mcp_tool` (13 ops, gravar/filtrar por agente) + 7 jobs de consolidação (`insights_service`, `pattern_analyzer`, `directive_promotion`, `memory_consolidator`...) — particionar na escrita.
- **P2 (defesa extra):** migrations de coluna `agente` em `agent_memory_embeddings` + KG entities; `world_model`/`ontology_query` (N05) por perfil.

### F3 — `AgentClient` parametrizado por perfil (GATED por F2 completo)
Ver `## FASE 3` do plano. Destravar 6 singletons (`get_settings` `@lru_cache`,
`AgentClient.__init__` injeção de settings, `get_client(agente_id)`, label do
briefing, `_discover_skills_from_project` allow-list, `agents=` filtrado a
`SUBAGENTS_PERMITIDOS`). Migrar `app/agente_lojas/` p/ `get_client('lojas')`;
aposentar o fork. **Reforçar D3 (fail-closed) no ponto de entrada do fork.**
Blast: 7 callsites em 3 produtos (web/Teams/WhatsApp) — por subsistema, nunca big-bang.

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
# baseline:
python -m pytest tests/agente_lojas/ tests/agente/sdk/test_memory_isolation_por_agente.py \
  tests/agente/test_memory_injection_fase3.py tests/agente/test_hook_budget.py -q
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

ESTADO: F0+F1 completos; F2/M3 fatia 1 feita (6 queries de memória direta isoladas
por agente_id, default='web' aditivo, teste-contrato verde). 9 commits, 96 testes.

OBJETIVO desta sessão (TDD, default='web' aditivo, estendendo o teste-contrato):
- F2/M3 fatia 2: propagar agente_id e filtrar em _build_operational_directives_parts
  (M10), _build_session_window (M08/M12), _build_user_rules (R01),
  build_intersession_briefing (B01-B03), buscar_memorias_semantica JOIN (E01),
  get_by_path (M09/H01). Aceite: sessão 'lojas' vê ZERO conteúdo 'web' em cada fonte.
- Depois F2 P1/P2 (memory_mcp_tool + jobs; migrations defesa) e F3 (client por perfil, gated).

ANTES de codar: `git rebase main` (a main é ativa — integrar antes de tocar o web);
rodar o baseline do handoff. NÃO push/merge sem aval (revisão 4-mãos).
Cada vetor = um commit TDD; o agente WEB é produção — default='web' mantém-no intacto.
```
