<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-30
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

Agente separado (decisao 2026-04-22) que REUSA o motor do SDK do agente web por perfil (`get_client('lojas')`) mas atende so o operador de loja, sem o contexto logistico Nacom. Reforca em camada-tool o contrato de isolamento de `app/hora/CLAUDE.md` via `skills` (allow-list) + tool surface fechado (ZERO MCP Nacom): skills/dados do dominio Nacom Goya ficam fora do alcance da loja. ~1305 LOC, 13 arquivos Python; o fork proprio `AgentLojasClient` foi APOSENTADO na FASE B.

**LOC**: ~1305 (config/services/routes/prompts; o MOTOR do SDK vem de `app/agente/`) | **Arquivos**: 13 (Python) | **Status**: MOTOR UNICO em PROD — cutover (E3.8b+E3.9) + FASE B (fork aposentado, flag removida) | **Atualizado**: 30/06/2026

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
|   |-- settings.py                # AgentLojasSettings (model, prompts, tools_enabled RESTRITO, skills) — perfil do motor
|   |-- skills_whitelist.py        # Allow-list HORA (SKILLS_PERMITIDAS) + SUBAGENTS_PERMITIDOS={orientador-loja}
|   `-- permissions.py             # can_use_tool HORA (_DANGEROUS_BASH_PATTERNS + /tmp); le o registry de contexto do motor web (re-export)
|-- prompts/
|   |-- system_prompt.md           # Identidade + regras operacionais da loja
|   `-- preset_operacional.md      # Tools + safety + /tmp
|-- services/
|   |-- __init__.py
|   `-- scope_injector.py          # Monta <loja_context> (consumido pelo hook E3.8a do motor)
|   # NOTA: o SDK NAO vive aqui — o motor vem de app/agente/sdk/ via get_client('lojas')
|   #       (fork sdk/ APOSENTADO na FASE B 2026-06-30)
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

## Reuso do motor web (cutover CONCLUIDO)

> **ESTADO (2026-06-30, FASE B).** O cutover do MOTOR UNICO esta concluido em PROD:
> a rota `/agente-lojas` usa o `AgentClient` web por perfil — `get_client('lojas')`
> produz settings/skills(allow-list)/agents({orientador-loja})/hooks/memoria/
> `<loja_context>` isolados por `agente='lojas'`. O fork proprio `AgentLojasClient`
> (`sdk/`) foi **APOSENTADO** (deletado). O "nao duplicar — parametrize" foi realizado.

| Vem do MOTOR web `app/agente/` | EXCLUSIVO do perfil 'lojas' (este modulo) |
|--------------------------------|-------------------------------------------|
| `sdk/client.py` (AgentClient via `get_client('lojas')`), `sdk/client_pool.py` (loop), `sdk/hooks.py` (`build_hooks(agente_id='lojas')`), `sdk/memory_injection.py` (isolada por agente), `config/permissions.py` (registry de contexto UNICO + ContextVars) | `config/settings.py` (AgentLojasSettings: model/prompts/`tools_enabled` restrito/`empresa_briefing_path=''`), `config/skills_whitelist.py`, `config/permissions.py` (`can_use_tool` HORA — `_DANGEROUS_BASH_PATTERNS`), `services/scope_injector.py` (`<loja_context>`), `prompts/*`, `routes/*`, `templates/*` |

O isolamento (briefing vazio, skills allow-list, agents={orientador-loja}, **ZERO MCP
Nacom**, `<loja_context>`, memoria por agente, sem hints/contexto Nacom) e' garantido
por gates por `agente_id` no motor (E1.2/E2.4/E3.8a + fix do tool surface) — provado por
`tests/agente/test_client_por_perfil.py`, `test_tool_surface_isolamento_perfil.py`,
`sdk/test_loja_context_perfil.py`, `sdk/test_memory_isolation_por_agente.py`. Detalhe +
file:line: handoff `docs/superpowers/plans/2026-06-29-convergencia-agente-lojas-handoff.md`.

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
rotas `/agente/api/sessions*` filtram `agente='web'`.
**MOTOR ÚNICO — CUTOVER + FASE B CONCLUIDOS EM PROD (2026-06-30):** a rota
`/agente-lojas` usa SEMPRE `get_client('lojas').stream_response()` (`routes/chat.py`
`_drain_via_motor`: seta os ContextVars web `agente='lojas'`+`loja_scope`, serializa
`StreamEvent`→SSE no formato do frontend lojas, `can_use_tool` HORA de `config/permissions`).
O motor produz settings/skills(allow-list)/agents({orientador-loja})/sem-briefing-Nacom
(E1.2); `build_hooks(agente_id='lojas')` isola memória/skill-reminders/enforce + injeta
`<loja_context>` (ContextVar `_current_loja_scope`) + suprime hints Nacom no PreToolUse
(E2.4/E3.8a); `memory_mcp_tool`/jobs gravam/leem por `get_current_agent_id()`. **2 rodadas
de revisão adversarial** corrigiram o **CRÍTICO** de isolamento — o perfil 'lojas' herdava o
tool surface Nacom (`allowed_tools` web + `mcp__*`): agora `AgentLojasSettings.tools_enabled`
é restrito e `_register_mcp` pula MCP p/ 'lojas' (**ZERO MCP**). **FASE B:** o fork
`AgentLojasClient` (`sdk/client.py`/`client_pool.py`/`hooks.py`/`__init__.py`) foi APOSENTADO
e a flag `AGENT_LOJAS_USA_MOTOR_UNICO` removida (rota usa o motor incondicionalmente). Migration
`uq_user_memory_path_agente` aplicada em PROD. Plano/file:line: handoff
`docs/superpowers/plans/2026-06-29-convergencia-agente-lojas-handoff.md` §"CUTOVER FEITO".

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
| M3   | Venda + isolamento total de memoria + Cost tracking granular por subagente | **Parcial** — skill `consultando-venda-loja` na whitelist (`SKILLS_DOMINIO_HORA`); **cost tracking por turno corrigido** (delta via `turn_cost_from_cumulative`, FIX 2026-06-26); **convergencia F0+F1 + F2/M3 COMPLETA** (isolamento de memoria por `agente_id` em TODO o modulo de injecao — `_load` + PreToolUse hooks; default='web' aditivo; review adversarial; 17 commits, 145 testes) — handoff `2026-06-29-convergencia-agente-lojas-handoff.md`. **F3 (MOTOR UNICO) CONCLUIDO em PROD (2026-06-30):** cutover E3.8b+E3.9 + FASE B (fork aposentado, flag removida, tool surface fechado) — ver seção "Particao de sessoes". |
| M4   | Analytics (apos fase financeira HORA) | Planejado |

---

## Gotchas

0. **Multi-turno = `resume`, NUNCA `session_id` (FIX S1).** O MOTOR (`get_client('lojas')`)
   trata o resume: turno 2+ usa `resume=sdk_session_id` (--resume CARREGA o `{id}.jsonl`)
   **sem** `session_id` (--session-id + --resume = exit code 1); turno 1 PRE-NOMEIA o JSONL
   via `session_id=our_session_id` (anti-amnesia — elimina a captura assincrona fragil do
   sdk_session_id). Mecanica GENERICA do motor web (`_with_resume` `client.py:2842`,
   `_build_options`), identica para 'web' e 'lojas'. O `SessionStore` (default ON via
   `AGENT_LOJAS_SESSION_STORE_ENABLED`) materializa o `{id}.jsonl` do Postgres cross-worker;
   o custo e gravado em **delta** via `turn_cost_from_cumulative`. Garantia do perfil lojas:
   `tests/agente_lojas/test_motor_resume_options.py`.

1. **Nao importar** `app/motochefe/` ou `app/carvia/` direto neste modulo
   (contrato de isolamento HORA). Se precisar de dado da Motochefe como
   fornecedor, consultar via `hora_nf_entrada`.

2. **O motor do SDK vive em `app/agente/sdk/` (NAO neste modulo).** O perfil lojas e
   servido por `get_client('lojas')` — NAO ha mais fork `AgentLojasClient` (aposentado na
   FASE B). Para mudar o comportamento do agente lojas: editar o PERFIL (`config/settings.py`
   tools_enabled/skills, `config/permissions.py` can_use_tool) ou o gate por `agente_id` no
   motor; NUNCA recriar um client proprio neste modulo.

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
