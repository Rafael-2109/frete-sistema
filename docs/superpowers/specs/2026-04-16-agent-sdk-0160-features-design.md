# Design — Features SDK Claude Agent 0.1.60

**Data**: 2026-04-16
**Status**: Aprovado (pendente revisao final do usuario)
**Autor**: Brainstorming com Rafael Nascimento
**Escopo**: `app/agente/`, `worker_render.py`, `worker_atacadao.py`, `docs/`, `.claude/references/`

---

## 1. Contexto e Motivacao

O projeto `frete_sistema` usa `claude-agent-sdk==0.1.60` com 11 subagentes especializados registrados em `.claude/agents/`. Os subagentes retornam resumos compactados (10:1 a 50:1) ao agente principal, gerando tres problemas conhecidos:

1. **Perda de informacao** — dados detalhados (SQL executado, resultados brutos, raciocinio) somem no resumo.
2. **Auditoria forense dificil** — investigar "por que o agente deu essa resposta?" exige re-executar ou escavar logs.
3. **Confianca nas respostas** — subagentes podem alucinar; hoje nao ha validacao automatizada.

A versao **0.1.60 do SDK** introduz duas APIs que resolvem a raiz do problema:

- `list_subagents(session_id) -> list[agent_id]`
- `get_subagent_messages(session_id, agent_id) -> list[SessionMessage]`

Com acesso estruturado ao transcript completo de cada subagente, podemos construir 6 features que transformam visibilidade, custo, confiabilidade e aprendizado do agente web.

## 2. Restricoes e Premissas

| Restricao | Origem |
|-----------|--------|
| Pipeline SSE 3-layer obrigatorio (R8) | `app/agente/CLAUDE.md:319-327` |
| Thread-safety via ContextVar (R2) | `app/agente/CLAUDE.md:163-174` |
| Hierarquia de timeouts (R3) | `app/agente/CLAUDE.md:226-244` |
| Timezone Brasil naive | `.claude/references/REGRAS_TIMEZONE.md` |
| Design tokens CSS (sem hex hardcoded) + dark mode | `~/.claude/CLAUDE.md` |
| Migrations: DDL + Python | `~/.claude/CLAUDE.md` |
| Worker RQ: reaproveitar existentes | Requisito do usuario |

**Premissa aceita**: `AgentSession.data` (JSONB) usado para persistencia granular em vez de tabela dedicada. Aceitamos trade-off de queries agregadas mais lentas em troca de zero DDL. Compensado com indice GIN direcionado e cache no `insights_service`.

## 3. Arquitetura Geral

### 3.1 Grupos de implementacao

Organizacao por tipo de consumidor (decisao B do brainstorming):

```
Grupo A (Backend/Leitura)                    Grupo B (UI user-facing)
─────────────────────────                    ─────────────────────────
#1 Admin endpoint debug                      #6 Linha inline expansivel
#3 Cost tracking granular                       └─ consome #1 endpoint
#5 Memory mining cross-subagent
   └─ todos leem via modulo comum (subagent_reader)

Grupo C (Migracao protocolo)                 Grupo D (Inteligencia)
──────────────────────────                   ──────────────────────
#2 Aposentar /tmp/ (soft)                    #4 Validacao anti-alucinacao
                                                 └─ consome #1, #3
```

### 3.2 Fundacao comum — `sdk/subagent_reader.py`

Modulo unico que encapsula acesso ao transcript do SDK. Todos os consumidores leem por aqui.

