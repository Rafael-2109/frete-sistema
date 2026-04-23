# Chat in-app + alertas do sistema — Design Spec

**Data**: 2026-04-23
**Autor**: Rafael Nascimento (+ Claude Code via brainstorming)
**Status**: Aprovado para implementacao
**Modulo**: `app/chat/` (novo)
**Escopo**: Subsistema C + D do pedido original "notificacoes proativas + chat entre usuarios"

> Subsistema A (push Teams proativo) e B (gatilhos de eventos) ficam para fases futuras,
> apos a implementacao deste chat.

---

## 1. Objetivo e escopo

### 1.1 Objetivo

Dar ao sistema canal de comunicacao **usuario <-> usuario** e **sistema -> usuario**, com threads
operacionais ancoradas em entidades (pedido, NF, recebimento) e compartilhamento de contexto por
deep link. Tudo in-app no MVP; push externo (Teams/email) em fase posterior.

### 1.2 No escopo (MVP, "F1")

- DMs 1-a-1 e grupos; canais livres + threads automaticas por entidade.
- Regra de permissao cruzada por sistemas (NACOM / CARVIA / MOTOCHEFE / HORA).
- Entrega em tempo real via **SSE + Redis pub/sub** (reusa padrao do `app/agente/routes/chat.py`).
- Conteudo de mensagem: markdown basico + anexos S3 + mentions (`@usuario`) + reacoes + reply.
- UI integrada em `app/templates/base.html` (navbar) — 1 botao com 2 badges (`sistema` / `usuario`).
- Encaminhamento de mensagem (dentro do chat) **e** compartilhamento de tela (qualquer pagina
  do sistema vira link).
- Alertas de sistema em `chat_message` com `sender_type='system'`: unifica storage, separa
  apenas visualmente. Instrumentados 3 eventos no MVP:
  - Recebimento concluido (ok / erro)
  - DFE com novo bloqueio no Odoo (Fase 2 recebimento)
  - CTe divergente do cotado (Fretes)

### 1.3 Fora do escopo (adiado)

- **F2**: Push Teams pro-ativo. Pre-requisito: dedup Usuario Teams <-> Usuario sistema
  (hoje sao cadastros separados).
- **F3**: Preferencias por usuario (cada um escolhe: in-app / Teams / email / por tipo).
- **F4**: Remocao definitiva de `app/notificacoes/` (dead code em producao) — requer migracao
  dos 3 callers (`app/carteira/routes/alertas_api.py`, `app/carteira/alert_system.py`,
  `app/seguranca/services/scan_orchestrator.py`).
- Presenca online/offline (chat assincrono, presenca falsa cria expectativa ruim).
- App mobile / PWA dedicado.

---

## 2. Decisoes ancora (resumo executivo)

| # | Decisao | Escolha | Alternativas rejeitadas |
|---|---------|---------|-------------------------|
| 1 | Caso de uso | Hibrido: canais livres + threads por entidade | Apenas ancorado; apenas livre |
| 2 | Realtime | SSE + Redis pub/sub | WebSocket/Socket.IO (exigiria troca de worker gunicorn); polling (experiencia ruim) |
| 3 | Permissao | Cruzada por conjunto de sistemas (A ⊇ B) | Aberto; por perfil; so admin cria |
| 4 | Threads de entidade | Framework generico `ChatThread(entity_type, entity_id)` + ativacao inicial em 3 entidades | Lista dura por tabela; tudo eager |
| 5 | Conteudo | Markdown + anexos + mentions + reacoes + reply | So texto; texto+md |
| 6 | Notif externa MVP | Apenas badge in-app | Teams push; email; tudo configuravel |
| 7 | UI ancora | Navbar com 1 botao + 2 badges (sistema/usuario) | Popup global; drawer permanente |
| 8 | Alertas do sistema | Unificados em `chat_message` (sender_type='system') — UI separada | Tabela dedicada; reaproveitar `AlertaNotificacao` |
| 9 | Nome do modulo | `app/chat/` (limpo) | `app/notificacoes/` (zumbi, sera removido em F4) |
| 10 | Eventos iniciais | Recebimento + DFE bloqueado + CTe divergente | Outros ficam sob demanda |

