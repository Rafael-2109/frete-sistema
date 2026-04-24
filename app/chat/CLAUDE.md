# Chat — Guia de Desenvolvimento

**LOC**: ~2.0K | **Arquivos**: 22 py/html + 2 JS + 1 CSS | **Atualizado**: 2026-04-24

Modulo de chat in-app + alertas do sistema unificados. Implementado na
branch `feature/chat-inapp` (plano 25 tasks, Fase F1 MVP).
Hardening P0 aplicado na branch `fix/chat-audit-p0` (2026-04-24) — ver secao "Gotchas".

**Spec**: `docs/superpowers/specs/2026-04-23-chat-inapp-design.md`
**Plano**: `docs/superpowers/plans/2026-04-23-chat-inapp.md`

---

## Estrutura

```
app/chat/
  __init__.py                  # Blueprint chat_bp (/api/chat)
  models.py                    # 7 modelos SQLAlchemy (1 JSONB, 1 tsvector FTS)
  markdown_parser.py           # extract_mentions (usado) + render_markdown/sanitize_html (DEAD — ver Gotchas)
  utils.py                     # url_safe(url) — validacao deep_link compartilhada
  routes/
    thread_routes.py           # GET/POST /threads + /dm + /group + /members + /entity/<t>/<id>/thread
    message_routes.py          # send / edit / delete / list / reactions / forward
    stream_routes.py           # /poll (realtime!) + /unread + /search FTS + /read + /ui/drawer + /stream (SSE legado)
    share_routes.py            # /share/screen + /entity/<t>/<id>/message
  services/
    permission_checker.py      # sistemas() + pode_adicionar() + pode_ver_thread()
    thread_service.py          # CRUD + lazy creation DM/system_dm/entity
    message_service.py         # send/edit/delete/list + mentions + publish
    attachment_service.py      # S3 upload + mime/size validacao + secure_filename
    system_notifier.py         # API publica alert(user_ids, source, ...)
  realtime/
    publisher.py               # publish(user_id, event, data) -> Redis chat_sse:<id>
    sse.py                     # stream_chat_events generator + heartbeat + catch-up
  hooks/                       # wrappers do SystemNotifier para workers externos
    recebimento.py             # notify_recebimento_finalizado(recebimento)
    dfe_bloqueado.py           # notify_dfe_bloqueado(dfe_id, nf, motivo, fornecedor)
    cte_divergente.py          # notify_cte_divergente(cte, cotado, cte_val)

app/templates/chat/
  _navbar_badge.html           # <li> navbar com botao chat + 2 badges
  _share_button.html           # <button> compartilhar tela
  drawer.html                  # fragmento drawer (carregado via /ui/drawer)

app/static/
  css/modules/_chat.css        # CSS do modulo (layer modules, design tokens)
  chat/js/chat_client.js       # SSE + badges (global window.ChatClient)
  chat/js/chat_ui.js           # Drawer + modais (global window.ChatUI)

scripts/migrations/
  2026-04-23_chat_schema.{py,sql}  # 7 tabelas + indices + trigger FTS
```

---

## Regras criticas

### R1: Redis e opcional — publish best-effort
`publisher.publish()` NAO lanca excecao se Redis down. Mensagem persiste
no DB; client reconnecta e pega via catch-up (`Last-Event-ID` -> query DB).

### R2: Realtime via POLLING (nao SSE)
Desde 2026-04-24 (fix/chat-audit-p0), `chat_client.js` usa polling em
`GET /api/chat/poll` a cada 4s (aba focada) / 15s (visivel sem foco) /
pausado (document.hidden).

Motivo: SSE mantinha 1 slot de worker gunicorn (`worker_class='gthread'`,
4 workers × 2 threads = 8 slots) aberto por user permanentemente. Com
agente web TAMBEM usando SSE, 4 users ativos = 8 slots consumidos =
sistema trava para requests normais.

Poll endpoint retorna `{new, edited, deleted, unread, last_id, server_ts}`.
Client mantem `since_id` + `since_ts` para query incremental.

**Rota `/stream` (SSE) permanece registrada** — codigo nao foi removido porque
o padrao pode ser util se algum futuro endpoint precisar push real. Nenhum
cliente consome hoje. Publisher Redis (`publisher.publish`) continua sendo
chamado mas publica em canal sem subscribers (no-op efetivo).