```python
# app/agente/sdk/subagent_reader.py

from claude_agent_sdk import list_subagents, get_subagent_messages

@dataclass
class SubagentSummary:
    agent_id: str
    agent_type: str           # "analista-carteira", etc.
    status: Literal["running", "done", "error"]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_ms: Optional[int]
    tools_used: list[dict]    # [{name, args_summary, result_summary, ts, duration_ms}]
    cost_usd: float
    input_tokens: int
    output_tokens: int
    num_turns: int
    findings_text: str        # assistant text final do subagent
    stop_reason: Optional[str]

def list_session_subagents(session_id: str) -> list[str]:
    """Wrapper de list_subagents — retorna agent_ids."""

def get_subagent_summary(
    session_id: str,
    agent_id: str,
    include_pii: bool = False,
    max_tool_chars: int = 500
) -> SubagentSummary:
    """
    Le mensagens completas + resume tools para exibicao/persistencia.
    Se include_pii=False, aplica pii_masker em args_summary/result_summary/findings_text.
    """

def get_session_subagents_summary(
    session_id: str,
    include_pii: bool = False
) -> list[SubagentSummary]:
    """Helper que combina list_session_subagents + get_subagent_summary em batch."""
```

**Benefico**: zero duplicacao. Se o SDK 0.1.61 mudar a API, um so ponto de ajuste.

### 3.3 Sanitizacao PII — `utils/pii_masker.py`

Util compartilhado usado por `subagent_reader` quando `include_pii=False`.

| Regex | Mascara |
|-------|---------|
| `\d{3}\.\d{3}\.\d{3}-\d{2}` (CPF) | `***.***.***-##` (preserva DV) |
| `\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}` (CNPJ) | `**.***.***/####-##` (preserva filial/DV) |
| `\d{11}` (CPF sem pontuacao, contexto) | `***********` |
| `\d{14}` (CNPJ sem pontuacao, contexto) | `**************` |
| `\S+@\S+\.\S+` (email) | `***@dominio.com` (preserva dominio) |

`current_user.perfil == 'administrador'` → `include_pii=True` em endpoints que suportam.

## 4. Detalhamento por Grupo

### 4.1 Grupo A — Backend/Leitura

#### Feature #1: Endpoint admin debug forense

**Objetivo**: Dev investigar respostas erradas do agente sem re-executar a sessao.

**Rotas** (novo blueprint sub `routes/admin_subagents.py`):

| Metodo | URL | Response |
|--------|-----|----------|
| `GET` | `/agente/api/admin/sessions/<session_id>/subagents` | `[{agent_id, agent_type, cost_usd, duration_ms, num_tools, status}]` |
| `GET` | `/agente/api/admin/sessions/<session_id>/subagents/<agent_id>` | `SubagentSummary` completo (raw, `include_pii=True`) |
| `GET` | `/agente/api/admin/sessions/<session_id>/subagents/<agent_id>/messages` | Lista bruta de `SessionMessage` (mais tecnico, para debug profundo) |

**Autenticacao**: `@login_required` + check inline `current_user.perfil == 'administrador'` → 403 (pattern de `admin_learning.py`).

**Flag**: `USE_SUBAGENT_DEBUG_ENDPOINT=true` (default).
**Env var rollback**: `AGENT_SUBAGENT_DEBUG_ENDPOINT=false`.

**Arquivos novos**:
- `app/agente/routes/admin_subagents.py` (~180 LOC)

**Arquivos modificados**:
- `app/agente/routes/__init__.py` (registrar sub-blueprint)
- `app/agente/config/feature_flags.py` (+1 flag)

---

#### Feature #3: Cost tracking granular por subagente

**Objetivo**: Dashboard de custo por subagente ao longo do tempo, identificar subagentes caros.

**Captura em `hooks.py:SubagentStop`**:

O hook ja captura `total_cost_usd` (hoje passa `input_tokens=0, output_tokens=0` ao `cost_tracker`). Extensao:

1. Ler `agent_transcript_path` do `hook_input` (ja feito).
2. Parsear JSONL completo (nao so ultima linha) e somar `usage` de AssistantMessages → `input_tokens`, `output_tokens`, `cache_read_tokens`.
3. Persistir em `AgentSession.data['subagent_costs']`.

**Schema JSONB** (versionado):

```json
{
  "version": 1,
  "entries": [
    {
      "agent_id": "uuid-v4",
      "agent_type": "analista-carteira",
      "cost_usd": 0.01234,
      "input_tokens": 1200,
      "output_tokens": 400,
      "cache_read_tokens": 800,
      "duration_ms": 8234,
      "num_turns": 4,
      "stop_reason": "end_turn",
      "started_at": "2026-04-16T14:22:11",
      "ended_at": "2026-04-16T14:22:19"
    }
  ]
}
```

