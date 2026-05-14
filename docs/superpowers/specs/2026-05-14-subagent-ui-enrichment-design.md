# Enriquecimento da exibição de Subagents no Chat Web — Design

**Data**: 2026-05-14
**Versão**: v1.0
**Autor**: Rafael Nascimento (com Claude Opus 4.7, via skill `superpowers:brainstorming`)
**Status**: design aprovado pelo dono do produto, pronto para writing-plans
**Origem**: feature do Claude Code (Agent View v2.1.139+) que permite ver ações do subagente, selecionar a sessão dele, ver prompt enviado parent→subagent e ver o trabalho dele

---

## 1. Contexto e motivação

### 1.1 Estado atual

O sistema web (`app/agente/`) já tem o **esqueleto** correto de exibição de subagents no chat:

- **5 eventos SSE** mapeados: `task_started`, `task_progress`, `task_notification`, `subagent_summary`, `subagent_validation` (`app/agente/sdk/client.py:826-882`)
- **Linha inline expansível** (`app/static/agente/js/chat.js:1093-1285`) com badge + meta + custo + tools resumidas
- **Endpoint lazy-fetch** `GET /api/sessions/<sid>/subagents/<aid>/summary` (`app/agente/routes/subagents.py`)
- **Endpoint admin forense** completo em `app/agente/routes/admin_subagents.py`
- **Reader SDK** robusto (`app/agente/sdk/subagent_reader.py`) com 3 fallbacks de path (default, `/tmp/.claude`, S3 archive) e proteção anti-path-traversal
- **PII masking** automático para non-admin via `mask_pii()` (`app/agente/utils/pii_masker.py`)
- **Worker validação Haiku** (anti-alucinação) já em produção

### 1.2 Lacunas identificadas vs Claude Code Agent View

Comparação com `https://code.claude.com/docs/en/agent-view`:

| Capacidade | Hoje | Claude Code | Gap |
|---|---|---|---|
| Estados visuais | 3 (`running/done/error`) | 6 + shape de processo | **Médio** |
| Descrição do que está fazendo | `last_tool_name` cru | One-liner Haiku-class | **Alto** (UX) |
| Ver transcript completo | Só `tools_used` + 400 chars findings | Attach → conversa inteira | **Alto** |
| Prompt enviado parent→subagent | ❌ não exibido | Visível no transcript | **Alto** (debug) |
| Hierarquia/aninhamento | Flat list | Tree via `parent_tool_use_id` | **Médio** |
| Tokens/custo ao vivo | Só no `subagent_summary` final | `TaskProgressMessage.usage` em real-time | **Médio** |
| Organização | Cronológica fixa | Pin/rename/tag/filter/group | **Baixo-Médio** |
| Output file do subagent | ❌ | Link de download | **Médio** |

### 1.3 APIs SDK disponíveis (verificadas no Context7 + docs.claude.com)

SDK 0.1.80 expõe APIs não totalmente exploradas pelo sistema:

- `get_subagent_messages(session_id, agent_id)` — ✅ usado (`subagent_reader.py:472`); fornece transcript bruto
- `list_subagents(session_id)` — ✅ usado
- `parent_tool_use_id` em `StreamEvent`/`AssistantMessage`/`UserMessage` — ❌ não correlacionado no frontend
- `TaskProgressMessage.usage: TaskUsage` (`total_tokens`, `tool_uses`, `duration_ms`) — ⚠️ parcial (só `last_tool_name`)
- `TaskNotificationMessage.output_file` — ❌ ignorado
- `tag_session` / `rename_session` — não usado para subagents (provável que SDK suporte só session principal; testar)

### 1.4 Decisões aprovadas via Q&A (brainstorming)

1. **Viewer shape** = Modal full-screen (reaproveita infra de `#artifact-modal`)
2. **Live progress** = leve (tokens + duração + last_tool no meta da linha inline)
3. **PII policy** = padrão atual + toggle admin "Mostrar PII" com audit log + Redis TTL 5min
4. **Parent linking** = correlação visual sutil via `parent_tool_use_id`
5. **Rename/tag persistence** = JSONB custom em `agent_sessions.data['subagent_metadata']`
6. **Delivery shape** = single spec coeso, entrega em 2 fases
7. **Arquitetura interna** = Stateful no `chat.js` existente + markup em `chat.html` + novo `_subagent-modal.css`

---

## 2. Princípios de design

1. **R8 honrado**: novo evento SSE = atualizar TODAS as 3 camadas (`client.py` → `routes/chat.py` → `chat.js`). Pattern já documentado em `app/agente/CLAUDE.md:378-398`.
2. **PII por padrão**: endpoints novos usam `_sanitize_subagent_summary_for_user` ou equivalente. Admin com toggle ativo é auditado.
3. **Reutilização**: `subagent_reader.py` continua sendo single source para leitura. Novos endpoints chamam funções dele, não duplicam parsing.
4. **Backward-compat**: linha inline existente continua funcionando se modal falhar (fallback gracioso). Feature flags por capacidade.
5. **Sem novos workers RQ na Fase 1**: P2.1 (Haiku one-liner summary) ficou fora de escopo.
6. **Zero migration DDL**: tudo persiste em `agent_sessions.data` (JSONB). Rollback = mudar env var.

---

## 3. Mapa de Fase 1 vs Fase 2

| Capacidade | Fase | Risco |
|---|---|---|
| P0.1 Modal transcript (prompt + timeline + findings) | **Fase 1** | Médio (novo endpoint + modal) |
| P0.2 Estados visuais ricos (`failed`/`stopped` + cor/ícone) | **Fase 1** | Baixo (só CSS + classes JS) |
| P0.3 Progresso ao vivo (tokens · duração · last_tool) | **Fase 1** | Baixo (estende metadata SSE) |
| P1.1 Correlação `parent_tool_use_id` | **Fase 1** | Baixo (propaga + CSS conector) |
| P1.2 Rename/tag subagent (JSONB custom) | **Fase 2** | Médio (PATCH endpoint + XSS) |
| P1.3 Download `output_file` | **Fase 2** | Baixo-Médio (mask_pii streaming) |

### 3.1 Fora de escopo (P2, adiado)

| Item | Por quê fora |
|---|---|
| P2.1 Haiku one-liner summary | Custo recorrente $/dia incerto; medir uso antes |
| P2.2 Fork de subagent | Uso real estimado baixo; espera demanda concreta |
| P2.3 Drawer de subagents da sessão | Modal já cobre 90% do valor |
| Integração com Teams bot (Adaptive Card) | Teams não suporta iframe; abordagem diferente |
| Telemetria visualização (painel admin) | Adicionar depois quando dados existirem |
| Notificação push quando subagent termina | Fora do escopo de visualização |

---

## 4. Arquitetura geral

### 4.1 Camadas afetadas

```
                        ┌─────────────────────────────┐
SDK (claude-agent-sdk)  │ TaskStarted/Progress/Notif. │ ── carregam TaskUsage
                        └──────────┬──────────────────┘
                                   │
                        ┌──────────▼──────────────────┐
Layer 1: client.py      │ _parse_sdk_message          │ ← adiciona usage no metadata
                        │   + propaga parent_tool_use │
                        └──────────┬──────────────────┘
                                   │ StreamEvent
                        ┌──────────▼──────────────────┐
Layer 2: routes/chat.py │ _process_stream_event       │ ── repassa para SSE
                        └──────────┬──────────────────┘
                                   │ SSE event
                        ┌──────────▼──────────────────┐
Layer 3: chat.js        │ renderSubagentLineProgress  │ ← atualiza meta rica
                        │ openSubagentModal           │ ← NOVO modal lazy-fetch
                        └──────────┬──────────────────┘
                                   │
                        ┌──────────▼──────────────────┐
Endpoints (fetch async) │ GET .../subagents/<aid>/transcript  ← NOVO
                        │ PATCH .../subagents/<aid>           ← NOVO (rename/tag, Fase 2)
                        │ GET .../subagents/<aid>/output_file ← NOVO (download, Fase 2)
                        │ POST .../subagents/<aid>/pii-toggle ← NOVO (audit)
                        └──────────┬──────────────────┘
                                   │
                        ┌──────────▼──────────────────┐
Persistência            │ agent_sessions.data         │
                        │   .subagent_metadata[aid]   │ ← NOVO (name, tags) — Fase 2
                        │   .subagent_pii_audit[]     │ ← NOVO (toggles)    — Fase 1
                        └─────────────────────────────┘
```

