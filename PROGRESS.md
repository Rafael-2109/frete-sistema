# Chat In-App — Progresso da Implementacao

**Branch**: `feature/chat-inapp`
**Ultima atualizacao**: 2026-04-23
**Progresso**: 20 de 25 tasks concluidas (80%) — **FASE D + FASE E (UI) COMPLETAS**

---

## Contexto — leia ANTES de continuar

1. **Spec**: `docs/superpowers/specs/2026-04-23-chat-inapp-design.md` (commit `d1e3a282`, 659 linhas, **aprovado pelo usuario**)
2. **Plano**: `docs/superpowers/plans/2026-04-23-chat-inapp.md` (commit `d4e30e72`, 25 tasks em 7 fases)
3. **Usuario**: quer **qualidade alta**, aprovou Subagent-Driven Development com 2-stage review (spec + code quality)
4. **Instrucao ativa do usuario**: "pode ir direto e focado" — autonomous mode, sem pedir confirmacao a cada passo

---

## Como retomar

Comando para a nova sessao Claude Code:

```
Continuando trabalho em feature/chat-inapp. Leia PROGRESS.md (raiz) primeiro.
Retome pela Task 8 (MessageService) usando superpowers:subagent-driven-development.
Padrao: implementer + spec reviewer + code quality reviewer por task.
Auto mode, usuario pediu para nao interromper a cada passo.
```

Verifique depois:
```bash
git status                            # confirmar branch feature/chat-inapp
git log --oneline main..HEAD | head  # ver commits (deve ter 19+)
source .venv/bin/activate
pytest tests/chat/ -v --no-header 2>&1 | tail -5  # confirmar ~30 tests passam
```

---

## Arquitetura ja implementada

```
app/chat/
  __init__.py                     # Blueprint chat_bp (/api/chat)
  models.py                       # 7 modelos SQLAlchemy ✅
  markdown_parser.py              # extract_mentions + sanitize ✅
  routes/
    __init__.py                   # vazio
    thread_routes.py              # STUB — implementar na Task 12
    message_routes.py             # STUB — Task 13
    stream_routes.py              # STUB — Task 14
    share_routes.py               # STUB — Task 15
  services/
    permission_checker.py         # sistemas() + pode_adicionar() ✅
    thread_service.py             # CRUD + lazy entity/system_dm ✅
    attachment_service.py         # S3 upload + validacao ✅
    # message_service.py          # Task 8 — PRÓXIMA
    # system_notifier.py          # Task 9
  realtime/
    publisher.py                  # publish(user_id, event, data) Redis ✅
    sse.py                        # stream_chat_events generator ✅

scripts/migrations/
  2026-04-23_chat_schema.sql      # DDL idempotente ✅
  2026-04-23_chat_schema.py       # wrapper com before/after ✅

tests/chat/
  conftest.py                     # fixtures: app, db_session, user_factory ✅
  test_models.py                  # 3 tests ✅
  test_markdown_parser.py         # 7 tests ✅
  test_permission_checker.py      # 7 tests ✅
  test_thread_service.py          # 6 tests ✅
  test_attachment_service.py      # 6 tests ✅
  test_publisher.py               # 3 tests ✅
  test_sse.py                     # 2 tests ✅
  # Total: ~34 tests passando
```

DB local tem 7 tabelas `chat_*` criadas (migration rodou). Indices + trigger FTS tambem.

---

## Tasks status (detalhado)