Defaults aceitos em bloco (ver secao 6.1): sem expiracao de mensagens, edit em 15min, soft delete,
read receipt 1:1 em DM, sem presenca, typing via SSE, busca FTS Postgres, 8KB/mensagem,
20MB/anexo (max 5/msg), LGPD via export+anonimizacao, threads de entidade sao **lazy**.

---

## 3. Arquitetura

### 3.1 Camadas

```
+------------------------------------------------------------------+
| UI                                                               |
|   base.html (navbar botao + badges)                              |
|   templates/chat/ (drawer, painel, modais)                       |
|   static/chat/js/ (ChatClient: SSE, send, forward, share)        |
+------------------------------------------------------------------+
| Rotas Flask — blueprint chat_bp em app/chat/routes/              |
|   /api/chat/threads[/<id>]      (GET list, POST create, PATCH)   |
|   /api/chat/threads/<id>/members (POST add, DELETE remove)       |
|   /api/chat/messages            (POST send)                      |
|   /api/chat/messages/<id>       (PATCH edit, DELETE)             |
|   /api/chat/messages/<id>/reactions (POST/DELETE)                |
|   /api/chat/messages/<id>/forward   (POST)                       |
|   /api/chat/entity/<type>/<id>/thread (GET or create-on-post)    |
|   /api/chat/stream                  (GET SSE)                    |
|   /api/chat/unread                  (GET counters)               |
|   /api/chat/search                  (GET FTS)                    |
|   /api/chat/share/screen            (POST: compartilhar tela)    |
+------------------------------------------------------------------+
| Services — app/chat/services/                                    |
|   PermissionChecker  — sistemas(u), pode_adicionar, pode_ver     |
|   MessageService     — validar, persistir, publish SSE           |
|   ThreadService      — lazy creation, arquivar, listar           |
|   SystemNotifier     — alert(user_ids, source, titulo, link, …)  |
|   Forwarder          — encaminhar mensagem / compartilhar tela   |
|   SearchService      — FTS com filtros (thread, autor, data)     |
|   AttachmentService  — upload S3, validacao, thumbnails          |
+------------------------------------------------------------------+
| Realtime — app/chat/realtime/                                    |
|   publisher.py  publish(user_id, event_type, payload)            |
|     -> r.publish(f'chat_sse:{user_id}', json)                    |
|   sse.py        stream_chat_events(user_id) generator            |
|     -> pubsub.subscribe + heartbeat + LastEventID replay         |
+------------------------------------------------------------------+
| Modelos — app/chat/models.py                                     |
|   ChatThread / ChatMember / ChatMessage / ChatAttachment /       |
|   ChatReaction / ChatMention / ChatForward                       |
+------------------------------------------------------------------+
| Migrations — scripts/migrations/                                 |
|   2026-04-23_chat_schema.py  (Python — create_app + before/after)|
|   2026-04-23_chat_schema.sql (SQL idempotente — IF NOT EXISTS)   |
+------------------------------------------------------------------+
```

### 3.2 Padrao SSE reutilizado

Verificado em `app/agente/routes/chat.py`:
- Linha 27: `from flask import ..., Response, stream_with_context`
- Linha 367-372: `Response(stream_with_context(_generator()), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'})`
- Linha 1106-1111: `pubsub.subscribe('agent_sse:<session_id>')` para eventos cross-worker

O chat herda esse padrao (canal: `chat_sse:{user_id}`). Isso garante que:
- 4 workers gunicorn rodando em paralelo entregam mensagem para usuario conectado a qualquer deles.
- Nao precisa sticky sessions no Render.
- Reconexao do client usa `Last-Event-ID` para catch-up via DB.

### 3.3 Interacoes externas

| Depende de | Uso |
|------------|-----|
| `app.auth.Usuario` | FK em ChatMember, ChatMessage, ChatMention |
| `app.utils.timezone.agora_utc_naive` | Timestamps naive UTC (regra do projeto) |
| `app.utils.redis_cache` | Conexao Redis ja existente |
| `app.utils.s3_storage` ou equivalente | Upload de anexos (ver `.claude/references/S3_STORAGE.md`) |
| Flask-Login `current_user` | Autenticacao de todas as rotas |

