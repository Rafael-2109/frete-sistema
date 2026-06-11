<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano de melhorias do agente Teams — identidade unificada, falante do turno, entrega proativa e extras
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-10
-->

# Teams Melhorias — Identidade, Falante do Turno, Entrega Proativa

> **Papel:** plano executável das melhorias do agente Teams aprovadas por Rafael em 2026-06-10
> (escopo completo A→D): identidade unificada Teams↔Web, identificação do falante em grupos,
> entrega proativa (fim do timeout de 5/10 min) e extras.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) ou
> superpowers:subagent-driven-development para implementar tarefa a tarefa. Checkboxes (`- [ ]`)
> marcam progresso.

## Indice

- [Contexto e regras](#contexto-e-regras)
- [Fatos verificados (fontes)](#fatos-verificados-fontes)
- [FASE A — Identidade unificada Teams↔Web](#fase-a--identidade-unificada-teamsweb)
- [FASE B — Falante do turno em grupos](#fase-b--falante-do-turno-em-grupos)
- [FASE C — Entrega garantida (proactive) + timeouts](#fase-c--entrega-garantida-proactive--timeouts)
- [FASE D — Extras aprovados](#fase-d--extras-aprovados)
- [FASE E — Entrega contínua no Teams (A+B)](#fase-e--entrega-contínua-no-teams-ab-aprovada-2026-06-11-próxima-sessão)
- [Pós-implementação (cada fase)](#pós-implementação-cada-fase)

## Contexto e regras

**Goal:** Resolver os 3 problemas do agente Teams (timeout 5/10 min, identidade fantasma por MD5
do nome, falante desconhecido em grupos) + 6 extras aprovados, com deploy da Azure Function.

**Architecture:** Backend Flask (`app/teams/`) + Azure Function bridge (`azure-functions/frete-bot/`,
ambos NESTE repo). 4 fases independentes em sequência: A (identidade AAD+email+código), B (falante
do turno via registry por sessão), C (proactive messaging via `continue_conversation` + heartbeat),
D (extras).

**Tech Stack:** Flask 3.1 / SQLAlchemy 2.0 / botbuilder-core 4.16 / Azure Functions Python v2 /
Claude Agent SDK 0.2.95.

**Worktree:** `.claude/worktrees/teams-melhorias` (branch `worktree-teams-melhorias`).
Baseline: 51 testes passando (`tests/teams/ + tests/agente/sdk/test_baseline_fastpath.py +
tests/agente/test_vinculacao_fastpath.py`).

### Regras de execução INVIOLÁVEIS

1. **Rodar testes da raiz do worktree** (hooks PAD quebram com `cd` para subdir) com
   `source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate` (venv da raiz).
2. **Migrations = DOIS artefatos**: `scripts/migrations/NOME.py` (create_app + before/after) +
   `scripts/migrations/NOME.sql` (idempotente, `IF NOT EXISTS`).
3. **Mudança em `hooks.py`/`client.py`/`permissions.py` DEVE ser testada no Teams E no web**
   (regra `app/agente/CLAUDE.md:232-234`).
4. **`sanitize_for_json()`** antes de atribuir dict a campo JSONB (conversation_reference).
5. **Timezone**: usar `agora_utc_naive()` (retorna Brasil naive — nome é legado).
6. Commits frequentes, sem `[skip render]`.
7. Toda tela nova DEVE ter link de acesso (menu `base.html` ou tela relacionada).

## Fatos verificados (fontes)

- `usuario_id` (AAD object ID) chega da function e é DESCARTADO: `app/teams/bot_routes.py:88`.
- Identidade Teams = MD5 do nome: `app/teams/services.py:124-126`.
- Polling da function: `POLL_MAX_ATTEMPTS=200 × 1.5s = 5 min` (`azure-functions/frete-bot/bot.py:62`);
  `functionTimeout: 00:10:00` (`host.json:21`).
- Split de respostas longas JÁ existe na function (`bot.py:1056 _send_split_response`, 3500 chars);
  backend trunca ANTES em 3800 (`app/teams/services.py:1031-1043`) — truncamento é o bug.
- Hooks com `user_name`/`user_id` em CLOSURE (`app/agente/sdk/hooks.py:156-158`); client do pool é
  reusado SEM reaplicar hooks (`app/agente/sdk/client_pool.py:321-331`) → identidade/memórias
  congeladas no falante que criou o client.
- `add_user_message(content)` não registra autor (`app/agente/models.py:179-199`).
- Fast-paths baseline/vinculação só existem no path SYNC `processar_mensagem_bot`
  (`app/teams/services.py:443-500`); path ATIVO é o ASYNC `process_teams_task_async` (1496+) — gap.
- `/bot/execute` (backend `bot_routes.py:402-440`) + `build_confirmation_card`/ramo `confirm`
  (function `bot.py:72-136,1694-1727`) são código morto: `requer_confirmacao` nunca é emitido
  pelo backend (grep confirma — só existe no módulo devolucao).
- Function app Azure: `frete-bot-func` (brazilsouth,
  `frete-bot-func-d4awggfge3awcqap.brazilsouth-01.azurewebsites.net` — `teams-manifest/manifest.json`).
  Tooling local OK: `func` 4.6 + `az` autenticado.
- Precedente de vínculo de canal: `Usuario.find_by_whatsapp_jid` (`app/auth/models.py:146`).
- Decisão Rafael: memórias em grupo = **do falante do turno**; vínculo garantido = **código de
  pareamento** (e-mail é só conveniência de 1ª linha).

---

## FASE A — Identidade unificada Teams↔Web

### Task A1: Migration identidade

**Files:**
- Create: `scripts/migrations/2026_06_10_teams_identidade.py`
- Create: `scripts/migrations/2026_06_10_teams_identidade.sql`

DDL (idempotente):
```sql
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS teams_user_id VARCHAR(64);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS teams_vinculo_origem VARCHAR(20);
CREATE UNIQUE INDEX IF NOT EXISTS uq_usuarios_teams_user_id
    ON usuarios (teams_user_id) WHERE teams_user_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS teams_vinculo_codigos (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES usuarios(id),
    codigo_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_teams_vinculo_codigos_hash ON teams_vinculo_codigos (codigo_hash);
```
`.py`: padrão dos migrations existentes (sys.path.insert + create_app + checagem before/after).
Rodar local: `python scripts/migrations/2026_06_10_teams_identidade.py` (autorizado sem pedir —
memória `feedback_migrations_local_autorizadas`).

- [x] DDL .sql + .py escritos e rodados localmente; colunas existem (verificar via psql/inspector)
- [x] Commit

### Task A2: Modelo Usuario + TeamsVinculoCodigo

**Files:**
- Modify: `app/auth/models.py` (campos + `find_by_teams_aad_id` + modelo `TeamsVinculoCodigo`)
- Test: `tests/teams/test_identidade_teams.py` (novo)

```python
# app/auth/models.py — campos no Usuario (junto de whatsapp_autorizado):
teams_user_id = db.Column(db.String(64), nullable=True, index=False)
teams_vinculo_origem = db.Column(db.String(20), nullable=True)  # 'codigo'|'email'|'admin'

@classmethod
def find_by_teams_aad_id(cls, aad_id):
    """Resolve AAD object ID do Teams para Usuario ativo (espelha find_by_whatsapp_jid)."""
    if not aad_id:
        return None
    return cls.query.filter_by(teams_user_id=str(aad_id), status='ativo').first()


class TeamsVinculoCodigo(db.Model):
    __tablename__ = 'teams_vinculo_codigos'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    codigo_hash = db.Column(db.String(64), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
```

Testes (red→green): `find_by_teams_aad_id` acha ativo / ignora inativo / None sem match.

- [x] Test red → implementação → green
- [x] Commit

### Task A3: Hierarquia de resolução em `_get_or_create_teams_user`

**Files:**
- Modify: `app/teams/services.py:98-159` (assinatura + hierarquia)
- Modify: `app/teams/bot_routes.py` (repassar `usuario_id`/`usuario_email` em
  `_handle_async_message`, `_handle_sync_message`, task queued e thread args)
- Modify: `app/teams/services.py:1496+` (`process_teams_task_async` aceita e repassa
  `usuario_aad_id`, `usuario_email`, `conversation_type`)
- Test: `tests/teams/test_identidade_teams.py`

Nova assinatura e hierarquia:
```python
def _get_or_create_teams_user(usuario, aad_id=None, email=None):
    # 1) Vínculo confirmado por AAD ID
    user = Usuario.find_by_teams_aad_id(aad_id)
    if user:
        return user.id
    # 2) Auto-match por e-mail corporativo (conveniência; grava vínculo origem='email')
    if email:
        user = Usuario.query.filter(
            func.lower(Usuario.email) == email.strip().lower(),
            Usuario.status == 'ativo',
        ).first()
        if user:
            if aad_id and not user.teams_user_id:
                user.teams_user_id = str(aad_id)
                user.teams_vinculo_origem = 'email'
                db.session.commit()
            return user.id
    # 3) Fallback legacy: fantasma por MD5 do nome (código atual inalterado)
    ...
```
NÃO criar fantasma se aad_id casa com fantasma já vinculado por nome — manter comportamento atual
do passo 3 intacto (zero regressão para quem já existe).

`bot_routes.bot_message`: extrair `usuario_email = str(dados.get("usuario_email", "")).strip()`
e repassar tudo. `TeamsTask` NÃO ganha colunas novas — propagação via args da thread.

- [x] Tests red (aad match / email match grava vínculo / fallback nome) → green
- [x] Baseline `tests/teams/` verde
- [x] Commit

### Task A4: Function envia e-mail + conversation_type + aad

**Files:**
- Modify: `azure-functions/frete-bot/bot.py:1529-1583` (`on_message_activity`) e
  `:1814-1850` (path análogo em `_handle_card_response`/ask_user_answer)

```python
from botbuilder.core.teams import TeamsInfo

# Em on_message_activity, após extrair user_id:
user_email = ""
try:
    member = await TeamsInfo.get_member(turn_context, turn_context.activity.from_property.id)
    user_email = member.email or member.user_principal_name or ""
except Exception as e:
    logger.warning(f"[BOT] TeamsInfo.get_member falhou (segue sem email): {e}")

conversation_type = (
    turn_context.activity.conversation.conversation_type or "personal"
    if turn_context.activity.conversation else "personal"
)
# payload ganha: "usuario_email": user_email, "conversation_type": conversation_type
```
`TeamsInfo` vem de `botbuilder-core` (já em requirements). Falha de Graph NUNCA bloqueia a
mensagem (try/except + log).

- [x] Código + revisão manual (function não tem suite pytest; validação real no deploy Fase C)
- [x] Commit

### Task A5: Fast-paths no path ASYNC + fast-path `vincular CODIGO`

**Files:**
- Create: `app/agente/sdk/vincular_teams_fastpath.py`
- Modify: `app/teams/services.py` (`process_teams_task_async`: bloco fast-path ANTES de
  `_get_or_create_teams_session`, espelhando o bloco sync 443-500 — corrige gap dos fast-paths
  baseline/vinculação que hoje só rodam no path sync morto)
- Modify: `app/agente/config/feature_flags.py` (`AGENT_TEAMS_VINCULO_FASTPATH`, default true)
- Test: `tests/teams/test_vincular_fastpath.py` (novo)

```python
# vincular_teams_fastpath.py (padrão baseline_fastpath: should_intercept + executar)
_VINCULAR_RE = re.compile(r'^\s*vincular\s+([A-Za-z0-9]{6})\s*$', re.IGNORECASE)

def should_intercept_vincular(mensagem):
    return bool(mensagem and _VINCULAR_RE.match(str(mensagem).strip()))

def executar_vincular_fastpath(mensagem, aad_id, email, nome, fallback_user_id):
    """Valida código de pareamento e grava vínculo. NUNCA levanta; respostas de erro são
    determinísticas (código inválido/expirado) — não cai no LLM."""
    codigo = _VINCULAR_RE.match(mensagem.strip()).group(1).upper()
    h = hashlib.sha256(codigo.encode()).hexdigest()
    vc = TeamsVinculoCodigo.query.filter(
        TeamsVinculoCodigo.codigo_hash == h,
        TeamsVinculoCodigo.used_at.is_(None),
        TeamsVinculoCodigo.expires_at > agora_utc_naive(),
    ).first()
    if not vc:
        return {"ok": True, "resposta": "Código inválido ou expirado. Gere um novo no sistema web (menu do usuário → Vincular Teams) e tente de novo."}
    if not aad_id:
        return {"ok": True, "resposta": "Não consegui identificar sua conta do Teams. Tente novamente."}
    user = db.session.get(Usuario, vc.user_id)
    user.teams_user_id = str(aad_id)
    user.teams_vinculo_origem = 'codigo'
    vc.used_at = agora_utc_naive()
    db.session.commit()
    merge_resumo = _merge_usuario_fantasma(nome, user.id)  # best-effort, ver Task A7
    return {"ok": True, "resposta": f"Vinculado! Você agora é {user.nome} ({user.email}) no sistema. {merge_resumo}"}
```
Intercept no async: responder direto via TeamsTask (status completed) SEM criar AgentSession nem
chamar LLM. Tests: código válido vincula+marca used / expirado / já usado / regex não casa
"vincular o pedido 123 na nota" (palavra a mais → NÃO intercepta — proteger do fast-path
NF×PO existente!).

- [x] Tests red → green (incluir caso anti-colisão com vinculação NF×PO)
- [x] Bloco async com baseline+vinculação+vincular (ordem: vincular → vinculação NF×PO → baseline)
- [x] Commit

### Task A6: Tela web de vinculação

**Files:**
- Modify: `app/auth/routes.py` (rota `GET/POST /auth/vincular-teams`, `@login_required`)
- Create: `app/templates/auth/vincular_teams.html`
- Modify: `app/templates/base.html` (item no dropdown do usuário)
- Modify: tela admin de edição de usuário (`app/auth/routes.py` editar + template
  correspondente — exibir vínculo atual + botão desvincular)
- Test: `tests/teams/test_vincular_rota_web.py`

Rota: gera código `secrets.choice` 6 chars (A-Z0-9 sem O/0/I/1), salva
`sha256(codigo)` com TTL 10 min (invalida códigos anteriores não usados do mesmo user),
renderiza código + instrução ("No Teams, envie: vincular ABC123 para o bot Agente Logístico").
UI: ler `.claude/references/design/GUIA_COMPONENTES_UI.md` ANTES de escrever o template
(regra dev). Sem `<style>` inline.

- [x] Test red (rota exige login; POST gera código e invalida anterior) → green
- [x] Link no menu (base.html) verificado
- [x] Commit

### Task A7: Merge de usuários fantasma

**Files:**
- Create: `scripts/migrations/2026_06_10_merge_usuarios_teams.py` (data-fix, só Python)
- Create: helper `_merge_usuario_fantasma(nome, user_id_real)` em
  `app/teams/services.py` (usado pelo fast-path A5)
- Test: `tests/teams/test_merge_fantasma.py`

Estratégia: descobrir TODAS as FKs para `usuarios(id)` via `information_schema` e reapontar
fantasma→real com UPDATE genérico (cobre agent_sessions, agent_memories, agent_step,
agent_invocation_metrics, agent_session_costs, teams_tasks, etc. sem lista hardcoded):
```sql
SELECT tc.table_name, kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND ccu.table_name = 'usuarios' AND ccu.column_name = 'id';
```
Fantasma identificado por `email = 'teams_' || md5(nome_normalizado)[:12] || '@teams.nacomgoya.local'`.
Pós-merge: fantasma `status='bloqueado'`, `observacoes += 'MERGED → user {id} em {data}'`.
Script standalone: `--dry-run` default, `--confirmar` executa, `--user-fantasma-id X --user-real-id Y`
explícitos OU `--auto` (casa todos fantasmas com usuarios reais por teams_user_id já vinculado).
Cuidado: colisão UNIQUE (ex. tabela com UQ(user_id, chave)) → capturar IntegrityError por tabela,
logar e continuar (relatório final lista pendências).

- [x] Test red (FK discovery + reapontamento em tabelas sintéticas) → green
- [x] Dry-run local OK
- [x] Commit
- **PROD (após deploy)**: rodar com Rafael ciente (não é automático)

---

## FASE B — Falante do turno em grupos

### Task B1: Etiqueta de falante no prompt + autor no histórico

**Files:**
- Modify: `app/teams/services.py` (`_obter_resposta_agente_streaming` e `_obter_resposta_agente`:
  param `conversation_type`; quando != 'personal', `prompt_completo = contexto_teams +
  f"[Mensagem de: {usuario}]\n" + mensagem`)
- Modify: `app/agente/models.py:179` (`add_user_message(self, content, author=None)` —
  acrescenta `'author': author` ao dict quando fornecido)
- Modify: `app/teams/services.py` (call sites `add_user_message(mensagem, author=usuario)` no
  path Teams; fallback XML — 2 ocorrências `services.py:815-835` e `:1204-1223` — vira
  `<msg role="user" author="...">` quando author presente)
- Test: `tests/teams/test_falante_turno.py`

Web NÃO muda (author=None → dict idêntico ao atual; testes existentes garantem).

- [x] Tests red (grupo prefixa; personal não prefixa; author persistido; fallback XML com autor) → green
- [x] Commit

### Task B2: Corrigir closure congelada dos hooks (registry por sessão)

**Files:**
- Create: `app/agente/sdk/turn_context_registry.py`
- Modify: `app/agente/sdk/client.py` (`stream_response`/`get_response`: `set_turn_user(our_session_id,
  user_id, user_name)` no início; clear no finally)
- Modify: `app/agente/sdk/hooks.py` (`build_hooks` ganha `our_session_id=None`; no
  `_user_prompt_submit_hook`, resolver `uid, uname = get_turn_user(our_session_id) or
  (user_id, user_name)` e usar nas memórias + `<session_context>`)
- Modify: `app/agente/sdk/client.py:_build_options` (propagar `our_session_id` ao `build_hooks`)
- Test: `tests/agente/sdk/test_turn_context_registry.py`

```python
# turn_context_registry.py — registry module-level keyed por our_session_id.
# Motivo: hooks vivem em closure criada NO TURNO QUE CONECTOU o client do pool
# (client_pool reusa sem reaplicar hooks). ContextVar não cruza thread Flask →
# daemon thread do pool. Dict por sessão é o mesmo pattern do resume_state.
_registry: dict = {}
_lock = threading.Lock()

def set_turn_user(session_id, user_id, user_name):
    if not session_id: return
    with _lock: _registry[session_id] = (user_id, user_name)

def get_turn_user(session_id):
    if not session_id: return None
    with _lock: return _registry.get(session_id)

def clear_turn_user(session_id):
    if not session_id: return
    with _lock: _registry.pop(session_id, None)
```
Fallback closure preserva comportamento atual quando registry vazio (web 1:1 inalterado;
defense-in-depth). Decisão Rafael: memórias injetadas = do falante do turno.
**Testar no Teams E no web** (regra módulo agente). Rodar suites:
`tests/teams/ tests/agente/sdk/ tests/agente/routes/` antes do commit.

- [x] Tests red (set/get/clear; hook usa turno; fallback closure) → green
- [x] Suites teams+agente verdes
- [x] Commit

---

## FASE C — Entrega garantida (proactive) + timeouts

### Task C1: Migration teams_tasks

**Files:**
- Create: `scripts/migrations/2026_06_10_teams_proactive.py` + `.sql`

```sql
ALTER TABLE teams_tasks ADD COLUMN IF NOT EXISTS conversation_reference JSONB;
ALTER TABLE teams_tasks ADD COLUMN IF NOT EXISTS delivered_via VARCHAR(12);
```
Modelo `app/teams/models.py`: + `conversation_reference = db.Column(db.JSON)`,
`delivered_via = db.Column(db.String(12))`.

- [x] Migration rodada local; modelo atualizado; commit

### Task C2: Function envia conversation_reference + mensagem fim-de-polling

**Files:**
- Modify: `azure-functions/frete-bot/bot.py` (`on_message_activity`: payload ganha
  `"conversation_reference": TurnContext.get_conversation_reference(turn_context.activity).serialize()`;
  fim do polling `bot.py:1474-1494` troca "Tempo limite excedido..." por
  "Ainda estou trabalhando nisso — te aviso aqui assim que terminar.")
- Modify: `app/teams/bot_routes.py` (`_handle_async_message`: salvar
  `task.conversation_reference = sanitize_for_json(dados.get("conversation_reference"))`)

`serialize()` é o método msrest do Model (dict JSON-safe). Tratar None (payload antigo durante
janela de deploy: backend tolera ausência).

- [x] Backend test: task persiste reference (tests/teams/test_proactive.py) → green
- [x] Commit

### Task C3: Claim atômico de entrega + endpoint /api/notify + caller backend

**Files:**
- Create: `app/teams/proactive.py`
- Modify: `app/teams/bot_routes.py` (`bot_task_status`: claim 'polling' ao retornar status final)
- Modify: `app/teams/services.py` (`process_teams_task_async`: após commit final de
  completed/error, se `elapsed > 270s` → `notify_function_delivery(task_id)`)
- Modify: `azure-functions/frete-bot/function_app.py` (rota `POST /api/notify`)
- Modify: `azure-functions/frete-bot/bot.py` (handler `deliver_proactive(payload)`)
- Modify: `app/agente/config/feature_flags.py` (`TEAMS_FUNCTION_URL`, `TEAMS_PROACTIVE_DELIVERY`
  default true)
- Test: `tests/teams/test_proactive.py`

Claim (anti-duplicata polling × proactive), nos DOIS lados:
```python
# bot_routes.bot_task_status — antes de retornar completed/error:
claimed = db.session.execute(sql_text(
    "UPDATE teams_tasks SET delivered_via='polling' "
    "WHERE id=:id AND delivered_via IS NULL"), {'id': task_id}).rowcount
db.session.commit()
if not claimed and task.delivered_via == 'proactive':
    return jsonify({"status": "already_delivered"})
```
```python
# proactive.py — notify_function_delivery(task_id):
# 1) claim: UPDATE ... SET delivered_via='proactive' WHERE id=:id AND delivered_via IS NULL
# 2) se ganhou: POST {TEAMS_FUNCTION_URL}/api/notify, X-API-Key=TEAMS_BOT_API_KEY,
#    json={task_id, resposta, resposta_card, conversation_reference} (timeout 30s)
# 3) POST falhou → rollback do claim (SET delivered_via=NULL WHERE delivered_via='proactive')
#    para o polling (se vivo) ou retry futuro entregar. Best-effort: NUNCA quebra a thread.
```
```python
# function_app.py — @app.route(route="api/notify", methods=["POST"], auth_level=ANONYMOUS)
# valida X-API-Key == BACKEND_API_KEY (mesma chave da ponte, direção inversa);
# bot.py: ref = ConversationReference().deserialize(payload["conversation_reference"])
# await BOT_APP.adapter.continue_conversation(ref,
#     lambda tc: _deliver(tc, payload), bot_id=MICROSOFT_APP_ID)
# _deliver: reusa _send_split_response + render_resposta_card (mesmo formato do polling).
```
Function side: polling que recebe `already_delivered` encerra silenciosamente (return).

- [x] Tests red (claim único; rollback de claim em falha de POST; notify só se elapsed>270s) → green
- [x] Commit

### Task C4: Heartbeat + thresholds

**Files:**
- Modify: `app/teams/services.py` (`_stream_with_flush`: `asyncio.create_task` de heartbeat 60s →
  raw SQL `UPDATE teams_tasks SET updated_at=:now WHERE id=:id AND status='processing'`, com
  app_context wrapper igual `_safe_flush`; cancelar no finally)
- Modify: `app/teams/services.py:2055-2056` (`cleanup_stale_teams_tasks`: processing 5→15 min;
  awaiting_user_input → threshold PRÓPRIO 30 min; queued 10→15 min)
- Modify: `app/teams/services.py:1235` (`INACTIVITY_TIMEOUT` lê env
  `TEAMS_INACTIVITY_TIMEOUT`, default 300 — botão de rollback sem deploy)
- Modify: `app/teams/CLAUDE.md` (R6/R7/lifecycle: documentar novos thresholds)
- Test: `tests/teams/test_cleanup_thresholds.py`

- [x] Tests red (cleanup respeita 15/30/15; heartbeat renova updated_at; cancelamento limpo) → green
- [x] Commit

### Task C5: Deploy function + env Render + validação real

> **EXECUTADO 2026-06-10/11**: token Azure local revogado (troca de senha) → deploy via
> **zip deploy com publish profile** (Kudu `/api/zipdeploy?isAsync=true`, build remoto Oryx,
> exigiu habilitar "SCM Basic Auth Publishing" no portal + re-download do profile — o 1o
> download veio com credenciais `REDACTED`). Env no Render foi ELIMINADA: default da
> `TEAMS_FUNCTION_URL` no código (`proactive.py`, env sobrepõe).

- [x] Deploy da function (zip deploy via publish profile; Oryx build success)
- [x] ~~Env TEAMS_FUNCTION_URL no Render~~ — default no código (commit c400a0ec6)
- [ ] Smoke FUNCIONAL no Teams: (1) pergunta rápida (polling entrega); (2) tarefa longa >5 min
  (function diz "te aviso" e resposta chega via proactive); (3) `vincular CODIGO`
- [x] Smoke técnico: /api/notify → 401 (rota nova no ar); /bot/health OK; migrations PROD
  aplicadas e verificadas; deploy Render live (dep-d8kug748, commit 05197c05f)

---

## FASE D — Extras aprovados

### Task D1: Remover truncamento de 3800 do backend

**Files:**
- Modify: `app/teams/services.py:1031-1043` (`_sanitizar_texto`: limite 3800→24000; manter corte
  defensivo em quebra de parágrafo só acima disso — Teams aceita ~28KB)
- Modify: `app/teams/services.py:183` (contexto: trocar "serão divididas automaticamente" por
  instrução real — function splita em blocos de 3500)
- Test: ajustar `tests/teams/` que cubram _sanitizar_texto (se existirem) + caso novo 10K chars

- [x] Tests green; commit

### Task D2: Fila concatena em vez de sobrescrever

**Files:**
- Modify: `app/teams/bot_routes.py:158-167` (`existing_queued.mensagem = f"{existing_queued.mensagem}\n\n{mensagem}"`,
  cap de 10000 chars — limite do endpoint)
- Modify: `app/teams/CLAUDE.md` R8
- Test: `tests/teams/test_fila_concatena.py`

- [x] Test red → green; commit

### Task D3: Rollback defensivo + remover /bot/execute e card morto

**Files:**
- Modify: `app/teams/bot_routes.py` (rollback try/except no início de `bot_task_status` e
  `bot_answer`; DELETAR rota `/bot/execute:402-440`)
- Modify: `azure-functions/frete-bot/bot.py` (DELETAR `build_confirmation_card:72-136`, ramo
  `confirm:1694-1727` e ramo `requer_confirmacao:1648-1658` — código morto confirmado)
- Modify: `app/teams/CLAUDE.md` (tabela de endpoints)
- Test: ajustar referência a /bot/execute se existir em testes

- [x] Suite teams verde; commit

### Task D4: Comando "nova conversa" (reset de contexto)

**Files:**
- Modify: `app/teams/services.py` (fast-path determinístico no bloco async da Task A5:
  regex `^\s*(nova|resetar|reiniciar)\s+(conversa|sess[aã]o)\s*$` i → expira sessão:
  `UPDATE agent_sessions SET updated_at = updated_at - interval '1 day' WHERE session_id=:sid`
  na sessão ativa da conversa → responde "Contexto reiniciado — próxima mensagem começa do zero.")
  Interceptar ANTES de `_get_or_create_teams_session` (senão a própria msg renova o TTL).
- Test: `tests/teams/test_reset_conversa.py`

- [x] Test red → green; commit

### Task D5 (PR separado): Upload de arquivos no Teams

**Files (investigar antes — passo 0 obrigatório):**
- Passo 0: mapear como o canal WEB processa upload (rota de upload do agente, storage S3,
  como o path chega ao agente/skill lendo-arquivos) — `app/agente/routes.py` +
  `.claude/references/S3_STORAGE.md`. SÓ depois desenhar o espelho Teams.
- Modify: `azure-functions/frete-bot/bot.py` (activity.attachments → download bytes →
  POST `/api/teams/bot/upload` multipart)
- Create: endpoint `bot_upload` em `app/teams/bot_routes.py` (S3 + injeção de referência no
  prompt da mensagem associada)
- Test: `tests/teams/test_upload.py`

- [ ] Investigação documentada no PR; implementação espelhando o web; testes; commit

---

## FASE E — Entrega contínua no Teams (A+B, aprovada 2026-06-11, PRÓXIMA SESSÃO)

> Decisão Rafael 2026-06-11: expectativa é "envios a qualquer momento", não
> "streaming até 5 min e depois só no final". Aprovado A+B completo em sessão nova.
> Contexto de validação: teste real de 11 min OK (task 295a6d7f, delivered_via=
> proactive 22:21:03, confirmação visual). Memória: teams_melhorias_2026_06_10.

### Task E1 (A): esticar o streaming em tempo real de 5 → ~8,5 min

**Files:**
- Modify: `azure-functions/frete-bot/bot.py` (`POLL_MAX_ATTEMPTS` default 200 → 340;
  340 × 1.5s = 510s = 8,5 min; teto da execução é functionTimeout=10min — host.json —
  sobra ~1,5 min de margem p/ processamento)
- Verificar: comentário no bot.py sobre update_activity falhar em msgs >2-3 min é
  EMPIRICAMENTE falso para o progressive update (teste de hoje atualizou a mesma msg
  por 6 min) — manter o update in-place até o fim do polling.

### Task E2 (B): blocos proativos após o fim do polling

**Design:**
- Migration: `teams_tasks.proactive_partial_chars INT NOT NULL DEFAULT 0` (offset de
  chars já entregues via blocos) — DDL .sql + .py (regra dos 2 artefatos).
- Backend (`app/teams/services.py`): no loop do heartbeat (`_heartbeat_loop`, já roda a
  cada 60s dentro de `_stream_with_timeout`), quando `elapsed > janela_polling` E houver
  delta de texto (full_text além do offset, > ~200 chars), POST `/api/notify` com payload
  `{tipo: 'partial', task_id, texto_delta, conversation_reference}` e persistir offset.
  SEM claim (claim `delivered_via` é exclusivo da entrega FINAL).
- Entrega final (`app/teams/proactive.py:notify_function_delivery`): enviar apenas
  `task.resposta[proactive_partial_chars:]` (delta restante) — evita repetir o que os
  blocos já entregaram. Offset=0 → comportamento atual (resposta completa).
- Function (`function_app.py` + `bot.py:deliver_proactive`): aceitar `tipo='partial'`
  (posta delta como mensagem nova, sem card) vs final (atual). Cada bloco proativo é
  MENSAGEM NOVA no chat (limitação do canal: proactive não edita mensagem existente).
- Gotchas: janela_polling acompanha E1 (constante `POLLING_WINDOW_SECONDS` em
  `proactive.py`, ajustar 270 → ~520); claim/rollback da final intocado; dedup garantido
  persistindo o offset ANTES do POST do bloco (se POST falha, NÃO avançar offset —
  inverter: só avançar offset APÓS POST 200, aceitando reenvio raro a duplicar bloco
  em vez de perder texto).
- Tests: `tests/teams/test_proactive.py` (final envia delta por offset; partial não
  clama; offset não avança em falha de POST).

### Task E3: deploy coordenado (mesma ordem da C5)

1. Backend: merge → main → push (auto-deploy Render) + migration PROD (.sql idempotente).
2. Function: zip deploy via publish profile (fluxo VALIDADO na C5 — token az local
   revogado; pedir ao Rafael o `.PublishSettings` se o de
   `/mnt/c/Users/rafael.nascimento/Downloads/frete-bot-func (1).PublishSettings` não
   estiver disponível; requer "SCM Basic Auth Publishing" ON): montar zip respeitando
   `.funcignore` + POST Kudu `/api/zipdeploy?isAsync=true` + poll
   `/api/deployments/latest` (Oryx build remoto já habilitado).
3. Smoke real: tarefa ~12 min — tempo real até 8,5 min + blocos proativos depois +
   entrega final só do delta restante.

- [x] E1 implementada (default 340) — redeploy junto da E3
- [x] E2: migration (2026_06_11_teams_proactive_partial) + backend (blocos no heartbeat
  via executor + offset CAS pós-POST-200) + function (tipo partial) + tests (11 novos,
  19 total em test_proactive.py)
- [x] E3: deploy coordenado EXECUTADO 2026-06-11 ~02:25 UTC — migration PROD via psql →
  backend `dep-d8l1kluk1jcs73e4qr2g` live 02:22 → function deployment `47c81456` 02:24
  (zip deploy publish profile); smoke técnico OK (/bot/health 200; /api/notify 401 sem
  key; tipo=partial com key → 200 = código novo confirmado)
- [ ] Smoke real >10 min com Rafael: tempo real até 8,5 min + blocos depois + final sem repetição
- [x] Atualizar `app/teams/CLAUDE.md` (lifecycle/flags/gotcha "Entrega continua") + esta seção

---

## Pós-implementação (cada fase)

1. Self-audit: checklist da fase vs arquivos tocados; imports; rotas registradas; links de menu.
2. Suites: `tests/teams/ tests/agente/sdk/ tests/agente/routes/` + baseline 51 originais.
3. Atualizar `app/teams/CLAUDE.md` (flags novas, lifecycle, endpoints, gotchas alterados).
4. Push + PR por fase (ou PR único com commits por fase — decidir no fechamento com Rafael).
5. PROD: migrations via Render Shell (.sql) ANTES do deploy de código; env vars novas;
   merge de fantasmas (A7) rodado com Rafael ciente; deploy function (C5) coordenado com
   deploy backend (janela de compat: backend tolera payload sem campos novos).