| # | Task | Status | Commit | Notas |
|---|------|--------|--------|-------|
| 1 | Estrutura + blueprint | ✅ | `d436ec0c` + `aa0bc821` | — |
| 2 | Modelos SQLAlchemy | ✅ | `6a313e63` + `fe397b22` + `741c942f` | Fix review: `text()` em partial indexes + `uq_chat_threads_system_dm` |
| 3 | Migration DDL | ✅ | `6747ff82` + `324fc834` + `856ee49e` | Fix: `engine.begin()` + `uq_chat_members_active` |
| 4 | Markdown parser | ✅ | `7d9356d2` + `47c3edb6` | — |
| 5 | PermissionChecker | ✅ | `4b862723` + `a00ed7ee` | — |
| 6 | ThreadService | ✅ | `218f9ba9` | — |
| 7 | AttachmentService | ✅ | `4f9226d5` + `ae131111` + `908ca958` | Fix review: `secure_filename` + S3_BUCKET guard |
| 10 | Publisher Redis | ✅ | `c6799651` + `5a59c879` | — |
| 11 | SSE generator | ✅ | `0c36f0ec` | — |
| 8 | MessageService | ✅ | `1a53bb1f` + `1b232823` + `7193a5f8` | Fixes review: SQL LIKE escape `_` + mock publish em edit/delete + `db.session.get` com expire_all |
| 9 | SystemNotifier | ✅ | `f0848a4b` + `a5003eb6` | Fix review: 2-pass atomic (commit parcial) + assert call_count |
| 12 | Rotas thread | ✅ | `5169c600` + `6d7fcd81` | Fix review: select 2.x + entity_type lower + add_member 200 |
| 13 | Rotas mensagem | ✅ | `9051d4e0` + `5b4cf0e1` | Fix review: forward valida membership origem + bloqueia deletada + audit best-effort |
| 14 | Rotas stream/unread/search | ✅ | `864e07d9` + `acfeb838` | Fix review: NULL semantics em unread para sender_user_id IS NULL (system msgs) |
| 15 | Rotas share/entity | ✅ | `6c584f5a` + `12b3f2b1` + `d8a13740` | Fix review: URL scheme allowlist (XSS + open redirect) + race guard IntegrityError |
| 16 | CSS + navbar badge | ✅ | `6f17979e` | CSS em modules/_chat.css (CLAUDE.md compliant), include _navbar_badge.html |
| 17 | JS ChatClient | ✅ | `4c9c551e` | SSE client + badges + counters, node --check OK |
| 18 | Drawer + painel | ✅ | `8995496b` | chat_ui.js + drawer.html + route /ui/drawer |
| 19 | Compartilhar tela | ✅ | `330888c8` | Modal de compartilhamento integrado no navbar |
| 20 | Encaminhar msg UI | ✅ | `1d844b82` | Botao ↪ em renderMessage + openForwardModal |
| **21** | **Integrar alerta recebimento** | ⏳ **PROXIMA (Fase F)** | — | Depende de 9 (feito) |
| 22 | Integrar alerta DFE | pending | — | Depende de 9 |
| 23 | Integrar alerta CTe | pending | — | Depende de 9 |
| 24 | CLAUDE.md modulo + raiz | pending | — | Documentacao |
| 25 | Smoke test E2E | pending | — | Final |

---

## Decisoes-chave (reforco do spec, para nao esquecer)

1. **Hibrido**: canais livres + threads ancoradas em entidades (pedido/NF/recebimento)
2. **Realtime**: SSE + Redis pub/sub (canal `chat_sse:{user_id}`) — reusa padrao do `app/agente/routes/chat.py`
3. **Permissao cruzada**: A pode adicionar/falar com B sse `sistemas(A) ⊇ sistemas(B)` (admin bypass)
4. **Sistemas**: NACOM (base), CARVIA, MOTOCHEFE, HORA — derivados de flags em `Usuario`
5. **Alertas unificados** em `chat_message` com `sender_type='system'` — sem tabela dedicada
6. **MVP**: apenas badge in-app; push Teams + email ficam para F2/F3 (pre-req: dedup Usuario Teams↔sistema)
7. **UI**: navbar com 1 botao + 2 badges (`sistema` amarelo + `usuario` vermelho); drawer 420px
8. **Conteudo**: markdown + anexos (20MB/5max) + mentions + reacoes + reply
9. **Defaults** (do bloco): edit 15min, soft delete, read receipt 1:1, sem presenca, typing SSE, FTS Postgres, 8KB/msg UTF-8 bytes, LGPD export+anonimiza, lazy threads
10. **Eventos sistema MVP**: recebimento (ok/erro), DFE bloqueado, CTe divergente
11. **Modulo novo**: `app/chat/` limpo; `app/notificacoes/` fica como zumbi ate F4

