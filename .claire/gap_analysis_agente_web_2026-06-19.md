# Gap Analysis — Agente Web (`app/agente`) vs Claude Agent SDK 0.2.101

> **Data**: 2026-06-19 · **Escopo**: capacidades existentes na versão instalada (claude-agent-sdk 0.2.101, CLI bundled 2.1.177, anthropic 0.109.1) e subsistemas já construídos, **não wired/ligados** no agente web.
> **Método**: 2 varreduras multi-agente (eixo interno: introspecção do pacote + código + flags + planos; eixo documental: doc oficial Anthropic + context7 + release notes), com reconciliação adversarial contra `SDK_CHANGELOG.md`, planos posteriores e estado real. Claims de maior ROI re-verificados diretamente (introspecção + grep).
> **Regra aplicada**: nada listado aqui é "pendência" sem reconciliar — 16 candidatos foram descartados (§9) por já estarem feitos/ligados/recusados conscientemente.

> **⚠️ Correção pós-execução (2026-06-19) — Bloco A aplicado.** Ao reabrir a fonte para corrigir, 2 itens deste relatório se mostraram imprecisos:
> 1. **`TaskBudget` NÃO era drift.** O `SDK_CHANGELOG.md:777/995` já diz corretamente *"campo já existe em `ClaudeAgentOptions` ... NÃO usado"*. Existe e é não-adotado — o changelog estava certo. Não foi alterado. (Continua válido como oportunidade não-adotada — §5.)
> 2. **ROADMAP NÃO estava em ~90%.** Verificação direta: `_with_resume()` permanece (`client.py:2823`), DC-1/4.5 e remoção da flag (5.1) pendentes → o status "60%, Fases 4-5 pendentes" estava substancialmente correto. Só o dead-code v2 (`_stream_response`/`_make_streaming_prompt`) havia sido deletado (2026-04-04) sem o roadmap registrar — corrigido como 4.2 ✅ / 5.2 ◑ parcial, sem reescrever o status para "concluído".
> 3. **Bônus encontrado na execução:** a linha `fork_session ... NÃO usadas` do changelog também estava drifada — `fork_session_via_store()` está em prod (`sessions.py:436` + UI). Corrigido.
> **Itens efetivamente corrigidos no Bloco A:** `get_context_usage` (→ IMPLEMENTADO), `list_subagents`/`get_subagent_messages` (→ ADOTADO), `fork_session` (→ ADOTADO via store), `tag_session` (→ recusa registrada), ROADMAP 4.2/5.2.

---

## 1. Resumo executivo

O módulo é maduro e a maioria dos "gaps" óbvios já foi avaliada e recusada com racional. O sinal real está concentrado em **4 frentes**:

1. **Dívida de reconciliação documental (S, risco nulo)** — 4 docs afirmam o oposto do código: `SDK_CHANGELOG.md` marca `get_context_usage`/`list_subagents` como "não implementado/não adotado" (estão wirados) e `TaskBudget` como "não implementado" (**existe** — verifiquei). `ROADMAP_SDK_CLIENT.md` diz 60%/Fases 4-5 pendentes (o `query()` legado já foi removido). É exatamente o drift que custa retrabalho.
2. **Custo direto (alto ROI)** — completar `cache_control` nos 5 jobs shadow que rodam sem cache; **Message Batches API (-50%)** nesses mesmos jobs; cache TTL 1h (a avaliar); effort-downgrade em turno trivial (alavanca já existe).
3. **Observabilidade operacional ausente** — `get_mcp_status()` nunca lido (10 MCP servers, zero health-check, e MCP virou non-blocking por default no 0.2.82); `RateLimitEvent` emitido mas nunca persistido; breakdown de `ContextUsageCategory` jogado fora.
4. **1 correção de wiring com prod LIVE** — DC-1: globals do Playwright colidem no daemon thread único multi-sessão.

O eixo "Nativo vs Custom" (memory tool, session metadata, permission hook, context editing) confirma: **o app resolve melhor com infra própria** (pgvector, Postgres, `can_use_tool`). Não migrar — no máximo complementar.

---

## 2. Bloco 0 — Dívida de reconciliação documental (fazer já, 1 sessão, risco nulo)

> Subsistema/feature já existe; o **doc** mente. Corrigir o doc, não o código. Custo S, zero runtime.