### 4.2 Feature flags (por capacidade)

Adicionar em `app/agente/config/feature_flags.py`:

| Flag | Default dev | Default prod (big-bang) | Cobre |
|---|---|---|---|
| `USE_SUBAGENT_MODAL` | `true` | `true` | P0.1 modal transcript |
| `USE_SUBAGENT_RICH_STATES` | `true` | `true` | P0.2 estados visuais + P1.1 parent link |
| `USE_SUBAGENT_LIVE_PROGRESS` | `true` | `true` | P0.3 tokens/duration no meta |
| `USE_SUBAGENT_RENAME_TAG` | `true` (Fase 2) | `true` (no merge Fase 2) | P1.2 rename/tag |
| `USE_SUBAGENT_OUTPUT_DOWNLOAD` | `true` (Fase 2) | `true` (no merge Fase 2) | P1.3 download |

**Estratégia big-bang**: todas as flags da Fase 1 sobem `true` simultaneamente no merge da PR-A; todas as flags da Fase 2 sobem `true` no merge da PR-B. Flags são mantidas **apenas como circuit breakers** para rollback rápido (env var no Render).

Pattern já estabelecido: `USE_SUBAGENT_UI`, `USE_SUBAGENT_DEBUG_ENDPOINT`.

---

## 5. Componentes detalhados

### 5.1 Backend

#### `app/agente/sdk/client.py` (modificações em `_parse_sdk_message`)

Linhas atuais 826-882 (já existentes `task_started`/`progress`/`notification`).

**Mudança 1 — `task_progress` enriquecido (P0.3)**:

```python
# linha 853-861
events.append(StreamEvent(
    type='task_progress',
    content=task_desc,
    metadata={
        'task_id': task_id,
        'last_tool_name': last_tool,
        'usage': getattr(message, 'usage', None),  # NOVO: TaskUsage dict
        'parent_tool_use_id': getattr(message, 'parent_tool_use_id', None),  # NOVO
    }
))
```

**Mudança 2 — `task_started` com `parent_tool_use_id` (P1.1)**:

```python
# linha 835-842
events.append(StreamEvent(
    type='task_started',
    content=task_desc,
    metadata={
        'task_id': task_id,
        'task_type': task_type,
        'parent_tool_use_id': getattr(message, 'tool_use_id', None),  # NOVO
    }
))
```

**Mudança 3 — `task_notification` com status estendido (P0.2)**: já passa `status` no metadata (linha 877-880). Frontend é quem mapeia `'completed'/'failed'/'stopped'` para classes CSS distintas. Sem alteração backend aqui.

#### `app/agente/sdk/subagent_reader.py` — nova função `get_subagent_transcript`

Diferencial de `get_subagent_summary` (já existente):

- Summary retorna `tools_used` resumido com correlação simples
- Transcript retorna **timeline cronológica completa** com prompt inicial do parent + tool calls com args completos + tool results + assistant text blocks em ordem

**Contrato**:

```python
@dataclass
class SubagentTranscriptEntry:
    """Uma entrada da timeline cronologica do subagent."""
    sequence: int                  # ordem no JSONL (1, 2, 3, ...)
    kind: Literal['user_prompt', 'assistant_text', 'tool_use',
                  'tool_result', 'thinking']
    timestamp: Optional[datetime]  # do JSONL
    content: Any                   # depende do kind:
                                   #   user_prompt: str
                                   #   assistant_text: str
                                   #   thinking: str
                                   #   tool_use: {name, input}
                                   #   tool_result: {tool_use_id, content, is_error}
    tool_use_id: Optional[str]     # correlaciona tool_use ↔ tool_result

def get_subagent_transcript(
    session_id: str,
    agent_id: str,
    directory: Optional[str] = None,
    include_pii: bool = False,
    max_content_chars: int = 4000,
) -> list[SubagentTranscriptEntry]:
    """Le transcript COMPLETO do subagent em ordem cronologica."""
```

**Reutiliza** `_candidate_directories`, `_resolve_transcript_path`, `mask_pii` já presentes.

**Validações**: `_is_safe_id` em ambos `session_id` e `agent_id` (anti-path-traversal, já presente).

#### `app/agente/routes/subagents.py` — 4 endpoints novos

**Endpoint 1 — `GET /api/sessions/<sid>/subagents/<aid>/transcript`** (Fase 1, P0.1):

- Autorização: dono OU admin (mesmo padrão de `api_user_subagent_summary`)
- Query param: `?include_pii=true` (só permitido se admin **e** Redis token válido)
- Retorna: `{success, session_id, agent_id, transcript: [entries], metadata: {...summary atual}}`
- Validação `_is_safe_id` em path params

**Endpoint 2 — `POST /api/sessions/<sid>/subagents/<aid>/pii-toggle`** (Fase 1):

- Apenas admin. Non-admin → 403.
- Body: `{enabled: bool}`
- Registra audit em `agent_sessions.data['subagent_pii_audit']` (FIFO máx 100)
- Server-side: SETEX Redis `agent:pii_unmask:{user_id}:{session_id}:{agent_id}` 300 "1"
- Rate limit: 10 toggles/min/user (Redis counter)
- Retorna `{success, expires_in: 300}`

**Endpoint 3 — `PATCH /api/sessions/<sid>/subagents/<aid>`** (Fase 2, P1.2):

- Body: `{name?: str, tags?: list[str]}`
- Persiste em `agent_sessions.data['subagent_metadata'][agent_id] = {name, tags, updated_at, updated_by}`
- Validações: name max 80 chars; tags max 10, cada max 30 chars
- Sanitização HTML via `bleach.clean()` server-side
- Reusa `flag_modified(session, 'data')` (R7 do CLAUDE.md módulo)

**Endpoint 4 — `GET /api/sessions/<sid>/subagents/<aid>/output_file`** (Fase 2, P1.3):

- Autorização: dono OU admin
- Resolve path via `_resolve_transcript_path` (não inventa)
- Streama JSONL com `Content-Type: application/jsonl`, `Content-Disposition: attachment`
- Admin: arquivo raw. Dono non-admin: aplica `mask_pii` linha a linha
- Fallback S3: se path local não existe, tenta `restore_session_from_s3()` antes de 404
- Sanity check tamanho: aborta se > 50MB

#### `app/agente/models.py` — sem nova coluna

Reusa `AgentSession.data` (JSONB existente). Convenção dos sub-paths:

```python
data = {
  ...,
  'subagent_costs': {...},              # JÁ EXISTE
  'subagent_validations': {...},        # JÁ EXISTE
  'subagent_metadata': {                # NOVO (Fase 2)
    '<agent_id>': {
      'name': str | None,
      'tags': list[str],
      'updated_at': iso,
      'updated_by': user_id
    }
  },
  'subagent_pii_audit': [               # NOVO (Fase 1)
    {'agent_id', 'user_id', 'enabled': bool, 'timestamp': iso, 'session_id'}
  ]
}
```

