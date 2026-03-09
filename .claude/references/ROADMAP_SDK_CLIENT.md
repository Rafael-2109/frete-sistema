# Migração: query() → ClaudeSDKClient — ROADMAP VIVO

> **Última atualização**: 2026-03-09
> **Status geral**: EM PROGRESSO
> **Progresso**: ██████░░░░ 60% (Fase 0 ✅ + Fase 1 ✅ + Fase 2 ✅ + Fase 3 ✅)
> **POC**: CONCLUÍDA (2.15x speedup) — `scripts/poc_sdk_client.py`
> **Rollback instantâneo**: `AGENT_PERSISTENT_SDK_CLIENT=false`

---

## 1. CONTEXTO E MOTIVAÇÃO

### Por que migrar

O agente web usa `query()` do Claude Agent SDK, que **spawna e destrói um subprocess CLI a cada turno** (~1.7s overhead). `ClaudeSDKClient` mantém o subprocess vivo entre turnos.

**Ganho primário**: Latência 2.15x menor (13.06s → 6.08s em 3 turnos).

**Ganhos secundários**:

| Recurso | query() (hoje) | ClaudeSDKClient (alvo) |
|---------|----------------|------------------------|
| Interrupt | Impossível (501) | `client.interrupt()` |
| Model switch mid-session | Impossível | `client.set_model()` |
| MCP server recovery | Impossível | `client.reconnect_mcp_server()` |
| Session tracking | Manual (capturar sdk_session_id, resume JSONL) | Automático (client mantém estado) |
| Overhead por turno | ~1.7s (spawn + destroy CLI) | ~0ms (stdin write) |

### Resultado da POC

| Métrica | query() | SDKClient | daemon thread (Flask) |
|---------|---------|-----------|----------------------|
| T1 total | 4.07s | 1.27s | 1.55s |
| T2 total | 4.92s | 1.50s | 2.22s |
| T3 total | 4.07s | 1.41s | 2.18s |
| **TOTAL** | **13.06s** | **6.08s** | **7.82s** |
| **Speedup** | 1x | **2.15x** | **1.67x** |

### Princípio cardinal

> **Esta migração é para EVOLUÇÃO, não para gerar problemas.**
> Zero funcionalidade perdida. Zero regressão. Rollback instantâneo via feature flag.
> Se qualquer feature quebrar, rollback ANTES de investigar.

---

## 2. ARQUITETURA ATUAL vs ALVO

### Atual (query() + resume)

```
HTTP POST /api/chat
  └─ Flask thread (Gunicorn gthread worker)
      └─ Thread(daemon=True)
          └─ asyncio.run()              ← cria event loop, destrói após
              └─ sdk.query(prompt)      ← spawna CLI subprocess
                  ├─ [processa]
                  └─ [destroi subprocess]
              └─ event_queue.put(events)
      └─ Generator: event_queue.get() → yield SSE
```

**Problemas**: ~1.7s overhead spawn/destroy por turno. Sem interrupt. Sem model switch.

### Alvo (ClaudeSDKClient persistente)

```
Flask request thread (gthread worker)
  └─ submit_coroutine(coro, _sdk_loop) → Future.result(timeout=540)

Daemon thread (_sdk_loop_thread):         ← event loop PERSISTENTE
  └─ _sdk_loop.run_forever()
      ├── PooledClient(session_A) ─ ClaudeSDKClient connected
      ├── PooledClient(session_B) ─ ClaudeSDKClient connected
      └── _cleanup_idle_clients() ─ periodic cada 60s
```

**Decisões arquiteturais**:
- **Pool por sessão (não por usuário)**: ClaudeSDKClient é stateful — 1:1 com sessão
- **Daemon thread único**: SDK exige mesmo event loop para todas operações do client
- **Flask bridge**: `run_coroutine_threadsafe()` submete work ao daemon
- **Idle timeout 15min**: disconnect automático libera recursos
- **JSONL backup continua**: safety net para worker recycle do Render

---

## 3. INVENTÁRIO DE FUNCIONALIDADES (PARIDADE OBRIGATÓRIA)

### 3.1 Endpoints (24 rotas)

Cada endpoint DEVE continuar funcionando identicamente após a migração.

| # | Endpoint | Método | Afetado? | Fase | Verificação |
|---|----------|--------|----------|------|-------------|
| E01 | `/agente/` | GET | NÃO | — | Página HTML, sem lógica de streaming |
| E02 | `/agente/api/chat` | POST | **SIM** | 1 | SSE streaming com novo path |
| E03 | `/agente/api/health` | GET | PARCIAL | 1 | + status do pool no response |
| E04 | `/agente/api/sessions` | GET | NÃO | — | Lista sessões do DB |
| E05 | `/agente/api/sessions/<id>/messages` | GET | NÃO | — | Histórico do JSONB |
| E06 | `/agente/api/admin/sessions/<id>/messages` | GET | NÃO | — | Admin, sem filtro user_id |
| E07 | `/agente/api/admin/generate-correction` | POST | NÃO | — | Sonnet, independente |
| E08 | `/agente/api/admin/save-correction` | POST | NÃO | — | DB, independente |
| E09 | `/agente/api/sessions/<id>` | DELETE | NÃO | — | Cascade delete DB |
| E10 | `/agente/api/sessions/<id>/rename` | PUT | NÃO | — | Update DB |
| E11 | `/agente/api/interrupt` | POST | **SIM** | 2 | 501 → real interrupt |
| E12 | `/agente/api/upload` | POST | NÃO | — | File upload /tmp |
| E13 | `/agente/api/files/<sid>/<fn>` | GET | NÃO | — | File download |
| E14 | `/agente/api/files` | GET | NÃO | — | List files |
| E15 | `/agente/api/files/<sid>/<fn>` | DELETE | NÃO | — | Remove file |
| E16 | `/agente/api/files/cleanup` | POST | NÃO | — | Cleanup files |
| E17 | `/agente/api/feedback` | POST | NÃO | — | DB feedback |
| E18 | `/agente/api/user-answer` | POST | PARCIAL | 1 | submit_answer() — dual events |
| E19 | `/agente/insights` | GET | NÃO | — | Dashboard HTML |
| E20 | `/agente/api/insights/data` | GET | NÃO | — | insights_service |
| E21 | `/agente/api/insights/friction` | GET | NÃO | — | friction_analyzer |
| E22 | `/agente/api/insights/memory` | GET | NÃO | — | insights_service |
| E23 | `/agente/api/async-health` | GET | NÃO | — | Debug endpoint |
| E24 | `/agente/api/contextvar-test` | GET | NÃO | — | Debug endpoint |