**Indice GIN** (migration DDL):

```sql
CREATE INDEX IF NOT EXISTS idx_agent_sessions_subagent_costs
ON agent_sessions USING GIN ((data -> 'subagent_costs'));
```

**Query helper em `models.py`**:

```python
@classmethod
def top_subagents_by_cost(cls, days: int = 30, limit: int = 10) -> list[dict]:
    """
    SELECT agent_type, SUM(cost_usd) total_cost, COUNT(*) invocacoes
    FROM agent_sessions, jsonb_array_elements(data->'subagent_costs'->'entries') e
    WHERE created_at > now() - interval '{days} days'
    GROUP BY agent_type
    ORDER BY total_cost DESC LIMIT {limit}
    """
```

**Dashboard**:
- `services/insights_service.py` adiciona secao `_render_subagent_cost_section()` → card com top 5 + grafico simples de linha (custo acumulado/dia).
- Cache de agregacao: TTL 15 min (padrao do insights hoje).

**Flag**: `USE_SUBAGENT_COST_GRANULAR=true` (default).

**Arquivos novos**:
- `scripts/migrations/agent_session_subagent_costs_idx.py` + `.sql`

**Arquivos modificados**:
- `app/agente/sdk/hooks.py` (extensao do `_subagent_stop_hook`)
- `app/agente/models.py` (+1 classmethod)
- `app/agente/services/insights_service.py` (+1 secao)
- `app/agente/config/feature_flags.py` (+1 flag)

---

#### Feature #5: Memory mining cross-subagente

**Objetivo**: Pattern analyzer captura regras descobertas pelos especialistas, nao so pelo pai.

**Extensao em `pattern_analyzer.py:extrair_conhecimento_sessao()`**:

```python
def extrair_conhecimento_sessao(
    app,
    user_id: int,
    session_messages: list[dict],
    include_subagents: bool = True,     # NOVO — controlado por flag
    session_id: Optional[str] = None,   # NOVO — necessario para get_subagent_messages
) -> bool:
    ...
    if include_subagents and session_id:
        subagents = get_session_subagents_summary(session_id, include_pii=False)
        subagent_section = _format_subagent_findings_for_extraction(subagents)
        # anexa ao contexto Sonnet antes das msgs do pai
```

**Formato da injecao** (antes do prompt atual):

```
## Descobertas dos Especialistas (sessao)

### analista-carteira (4 tools, 8s)
- query_sql: 24 pedidos em aberto para Atacadao
- view_memories: regra "cliente X prefere pallet misturado"
- ...

### raio-x-pedido (2 tools, 3s)
- ...

## Conversa principal (pai)

[mensagens originais]
```

**Limite**: 2K chars por subagent (`max_tool_chars=500` no reader), cap total sessao mantido em 40K.

**Custo**: zero adicional — ja estamos rodando Sonnet pos-sessao (~$0.003/sessao). Apenas mais contexto no mesmo call.

**Flag**: `USE_SUBAGENT_MEMORY_MINING=true` (default).

**Arquivos modificados**:
- `app/agente/services/pattern_analyzer.py` (+param + formatter)
- `app/agente/routes/_helpers.py` (caller passa `session_id`)
- `app/agente/config/feature_flags.py` (+1 flag)

### 4.2 Grupo B — UI #6 Linha inline expansivel

#### Fluxo SSE completo