**Sem migration DDL** — JSONB aceita o novo schema dinamicamente. Defaults via `dict.setdefault(...)` no momento do PATCH/POST.

### 5.2 Frontend

#### `app/static/agente/js/chat.js` — extensões

**Em `renderSubagentLineStart` (linha 1104)**: capturar `parent_tool_use_id` no dataset:

```js
line.dataset.parentToolUseId = data.parent_tool_use_id || '';
// se houver, anexar pequeno marcador "↳" linkado à mensagem do parent
```

**Em `renderSubagentLineProgress` (linha 1140)**: meta enriquecido:

```js
// data.usage = {total_tokens, tool_uses, duration_ms}
const usage = data.usage || {};
const tokStr = usage.total_tokens ? `${formatTokens(usage.total_tokens)} tok` : '';
const durStr = usage.duration_ms ? `${(usage.duration_ms / 1000).toFixed(1)}s` : '';
const toolStr = data.last_tool_name ? `${data.last_tool_name}…` : 'processando…';
meta.textContent = [toolStr, tokStr, durStr].filter(Boolean).join(' · ');
```

**Em `renderSubagentLineSummary` (linha 1149)**: mapear `data.status` para classes CSS:

```js
line.classList.remove('running');
const cssState = data.status === 'failed' ? 'failed'
               : data.status === 'stopped' ? 'stopped'
               : data.status === 'error' ? 'error'
               : 'done';
line.classList.add(cssState);
```

**Substituir `toggleSubagentExpand` por `openSubagentModal`** (linha 1214):

- Inline expansion atual fica como fallback (se `USE_SUBAGENT_MODAL=false`)
- Modal carrega via `GET .../transcript` lazy
- Modal renderiza 3 seções: prompt, timeline, findings
- Botão "Mostrar PII" só visível para admin (via `window.AGENT_DEBUG.is_admin`)

**Novas funções**:

```js
async function openSubagentModal(agentId) { ... }
function closeSubagentModal() { ... }
async function togglePIIInModal(agentId, enabled) { ... }
function renderTranscriptTimeline(entries) { ... }
function jumpToParentMessage(parentToolUseId) { ... }
```

#### `app/agente/templates/agente/chat.html` — markup do modal

Adicionar **antes** do `#artifact-modal` existente, seguindo o mesmo padrão (overlay custom, não Bootstrap):

```html
<div id="subagent-transcript-modal" class="subagent-modal" hidden>
  <div class="subagent-modal-backdrop" data-close="modal"></div>
  <div class="subagent-modal-panel" role="dialog" aria-labelledby="subagent-modal-title">
    <header class="subagent-modal-header">
      <span class="subagent-modal-badge"></span>
      <h2 id="subagent-modal-title"></h2>
      <span class="subagent-modal-meta"></span>
      <div class="subagent-modal-actions">
        <button class="btn-pii-toggle" hidden>Mostrar PII</button>
        <button class="btn-download-jsonl" hidden>JSONL</button>
        <button class="btn-close" data-close="modal">×</button>
      </div>
    </header>
    <section class="subagent-modal-section" data-section="prompt">
      <h3>Prompt do agente principal</h3>
      <pre class="prompt-content"></pre>
    </section>
    <section class="subagent-modal-section" data-section="timeline">
      <h3>Timeline</h3>
      <ol class="timeline-list"></ol>
    </section>
    <section class="subagent-modal-section" data-section="findings">
      <h3>Findings</h3>
      <div class="findings-content"></div>
    </section>
  </div>
</div>
```

#### `app/static/agente/css/_subagent-modal.css` — novo arquivo

- Estados visuais ricos (`.failed` red, `.stopped` grey + ícones)
- Modal overlay (z-index 1050, igual ao `#artifact-modal`)
- Design tokens (`var(--agent-*)`) — sem hex hardcoded
- Light/dark mode automático via tokens
- Linha de correlação parent (CSS pseudo-element `::before` na linha inline)

Import em `app/static/agente/css/agent-theme.css`.

#### `app/static/agente/css/_subagent-inline.css` — extensões

- `.subagent-inline.failed .subagent-dot { background: var(--agent-danger); }` (adicionar)
- `.subagent-inline.stopped .subagent-dot { background: var(--text-muted); }`
- `.subagent-inline[data-parent-tool-use-id]::before` — linha conectora sutil ao parent
- Cursor `pointer` agora abre modal (não toggle inline) quando `USE_SUBAGENT_MODAL=true`

### 5.3 Resumo de arquivos tocados

| Fase | Arquivo | Tipo |
|---|---|---|
| 1 | `app/agente/sdk/client.py` | Modificação (extensão de metadata) |
| 1 | `app/agente/sdk/subagent_reader.py` | Modificação (+`get_subagent_transcript`) |
| 1 | `app/agente/routes/subagents.py` | Modificação (+2 endpoints) |
| 1 | `app/agente/config/feature_flags.py` | +5 flags |
| 1 | `app/static/agente/js/chat.js` | Modificação extensa |
| 1 | `app/agente/templates/agente/chat.html` | +markup modal |
| 1 | `app/static/agente/css/_subagent-modal.css` | **Arquivo novo** |
| 1 | `app/static/agente/css/_subagent-inline.css` | Modificação |
| 1 | `app/static/agente/css/agent-theme.css` | +import `_subagent-modal.css` |
| 1 | `tests/agente/test_subagent_transcript.py` | **Arquivo novo** |
| 1 | `tests/agente/test_subagent_routes.py` | **Arquivo novo** |
| 1 | `tests/agente/test_subagent_client_metadata.py` | **Arquivo novo** |
| 2 | `app/agente/routes/subagents.py` | +2 endpoints (PATCH, output_file) |
| 2 | `app/static/agente/js/chat.js` | +botões modal (rename, tag, download) |
| 2 | `tests/agente/test_subagent_routes.py` | +5 testes Fase 2 |

**Zero migration SQL. Zero novo worker RQ. Zero nova tabela.**

---

## 6. Fluxo de dados + riscos mapeados

### 6.1 Cenário 1 — Subagent inicia e progride (P0.2, P0.3, P1.1)

```
[1] Usuario digita prompt no chat
        │
        ▼
[2] SDK delega para subagente (TaskStartedMessage chega no stream)
        │       ─── RISCO A ───
        ▼
[3] client.py:_parse_sdk_message le getattr(message, 'tool_use_id', None)
        │       Mitigacao: getattr defensivo. Se campo NAO existe no SDK
        │       (versao antiga), valor = None, frontend ignora correlacao.
        │       Comportamento atual NAO regride.
        ▼
[4] StreamEvent('task_started') emit com metadata enriquecido
        │
        ▼
[5] routes/chat.py:_process_stream_event re-emite como SSE
        │
        ▼
[6] chat.js case 'task_started': renderSubagentLineStart(data)
        │
        ▼
[7] SDK envia TaskProgressMessage com usage = {total_tokens, tool_uses, duration_ms}
        │       ─── RISCO B ───
        ▼
[8] client.py captura usage via getattr (defensivo)
        │
        ▼
[9] chat.js renderSubagentLineProgress atualiza meta:
    "Grep · 3.4K tok · 12s"
        │
        ▼
[10] SDK envia TaskNotificationMessage com status (completed/failed/stopped)
        │
        ▼
[11] chat.js renderSubagentLineSummary aplica classe CSS:
     .done (verde) / .failed (vermelho) / .stopped (cinza)
```

### 6.2 Cenário 2 — Usuário abre modal de transcript (P0.1)