### 3.2 MCP Tools (38 tools em 7 servers)

| # | Server | Tool | ContextVar? | _execute_with_context? | Globals? | Status |
|---|--------|------|-------------|------------------------|----------|--------|
| T01 | sql | `consultar_sql` | `_current_user_id` | SIM | cache singleton | SAFE |
| T02 | memory | `view_memories` | `_current_user_id` | SIM | — | SAFE |
| T03 | memory | `save_memory` | `_current_user_id` | SIM | — | SAFE |
| T04 | memory | `update_memory` | `_current_user_id` | SIM | — | SAFE |
| T05 | memory | `delete_memory` | `_current_user_id` | SIM | — | SAFE |
| T06 | memory | `list_memories` | `_current_user_id` | SIM | — | SAFE |
| T07 | memory | `clear_memories` | `_current_user_id` | SIM | — | SAFE |
| T08 | memory | `search_cold_memories` | `_current_user_id` | SIM | — | SAFE |
| T09 | memory | `view_memory_history` | `_current_user_id` | SIM | — | SAFE |
| T10 | memory | `restore_memory_version` | `_current_user_id` | SIM | — | SAFE |
| T11 | memory | `resolve_pendencia` | `_current_user_id` | SIM | — | SAFE |
| T12 | memory | `log_system_pitfall` | `_current_user_id` | SIM | — | SAFE |
| T13 | schema | `consultar_schema` | — | — | cache singleton | SAFE |
| T14 | schema | `consultar_valores_campo` | — | — | cache singleton | SAFE |
| T15 | sessions | `search_sessions` | `_current_user_id` | SIM | — | SAFE |
| T16 | sessions | `list_recent_sessions` | `_current_user_id` | SIM | — | SAFE |
| T17 | sessions | `semantic_search_sessions` | `_current_user_id` | SIM | — | SAFE |
| T18 | render | `consultar_logs` | — | — | — | SAFE (stateless) |
| T19 | render | `consultar_erros` | — | — | — | SAFE (stateless) |
| T20 | render | `status_servicos` | — | — | — | SAFE (stateless) |
| T21 | routes | `search_routes` | — | — | — | SAFE (stateless) |
| T22 | browser | `browser_navigate` | — | — | `_page` global | DC-1 |
| T23 | browser | `browser_snapshot` | — | — | `_page` global | DC-1 |
| T24 | browser | `browser_screenshot` | — | — | `_page` global | DC-1 |
| T25 | browser | `browser_click` | — | — | `_page` global | DC-1 |
| T26 | browser | `browser_type` | — | — | `_page` global | DC-1 |
| T27 | browser | `browser_select_option` | — | — | `_page` global | DC-1 |
| T28 | browser | `browser_read_content` | — | — | `_page` global | DC-1 |
| T29 | browser | `browser_close` | — | — | `_page` global | DC-1 |
| T30 | browser | `browser_evaluate_js` | — | — | `_page` global | DC-1 |
| T31 | browser | `browser_switch_frame` | — | — | `_frame_local` | DC-1 |
| T32 | browser | `browser_ssw_login` | — | — | `_page` global | DC-1 |
| T33 | browser | `browser_ssw_navigate_option` | — | — | `_page` global | DC-1 |
| T34 | browser | `browser_atacadao_login` | — | — | `_page` global | DC-1 |

**Legenda Status**:
- SAFE = Funciona no daemon thread sem modificação
- DC-1 = Globals compartilhados — mitigado por asyncio.Lock, fix na Fase 4

### 3.3 Hooks SDK (6 hooks)

| # | Hook | Linhas client.py | Closures | Acessa DB? | Implicação daemon |
|---|------|------------------|----------|------------|-------------------|
| H01 | PreToolUse (`_keep_stream_open`) | 1227-1261 | tool_name (runtime) | NÃO | SAFE — sem estado persistente |
| H02 | PostToolUse (`_audit_post_tool_use`) | 1263-1286 | — | NÃO | SAFE — logging apenas |
| H03 | PostToolUseFailure | 1288-1346 | — | NÃO | SAFE — logging + context |
| H04 | PreCompact | 1348-1413 | flag | NÃO | SAFE — instrução de compactação |
| H05 | Stop | 1416-1461 | flag, user_id | NÃO | SAFE — logging |
| H06 | UserPromptSubmit | 1464-1560 | user_id, self, flags | **SIM** | DC-3 — model pode ficar stale |

**DC-3 Fix**: Hook H06 usa `options_dict.get("model")` em closure — com client persistente, pode ficar stale após `set_model()`. Fix: ler `self.settings.model`.

### 3.4 ContextVars (5 variáveis)

| # | ContextVar | Módulo | Default | Setada por | Lida por | Daemon OK? |
|---|------------|--------|---------|------------|----------|------------|
| CV01 | `_current_user_id` (sql) | text_to_sql_tool.py:34 | 0 | client.py:1614 | sql handler | SIM — setar antes de query() |
| CV02 | `_current_user_id` (memory) | memory_mcp_tool.py:30 | 0 | client.py:1644 | memory handler | SIM — setar antes de query() |
| CV03 | `_current_user_id` (sessions) | session_search_tool.py:22 | 0 | client.py:1711 | sessions handler | SIM — setar antes de query() |
| CV04 | `_current_session_id` | permissions.py:48 | None | permissions.py:67 | permissions.py:76 | SIM — setar antes de query() |
| CV05 | `_debug_mode` | permissions.py:52 | False | permissions.py:57 | permissions.py:62 | SIM — setar antes de query() |

**AÇÃO Fase 1**: `client_pool.py` DEVE setar CV01-CV05 antes de CADA `query()` no daemon thread.

### 3.5 Services (10 services)