Nao depende de `app/notificacoes/` (modulo zumbi). Spec F4 removera.

---

## 4. Modelos de dados

Todos com `criado_em` e timezone naive UTC (`app.utils.timezone.agora_utc_naive`).

### 4.1 `chat_thread`

Unidade de conversa (DM, grupo, thread de entidade, caixa de sistema).

| Campo | Tipo | Notas |
|-------|------|-------|
| id | BIGINT PK | |
| tipo | VARCHAR(20) NOT NULL | `dm` \| `group` \| `entity` \| `system_dm` |
| titulo | VARCHAR(200) | Null em `dm`/`entity`/`system_dm` (derivado) |
| entity_type | VARCHAR(50) | `pedido` \| `nf` \| `recebimento` \| outro; null se nao-entity |
| entity_id | VARCHAR(100) | `num_pedido` e string (`VCD123`); id alfanumerico permitido |
| sistemas_required | JSONB NOT NULL DEFAULT `[]` | Uniao derivada dos membros, recalculada em add/remove |
| criado_por_id | INT FK usuarios.id | Null para `system_dm` automaticos |
| criado_em | TIMESTAMP NOT NULL | |
| atualizado_em | TIMESTAMP | |
| arquivado_em | TIMESTAMP | Soft archive (thread some da lista) |
| last_message_at | TIMESTAMP | Index para ordenar lista |

Constraints:
- `UNIQUE (entity_type, entity_id) WHERE entity_type IS NOT NULL` — 1 thread por entidade
- `UNIQUE (tipo, criado_por_id) WHERE tipo='system_dm'` — 1 caixa de sistema por usuario
- Index `(last_message_at DESC)`

### 4.2 `chat_member`

| Campo | Tipo | Notas |
|-------|------|-------|
| id | BIGINT PK | |
| thread_id | BIGINT FK chat_thread(id) ON DELETE CASCADE | |
| user_id | INT FK usuarios(id) | |
| role | VARCHAR(20) NOT NULL DEFAULT `member` | `owner` \| `admin` \| `member` |
| adicionado_por_id | INT FK usuarios(id) | Null para auto-add (entity, system_dm) |
| adicionado_em | TIMESTAMP NOT NULL | |
| last_read_message_id | BIGINT FK chat_message(id) | Null = tudo nao lido |
| silenciado | BOOL NOT NULL DEFAULT false | Mute |
| removido_em | TIMESTAMP | Soft remove |

Constraints:
- `UNIQUE (thread_id, user_id) WHERE removido_em IS NULL`
- Index `(user_id, thread_id)` para listagem rapida

### 4.3 `chat_message`

Mensagens — chat humano + alertas do sistema unificados.

| Campo | Tipo | Notas |
|-------|------|-------|
| id | BIGINT PK | Alto volume esperado |
| thread_id | BIGINT FK chat_thread(id) | |
| sender_type | VARCHAR(10) NOT NULL | `user` \| `system` |
| sender_user_id | INT FK usuarios(id) | Null se `system` |
| sender_system_source | VARCHAR(50) | `recebimento` \| `dfe` \| `cte` etc.; null se `user` |
| content | TEXT NOT NULL | Markdown; limite 8192 **bytes UTF-8** (`len(content.encode('utf-8')) <= 8192`) validado app-side |
| content_tsv | tsvector | Full-text, indexado GIN, atualizado via trigger |
| reply_to_message_id | BIGINT FK chat_message(id) | Reply/quote |
| deep_link | VARCHAR(500) | URL contextual (share de tela ou alert do sistema) |
| nivel | VARCHAR(20) | Apenas para `system`: `INFO` \| `ATENCAO` \| `CRITICO` |
| dados | JSONB | Contexto estruturado (recebimento_id, nf, etc.) — **usar `sanitize_for_json`** |
| criado_em | TIMESTAMP NOT NULL | |
| editado_em | TIMESTAMP | |
| deletado_em | TIMESTAMP | Soft delete |
| deletado_por_id | INT FK usuarios(id) | |

