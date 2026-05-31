# Agente Web — SDK Changelog (0.1.49 → 0.2.87)

> Historico de adocoes, breaking changes, bug fixes e features NAO adotadas do
> Claude Agent SDK + Anthropic SDK Python. Extraido de `CLAUDE.md` para reducao de ruido.
>
> **Atualizado**: 2026-05-25 (SDK 0.2.87 + CLI 2.1.150 + adocao tardia das Task* tools)

---

## Modelo default: Opus 4.7 → 4.8 (2026-05-28)

**Sem mudanca de versao de SDK** (`claude-agent-sdk==0.2.87`). Troca apenas do modelo default.

### Migracao Opus 4.7 → 4.8 (2026-05-28)
- `config/settings.py`: default `model="claude-opus-4-8"`; `MODEL_PRICING` ganha `'claude-opus-4-8': (5.00, 25.00)` (4.7/4.6/4.5 mantidos como legado); fallback de `calculate_cost` aponta para 4.8.
- `sdk/pricing.py`: `DEFAULT_MODEL='claude-opus-4-8'` + entrada no `MODEL_PRICING`.
- `config/feature_flags.py`: `TEAMS_DEFAULT_MODEL` default `claude-opus-4-8`.
- `config/agent_loader.py`: aliases `opus-4-8`/`opus_4_8` adicionados ao `_MODEL_MAP` (4.7/4.6 mantidos).
- `routes/chat.py` + `agente_lojas/routes/chat.py`: fallback de modelo `claude-opus-4-8`.
- UI: `templates/agente/chat.html` (2 dropdowns) + `static/agente/js/chat.js` (registry MODEL_INFO; 4.7/4.6 viram "Opus (legado)").
- **Rollback instantaneo** via env vars: `AGENT_MODEL=claude-opus-4-7` + `TEAMS_DEFAULT_MODEL=claude-opus-4-7` (ou `claude-opus-4-6`).
- **Breaking changes**: NENHUMA. Opus 4.8 mantem a mesma superficie de API que 4.7 (adaptive thinking only; `temperature/top_p/top_k` e `budget_tokens` ja removidos no 4.7; prefill de assistant removido — nada disso usado). Mesmo preco $5/$25 per MTok, 1M context, 128K max output.
- **Comportamento** (re-tuning opcional, nao aplicado): 4.8 narra mais entre tool calls e e mais deliberado/pergunta mais; mais conservador para acionar subagentes/memoria/custom tools (steerable via prompt). `xhigh` effort continua valido (4.7/4.8).

---

## SDK 0.2.83 → 0.2.87 (atualizado 2026-05-25) — CLI bumps + adocao tardia Task* tools

**Versao**: `claude-agent-sdk==0.2.87` (CLI bundled 2.1.150) + `anthropic==0.98.1`
**Bumps intermediarios**: 0.2.83 (CLI 2.1.146), 0.2.84 (2.1.147), 0.2.85 (2.1.148), 0.2.86 (2.1.149)

### Mudancas no SDK Python (zero!)