```
┌─ Frontend ──────────────────────────────────────────────────────┐
│                                                                  │
│  case 'task_started'     → insere linha colapsada (dot pulsante) │
│  case 'task_progress'    → atualiza "N tools · Ys"               │
│  case 'subagent_summary' → dot verde, mostra resumo final        │
│  click expand            → fetch summary + lazy-render detalhes  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
          ▲
          │ SSE events (3-layer R8)
          │
┌─ Backend SDK ───────────────────────────────────────────────────┐
│                                                                  │
│  sdk/client.py          emite StreamEvent('subagent_summary')    │
│  routes/chat.py         _sse_event('subagent_summary', ...)      │
│  hooks.py:SubagentStop  dispara emissao (ja capturando cost)     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### Camada 1 — `sdk/client.py`

Criar metodo `emit_subagent_summary(agent_id, agent_type, summary_dict)` chamado pelo `_subagent_stop_hook`. O metodo constroi `StreamEvent(type='subagent_summary', data=...)` e o coloca diretamente na event_queue (respeitando ContextVar pattern, sem tocar em `permissions.py`). Evita parsing sintetico em `_parse_sdk_message`.

#### Camada 2 — `routes/chat.py`

```python
elif event.type == 'subagent_summary':
    data = event.data
    # Sanitiza PII se nao-admin
    if current_user.perfil != 'administrador':
        data = _sanitize_subagent_summary(data)
        data.pop('cost_usd', None)  # usuario nao-admin nao ve custo
    yield _sse_event('subagent_summary', data)
```

#### Camada 3 — `static/agente/js/chat.js`

```javascript
case 'subagent_summary':
    renderSubagentLine(data);  // helper novo
    break;
```

**Estados da linha**:

| Estado | Gatilho | Visual |
|--------|---------|--------|
| `running` | `task_started` recebido | linha colapsada, dot amarelo pulsante, "executando..." |
| `done` | `subagent_summary` recebido | dot verde, "concluido · N tools · Ys · $X.XXX" |
| `expanded` | click na linha | injeta detalhes via lazy-fetch (abaixo) |
| `validation_warning` | `subagent_validation` com score<70 | icone amarelo ⚠ ao lado do nome |

**Lazy-fetch de detalhes** (ao expandir):

- Usuario comum: `GET /agente/api/sessions/<id>/subagents/<aid>/summary` (rota nova, NAO admin) → retorna summary com PII mascarada e SEM custo. Responsavel por autorizar = so dono da sessao ve.
- Admin: usa o endpoint admin do #1.

**Ambas rotas retornam mesmo schema** — diferenca e apenas sanitizacao.

#### CSS — `static/agente/css/_subagent-inline.css`

Arquivo novo (via `@import` em `agent-theme.css`). Usa tokens existentes `--agent-*`:

```css
.subagent-inline {
  background: rgba(148, 163, 184, 0.08);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 6px;
  padding: 8px 12px;
  margin: 6px 0;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  color: var(--agent-text-secondary);
  font-size: 12px;
  transition: all 0.2s ease;
}
.subagent-inline:hover { background: rgba(148, 163, 184, 0.12); }
.subagent-inline .badge { /* ... */ }
.subagent-inline.running .dot { animation: pulse 1.5s infinite; background: var(--agent-warning); }
.subagent-inline.done .dot { background: var(--agent-success); }
.subagent-inline.expanded { flex-direction: column; align-items: stretch; }
/* ... demais estados ... */
```

**Dark/light**: tokens `--agent-*` ja adaptam automaticamente.

**Flag**: `USE_SUBAGENT_UI=true` (default). Fallback: se flag false, `chat.js` ignora `subagent_summary` e mantem comportamento atual (timeline lateral + typing indicator).

**Arquivos novos**:
- `app/static/agente/css/_subagent-inline.css`
- `app/agente/utils/pii_masker.py`
- `app/agente/routes/subagents.py` (rota publica user-facing para lazy-fetch)

**Arquivos modificados**:
- `app/agente/sdk/client.py` (+emit, +parse tipo novo)
- `app/agente/sdk/hooks.py` (dispara emissao)
- `app/agente/routes/chat.py` (SSE passthrough + sanitizacao)
- `app/agente/routes/__init__.py` (registrar blueprint subagents)
- `app/static/agente/js/chat.js` (+case, +renderSubagentLine)
- `app/static/agente/css/agent-theme.css` (+@import)
- `app/agente/templates/agente/chat.html` (container-alvo, se necessario)

### 4.3 Grupo C — #2 Aposentar `/tmp/subagent-findings/` (soft)

**Objetivo**: Tornar SDK transcript a fonte canonica de findings. Manter `/tmp/` como fallback escrito para seguranca.

**Mudanca 1 — Ordem de leitura**: Parent agent le `get_subagent_findings(session_id)` ANTES de `/tmp/subagent-findings/`.

**Novo helper em `subagent_reader.py`**:

```python
def get_subagent_findings(session_id: str, agent_type: str) -> Optional[str]:
    """
    Retorna findings_text do subagent mais recente do agent_type.
    Se nao encontrado (SDK falha, JSONL corrompido), retorna None — caller usa /tmp/ como fallback.
    """
