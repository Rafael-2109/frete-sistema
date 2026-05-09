# WhatsApp Bot — Guia de Desenvolvimento

**LOC**: ~875 | **Arquivos**: 5 (Python) + plugin TS externo | **Atualizado**: 09/05/2026

Canal WhatsApp via OpenClaw + Baileys (NAO oficial Cloud API). Plugin externo
`nacom-bridge` (em `~/.openclaw/plugins/`) faz roteamento deterministico e
posta inbound aqui. Cerebro fica TODO no Agent SDK Nacom.

> **Memoria base**: `memory/openclaw_whatsapp_integration.md` — ground truth
> sobre OpenClaw + caminhos locais para Pyright/Pylance navegar.

---

## Estrutura

```
app/whatsapp/
├── __init__.py        # Blueprint /api/whatsapp
├── models.py          # WhatsAppTask (lifecycle async)
├── decorators.py      # require_plugin_token (Bearer)
├── bot_routes.py      # POST /inbound, GET /health
├── services.py        # process_whatsapp_task_async + send via gateway
└── CLAUDE.md          # Este arquivo
```

Migration: `scripts/migrations/2026_05_09_whatsapp_module.{py,sql}`

---

## Arquitetura — "Caminho D" (gateway puro)

```
WhatsApp ─┬─▶ OpenClaw Baileys (~/.openclaw/)
           │
           ▼
[Plugin nacom-bridge — inbound_claim]
   - Decisao deterministica (allowlist Nacom)
   - Synthetic reply: "👀 Consultando..."
   - POST http://127.0.0.1:5000/api/whatsapp/inbound
       Authorization: Bearer <OPENCLAW_PLUGIN_TOKEN>
       X-OpenClaw-Sender, X-OpenClaw-Conversation, X-OpenClaw-IsGroup, ...
       body: {text: "..."}
           ▼
   bot_routes.inbound() ─▶ require_plugin_token
                       ─▶ Usuario.find_by_whatsapp_jid (banco, multi-formato)
                       ─▶ Cria WhatsAppTask, dispara Thread daemon=False
                       ─▶ retorna 202 imediato
           ▼
   services.process_whatsapp_task_async (background, mesma thread Flask)
     1. status=processing
     2. _get_or_create_whatsapp_session (TTL 4h por peer)
     3. Set ContextVars MCP (memory, session, sql)
     4. Agent SDK call (TEAMS_DEFAULT_MODEL, timeout 240s)
     5. Salva mensagens na sessao
     6. _send_whatsapp_reply via gateway loopback:18789
     7. status=completed/error, cleanup
```

---

## Regras Criticas (espelhadas do Teams)

### R1: Thread non-daemon — `daemon=False` OBRIGATORIO
`process_whatsapp_task_async` roda em `Thread(daemon=False)`. Garante
conclusao durante reciclagem gunicorn. Alterar para `daemon=True` = task
morre no meio, resposta perdida.
— FONTE: `bot_routes.py:130-138`

### R2: Commit com retry — SEMPRE usar `_commit_with_retry()`
Render PostgreSQL derruba SSL apos 30-40s idle. `db.session.commit()` direto
falha com `OperationalError`. `_commit_with_retry` retorna False em SSL drop;
caller DEVE re-fetch + re-apply antes de novo commit.
— FONTE: `services.py:35-58`

### R3: Re-fetch apos task perdida
Apos commits intermediarios, `task` ORM objeto pode estar stale/expired.
SEMPRE `db.session.get(WhatsAppTask, task_id)` antes de mutar atributos
finais (status=completed).
— FONTE: `services.py:340-343`

### R4: ContextVars MCP — set ANTES, clear no finally
`memory_mcp_tool`, `session_search_tool`, `text_to_sql_tool` usam ContextVar
isolado por thread. Sem set: `RuntimeError("user_id nao definido")`.
Sem clear: vazamento cross-request.
— FONTE: `services.py:_set_mcp_context_vars`, `_clear_mcp_context_vars`

### R5: Cleanup obrigatorio no `finally`
Thread DEVE chamar: `cleanup_session_context()` + `cleanup_teams_task_context()`
+ `_clear_mcp_context_vars()` + `db.session.remove()`. Esquecer = ContextVars
poluidas → proxima request ve session/task da anterior.
— FONTE: `services.py:402-422`

### R6: Sender identity vem do PLUGIN, NUNCA do agente
O header `X-OpenClaw-Sender` e injetado pelo plugin (codigo TS controlado).
NUNCA aceitar sender vindo de campo do body — agente poderia alucinar.
Resolucao `Usuario.find_by_whatsapp_jid` filtra `whatsapp_autorizado=True`
+ `status='ativo'` (defesa em profundidade).
— FONTE: `bot_routes.py:82-94`

### R7: Plugin Fail-Open compensado
Hook `inbound_claim` no OpenClaw SDK falha-aberto (timeout/exceção → cai
pro agente embedded). Plugin DEVE try/catch tudo e retornar
`{handled:true, reply:{text:"❌"}}` em qualquer erro. Side-effect: Flask
sempre recebe POST mesmo que sender_token esteja errado — tratar como
log warning, nao panic.

