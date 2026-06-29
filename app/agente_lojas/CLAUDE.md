<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-26
-->
# Agente Lojas HORA — Guia de Desenvolvimento

> **Papel:** guia de desenvolvimento do agente dedicado as Lojas Motochefe (HORA), endpoint `/agente-lojas/*` — compartilha o SDK com `app/agente/` mas com system_prompt, skills, subagents e escopo de dados isolados.

## Indice

- [Contexto](#contexto)
- [Porque existe um agente separado](#porque-existe-um-agente-separado)
- [Estrutura](#estrutura)
- [Reuso vs exclusivo](#reuso-vs-exclusivo)
- [Autorizacao](#autorizacao)
- [Escopo de dados por loja](#escopo-de-dados-por-loja)
- [Particao de sessoes e memorias](#particao-de-sessoes-e-memorias)
- [Fases de evolucao](#fases-de-evolucao)
- [Gotchas](#gotchas)
- [Referencias](#referencias)

## Contexto

Agente separado (decisao 2026-04-22) que reusa a infra do SDK mas atende so o operador de loja, sem o contexto logistico Nacom. Reforca em camada-tool o contrato de isolamento de `app/hora/CLAUDE.md` via `skills=sorted(SKILLS_PERMITIDAS)` (SDK 0.1.77+): skills do dominio Nacom Goya ficam rejeitadas pelo Skill tool. ~2172 LOC, 17 arquivos Python, status M2.

**LOC**: ~2172 (+34 testes em tests/agente_lojas) | **Arquivos**: 17 (Python) | **Status**: M2 SDK completo + UX hardened (markdown render, TodoWrite UI, SessionStore opcional, historico de sessoes na UI, 34 testes automatizados) | **Atualizado**: 06/06/2026

Agente dedicado ao pessoal das Lojas Motochefe (HORA), endpoint `/agente-lojas/*`.
Compartilha SDK com `app/agente/` mas com system_prompt, skills, subagents e
escopo de dados isolados.

> **Skills ativas** (`config/skills_whitelist.py`): `consultando-estoque-loja`, `rastreando-chassi` (M1) + `acompanhando-pedido`, `conferindo-recebimento`, `consultando-pecas-faltando` (M2) + `lendo-arquivos`, `exportando-arquivos`, `orientador-loja` (subagent M2).

> **Barreira SDK adicional** (M2 SDK + skills option 0.1.77+): `build_options()` passa `skills=sorted(SKILLS_PERMITIDAS)` em `ClaudeAgentOptions`. SDK injeta patterns granulares `Skill(consultando-estoque-loja)`, `Skill(rastreando-chassi)`, etc. em allowed_tools (verificado em `_internal/transport/subprocess_cli.py:165-201:_apply_skills_defaults`). Skills do dominio Nacom Goya **rejeitadas pelo Skill tool** — defesa em profundidade do contrato `app/hora/CLAUDE.md`. Doc oficial: "context filter, not sandbox" — files das skills continuam acessiveis via Read/Bash, can_use_tool segue como barreira de seguranca real.

---

## Porque existe um agente separado

Contrato de isolamento do `app/hora/CLAUDE.md` proibe cross-module entre
HORA, Motochefe-distribuidora e Nacom logistico. Consequencia: o agente
logistico (com ~28K de contexto sobre carteira, frete, Odoo, SSW) nao deve
atender operador de loja — e vice-versa. System prompts, skills e subagents
divergem radicalmente; misturar cria branching por perfil em dezenas de
locais.

Decisao (2026-04-22): novo modulo `app/agente_lojas/` reusando infra do SDK.

Ver proposta completa e decisoes D1-D7 na conversa de spawn.

---

## Estrutura

```
app/agente_lojas/
|-- __init__.py                    # Blueprint + init_app
|-- CLAUDE.md                      # Este arquivo
|-- decorators.py                  # @require_acesso_agente_lojas
|-- config/
|   |-- __init__.py
|   |-- settings.py                # AgentLojasSettings (model, prompt paths, skills)
|   |-- skills_whitelist.py        # Lista de skills permitidas (M1+)
|   `-- permissions.py             # can_use_tool (M2 SDK — AskUserQuestion + /tmp)
|-- prompts/
|   |-- system_prompt.md           # Identidade + regras operacionais da loja
|   `-- preset_operacional.md      # Tools + safety + /tmp
|-- services/
|   |-- __init__.py
|   `-- scope_injector.py          # Injeta loja_hora_id no user_prompt_submit
|-- sdk/
|   |-- __init__.py                # Re-exports (get_lojas_client, stream_lojas_chat)
|   |-- client.py                  # AgentLojasClient (build_options + stream_response)
|   |-- client_pool.py             # Event loop persistente (M2 SDK Fase B)
|   `-- hooks.py                   # UserPromptSubmit + PreToolUse (M2 SDK)
|-- routes/
|   |-- __init__.py                # Blueprint agente_lojas_bp
|   |-- chat.py                    # POST /agente-lojas/api/chat (SSE)
|   |-- sessions.py                # Listar/deletar sessoes filtrando agente='lojas'
|   |-- health.py                  # GET /agente-lojas/api/health
|   `-- user_answer.py             # POST /agente-lojas/api/user-answer (M2 SDK)
`-- templates/agente_lojas/
    `-- chat.html                  # UI de chat com modal AskUserQuestion (M2 SDK)
```

---

## Reuso vs exclusivo

> **ESTADO REAL (corrigido 2026-06-26 apos estudo).** A tabela anterior estava
> ERRADA: afirmava reuso de `sdk/client.py` (AgentClient), `sdk/hooks.py`
> (build_hooks), `sdk/memory_injection.py` e `sdk/client_pool.py` que **nunca
> existiu**. O modulo tem um **fork proprio** `AgentLojasClient` (~350 LOC, NAO
> herda AgentClient) e reusa o web so por **imports pontuais**. Esse fork driftou
> para tras (ver Gotcha 0). A intencao original "nao duplicar — parametrize" e o
> alvo P2, ainda nao realizado.

| Realmente reusado de `app/agente/` (import) | Fork proprio deste modulo |
|---------------------------------------------|---------------------------|
| `sdk/session_store_adapter.py` (`get_or_create_session_store`) | `sdk/client.py` (AgentLojasClient — NAO herda AgentClient) |
| `sdk/pricing.py` (`turn_cost_from_cumulative`) | `sdk/client_pool.py` (so event loop; nao reusa o client) |
| `sdk/pending_questions.py` (AskUser cross-worker Redis) | `sdk/hooks.py` (proprio; web tem build_hooks) |
| `sdk/subagent_reader.py` (`get_subagent_findings`) | `config/permissions.py` (proprio; reusa pending_questions) |
| `models.py` (AgentSession, AgentMemory) | `config/settings.py` (subclass de AgentSettings) |
| `config/settings.py` (AgentSettings base) | `prompts/*`, `services/scope_injector.py`, `routes/*`, `templates/*` |

**NAO reusado** (gap deliberado): `sdk/memory_injection.py` — o fork NAO injeta
memoria (isolamento por OMISSAO; M3 pendente); `prompts/` e briefing Nacom.

**Decisao P2 (estudo 2026-06-26):** CONVERGIR para reusar o `AgentClient` web
parametrizado por perfil (o "nao duplicar" original), **GATED em M3**
(particionar `memory_injection` por coluna `agente`). Reusar antes disso vaza
memoria logistica Nacom para o operador de loja. Ver Gotcha 0 + fase M3.

---

## Autorizacao

Decorator unico em `decorators.py:require_acesso_agente_lojas`:

```python
# Permite:
#  - current_user.sistema_lojas == True
#  - current_user.perfil == 'administrador' (admin ve todos)
# Nega para todos os outros.
```

Reusa metodo `current_user.pode_acessar_lojas()` ja existente em
`app/auth/models.py:169`.

---

## Escopo de dados por loja

Hook `_user_prompt_submit` injeta a cada turno:

```xml
<loja_context>
  loja_ids_permitidas: [3]       <!-- usuario escopado -->
  loja_default: 3
  pode_ver_todas: false
</loja_context>
```

Para admin (Rafael):
```xml
<loja_context>
  loja_ids_permitidas: null      <!-- todas -->
  pode_ver_todas: true
</loja_context>
```

Fonte de verdade: `current_user.lojas_hora_ids_permitidas()`.
Skills e subagents DEVEM ler esse contexto e filtrar queries SQL
(`AND loja_id = ANY(...)`).

---

## Particao de sessoes e memorias

Coluna `agente` adicionada em `agent_sessions` e `agent_memories`
(migration `scripts/migrations/2026_04_22_add_agente_coluna.{py,sql}`):

- `'web'` = agente logistico Nacom (valor legado/default)
- `'lojas'` = agente Lojas HORA

Listagens e retrieval DEVEM filtrar por `agente=<valor>` para evitar
cross-contamination.

**M0**: sessoes sao tagueadas corretamente. Retrieval de memoria ainda
compartilha com 'web' (nao e critico enquanto nao houver memorias).
**M3 (convergencia F2 — COMPLETA 2026-06-29):** isolamento por `agente_id` no
agente web cobre TODAS as queries de memoria empresa/user do modulo de injecao
(`default='web'` aditivo, web inalterado, fork ainda em air gap):
- **Caminho do `_load`** (fatia 1+2): Tier 1/1.5/1.6, materializacao Tier 2/KG,
  fallback, `operational_directives` (M10), `session_window`+`resolved_pendencias`
  (M08/M09 via `get_by_path_for_agent`), `routing_context`+dominio (M11/M12),
  canal L1 `user_rules` (R01), `intersession_briefing` (B01-B03), busca semantica
  pgvector+fallback (E01).
- **PreToolUse hooks** (fatia 2): `get_skill_reminders_for_session` (M13) e
  `_load_enforce_directives` (cache key inclui agente) — query JA filtra; o WIRING
  do `agente_id` nesses callers (via `build_hooks`) e F3.
Review adversarial 4-dim + code-review app-wide (34 agentes) feitos.
**Fase 1 (fundação de ESCRITA/UI) estrutural feita**: constraint
`(user_id,path,agente)` (migration `2026_06_30_constraint_agente_memoria`),
`create_file/create_directory(agente=)`, ContextVar `_current_agent_id` (infra),
rotas `/agente/api/sessions*` filtram `agente='web'`. 22 commits, 554 testes + 1 skip.
**PENDENTE — "motor único" (sessão de contexto cheio):** parametrizar AgentClient
por perfil + wiring `agente_id` (build_hooks/rotas) + memory_mcp_tool/jobs por
agente + migrar `app/agente_lojas/` p/ `get_client('lojas')` e aposentar o fork.
Plano consolidado (ETAPAS 1-3) no handoff
`docs/superpowers/plans/2026-06-29-convergencia-agente-lojas-handoff.md`.

---

## Fases de evolucao

| Fase | Escopo | Status |
|------|--------|--------|
| M0   | Esqueleto: endpoint, auth, menu dual, prompt stub | **Concluido** |
| M1   | Skills M1: `consultando-estoque-loja`, `rastreando-chassi` + system prompt + hook `<loja_context>` | **Concluido** |
| M2 (skills) | `acompanhando-pedido`, `conferindo-recebimento`, `consultando-pecas-faltando`, subagent `orientador-loja` | **Concluido** |
| M2 (SDK Fase A) | AskUserQuestion + can_use_tool + frontend rico (tool_call/tool_result/thinking/error/modal ask) | **Concluido** (2026-05-09) |
| M2 (SDK Fase B) | Event loop persistente + output_format + stderr_callback + max_budget_usd + barreira SDK skills | **Concluido** (2026-05-09) |
| M2 (SDK Fase C) | Hooks PostToolUse audit + permissions hardening | **Concluido** (2026-05-09) |
| M2 (UX P0) | Markdown rendering (marked + DOMPurify), TodoWrite progress UI, 34 testes (can_use_tool, scope_injector, todos parser) | **Concluido** (2026-05-09) |
| M2 (UX P1) | PostgresSessionStore opt-in (`AGENT_LOJAS_SESSION_STORE_ENABLED`), historico de sessoes no UI (dropdown + nova sessao) | **Concluido** (2026-05-09) |
| M3   | Venda + isolamento total de memoria + Cost tracking granular por subagente | **Parcial** — skill `consultando-venda-loja` na whitelist (`SKILLS_DOMINIO_HORA`); **cost tracking por turno corrigido** (delta via `turn_cost_from_cumulative`, FIX 2026-06-26); **convergencia F0+F1 + F2/M3 COMPLETA** (isolamento de memoria por `agente_id` em TODO o modulo de injecao — `_load` + PreToolUse hooks; default='web' aditivo; review adversarial; 17 commits, 145 testes) — branch `worktree-convergencia-agente-lojas`, handoff `2026-06-29-convergencia-agente-lojas-handoff.md`. **PENDENTE: F2 P1/P2 (escrita) + F3** (reuso do AgentClient web por perfil — gated por F2, agora verde; ver Gotcha 0) |
| M4   | Analytics (apos fase financeira HORA) | Planejado |

---

## Gotchas

0. **Multi-turno = `resume`, NUNCA `session_id` (FIX S1 2026-06-26).** `build_options`
   passa `resume=sdk_session_id` (--resume CARREGA o `{id}.jsonl`) a partir do
   turno 2, **sem** setar `session_id` (--session-id apenas NOMEIA; --session-id +
   --resume exige --fork-session e forkar X->X = exit code 1). Espelha
   `_with_resume` do agente web (`app/agente/sdk/client.py:2842`).
   **Turno 1 (F1.5 2026-06-28):** quando `our_session_id` (nosso UUID) e passado,
   `build_options` PRE-NOMEIA o JSONL via `session_id=our_session_id` (SEM resume)
   — elimina a captura assincrona fragil via SystemMessage (race: se nao chega, o
   turno 2 perde o resume -> amnesia). ADITIVO e mutuamente exclusivo com o resume
   (o ramo `if sdk_session_id` ja tratou o turno 2+), preservando o invariante
   acima. Espelha web `client.py:1655-1663`. O bug original:
   o modulo so passava `session_id` reusando o id do turno anterior -> amnesia +
   colisao de JSONL ("nao responde 2 perguntas sequenciais"). O `SessionStore`
   agora e **default ON** (`AGENT_LOJAS_SESSION_STORE_ENABLED=True`) para que o
   `{id}.jsonl` seja materializavel do Postgres cross-worker; um **probe**
   (`_store.load`) em `stream_response` REMOVE o `resume` se a sessao nao existir
   no store (evita --resume de JSONL inexistente). A resposta do **assistant**
   passou a ser persistida em `agent_sessions.data['messages']` (antes so o turno
   do usuario), e o custo e gravado em **delta** via `turn_cost_from_cumulative`
   (antes somava o acumulado cru do SDK -> inflacao ~Nx). **Robustez P1 alinhada
   ao web (2026-06-26):** timeouts 300s/1740s (era 240s/540s — cortavam skill
   pesada/subagente), `max_turns` removido (era 20 — cortava respostas
   multi-step) com guard de runaway por `max_budget_usd` default 1.5 USD, stderr
   do CLI capturado no drain p/ diagnostico de ProcessError, e read-back de
   observabilidade dos findings do subagente no SubagentStop (validacao
   anti-alucinacao Haiku = M3/P2).

1. **Nao importar** `app/motochefe/` ou `app/carvia/` direto neste modulo
   (contrato de isolamento HORA). Se precisar de dado da Motochefe como
   fornecedor, consultar via `hora_nf_entrada`.

2. **AgentClient esta em `app/agente/sdk/client.py`** — reuso por import,
   nao copiar.

3. **Template `chat.html`** usa mesmo pattern SSE do `agente/templates/agente/chat.html`
   mas aponta para `/agente-lojas/api/chat`. URLs DEVEM usar `url_for('agente_lojas.X')`.

4. **Sessoes sao marcadas com `agente='lojas'` no insert**. Listagem
   deve SEMPRE incluir `.filter_by(agente='lojas')`.

5. **`<script>` do chat DEVE ficar em `{% block scripts %}`, NUNCA em
   `{% block content %}`.** No `base.html` o `bootstrap.bundle.min.js` carrega
   DEPOIS do `{% block content %}` e ANTES do `{% block scripts %}`. Um IIFE
   no content que use `bootstrap`/`jQuery` em parse-time (ex.:
   `new bootstrap.Modal(...)`) estoura `ReferenceError`, aborta o script
   inteiro e o `addEventListener('submit')` nunca registra -> o `<form>` faz
   submit nativo (reload: "tela pisca e a mensagem some"). Regressao coberta
   por `tests/agente_lojas/test_chat_template.py`.

6. **Fetch POST `/agente-lojas/api/*` DEVE enviar header `X-CSRFToken`**
   (lido de `<meta name="csrf-token">`). `CSRFProtect` e global
   (`app/__init__.py`) e estas rotas NAO estao isentas — sem o header o POST
   retorna 400.

---

## Referencias

- `app/hora/CLAUDE.md` — contrato de isolamento do modulo HORA
- `app/agente/CLAUDE.md` — guia dev do agente logistico (infra reusada)
- `app/auth/models.py:169-184` — pode_acessar_lojas() + lojas_hora_ids_permitidas()
- `scripts/migrations/2026_04_22_add_agente_coluna.{py,sql}` — migration coluna agente