```

**Mudanca 2 — Documentacao**:
- `.claude/references/SUBAGENT_RELIABILITY.md`: adicionar secao "Ordem de leitura" e notar que SDK transcript e fonte primaria.
- `CLAUDE.md` raiz: atualizar menção ao protocolo.

**Mudanca 3 — Subagents permanecem inalterados**:
- Os 6 agents de acao (analista-carteira, gestor-ssw, dev-odoo, especialista-odoo, auditor-financeiro, gestor-recebimento) continuam instruidos a escrever em `/tmp/subagent-findings/` — rede de seguranca.

**Flag**: sem flag dedicada. Mudanca e aditiva (nova fonte preferida, fallback mantido).

**Arquivos modificados**:
- `.claude/references/SUBAGENT_RELIABILITY.md`
- `CLAUDE.md` (raiz)
- Consumidores do pattern (onde o parent le findings — a mapear na fase de writing-plans)

### 4.4 Grupo D — #4 Validacao anti-alucinacao (async)

#### Fluxo

```
SubagentStop hook
  ├─> persist cost granular (sync)                          ← #3
  └─> enqueue validation job (async, queue=agent_validation) ← #4
         │
         ▼
     worker_render.py | worker_atacadao.py
         │
         ▼
     app/agente/workers/subagent_validator.py
         │
         ▼
     Haiku 4.5: compara tool_result vs assistant response
         │
         ▼
     AgentSession.data['subagent_validations'] += entry
         │
     [score < threshold]
         │
         ▼
     SSE event 'subagent_validation' -> frontend renderiza icone ⚠
```

#### Worker e queue

**NAO cria worker novo**. Ajuste em ambos workers existentes:

```python
# worker_render.py  (linha atual: default='atacadao,odoo_lancamento,impostos,recebimento,high,default')
default='atacadao,odoo_lancamento,impostos,recebimento,agent_validation,high,default'

# worker_atacadao.py  (linha atual: default='atacadao,high,default')
default='atacadao,agent_validation,high,default'
```

#### Job — `app/agente/workers/subagent_validator.py`

```python
def validate_subagent_output(session_id: str, agent_id: str, threshold: int = 70):
    """
    Job RQ enfileirado em 'agent_validation'.
    1. Carrega summary via subagent_reader.get_subagent_summary()
    2. Extrai ultima tool_result + findings_text (resposta final do subagent)
    3. Chama Haiku 4.5 com prompt estruturado
    4. Parseia output JSON {score, reason, flagged_claims}
    5. Persiste em AgentSession.data['subagent_validations']
    6. Se score < threshold, emite SSE event 'subagent_validation' via event_queue
    """
```

**Prompt Haiku** (via `claude-api` skill, com prompt caching):

```
Sistema:
Voce compara o que um especialista fez (tool_result) vs o que ele reportou (resposta final).
Retorne JSON: {"score": int 0-100, "reason": str curta, "flagged_claims": list[str]}

Score alto (>= 80): resposta e consistente com os dados retornados pelas tools.
Score medio (50-79): pequenas inconsistencias ou omissoes.
Score baixo (<50): resposta contradiz ou inventa informacoes.

Usuario:
## Tools chamadas:
{tool_calls_resumidos}

## Resultado ultima tool:
{ultima_tool_result}