| # | Service | LOC | Flag | Chamado de | Impactado? |
|---|---------|-----|------|------------|------------|
| S01 | pattern_analyzer.py | 912 | `USE_PATTERN_LEARNING` | routes.py (bg), client.py (hooks) | NÃO |
| S02 | knowledge_graph_service.py | 936 | `MEMORY_KNOWLEDGE_GRAPH` | client.py (_load_memories) | NÃO |
| S03 | insights_service.py | 879 | `USE_AGENT_INSIGHTS` | routes.py (/insights) | NÃO |
| S04 | friction_analyzer.py | 463 | `USE_FRICTION_ANALYSIS` | routes.py (/insights) | NÃO |
| S05 | memory_consolidator.py | 510 | `USE_MEMORY_CONSOLIDATION` | Background job | NÃO |
| S06 | session_summarizer.py | 402 | `USE_SESSION_SUMMARY` | routes.py (bg) | NÃO |
| S07 | sentiment_detector.py | 177 | `USE_SENTIMENT_DETECTION` | routes.py (_async_stream) | PARCIAL — chamado no stream |
| S08 | intersession_briefing.py | 331 | `USE_INTERSESSION_BRIEFING` | client.py (_load_memories) | NÃO |
| S09 | suggestions_generator.py | 209 | `USE_PROMPT_SUGGESTIONS` | routes.py (pós-done) | PARCIAL — chamado pós-stream |
| S10 | tool_skill_mapper.py | 316 | TBD | TBD | NÃO |

**S07 e S09**: Chamados dentro do fluxo de streaming em routes.py. O novo path DEVE chamar esses services nos mesmos pontos.

### 3.6 Feature Flags (45 flags)

Todas as 45 flags em `feature_flags.py` DEVEM continuar respeitadas. A migração adiciona 1 nova flag:

| Flag nova | Env Var | Default | Função |
|-----------|---------|---------|--------|
| `USE_PERSISTENT_SDK_CLIENT` | `AGENT_PERSISTENT_SDK_CLIENT` | `false` | Ativa o novo path SDKClient |

### 3.7 SSE Event Types (12 tipos)

O protocolo SSE frontend ↔ backend NÃO muda. Todos os event types DEVEM ser emitidos identicamente:

| # | Event Type | Origem | Verificação |
|---|------------|--------|-------------|
| SSE01 | `init` | routes.py | session_id no data |
| SSE02 | `text` | _parse_sdk_message | Conteúdo incremental |
| SSE03 | `thinking` | _parse_sdk_message | Extended thinking |
| SSE04 | `tool_call` | _parse_sdk_message | tool_name, tool_id |
| SSE05 | `tool_result` | _parse_sdk_message | result, is_error |
| SSE06 | `todos` | _parse_sdk_message | Lista de tarefas |
| SSE07 | `done` | routes.py | tokens, cost_usd |
| SSE08 | `suggestions` | routes.py (pós-done) | 2-3 sugestões |
| SSE09 | `error` | routes.py / client.py | Mensagem de erro |
| SSE10 | `ask_user_question` | permissions.py | Pergunta interativa |
| SSE11 | `destructive_action_warning` | permissions.py | Alerta irreversível |
| SSE12 | `interrupt_ack` | routes.py | Confirmação interrupt |

### 3.8 Timeout Cascade (INVARIANTE)

Ordem OBRIGATÓRIA — **nunca alterar**:

```
Heartbeat SSE (10s) < AskUser web (55s) < AskUser Teams (120s) < SDK stream_close (240s) < Stream max (540s) < Render hard (600s)
```

### 3.9 Thread-Safety Mechanisms (3 mecanismos — PRESERVAR)

| # | Mecanismo | O que protege | Onde |
|---|-----------|---------------|------|
| TS01 | ContextVar (`_current_session_id`) | Isolamento session_id por thread/coroutine | permissions.py:48 |
| TS02 | Dict `_stream_context` + `_context_lock` | event_queue cross-thread | permissions.py:41-42 |
| TS03 | Dict `_teams_task_context` + `_context_lock` | Associação sessão ↔ TeamsTask | permissions.py:109 |

### 3.10 Integração Teams (DEVE FUNCIONAR)

| # | Funcionalidade | Arquivo | Impactada? | Fase |
|---|----------------|---------|------------|------|
| TM01 | Auto-criação de user Teams | services.py | NÃO | — |
| TM02 | Processamento async (daemon thread) | services.py | **SIM** | 3 |
| TM03 | AskUserQuestion via Adaptive Card | services.py + permissions.py | **SIM** | 3 |
| TM04 | Progressive streaming (flush parcial) | services.py | **SIM** | 3 |
| TM05 | Persistência de sessão (conversation_id) | services.py | NÃO | — |

---

## 4. DESCOBERTAS CRÍTICAS

### DC-1: Playwright MCP — Globals Compartilhados (RISCO ALTO)

**Fonte**: `app/agente/tools/playwright_mcp_tool.py`

**Problema**: Module-level globals `_playwright`, `_browser`, `_context`, `_page`, `_frame_local` compartilhados. No daemon thread persistente, 2 sessões usando browser simultaneamente = colisão de estado.

**Mitigação Fase 1** (aceitável):
- Concorrência baixa (~4 usuários, browser é tool rara)
- Hoje já compartilha globals entre requests sequenciais
- asyncio.Lock do PooledClient serializa chamadas no mesmo event loop

**Fix definitivo Fase 4**:
- Dict `_pages: Dict[str, Page]` keyed por session_id
- ContextVar `_current_frame` em vez de `threading.local()`

### DC-2: Flask app_context no Daemon Thread (RISCO ALTO)

**Fonte**: `app/agente/config/permissions.py`

**Problema**: Daemon thread NÃO tem Flask app_context. 2 pontos acessam `db.session` sem wrapper:
- `permissions.py:347-352` — `db.session.get(TeamsTask)` no Teams AskUser
- `permissions.py:375-380` — Mesmo, no timeout path

**Todos os outros pontos JÁ são safe**:
- MCP tools: `_execute_with_context()` fallback
- `_load_user_memories_for_context()`: try/except `current_app` + `create_app()`
- Skills: CLI subprocess com próprio `create_app()`

**Fix obrigatório Fase 0**: Wrap ambos pontos em `_execute_with_context()`.

### DC-3: Hooks Persistem com o Client (RISCO MÉDIO)

**Fonte**: `app/agente/sdk/client.py` — `_build_options()` linhas 1026-1838

**Hoje**: `_build_options()` chamado a cada `stream_response()` → hooks recriados fresh.
**Novo**: `_build_options()` chamado 1x no `connect()` → hooks persistem com o client.

**Análise de closures**:
| Closure | Valor | Muda entre turnos? | Risco |
|---------|-------|---------------------|-------|
| `user_id` | int | NÃO (constante por sessão) | SAFE |
| `self` | AgentClient | NÃO (singleton) | SAFE |
| `self.settings.model` | str | NÃO (atributo atualizado) | SAFE |
| `options_dict.get("model")` | str | SIM (se set_model()) | **STALE** |
| flags (`USE_*`) | bool | NÃO (env vars, constantes) | SAFE |