```
[1] Usuario clica na linha inline do subagent
        │
        ▼
[2] chat.js openSubagentModal(agentId)
        │
        ▼
[3] fetch GET /agente/api/sessions/<sid>/subagents/<aid>/transcript
        │       ─── RISCO C ───
        ▼
[4] routes/subagents.py valida:
    - USE_SUBAGENT_MODAL ON?   → 404 se OFF
    - sessao existe?           → 404
    - usuario = dono OU admin? → 403
    - _is_safe_id(agent_id)?   → 404
        │
        ▼
[5] subagent_reader.get_subagent_transcript(sid, aid, include_pii=is_admin_unmasked)
        │       ─── RISCO D ───
        │       include_pii=True so se admin TIVER feito toggle valido em Redis.
        ▼
[6] Reader le JSONL via get_subagent_messages do SDK
        │       ─── RISCO E ───
        │       3 fallbacks ja existentes: default, /tmp/.claude, S3 archive.
        ▼
[7] Parse cronologico
        │       ─── RISCO F ───
        │       Cap max_content_chars=4000 por entry. JSONL corrompido = linha
        │       ignorada (pattern existente).
        ▼
[8] Sanitizacao PII por entry
        │
        ▼
[9] Response JSON
        │
        ▼
[10] chat.js renderTranscriptTimeline preenche modal
     Botao "Mostrar PII" so renderizado se window.AGENT_DEBUG.is_admin = true
```

### 6.3 Cenário 3 — Admin toggle "Mostrar PII"

```
[1] Admin clica botao "Mostrar PII" no modal
        │
        ▼
[2] chat.js POST /agente/api/sessions/<sid>/subagents/<aid>/pii-toggle
    body: {enabled: true}
        │       ─── RISCO G ───
        ▼
[3] routes valida:
    - current_user.perfil == 'administrador' → senao 403
    - rate limit: max 10 toggles/min por user (Redis)
        │
        ▼
[4] Registra audit em agent_sessions.data['subagent_pii_audit']
    FIFO cap 100 entries.
    flag_modified(session, 'data')  ← R7 obrigatorio (CLAUDE.md)
        │
        ▼
[5] SETEX Redis agent:pii_unmask:{user_id}:{sid}:{aid} 300 "1"
        │       TTL 5min — toggle expira sozinho.
        ▼
[6] Retorna {success, expires_in: 300}
        │
        ▼
[7] chat.js refetch GET .../transcript?include_pii=true
        │
        ▼
[8] Backend valida: admin + Redis EXISTS antes de incluir PII.
    Defesa em profundidade.
```

### 6.4 Cenário 4 — Rename/tag (Fase 2)

```
[1] Admin clica icone rename no modal
        │
        ▼
[2] PATCH /agente/api/sessions/<sid>/subagents/<aid>
    body: {name: "Analise pedido VCD123"}
        │       ─── RISCO H ───
        ▼
[3] Validacao:
    - flag USE_SUBAGENT_RENAME_TAG ON? → 404 se OFF
    - dono OU admin? → 403
    - name: max 80 chars, bleach.clean()
    - tags: max 10, cada max 30 chars
        │
        ▼
[4] data.setdefault('subagent_metadata', {})[agent_id] = {
        'name': name, 'tags': tags,
        'updated_at': agora_brasil_naive().isoformat(),
        'updated_by': current_user.id
    }
    flag_modified(session, 'data')
    db.session.commit()
```

### 6.5 Mapa de riscos e mitigações

| ID | Risco | Camada | Mitigação | Detectável por |
|---|---|---|---|---|
| **A** | SDK pode não ter `tool_use_id` em `TaskStartedMessage` | SDK boundary | `getattr(..., None)` defensivo. Frontend ignora se None. | Smoketest |
| **B** | SDK pode não popular `usage` em `TaskProgressMessage` | SDK boundary | `getattr(..., None)` + frontend mostra meta antiga | Smoketest |
| **C** | Endpoint chamado com flag OFF | Backend | 404 explícito + feature flag check | Teste unitário |
| **D** | PII vazado para non-admin | Backend | `include_pii=True` requer admin **E** Redis token válido (defesa em profundidade) | Teste unitário + audit log |
| **E** | JSONL transcript não existe (Render restart) | Backend | 3 fallbacks (filesystem + S3 archive). Path traversal bloqueado. | Smoketest existente |
| **F** | JSONL corrompido | Backend | Linha inválida = ignorada. Findings parciais > crash. | Teste com fixture corrompido |
| **G** | Admin abusa toggle PII | Backend | Audit log FIFO + rate limit Redis + TTL 5min | Query no audit log |
| **H** | XSS via rename/tag | Backend | `bleach.clean()` server-side + escape client-side | Teste XSS payload |

### 6.6 Pontos onde existing code NÃO muda (proteção contra regressão)

- **Linha inline atual** (`renderSubagentLineStart/Progress/Summary/ValidationWarning`): código se mantém — apenas **estende**. Se flag novo for OFF, comportamento atual preservado pixel-perfect.
- **`subagent_reader.get_subagent_summary`**: zero alteração. Continua sendo usado por `api_user_subagent_summary` (linha 61 de `routes/subagents.py`) e workers de validação.
- **`api_admin_*` endpoints** em `admin_subagents.py`: zero alteração. Forense admin continua funcionando.
- **Subagent SSE events** (`task_started`, `task_progress`, `task_notification`, `subagent_summary`, `subagent_validation`): só **adicionam** metadata; campos antigos preservados. Backward-compat 100%.
- **Persistência**: zero migration. Defaults via `setdefault` em runtime — sessões antigas sem o sub-path funcionam normalmente.

---

## 7. Tratamento de erros

### 7.1 Erros frontend → backend (no modal)

| Cenário | HTTP | Mensagem | Ação UI |
|---|---|---|---|
| Feature flag OFF | 404 | "Visualização detalhada indisponível no momento." | Fecha modal, mantém linha inline com expand antigo (fallback) |
| Sessão não pertence ao user | 403 | "Você não tem acesso a esta sessão." | Fecha modal |
| Subagent não encontrado (JSONL ausente) | 404 | "Transcript não encontrado. A sessão pode ter sido arquivada." | Botão "Tentar restaurar do arquivo" |
| Transcript corrompido (JSONL parse error) | 200 + parcial | Banner amarelo: "Algumas entradas não puderam ser lidas. Mostrando o que foi recuperado." | Renderiza o que foi parseado |
| Erro genérico backend | 500 | "Não foi possível carregar o transcript. Tente novamente em instantes." | Botão "Tentar novamente" + log Sentry |
| Network timeout (>30s) | — | "Conexão lenta. Verifique sua rede e tente novamente." | Abort + retry button |

### 7.2 Erros do PII toggle (admin)

| Cenário | HTTP | Mensagem | Ação UI |
|---|---|---|---|
| Non-admin tenta toggle | 403 | (botão nunca renderiza para non-admin) | Defesa em profundidade backend |
| Rate limit excedido | 429 | "Muitas trocas em sequência. Aguarde 1 minuto." | Desabilita botão por 60s |
| Redis indisponível | 500 | "Recurso temporariamente indisponível." | Botão volta ao estado anterior + log Sentry |

### 7.3 Erros do rename/tag (Fase 2)

| Cenário | HTTP | Mensagem | Ação UI |
|---|---|---|---|
| Nome > 80 chars | 400 | "Nome deve ter no máximo 80 caracteres." | Input mantém foco + counter visual |
| Tag inválida (chars proibidos) | 400 | "Tag contém caracteres não permitidos." | Highlight da tag inválida |
| Conflito de update (race condition entre 2 abas) | 409 | "Outro usuário atualizou este subagent. Recarregue para ver as mudanças." | Refresh button |

### 7.4 Erros do download `output_file` (Fase 2)