## Resposta final do subagent:
{findings_text}
```

**Modelo**: `claude-haiku-4-5-20251001` (~$0.0005/call).
**Latencia**: 200-400ms (nao impacta parent pois e async).

#### Persistencia

```json
AgentSession.data['subagent_validations'] = {
  "version": 1,
  "entries": [
    {
      "agent_id": "uuid",
      "agent_type": "analista-carteira",
      "score": 65,
      "reason": "Resposta menciona 30 pedidos mas tool retornou 24.",
      "flagged_claims": ["30 pedidos em aberto"],
      "validated_at": "2026-04-16T14:22:25"
    }
  ]
}
```

#### UX

- Frontend recebe SSE `subagent_validation` → adiciona icone amarelo ⚠ ao lado do nome do subagent na linha #6.
- Click expande: mostra `reason` + `flagged_claims`.
- **Nao bloqueia** resposta do parent — valida em background, usuario ve flag aparecer alguns segundos depois.

**Threshold env var**: `AGENT_SUBAGENT_VALIDATION_THRESHOLD=70` (configuravel sem redeploy).

**Flag**: `USE_SUBAGENT_VALIDATION=true` (default).

**Arquivos novos**:
- `app/agente/workers/subagent_validator.py` (~140 LOC)

**Arquivos modificados**:
- `app/agente/sdk/hooks.py` (enqueue no SubagentStop)
- `app/agente/sdk/client.py` (+StreamEvent tipo novo)
- `app/agente/routes/chat.py` (SSE passthrough)
- `app/static/agente/js/chat.js` (+case, atualiza linha existente com icone)
- `worker_render.py` (+queue no --queues default)
- `worker_atacadao.py` (+queue no --queues default)
- `app/agente/config/feature_flags.py` (+1 flag)

## 5. Feature Flags — Resumo

Todas com `default=True`, rollback via env var:

| Flag | Env var | Feature |
|------|---------|---------|
| `USE_SUBAGENT_DEBUG_ENDPOINT` | `AGENT_SUBAGENT_DEBUG_ENDPOINT` | #1 |
| `USE_SUBAGENT_COST_GRANULAR` | `AGENT_SUBAGENT_COST_GRANULAR` | #3 |
| `USE_SUBAGENT_MEMORY_MINING` | `AGENT_SUBAGENT_MEMORY_MINING` | #5 |
| `USE_SUBAGENT_UI` | `AGENT_SUBAGENT_UI` | #6 |
| `USE_SUBAGENT_VALIDATION` | `AGENT_SUBAGENT_VALIDATION` | #4 |
| — | `AGENT_SUBAGENT_VALIDATION_THRESHOLD` (default 70) | #4 threshold |
| — | `AGENT_SUBAGENT_UI_RAW` (default false) | #6 admin override para ver PII |

## 6. Plano de Fases

```
Fase 1 — Fundacao (paralelo, ~3-4 dias)
├─ subagent_reader.py (modulo base) + pii_masker.py
├─ #1 Admin endpoint (depende: reader)
└─ #3 Cost granular (depende: reader + hook + migration indice GIN)

Fase 2 — UI e Mining (paralelo, ~2-3 dias)
├─ #6 UI (depende: #1 endpoint)
└─ #5 Memory mining (depende: reader)

Fase 3 — Migracao documental (~1 dia)
└─ #2 ordem de leitura + docs (depende: reader)

Fase 4 — Validacao (~3 dias, isolado)
└─ #4 worker + job + queue adjust (depende: #1 + #3 para contexto, mas implementavel apos)