**Fix Fase 1**: No Hook H06 (`_user_prompt_submit_hook`), ler `self.settings.model` em vez de `options_dict.get("model")`.

### DC-4: MCP Servers — Lifecycle no Connect (RISCO BAIXO)

**Fonte**: `app/agente/sdk/client.py` — linhas 1609-1828

7 MCP servers instanciados em `_build_options()` e passados via `mcp_servers` dict. Com SDKClient:
- Instanciados 1x no `connect()` — **OK, são stateless ou usam ContextVar**
- `user_id` setado via ContextVar antes de cada `query()` pelo pool — **OK**
- `_execute_with_context()` garante app_context para DB — **OK**
- Browser globals compartilhados — **DC-1, mitigado por Lock**

### DC-5: _make_streaming_prompt() Eliminável (SIMPLIFICAÇÃO)

**Fonte**: `app/agente/sdk/client.py` — linhas 2467-2512

O padrão `_make_streaming_prompt()` + `streaming_done_event` + `await done_event.wait(timeout=600)` existe SOMENTE porque `query()` precisa de um AsyncIterable de prompts que fica aberto até ResultMessage. Com `ClaudeSDKClient.query(prompt_string)`, esse mecanismo inteiro é desnecessário.

**Eliminado no path persistente** (mantido no path query() para rollback).

### DC-6: asyncio.Event.set() Cross-Thread (RISCO BAIXO)

**Fonte**: `app/agente/sdk/pending_questions.py` — linhas 88-92

`submit_answer()` chama `pq.async_event.set()` de Flask thread enquanto daemon thread aguarda em `async_wait_for_answer()`. No CPython, GIL protege, mas não é oficialmente thread-safe.

**Mitigação**: Monitorar. Se race condition aparecer, substituir por `loop.call_soon_threadsafe(pq.async_event.set)`.

### DC-7: disconnect() Cross-Task Causa Subprocess Zombie (RISCO CRÍTICO — FIXADO)

**Fonte**: `app/agente/sdk/client_pool.py` — `disconnect_client()` e `_periodic_cleanup()`

**Problema**: `disconnect()` chama `query.close()` (query.py:659-667) que faz:
```python
self._tg.cancel_scope.cancel()
with suppress(CancelledError):
    await self._tg.__aexit__(None, None, None)  # ← FALHA: Task B ≠ Task A
await self.transport.close()  # ← NUNCA ALCANÇADO
```
O `__aexit__()` lança `RuntimeError("Attempted to exit cancel scope in a different task")`.
`suppress()` só captura `CancelledError`, NÃO `RuntimeError`.
`transport.close()` (que chama `_process.terminate()`) NUNCA é alcançado.

**Consequência em produção**:
- CPU: avg 2.87 / max 3.99 de 4.0 CPUs em sistema OCIOSO
- Memória: crescimento monotônico 1762MB → 3684MB (de 8192MB limite)
- Cada interação cria novo subprocess (~100-150MB + CPU constante)
- Cleanup remove do registry mas NÃO mata subprocess → zombie acumula

**Fix aplicado (2026-03-09)**:
- `_force_kill_subprocess(client)`: Acessa `client._transport.close()` diretamente, bypassando `query.close()`
- `transport.close()` é SAFE de qualquer task porque usa `suppress(Exception)` em todos os pontos críticos
- `_process.terminate()` é OS-level (sem cancel scope)
- Fallback: se `transport.close()` falhar, `_process.terminate()` direto
- Aplicado em `disconnect_client()` e `get_or_create_client()` (substituição de client antigo)

**Fragilidade**: Acessa internals do SDK (`_transport`, `_query`, `_process`). Versão pinada 0.1.48.
Se SDK mudar internals, `_force_kill_subprocess()` falha graciosamente (try/except + getattr).

**Rollback temporário (2026-03-09)**: `AGENT_PERSISTENT_SDK_CLIENT=false` até fix ser deployed.

### DC-8: CancelledError Bypassa streaming_done_event (RISCO CRÍTICO — FIXADO)

**Fonte**: `app/agente/sdk/client.py` — `_stream_response()` linhas 2641-2856

**Problema**: O método tem 5 except handlers (ProcessError, CLINotFoundError, CLIJSONDecodeError, BaseExceptionGroup, Exception), cada um chamando `streaming_done_event.set()`. MAS `asyncio.CancelledError` é `BaseException` desde Python 3.9 — **NÃO é `Exception`** — e bypassa TODOS os handlers.

**Cadeia de eventos no Teams**:
1. Teams recebe mensagem → thread non-daemon inicia
2. `asyncio.run(_stream_with_timeout())` é chamado
3. `_stream_with_timeout()` wrapa em `asyncio.wait_for(timeout=240)`
4. Após 240s, `wait_for` **cancela** a coroutine com `CancelledError`
5. `CancelledError` propaga por `_stream_response()` — **NÃO é capturado**
6. `streaming_done_event.set()` **NUNCA é chamado**
7. `_make_streaming_prompt()` fica bloqueado em `done_event.wait(timeout=600)` por **10 minutos**
8. Subprocess CLI fica ativo consumindo CPU
9. A cada retry, um NOVO subprocess é criado → acumula

**Fix aplicado (2026-03-09)**: Bloco `finally` após todos os except handlers garante que `streaming_done_event.set()` é SEMPRE chamado. Guard `is_set()` evita log duplicado quando except handler já liberou. Defense-in-depth: handlers individuais mantidos.

**Nota**: O path persistente (`_stream_response_persistent`) é **imune** porque `streaming_done_event = None`.

**Critérios para re-habilitar `AGENT_PERSISTENT_SDK_CLIENT=true`**:
1. Fix DC-8 (finally block) deployed e validado por 48h sem picos de CPU
2. Canary: habilitar para 1 conversa Teams de baixo tráfego por 24h
3. Monitorar: CPU < 50%, memória estável, zero orphan subprocesses no health check
4. Expandir: todas as conversas Teams → web admin → todos os usuários

---

## 5. FASES DE IMPLEMENTAÇÃO

### FASE 0: Infraestrutura (sem mudança de comportamento)

**Objetivo**: Criar toda a base necessária SEM ativar nada. Flag=false, sistema idêntico.

**Pré-condições**: Nenhuma.