| Cenário | HTTP | Mensagem | Ação UI |
|---|---|---|---|
| JSONL ausente local + S3 também | 404 | "Arquivo não disponível para download." | Esconde botão |
| Arquivo > 50MB (sanity check) | 413 | "Arquivo muito grande para download direto." | Sugere usar admin endpoint |
| Mask_pii falha em alguma linha | 200 + warning | (silencioso, log Sentry) | Download continua |

### 7.5 Erros silenciados + logados (não chegam ao usuário)

| Cenário | Camada | Tratamento |
|---|---|---|
| Path traversal tentado (`agent_id` malformado) | `_is_safe_id` | Loga `logger.warning`, retorna 404 (não revela validação) |
| Race condition no JSONB | SQLAlchemy | `try/except IntegrityError`, retry uma vez, depois 409 |
| Redis pubsub `subagent_summary` race | client.py | Já mitigado (R-MULTIWORKER) — fallback para `event_queue` local |

### 7.6 Logging server-side

Padrão atual: `logger = logging.getLogger('sistema_fretes')`. Manter.

```python
# Padrao em cada endpoint novo:
logger.info(
    f"[subagent_transcript] user_id={current_user.id} "
    f"session={session_id[:16]} agent={agent_id[:12]} "
    f"include_pii={include_pii} entries={len(transcript)}"
)

# Sentry tag:
import sentry_sdk
with sentry_sdk.push_scope() as scope:
    scope.set_tag("feature", "subagent_modal")
    scope.set_tag("agent_id_prefix", agent_id[:8])
```

### 7.7 Loading / empty / error states no modal

Três estados visuais sempre cobertos: skeleton (loading), placeholder com botão "Tentar restaurar do S3" (empty), e botão "Tentar novamente" (error). Detalhes em mockups no plano de implementação.

### 7.8 Telemetria

```python
# Endpoint /transcript: incrementa Redis counter
redis.hincrby('agent:metrics:subagent_modal:daily', date_str, 1)

# Endpoint /pii-toggle: ja gerado audit em JSONB (cobre)

# Frontend: console.log estruturado para Sentry breadcrumbs
console.log('[subagent-modal] opened', {agent_id, has_admin_toggle})
```

---

## 8. Testes

### 8.1 Inventário

| Tipo | Local | Quando rodar |
|---|---|---|
| Unitário backend | `tests/agente/test_subagent_*.py` (NOVOS) | Pré-commit (manual) + CI futuro |
| Smoketest SDK | `/api/admin/debug/subagent-smoketest` (já existe + extensão) | Pós-deploy, manual |
| E2E manual | Checklist em Definition of Done | Antes de habilitar feature flag em prod |
| Regression visual | `tests/visual/` (existente, Playwright + PIL) | Antes de cada PR que toca CSS/templates |
| Lint UI | `scripts/audits/ui_policy_lint.py --enforce-new` | Pré-commit (hook já existe) |

### 8.2 Testes unitários — Fase 1 (3 arquivos novos)

#### `tests/agente/test_subagent_transcript.py` (8 testes)

```python
def test_transcript_inclui_prompt_inicial(fake_subagent_jsonl):
    """1a UserMessage do JSONL = user_prompt."""

def test_transcript_ordenacao_cronologica(fake_subagent_jsonl):
    """sequence cresce monotonicamente."""

def test_transcript_correlaciona_tool_use_tool_result(fake_subagent_jsonl):
    """tool_use_id linka tool_use -> tool_result."""

def test_transcript_mask_pii_quando_include_pii_false(fake_subagent_jsonl):
    """CPF/CNPJ/email mascarados em todas entries quando flag off."""

def test_transcript_jsonl_corrompido_retorna_parcial(fake_subagent_jsonl):
    """Linha invalida = skip. Resto e retornado."""

def test_transcript_jsonl_inexistente_retorna_vazio(tmp_path):
    """Sem JSONL, retorna []."""

def test_transcript_path_traversal_bloqueado():
    """agent_id com '..' ou '*' = []."""

def test_transcript_respeitar_max_content_chars():
    """Content > max e truncado."""
```

#### `tests/agente/test_subagent_routes.py` (9 testes Fase 1 + 5 Fase 2)

Cobertura dos 4 endpoints novos:

```python
# Fase 1:
def test_transcript_404_se_feature_flag_off(client, app): ...
def test_transcript_403_se_nao_dono_nem_admin(client, other_user_session): ...
def test_transcript_200_dono_recebe_pii_mascarada(client, dono_user, sess): ...
def test_transcript_admin_com_pii_toggle_recebe_raw(client, admin_user, sess): ...
def test_pii_toggle_registra_audit_log(client, admin_user, sess): ...
def test_pii_toggle_rate_limit_10_por_minuto(client, admin_user, sess, redis_client): ...
def test_pii_toggle_403_non_admin(client, dono_user, sess): ...
def test_pii_toggle_redis_setex_5min(client, admin_user, sess, redis_client): ...
def test_pii_toggle_404_se_flag_off(client, admin_user, sess): ...

# Fase 2:
def test_patch_subagent_persiste_em_jsonb(client, dono_user, sess): ...
def test_patch_subagent_sanitiza_html(client, dono_user, sess): ...
def test_patch_subagent_400_se_nome_muito_longo(client, dono_user, sess): ...
def test_download_output_file_admin_recebe_raw(client, admin_user, sess): ...
def test_download_output_file_non_admin_recebe_mask(client, dono_user, sess): ...
```

#### `tests/agente/test_subagent_client_metadata.py` (3 testes)

```python
def test_task_progress_propaga_usage(): ...
def test_task_progress_usage_ausente_nao_quebra(): ...
def test_task_started_propaga_parent_tool_use_id(): ...
```

### 8.3 Smoketest existente — extensão

`api_admin_subagent_smoketest` (`routes/admin_subagents.py:281-373`) ganha verificação adicional:

```python
# Adicionar em api_admin_subagent_smoketest:
from app.agente.sdk.subagent_reader import get_subagent_transcript
transcript = get_subagent_transcript(row.session_id, agent_ids[0])
report['transcript_entries'] = len(transcript)
report['has_user_prompt'] = any(e.kind == 'user_prompt' for e in transcript)
# healthy requer (entries > 0 AND has_user_prompt)
```

### 8.4 E2E manual checklist (Fase 1)

Sequência para validar antes de habilitar `USE_SUBAGENT_MODAL=true` em prod:

1. [ ] Abrir sessão chat web no agente Nacom
2. [ ] Pedir algo que dispara subagent (ex: "analise pedido VCD123" → `analista-carteira`)
3. [ ] Observar linha inline aparecer com estado `running`
4. [ ] Linha mostra meta atualizando: tokens · duração · tool atual (P0.3)
5. [ ] Linha vira `done` ao terminar (P0.2) — se subagent falhar, vira `failed`
6. [ ] Click na linha → modal abre
7. [ ] Modal mostra: prompt enviado, timeline cronológica, findings
8. [ ] PII em CPFs/CNPJs visíveis na timeline = mascarada
9. [ ] Como admin, botão "Mostrar PII" aparece. Click → PII revelada. Reload em 5min → mascara de novo.
10. [ ] DevTools Network: GET /transcript retorna 200 e payload bem-formado
11. [ ] DevTools Console: sem erros JS
12. [ ] Feature flag `USE_SUBAGENT_MODAL=false` → fallback inline expand continua funcionando

**Bloqueador de promoção**: qualquer um dos 12 falhando → não habilita em prod.

### 8.5 Regression visual

`tests/visual/` já existe. Capturar screenshots **antes** de mudar CSS:
- Linha inline em estado running, done, failed, stopped, validation_warning
- Modal fechado (não impacta)

Threshold típico: 2% diff por imagem.

### 8.6 Smoketest pós-deploy automatizado