| Item | Doc (afirma) | Realidade (prova) | Ação |
|---|---|---|---|
| `get_context_usage` | `SDK_CHANGELOG.md:997` "NÃO implementado" | wirado nas 3 camadas: `client.py:461-502` → `routes/chat.py:1311-1313` → `chat.js:5112-5147`; método confirma em `ClaudeSDKClient.get_context_usage` (introspecção) | Atualizar changelog:997 → "wired client→routes→done→chat.js" |
| `list_subagents`/`get_subagent_messages` | `SDK_CHANGELOG.md:978` "NÃO adotado" (contradiz a própria linha 1011) | em uso: `admin_subagents.py:240,286-347`, `subagent_reader.py:22`, `session_search_tool.py:798,825` | changelog:978 → ADOTADOS |
| `task_budget`/`TaskBudget` | `SDK_CHANGELOG.md:777,802,995` "NÃO implementado" | **`TaskBudget` existe em 0.2.101** (introspecção: `hasattr=True`). É "não-adotado", não "inexistente" | Corrigir o changelog: existe e é não-adotado (ver §5) |
| Migração `query()`→`ClaudeSDKClient` | `ROADMAP_SDK_CLIENT.md:64-67,583` "≈60%, Fases 4-5 pendentes" | path `query()` removido (`client.py:2816-2818`); JSONL superseded por `PostgresSessionStore` (`session_persistence.py:3-13`) | Marcar 5.2 concluída, 4.3/4.4 superseded-por-SessionStore, status ~90%, único item vivo = DC-1 |
| `tag_session`/`rename_session` | sem nenhuma ocorrência no changelog (gap silencioso) | zero uso em `app/agente`; `rename` via DB próprio (`sessions.py:204`) | Avaliar e **registrar** a recusa consciente (metadados DB-nativos são mais ricos) — fecha o último gap não-reconciliado |

---

## 3. Bloco 1 — Custo direto (alto ROI)

| Oportunidade | Estado atual (arquivo:linha) | Ação | Esforço | Risco |
|---|---|---|---|---|
| **`cache_control` ausente nos 5 jobs shadow** | `step_judge.py:70`, `plan_verifier.py:68`, `subagent_validator.py:49`, `verifiers.py:51`, `plan_triage.py:81` — todos `anthropic.Anthropic().messages.create()` síncrono com system-prefixo FIXO e **sem** `cache_control` (verificado) | Adicionar `cache_control:{type:'ephemeral'}` no bloco system fixo (−90% no read). Padrão já usado em 8 arquivos | S | baixo |
| **Message Batches API (−50%)** nos jobs shadow | mesmos 5 callsites; perfil "pode esperar" (calibração/flywheel, fora do hot-path do usuário) | Migrar para `messages.batches` (0.109.1). **Ressalva**: o `subagent_validator` é anti-alucinação — só mandar p/ batch se for puramente shadow/calibração; se vira alerta operacional, latência (até 24h) degrada utilidade. Os outros 4 são seguros | M | baixo |
| **`AGENT_WARM_EFFORT_DOWNGRADE`** (effort `high`→`low` em turno trivial de sessão Opus quente) | `chat.js:367` força `high` p/ Opus; `client.py:1724` aplica; classificador trivial **já existe** (`model_router.py:72-100`), `pick_warm_model:243-270` não toca effort | Flag OFF→shadow: sessão quente + prompt trivial ⇒ baixar effort **sem trocar modelo** (preserva o cache MODEL-SCOPED). Medir delta de thinking-tokens, depois promover | S | baixo |
| **Cache TTL 1h (`ENABLE_PROMPT_CACHING_1H`)** | bloco `env` existe (`client.py:1611`, hoje só 1 var); `_alert_cache_miss` (`client.py:168`/`:1332`) já mede o desperdício | **Avaliar/medir antes de ligar.** Documentado pela Anthropic, mas: (a) **não confirmei** suporte no CLI bundled 2.1.177 localmente; (b) cache-write de 1h custa ~2x base (vs 1.25x p/ 5min) — só compensa se houver reuso entre 5–60min. Forte candidato p/ **Teams** (sessões espaçadas, system ~16.6K estático). Teste: 1 sessão com a flag + ler `cache_creation_input_tokens` na `ResultMessage` | S (se suportado) | médio |