| Task | Status | Arquivo | O que fazer | Dependência |
|------|--------|---------|-------------|-------------|
| 0.1 | ✅ | `permissions.py:347-352,375-380` | Fix DC-2: wrap `db.session.get(TeamsTask)` em `_execute_with_context()` nos 2 pontos | — |
| 0.2 | ✅ | `app/agente/sdk/client_pool.py` **(NOVO)** | Criar: PooledClient dataclass, _registry dict, daemon thread (`_sdk_loop`), `submit_coroutine()`, `shutdown_pool()`, `_cleanup_idle_clients()`, `get_or_create_client()`, `disconnect_client()` | — |
| 0.3 | ✅ | `feature_flags.py` | Adicionar `USE_PERSISTENT_SDK_CLIENT` (default false) | — |
| 0.4 | ✅ | `client.py` | Extrair `_parse_sdk_message()` de `_stream_response()` (linhas 1960-2262). Método reutilizável por ambos os paths | — |
| 0.5 | ✅ | `sdk/__init__.py` | Export `submit_coroutine` e `get_or_create_client` | 0.2 |

**Pós-condições (OBRIGATÓRIO verificar)**:
- [ ] `AGENT_PERSISTENT_SDK_CLIENT=false` → sistema funciona identicamente
- [ ] Teams AskUser continua OK (testar com Adaptive Card)
- [ ] `_parse_sdk_message()` retorna MESMOS StreamEvents que o código inline
- [ ] `client_pool.py` importa sem erro mas daemon thread NÃO inicia (flag=false)
- [ ] Nenhum endpoint mudou comportamento
- [ ] Todos os 38 MCP tools continuam funcionando

**Rollback**: Reverter 0.1-0.5 — são adições sem efeito colateral.

---

### FASE 1: Web Streaming (feature-flagged, canary)

**Objetivo**: Novo path coexiste com antigo, controlado por flag. Canary em admins primeiro.

**Pré-condições**: Fase 0 completa e verificada.

| Task | Status | Arquivo | O que fazer | Dependência |
|------|--------|---------|-------------|-------------|
| 1.1 | ✅ | `client.py` | Criar `_stream_response_persistent()` — usa `get_or_create_client()`, `client.query()`, `receive_response()`, `_parse_sdk_message()` | 0.2, 0.4 |
| 1.2 | ✅ | `client.py` | Fix DC-3: No `_user_prompt_submit_hook`, usar `self.settings.model` em vez de `options_dict.get("model")` | — |
| 1.3 | ✅ | `client.py:stream_response()` | Dispatch: `if USE_PERSISTENT_SDK_CLIENT: path novo, else: path antigo` + parâmetro `our_session_id` | 1.1 |
| 1.4 | ✅ | `routes.py` | Novo path: `submit_coroutine()` em vez de `asyncio.run()` quando flag=true. SSE + Queue inalterados. Thread mantida (bloqueia em future.result) | 0.2, 1.3 |
| 1.5 | ✅ | `(implícito)` | ContextVars CV01-CV05 setadas em `async_stream()` e `_build_options()` — propagam ao daemon thread via Task context | — |
| 1.6 | ✅ | `(implícito)` | `_build_options()` (chamado todo turno) seta ContextVars dos MCP tools. `async_stream()` seta session_id e debug_mode | 0.2 |
| 1.7 | ✅ | `(implícito)` | S07 (sentiment) e S09 (suggestions) chamados no mesmo `async_stream()` — código compartilhado por ambos paths | 1.4 |
| 1.8 | ✅ | `(implícito)` | DB persistence em `_save_messages_to_db()` no finally de `_stream_chat_response()` — independente do path de streaming | 1.4 |
| 1.9 | ✅ | `routes.py` | Health check (`/api/health`) inclui `sdk_client_pool` status quando flag=true via `get_pool_status()` | 0.2 |

**Pós-condições (OBRIGATÓRIO verificar)**:
- [ ] `flag=false` → sistema idêntico (ZERO regressão)
- [ ] `flag=true` para admin → chat funciona via SSE
- [ ] Multi-turn: 3 mensagens → contexto preservado no turno 2+
- [ ] AskUserQuestion web: tool pergunta → responder → fluxo completa
- [ ] Todos os 12 SSE event types emitidos corretamente
- [ ] Tokens contabilizados (`done` event com input_tokens, output_tokens, cost_usd)
- [ ] Sessão persistida no DB (messages, transcript, title, cost)
- [ ] Session resume funciona após page refresh
- [ ] Memory injection (Tier 0-2b) funciona via H06 UserPromptSubmit
- [ ] Sugestões contextuais (S09) aparecem pós-done
- [ ] Sentiment detection (S07) ativa quando configurado
- [ ] Pattern extraction pós-sessão (pattern_analyzer) dispara
- [ ] Knowledge graph queries (S02) retornam dados
- [ ] Debug mode funciona para admin
- [ ] 2 tabs abertas → sessões independentes sem interferência

**Rollback**: `AGENT_PERSISTENT_SDK_CLIENT=false` → instantâneo, sem restart.

**Canary**: `USE_PERSISTENT_SDK_CLIENT=true` + `current_user.perfil == 'administrador'`

---

### FASE 2: Interrupt (feature nova)

**Objetivo**: Habilitar `POST /api/interrupt` (hoje retorna 501).

**Pré-condições**: Fase 1 estável por ≥1 semana.

| Task | Status | Arquivo | O que fazer | Dependência |
|------|--------|---------|-------------|-------------|
| 2.1 | ✅ | `routes.py` | Implementar interrupt real: `submit_coroutine(pooled.client.interrupt())` → 200 | 0.2 |
| 2.2 | ✅ | `routes.py` | SSE event `interrupt_ack` — já emitido por `_parse_sdk_message()` em client.py:1316 quando ResultMessage tem subtype='interrupted'. Frontend trata em chat.js:919. | 2.1 |

**Pós-condições**:
- [ ] Frontend já tem botão interrupt → clicar durante tool call longa → resposta interrompida
- [ ] interrupt_ack event emitido
- [ ] Sessão continua funcional após interrupt (não precisa reconectar)
- [ ] Interrupt de sessão inexistente retorna 404 (não 500)

**Rollback**: Reverter 2.1-2.2 (endpoint volta a 501).

---

### FASE 3: Teams

**Objetivo**: Teams usa o mesmo pool em vez de `asyncio.run()`.