Indexes:
- `(thread_id, criado_em DESC)` — listagem principal
- `(sender_user_id, criado_em DESC) WHERE sender_type='user'` — "minhas mensagens"
- `GIN (content_tsv)` — FTS
- `(deletado_em) WHERE deletado_em IS NOT NULL` — auditoria de deletes

### 4.4 `chat_attachment`

| Campo | Tipo |
|-------|------|
| id BIGINT PK | |
| message_id BIGINT FK chat_message(id) ON DELETE CASCADE | |
| s3_key VARCHAR(500) NOT NULL | |
| filename VARCHAR(255) NOT NULL | |
| mime_type VARCHAR(100) NOT NULL | |
| size_bytes BIGINT NOT NULL | |
| criado_em TIMESTAMP NOT NULL | |

Validacao: max 20MB/arquivo, 5/mensagem; mime_type whitelisted (imagens + PDF + planilhas);
quota por usuario definida em configuracao (ver secao 7.3).

### 4.5 `chat_mention`

| Campo | Tipo |
|-------|------|
| id BIGINT PK | |
| message_id BIGINT FK chat_message(id) ON DELETE CASCADE | |
| mentioned_user_id INT FK usuarios(id) | |

Trigger de notificacao: mention gera payload SSE com flag `urgente=true` para o UI destacar.

### 4.6 `chat_reaction`

| Campo | Tipo |
|-------|------|
| id BIGINT PK | |
| message_id BIGINT FK chat_message(id) ON DELETE CASCADE | |
| user_id INT FK usuarios(id) | |
| emoji VARCHAR(16) NOT NULL | |
| criado_em TIMESTAMP NOT NULL | |

`UNIQUE (message_id, user_id, emoji)` — mesma reacao so uma vez.

### 4.7 `chat_forward`

Auditoria de encaminhamento (quem encaminhou o que, para onde).

| Campo | Tipo |
|-------|------|
| id BIGINT PK | |
| original_message_id BIGINT FK chat_message(id) | |
| forwarded_message_id BIGINT FK chat_message(id) | Nova msg criada na thread destino |
| forwarded_by_id INT FK usuarios(id) | |
| criado_em TIMESTAMP NOT NULL | |

---

## 5. Regra de permissao cruzada

### 5.1 Definicao formal

```python
# app/chat/services/permission_checker.py

DOMAIN_NACOM = 'NACOM'
DOMAIN_CARVIA = 'CARVIA'
DOMAIN_MOTOCHEFE = 'MOTOCHEFE'
DOMAIN_HORA = 'HORA'

def sistemas(user) -> set[str]:
    """Conjunto de sistemas/dominios acessiveis pelo usuario."""
    s = {DOMAIN_NACOM}  # todo usuario logado tem Nacom
    if user.sistema_carvia:
        s.add(DOMAIN_CARVIA)
    if user.sistema_motochefe:
        s.add(DOMAIN_MOTOCHEFE)
    if user.loja_hora_id is not None:
        s.add(DOMAIN_HORA)
    return s

def pode_adicionar(actor, target) -> bool:
    """actor pode iniciar DM com target OU adicionar target a grupo."""
    if actor.perfil == 'administrador':
        return True
    # `>=` em set em Python == issuperset (A contem B ou sao iguais)
    return sistemas(actor) >= sistemas(target)

def pode_ver_thread(user, thread) -> bool:
    """user pode ler mensagens desta thread."""
    if user.perfil == 'administrador':
        return True
    return ChatMember.query.filter_by(
        thread_id=thread.id, user_id=user.id, removido_em=None
    ).first() is not None

def usuarios_elegiveis_para_adicionar(actor):
    """Queryset de Usuarios que actor pode adicionar em DM/grupo."""
    # Otimizacao: query SQL que derive sistemas via flags e filtre subset
    ...
```

### 5.2 Propriedades derivadas