---

## 4. Bloco 2 — Observabilidade operacional (M, baixo risco — agrupar: mesma área `routes/chat.py` + init)

| Oportunidade | Estado atual (arquivo:linha) | Ação | Valor |
|---|---|---|---|
| **`get_mcp_status()` nunca lido** | `client.py:1862-1935` registra 10 MCP servers, zero leitura de status; `SDK_CHANGELOG.md:297` admite que a validação atual não detecta o failure mode. **Método existe** (`ClaudeSDKClient.get_mcp_status` = True, verificado) | Após init, chamar `get_mcp_status()`; WARN se algum `!= connected`; painel admin opcional reusando `admin_session_store` | alto (MCP é non-blocking por default desde 0.2.82 — falha silenciosa hoje) |
| **`RateLimitEvent` emitido mas nunca persistido** | `client.py:1033-1060` parseia e emite StreamEvent; `chat.js:2451-2461` só mostra toast; persistência = zero | Persistir linha leve (ts, status, utilization, rate_limit_type, user_id, channel) no padrão `AgentInvocationMetric`; agregar no admin. Best-effort/try-except | médio (saúde Anthropic hoje some no toast) |
| **`ContextUsageCategory` breakdown descartado** | `client.py:486-503` colapsa em used/total/percent; o SDK retorna `categories[]`/`memoryFiles`/`mcpTools`/`agents`/`systemPromptSections`/`skills`/`messageBreakdown` | Preservar o breakdown no `done_payload`; mostrar qual categoria domina a janela em sessões longas (admin/insights) | médio (governança de prompt FASE 5 + injeção multi-tier — saber QUAL categoria consome é acionável p/ poda) |

---

## 5. Bloco 3+4 — Wiring LIVE + features SDK de valor médio (avaliar)

| Oportunidade | Estado atual (arquivo:linha) | Ação | Esforço | Risco |
|---|---|---|---|---|
| **DC-1: Playwright globals colidem no daemon multi-sessão** (wiring, prod LIVE) | `playwright_mcp_tool.py:57` (`_page` global), `:62` (`threading.local()`); `client_pool.py:172-215` (daemon thread ÚNICO via `run_coroutine_threadsafe`); `USE_PERSISTENT_SDK_CLIENT` ON | Dict `_pages` keyed por `session_id` + `ContextVar _current_frame` (confirmar `permissions.py:46 _current_session_id` antes). Único item da Fase 4 genuinamente não-feito | M | médio |
| **`task_budget`/`TaskBudget` por subagente Opus xhigh** | só `max_budget_usd` global por-request ($5, `client.py:1790`); zero uso de TaskBudget (existe em 0.2.101) | Flag `AGENT_TASK_BUDGET` (OFF) via `dataclasses.replace` forward-compat; **profiling de tokens/subagente primeiro**, depois fixar teto. Capa o pior caso de runaway nos 8 subagentes xhigh | M | médio |
| **`DeferredToolUse` (par do ToolSearch)** | ToolSearch ligado (`settings.py:88`, `stream_parser.py:148`), mas o ciclo `DeferredToolUse` não é tratado | Avaliar fechar o ciclo (carregar tools sob demanda) — alinhado ao budget de descrições de skills (deny-list a 25) | M | baixo |
| **Hook `Notification` → Teams/push** | `build_hooks` registra 8 eventos; `NotificationHookInput` disponível, não usado | Forward de `idle_prompt`/`permission_prompt`/`auth_success` p/ Teams/push (relevante p/ AskUserQuestion em canal assíncrono) | M | baixo |
| **Structured output: `error_max_structured_output_retries`** | core wirado (`chat.py:203`→`client.py:1758`→`:1383`), mas backend só trata SUCESSO | Tratar a falha de retries (hoje vira saída vazia silenciosa) + `model_validate` Pydantic nos fast-paths deterministicos | S | baixo |
| **`effort: xhigh` no agente principal** | já em 8 subagentes; o seletor do principal não oferece `xhigh` | Expor no seletor (opcional; Opus 4.7/4.8 suportam) | S | baixo |

---

## 6. Nativo vs Custom — decisão por item