---

## Processo de execucao (para reproduzir)

1. **Por task, dispatch 3 subagentes**:
   - Implementer (`general-purpose`, sonnet) — recebe full task text + workflow inline + warnings sobre gotchas
   - Spec reviewer (`general-purpose`, sonnet) — compara diff contra spec da task
   - Code quality reviewer (`feature-dev:code-reviewer`, sonnet) — HIGH confidence only

2. **Se reviewer achar issue**: aplico fix diretamente (ou re-dispatch) + re-review

3. **Warnings Pyright (`reportMissingImports`)**: ignorar — runtime funciona, tests passam. Sao config-noise do Pyright server.

4. **TaskUpdate** para cada task: in_progress ao iniciar, completed ao fechar ambos reviews.

5. **Commits frequentes**: 1 `feat()` por task + `fix()` ou `chore()` para cada fix de review.

---

## Issues ja pegos pelos reviews (padrao de alerta)

1. **Partial indexes**: `Column('x').isnot(None)` em `__table_args__` gera DDL fragil — usar `text("x IS NOT NULL")`.
2. **Migration SQLAlchemy 2.x**: `engine.connect()` NAO comita DDL automaticamente; usar `engine.begin()`.
3. **Path traversal**: `filename` em S3 key — usar `werkzeug.utils.secure_filename`.
4. **S3 bucket vazio**: env var missing faz boto3 silenciosamente falhar — guard eager no metodo.
5. **Uniqueness dupla em threads**: precisa `uq_chat_threads_entity` (entity) + `uq_chat_threads_system_dm` (1 system_dm/user).
6. **Membership ativo**: `uq_chat_members_active` WHERE `removido_em IS NULL`.

Estas licoes estao codificadas em modelos + migrations. Se refizer algo, respeite os padroes.

---

## Diretrizes operacionais

- **Timezone**: sempre `agora_utc_naive()` de `app.utils.timezone` (naive UTC — convencao do projeto)
- **JSONB com Decimal**: sempre `sanitize_for_json()` de `app.utils.json_helpers` antes de atribuir
- **Pyright suppressions**: em arquivos de stub com lazy imports, usar file-level `# pyright: reportUnusedImport=false`
- **Migrations**: dois artefatos (`.py` + `.sql` idempotente), `sys.path.insert` obrigatorio no topo do `.py`
- **Testes**: TDD (test first), usar fixtures do `tests/chat/conftest.py` (app/db_session/user_factory)

---

## Arquivos NAO tocar

- `app/notificacoes/` — zumbi; sera removido em F4 (Task 24+ ou sprint futuro)
- `app/agente/routes/chat.py` — e REFERENCIA para padrao SSE, nao modificar
- Modelos fora de `app/chat/` — so leitura (para FKs)

---

## Proxima acao

**Task 8**: MessageService. Arquivo em `app/chat/services/message_service.py`. Ver plano (Task 8) para codigo completo. Precisa:
- `send(sender, thread_id, content, reply_to_message_id?, deep_link?, attachments?)`
- `edit(user, message_id, new_content)` com janela 15min
- `delete(user, message_id)` soft delete
- `list_for_thread(user, thread_id, limit, before_id?)`
- **Publish SSE** para cada membro ativo (exceto sender) via `from app.chat.realtime.publisher import publish`
- Parser de mentions via `from app.chat.markdown_parser import extract_mentions`
- Validar membership + 8KB UTF-8 + criar `chat_mention` so se mencionado e membro ativo

6+ tests obrigatorios (send simples, rejects non-member, oversized, mentions persistem, edit within window, soft delete).

Apos Task 8: Task 9 (SystemNotifier), depois rotas HTTP (12-15), UI (16-20), integracoes (21-23), docs (24-25).

Boa sorte!