Após deploy em prod:

```bash
curl https://sistema-fretes.onrender.com/agente/api/admin/debug/subagent-smoketest \
  -H "Cookie: session=$ADMIN_SESSION"
```

Resposta esperada: `healthy: true, transcript_entries > 0, has_user_prompt: true`.

Se `healthy: false` por 3 ciclos (cron 6h cada = 18h) → rollback automático sugerido: env var `USE_SUBAGENT_MODAL=false`.

### 8.7 Cobertura de testes — meta

| Componente | Cobertura mínima |
|---|---|
| `subagent_reader.get_subagent_transcript` | 80%+ |
| `routes/subagents.py` endpoints | 90%+ |
| `client.py _parse_sdk_message` task_* | 70%+ |

Verificação via `pytest --cov=app/agente/sdk --cov=app/agente/routes/subagents`.

### 8.8 Garantia de não-quebrar-existente

Antes de qualquer commit Fase 1, rodar:

```bash
pytest tests/agente/ -v
```

Listagem rápida de testes que vou tocar transversalmente (precisa não-regredir):
- `tests/agente/test_*` (todos os existentes)
- `pytest tests/ -k subagent`

---

## 9. Definition of Done

### 9.1 Fase 1 — Done quando TODOS os 18 itens checados

**Backend:**
- [ ] `client.py:_parse_sdk_message` propaga `usage` em `task_progress.metadata` (verificar SSE no DevTools)
- [ ] `client.py` propaga `parent_tool_use_id` em `task_started.metadata`
- [ ] `subagent_reader.get_subagent_transcript` retorna timeline com `user_prompt`
- [ ] `GET /api/sessions/<sid>/subagents/<aid>/transcript` retorna 200/403/404 corretos
- [ ] `POST /api/sessions/<sid>/subagents/<aid>/pii-toggle` retorna 200/403/429
- [ ] Audit log em `agent_sessions.data['subagent_pii_audit']` populado a cada toggle
- [ ] Redis token PII com TTL 5min funcionando
- [ ] `_is_safe_id` aplicado em todos endpoints novos (anti-path-traversal)
- [ ] 5 feature flags adicionadas em `config/feature_flags.py`

**Frontend:**
- [ ] Linha inline mostra `tokens · duração · tool` em runtime (P0.3)
- [ ] Linha inline tem 5 estados visuais distintos: running/done/failed/stopped/validation_warning
- [ ] Linha inline tem correlação visual com mensagem do parent (P1.1)
- [ ] Click na linha → modal abre com prompt + timeline + findings
- [ ] Modal: botão "Mostrar PII" visível só para admin, expira em 5min
- [ ] Modal: erro handling (404/403/500/timeout) com mensagens claras

**Testes + verificação:**
- [ ] `tests/agente/test_subagent_transcript.py` — 8 testes passando
- [ ] `tests/agente/test_subagent_routes.py` — 9 testes passando (Fase 1)
- [ ] `tests/agente/test_subagent_client_metadata.py` — 3 testes passando
- [ ] Smoketest retorna `healthy: true` com `has_user_prompt: true`
- [ ] Pytest existing em `tests/agente/` continua passando (zero regressão)
- [ ] Feature flag OFF → comportamento atual preservado (regression test manual)

### 9.2 Fase 2 — Done quando TODOS os 10 itens checados

**Backend:**
- [ ] `PATCH /api/sessions/<sid>/subagents/<aid>` aceita `{name, tags}`, persiste em JSONB
- [ ] Sanitização HTML via `bleach.clean()` em name/tags
- [ ] `flag_modified(session, 'data')` aplicado (R7)
- [ ] `GET /api/sessions/<sid>/subagents/<aid>/output_file` streama JSONL com mask_pii para non-admin
- [ ] Fallback S3 (`restore_session_from_s3`) quando JSONL local ausente
- [ ] 2 flags Fase 2 adicionadas em feature_flags.py

**Frontend:**
- [ ] Modal: ícones rename/tag visíveis (admin) e funcionando
- [ ] Modal: botão "Download JSONL" visível (admin) e funcionando

**Testes:**
- [ ] `tests/agente/test_subagent_routes.py` — +5 testes Fase 2 passando
- [ ] Teste XSS payload no rename (sanitização)

---

## 10. Plano de rollout em prod (big-bang)

**Estratégia escolhida pelo dono do produto**: big-bang. Todas as features da Fase 1 ativadas simultaneamente no merge da PR-A; idem Fase 2 no merge da PR-B. Sem habilitação gradual de flags. Feature flags permanecem como **circuit breakers** apenas para rollback em emergência.

```
[FASE 1 deploy]
   │
   1. Merge PR-A → auto-deploy Render disparado
      Defaults em config/feature_flags.py:
        USE_SUBAGENT_MODAL=true
        USE_SUBAGENT_RICH_STATES=true
        USE_SUBAGENT_LIVE_PROGRESS=true
   │
   2. Deploy completa (~13 min observado em deploys recentes)
   │
   3. Smoketest pós-deploy:
      curl /agente/api/admin/debug/subagent-smoketest
      → Esperado: healthy=true, has_user_prompt=true
   │
   4. Usuario executa Roadmap de Testes (secao 10.2)
      → Confirma todos blocos A-J passando
   │
   5. Monitoramento Sentry: query "feature:subagent_modal" + "agent_id_prefix:*"
      → Esperado: zero novas issues nas primeiras 24h
```

Mesma sequência para Fase 2 ao mergear PR-B (com blocos F e G do roadmap).

### 10.1 Rollback atômico

Cada flag é independente:

| Sintoma | Ação | Tempo |
|---|---|---|
| Modal causa JS error visível | `USE_SUBAGENT_MODAL=false` (env var Render) | < 30s |
| Endpoint /transcript explode em prod | Mesmo flag desliga (404 nativo) | < 30s |
| Estados visuais quebram CSS de outras telas | `USE_SUBAGENT_RICH_STATES=false` | < 30s |
| Live progress causa flood de SSE | `USE_SUBAGENT_LIVE_PROGRESS=false` | < 30s |
| Toggle PII admin sendo abusado | Redis DELETE em `agent:pii_unmask:*` | < 30s |
| Rename/tag corrompe JSONB | `USE_SUBAGENT_RENAME_TAG=false` + script cleanup do sub-path | 5-15min |
| Erro em SDK boundary (`client.py`) | Revert do commit específico (mudança ~10 linhas) | 5-10min |

**Garantia chave**: zero migration DDL → rollback = mudar env var + restart Render worker. Sem risco de schema inconsistente entre deploys.

### 10.2 Roadmap de testes do usuário (E2E pós-deploy)