| Nativo Anthropic | App reimplementa | Veredito | Razão |
|---|---|---|---|
| **Memory tool** (`memory_20250818`) | `AgentMemory` + `memory_mcp_tool.py` (13 ops) + pgvector + escopo + KG + decay + PII + inbox | **MANTER custom** | Nativo é menos capaz; migrar = regressão |
| **Session metadata** (`tag_session`/`get_session_info`) | `PostgresSessionStore` + `AgentSession.title/summary` (SOT) | **MANTER custom** | DB filtra mais rápido que parse de JSONL |
| **Permission via hook** (`PermissionRequest`) | `can_use_tool` (`permissions.py:498`, async, agent_id-aware, Redis) | **MANTER custom** | Callback é mais expressivo que hook declarativo |
| **Session summary fold** (`fold_session_summary`) | `session_summarizer.py` + coluna `summary` | **MANTER custom** | `list_session_summaries` nem é top-level em 0.2.101 |
| **Structured output** (`output_format`) | já wirado end-to-end | **COMPLEMENTAR** (ver §5: retries) | core ok, falta tratar falha |
| **Context editing granular** (`context_management`) | só a GA via CLI (`USE_CONTEXT_CLEARING`) | **COMPLEMENTAR quando o SDK expuser** | `context_management` **não** é campo de `ClaudeAgentOptions` 0.2.101 (só API-direct). `exclude_tools` preservaria SQL/schema enquanto limpa screenshots base64 |
| **Cost tracking / cache TTL** (`ENABLE_PROMPT_CACHING_1H`) | mede miss, não seta TTL | **COMPLEMENTAR (avaliar, §3)** | resolve o cenário que o próprio alerta detecta |

---

## 7. O que um bump do SDK destravaria (não está em 0.2.101)

| Item | Estado em 0.2.101 | Bump destravaria |
|---|---|---|
| Hooks `SessionStart`/`SessionEnd`/`StopFailure` | string no CLI 2.1.177, **ausentes do `HookEvent` Literal tipado** (registráveis só por string-key frágil) | registro tipado/seguro de teardown e erro-por-tipo (lugar canônico p/ archive S3 + consolidação — hoje roda no `_stop_hook` a cada turno) |
| `context_management` granular (`clear_tool_uses`/`exclude_tools`/`keep`/`trigger`) | **não** é campo de `ClaudeAgentOptions` (só API-direct) | context editing granular dentro do loop do Agent SDK |
| `list_session_summaries()` top-level | só método opcional de `SessionStore` | protocolo importável de leitura de resumos in-SDK |

> `betas`/`SdkBeta` **existe** em 0.2.101 e é o canal limpo p/ opt-in de betas futuras (sem `extra_args`) — sem beta relevante ativo hoje (1M virou GA).

---

## 8. Precisa confirmar em prod antes de agir (`needs_prod_check`)

| Item | Confirmar | Onde |
|---|---|---|
| `ENABLE_PROMPT_CACHING_1H` | suporte real no CLI bundled 2.1.177 (teste: medir `cache_creation_input_tokens`) | §3 |
| Flags shadow judge/verify/triage | estado real em prod (dossier diz ON, código default OFF). **GATE-1 já cumprido 2026-06-12**; se ON, rodar GATE-2 ≥1 semana. NÃO promover a runtime sem concordância ≥80% | `feature_flags.py:1073/1084/1089`; `EXECUCAO.md:506` |
| `USE_USER_XML_POINTER` (G-F4) | **provável no-op** — `AGENT_FIXED_BLOCKS_CAP` (ON) já destila user.xml; plano 2026-06-09 (F6) já cobre o overflow | `memory_injection.py:1601-1627` |
| `USE_RECURRENCE_SCORE` | quantas `AgentMemory` têm `correction_count≥1` (gate de dados; adicionar gatilho de re-visita senão vira zumbi) | `feature_flags.py:672` |
| `USE_IMPROVEMENT_DIALOGUE` | ligar canary (~$0.005/sessão) e revisar qualidade da inbox antes de `INJECT_BOOT` | `feature_flags.py:622` |

---

## 9. Conscientemente fora de escopo (reconciliado, NÃO ignorado)