**Pré-condições**: Fase 1 estável por ≥2 semanas.

| Task | Status | Arquivo | O que fazer | Dependência |
|------|--------|---------|-------------|-------------|
| 3.1 | ✅ | `teams/services.py` | Substituir `asyncio.run()` por `submit_coroutine()` nos 2 paths (sync e streaming) | 0.2 |
| 3.2 | ✅ | `teams/services.py` | Manter non-daemon thread para o wrapper que chama `submit_coroutine()` | 3.1 |
| 3.3 | ✅ | `teams/services.py` | Garantir que ContextVars são setadas (user_id, session_id) antes de submit | 3.1 |

**Pós-condições**:
- [ ] Mensagem via Teams → resposta chega
- [ ] AskUserQuestion via Adaptive Card funciona (timeout 120s)
- [ ] Progressive streaming (flush parcial) funciona
- [ ] Auto-criação de user Teams continua OK
- [ ] Sessão Teams persiste por conversation_id

**Rollback**: Reverter 3.1-3.3 (volta para `asyncio.run()`).

---

### FASE 4: Simplificação (após 2-4 semanas estável)

**Objetivo**: Remover complexidade do path antigo, agora que o novo é o padrão.

**Pré-condições**: Fases 1-3 estáveis por ≥4 semanas, flag=true para TODOS os usuários.

| Task | Status | Arquivo | O que fazer | Dependência |
|------|--------|---------|-------------|-------------|
| 4.1 | ○ | `client.py` | Remover `streaming_done_event` do path persistente | 1.1 |
| 4.2 | ○ | `client.py` | Remover `_make_streaming_prompt()` do path persistente | 1.1 |
| 4.3 | ○ | `session_persistence.py` | Reduzir backup JSONL: apenas no disconnect/recycle (não todo turno) | 1.1 |
| 4.4 | ○ | `routes.py`, `models.py` | Remover tracking de `sdk_session_id` no DB para sessões ativas (client gerencia) | 1.1 |
| 4.5 | ○ | `playwright_mcp_tool.py` | Fix DC-1: Dict `_pages: Dict[str, Page]` per session_id + ContextVar `_current_frame` | — |

**Pós-condições**:
- [ ] Path persistente mais simples (sem done_event, sem _make_streaming_prompt)
- [ ] JSONL backup apenas no disconnect/recycle
- [ ] Browser sessions isoladas por session_id (sem globals compartilhados)
- [ ] ZERO regressão em todas as funcionalidades

**Rollback**: Reverter tasks individualmente (cada uma é independente).

---

### FASE 5: Remoção do path query() (após 2-4 semanas da Fase 4)

**Objetivo**: `query()` removido. SDKClient é o único path.

**Pré-condições**: Fase 4 estável por ≥4 semanas. Nenhum relatório de bug relacionado ao novo path.

| Task | Status | Arquivo | O que fazer | Dependência |
|------|--------|---------|-------------|-------------|
| 5.1 | ○ | `feature_flags.py` | Remover `USE_PERSISTENT_SDK_CLIENT` (sempre true) | 4.x |
| 5.2 | ○ | `client.py` | Remover `_stream_response()` (path antigo), `_make_streaming_prompt()`, `_with_resume()` | 5.1 |
| 5.3 | ○ | `routes.py` | Remover branch `if not USE_PERSISTENT_SDK_CLIENT` | 5.1 |
| 5.4 | ○ | `CLAUDE.md`, `app/agente/CLAUDE.md` | Documentar nova arquitetura | 5.1-5.3 |

**Pós-condições**:
- [ ] Código limpo, sem branches mortos
- [ ] Documentação atualizada
- [ ] ZERO regressão (teste end-to-end completo)

**Rollback**: Git revert (último recurso — Fase 5 só executa quando há confiança total).

---

## 6. ARQUIVOS IMPACTADOS — MAPA COMPLETO

### Criados

| Arquivo | Fase | LOC est. | Descrição |
|---------|------|----------|-----------|
| `app/agente/sdk/client_pool.py` | 0 | ~300 | Pool de ClaudeSDKClient por sessão, daemon thread, submit_coroutine |

### Modificados

| Arquivo | Fase(s) | LOC atual | O que muda |
|---------|---------|-----------|------------|
| `app/agente/config/permissions.py` | 0, 1 | 607 | Fix DC-2 (2 pontos app_context) + `_make_scoped_can_use_tool()` |
| `app/agente/sdk/client.py` | 0, 1, 3 | 2672 | `_parse_sdk_message()` extraído + `_stream_response_persistent()` + dispatch + fix DC-3 + `our_session_id` em `get_response()` |
| `app/agente/routes.py` | 1, 2 | 3074 | Novo path `submit_coroutine()` + interrupt real + health pool |
| `app/agente/config/feature_flags.py` | 0 | 243 | +1 flag (`USE_PERSISTENT_SDK_CLIENT`) |
| `app/agente/sdk/__init__.py` | 0 | ~10 | Export `submit_coroutine`, `get_or_create_client` |
| `app/teams/services.py` | 3 | ~950 | `submit_coroutine()` em vez de `asyncio.run()` |
| `app/agente/tools/playwright_mcp_tool.py` | 4 | 1665 | Page per session + ContextVar para frame |
| `app/agente/CLAUDE.md` | 5 | ~210 | Documentar nova arquitetura |
| `CLAUDE.md` | 5 | ~230 | Referência ao roadmap |

### NÃO impactados (confirmado por análise profunda)

| Arquivo | LOC | Motivo de segurança |
|---------|-----|---------------------|
| `tools/memory_mcp_tool.py` | 2159 | ContextVar `_current_user_id` + `_execute_with_context()` em todas as operações |
| `tools/text_to_sql_tool.py` | 471 | ContextVar `_current_user_id` + `_execute_with_context()` |
| `tools/session_search_tool.py` | 413 | ContextVar `_current_user_id` + `_execute_with_context()` |
| `tools/schema_mcp_tool.py` | 381 | Stateless + try/except `current_app` + `create_app()` fallback |
| `tools/render_logs_tool.py` | 654 | Stateless (API externa Render, sem DB) |
| `tools/routes_search_tool.py` | 183 | Stateless (embeddings read-only, sem ContextVar) |
| `tools/_mcp_enhanced.py` | ~200 | Wrapper stateless, nenhum estado próprio |
| `sdk/session_persistence.py` | 206 | Safety net para worker recycle — continua como está |
| `sdk/pending_questions.py` | 219 | Dual events (threading + asyncio) funcionam no daemon thread |
| `sdk/cost_tracker.py` | ~100 | Tracking independente, sem estado thread |
| `services/pattern_analyzer.py` | 912 | Background daemon thread próprio (já existente) |
| `services/knowledge_graph_service.py` | 936 | DB queries via `_execute_with_context()` |
| `services/insights_service.py` | 879 | DB queries independentes |
| `services/friction_analyzer.py` | 463 | DB queries independentes |
| `services/memory_consolidator.py` | 510 | Background job independente |
| `services/session_summarizer.py` | 402 | Chamado pós-stream, independente |
| `services/sentiment_detector.py` | 177 | Regex puro, zero estado |
| `services/intersession_briefing.py` | 331 | DB queries independentes |
| `services/suggestions_generator.py` | 209 | Chamado pós-stream, API call independente |
| `.claude/skills/**` | ~5000 | CLI subprocess independente com próprio `create_app()` |