### R3: PermissionChecker em TODA rota de escrita
Revalidar mesmo que UI tenha filtrado. Admin bypass via
`user.perfil == 'administrador'`. Forward exige membership na thread ORIGEM.

**`ThreadService.add_member` (hardening P0 2026-04-24)**:
- DM e system_dm NAO aceitam add (`raise PermissionError`).
- group/entity: actor precisa ser `owner`/`admin` da thread OU admin global.
- `pode_adicionar(actor, target)` continua como gate cross-domain (sistemas).
Antes do fix, qualquer user podia se auto-adicionar em qualquer thread (IDOR).

### R4: `sanitize_for_json` em `ChatMessage.dados`
`dados` e JSONB; valores Decimal/datetime quebram flush.
Usar `app.utils.json_helpers.sanitize_for_json`. SystemNotifier ja faz.

### R5: Alertas unificados em `chat_message`
`sender_type='system'` + `sender_system_source='recebimento'|'dfe'|'cte'|...`.
Nao criar tabela separada.

### R6: Mentions so valem para membros ativos
Parser extrai `@usuario` do content. Se mencionado NAO e membro ativo,
`chat_mention` nao e criada. SQL LIKE tem escape (`_` e wildcard single-char).

### R7: URL validation em deep_link
`app/chat/utils.url_safe()` — fonte unica de validacao. Usado em:
- `share_routes.py` share_screen
- `MessageService.send` (toda mensagem com deep_link, inclusive forward)

Bloqueia: `javascript:`, `data:`, `file:`, `//host` (open redirect),
`/\t/host` / `/\n/host` (TAB/CR/LF injection pre-netloc). Aceita http/https
ou path absoluto `/...` sem netloc. **NAO duplicar _url_safe** em novos endpoints
— importar de `app.chat.utils`.

### R8: Soft delete esconde content
`_message_dict` retorna `content=None` se `deletado_em IS NOT NULL`.
Forward de msg deletada e bloqueado.
Edit de msg deletada tambem e bloqueado (hardening P0): `edit` lancava SSE `message_edit`
com `new_content` vazando preview oculto. Hoje levanta `MessageError`.
SSE catch-up (`realtime/sse._catchup_events`) filtra `deletado_em IS NULL`
— antes do fix, Last-Event-ID vazava preview de mensagens deletadas.
`delete()` publica SSE `message_delete` para que clientes atualizem sem F5.

---

## API publica

### SystemNotifier (para workers que disparam alertas)

```python
from app.chat.services.system_notifier import SystemNotifier
SystemNotifier.alert(
    user_ids=[12, 45],
    source='recebimento',
    titulo='Recebimento #1234 concluiu com erro',
    content='NF 12345 — divergencia item 3',
    deep_link='/recebimento/1234',
    nivel='CRITICO',  # INFO | ATENCAO | CRITICO
    dados={'recebimento_id': 1234},  # opcional, JSONB
)
```

### Hooks (wrappers testados para eventos comuns)

```python
from app.chat.hooks.recebimento import notify_recebimento_finalizado
from app.chat.hooks.dfe_bloqueado import notify_dfe_bloqueado
from app.chat.hooks.cte_divergente import notify_cte_divergente
```

Todos com try/except interno — nao levantam excecao.

---

## Gotchas

### Bug #1: FK circular `last_read_message_id`
`chat_members.last_read_message_id` -> `chat_messages.id` MAS
`chat_messages.thread_id` -> `chat_threads.id`. SQLAlchemy exige
`use_alter=True` no FK para evitar circular em `create_all`.
Ver `models.py:66`.

### Bug #2: SSE com 4 workers gunicorn
`WEB_CONCURRENCY=1` do `render.yaml` e sobrescrito por `start_render.sh`
para `workers=4`. Redis pub/sub e OBRIGATORIO — sem ele mensagens ficam
presas no worker que gerou.

### Bug #3: `query.get()` cacheado em tests
SQLAlchemy 2.x identity map cacheia. Em tests que commitam via service +
verificam via query, usar `db.session.expire_all()` + `db.session.get()`.