| Caso | Comportamento |
|------|---------------|
| A tem `{NACOM,CARVIA}`, B tem `{NACOM}` | A pode iniciar DM com B. B pode responder (ja e membro). |
| A tem `{NACOM}`, B tem `{NACOM,CARVIA}` | A **nao** pode iniciar. B sim. |
| Grupo com membros `{NACOM}` + `{CARVIA}` — quem pode adicionar novo `{NACOM,CARVIA,MOTOCHEFE}`? | So quem ja tem `{NACOM,CARVIA,MOTOCHEFE}` ou superconjunto. |
| Usuario perde acesso a CARVIA (flag vira false) | Membership revalidado em toda leitura; thread some da lista; historico preservado (auditoria). |
| Admin | Bypass total. |

### 5.3 Enforcement

- UI: autocomplete de "adicionar usuario" so mostra elegiveis.
- Backend: **toda rota de escrita** revalida (`MessageService.send`, `ThreadService.add_member`).
- Leitura: `pode_ver_thread` checado antes de devolver mensagens (inclusive SSE).

### 5.4 Ponto aberto a validar pos-MVP

Perfil `vendedor` tem `vendedor_vinculado` (carteira isolada). Spec **nao** aplica esse isolamento
ao chat (vendedor pode falar com outro vendedor mesmo sem carteira em comum). Registrado como
"ponto a validar no primeiro mes de uso".

---

## 6. Fluxos criticos

### 6.1 Envio de mensagem (usuario)

1. `POST /api/chat/messages` com `{thread_id, content, reply_to_message_id?, attachments?}`.
2. `MessageService.send`:
   - Valida `current_user e membro ativo da thread`
   - Valida tamanho em bytes UTF-8: `len(content.encode('utf-8')) <= 8192`
   - Parse markdown: extrai `@usuarios`, valida se cada um e membro (se nao, ignora silenciosamente)
   - Sanitiza HTML de saida (bleach ou similar)
   - Em transacao:
     - Insere `chat_message`
     - Insere `chat_mention` para cada mention valida
     - Insere `chat_attachment` (S3 ja fez upload em request anterior; so registra)
     - Atualiza `chat_thread.last_message_at = now()`
3. Publica em Redis para **cada** membro ativo (exceto sender):
   ```python
   publish(user_id, 'message_new', {
       'thread_id': ..., 'message_id': ...,
       'preview': content[:100], 'sender': {...},
       'urgente': user_id in mentioned_user_ids,
       'deep_link': thread_deep_link,
   })
   ```
4. SSE do cliente recebe e atualiza UI + incrementa badge.

### 6.2 Recebimento SSE (cliente)

- Browser: `new EventSource('/api/chat/stream')` (cookie Flask-Login enviado).
- Backend: `stream_chat_events(current_user.id)` generator
  - `pubsub.subscribe('chat_sse:{user_id}')`
  - Emit heartbeat a cada 25s (Render dropa conexao idle 30-40s — ver `app/teams/CLAUDE.md` R2)
  - On message: `yield f'event: {evt_type}\ndata: {json}\nid: {msg_id}\n\n'`
- Cliente reconecta automaticamente; browser manda `Last-Event-ID` no header; backend reenvia
  tudo > `Last-Event-ID` (query direta ao DB; max 100 mensagens de catch-up).

### 6.3 "Compartilhar esta tela" (share_screen)

Componente `{% include 'chat/share_button.html' %}` no `base.html` — visivel em toda pagina.

1. Click abre modal:
   - Autocomplete destinatario (elegiveis via `usuarios_elegiveis_para_adicionar`)
   - Textarea comentario livre
   - Preview: `{{ self.title() }}` (titulo da pagina) + `window.location.pathname`
2. `POST /api/chat/share/screen` `{destinatario_user_id, comentario, url, title}`:
   - Busca ou cria DM entre `current_user` e `destinatario` (lazy)
   - Cria `chat_message(content=f'{comentario}', deep_link=url, dados={'screen_title': title})`
3. Destinatario recebe notificacao com preview; click no link abre a tela.

### 6.4 Encaminhar mensagem do chat

Hover em mensagem -> botao `↪`.