**Pré-requisitos**:
- 1 conta admin (`perfil='administrador'`)
- 1 conta user normal (dono de sessão, perfil padrão)
- Chat web aberto em https://sistema-fretes.onrender.com/agente/chat
- DevTools aberto (aba Network + Console)
- Acesso ao Sentry (https://nacom.sentry.io)

**Tempo estimado total**: 30-45min para Fase 1 (blocos A-E + H-J), +10-15min para Fase 2 (blocos F-G).

---

#### Bloco A — Estados visuais (P0.2)

Cada estado tem cor + ícone distintos. Verificar visualmente.

| # | Cenário | Como reproduzir | Resultado esperado |
|---|---|---|---|
| A.1 | Estado `running` | Pedir "analise pedido VCD123 com analista-carteira" | Dot amarelo pulsando + badge `analista-carteira` + meta "executando..." |
| A.2 | Estado `done` | Aguardar conclusão de A.1 | Dot verde fixo + meta `N tools · Xs · $Y` |
| A.3 | Estado `failed` | Pedir "usar analista-carteira para algo invalido que falhe" (ou matar SDK no meio) | Dot vermelho + meta com `status=failed` |
| A.4 | Estado `stopped` | Iniciar subagent, clicar botão Interromper no chat | Dot cinza + meta com `status=stopped` |
| A.5 | Estado `validation_warning` | (depende do worker Haiku detectar inconsistência) — opcional, pode pular se não reproduzir | Ícone ⚠ amarelo sobreposto à linha |

**Bloqueador**: A.1 a A.4 obrigatórios. A.5 best-effort.

---

#### Bloco B — Progresso ao vivo (P0.3)

Durante execução de A.1, observar a linha:

| # | Cenário | Resultado esperado |
|---|---|---|
| B.1 | Meta inicial | `executando...` |
| B.2 | Meta com tool em uso | `Bash...` ou `Grep...` (último tool chamado pelo subagent) |
| B.3 | Meta com tokens | `Grep · 1.2K tok · 5s` (atualiza periodicamente) |
| B.4 | Meta final | `5 tools · 12s · $0.04` (após conclusão) |

**DevTools verificação**: aba Network → eventos `task_progress` SSE devem ter `metadata.usage` populado.

**Bloqueador**: B.1 e B.4 obrigatórios. B.2 e B.3 confirmam metadata SDK chegando.

---

#### Bloco C — Modal transcript (P0.1)

| # | Cenário | Resultado esperado |
|---|---|---|
| C.1 | Click na linha | Modal full-screen abre, backdrop escurece chat |
| C.2 | Seção "Prompt do agente principal" | Não vazia, mostra texto enviado pelo agente principal ao subagent (ex: "Analise pedido VCD123 com regras P1-P7") |
| C.3 | Seção "Timeline" | Lista cronológica: user_prompt → assistant_text → tool_use → tool_result → ... |
| C.4 | Seção "Findings" | Texto final do subagent (resposta retornada ao parent) |
| C.5 | ESC | Modal fecha |
| C.6 | Click no backdrop | Modal fecha |
| C.7 | Botão X | Modal fecha |

**DevTools verificação**: aba Network → GET `/agente/api/sessions/<sid>/subagents/<aid>/transcript` retorna 200, payload tem 3 seções (`prompt`, `timeline`, `findings`).

**Bloqueador**: TODOS obrigatórios. C.2 é a feature principal — sem ele, modal é só decoração.

---

#### Bloco D — PII e admin toggle (segurança crítica)

Pré-requisito: subagent executado tem CPFs/CNPJs nos tools (ex: consulta de cliente Atacadão).

| # | Cenário | Como reproduzir | Resultado esperado |
|---|---|---|---|
| D.1 | User normal vê PII mascarada | Login como user normal, abrir modal de subagent que consultou cliente | CPFs aparecem como `***.***.***-**`, CNPJs como `**.***.***/****-**` |
| D.2 | Admin sem toggle vê PII mascarada | Login como admin, abrir modal SEM clicar "Mostrar PII" | Mesma máscara de D.1 |
| D.3 | Admin com toggle vê PII raw | Click no botão "Mostrar PII" no modal | CPFs/CNPJs aparecem em texto bruto. Reload do modal já mostra raw (Redis token válido) |
| D.4 | Audit log incrementado | Após D.3, verificar via SQL: `SELECT data->'subagent_pii_audit' FROM agent_sessions WHERE session_id='<sid>'` | Entry com `{agent_id, user_id, enabled:true, timestamp}` |
| D.5 | Toggle expira em 5min | Após D.3, aguardar 5min, reabrir modal | PII volta a mascarar |
| D.6 | Rate limit 10/min | Click 11x consecutivos no botão "Mostrar PII" | 11ª tentativa retorna 429 com mensagem "Muitas trocas em sequência. Aguarde 1 minuto." |
| D.7 | User normal NÃO vê botão | Login como user normal, abrir modal | Botão "Mostrar PII" não renderizado no DOM |

**Bloqueador**: TODOS obrigatórios — falha de qualquer um é vazamento de PII.

---

#### Bloco E — Correlação parent (P1.1)

| # | Cenário | Resultado esperado |
|---|---|---|
| E.1 | Linha inline tem marcador `↳` | Próximo à badge do subagent, visível |
| E.2 | Linha está visualmente alinhada com mensagem do parent | CSS conector mostra qual mensagem disparou o subagent |
| E.3 | Click no marcador `↳` | (Fase 1 opcional) Scroll do chat para a mensagem do parent + highlight temporário |

**Bloqueador**: E.1 obrigatório (correlação visual). E.2 e E.3 best-effort.

---

#### Bloco F — Rename/tag (Fase 2, P1.2)

Pré-requisito: PR-B mergeada. Flag `USE_SUBAGENT_RENAME_TAG=true`.

| # | Cenário | Como reproduzir | Resultado esperado |
|---|---|---|---|
| F.1 | Admin renomeia subagent | Modal → ícone ✎ → digita "Analise pedido VCD123" → Salvar | Header do modal mostra novo nome. Linha inline no chat também atualiza |
| F.2 | Admin adiciona tag | Modal → ícone 🏷️ → adiciona "p3" e "urgente" → Salvar | Badges de tag aparecem no modal e na linha |
| F.3 | Admin remove tag | Modal → click no X de uma tag | Tag desaparece |
| F.4 | Persistência | Recarregar a página, reabrir mesmo subagent | Nome e tags persistem |
| F.5 | XSS payload sanitizado | Renomear para `<script>alert(1)</script>` | Salva como string escapada; sem alert disparado |
| F.6 | Nome > 80 chars rejeitado | Tentar salvar nome com 100 chars | HTTP 400 + mensagem "Nome deve ter no máximo 80 caracteres." |
| F.7 | Tags > 10 rejeitadas | Tentar adicionar 11ª tag | HTTP 400 + mensagem clara |

**SQL para verificação**: `SELECT data->'subagent_metadata' FROM agent_sessions WHERE session_id='<sid>'` → deve mostrar entry para o `<agent_id>`.

**Bloqueador**: F.1, F.2, F.5 (XSS), F.6 obrigatórios.

---

#### Bloco G — Download output_file (Fase 2, P1.3)

Pré-requisito: Flag `USE_SUBAGENT_OUTPUT_DOWNLOAD=true`.

| # | Cenário | Como reproduzir | Resultado esperado |
|---|---|---|---|
| G.1 | Admin baixa JSONL raw | Modal → botão "JSONL" | Download de `<agent_id>.jsonl` com Content-Type `application/jsonl`. Arquivo tem dados raw sem mask |
| G.2 | User normal baixa JSONL com mask | Login user normal → mesmo modal → "JSONL" | Download com CPFs/CNPJs mascarados linha a linha |
| G.3 | JSONL ausente (sessão arquivada) | Tentar baixar de sessão > 30 dias | Sistema tenta restore S3; se falhar: 404 + botão escondido |
| G.4 | Arquivo > 50MB | (raro; simulação manual) | HTTP 413 + mensagem "Arquivo muito grande para download direto." |

**Bloqueador**: G.1 e G.2 obrigatórios.

---

#### Bloco H — Backward-compat e rollback

Testar que rollback via env var funciona instantaneamente.

| # | Cenário | Como reproduzir | Resultado esperado |
|---|---|---|---|
| H.1 | Flag MODAL off | No Render dashboard, env var `USE_SUBAGENT_MODAL=false` + restart worker | Click na linha não abre modal; fallback inline expand antigo aparece |
| H.2 | Flag RICH_STATES off | Env var `USE_SUBAGENT_RICH_STATES=false` + restart | Linha volta aos 3 estados antigos (running/done/error). Sem failed/stopped distintos |
| H.3 | Flag LIVE_PROGRESS off | Env var `USE_SUBAGENT_LIVE_PROGRESS=false` + restart | Meta volta a `usando Grep...` simples, sem tokens/duração |
| H.4 | Subagent antigo (JSONL pré-modificação) | Abrir modal de sessão arquivada antes do deploy | Modal renderiza sem `parent_tool_use_id` (campo opcional); sem crash |

**Bloqueador**: H.1 obrigatório (circuit breaker mais importante).

Após teste, restaurar flags = `true` antes de prosseguir.

---

#### Bloco I — Performance

| # | Cenário | Resultado esperado | Como medir |
|---|---|---|---|
| I.1 | Modal abre rápido | < 1s para transcript médio (50 entries) | DevTools → Network → tempo de `/transcript` |
| I.2 | Sem flicker no SSE | Linha não pisca entre `task_progress` consecutivos | Observação visual + Performance recording |
| I.3 | SSE não floods | Eventos por minuto < 60 durante subagent ativo | DevTools → Network → count eventos `task_progress` |

**Bloqueador**: I.1 obrigatório. Se > 5s para transcripts pequenos, há regressão.

---

#### Bloco J — Erro handling

| # | Cenário | Como reproduzir | Resultado esperado |
|---|---|---|---|
| J.1 | Sessão arquivada (JSONL ausente) | Abrir modal de sessão > 30 dias antiga | Mensagem clara "Transcript não encontrado. A sessão pode ter sido arquivada." + botão "Tentar restaurar do arquivo" |
| J.2 | Rate limit PII | Já testado em D.6 | Botão desabilita por 60s, mensagem clara |
| J.3 | Network timeout | Throttling DevTools → "Offline" → click modal | Após 30s: "Conexão lenta. Verifique sua rede e tente novamente." + retry button |
| J.4 | 500 backend | (raro; simulação manual via DB lock) | Mensagem genérica clara + Sentry registra com tag `feature:subagent_modal` |
| J.5 | 403 cross-user | User A tenta abrir modal de sessão do User B | Mensagem "Você não tem acesso a esta sessão." |

**Bloqueador**: J.1 e J.5 obrigatórios.

---

#### Resumo de cobertura por fase

| Fase | Blocos obrigatórios | Total de cenários |
|---|---|---|
| **Fase 1** | A (1-4) + B (1, 4) + C (1-7) + D (1-7) + E (1) + H (1) + I (1) + J (1, 5) | **22 cenários** |
| **Fase 2** | F (1, 2, 5, 6) + G (1, 2) | **6 cenários adicionais** |

**Critério de aceitação para promoção em prod**: todos os cenários **Bloqueador** passando. Cenários best-effort podem falhar isoladamente sem bloquear.

### 10.3 Validação automatizada complementar

Em paralelo aos testes manuais, rodar smoketest:

```bash
# Espera healthy=true, transcript_entries>0, has_user_prompt=true
curl https://sistema-fretes.onrender.com/agente/api/admin/debug/subagent-smoketest \
  -H "Cookie: session=$ADMIN_SESSION_COOKIE"
```

E monitorar Sentry com filtro:

```
project:python-flask
environment:production
firstSeen:-1h
tags[feature]:subagent_modal
```

→ Esperado: zero issues novas durante o roadmap de testes.

---

## 11. Timeline estimado

| Etapa | Esforço | Quem |
|---|---|---|
| Escrever plano detalhado (writing-plans skill) | 30-60min | eu |
| Implementar Fase 1 backend (com TDD) | 4-6h | eu |
| Implementar Fase 1 frontend | 3-5h | eu |
| Testes pytest Fase 1 | 2-3h | eu |
| Code review (você) | 30-60min | você |
| Deploy Fase 1 (big-bang) | < 15min | auto-deploy Render |
| **Roadmap de testes Fase 1 (seção 10.2 blocos A-E + H-J)** | **30-45min** | **você** |
| Monitoramento Sentry pós-roadmap | 24h passive | você |
| **Total Fase 1** | **~15-22h trabalho ativo + 24h monitoring** | |
| Implementar Fase 2 | 3-5h | eu |
| Testes pytest Fase 2 | 1-2h | eu |
| Deploy Fase 2 | < 15min | auto-deploy |
| **Roadmap de testes Fase 2 (blocos F + G)** | **10-15min** | **você** |
| **Total Fase 2** | **~5-8h trabalho ativo + 24h monitoring** | |

Fases podem ser separadas por dias ou semanas — não há acoplamento entre elas. Roadmap de testes (seção 10.2) é critério **bloqueador** para considerar a fase entregue.

---

## 12. Riscos residuais reconhecidos

1. **SDK pode mudar shape de `parent_tool_use_id` em versão futura**: mitigado por `getattr(..., None)` defensivo + smoketest detecta
2. **Transcript JSONL pode crescer muito** (subagent que faz 50+ tool calls): mitigado por `max_content_chars=4000` por entry; teto absoluto Excel ~500KB
3. **Admin toggle PII pode ser usado sem necessidade real**: mitigado por audit log + TTL 5min + rate limit 10/min
4. **Modal não renderiza no Teams** (apenas web): comportamento esperado; backend retorna marcador e Teams ignora

---

## 13. Referências

- Avaliação inicial: ver histórico de chat (2026-05-13) — gap analysis vs Claude Code Agent View
- Claude Code Agent View docs: https://code.claude.com/docs/en/agent-view
- Claude Agent SDK subagents: https://code.claude.com/docs/en/agent-sdk/subagents
- Claude Agent SDK sessions: https://code.claude.com/docs/en/agent-sdk/sessions
- Module README: `app/agente/CLAUDE.md`
- Module sub-guide: `app/agente/services/CLAUDE.md`
- SDK changelog: `app/agente/SDK_CHANGELOG.md`
- Pattern Subagent Reliability: `.claude/references/SUBAGENT_RELIABILITY.md`
- Existing endpoints touched: `app/agente/routes/subagents.py`, `app/agente/routes/admin_subagents.py`
- Existing reader: `app/agente/sdk/subagent_reader.py`
- Existing frontend: `app/static/agente/js/chat.js:1093-1285`, `app/static/agente/css/_subagent-inline.css`

---

## 14. Histórico de decisões durante brainstorming

| Q | Decisão | Por quê |
|---|---|---|
| Q1: Forma do viewer | Modal full-screen | Reaproveita infra de `#artifact-modal`; foco máximo; padrão estabelecido |
| Q2: Granularidade do progresso ao vivo | Leve (tokens · duração · tool no meta) | Zero overhead novo no SSE; aproveita `TaskUsage` que já vem; tools detalhadas só no modal |
| Q3: Política PII | Toggle "Mostrar PII" para admin + audit log | Mitiga screenshot acidental do admin; mantém padrão atual para non-admin |
| Q4: Hierarquia `parent_tool_use_id` | Correlação visual sutil | Útil em sessões longas; custo baixo; preparado para futuro |
| Q5: Persistência rename/tag | Coluna JSONB custom em `agent_sessions.data` | Padrão já usado; sobrevive a qualquer mudança SDK; robusto |
| Q6: Delivery shape | 1 spec coeso, 2 fases sequenciais | Evita re-design entre PRs; Fase 1 maior valor primeiro |
| Q7: Arquitetura interna | Stateful em `chat.js` existente | `chat.js` é monolítico estável; padrão `#artifact-modal`; estado compartilhado |
| Q8: Rollout em prod | **Big-bang** (todas flags `true` no merge) + Roadmap de testes manual obrigatório | Usuário prefere validar tudo de uma vez via roadmap estruturado (seção 10.2) em vez de habilitar incrementalmente. Flags mantidas como circuit breakers para rollback emergencial |