Total estimado: 10-11 dias de dev + testes + rollout monitorado.
```

## 7. Testing Strategy

### 7.1 Unit

- `subagent_reader.py`: mock `list_subagents`/`get_subagent_messages`, verifica parsing de SessionMessage → SubagentSummary.
- `pii_masker.py`: fixtures com CPF/CNPJ/email variados, edge cases (CPF inside JSON string, CNPJ in SQL, etc.).
- `subagent_validator.py`: mock Anthropic client, verifica parse de output + persistencia JSONB.

### 7.2 Integration

- Spawnar sessao de teste (helper ja existente no projeto), disparar subagent real (ex: `analista-carteira`), validar:
  - JSONL escrito em `~/.claude/projects/<proj>/<session>/subagents/`
  - `get_subagent_summary()` retorna dados consistentes
  - Cost persistido em `AgentSession.data['subagent_costs']`

### 7.3 E2E

- Playwright: abre `/agente/chat`, envia pergunta que dispara subagent, verifica:
  - Linha inline aparece com estado `running`
  - Apos alguns segundos, muda para `done` com resumo
  - Click expande, detalhes carregam
  - Admin ve custo; usuario nao-admin nao ve

### 7.4 Validacao manual no rollout

- Habilitar uma flag por vez em producao (start com `USE_SUBAGENT_DEBUG_ENDPOINT`).
- Monitorar Sentry + logs do Render por 24h apos cada flag.
- Validar metricas: latencia SSE, custo por sessao, error rate.

## 8. Rollback

| Feature | Rollback |
|---------|----------|
| #1 | `AGENT_SUBAGENT_DEBUG_ENDPOINT=false` (rota retorna 404) |
| #3 | `AGENT_SUBAGENT_COST_GRANULAR=false` (hook para de persistir; indice GIN fica mas e inert) |
| #5 | `AGENT_SUBAGENT_MEMORY_MINING=false` (pattern_analyzer ignora param) |
| #6 | `AGENT_SUBAGENT_UI=false` (backend para de emitir event; frontend ignora) |
| #4 | `AGENT_SUBAGENT_VALIDATION=false` (hook nao enfileira; queue existe mas vazia) |
| #2 | Reverter commit docs — subagents seguem escrevendo em `/tmp/` sem mudanca |

## 9. Risk Assessment

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| SDK 0.1.60 tem edge case em `get_subagent_messages` (retorno vazio, JSONL corrompido) | Media | Medio | Fallback para `/tmp/` + log estruturado; #2 nao remove `/tmp/` de vez |
| JSONB `subagent_costs` cresce muito em sessoes longas (30+ subagents) | Baixa | Baixo | Schema versionado permite migrar p/ tabela dedicada se necessario |
| Haiku 4.5 alucina score (false positive/negative) | Media | Medio | Threshold env var ajustavel; UX e warning, nao bloqueio |
| Queue `agent_validation` atrapalha outras filas | Baixa | Baixo | RQ processa em paralelo; priority nativa do queue list |
| CSS novo quebra timeline lateral existente | Baixa | Medio | Arquivo novo `_subagent-inline.css` isolado; nao toca `agent-theme.css` |
| PII mascara inadequadamente (falso positivo em texto legitimo) | Media | Baixo | Regex conservadora (apenas formatos brasileiros); admin sempre ve raw |
| Emit sintetico de `subagent_summary` via event_queue quebra R2 (thread-safety) | Baixa | Alto | Seguir ContextVar pattern; review obrigatorio em `permissions.py` |

## 10. Dependencias Externas

- `claude-agent-sdk==0.1.60` (ja instalado)
- `anthropic` SDK (ja instalado — #4)
- `rq` (ja instalado — #4)
- Nada novo a adicionar ao `requirements.txt`.

## 11. Checklist de Conformidade

- [x] Pipeline SSE 3-layer respeitado (#6, #4)
- [x] Thread-safety via ContextVar (permissions.py nao modificada)
- [x] Hierarquia de timeouts respeitada (validacao e async, nao bloqueia stream)
- [x] Timezone Brasil naive (datetimes sem tzinfo)
- [x] Design tokens (zero hex hardcoded em `_subagent-inline.css`)
- [x] Migrations: DDL + Python (apenas #3, indice GIN)
- [x] Workers existentes reaproveitados (#4)
- [x] Feature flags com rollback via env var
- [x] Admin/user permission split (#1, #6)
- [x] PII sanitization para user, raw para admin (#6)
- [x] `/tmp/` fallback mantido (#2)

## 12. Proximos Passos

1. Este spec e revisado e aprovado pelo usuario.
2. Invocar skill `superpowers:writing-plans` para gerar plano executavel (steps enumerados com checkpoints).
3. Executar via `superpowers:executing-plans` com approval gates por fase.

## Apendice A — Mapa de arquivos

### Arquivos novos

| Arquivo | Proposito | LOC estimada |
|---------|-----------|--------------|
| `app/agente/sdk/subagent_reader.py` | Fundacao — wrapper SDK + summary | ~200 |
| `app/agente/utils/pii_masker.py` | Mascaramento CPF/CNPJ/email | ~80 |
| `app/agente/routes/admin_subagents.py` | #1 endpoint admin | ~180 |
| `app/agente/routes/subagents.py` | #6 endpoint user-facing (lazy-fetch) | ~100 |
| `app/agente/workers/subagent_validator.py` | #4 job RQ validacao | ~140 |
| `app/static/agente/css/_subagent-inline.css` | #6 estilos linha | ~120 |
| `scripts/migrations/agent_session_subagent_costs_idx.py` | #3 indice GIN Python | ~40 |
| `scripts/migrations/agent_session_subagent_costs_idx.sql` | #3 indice GIN SQL | ~10 |

### Arquivos modificados

| Arquivo | Mudancas |
|---------|----------|
| `app/agente/sdk/hooks.py` | Extensao SubagentStop (tokens + enfileira validacao) |
| `app/agente/sdk/client.py` | +emit `subagent_summary` e `subagent_validation` |
| `app/agente/routes/chat.py` | +SSE passthrough dos 2 eventos novos |
| `app/agente/routes/__init__.py` | Registrar 2 blueprints novos |
| `app/agente/routes/_helpers.py` | Passa `session_id` para pattern_analyzer |
| `app/agente/services/pattern_analyzer.py` | +param `include_subagents` + formatter |
| `app/agente/services/insights_service.py` | +secao custo por subagent |
| `app/agente/models.py` | +classmethod `top_subagents_by_cost` |
| `app/agente/config/feature_flags.py` | +5 flags |
| `app/agente/CLAUDE.md` | +documentacao das features adotadas |
| `app/agente/templates/agente/chat.html` | Nao modificar (linhas sao injetadas dinamicamente por `chat.js` no container `#messages` existente) |
| `app/static/agente/js/chat.js` | +case `subagent_summary`, +case `subagent_validation`, +renderSubagentLine |
| `app/static/agente/css/agent-theme.css` | +@import `_subagent-inline.css` |
| `worker_render.py` | +queue `agent_validation` |
| `worker_atacadao.py` | +queue `agent_validation` |
| `.claude/references/SUBAGENT_RELIABILITY.md` | +secao "Ordem de leitura" |
| `CLAUDE.md` (raiz) | Atualizar referencia ao protocolo |