1. Modal: escolhe thread destino OU usuario (cria DM se nao existir) + comentario opcional.
2. `POST /api/chat/messages/<id>/forward` `{destino_thread_id?, destino_user_id?, comentario?}`.
3. Cria nova `chat_message` na thread destino (sender=current_user) + row em `chat_forward`.
4. Render no destino mostra "Fulano encaminhou: ..." com referencia a mensagem original.

### 6.5 Alerta do sistema (SystemNotifier)

API publica:
```python
from app.chat.services.system_notifier import SystemNotifier

SystemNotifier.alert(
    user_ids=[12, 45],
    source='recebimento',
    titulo='Recebimento #1234 concluiu com erro',
    content='NF 12345 — divergencia de qtd no item 3 (esperado 100, recebido 95)',
    deep_link='/recebimento/1234',
    nivel='CRITICO',
    dados={'recebimento_id': 1234, 'nf_numero': '12345'},
)
```

Implementacao:
```python
def alert(user_ids, source, titulo, content, deep_link, nivel='INFO', dados=None):
    from app.utils.json_helpers import sanitize_for_json
    for uid in user_ids:
        thread = _get_or_create_system_dm(uid)  # lazy
        msg = ChatMessage(
            thread_id=thread.id,
            sender_type='system',
            sender_system_source=source,
            content=f'**{titulo}**\n\n{content}',  # titulo vira bold na UI
            deep_link=deep_link,
            nivel=nivel,
            dados=sanitize_for_json(dados or {}),
        )
        db.session.add(msg)
    db.session.commit()
    # publish SSE para cada uid (fora da transacao, best-effort)
    for uid in user_ids:
        publish(uid, 'message_new', payload)
```

### 6.6 Thread de entidade (lazy)

`GET /api/chat/entity/<type>/<id>/thread`:
- Se existe: devolve thread + primeiras 50 msgs
- Se nao: devolve 404 + `{'entity_type': ..., 'entity_id': ..., 'hint': 'post to create'}`
- UI mostra "Seja o primeiro a comentar" com textarea

`POST /api/chat/messages` com `thread_id=null` + `entity_type` + `entity_id`:
- `MessageService.send` cria thread `tipo='entity'` + adiciona autor como `owner`
- Continua fluxo normal

Adicao de outros membros:
- `@mencao` automaticamente adiciona o mencionado (se `pode_adicionar(autor, mencionado)`)
- Manual via botao "Adicionar" na thread (requer permissao)

---

## 7. UI (integracao com base.html)

### 7.1 Navbar

```html
<!-- app/templates/base.html — proximo ao perfil do usuario -->
<li class="nav-item">
  <button id="chat-toggle" class="btn btn-link nav-link position-relative">
    💬
    <span id="chat-badge-system" class="badge bg-warning position-absolute"
          style="top: 0; left: 0;">0</span>
    <span id="chat-badge-user"  class="badge bg-danger position-absolute"
          style="top: 0; right: 0;">0</span>
  </button>
</li>
```

- Badge `sistema` (amarelo, topo-esquerdo): `COUNT(*) WHERE sender_type='system' AND last_read_at < criado_em`
- Badge `usuario` (vermelho, topo-direito): idem com `sender_type='user'`
- Contadores atualizam via SSE (`event: unread_changed`) ou poll a cada 30s (fallback)

### 7.2 Drawer lateral

- Largura 420px, slide-in pela direita; toggle do botao acima
- Tabs: `DMs` | `Grupos` | `Entidades` | `Sistema`
- Lista ordenada por `last_message_at DESC`, com preview da ultima msg e contador de nao lidas
- Click abre painel de mensagens no mesmo drawer (em telas largas, 2 colunas: lista + painel)

### 7.3 Painel de mensagens

- Header: avatar/titulo da thread, lista de membros (tooltip), botao `⋮` (configs, sair, silenciar)
- Lista virtual scroll reversa (carrega mais ao rolar para cima)
- Render de markdown sanitizado; anexos inline (imagem = preview, pdf = link com icone)
- Reacoes como pills abaixo da mensagem
- Footer: textarea com atalhos (Enter=envia, Shift+Enter=quebra), `📎`, `@` trigga autocomplete