Diff GitHub `v0.2.82...v0.2.87`: **19 commits, 10 arquivos modificados, ZERO arquivos `src/` do SDK Python**.
Todas as 5 versoes sao apenas CLI bundled bumps (2.1.143 → 2.1.150). A unica mudanca nao-bump foi
em CI workflows (#984: Workload Identity Federation, escopo interno Anthropic).

### Mudanca real do PROJETO: adocao das Task* tools (descoberta retroativa)

A breaking change `TodoWrite -> TaskCreate/TaskUpdate/TaskGet/TaskList` foi **introduzida no 0.2.82**
(ver secao abaixo), mas **passou despercebida** ate este upgrade — release notes oficial do 0.2.82
no GitHub tem secao `### Breaking` que **nao consta no `CHANGELOG.md` do repo** (lugar onde a doc
projeto havia se baseado).

**Investigacao retroativa em 2026-05-25 (apos upgrade):**
- Consulta `claude_session_store` mtime >= 2026-05-16 mostra: TaskCreate/Update/Get/List em 54 rows
  cada como `deferred_tools_delta` (listing) — mas ZERO invocacoes reais (`tool_use` blocks).
  TodoWrite tambem ZERO invocacoes reais nesse periodo.
- Top tools usadas em prod (>= 16/05): Bash 611, mcp__sql 227, Read 120, mcp__schema 72,
  ToolSearch 71, Grep 70, Edit 38, Skill 33, Glob 24, Agent 21.
- **Conclusao**: codigo que reagia a TodoWrite era morto **pre-existente** (agente nunca chamou
  TodoWrite mesmo antes do upgrade). Quebra do 0.2.82 sem impacto pratico observado.

**Decisao**: ativar TaskCreate proativamente — instrumentar parser + UI + system_prompt para que,
quando o agente comecar a usar (orientado pela nova secao `<task_management>` no system prompt),
a UI ja renderize progresso em tempo real.

### Arquivos modificados (12 — adocao Task* tools)

| # | Arquivo | Mudanca |
|---|---------|---------|
| 1 | `app/agente/sdk/client.py` | `_extract_tool_description` (L626): 4 branches Task* (description amigavel). Novos helpers estaticos `_extract_task_id_from_text`, `_parse_task_list_output`, e metodo `_build_task_event(tool_name, original_input, result_content)`. No `_parse_sdk_message` UserMessage handler: emite `task_event` com `{action, task_id, subject?, tasks?, status?}` apos `tool_result` quando tool e Task* e nao houver erro. Usa `raw_result_content` (sem truncamento de 500 chars) para evitar parser quebrar TaskList grande. |
| 2 | `app/agente_lojas/sdk/client.py` | Remove `_try_parse_todos`. Adiciona `_build_task_event_from_result(content)` — handler standalone sem state, detecta tipo por regex no texto: `'Task #N created'`, `'Updated task #N'`, ou linhas `'#N [status] subject'`. Limitacao documentada: perde `description` do TaskCreate e detalhes extras do TaskUpdate (compensado via snapshot do TaskList). `ALLOWED_TOOLS_M1` substitui `'TodoWrite'` pelas 4 Task* tools. |
| 3 | `app/agente/config/settings.py:66` | `tools_enabled` substitui `'TodoWrite'` por 4 Task* tools (TaskOutput/TaskStop ja presentes pre-existentes). |
| 4 | `app/agente/services/tool_skill_mapper.py:76` | `TOOL_TO_CATEGORY` substitui `'TodoWrite'` por 4 entradas Task* -> `'Gestao de Tarefas'`. |
| 5 | `app/agente_lojas/config/permissions.py:282` | Comentario atualizado. Allow direto continua (sem logica adicional). |
| 6 | `app/agente/routes/chat.py:809` | Novo handler `elif event.type == 'task_event'` apos handler 'todos' (back-compat). Emite SSE `task_event` com payload `{action, task_id?, subject?, tasks?, status?}`. R8 (contrato 3 camadas) preservado. |
| 7 | `app/static/agente/js/chat.js` | `toolIcons` (L684) substitui TodoWrite por 4 icons Task*. `updateTodoList` agora aceita formato canonical Task* (`{task_id, status, subject}`) via helper `_normalizeTodoItem` — formato antigo TodoWrite (`{status, content, activeForm}`) preservado p/ back-compat. Novo case `'task_event'` no switch SSE, com 3 actions: `created` (push), `updated` (merge por task_id), `snapshot` (replace). |
| 8 | `app/agente_lojas/templates/agente_lojas/chat.html` | Refatora `appendTodos` para usar `Map<task_id, task>` interno (`currentTasks`) + helper `_renderTasks()` ordenado por task_id numerico. Novo handler `appendTaskEvent(meta)` espelha logica do Nacom. `appendTodos` mantido para back-compat. Case `'task_event'` adicionado no SSE switch. |
| 9 | `app/agente_lojas/prompts/preset_operacional.md:3` | Substitui `"TodoWrite"` por `"TaskCreate, TaskUpdate, TaskGet, TaskList"` na lista de tools disponiveis. |
| 10 | `app/agente/prompts/system_prompt.md` (fim) | Novo bloco `<task_management>` orientando uso de TaskCreate/Update/List em tarefas 3+ acoes ou multi-step. Exemplo concreto (auditoria de carteira P1-P7). NAO usar para tarefas triviais. Status validos enumerados. |
| 11 | `app/agente/CLAUDE.md` | Bump versao + tabela eventos (`todos` -> `task_event`). |
| 12 | `requirements.txt` | `claude-agent-sdk==0.2.82` -> `0.2.87`. |

### Shape canonical do evento SSE `task_event`

```javascript
// Backend emite (3 actions):
{ type: 'task_event', content: { action: 'created', task_id: '1', subject: '...', description: '...', status: 'pending' } }
{ type: 'task_event', content: { action: 'updated', task_id: '1', status: 'completed' } }
{ type: 'task_event', content: { action: 'snapshot', tasks: [{ task_id, status, subject }, ...] } }

// SSE achatado (chat.py:_sse_event ou agente_lojas route._sse):
event: task_event
data: { "action": "created", "task_id": "1", "subject": "...", "description": "...", "status": "pending" }
```

### Limitacoes conhecidas (documentadas)

- **Agente Lojas**: parser standalone (sem `state.tool_calls` arquivado) entao detecta tipo por
  regex no output texto. Perde `description` do TaskCreate e detalhes extras do TaskUpdate
  (ex: novo `subject`). Compensado pela snapshot do TaskList quando agente lista.
- **Output do CLI e texto formatado, nao JSON**: parser regex pode quebrar se CLI mudar formato
  no futuro (ex: 'Task #N created successfully:' -> outro literal). Mitigacao: helpers
  isolados, fix por regex update.
- **Sem testes unitarios** ainda — apenas smoke test inline validou todos os parsers em
  isolamento (executado em 25/05/2026 antes do commit).

### Validacao recomendada (pos-deploy)

1. **Restart workers** apos `pip install -r requirements.txt`
2. **Sanity check**: invocar agente com prompt multi-step ("audita a carteira completa") e
   confirmar emissao de evento `task_event` (logs `[AGENT_SDK]` + DevTools Network SSE)
3. **Frontend**: verificar painel de tarefas renderizando no chat (mesmo onde TodoWrite
   nunca apareceu)
4. **Sentry**: monitorar janela de 24h para erros `Falha ao emitir task_event` no log
   (esperado: zero) ou TypeErrors no chat.js
5. **Local dev**: `.venv/bin/pip install --upgrade claude-agent-sdk==0.2.87`

### CLI bundled bumps consecutivos

| SDK | CLI |
|-----|-----|
| 0.2.83 | 2.1.146 |
| 0.2.84 | 2.1.147 |
| 0.2.85 | 2.1.148 |
| 0.2.86 | 2.1.149 |
| 0.2.87 | 2.1.150 |

> Cadence: 1 CLI bump por SDK release (commits intermediarios 2.1.143/144/145 nunca foram
> publicados como SDK release — apenas o 2.1.146 foi). Ver `git log` no repo CLI para detalhe.

Bumps sequenciais sem changelog detalhado (release notes de cada um sao apenas "Updated bundled
Claude CLI to version X"). Cadence sugere alta estabilidade. Unica mudanca nao-bump foi CI
Workload Identity Federation (#984), escopo interno Anthropic.

---

## SDK 0.2.82 (atualizado 2026-05-16, revisao 2026-05-25) — stderr callback isolation + EffortLevel + CVE mcp + ⚠️ 2 BREAKING omitidas

> **NOTA DE REVISAO (2026-05-25)**: A documentacao original deste upgrade BASEOU-SE no
> `CHANGELOG.md` do repo (que NAO listava breakings). Investigacao retroativa via release notes
> do GitHub (`https://github.com/anthropics/claude-agent-sdk-python/releases/tag/v0.2.82`)
> revelou secao `### Breaking` AUSENTE DO `CHANGELOG.md` DO REPO (presente apenas na release page do
> GitHub), com **2 mudancas omitidas que existiam ali**:
>
> **Breaking #1 — TodoWrite -> Task* tools**: Headless e SDK sessions agora usam
> `TaskCreate`/`TaskUpdate`/`TaskGet`/`TaskList` em vez de `TodoWrite`. Tool consumers devem
> **acumular por task_id** em vez de substituir snapshot list. **Codigo TodoWrite no projeto
> ficou morto** desde 16/05 (era morto **mesmo antes** do upgrade — agente nunca chamava).
> Refatoracao completa feita em 25/05/2026 — ver secao 0.2.83-0.2.87 acima.
>
> **Breaking #2 — MCP non-blocking por default**: MCP servers conectam em background.
> Sessions iniciam imediatamente e slow servers reportam `status: "pending"` no `init`.
> Override: `MCP_CONNECTION_NONBLOCKING=0` (restaura comportamento antigo, espera 5s) ou
> marcar server `alwaysLoad: true`. **Sem sintoma observado em prod** (0 rows com
> status='pending'/alwaysLoad nas entries de `init` pos-16/05) — MCP servers do projeto
> (memory, schema, sql, sessions, artifact, playwright, render_logs, routes_search,
> teams_card, text_to_sql) inicializam rapido o suficiente. **Sem intervencao necessaria** —
> mas atencao: a query de validacao (rows com `status='pending'`) NAO detecta o failure
> mode real (tool call do 1o turno antes do MCP server estar pronto, que aparece como
> `MCP connection error` no log). **Monitorar pos-deploy 48h** Sentry/logs por
> `MCP.*(connection|server).*error` nos primeiros segundos de cada nova sessao SDK.

**Versao**: `claude-agent-sdk==0.2.82` (CLI bundled 2.1.142) + `anthropic==0.98.1`
**Bumps intermediarios**: 0.1.81 (CLI 2.1.139)

> **Sobre o salto 0.1.81 → 0.2.82**: bump cosmetico (sem breaking changes). Numero
> minor pulou de `.1` para `.2`, e patch pulou de `.81` para `.82` aparentemente para
> alinhar com a serie CLI 2.1.x. Changelog oficial NAO lista nenhuma incompatibilidade
> de API entre 0.1.81 e 0.2.82.

### Bug fixes gratuitos via upgrade

#### BF1: Stderr callback isolation (#932) — BENEFICIO direto ao projeto

**Mecanica antes do 0.2.82**: se um `stderr` callback (passado via
`ClaudeAgentOptions(stderr=...)`) lancasse exception ao processar uma linha,
o stderr reader loop morria silenciosamente, derrubando TODA a captura de
stderr pelo resto da sessao SDK.

**Mecanica depois**: cada linha eh tratada em try/except isolado. Exception
em uma linha NAO afeta entrega das proximas.

**Impacto no projeto**: o projeto usa stderr callback em:
- `app/agente_lojas/sdk/client.py:264-269` — `_stderr_callback` empurra para `queue.SimpleQueue`
- `app/agente/sdk/client.py:1294` — gated por `USE_STDERR_CALLBACK` feature flag

Os callbacks ja tinham try/except defensivo interno (`put_nowait` raise se queue
cheia), mas agora o SDK tambem isola — defesa em profundidade.

#### BF2: CancelledError em eager-flush done callback (#931)

Reduz noise de logs `Exception in callback` durante shutdown quando tasks
de eager-flush pendentes sao canceladas. Sem impacto funcional, apenas
limpeza de log.

#### BF3: `permission_suggestions` type tighter (#955) — sem impacto

`SDKControlPermissionRequest.permission_suggestions` mudou de `list[Any] | None`
para `list[dict[str, Any]] | None`. Projeto NAO constroi esse campo manualmente
(verificado: apenas SDK interno em `_internal/query.py` o le, via
`permission_request.get(...)`). Type stricter, zero adaptacao necessaria.

### Feature documentada mas NAO adotada

#### F12: `EffortLevel` type alias (SDK 0.2.82, #951)

Type publico exportado de `claude_agent_sdk`:
```python
from claude_agent_sdk import EffortLevel
EffortLevel = Literal["low", "medium", "high", "max", "xhigh"]
```

**Status**: NAO adotado. Projeto ja usa strings literais via `effort=` em
`ClaudeAgentOptions` (ex: `effort="xhigh"` para subagentes em `client.py`).
Adocao seria apenas cosmetica (type hint em wrappers proprios). Documentado
como possibilidade futura ao refatorar `agent_loader.py` ou `permissions.py`.

### Doc clarification (sem impacto)

#### D1: Hooks dispatch concorrente (#956)

Doc oficial clarificou que multiplos `HookMatcher` registrados para o MESMO
evento (ex: dois matchers em `PreToolUse`) sao executados em PARALELO, nao
sequencial. Hooks ordering-dependent (rate limiters, gates) precisam ser
combinados em UM matcher.

**Auditoria do projeto** (`app/agente/sdk/hooks.py:1078-1117`): cada evento
tem APENAS UM matcher registrado (`PreToolUse`, `PostToolUse`, `PreCompact`,
`Stop`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`,
`PostToolUseFailure`). Zero dependencia de ordem entre matchers — clarificacao
nao afeta projeto.

### Security update (sem impacto — ja satisfeito)

#### S1: CVE-2025-66416 / GHSA-9h52-p55h-vw2f (#927)

`mcp` dependency lower bound subiu para `>=1.23.0`. Versoes antigas desabilitavam
DNS rebinding protection por default. Projeto ja roda `mcp>=1.26.0` no
`requirements.txt:72` — sem ajuste necessario.

### CLI bundled bumps

- **0.1.81**: CLI 2.1.138 → 2.1.139
- **0.2.82**: CLI 2.1.139 → 2.1.142

Bumps consecutivos sem mudancas API Python. Cadence sugere estabilidade.

### Status pos-upgrade

| Item | Antes (0.1.80) | Depois (0.2.82) |
|------|----------------|-----------------|
| `requirements.txt` | `claude-agent-sdk==0.1.80` | `claude-agent-sdk==0.2.82` |
| CLI bundled | 2.1.138 | 2.1.142 |
| Stderr callback robustness | Exception derrubava reader loop | Isolado por linha |
| `EffortLevel` type | n/a (string literal) | Disponivel mas nao adotado |
| `permission_suggestions` type | `list[Any]` | `list[dict[str, Any]]` (sem uso direto) |
| Hooks ordering | Sem matchers concorrentes | Sem matchers concorrentes (auditado) |
| `mcp` lower bound | satisfeito (>=1.26.0) | satisfeito (>=1.26.0) |

### Validacao recomendada (pos-deploy)

1. **Restart workers** apos `pip install -r requirements.txt`
2. **Sanity check**: invocar agente e verificar log `[SDK]` sem warnings novos
3. **Sentry**: monitorar nova janela de 24h para erros relacionados a
   `stderr`/`permission_suggestions` (esperado: zero)
4. **Local dev**: rodar `.venv/bin/pip install --upgrade claude-agent-sdk==0.2.82`
   para sincronizar com producao

---

## SDK 0.1.80 (atualizado 2026-05-09) — `skills` option + actionable errors + CLI bumps

**Versao**: `claude-agent-sdk==0.1.80` (CLI bundled 2.1.138) + `anthropic==0.98.1`
**Bumps intermediarios**: 0.1.77 (CLI 2.1.133), 0.1.78 (CLI 2.1.136), 0.1.79 (CLI 2.1.137)

### Features adotadas

#### F11: `skills` option em `ClaudeAgentOptions` (SDK 0.1.77, #924) — substitui `"Skill"` em `allowed_tools`

**Mecanica**: novo campo `skills: list[str] | Literal["all"] | None = None` em
`ClaudeAgentOptions`. Quando set, SDK auto-configura `"Skill"` em `allowed_tools`
E `setting_sources` automaticamente. Doc oficial:

> *"This is a context filter, not a sandbox: unlisted skills are hidden from the
> model's listing and rejected by the Skill tool, but their files remain on disk
> and are reachable via Read/Bash."*

Valores:
- `None` (default): nenhuma auto-config; CLI defaults aplicam (NAO eh "skills off").
- `"all"`: habilita todas as skills descobertas via `setting_sources`.
- `list[str]`: habilita apenas as skills listadas (filtro real para o model).

**Forward-compat**: `_check_options_skills_field()` em `client.py` (introspection
via `dataclasses.fields(ClaudeAgentOptions)`). Constante `_SDK_HAS_OPTIONS_SKILLS`
calculada uma vez no import — zero overhead por request. Mesmo padrao usado em
`agent_loader.py` (`_SDK_HAS_NATIVE_FIELDS`, `_SDK_HAS_EFFORT_FIELD`).

**Auto-config interno do SDK** (verificado em
`_internal/transport/subprocess_cli.py:165-201` — `_apply_skills_defaults`):

| `options.skills` | injecao em `allowed_tools` | injecao em `setting_sources` |
|------------------|----------------------------|------------------------------|
| `None` (default) | nenhuma                    | nenhuma (NO-OP)              |
| `"all"`          | `"Skill"` (pattern simples)| `["user", "project"]` se `None` |
| `list[str]`      | `Skill(name)` por entry    | `["user", "project"]` se `None` |

**Importante**: `setting_sources` explicito do caller eh PRESERVADO. O default
`["user", "project"]` so eh aplicado se `setting_sources is None`. Como ambos
agentes passam `setting_sources=["project"]` explicito, nosso valor sobrevive.

**Filtro granular** (descoberta valiosa para `agente_lojas`): com
`skills=list[str]`, o SDK injeta `Skill(name)` por entry — ex:
`Skill(consultando-estoque-loja)`, `Skill(rastreando-chassi)`, etc. Isso eh
filtro de auto-allow PER-SKILL, mais forte que apenas listing filter. Nomes
nao listados em `SKILLS_PERMITIDAS` nao casam o pattern → rejeitados pelo
Skill tool. `tool_name` no `can_use_tool` callback continua sendo `"Skill"`
(nome real do tool no protocolo CLI), nao o pattern — validacoes em
`permissions.py:705` (`tool_name == 'Skill'`) continuam intactas.

**Aplicado em DOIS agentes com estrategias diferentes**:

##### `app/agente_lojas/` — whitelist explicita (defesa em profundidade)
- **Antes**: `'Skill'` em `ALLOWED_TOOLS_M1` + `setting_sources=["project"]`. Operador
  HORA via TODAS as skills do projeto no listing (incluindo skills Nacom Goya como
  `cotando-frete`, `rastreando-odoo`, `gerindo-expedicao` — violacao do contrato de
  isolamento documentado em `app/hora/CLAUDE.md`).
- **Depois**: `skills=sorted(SKILLS_PERMITIDAS)` (7 skills HORA + 2 compartilhadas).
  Skills Nacom ficam ocultas do listing do model. Defesa em profundidade do contrato
  HORA — nao substitui `can_use_tool` (filter, not sandbox).
- **Bonus**: `'Skill'` removida de `ALLOWED_TOOLS_M1` (SDK auto-configura).
  `setting_sources=["project"]` mantido explicito (descobre tambem subagents
  `.claude/agents/orientador-loja.md`).

##### `app/agente/` (Nacom) — `skills="all"` (centralizacao)
- **Antes**: `'Skill'` em `tools_enabled` (settings.py).
- **Depois**: `'Skill'` removida de `tools_enabled`; `options_dict["skills"] = "all"`
  injetado em `_build_options()` apos init do dict. Mantem comportamento (todas as
  skills disponiveis) mas com config centralizada via SDK option.
- **Beneficio**: setting_sources auto-configurado pelo SDK (linha existente
  `setting_sources=["project"|"user"]` em `_build_options:1217` continua valida e
  explicita — a auto-config do SDK eh idempotente).

**Fallback (SDK < 0.1.77)**:
- Ambos agentes injetam `'Skill'` em `allowed_tools` manualmente quando
  `_SDK_HAS_OPTIONS_SKILLS=False`. Log debug emitido em agente Nacom alertando para
  upgrade do `requirements.txt`.

**Arquivos modificados**:
- `requirements.txt:70`: `claude-agent-sdk==0.1.76` -> `claude-agent-sdk==0.1.80`.
- `app/agente_lojas/sdk/client.py`:
  - Imports: adicionado `dataclasses` e `from app.agente_lojas.config.skills_whitelist import SKILLS_PERMITIDAS`.
  - `ALLOWED_TOOLS_M1`: removido `'Skill'`.
  - `_check_skills_option()` + `_SDK_HAS_SKILLS_OPTION` introspection.
  - `build_options()`: aplica `skills=sorted(SKILLS_PERMITIDAS)` ou fallback.
  - Docstring atualizada para mencionar option `skills=`.
- `app/agente/config/settings.py:40-46`: `'Skill'` removida de `tools_enabled` +
  comentario explicativo da deprecation.
- `app/agente/sdk/client.py`:
  - `_check_options_skills_field()` + `_SDK_HAS_OPTIONS_SKILLS` introspection
    (apos import de `MirrorErrorMessage`).
  - `_build_options()`: bloco condicional `skills="all"` ou fallback `'Skill'`
    em `allowed_tools` (apos init do `options_dict`, antes do `session_id`).

**Justificativa do escopo**:
- Whitelist no `agente_lojas` eh ganho real de seguranca/UX — operador nao ve
  skills inaplicaveis. Centralizacao no `agente` Nacom eh ganho de manutenibilidade
  (config unica via SDK option).
- NAO removido `setting_sources=["project"]` explicito (idempotente com auto-config
  do SDK; mantido para descoberta de subagents `.claude/agents/*.md`).

**Rollback rapido**: `claude-agent-sdk==0.1.76` no requirements.txt — codigo continua
funcional (forward-compat detecta ausencia do field, injeta `'Skill'` em
`allowed_tools` automaticamente). Sem mudancas de schema/migration.

#### F12: Actionable error messages apos error result (SDK 0.1.77, #918) — `ProcessError` carrega texto real

**Mecanica**: SDK 0.1.76 e anteriores: qualquer falha do CLI virava
`Command failed with exit code 1` (generico). SDK 0.1.77+: substituiu pela
mensagem real do erro (ex: `"Reached maximum number of turns"`), igual ao TS SDK.

**Aplicabilidade**: `app/agente/sdk/client.py` tem 10+ callsites de `ProcessError`
com comentarios explicitos sobre dificuldade de diagnostico (`# nunca propaga o
stderr real` em `client.py:1362`). Diagnostico de timeouts, max-turns e refusals
melhora automaticamente sem mudanca de codigo.

**Adocao**: GRATIS via upgrade SDK. Nenhum codigo modificado. Comportamento ativo
imediatamente para qualquer ProcessError lancado pelo SDK.

**Beneficio observavel**:
- Logs `[AGENT_CLIENT] ProcessError: ...` agora mostram causa raiz textual.
- Sentry events com mensagem util em vez de `"exit code 1"` generico.
- Stderr callback (`extra_args: {"debug-to-stderr": None}`) continua complementar.

### Bug fixes gratuitos via upgrade (SDK 0.1.78-0.1.80)

- **CLI bumps 2.1.133 -> 2.1.138** (0.1.78, 0.1.79, 0.1.80): tres bumps consecutivos
  sem changelog Python (apenas patch-level no CLI subjacente). Padrao historico:
  bumps adotados via upgrade rotineiro. Cadence de 2 dias entre releases sugere
  estabilidade.

### Features documentadas mas NAO implementadas

- **`skills=[]` (filtro total)**: caso de uso "operar SEM skills" nao existe no
  projeto. Os dois agentes precisam de pelo menos uma skill. `[]` permanece
  documentado como possibilidade futura (ex: agente puramente conversacional).

### Status pos-upgrade

| Item | Antes (0.1.76) | Depois (0.1.80) |
|------|----------------|-----------------|
| `requirements.txt` | `claude-agent-sdk==0.1.76` | `claude-agent-sdk==0.1.80` |
| Agente Nacom — `'Skill'` | em `tools_enabled` | removido; `skills="all"` em options |
| Agente Lojas — `'Skill'` | em `ALLOWED_TOOLS_M1` | removido; `skills=sorted(SKILLS_PERMITIDAS)` |
| Agente Lojas — listing skills | TODAS (~30 skills incluindo Nacom) | 9 skills (7 HORA + 2 compartilhadas) |
| `ProcessError` mensagem | `"Command failed with exit code 1"` | causa raiz textual |
| Forward-compat SDK < 0.1.77 | n/a | injeta `'Skill'` automaticamente |

---

## SDK 0.1.76 (atualizado 2026-05-07) — xhigh subagentes + api_error_status + permission enrichment

**Versao**: `claude-agent-sdk==0.1.76` (CLI bundled 2.1.132) + `anthropic==0.98.1`
**Bumps intermediarios**: 0.1.74 (CLI 2.1.129), 0.1.75 (CLI 2.1.131)

### Features adotadas

#### F4: Permission context enrichment (SDK 0.1.74) — display_name + description

**Mecanica**: `ToolPermissionContext` ganhou `display_name` (ex: "Web Search"), `description`,
`decision_reason`, `blocked_path`, `title`. Bonus 0.1.74: doc clarificou que `can_use_tool`
so dispara em `"ask"` permission decisions, nao em `allow`/`deny`.

**Aplicacao**: `app/agente/config/permissions.py:can_use_tool` extrai `display_name` e
`description` via `getattr` (forward-compat). Logs admin de subagentes ficam mais legiveis.

**Arquivos modificados**:
- `app/agente/config/permissions.py:300-345`: extracao + log enriquecido (ja tinha
  `agent_id`/`tool_use_id` desde SDK 0.1.52).

**Justificativa do escopo**: `decision_reason` redundante (sempre "ask" — ver doc 0.1.74),
`blocked_path` redundante (ja temos `ALLOWED_WRITE_PREFIXES` check).

#### F6: `xhigh` effort level (SDK 0.1.74) — Opus 4.7-specific

**Mecanica**: `"xhigh"` adicionado ao Literal de `effort` em `ClaudeAgentOptions` E
`AgentDefinition`. Entre `high` e `max`. Doc Anthropic: *"the best setting for most coding
and agentic use cases on 4.7, and the default in Claude Code"*. Fallback automatico para
`high` em modelos nao-Opus 4.7. SDK 0.1.60 ja documentava como acessivel via `extra_args`
(workaround); SDK 0.1.74 oficializa no campo nativo.

**Arquitetura adotada**: opcional via frontmatter dos `.claude/agents/*.md` (per-subagente).

- **Parser** (`agent_loader.py`): novo `_check_effort_field()` (introspection), `_VALID_EFFORTS`
  whitelist (`{low, medium, high, xhigh, max}`), parse de `effort` do frontmatter com
  validacao silenciosa (valor invalido = ignora + warn, nao quebra carregamento).
- **Forward-compat**: `agent_kwargs["effort"] = effort` so se `_SDK_HAS_EFFORT_FIELD=True`
  (SDK >= 0.1.74). SDK < 0.1.74: log debug + ignora (subagente herda effort do main).

**Aplicado em** (7 subagentes Opus pesados):
- `analista-carteira.md` — analise multi-step P1-P7 + comunicacao PCP/Comercial
- `auditor-financeiro.md` — reconciliacao Local x Odoo + SEM_MATCH
- `desenvolvedor-integracao-odoo.md` — criar/modificar integracoes (dev-only)
- `especialista-odoo.md` — pipeline Odoo cross-area
- `gestor-recebimento.md` — pipeline 4 fases recebimento
- `gestor-motos-assai.md` — pipeline B2B Q.P.A. Sendas/Assai
- `raio-x-pedido.md` — visao 360 cruzando carteira/entrega/frete

**NAO aplicado em** 6 subagentes Sonnet — `xhigh` em Sonnet faz fallback para `high`,
que ja eh o default do Sonnet 4.6 (no-op efetivo).

**Custo esperado**: 20-40% mais tokens nos 7 Opus vs `high`. Cap atual `MAX_BUDGET_USD=5.0`
permanece como guard. Monitorar `cost_tracker.py` por subagent_type por 7 dias.

**Rollback**: remover linha `effort: xhigh` dos frontmatter dos 6 .md.

**Arquivos modificados**:
- `app/agente/config/agent_loader.py:42-90`: `_check_effort_field()` + `_VALID_EFFORTS`.
- `app/agente/config/agent_loader.py:359-373`: parse de frontmatter `effort` + validacao.
- `app/agente/config/agent_loader.py:391-401`: aplicacao com forward-compat introspection.
- `app/agente/config/agent_loader.py:417-419`: log enriquecido com `effort=xhigh`.
- `.claude/agents/{7 Opus}.md`: linha `effort: xhigh` no frontmatter.

#### F8: `api_error_status` em ResultMessage (SDK 0.1.76) — classificacao granular de falhas API

**Mecanica**: `ResultMessage.api_error_status: int | None` traz HTTP status (429/500/529)
quando `is_error=True`. Permite classificar falhas vs apenas inspecao de string em `errors[]`.
Compoe com `APIStatusError.type` ja adotado em `scanner` e `memory_consolidator`
(anthropic 0.87.0+).

**Aplicacao**:
- **Captura** (`client.py:_parse_sdk_message` handler ResultMessage): `getattr(message,
  'api_error_status', None)` (forward-compat: None se SDK < 0.1.76 ou sem erro).
- **Log enriquecido** (`client.py:980-989`): `http_status={api_error_status}` no log
  de ResultMessage quando preenchido.
- **Propagacao SSE** (`client.py:done event content`): `'api_error_status': api_error_status`.
- **`done_payload`** (`routes/chat.py:910+`): incluido no SSE para frontend.
- **Sentry tag** (`routes/chat.py`): `anthropic_http_status=<code>` + `anthropic_http_5xx=true`
  quando >= 500. Best-effort (try/except), nao quebra stream se Sentry indisponivel.
- **Log warning** (`routes/chat.py`): `"[AGENTE] Anthropic API error: HTTP {code}..."`.

**Beneficio**: distinguir 429 (rate limit, retry imediato) de 529 (overloaded, retry longo)
de 500 (server error real). Permite dashboards `/admin/insights` agruparem por codigo HTTP.

**Arquivos modificados**:
- `app/agente/sdk/client.py:920-1058`: captura + log + propagacao no done event.
- `app/agente/routes/chat.py:910-944`: done_payload + Sentry tag (sem alerta automatico).

### Bug fixes gratuitos via upgrade (SDK 0.1.74-0.1.76)

- **F7: Atexit subprocess cleanup** (0.1.74): SDK registra atexit handler que termina
  subprocesses CLI vivos quando processo Python encerra (anti-zombie no shutdown abrupto).
  Complementa nosso `_force_kill_subprocess` em `client_pool.py` (cobre cenario operacional
  normal). Validar pos-deploy: `kill -9 <gunicorn_worker>` + `ps -ef | grep claude`.
- **F9: PermissionUpdate.from_dict()** (0.1.76): `ToolPermissionContext.suggestions` agora
  vem como `list[PermissionUpdate]` (antes era `list[dict]` raw). Bug fix preventivo —
  nao consumimos `suggestions` no projeto (CLI nao tem UI interativa para gerar regras).
- **ResourceWarning on disconnect** (0.1.74): fix `Unclosed <MemoryObjectReceiveStream>`.
- **Session created_at timestamp** (0.1.74): `list_sessions()` mais nao retorna `None` em
  sessoes cujo primeiro JSONL record nao tem timestamp.

### Features documentadas mas NAO implementadas

#### F3: `strict_mcp_config` (SDK 0.1.74) — DOCUMENTADO, nao adotado

**Mecanica**: quando `True`, CLI usa APENAS `mcp_servers` passados em `ClaudeAgentOptions`,
ignorando project/user/global config (`.mcp.json`).

**Beneficio**: determinismo total DEV vs PROD. Em PROD (Render com `HOME=/tmp`)
provavelmente nao muda nada (sem `.mcp.json`). Em DEV local, evita MCP "fantasma" do
usuario vazar pra agente.

**Quando implementar**: ativar via flag `AGENT_STRICT_MCP_CONFIG=true` quando aparecer
caso real de divergencia DEV/PROD. Adocao trivial (~15 LOC):
```python
if 'strict_mcp_config' in {f.name for f in dataclasses.fields(ClaudeAgentOptions)}:
    options_dict["strict_mcp_config"] = AGENT_STRICT_MCP_CONFIG
```

### Features NAO adotadas (sem caso de uso)

- **F1: `include_hook_events`** (SDK 0.1.74) — emite `HookEventMessage` no stream principal.
  Nossos 8 hooks Python ja logam tudo via `logger.info`. Stream poluido sem consumidor
  claro. Reavaliar se aparecer caso de "hook silenciosamente falhou".
- **F2: `defer` permission decision + `DeferredToolUse`** (SDK 0.1.74) — round-trip async
  para aprovacao demorada. Nosso fluxo `register_question`/`wait_for_answer` (Event +
  TeamsTask.status='awaiting_user_input') ja cobre 95% dos casos com timeouts 55s/120s.
  Reabrir caso se TeamsTask timeouts >5%/mes em prod.
- **F5: `updatedToolOutput` em PostToolUse** (SDK 0.1.74) — antes so MCP, agora qualquer
  tool. Sem caso de governance/compliance que demande reescrita de output. Reavaliar se
  surgir requisito (ex: "agente nunca pode ver coluna X").
- **F10: anthropic 0.99.0 (workspace OIDC) + 0.100.0 (Managed Agents multiagents/outcomes/
  webhooks/vault validation)** — sistema usa API key direto (sem OIDC), e Managed Agents
  duplica stack atual de 35K LOC. Nossos 13 `.claude/agents/*.md` + Task tool nativo +
  validador Haiku cobrem multi-agent + outcomes + observability.

---

## SDK 0.1.73 + anthropic 0.98.1 (atualizado 2026-05-05) — Upgrade massivo + features novas

**Versao**: `claude-agent-sdk==0.1.73` (CLI bundled 2.1.128) + `anthropic==0.98.1`
**Floor adicionado**: `mcp>=1.19.0` (era unbounded; floor garante fix CallToolResult)

### Features adotadas

#### 1. `session_store_flush` (SDK 0.1.73) — feature flag opt-in

**Mecanica**: novo campo em `ClaudeAgentOptions`:
- `"batched"` (default): TranscriptMirrorBatcher entrega frames ao `SessionStore.append()` no end-of-turn.
- `"eager"`: entrega near-real-time, frame-by-frame.

**Arquitetura adotada**: feature flag persistente, default OFF.

- **Config**: `AGENT_SDK_SESSION_STORE_FLUSH` env var, default `"batched"`.
- **Aplicacao** (`client.py:_stream_response_persistent`): `dataclasses.replace(options, session_store_flush=...)`.
- **Forward-compat**: introspection `dataclasses.fields(options)` evita erro se SDK < 0.1.73.

**Quando ativar `eager`**:
- Live-tailing UI no `/admin/session_store` (atualizacao mid-turn).
- Crash durability: se gunicorn worker crasha mid-turn, transcript em andamento persiste.
- Cross-process resume mid-turn.

**Custos**:
- Carga Postgres: dezenas-centenas de INSERTs por turn → satura pool asyncpg LAZY (`max=3` per-worker).
- Latencia: +5-20ms por chunk SSE.
- ATIVAR APENAS apos profiling (frames/turn medio + impacto em pool DB).

**Rollback**: `AGENT_SDK_SESSION_STORE_FLUSH=batched` + redeploy.

**Arquivos modificados**:
- `app/agente/config/feature_flags.py`: nova flag `AGENT_SDK_SESSION_STORE_FLUSH`.
- `app/agente/sdk/client.py:1615-1647`: aplica flush via `dataclasses.replace` com introspection forward-compat.

#### 2. `APIStatusError.type` (anthropic 0.87.0) — classificacao granular de erros

**Mecanica**: `anthropic.APIStatusError` agora expoe `.type` com valores: `invalid_request_error`, `authentication_error`, `permission_error`, `not_found_error`, `rate_limit_error`, `timeout_error`, `overloaded_error`, `api_error`, `billing_error`.

**Beneficio**: distinguir 429 retry-imediato de 529 retry-com-backoff de 403 billing vs 403 permission.

**Arquivos modificados**:
- `app/scanner/service.py:237-256`: `except anthropic.APIStatusError` separado de `except anthropic.APIError`. Mensagens de erro categorizadas para o usuario por `e.type`.
- `app/agente/services/memory_consolidator.py:632-647`: log granular com `e.type`. R1 best-effort mantido (return None).

**NAO refatorados** (best-effort generico R1 por design): `improvement_suggester.py`, `session_summarizer.py`, `suggestion_generator.py`, `parser_append_service.py`, `admin_learning.py` — usam `except Exception` que ja captura tudo. Refatorar so se aparecer caso real onde granularidade e necessaria.

#### 3. `stop_details` estruturado (anthropic 0.88.0 + streaming fix em 0.98.0)

**Mecanica**: quando `stop_reason == "refusal"`, response.stop_details retorna `{category: "cyber"|"bio"|None, explanation: str|None}`. Bug fix em 0.98.0: `message_delta` agora propaga `stop_details` para Message acumulado em streaming (antes so aparecia em non-streaming).

**Beneficio**: distinguir refusals de safety reais vs falsos positivos. Util em audit/observability admin.

**Arquivos modificados**:
- `app/agente/sdk/client.py:_parse_sdk_message` handler `ResultMessage`: captura `stop_details` via `getattr` (tolera SDK pre-0.88.0). Suporta `model_dump()`, dict raw, ou objeto com `.category`/`.explanation`. Logado em INFO se presente.
- `app/agente/sdk/client.py`: propagado em `StreamEvent('done').content['stop_details']`.
- `app/agente/routes/chat.py:elif event.type == 'done'`: surfaced no `done_payload` SSE + `logger.warning` quando refusal real ocorre.

#### 4. Bug fix gratuito (SDK 0.1.70): MCP CallToolResult silenciosamente perdido

**Mecanica**: SDK 0.1.69 e anteriores com `mcp<1.19.0` convertiam `CallToolResult` retornado por handlers SDK MCP em validation-error blob. Modelo recebia erro em vez do output real.

**Aplicabilidade**: 7 MCP servers no projeto (memory_mcp_tool 12 ops + session_search_tool 4 ops + render_logs + schema_mcp + text_to_sql + playwright + teams_card + routes_search). `mcp` instalado: 1.26.0+ (atende floor). Floor `mcp>=1.19.0` adicionado em `requirements.txt` para garantir em deploys futuros.

### Features NAO adotadas

- **`session_store_flush=eager`** ativado por default — risco Postgres saturar pool antes de profiling. Flag esta IMPLEMENTADA, mas default `batched`.
- **Trio compatibility fix (0.1.67)** — sistema usa asyncio puro, nao aplicavel.
- **Sandbox network config (0.1.71)** — sistema nao usa SDK sandbox.
- **Filesystem memory tools (anthropic 0.86.0)** — sistema atual (`agent_memories` + Voyage + KG) e mais sofisticado.
- **Managed Agents + CMA Memory (anthropic 0.92, 0.97, 0.98)** — duplica stack atual de 35K LOC.
- **Beta advisor tool (anthropic 0.93.0)** — sistema ja tem subagentes para isso.
- **Workload Identity Federation (anthropic 0.98.0)** — usa API key direto, nao AWS/GCP/Azure.
- **`task_budget` em subagentes** (anthropic 0.96.0) — campo ja existe em `ClaudeAgentOptions`, candidato a feature flag futura para subagentes Opus longos (`analista-carteira`, `raio-x-pedido`). NAO IMPLEMENTADO neste passo.

### Bumps de CLI bundled (sem mudancas API Python)

| SDK | CLI bundled |
|-----|-------------|
| 0.1.67 | 2.1.120 |
| 0.1.68 | 2.1.119 (rollback CLI) |
| 0.1.69 | 2.1.121 |
| 0.1.70 | 2.1.122 |
| 0.1.71 | 2.1.123 |
| 0.1.72 | 2.1.126 |
| 0.1.73 | 2.1.128 |

### Anthropic SDK 0.85.0 → 0.98.1 — features que vieram gratis via upgrade

| Versao | Feature | Status |
|--------|---------|--------|
| 0.85.0 | GA `thinking-display-setting` | Ja em uso via SDK 0.1.65 |
| 0.86.0 | Filesystem memory tools | NAO adotado (sistema atual e superior) |
| 0.87.0 | `APIStatusError.type` | **ADOTADO** (scanner + memory_consolidator) |
| 0.88.0 | `stop_details` estruturado | **ADOTADO** (client.py + routes/chat.py) |
| 0.92.0 | Managed Agents | NAO adotado |
| 0.93.0 | Beta advisor tool | NAO adotado |
| 0.94.1 | Streaming missing events fix | Gratis via upgrade |
| 0.96.0 | `claude-opus-4-7` + token budgets oficiais | Modelo ja em uso, task_budget pendente |
| 0.97.0 | CMA Memory public beta | NAO adotado |
| 0.98.0 | Streaming `stop_details` propagation fix | **CRITICO** para feature 3 acima |

---

## SDK 0.1.66 (atualizado 2026-04-23) — Thinking display override

**Versao**: `claude-agent-sdk==0.1.66`
**CLI bundled**: 2.1.119

### Feature adotada: `ThinkingConfig.display` (SDK 0.1.65)

**MECANICA REAL**: `display` controla se o modelo gera texto SUMARIZADO do
raciocinio. Thinking real (chain-of-thought interno) acontece identico nos dois
casos; o que muda e o modelo gerar ou nao o resumo legivel:

| Valor | Comportamento | Custo | Qualidade |
|-------|---------------|-------|-----------|
| `summarized` | Modelo gera resumo do raciocinio + resposta | Tokens extras + latencia | Mesma da resposta final |
| `omitted` | Modelo pula o resumo, entrega so resposta | Mais rapido, mais barato | Identica |

**Arquitetura adotada**: toggle per-user persistente.

- **Default global**: `AGENT_THINKING_DISPLAY=omitted` (velocidade + economia).
- **Override per-user**: `Usuario.preferences['agent_thinking_display']` (JSONB).
  - Toggle no header do chat (icone cerebro): OFF=omitted, ON=summarized.
  - Persistido via `POST /agente/api/user-preferences`; lido por `api_chat` e
    propagado em `_stream_chat_response` -> `_async_stream_sdk_client` ->
    `client.stream_response` -> `client._build_options`.
  - Precedencia: user pref > env flag > skip.
- **Teams bot**: sem toggle (Teams nao processa `StreamEvent('thinking')`).
  Default `omitted` protege — zero impacto.
- **Debug panel (admin)**: respeita a preference do proprio admin (opcao b).
  Sem forcar `summarized` implicito.

**Arquivos criados/modificados**:

- `scripts/migrations/2026_04_23_add_usuarios_preferences.{py,sql}`: adiciona
  coluna `usuarios.preferences` JSONB default `'{}'`.
- `app/auth/models.py`: coluna + helpers `get_preference`/`set_preference` (usa
  `flag_modified` para JSONB mutation).
- `app/agente/routes/user_preferences.py`: rotas GET/POST com whitelist
  `_VALID_PREFERENCES` (rejeita chave/valor desconhecido com 400).
- `app/agente/sdk/client.py`: param `thinking_display` em `stream_response`,
  `_stream_response_persistent`, `_build_options`. Lido em precedencia
  user_pref > AGENT_THINKING_DISPLAY env.
- `app/agente/routes/chat.py:api_chat`: le `current_user.get_preference`
  e propaga em toda a cadeia de streaming.
- `app/agente/templates/agente/chat.html`: toggle `#thinking-display-toggle`.
- `app/static/agente/js/chat.js`: GET preference no DOMContentLoaded (localStorage
  mirror para render instantaneo), POST on change (rollback UI se backend falhar).

**Rollback**:
- `AGENT_THINKING_DISPLAY=off` + redeploy: nao passa campo, SDK/CLI decidem default (comportamento pre-0.1.65).
- User toggle: mudar para OFF, persiste omitted (ou limpar pref via SQL direto).

**Teste local** (2026-04-23):
- Migration executada (466 usuarios, preferences='{}' default, 0 NULL).
- `get_preference`/`set_preference` + rollback de transacao validados.
- Rotas GET/POST registradas em `/agente/api/user-preferences`.
- 5 arquivos Python compilam sem erro.

### Features 0.1.65 nao adotadas

- **`list_session_summaries()` protocol method** + `fold_session_summary()` helper: sem consumidor. Rota `/api/sessions/summaries` (`routes/sessions.py:251`) usa `AgentSession.summary` do DB nativo (mais rapido que parse JSONL). Adapter `PostgresSessionStore` mantem nao-implementado (linha 265).
- **`import_session_to_store()` helper**: migration local→store ja executada em Fase B (2026-04-21). Utilidade marginal.
- **`AdvisorToolResultBlock`**: nao usamos advisor MCP tool.

### Fix grátis via upgrade

- **`ServerToolUseBlock` + `ServerToolResultBlock` parser fix** (#836): antes `AssistantMessage(content=[])` quando mensagem tinha só server-side tool call. `WebSearch`/`WebFetch` na whitelist `allowed_tools` (`settings.py:52-53`) beneficiam — fix automatico via SDK upgrade.
- **Bounded retry em mirror append + UUID idempotency** (#857): esperamos menos `MirrorErrorMessage` no Sentry. Handler em `client.py:616` permanece como safety net.
- **`--debug-to-stderr` detection removida do transport**: stderr piping agora depende só de callback registrado. Nossa pipeline (`client.py:1279`) sempre registra callback quando `stderr_queue is not None` → zero impacto. Ainda passamos `extra_args: {"debug-to-stderr": None}` (CLI 2.1.118/2.1.119 aceitam; removal CLI é futuro).

### 0.1.66

Apenas bump CLI 2.1.119 (sem mudancas de API Python).

---

## SDK 0.1.64 (atualizado 2026-04-21) — SessionStore Fase B (cutover)

**Versao**: `claude-agent-sdk==0.1.64`, `asyncpg==0.30.0` (novo driver async)
**CLI bundled**: 2.1.116

### Feature: PostgresSessionStore (source-of-truth)

Tabela `claude_session_store` substituiu `session_persistence.py` — SDK 0.1.64 nativo via `TranscriptMirrorBatcher` (escrita) + `materialize_resume_session` (resume).

- **Adapter**: `app/agente/sdk/session_store_adapter.py` — `PostgresSessionStore` (5 dos 6 metodos do protocol)
- **Tabela**: `claude_session_store` (migration `2026_04_21_claude_session_store.{sql,py}`)
- **Conformance**: `tests/agente/sdk/test_session_store_conformance.py` — 13 contratos do harness oficial SDK 0.1.64
- **Flag**: `AGENT_SDK_SESSION_STORE_ENABLED` (default **ON** apos Fase B)
- **Timeout**: `AGENT_SDK_SESSION_STORE_LOAD_TIMEOUT_MS` (default 30000ms)

### Historico de fases

| Fase | Data | Estado |
|------|------|--------|
| A (dual-run) | 2026-04-21 15:00-16:30 | Flag OFF default, session_persistence.py em paralelo, criterio C4 "apenas sessions novas" |
| **B (cutover)** | 2026-04-21 17:00 | Flag ON default, 6 callsites legados removidos, session_persistence.py reduzido a helpers de path, migration batch populou store |

### Rollback

- `AGENT_SDK_SESSION_STORE_ENABLED=false` + redeploy (0 downtime)
- `session_persistence.py` NAO e tocado em Fase A — continua funcionando em paralelo (belt + suspenders)
- Dados orfaos em `claude_session_store` nao afetam performance (indexed)

### Pool asyncpg

- **LAZY per-worker** via `asyncio.Lock` — evita sockets compartilhados em gunicorn fork (C2 adversarial)
- `min_size=1, max_size=3` por worker — 4 workers × 3 = 12 conn asyncpg + 4 × 15 psycopg2 = ~72/~197 Render Basic 4GB
- DSN parsed: `_prepare_dsn()` remove `client_encoding` e `options=-c ...` (psycopg2-specific, asyncpg ignora)
- Shutdown: `close_session_store_pool()` disponivel (best-effort, nao bloqueia)

### Integracao (`client.py`)

1. `_build_options` (sync) — inalterada; retorna `ClaudeAgentOptions` base
2. `_stream_response_persistent` (async, linha ~1422) — apos `options = self._build_options(...)`, se flag ON E session NOVA: `options = replace(options, session_store=store, load_timeout_ms=...)` via `dataclasses.replace`
3. `_parse_sdk_message` (linha ~547) — handler `MirrorErrorMessage` (subclass SystemMessage): log ERROR + Sentry, NAO propagado como SSE

### Encoding `project_key`

- `project_key_for_directory('/home/rafaelnascimento/projetos/frete_sistema')` = `-home-rafaelnascimento-projetos-frete-sistema`
- **Identico ao regex atual** de `session_persistence.py` (verificado empirico via SDK)
- Sem migracao de dados — sessions legadas e novas usam mesma chave

### MirrorErrorMessage

- Subclass de `SystemMessage` em SDK 0.1.64+
- Emitida quando `store.append()` falha — contrato at-most-once (batch perdido, nao retentado)
- Disco local continua durable — session nao quebra
- Import condicional (try/except) em `client.py:47-57` para compat com SDK < 0.1.64

### Fase B (EXECUTADA 2026-04-21)

- ✅ `session_persistence.py` reduzido a helpers de path (`_get_session_path` mantido para cleanup stale JSONL em client.py/client_pool.py)
- ✅ 6 callsites legados removidos: `chat.py:321,1311` (pre/pos-stream) + `teams/services.py:579,641,950,1154` (streaming + non-streaming)
- ✅ Flag `AGENT_SDK_SESSION_STORE_ENABLED` default **ON**; criterio C4 "apenas sessions novas" removido (flag universal)
- ✅ Migration batch `scripts/migrations/2026_04_21_migrar_session_persistence_to_store.py` populou store (rodar manualmente no Render Shell com `--project-key=-opt-render-project-src`)
- ✅ 81/81 testes existentes passaram pos-cutover
- Fallback defense in depth: se store falhar, `UserPromptSubmit` hook (`chat.py:341-360`) reinjeta contexto XML das ultimas 10 msgs do `AgentSession.data['messages']` JSONB

### Fase C (cleanup) — EXECUTADA 2026-04-21

- ✅ `ALTER TABLE agent_sessions DROP COLUMN sdk_session_transcript` via `scripts/migrations/2026_04_21_drop_sdk_session_transcript.{py,sql}` (libera ~66MB)
- ✅ `AgentSession.save_transcript()` / `get_transcript()` removidos (`models.py` — zero callers verificados antes do drop)
- ✅ `session_store_adapter.session_has_legacy_transcript()` e `session_has_store_entries()` removidas (helpers do criterio C4 dual-run, orfas pos-Fase B)
- ✅ `session_turn_indexer.py` removido `defer(AgentSession.sdk_session_transcript)` — nao mais necessario
- ⏳ `session_persistence.py` mantido como helpers de path (2 funcoes) — remocao completa exige realocar `_get_session_path` usado em cleanup stale JSONL

### Referencias

- Plano adversarial-revised: `/tmp/subagent-findings/20260421-sessionstore-60ddbe70/phase3/plan-v2-final.md`
- Rollback runbook: `app/agente/ROLLBACK_SESSION_STORE.md`
- Reference adapter oficial: `anthropics/claude-agent-sdk-python/examples/session_stores/postgres_session_store.py`
- Conformance harness: `claude_agent_sdk.testing.run_session_store_conformance`

---

## SDK 0.1.60 (atualizado 2026-04-16)

**Versao**: `claude-agent-sdk==0.1.60`
**Modelo default**: `claude-opus-4-7` (migrado de 4.6 em 2026-04-16)

### Migracao Opus 4.6 → 4.7 (2026-04-16)
- `config/settings.py:31`: default `model="claude-opus-4-7"` (mesmo preco $5/$25 per MTok, adaptive thinking, 1M context, 128K max output).
- `config/settings.py:MODEL_PRICING`: adicionado `'claude-opus-4-7': (5.00, 25.00)`; 4.6 e 4.5 mantidos como legado.
- `config/feature_flags.py:322`: `TEAMS_DEFAULT_MODEL` default `claude-opus-4-7`.
- **Rollback instantaneo** via env vars: `AGENT_MODEL=claude-opus-4-6` + `TEAMS_DEFAULT_MODEL=claude-opus-4-6`.
- **Breaking changes aplicaveis**: thinking `{"type": "enabled"}` removido (nao usavamos — ja usavamos `effort` nativo); `temperature/top_p/top_k` removidos (nao usados em Opus — Sonnet/Haiku em services nao sao afetados); prefill de assistant removido (nao usado); thinking `display: "omitted"` default (risco UX — CLI 2.1.111 pode exibir normalmente via `effort`; monitorar eventos `thinking` na pipeline SSE).
- **Comportamento**: tokenizer novo (~0-35% mais tokens por texto), respostas calibradas pela complexidade, mais literal, tom mais direto, spawna menos subagentes por default, usa menos tools por default (steerable via `effort=high` ou prompt).
- **Features novas disponiveis nao adotadas**: `xhigh` effort level (SDK 0.1.60 nao expõe no Literal type — via `extra_args` se necessario), `task_budget` beta (`task-budgets-2026-03-13` — campo ja existe em `ClaudeAgentOptions`), alta resolucao de imagem (2576px automatico, irrelevante para screenshots Playwright ja comprimidos).

### Features adotadas (0.1.56–0.1.60):
- **`list_subagents()`/`get_subagent_messages()`** (0.1.60): Helpers para inspecionar cadeias de mensagens de subagentes spawnados. Exportados no top-level. **NAO adotado ainda** — candidato a endpoint admin de debug.
- **Distributed tracing W3C** (0.1.60): `TRACEPARENT`/`TRACESTATE` propagados para subprocess CLI quando span OpenTelemetry ativo. **NAO adotado** (projeto nao usa OTEL).
- **Cascading `delete_session()`** (0.1.60): Agora remove diretorios de transcript de subagentes irmaos. **NAO aplicavel** (projeto nao usa `delete_session()` do SDK, usa fluxo DB proprio).
- **`setting_sources=[]` fix** (0.1.60): Lista vazia passada nao e mais silenciosamente descartada — desabilita todos os settings do filesystem corretamente. Adotado automaticamente via upgrade.
- **CLI empacotado 2.1.111** (0.1.60): Base para comportamento Opus 4.7 + correcoes diversas.
- **`thinking={"type": "adaptive"}` mapping fix** (0.1.57): Comportamento alinhado com TS SDK. **Critico para Opus 4.7** (que depende de adaptive thinking). Adotado automaticamente.
- **`exclude_dynamic_sections` em `SystemPromptPreset`** (0.1.57): Move secoes dinamicas per-user para fora do system prompt → cross-user cache hits. **NAO adotado** — arquitetura atual usa string direta com hook `session_context` (`USE_PROMPT_CACHE_OPTIMIZATION`), ja otimizada. Mudaria o fluxo.
- **`"auto"` em `PermissionMode`** (0.1.57): **NAO adotado** — projeto usa `can_use_tool` callback customizado em `permissions.py`.
- **`maxResultSizeChars` MCP fix** (0.1.55): Resultados MCP grandes nao sao mais truncados silenciosamente. CLI 2.1.91.

### Features adotadas (0.1.51–0.1.53):
- **`typing.Annotated` em MCP tools** (0.1.52): Descriptions por parametro no JSON Schema. `_mcp_enhanced.py:_python_type_to_json_schema()` processa `Annotated[str, "desc"]` → `{"type": "string", "description": "desc"}`. Aplicado em 34 tools (7 MCP servers). Modelo recebe instrucoes por parametro em vez de adivinhar pelo nome.
- **`ToolPermissionContext.tool_use_id/agent_id`** (0.1.52): `can_use_tool()` agora recebe `agent_id` (UUID instancia do subagente) e `tool_use_id` (ID unico da tool call). `permissions.py` registra mapa `agent_id→agent_type` via `SubagentStart` hook. Infraestrutura de politicas por subagente pronta (`_SUBAGENT_DENY_POLICIES`, vazio por default — `tools` whitelist ja restringe). Audit trail com agent_type em cada permissao.
- **`AgentDefinition.disallowedTools/maxTurns/initialPrompt`** (0.1.51): `agent_loader.py` parseia `disallowed_tools`, `max_turns`, `initial_prompt` do frontmatter. Disponivel para uso nos `.claude/agents/*.md` quando necessario — nao aplicado por padrao.
- **`ClaudeAgentOptions.session_id`** (0.1.52): Pre-declara UUID do JSONL. `_build_options()` passa `our_session_id` como `session_id` → naming deterministico. Resume usa `our_session_id` como fallback se `sdk_session_id` ausente. **NOTA**: Issue #560 (aberta) — `ClaudeSDKClient` nao usa `session_id` para isolamento; nosso pool resolve via instancias separadas.
- **`ResultMessage.errors`** (0.1.51): Campo `errors` logado no ResultMessage handler e propagado no StreamEvent `done`.
- **`fork_session()`/`delete_session()`** (0.1.51, NAO usadas): APIs de sessao. Disponiveis para uso futuro.
- **`task_budget`** (0.1.51, NAO usado): Limite de tokens por task/subagent.
- **`SystemPromptFile`** (0.1.51, NAO usado): System prompt via arquivo. Nosso prompt e ~3KB string — sem necessidade.
- **`get_context_usage()`** (0.1.52, NAO implementado): Monitoramento de context window. Requer wiring 3-layer (client→routes→chat.js).
- **`stderr` callback** (0.1.53, implementado 2026-04-01): Captura debug output do CLI subprocess em real-time. Pipeline 3-layer: `_build_options(stderr_queue)` → `StreamEvent('stderr')` → SSE → debug panel (admin-only). Flag: `USE_STDERR_CALLBACK`. Requer `debug_mode=true` no request E flag ativa. `extra_args: {"debug-to-stderr": None}` habilita output no CLI.
- **`output_format`** (0.1.53, frontend implementado 2026-04-01): Structured output com JSON Schema. Backend ja estava wired (`_build_options` + done event). Frontend agora renderiza `structured_output` como tabela (arrays), badges (fields simples), ou JSON collapsible (fallback). Request param: `output_format: {type: "json_schema", schema: {...}}`.

### Features adotadas (anteriores, mantidas):
- **`ResultMessage.stop_reason`**: Populado automaticamente no StreamEvent `done` e logado.
- **Task messages** (`TaskStartedMessage`, `TaskProgressMessage`, `TaskNotificationMessage`): SSE events para observabilidade de subagentes.
- **`agent_id`/`agent_type` em hooks**: `PostToolUseHookInput` logados no `[AUDIT] PostToolUse`.
- **`effort` field nativo**: `ClaudeAgentOptions.effort` — substituiu `max_thinking_tokens`.
- **`RateLimitEvent`** (0.1.50): Pipeline 3-layer: client.py → routes/chat.py → chat.js (toast).
- **`HookMatcher.timeout`** (0.1.50): `UserPromptSubmit` usa 120s.
- **`AgentDefinition.skills`** (0.1.49): Skills nativas via `_SDK_HAS_NATIVE_FIELDS`.

### Features adotadas (2026-04-16 — SDK 0.1.60 fases 1-2):
- **`sdk/subagent_reader.py`**: Wrapper de `list_subagents` + `get_subagent_messages`. Fundacao usada por #1, #3, #5, #6. Retorna `SubagentSummary` com tools cronologicas, cost, tokens, findings_text. Aplica mascaramento PII por default (regex brasileiro em `utils/pii_masker.py`).
- **Endpoint admin debug forense** (`routes/admin_subagents.py`, #1): 3 rotas admin-only — `/api/admin/sessions/<id>/subagents[/<aid>[/messages]]`. Flag `USE_SUBAGENT_DEBUG_ENDPOINT` (default true).
- **Cost tracking granular** (`hooks.py` + `models.py` + `services/insights_service.py`, #3): SubagentStop persiste entry em `AgentSession.data['subagent_costs']` (JSONB v1, indice GIN em `scripts/migrations/agent_session_subagent_costs_idx.{py,sql}`). Classmethod `AgentSession.top_subagents_by_cost(days, limit)`. Flag `USE_SUBAGENT_COST_GRANULAR`.
- **UI linha inline expansivel** (`routes/subagents.py` + `static/agente/js/chat.js` + `static/agente/css/_subagent-inline.css`, #6): Linha dentro do fluxo da conversa com estados running/done/expanded. Lazy-fetch em `/api/sessions/<id>/subagents/<aid>/summary`. PII sanitizada via `_sanitize_subagent_summary_for_user()` em `routes/chat.py` para non-admin. Admin ve cost + raw. Flag `USE_SUBAGENT_UI`.
- **Memory mining cross-subagent** (`services/pattern_analyzer.py`, #5): `extrair_conhecimento_sessao(include_subagents=True, session_id=...)` injeta findings dos especialistas antes da conversa principal no prompt Sonnet. Cap 2K chars/subagent. Flag `USE_SUBAGENT_MEMORY_MINING`.

### Features adotadas (2026-04-17 — SDK 0.1.60 fase 4):
- **Validacao anti-alucinacao async** (`workers/subagent_validator.py` + `sdk/hooks.py` enqueue + `routes/chat.py` pubsub subscriber, #4): `SubagentStop` hook enfileira job RQ em queue `agent_validation` (processada por `worker_render.py` e `worker_atacadao.py`). Worker carrega summary via `subagent_reader`, chama Haiku 4.5 (`claude-haiku-4-5-20251001`) com prompt estruturado comparando tool_results vs `findings_text`, parseia JSON `{score, reason, flagged_claims}` e persiste em `AgentSession.data['subagent_validations']` (JSONB v1). Se `score < SUBAGENT_VALIDATION_THRESHOLD` (default 70, env var), publica evento `subagent_validation` no canal Redis `agent_sse:<session_id>`. SSE generator em `routes/chat.py` subscreve esse canal via non-blocking `pubsub.get_message(timeout=0.0)` e emite evento ao frontend. `chat.js` renderiza icone ⚠ amarelo na linha do subagent (CSS `.validation-warning`). Flag `USE_SUBAGENT_VALIDATION` controla enqueue + subscribe. Custo: ~$0.0005/call.

**PII sanitization** (`utils/pii_masker.py`): Regex conservadora CPF/CNPJ/email formatados e sem formatacao. Preserva DV/filial/dominio. Admin pula sanitizacao via `_sanitize_subagent_summary_for_user()` em `routes/chat.py`.

**GOTCHA**: Global exception handler em `app/__init__.py:511` re-raise HTTPException (exceto 404). `abort(403)` NAO funciona em rotas deste app — usar `return jsonify({'success': False, 'error': '...'}), 403` inline (pattern de `admin_learning.py`).

**Pendente** (fase 3): #2 aposentar `/tmp/subagent-findings/` (soft, mantem fallback).

### Bugs corrigidos na Fase 2 (2026-04-17)

Diagnosticados via logs Render: **19/19 sessoes em 48h com `subagent_costs` VAZIO** antes do fix. 3 bugs de raiz + 1 descoberto durante investigacao:

- **Bug 1 — `cost_usd=None` sempre**: JSONL de SUBAGENT nao contem `type:'result'` (SDK 0.1.60 exclui `result` de `_TRANSCRIPT_ENTRY_TYPES` em `sessions.py:791-794`). Solucao: novo helper `_compute_subagent_metadata_from_jsonl()` em `subagent_reader.py` soma `usage` de cada `AssistantMessage` + diff de timestamps. `_read_result_metadata()` ainda tenta `type:'result'` primeiro (compat forward).

- **Bug 2 — `subscribers=0` em 60% dos publishes**: race condition hook async (`spawn_task`) vs SSE close em 3s pos-`done`. Solucao T7: `_emit_subagent_summary` (`client.py:73`) publica em pubsub **E** `RPUSH` em `agent_sse_buffer:<session_id>` (TTL 5min, cap 20). SSE generator dreva buffer com `LRANGE 0 -1` antes de subscribir pubsub (`routes/chat.py:963-1010`).

- **Bug 3 — `list_subagents` retornando vazio**: REFUTADO em producao. `CLAUDE_CONFIG_DIR=/tmp/.claude` ja setado como env var no Render; SDK default funciona.

- **Bug 4 — parser de blocks retorna 0 tools**: `SessionMessage.message` do SDK 0.1.60 e dict Anthropic `{role, content, ...}` — parser antigo acessava `msg.content` direto (sempre None). Fix em `subagent_reader.py:_extract_content_list()` usa `msg.message.get('content')`. Log de 2026-04-17 12:20:13 mostrava `status=done tools_used=0 findings_len=0` apesar de JSONL de 131KB com 24 linhas — era este bug.

**Pricing correto com cache** (`sdk/pricing.py` novo): tabela por modelo distinguindo `input`, `output`, `cache_creation` (1.25x input), `cache_read` (0.10x input). Ex Opus 4.7: $5/$25 per MTok.

**Persistencia v2** (`hooks.py:528-610`): entries em `AgentSession.data->'subagent_costs'->'entries'` agora tem `schema_version='v2'`, escritas via `UPDATE ... jsonb_set(..., || :entry_json::jsonb)` SQL raw — atomico, elimina lost-update de subagents concorrentes que afetava v1 silenciosamente.

**Smoketest endpoint** (`routes/admin_subagents.py:api_admin_subagent_smoketest`): `GET /agente/api/admin/debug/subagent-smoketest` valida pipeline end-to-end (list_subagents + get_subagent_summary + SQL entries). Healthy requer `status=done` + `num_turns>0 OU cost_usd>0` + `tools_used>0 OU findings_len>0`.

### Bug fixes criticos (0.1.51–0.1.53):
- **`is_error` MCP propagado** (0.1.51): Modelo sabe quando MCP tool falhou (antes interpretava erro como sucesso)
- **`SIGKILL` fallback nativo** (0.1.51): SDK agora mata subprocess zombie. `_force_kill_subprocess()` em `client_pool.py` pode ser simplificado
- **`control_cancel_request`** (0.1.52): Hooks in-flight cancelados corretamente (antes ficavam zombie)
- **Cross-task `RuntimeError` fix** (0.1.51): `disconnect()` nao falha mais ao ser chamado de task diferente
- **`--setting-sources` fix** (0.1.53): Lista vazia nao corrompe flags do CLI
- **Deadlock `query()`+hooks fix** (0.1.53): Afeta apenas path v2 (codigo morto)

### NAO usadas (mantidas para referencia):
- **Session Management APIs** (0.1.50): `list_sessions()`, `get_session_info()`, etc.
- **MCP Runtime Control** (0.1.50): `get_mcp_status()`, `toggle_mcp_server()`, etc.
- **`AgentDefinition.mcpServers`** (0.1.49): Apenas para servers EXTERNOS.
- **`AgentDefinition.memory`** (0.1.49): Conflita com sistema custom PostgreSQL.