### R8: WhatsApp ≠ Teams — formatacao limitada
- SEM tabelas markdown (`| col |`)
- SEM headers (`##`)
- SEM code blocks (` ``` `)
- PERMITIDO: `*bold*`, `_italic_`, `~strike~`, `- lista`, emojis
- OpenClaw chunka >4096 chars automaticamente (NAO chunkar manualmente)
— FONTE: `services.py:_get_whatsapp_context`

---

## Modelo WhatsAppTask

> Campos: ver `models.py` ou query `\d whatsapp_tasks` no Postgres.

**Lifecycle**:
```
pending → processing → completed | error | timeout | awaiting_user_input
```

| Coluna | Origem | Uso |
|--------|--------|-----|
| `peer_jid` | `X-OpenClaw-Sender` | E.164 DM ou JID Baileys grupo |
| `conversation_jid` | `X-OpenClaw-Conversation` | DM=peer, grupo=`...@g.us` |
| `is_group` | `X-OpenClaw-IsGroup` | Distingue rendering/contexto |
| `user_id` | `Usuario.find_by_whatsapp_jid(peer)` | FK Usuario Nacom |
| `openclaw_message_id` | `X-OpenClaw-MessageId` | Deduplicacao futura |

---

## Endpoints

| Endpoint | Metodo | Auth | Funcao |
|----------|--------|------|--------|
| `/api/whatsapp/inbound` | POST | Bearer plugin | Recebe inbound, cria task async, retorna 202 |
| `/api/whatsapp/health` | GET | — | Status threads ativas + tokens configurados |

Futuro Fase 6:
- `/api/whatsapp/answer` — AskUserQuestion via numeracao no texto ou polls
- `/api/whatsapp/status/<task_id>` — polling (nao usado hoje, plugin e fire-and-forget)

---

## Configuracao (variaveis de ambiente)

```bash
# Token Bearer que o plugin OpenClaw envia em Authorization
OPENCLAW_PLUGIN_TOKEN=<gerado-aleatorio-64-chars>

# Token admin do gateway OpenClaw (para enviar respostas)
# Vem de: cat ~/.openclaw/openclaw.json | jq -r .gateway.auth.token
OPENCLAW_GATEWAY_TOKEN=<token-admin-do-gateway>

# Opcional: URL do gateway (default: http://127.0.0.1:18789)
OPENCLAW_GATEWAY_URL=http://127.0.0.1:18789

# Opcional: kill switch
OPENCLAW_NOTIFY_ENABLED=true
```

Para gerar `OPENCLAW_PLUGIN_TOKEN`:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

O **mesmo valor** deve ser configurado no plugin `nacom-bridge` (em
`~/.openclaw/openclaw.json` -> `plugins.entries.nacom-bridge.config.fluxToken`
ou similar — formato confirmado no plugin).

---

## Pontos NAO implementados (Fase 6)

- **AskUserQuestion**: agente nao pode perguntar e esperar resposta
  (precisa parsing de "1", "2", "3" ou polls WhatsApp)
- **Progressive streaming**: usuario recebe so resposta final
  (sem "🔍 consultando...", "📊 analisando...")
- **Anexos inbound**: imagens/audios/documentos vem em metadata mas nao
  sao processados (ex: OCR, transcricao)
- **Retry loop**: uma tentativa, se falhar e erro
- **Smart model routing**: usa TEAMS_DEFAULT_MODEL fixo
- **Post-session processing**: nao roda summarization/extracao
- **Polls/reactions outbound**: helper so manda texto

---

## Troubleshooting

### Plugin envia mas Flask rejeita 403 sender_not_authorized
1. Verifique `usuarios.whatsapp_autorizado=True` para o telefone
2. `Usuario.normalize_whatsapp_identifier(jid)` deve retornar variantes que
   batem com `usuarios.telefone` (ver tests/test_whatsapp_normalize.py)
3. Telefone no banco pode estar em formato BR (sem 55) — funcao trata,
   mas confirme com `SELECT telefone FROM usuarios WHERE id=N`

### Resposta nao chega no WhatsApp
1. `GET /api/whatsapp/health` — verifica `gateway_configured: true`
2. `OPENCLAW_GATEWAY_TOKEN` correto? `cat ~/.openclaw/openclaw.json | jq .gateway.auth.token`
3. Gateway OpenClaw vivo? `curl http://127.0.0.1:18789/healthz`
4. Logs Flask: `tail -f /var/log/flask.log | grep WHATSAPP`

### Task fica em "processing" infinitamente
- `cleanup_stale_whatsapp_tasks()` roda lazy a cada `/inbound` — mata > 5min
- Manual: `UPDATE whatsapp_tasks SET status='timeout' WHERE id='...'`

### Plugin nao consegue rodar inbound_claim
- `openclaw plugins inspect nacom-bridge --runtime` (verifica se carregou)
- `openclaw gateway restart` apos mudar plugin (nao tem hot-reload)

---

## Interdependencias

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app.utils.whatsapp_notify` | `send_whatsapp` (gateway HTTP) | Lib helper, sem app context |
| `app.auth.models.Usuario` | `find_by_whatsapp_jid` | Multi-formato BR/E.164 |
| `app.agente.sdk` | `get_client`, `submit_coroutine` | Mesma SDK do Teams |
| `app.agente.config.permissions` | ContextVar set/cleanup | Cross-thread — testar Teams se mudar |
| `app.agente.tools.*_mcp_tool` | ContextVar de user_id | 3 ContextVars independentes |
| `app.agente.models.AgentSession` | Persistencia conversa | TTL 4h por peer |
| `app.teams.services._extrair_texto_resposta` | Parse de response SDK | Reuso direto, NAO duplicar |

> **REGRA**: Mudancas em `app/agente/sdk/client.py`, `permissions.py`, `pending_questions.py`
> DEVEM ser testadas no Teams bot E no WhatsApp bot.