### Bug #4: NULL semantics no unread
`sender_user_id != current_user.id` em SQL (`<>`) retorna NULL quando
`sender_user_id IS NULL`. Mensagens de sistema (sender_user_id=NULL)
eram silenciosamente excluidas. Fix: `or_(is_(None), != current_user.id)`.

### Bug #5: Poluicao DB em tests
Services commitam; `db_session` fixture com rollback nao desfaz.
Solucao: emails com `uuid.uuid4().hex[:8]` prefix por run. **TODOS** os arquivos
de test devem ter `_RUN` no topo e usar `f'foo_{_RUN}@t.local'`.

### Bug #6: `get_or_create_dm` cria duplicata em concorrencia (P0 fix)
SELECT + INSERT sem lock criava 2 DMs em double-click. Solucao:
`pg_advisory_xact_lock(hash(par_ordenado))` serializa por par.
Mesmo padrao em `get_or_create_system_dm` (workers RQ concorrentes).

### Bug #7: Markdown renderer e DEAD CODE
`render_markdown` e `sanitize_html` em `markdown_parser.py` NAO sao invocados
em lugar nenhum do backend. Frontend (`chat_ui.js:203`) usa `escapeHtml(m.content)`
direto. Resultado: `**bold**` aparece literal, `[link](url)` nao vira link clicavel.
O UNICO vetor de link e `deep_link` (validado via `url_safe`).

Decisao pendente: ativar markdown (aplicar `sanitize_html` no `_message_dict`) OU
remover o dead code e documentar que mensagens sao texto puro. Se ativar, revalidar
testes de XSS (payloads com inline handlers `onerror`, base64 data URIs).

### Débito: Hooks de alerta nao instalados em workers (nao e bug)
`notify_recebimento_finalizado`, `notify_dfe_bloqueado`, `notify_cte_divergente`
NAO sao chamados em `app/recebimento/` nem `app/fretes/`. Alertas estao
prontos mas inativos. Instalar nos call-sites documentados em "Ativacao de
alertas — tasks pendentes" abaixo.

---

## Ativacao de alertas — tasks pendentes

Os hooks (`app/chat/hooks/`) estao prontos e testados. Instalar chamadas
nos workers existentes:

### Recebimento (Task 21)
Em `app/recebimento/workers/recebimento_lf_jobs.py`, apos setar
`transfer_status='concluido'` ou `='erro'`:

```python
try:
    from app.chat.hooks.recebimento import notify_recebimento_finalizado
    notify_recebimento_finalizado(recebimento)
except Exception as e:
    logger.error(f'[CHAT hook] falhou: {e}', exc_info=True)
```

### DFE bloqueado (Task 22)
Em `app/recebimento/services/odoo_po_service.py` ou jobs de validacao fiscal,
no ponto onde divergencia NF-PO e criada:

```python
try:
    from app.chat.hooks.dfe_bloqueado import notify_dfe_bloqueado
    notify_dfe_bloqueado(
        dfe_id=dfe.id, nf_numero=dfe.numero_nf,
        motivo='Divergencia de preco no item X', fornecedor=fornecedor.nome,
    )
except Exception:
    ...
```

### CTe divergente (Task 23)
Em `app/fretes/services/` onde CTe e comparado com cotacao:

```python
try:
    from app.chat.hooks.cte_divergente import notify_cte_divergente
    notify_cte_divergente(cte, valor_cotado=cotacao.total, valor_cte=cte.valor)
except Exception:
    ...
```

---

## Observabilidade

- Logs: prefixo `[CHAT]` em logger de `app.utils.logging_config`
- Sentry: SystemNotifier + SSE generator capturados automaticamente
- Metricas: `SELECT COUNT(*), sender_type FROM chat_message GROUP BY ...`

---

## Interdependencias

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app.auth.models.Usuario` | FK em member/message/mention | Mudanca de perfil afeta permissao |
| `app.utils.json_helpers` | sanitize_for_json | Obrigatorio em `ChatMessage.dados` |
| `app.utils.timezone` | agora_utc_naive | Todos timestamps naive UTC |
| `app.utils.logging_config` | logger | Prefixo `[CHAT]` |
| Redis (`REDIS_URL` env) | pub/sub | Opcional — publish sem Redis = graceful degrade |
| Padrao de `app/agente/routes/chat.py` | stream_with_context + pubsub | Manter compatibilidade de SSE |