Total novos: 8 arquivos (~870 LOC).
Total modificados: 17 arquivos.

## Apendice B — Decisoes tomadas no brainstorming

| # | Decisao | Escolha final |
|---|---------|---------------|
| 1 | Ordem de implementacao | **B** (agrupamento por tipo de consumidor: A/B/C/D) |
| 2 | UI timing | **C** (hibrido progressivo: tempo real + expansao on-demand) |
| 3 | UI layout | **A** (inline na conversa, colapsada/expandida no mesmo lugar) |
| 4 | Feature flags | Uma por feature, `default=True`, env var rollback |
| 5 | Auth #1 | `@login_required` + inline `perfil=='administrador'` |
| 6 | UI visibility | Usuario ve blocos sanitizados sem custo; admin ve tudo raw |
| 7 | Memory mining | Reutilizar `extrair_conhecimento_sessao` com `include_subagents=True` |
| 8 | Persistencia cost | JSONB em `AgentSession.data` (sem tabela dedicada) + indice GIN |
| 9 | Escopo #2 | Manter `/tmp/` como fallback escrito (leitura preferencial via SDK) |
| 10 | Validacao execucao | Async via Redis Queue |
| 11 | Validacao threshold | Score numerico 0-100, flag se `< 70` (env var) |
| 12 | Validacao UX | Icone amarelo discreto, sem banner vermelho |
| 13 | Worker #4 | Reaproveitar `worker_render.py` + `worker_atacadao.py` (nova queue `agent_validation`) |