---

## 7. RISCOS — REGISTRO VIVO

| # | Risco | Sev. | Prob. | Mitigação | Status |
|---|-------|------|-------|-----------|--------|
| R01 | Daemon thread morre → agente offline | ALTA | BAIXA | try/except + auto-restart + health check monitora `thread.is_alive()` | PLANEJADO |
| R02 | Zombie CLI processes após crash | ALTA | BAIXA | `_cleanup_idle_clients()` a cada 60s; `worker_exit` hook; `ps` check em health | PLANEJADO |
| R03 | ContextVar não propaga em callbacks SDK | ALTA | MÉDIA | `_make_scoped_can_use_tool()` seta CV01-CV05 explicitamente antes de cada callback | PLANEJADO |
| R04 | Playwright globals compartilhados (DC-1) | ALTA | BAIXA | asyncio.Lock serializa no daemon; concorrência baixa; fix Fase 4 | ACEITO (Fase 1) |
| R05 | app_context ausente em permissions.py (DC-2) | ALTA | CERTA | Fix obrigatório Fase 0 (2 pontos) | PLANEJADO |
| R06 | Hook closure stale após set_model() (DC-3) | MÉDIA | MÉDIA | Ler `self.settings.model` em vez de `options_dict` | PLANEJADO |
| R07 | Worker recycle perde clients no registry | MÉDIA | CERTA | JSONL backup continua; reconnect com resume; safety net | ACEITO |
| R08 | Query concurrent na mesma sessão | MÉDIA | BAIXA | asyncio.Lock por PooledClient; segunda request → "session busy" | PLANEJADO |
| R09 | Model switch invalida connect-time options | MÉDIA | BAIXA | `client.set_model()` nativo; se option afeta connect: disconnect + reconnect | PLANEJADO |
| R10 | MCP server falha persiste entre turnos | BAIXA | BAIXA | `client.reconnect_mcp_server()` on failure; retry automático | PLANEJADO |
| R11 | asyncio.Event.set() cross-thread (DC-6) | BAIXA | MUITO BAIXA | GIL protege no CPython; monitorar; fallback `loop.call_soon_threadsafe()` | ACEITO |
| R12 | Feature flags lidas no connect ficam stale | BAIXA | BAIXA | Flags são env vars, constantes por lifecycle do worker | ACEITO |
| R13 | disconnect() cross-task mata subprocess zombie (DC-7) | CRÍTICA | CERTA | `_force_kill_subprocess()` + acesso direto a `transport.close()` | **FIXADO** |
| R14 | CancelledError bypassa streaming_done_event (DC-8) | CRÍTICA | CERTA | `finally` block em `_stream_response()` garante `.set()` | **FIXADO** |

---

## 8. ROLLBACK — ESTRATÉGIA POR CAMADA

### Rollback Instantâneo (segundos)
```bash
# Render Dashboard → Environment Variables
AGENT_PERSISTENT_SDK_CLIENT=false
# Redeploy → sistema volta 100% para query()
```

### Rollback por Fase
| Fase | Como reverter | Tempo | Risco |
|------|---------------|-------|-------|
| 0 | Não precisa (sem efeito com flag=false) | 0s | ZERO |
| 1 | `AGENT_PERSISTENT_SDK_CLIENT=false` | ~30s (env var change + restart) | ZERO |
| 2 | Reverter 2.1-2.2 (endpoint volta a 501) | Git revert + deploy | ZERO |
| 3 | Reverter 3.1-3.3 (volta asyncio.run()) | Git revert + deploy | ZERO |
| 4 | Git revert tasks individuais | Git revert + deploy | BAIXO |
| 5 | **IRREVERSÍVEL** — path antigo removido | — | Só executar com confiança TOTAL |

---

## 9. VERIFICAÇÃO END-TO-END

### Checklist por Fase

#### Fase 0 (Infra)
- [ ] V0.1: Sistema funciona com flag=false (ZERO regressão)
- [ ] V0.2: Teams AskUser via Adaptive Card funciona (DC-2 fix)
- [ ] V0.3: `_parse_sdk_message()` unitário — mesmos StreamEvents que inline
- [ ] V0.4: `client_pool.py` importa sem erro, daemon NÃO inicia

#### Fase 1 (Web Streaming)
- [ ] V1.01: flag=false → sem regressão
- [ ] V1.02: flag=true admin → chat funciona SSE
- [ ] V1.03: Multi-turn (3 msgs) → contexto preservado
- [ ] V1.04: AskUserQuestion web → responder → completa
- [ ] V1.05: Todos 12 SSE event types emitidos
- [ ] V1.06: Tokens contabilizados (done event)
- [ ] V1.07: Sessão persistida DB (messages, transcript, title, cost)
- [ ] V1.08: Session resume após page refresh
- [ ] V1.09: Memory injection (Tier 0-2b) funciona
- [ ] V1.10: Sugestões pós-done (S09)
- [ ] V1.11: Sentiment detection (S07)
- [ ] V1.12: Pattern extraction pós-sessão (S01)
- [ ] V1.13: Knowledge graph queries (S02)
- [ ] V1.14: Debug mode admin
- [ ] V1.15: 2 tabs → sessões independentes
- [ ] V1.16: Skill execution (e.g., cotando-frete) funciona via tool
- [ ] V1.17: SQL queries via mcp__sql__consultar_sql
- [ ] V1.18: Memory CRUD via mcp__memory__*
- [ ] V1.19: Browser tools (navigate, screenshot) via mcp__browser__*
- [ ] V1.20: Session search via mcp__sessions__*
- [ ] V1.21: File upload + vision (image_files param)
- [ ] V1.22: Plan mode (readonly, permission_mode="plan")
- [ ] V1.23: Effort level (off/low/medium/high/max)
- [ ] V1.24: Extended context flag
- [ ] V1.25: Budget control flag