### 7.4 "Compartilhar esta tela"

- Botao discreto no topo direito de cada pagina (dentro do bloco header do `base.html`)
- Icone `↗` + tooltip "Compartilhar esta tela"
- Click abre modal da secao 6.3

### 7.5 Integracao com design tokens

Seguir `.claude/references/design/GUIA_COMPONENTES_UI.md`. Badges usam API `--_badge-bg/color`.
CSS em `app/static/chat/css/chat.css`, carregado via layer `modules` no `main.css`.

---

## 8. Erros, bordas, observabilidade

| Cenario | Tratamento |
|---------|------------|
| SSE cai (worker recycle) | Client reconecta; `Last-Event-ID` -> catch-up via DB (max 100 msgs) |
| Usuario perde acesso a sistema | Membership revalidado em toda leitura; thread some; historico preservado |
| Redis indisponivel para publish | Mensagem persiste no DB; entrega atraves de polling no reconnect (graceful degrade) |
| Pubsub drop entre publish e subscribe | Cliente faz poll `/api/chat/unread` a cada 30s como fallback |
| `@mencao` a usuario sem permissao a thread | Mention ignorada silenciosamente (nao gera row em `chat_mention`) |
| Upload S3 falha | Transacao de mensagem rollback; 400 no endpoint |
| Content > 8KB | 400 no backend + validacao client-side |
| Worker gunicorn reciclado no meio de envio | DB ja foi commit; SSE reentregue no reconnect; cliente nao ve perda |
| SSL drop PostgreSQL (Render 30-40s) | Reusar `_commit_with_retry()` do padrao `app/teams/services.py:130-164` |
| Anexo S3 orfao (msg rollback depois de upload) | Cleanup job RQ semanal: delete S3 keys sem row em `chat_attachment` |

Observabilidade:
- Sentry: capturar exceptions em `MessageService`, `SystemNotifier`, SSE generator
- Logs estruturados: `logger.info('[CHAT] message_sent', extra={'thread_id', 'msg_id', 'user_id'})`
- Metricas: contar `chat_message` por dia, por `sender_type`, por `source` (para dimensionar uso)

---

## 9. Testes

### 9.1 Unit (`tests/chat/`)

- `PermissionChecker`: matriz de casos (8 combinacoes de sistemas × admin)
- `MessageService.send`: mentions, sanitizacao, limite 8KB
- Markdown parser: extrai mentions sem falsos positivos (`@bob@email.com` nao e mention)
- FTS query builder: escape de caracteres especiais Portugues

### 9.2 Integracao (com DB fixtures)

- Fluxo completo: criar DM, enviar, editar, deletar, reacao, reply
- Lazy thread creation em `entity`
- `SystemNotifier.alert` gera thread `system_dm` + msg + SSE publish
- Permission denied em escritas de nao-membro
- Encaminhamento cria row em `chat_forward`

### 9.3 SSE (com Redis real ou mock)

- Subscribe + publish -> cliente recebe evento correto
- Reconnect com `Last-Event-ID` -> replay do DB
- Heartbeat evita drop em 25s

### 9.4 Worker (alertas do sistema)

- 3 cenarios do MVP:
  - Recebimento worker chamando `SystemNotifier.alert` com status=`erro`
  - DFE bloqueado (Fase 2 recebimento) -> alerta para Gabriella/Nicoly
  - CTe divergente (Fretes) -> alerta para controller de frete

### 9.5 E2E (smoke)

- Selenium/Playwright: logar, abrir chat, enviar mensagem, validar render

---

## 10. Migrations

Seguindo regra de 2 artefatos (`~/.claude/CLAUDE.md` secao Migrations):

### 10.1 `scripts/migrations/2026-04-23_chat_schema.py`

```python
#!/usr/bin/env python3
"""Cria 7 tabelas do modulo chat in-app + indices + trigger FTS."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db

def main():
    app = create_app()
    with app.app_context():
        # before
        before = {t: _count(t) for t in TABLES}
        print('Before:', before)

        # DDL idempotente
        db.engine.execute(DDL_SQL)

        # after
        after = {t: _count(t) for t in TABLES}
        print('After:', after)
        assert all(_table_exists(t) for t in TABLES), "algumas tabelas nao foram criadas"

if __name__ == '__main__':
    main()
```