- **`fork_session` "sem UI"** — FALSO: UI 100% wirada (`chat.js:3697-3780`); finder grepou dir errado.
- **A4 promoção shadow→ativa** — FALSO: `approval_inbox_service.py:65-67` + rotas `memories.py:438-466` + `memorias.html` cobrem.
- **Capability Registry "sem consumidor"** — FALSO: `context_enrichment.py:44,75` consome.
- **Skill-RAG (F4/F5) + World Model (D5) "OFF"** — FALSO: ambos ON em prod (`EXECUCAO.md:258-259`).
- **`AGENT_SKILL_EVAL` "divergência"** — ON em prod desde 2026-06-07 (env tem precedência sobre default OFF).
- **Calibration Sampler (GATE-1)** — cumprido 2026-06-12, 100% deployado.
- **`include_hook_events`** — recusa consciente (`SDK_CHANGELOG.md:687`); stream poluído.
- **`include_partial_messages`** (token-a-token) — adiar: multiplica frames SSE; mesmo racional do `include_hook_events`. Validar custo SSE antes.
- **`TaskUpdatedMessage` (#1016)** — recusado (`SDK_CHANGELOG.md:36-42`); reavaliar só com hang real de subagente em TERMINAL.
- **`fold_session_summary`** (compactação JSONL) — recusado (`SDK_CHANGELOG.md:867`); `AgentSession.summary` DB-native cobre.
- **`DeferredToolUse` + defer permission (F2)** — recusado (`SDK_CHANGELOG.md:690`); register_question cobre ~95% (distinto do ciclo de tool-loading do §5).
- **`sandbox`/`plugins`/`enable_file_checkpointing`** — sandbox e plugins recusados (`:772`,`:430`); checkpointing inútil (agente raramente edita arquivo, `/rewind` é TTY).
- **`max_thinking_tokens`** — aposentado por `effort` (`SDK_CHANGELOG.md:1005`); app usa thinking adaptive.
- **Memory tool / Token Counting / `exclude_dynamic_sections`** — nativo inferior ao custom / útil só offline / inaplicável (app usa system_prompt STRING + `USE_PROMPT_CACHE_OPTIMIZATION` já faz equivalente).
- **Prompt cache TTL/cache_control no caminho principal** — já ~82% hit; cache_control não exposto no path do SDK (rejeitado plano 2026-06-06).

---

## 10. Sequência recomendada (valor × confiança ÷ risco)

**Bloco A — Reconciliação documental (S, risco nulo) — 1 sessão:**
Corrigir `SDK_CHANGELOG.md` (997, 978, 777/802/995-TaskBudget) + `ROADMAP_SDK_CLIENT.md` (Fase 5.2/4.x) + registrar `tag_session` como recusa. Elimina retrabalho; é a regra de ouro em ação.

**Bloco B — Custo barato e seguro:**
`cache_control` nos 5 jobs shadow → `AGENT_WARM_EFFORT_DOWNGRADE` em shadow → medir → promover.

**Bloco C — Custo com avaliação:**
Message Batches nos 4 jobs shadow seguros (validador à parte) → avaliar `ENABLE_PROMPT_CACHING_1H` em Teams (teste de cache_creation antes).

**Bloco D — Observabilidade (agrupar, mesma área):**
`get_mcp_status()` pós-init + persistir `RateLimitEvent` + breakdown `ContextUsageCategory` no done_payload.

**Bloco E — Wiring LIVE:**
DC-1 Playwright (`_pages` dict + ContextVar).

**Bloco F — Avaliar com dados:**
`task_budget` (profiling primeiro) · structured-output retries · Notification→Teams · DeferredToolUse ciclo.

**Adiar:** `include_partial_messages`, `TaskUpdatedMessage`, `fold_session_summary`, sandbox, gates de dados shadow (canary cauteloso).

---

### Arquivos-chave para execução

`app/agente/sdk/client.py` (env/cache, rate_limit, context_usage, mcp registro, effort, max_budget) · `sdk/model_router.py` (classificador trivial) · `sdk/cost_tracker.py` (get_session_cost) · `tools/playwright_mcp_tool.py` (DC-1) · `sdk/client_pool.py` (daemon único) · `workers/{step_judge,plan_verifier,subagent_validator}.py` + `sdk/{verifiers,plan_triage}.py` (batch + cache_control) · `static/agente/js/chat.js` (effort, context_usage, rate_limit) · `SDK_CHANGELOG.md` + `.claude/references/ROADMAP_SDK_CLIENT.md` + `docs/blueprint-agente/EXECUCAO.md` (reconciliação).