#### Fase 2 (Interrupt)
- [ ] V2.1: Interrupt durante tool call → resposta interrompida
- [ ] V2.2: interrupt_ack event emitido
- [ ] V2.3: Sessão funcional após interrupt

#### Fase 3 (Teams)
- [ ] V3.1: Mensagem via Teams → resposta
- [ ] V3.2: AskUserQuestion Adaptive Card
- [ ] V3.3: Progressive streaming
- [ ] V3.4: Auto-criação user Teams
- [ ] V3.5: Sessão por conversation_id

#### Fase 4 (Simplificação)
- [ ] V4.1: JSONL backup apenas no disconnect
- [ ] V4.2: Browser sessions isoladas (DC-1 fix)
- [ ] V4.3: ZERO regressão

#### Fase 5 (Remoção)
- [ ] V5.1: Código limpo, sem branches mortos
- [ ] V5.2: Docs atualizados
- [ ] V5.3: ZERO regressão (teste end-to-end COMPLETO)

### Testes de Regressão Automatizáveis

| # | Teste | Tipo | O que verifica |
|---|-------|------|----------------|
| REG01 | Grep `streaming_done_event.set()` em client.py | Static | Todos error handlers chamam set() |
| REG02 | Grep `event_queue.put(None)` em routes.py | Static | Sentinel no finally |
| REG03 | Grep `with _context_lock:` em permissions.py | Static | Lock em toda modificação de globals |
| REG04 | Grep `ContextVar` vs `threading.local()` | Static | Sem regressão para threading.local |
| REG05 | Timeout order: 55 < 240 < 540 < 600 | Static | Cascata respeitada |
| REG06 | `asyncio.new_event_loop()` = 0 hits no agente/ | Static | Sempre usar asyncio.run() |
| REG07 | Health check retorna 200 | Integration | API + pool funcionando |
| REG08 | Chat message → SSE stream | Integration | Fluxo completo web |
| REG09 | File upload + response | Integration | Vision API |
| REG10 | AskUserQuestion round-trip | Integration | Dual events |

---

## 10. LOG DE DECISÕES

| Data | Decisão | Motivo | Alternativa rejeitada |
|------|---------|--------|-----------------------|
| 2026-03-08 | Pool por sessão (não por usuário) | ClaudeSDKClient é stateful, 1:1 com conversa | Pool genérico (não respeita estado) |
| 2026-03-08 | Daemon thread único (não thread-per-request) | SDK exige mesmo event loop | asyncio.run() por request (overhead) |
| 2026-03-08 | Feature flag (não migração big-bang) | Rollback instantâneo, canary possível | Substituição direta (risco alto) |
| 2026-03-08 | JSONL backup mantido (não removido) | Safety net para worker recycle Render | Remover backup (perde resume) |
| 2026-03-08 | DC-1 Playwright aceito na Fase 1 | Concorrência baixa, tool rara, Lock serializa | Bloquear Fase 1 até fix (delay desnecessário) |

---

## 11. LOG DE PROGRESSO

| Data | Fase | Task | Status | Notas |
|------|------|------|--------|-------|
| 2026-03-08 | POC | Benchmark 3 abordagens | CONCLUÍDO | 2.15x speedup confirmado |
| 2026-03-08 | PLAN | Pesquisa profunda (3 agents) | CONCLUÍDO | DC-1 a DC-6 identificados |
| 2026-03-08 | PLAN | Roadmap vivo v1 | CONCLUÍDO | Este documento |
| 2026-03-08 | 0 | Tasks 0.1-0.5 | CONCLUÍDO | DC-2 fix, client_pool.py, flag, _parse_sdk_message, exports |
| 2026-03-08 | 1 | Tasks 1.1-1.9 | CONCLUÍDO | _stream_response_persistent, DC-3 fix, dispatch, submit_coroutine, health |
| 2026-03-08 | 2 | Tasks 2.1-2.2 | CONCLUÍDO | Interrupt real via submit_coroutine(client.interrupt()). interrupt_ack já emitido por _parse_sdk_message |
| 2026-03-08 | 3 | Tasks 3.1-3.3 | CONCLUÍDO | submit_coroutine() em 2 paths Teams. our_session_id adicionado a get_response(). _safe_flush() com app_context no daemon. Non-daemon thread mantido |
| 2026-03-09 | FIX | DC-7 subprocess zombie | CONCLUÍDO | _force_kill_subprocess() bypassa query.close() e chama transport.close() diretamente. Fix em disconnect_client() e get_or_create_client(). Rollback temporário: flag=false |
| 2026-03-09 | FIX | DC-8 CancelledError bypass | CONCLUÍDO | finally block em _stream_response(). Health check com monitoramento threads/processes. Orphan cleanup em Teams. Documentado em CLAUDE.md R5 |

---

## 12. REFERÊNCIAS

| Recurso | Caminho |
|---------|---------|
| POC benchmark | `scripts/poc_sdk_client.py` |
| SDK ClaudeSDKClient API | `.venv/lib/python3.12/site-packages/claude_agent_sdk/client.py` |
| SDK query() API | `.venv/lib/python3.12/site-packages/claude_agent_sdk/query.py` |
| Agent client atual | `app/agente/sdk/client.py` (2672 linhas) |
| Routes Flask | `app/agente/routes.py` (3074 linhas) |
| Permissions | `app/agente/config/permissions.py` (607 linhas) |
| Pending questions | `app/agente/sdk/pending_questions.py` (219 linhas) |
| Session persistence | `app/agente/sdk/session_persistence.py` (206 linhas) |
| Feature flags | `app/agente/config/feature_flags.py` (243 linhas) |
| Teams services | `app/teams/services.py` (~950 linhas) |
| Playwright MCP | `app/agente/tools/playwright_mcp_tool.py` (1665 linhas) |
| Agente CLAUDE.md | `app/agente/CLAUDE.md` |
| Roadmap persistido | `.claude/references/ROADMAP_SDK_CLIENT.md` |
| Docs oficiais SDK sessions | `platform.claude.com/docs/en/agent-sdk/sessions` |