### 10.2 `scripts/migrations/2026-04-23_chat_schema.sql`

SQL puro idempotente (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`) para executar
no Render Shell. Inclui:
- 7 tabelas
- Indices listados na secao 4
- Trigger `chat_message_tsv_trigger` que atualiza `content_tsv` em INSERT/UPDATE de `content`
  (usando `portuguese` como configuracao FTS)

---

## 11. Fases de entrega

| Fase | Escopo | Pre-requisito |
|------|--------|---------------|
| **F1 (MVP)** | Tudo do spec. Modulo `app/chat/` + 3 alertas (recebimento, DFE, CTe) instrumentados | — |
| **F2** | Push Teams pro-ativo para mencoes e alertas `CRITICO` | Dedup Usuario Teams <-> Usuario sistema |
| **F3** | Tela "Minhas preferencias de notificacao" + email fallback | F2 |
| **F4** | Remocao de `app/notificacoes/` | Migracao dos 3 callers (carteira + seguranca) para `app/chat/` |

---

## 12. Dividas tecnicas e riscos

### 12.1 Dividas declaradas

- **D1**: `app/notificacoes/` sobrevive como dead code ate F4. Documentar em `CLAUDE.md` raiz.
- **D2**: Dedup Usuario Teams <-> Usuario sistema — requisito de F2.
- **D3**: Perfil `vendedor.vendedor_vinculado` nao e respeitado no chat. Validar pos-MVP.
- **D4**: Generator SSE mantem conexao Postgres aberta por muito tempo — monitorar pool.
  Se virar gargalo, passar a usar `db.session.close()` apos cada evento consumido.

### 12.2 Riscos

- **R1 — volume de SSE**: 50 usuarios × 4 workers = 200 conexoes Redis persistentes. Monitorar
  `CLIENT LIST` no Redis e ajustar `maxclients` se necessario.
- **R2 — crescimento FTS**: `content_tsv` em todas as mensagens pode pesar. Revisar > 10M linhas.
  Mitigacao: indice particionado por `criado_em`.
- **R3 — deep_link quebra com refactor de rotas**: convencao adotada: `deep_link` e string opaca,
  UI abre em nova aba, sem parse. Rotas que mudam precisam de redirect.
- **R4 — abuso de anexos S3**: sem quota por usuario, custo pode subir. Mitigacao: config
  `MAX_ATTACHMENTS_PER_USER_PER_DAY` + monitoramento via Sentry.
- **R5 — chat como vetor de vazamento**: usuario pode "roubar" informacao postando `@outro`.
  Mitigacao: permissao cruzada ja filtra; registrar auditoria em `chat_forward`.

---

## 13. Referencias

- Padrao SSE: `app/agente/routes/chat.py:27,367-372,1106-1111`
- Pub/sub Redis: mesmo arquivo, canais `agent_sse:<session_id>`
- SSL retry Postgres: `app/teams/services.py:130-164` (`_commit_with_retry`)
- Reciclagem worker: `start_render.sh` hook `worker_exit`
- S3 storage: `.claude/references/S3_STORAGE.md`
- Timezone: `.claude/references/REGRAS_TIMEZONE.md` (naive UTC)
- Sanitizacao JSONB: `app/utils/json_helpers.sanitize_for_json` (obrigatorio em `dados`)
- Design tokens: `.claude/references/design/GUIA_COMPONENTES_UI.md`
- Modelo `Usuario`: `app/auth/models.py:15-161`
- Gotchas Teams: `app/teams/CLAUDE.md` (R1-R8)

---

## 14. Aprovacao

- [x] Usuario (Rafael): aprovou decisoes 1-10 + bloco de defaults (pergunta 9) durante brainstorming 2026-04-23
- [ ] Revisao final deste spec (ver secao "Proximos passos" no chat)
- [ ] Plano de implementacao (writing-plans — proxima etapa)
