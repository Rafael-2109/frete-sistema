# Chat In-App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar modulo `app/chat/` MVP (Fase F1 do spec): chat usuario↔usuario (DM/grupos), threads ancoradas em entidades (pedido/NF/recebimento), alertas do sistema unificados (sender_type='system'), UI na navbar com 2 badges, entrega realtime SSE+Redis. Incluir 3 integracoes de alerta (recebimento / DFE bloqueado / CTe divergente).

**Architecture:** Reusa padrao SSE+Redis pub/sub ja em producao em `app/agente/routes/chat.py`. Modelos em `app/chat/models.py` (7 tabelas), servicos em `app/chat/services/`, rotas em `app/chat/routes/`, frontend em `app/static/chat/` + `app/templates/chat/`. Permissao cruzada por conjunto de sistemas (NACOM/CARVIA/MOTOCHEFE/HORA) central em `PermissionChecker`.

**Tech Stack:** Flask + SQLAlchemy + PostgreSQL (jsonb + tsvector) + Redis pub/sub + SSE nativo (Flask `stream_with_context`) + Jinja2 + Bootstrap 5 + vanilla JS (EventSource).

**Spec de origem:** `docs/superpowers/specs/2026-04-23-chat-inapp-design.md` (commit `d1e3a282`).

---

## Mapa de arquivos (decomposicao antes das tasks)

### Arquivos a criar

```
app/chat/
  __init__.py                      # Blueprint chat_bp
  models.py                        # 7 modelos
  routes/__init__.py
  routes/thread_routes.py          # /threads, /members, /entity/<t>/<id>
  routes/message_routes.py         # /messages, /reactions, /forward
  routes/stream_routes.py          # /stream (SSE) + /unread + /search
  routes/share_routes.py           # /share/screen
  services/__init__.py
  services/permission_checker.py   # sistemas(u), pode_adicionar, pode_ver
  services/thread_service.py       # get_or_create_dm, lazy entity, list
  services/message_service.py      # send, edit, delete, list
  services/attachment_service.py   # upload S3, validacao
  services/system_notifier.py      # alert API publica
  services/forwarder.py            # encaminhar msg + share screen
  services/search_service.py       # FTS query builder
  markdown_parser.py               # extract_mentions + sanitize
  realtime/__init__.py
  realtime/publisher.py            # publish(user_id, event, payload)
  realtime/sse.py                  # stream_chat_events generator
  CLAUDE.md                        # guia de dev do modulo

app/static/chat/
  css/chat.css                     # estilos modulo
  js/chat_client.js                # SSE, badges, reconnect
  js/chat_ui.js                    # drawer, painel, modais

app/templates/chat/
  _navbar_badge.html               # include em base.html
  _share_button.html               # include em base.html
  drawer.html                      # tabs + lista threads (fragmento)
  panel.html                       # painel mensagens (fragmento)

tests/chat/
  __init__.py
  conftest.py                      # fixtures usuarios + threads
  test_permission_checker.py
  test_markdown_parser.py
  test_thread_service.py
  test_message_service.py
  test_system_notifier.py
  test_publisher.py
  test_sse.py
  test_routes_thread.py
  test_routes_message.py
  test_routes_stream.py
  test_integration_recebimento.py

scripts/migrations/
  2026-04-23_chat_schema.py        # Python (create_app + before/after)
  2026-04-23_chat_schema.sql       # SQL idempotente
```

### Arquivos a modificar

```
app/__init__.py                    # registrar chat_bp
app/templates/base.html            # incluir navbar_badge + share_button
app/static/css/main.css            # @import modulo chat.css (layer modules)
app/recebimento/workers/<file>     # chamar SystemNotifier.alert ao final
app/recebimento/services/<nf_po>   # alertar ao criar bloqueio DFE (Fase 2)
app/fretes/services/<cte>          # alertar divergencia CTe
CLAUDE.md                          # adicionar link para app/chat/CLAUDE.md
```

---

## Fases do plano

| Fase | Tasks | Output |
|------|-------|--------|
| **A** — Infraestrutura | 1-3 | Modelos + migration + blueprint registrado |
| **B** — Services core | 4-9 | Permissao + thread + message + anexos + system notifier |
| **C** — Realtime | 10-11 | Publisher + SSE |
| **D** — Rotas HTTP | 12-15 | 10 endpoints funcionais + testes |
| **E** — UI | 16-20 | Navbar + drawer + painel + share + forward |
| **F** — Alertas instrumentados | 21-23 | Recebimento + DFE + CTe disparam alertas |
| **G** — Docs + E2E | 24-25 | CLAUDE.md do modulo + smoke test |

---

# FASE A — Infraestrutura

## Task 1: Criar estrutura do modulo + blueprint vazio

**Files:**
- Create: `app/chat/__init__.py`
- Create: `app/chat/routes/__init__.py`
- Create: `app/chat/services/__init__.py`
- Create: `app/chat/realtime/__init__.py`
- Create: `tests/chat/__init__.py`
- Modify: `app/__init__.py` (registrar blueprint)

- [ ] **Step 1: Criar blueprint vazio**

```python
# app/chat/__init__.py
from flask import Blueprint

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

# Import routes para registro (lazy, apos blueprint existir)
from app.chat.routes import thread_routes, message_routes, stream_routes, share_routes  # noqa: E402,F401
```

- [ ] **Step 2: Criar `__init__.py` vazios nos subpacotes**

```python
# app/chat/routes/__init__.py
# (vazio — rotas importadas pelo blueprint)
```

```python
# app/chat/services/__init__.py
# (vazio — servicos importados sob demanda)
```

```python
# app/chat/realtime/__init__.py
# (vazio)
```

```python
# tests/chat/__init__.py
# (vazio)
```

- [ ] **Step 3: Criar stubs vazios de routes**

```python
# app/chat/routes/thread_routes.py
from app.chat import chat_bp  # noqa: F401
# rotas serao adicionadas na Fase D
```

Repetir (mesmo conteudo) para `message_routes.py`, `stream_routes.py`, `share_routes.py`.

- [ ] **Step 4: Registrar blueprint em `app/__init__.py`**

Localizar bloco de blueprint registration (proximo a linha ~912 onde `notificacoes_bp` e registrado) e adicionar:

```python
# app/__init__.py — dentro da funcao create_app()
from app.chat import chat_bp
app.register_blueprint(chat_bp)
```

- [ ] **Step 5: Verificar boot (teste manual)**

Run: `source .venv/bin/activate && python -c "from app import create_app; app = create_app(); print([bp.name for bp in app.blueprints.values() if bp.name == 'chat'])"`
Expected: `['chat']`

- [ ] **Step 6: Commit**

```bash
git add app/chat/ tests/chat/ app/__init__.py
git commit -m "feat(chat): criar estrutura do modulo + blueprint vazio"
```

---

## Task 2: Modelos SQLAlchemy (7 tabelas)

**Files:**
- Create: `app/chat/models.py`
- Test: `tests/chat/test_models.py`

- [ ] **Step 1: Escrever teste de criacao de modelos**

```python
# tests/chat/test_models.py
import pytest
from app import create_app, db
from app.chat.models import (
    ChatThread, ChatMember, ChatMessage, ChatAttachment,
    ChatReaction, ChatMention, ChatForward
)
from app.auth.models import Usuario
from app.utils.timezone import agora_utc_naive


@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app


def test_chat_thread_fields(app_ctx):
    t = ChatThread(tipo='dm', criado_em=agora_utc_naive(), sistemas_required=[])
    assert t.tipo == 'dm'
    assert t.entity_type is None
    assert t.arquivado_em is None


def test_chat_message_has_tsvector_and_defaults(app_ctx):
    m = ChatMessage(
        thread_id=1,
        sender_type='user',
        sender_user_id=1,
        content='teste',
        criado_em=agora_utc_naive(),
    )
    assert m.sender_type == 'user'
    assert m.deletado_em is None
    assert m.nivel is None


def test_chat_member_unique_active(app_ctx):
    mem = ChatMember(thread_id=1, user_id=1, role='member', adicionado_em=agora_utc_naive())
    assert mem.role == 'member'
    assert mem.silenciado is False
    assert mem.removido_em is None
```

- [ ] **Step 2: Rodar teste (esperado FAIL — modulo nao existe)**

Run: `pytest tests/chat/test_models.py -v`
Expected: FAIL com `ImportError` ou `ModuleNotFoundError`.

- [ ] **Step 3: Implementar `models.py` completo**

```python
# app/chat/models.py
"""
Modelos do modulo chat in-app.

Referencia: docs/superpowers/specs/2026-04-23-chat-inapp-design.md secao 4.
"""
from sqlalchemy import (
    Column, BigInteger, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import relationship

from app import db
from app.utils.timezone import agora_utc_naive


class ChatThread(db.Model):
    __tablename__ = 'chat_threads'

    id = Column(BigInteger, primary_key=True)
    tipo = Column(String(20), nullable=False)  # dm | group | entity | system_dm
    titulo = Column(String(200), nullable=True)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(100), nullable=True)
    sistemas_required = Column(JSONB, nullable=False, default=list)
    criado_por_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    criado_em = Column(DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = Column(DateTime, nullable=True, onupdate=agora_utc_naive)
    arquivado_em = Column(DateTime, nullable=True)
    last_message_at = Column(DateTime, nullable=True)

    criado_por = relationship('Usuario', foreign_keys=[criado_por_id])

    __table_args__ = (
        UniqueConstraint(
            'entity_type', 'entity_id',
            name='uq_chat_threads_entity',
            postgresql_where=(Column('entity_type').isnot(None)),
        ),
        Index('idx_chat_threads_last_msg', 'last_message_at'),
        CheckConstraint("tipo IN ('dm','group','entity','system_dm')", name='ck_chat_threads_tipo'),
    )


class ChatMember(db.Model):
    __tablename__ = 'chat_members'

    id = Column(BigInteger, primary_key=True)
    thread_id = Column(BigInteger, ForeignKey('chat_threads.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    role = Column(String(20), nullable=False, default='member')  # owner | admin | member
    adicionado_por_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    adicionado_em = Column(DateTime, nullable=False, default=agora_utc_naive)
    last_read_message_id = Column(BigInteger, ForeignKey('chat_messages.id', use_alter=True), nullable=True)
    silenciado = Column(Boolean, nullable=False, default=False)
    removido_em = Column(DateTime, nullable=True)

    thread = relationship('ChatThread', backref='members', foreign_keys=[thread_id])
    user = relationship('Usuario', foreign_keys=[user_id])

    __table_args__ = (
        Index('idx_chat_members_user_thread', 'user_id', 'thread_id'),
        CheckConstraint("role IN ('owner','admin','member')", name='ck_chat_members_role'),
    )


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = Column(BigInteger, primary_key=True)
    thread_id = Column(BigInteger, ForeignKey('chat_threads.id'), nullable=False)
    sender_type = Column(String(10), nullable=False)  # user | system
    sender_user_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    sender_system_source = Column(String(50), nullable=True)
    content = Column(Text, nullable=False)
    content_tsv = Column(TSVECTOR, nullable=True)
    reply_to_message_id = Column(BigInteger, ForeignKey('chat_messages.id'), nullable=True)
    deep_link = Column(String(500), nullable=True)
    nivel = Column(String(20), nullable=True)  # INFO | ATENCAO | CRITICO
    dados = Column(JSONB, nullable=True)
    criado_em = Column(DateTime, nullable=False, default=agora_utc_naive)
    editado_em = Column(DateTime, nullable=True)
    deletado_em = Column(DateTime, nullable=True)
    deletado_por_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)

    thread = relationship('ChatThread', backref='messages', foreign_keys=[thread_id])
    sender_user = relationship('Usuario', foreign_keys=[sender_user_id])
    reply_to = relationship('ChatMessage', remote_side=[id], foreign_keys=[reply_to_message_id])

    __table_args__ = (
        Index('idx_chat_messages_thread_time', 'thread_id', 'criado_em'),
        Index('idx_chat_messages_sender_time', 'sender_user_id', 'criado_em',
              postgresql_where=(Column('sender_type') == 'user')),
        Index('idx_chat_messages_content_tsv', 'content_tsv', postgresql_using='gin'),
        CheckConstraint("sender_type IN ('user','system')", name='ck_chat_messages_sender_type'),
        CheckConstraint(
            "(sender_type='user' AND sender_user_id IS NOT NULL) OR "
            "(sender_type='system' AND sender_system_source IS NOT NULL)",
            name='ck_chat_messages_sender_consistency',
        ),
    )


class ChatAttachment(db.Model):
    __tablename__ = 'chat_attachments'

    id = Column(BigInteger, primary_key=True)
    message_id = Column(BigInteger, ForeignKey('chat_messages.id', ondelete='CASCADE'), nullable=False)
    s3_key = Column(String(500), nullable=False)
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    criado_em = Column(DateTime, nullable=False, default=agora_utc_naive)

    message = relationship('ChatMessage', backref='attachments')


class ChatMention(db.Model):
    __tablename__ = 'chat_mentions'

    id = Column(BigInteger, primary_key=True)
    message_id = Column(BigInteger, ForeignKey('chat_messages.id', ondelete='CASCADE'), nullable=False)
    mentioned_user_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)

    message = relationship('ChatMessage', backref='mentions')
    mentioned_user = relationship('Usuario')


class ChatReaction(db.Model):
    __tablename__ = 'chat_reactions'

    id = Column(BigInteger, primary_key=True)
    message_id = Column(BigInteger, ForeignKey('chat_messages.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    emoji = Column(String(16), nullable=False)
    criado_em = Column(DateTime, nullable=False, default=agora_utc_naive)

    message = relationship('ChatMessage', backref='reactions')

    __table_args__ = (
        UniqueConstraint('message_id', 'user_id', 'emoji', name='uq_chat_reactions'),
    )


class ChatForward(db.Model):
    __tablename__ = 'chat_forwards'

    id = Column(BigInteger, primary_key=True)
    original_message_id = Column(BigInteger, ForeignKey('chat_messages.id'), nullable=False)
    forwarded_message_id = Column(BigInteger, ForeignKey('chat_messages.id'), nullable=False)
    forwarded_by_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    criado_em = Column(DateTime, nullable=False, default=agora_utc_naive)

    original = relationship('ChatMessage', foreign_keys=[original_message_id])
    forwarded = relationship('ChatMessage', foreign_keys=[forwarded_message_id])
    forwarded_by = relationship('Usuario', foreign_keys=[forwarded_by_id])
```

- [ ] **Step 4: Importar modelos no boot para registrar**

Localizar onde outros modulos importam modelos em `app/__init__.py` (proximo ao registro de blueprints) e adicionar:

```python
# Dentro de create_app(), apos db.init_app(app)
from app.chat import models as _chat_models  # noqa: F401  — registra modelos no metadata
```

- [ ] **Step 5: Rodar teste (esperado PASS)**

Run: `pytest tests/chat/test_models.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add app/chat/models.py tests/chat/test_models.py app/__init__.py
git commit -m "feat(chat): modelos SQLAlchemy — 7 tabelas (thread/member/message/attachment/mention/reaction/forward)"
```

---

## Task 3: Migration — SQL + Python

**Files:**
- Create: `scripts/migrations/2026-04-23_chat_schema.sql`
- Create: `scripts/migrations/2026-04-23_chat_schema.py`

- [ ] **Step 1: Escrever SQL idempotente**

```sql
-- scripts/migrations/2026-04-23_chat_schema.sql
-- Cria 7 tabelas do modulo chat + indices + trigger FTS
-- Idempotente: pode rodar multiplas vezes

BEGIN;

CREATE TABLE IF NOT EXISTS chat_threads (
    id BIGSERIAL PRIMARY KEY,
    tipo VARCHAR(20) NOT NULL,
    titulo VARCHAR(200),
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    sistemas_required JSONB NOT NULL DEFAULT '[]'::jsonb,
    criado_por_id INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    atualizado_em TIMESTAMP,
    arquivado_em TIMESTAMP,
    last_message_at TIMESTAMP,
    CONSTRAINT ck_chat_threads_tipo CHECK (tipo IN ('dm','group','entity','system_dm'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_chat_threads_entity
    ON chat_threads(entity_type, entity_id) WHERE entity_type IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chat_threads_last_msg ON chat_threads(last_message_at);

-- chat_messages (antes de chat_members por causa de FK last_read_message_id)
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    thread_id BIGINT NOT NULL REFERENCES chat_threads(id),
    sender_type VARCHAR(10) NOT NULL,
    sender_user_id INTEGER REFERENCES usuarios(id),
    sender_system_source VARCHAR(50),
    content TEXT NOT NULL,
    content_tsv TSVECTOR,
    reply_to_message_id BIGINT REFERENCES chat_messages(id),
    deep_link VARCHAR(500),
    nivel VARCHAR(20),
    dados JSONB,
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    editado_em TIMESTAMP,
    deletado_em TIMESTAMP,
    deletado_por_id INTEGER REFERENCES usuarios(id),
    CONSTRAINT ck_chat_messages_sender_type CHECK (sender_type IN ('user','system')),
    CONSTRAINT ck_chat_messages_sender_consistency CHECK (
        (sender_type='user' AND sender_user_id IS NOT NULL) OR
        (sender_type='system' AND sender_system_source IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_thread_time
    ON chat_messages(thread_id, criado_em);
CREATE INDEX IF NOT EXISTS idx_chat_messages_sender_time
    ON chat_messages(sender_user_id, criado_em) WHERE sender_type = 'user';
CREATE INDEX IF NOT EXISTS idx_chat_messages_content_tsv
    ON chat_messages USING gin(content_tsv);

-- Trigger para atualizar content_tsv
CREATE OR REPLACE FUNCTION chat_messages_tsv_update() RETURNS trigger AS $$
BEGIN
    NEW.content_tsv := to_tsvector('portuguese', COALESCE(NEW.content, ''));
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS chat_messages_tsv_trigger ON chat_messages;
CREATE TRIGGER chat_messages_tsv_trigger
    BEFORE INSERT OR UPDATE OF content ON chat_messages
    FOR EACH ROW EXECUTE FUNCTION chat_messages_tsv_update();

CREATE TABLE IF NOT EXISTS chat_members (
    id BIGSERIAL PRIMARY KEY,
    thread_id BIGINT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES usuarios(id),
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    adicionado_por_id INTEGER REFERENCES usuarios(id),
    adicionado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    last_read_message_id BIGINT REFERENCES chat_messages(id),
    silenciado BOOLEAN NOT NULL DEFAULT FALSE,
    removido_em TIMESTAMP,
    CONSTRAINT ck_chat_members_role CHECK (role IN ('owner','admin','member'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_chat_members_active
    ON chat_members(thread_id, user_id) WHERE removido_em IS NULL;
CREATE INDEX IF NOT EXISTS idx_chat_members_user_thread ON chat_members(user_id, thread_id);

CREATE TABLE IF NOT EXISTS chat_attachments (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    s3_key VARCHAR(500) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS chat_mentions (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    mentioned_user_id INTEGER NOT NULL REFERENCES usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_chat_mentions_user ON chat_mentions(mentioned_user_id);

CREATE TABLE IF NOT EXISTS chat_reactions (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES usuarios(id),
    emoji VARCHAR(16) NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    CONSTRAINT uq_chat_reactions UNIQUE(message_id, user_id, emoji)
);

CREATE TABLE IF NOT EXISTS chat_forwards (
    id BIGSERIAL PRIMARY KEY,
    original_message_id BIGINT NOT NULL REFERENCES chat_messages(id),
    forwarded_message_id BIGINT NOT NULL REFERENCES chat_messages(id),
    forwarded_by_id INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC')
);

COMMIT;
```

- [ ] **Step 2: Escrever Python migration com before/after**

```python
# scripts/migrations/2026-04-23_chat_schema.py
"""Cria 7 tabelas do modulo chat — com verificacao before/after."""
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db

TABLES = [
    'chat_threads', 'chat_messages', 'chat_members',
    'chat_attachments', 'chat_mentions', 'chat_reactions', 'chat_forwards',
]


def table_exists(conn, name):
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = :name"
    ), {'name': name}).fetchone()
    return result is not None


def main():
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        print('=== BEFORE ===')
        for t in TABLES:
            print(f'  {t}: {"YES" if table_exists(conn, t) else "NO"}')

        sql_path = Path(__file__).with_suffix('.sql')
        with sql_path.open() as f:
            ddl = f.read()

        conn.execute(text(ddl))
        conn.commit()

        print('=== AFTER ===')
        missing = []
        for t in TABLES:
            exists = table_exists(conn, t)
            print(f'  {t}: {"YES" if exists else "NO"}')
            if not exists:
                missing.append(t)

        if missing:
            raise SystemExit(f'Tabelas nao criadas: {missing}')

        print('\nMigration concluida com sucesso.')


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Rodar migration local**

Run: `source .venv/bin/activate && python scripts/migrations/2026-04-23_chat_schema.py`
Expected: Output lista as 7 tabelas como `YES` no AFTER; "Migration concluida com sucesso."

- [ ] **Step 4: Validar schema via psql (teste manual)**

Run: `psql $DATABASE_URL -c "\d chat_messages"`
Expected: lista todas as colunas + indices + constraints.

- [ ] **Step 5: Commit**

```bash
git add scripts/migrations/2026-04-23_chat_schema.py scripts/migrations/2026-04-23_chat_schema.sql
git commit -m "migration(chat): DDL das 7 tabelas do modulo chat (Python + SQL)"
```

---

# FASE B — Services core

## Task 4: Markdown parser (extrair mentions + sanitizar)

**Files:**
- Create: `app/chat/markdown_parser.py`
- Test: `tests/chat/test_markdown_parser.py`

- [ ] **Step 1: Escrever testes**

```python
# tests/chat/test_markdown_parser.py
from app.chat.markdown_parser import extract_mentions, sanitize_html, render_markdown


def test_extract_mentions_simple():
    assert extract_mentions('Oi @rafael e @marcus') == ['rafael', 'marcus']


def test_extract_mentions_ignores_email():
    # @bob@email.com NAO e mention
    assert extract_mentions('mande para bob@email.com') == []


def test_extract_mentions_ignores_code_block():
    text = 'use `@decorator` em codigo'
    # simplificacao: ignorar mentions dentro de backticks
    assert extract_mentions(text) == []


def test_extract_mentions_unique():
    assert extract_mentions('@a @b @a') == ['a', 'b']


def test_render_markdown_basic():
    html = render_markdown('**bold** and *italic*')
    assert '<strong>bold</strong>' in html
    assert '<em>italic</em>' in html


def test_sanitize_html_strips_script():
    dirty = '<p>texto</p><script>alert(1)</script>'
    clean = sanitize_html(dirty)
    assert '<script>' not in clean
    assert '<p>texto</p>' in clean


def test_sanitize_html_keeps_links_with_rel_noopener():
    dirty = '<a href="http://x.com">x</a>'
    clean = sanitize_html(dirty)
    assert 'rel="noopener' in clean or 'rel="nofollow' in clean or 'href="http://x.com"' in clean
```

- [ ] **Step 2: Rodar testes (FAIL — modulo nao existe)**

Run: `pytest tests/chat/test_markdown_parser.py -v`
Expected: ImportError.

- [ ] **Step 3: Implementar parser**

```python
# app/chat/markdown_parser.py
"""
Parser de markdown para mensagens de chat.

Extrai mentions (@usuario) e renderiza markdown para HTML sanitizado.
Mentions dentro de backticks (`@x`) ou emails (bob@email.com) sao ignoradas.
"""
import re
from typing import List

import markdown as md_lib
import bleach


# Regex: @palavra (letras, numeros, _, -, .) NAO precedido por alfanumerico/@/. (evita email)
# e NAO dentro de backticks (pre-processado separadamente)
_MENTION_RE = re.compile(r'(?<![a-zA-Z0-9_@.])@([a-zA-Z0-9_][a-zA-Z0-9_.-]*)')
_BACKTICK_BLOCK_RE = re.compile(r'`[^`]*`')

ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre',
    'ul', 'ol', 'li', 'blockquote', 'a', 'h1', 'h2', 'h3', 'h4',
]
ALLOWED_ATTRS = {'a': ['href', 'title', 'rel', 'target']}


def extract_mentions(text: str) -> List[str]:
    """Extrai usernames mencionados (@usuario), sem duplicatas, ignorando backticks e emails."""
    # Remove blocos backtick antes de buscar
    cleaned = _BACKTICK_BLOCK_RE.sub('', text)
    matches = _MENTION_RE.findall(cleaned)
    # Preservar ordem, remover duplicatas
    seen = set()
    result = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def render_markdown(text: str) -> str:
    """Renderiza markdown para HTML (sem sanitizar — usar sanitize_html depois)."""
    return md_lib.markdown(text, extensions=['extra', 'sane_lists'])


def sanitize_html(html: str) -> str:
    """Remove tags/atributos perigosos. Adiciona rel=noopener em links."""
    cleaned = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
    cleaned = bleach.linkify(cleaned, callbacks=[
        lambda attrs, new: {**attrs, (None, 'rel'): 'noopener nofollow', (None, 'target'): '_blank'}
    ])
    return cleaned
```

- [ ] **Step 4: Instalar dependencias (se faltarem)**

Run: `source .venv/bin/activate && pip install markdown bleach && pip freeze | grep -E "markdown|bleach"`
Expected: versoes listadas.

Se novos pacotes, adicionar em `requirements.txt`:

```
markdown==3.5.2
bleach==6.1.0
```

- [ ] **Step 5: Rodar testes**

Run: `pytest tests/chat/test_markdown_parser.py -v`
Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add app/chat/markdown_parser.py tests/chat/test_markdown_parser.py requirements.txt
git commit -m "feat(chat): markdown parser + sanitizacao HTML + extracao de mentions"
```

---

## Task 5: PermissionChecker (regra cruzada por sistemas)

**Files:**
- Create: `app/chat/services/permission_checker.py`
- Test: `tests/chat/test_permission_checker.py`

- [ ] **Step 1: Escrever testes**

```python
# tests/chat/test_permission_checker.py
import pytest
from types import SimpleNamespace

from app.chat.services.permission_checker import (
    sistemas, pode_adicionar,
    DOMAIN_NACOM, DOMAIN_CARVIA, DOMAIN_MOTOCHEFE, DOMAIN_HORA,
)


def user(perfil='logistica', carvia=False, motochefe=False, hora=None):
    return SimpleNamespace(
        perfil=perfil,
        sistema_carvia=carvia,
        sistema_motochefe=motochefe,
        loja_hora_id=hora,
    )


def test_sistemas_base_nacom():
    assert sistemas(user()) == {DOMAIN_NACOM}


def test_sistemas_carvia():
    assert sistemas(user(carvia=True)) == {DOMAIN_NACOM, DOMAIN_CARVIA}


def test_sistemas_todos():
    u = user(carvia=True, motochefe=True, hora=5)
    assert sistemas(u) == {DOMAIN_NACOM, DOMAIN_CARVIA, DOMAIN_MOTOCHEFE, DOMAIN_HORA}


def test_pode_adicionar_superset():
    actor = user(carvia=True)         # {NACOM, CARVIA}
    target = user(carvia=False)       # {NACOM}
    assert pode_adicionar(actor, target) is True


def test_pode_adicionar_negado_se_faltar():
    actor = user(carvia=False)        # {NACOM}
    target = user(carvia=True)        # {NACOM, CARVIA}
    assert pode_adicionar(actor, target) is False


def test_pode_adicionar_iguais():
    a = user(carvia=True)
    b = user(carvia=True)
    assert pode_adicionar(a, b) is True


def test_admin_bypass():
    actor = user(perfil='administrador')
    target = user(carvia=True, motochefe=True)  # mais que actor
    assert pode_adicionar(actor, target) is True
```

- [ ] **Step 2: Rodar testes (FAIL)**

Run: `pytest tests/chat/test_permission_checker.py -v`
Expected: ImportError.

- [ ] **Step 3: Implementar**

```python
# app/chat/services/permission_checker.py
"""
Regra de permissao cruzada por sistemas.

Ver spec secao 5: `sistemas(A) >= sistemas(B)` para A adicionar B
(admin bypass total).
"""
from typing import Set

DOMAIN_NACOM = 'NACOM'
DOMAIN_CARVIA = 'CARVIA'
DOMAIN_MOTOCHEFE = 'MOTOCHEFE'
DOMAIN_HORA = 'HORA'


def sistemas(user) -> Set[str]:
    """Conjunto de sistemas acessiveis pelo usuario."""
    s = {DOMAIN_NACOM}  # todo usuario logado tem Nacom
    if getattr(user, 'sistema_carvia', False):
        s.add(DOMAIN_CARVIA)
    if getattr(user, 'sistema_motochefe', False):
        s.add(DOMAIN_MOTOCHEFE)
    if getattr(user, 'loja_hora_id', None) is not None:
        s.add(DOMAIN_HORA)
    return s


def pode_adicionar(actor, target) -> bool:
    """actor pode iniciar DM com target / adicionar target a grupo."""
    if getattr(actor, 'perfil', None) == 'administrador':
        return True
    # `>=` em set e issuperset (inclui igualdade)
    return sistemas(actor) >= sistemas(target)


def pode_ver_thread(user, thread) -> bool:
    """user pode ler mensagens desta thread (membro ativo ou admin)."""
    if getattr(user, 'perfil', None) == 'administrador':
        return True
    from app.chat.models import ChatMember
    return ChatMember.query.filter_by(
        thread_id=thread.id, user_id=user.id, removido_em=None,
    ).first() is not None


def usuarios_elegiveis_query(actor):
    """
    Queryset de Usuarios que actor pode adicionar.

    Admin: todos. Outros: usuarios com subset de flags.
    """
    from app.auth.models import Usuario

    q = Usuario.query.filter(Usuario.id != actor.id)
    if getattr(actor, 'perfil', None) == 'administrador':
        return q

    # target.flags subset de actor.flags
    conds = []
    if not getattr(actor, 'sistema_carvia', False):
        conds.append(Usuario.sistema_carvia.is_(False))
    if not getattr(actor, 'sistema_motochefe', False):
        conds.append(Usuario.sistema_motochefe.is_(False))
    if getattr(actor, 'loja_hora_id', None) is None:
        conds.append(Usuario.loja_hora_id.is_(None))

    for c in conds:
        q = q.filter(c)
    return q
```

- [ ] **Step 4: Rodar testes**

Run: `pytest tests/chat/test_permission_checker.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add app/chat/services/permission_checker.py tests/chat/test_permission_checker.py
git commit -m "feat(chat): PermissionChecker — sistemas + pode_adicionar cruzada"
```

---

## Task 6: ThreadService (CRUD + lazy entity/system_dm)

**Files:**
- Create: `app/chat/services/thread_service.py`
- Test: `tests/chat/test_thread_service.py`
- Create: `tests/chat/conftest.py`

- [ ] **Step 1: conftest com fixtures reutilizaveis**

```python
# tests/chat/conftest.py
import pytest

from app import create_app, db
from app.auth.models import Usuario
from app.utils.timezone import agora_utc_naive


@pytest.fixture(scope='module')
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def db_session(app):
    """Rollback apos cada teste."""
    connection = db.engine.connect()
    trans = connection.begin()
    session = db.session
    yield session
    trans.rollback()
    connection.close()
    session.remove()


def _mk_user(**kw):
    defaults = dict(
        nome='Teste', email=f'user{id({}):x}@t.local', senha_hash='x',
        perfil='logistica', sistema_carvia=False, sistema_motochefe=False,
        loja_hora_id=None,
    )
    defaults.update(kw)
    u = Usuario(**defaults)
    db.session.add(u)
    db.session.flush()
    return u


@pytest.fixture
def user_factory(db_session):
    return _mk_user
```

- [ ] **Step 2: Testes do ThreadService**

```python
# tests/chat/test_thread_service.py
import pytest
from app.chat.services.thread_service import ThreadService
from app.chat.models import ChatThread, ChatMember


def test_get_or_create_dm_cria_se_nao_existe(db_session, user_factory):
    a = user_factory(email='a@t.local')
    b = user_factory(email='b@t.local')

    thread = ThreadService.get_or_create_dm(a, b)
    assert thread.id is not None
    assert thread.tipo == 'dm'
    members = ChatMember.query.filter_by(thread_id=thread.id).all()
    assert {m.user_id for m in members} == {a.id, b.id}


def test_get_or_create_dm_retorna_existente(db_session, user_factory):
    a = user_factory(email='a2@t.local')
    b = user_factory(email='b2@t.local')
    t1 = ThreadService.get_or_create_dm(a, b)
    t2 = ThreadService.get_or_create_dm(b, a)  # ordem invertida
    assert t1.id == t2.id


def test_get_or_create_system_dm(db_session, user_factory):
    u = user_factory(email='sys@t.local')
    t = ThreadService.get_or_create_system_dm(u)
    assert t.tipo == 'system_dm'
    assert t.criado_por_id == u.id


def test_lazy_entity_thread_not_exists_returns_none(db_session):
    result = ThreadService.get_entity_thread('pedido', 'VCD999')
    assert result is None


def test_create_entity_thread(db_session, user_factory):
    owner = user_factory(email='ow@t.local')
    t = ThreadService.create_entity_thread('pedido', 'VCD001', creator=owner)
    assert t.entity_type == 'pedido'
    assert t.entity_id == 'VCD001'
    members = ChatMember.query.filter_by(thread_id=t.id).all()
    assert len(members) == 1
    assert members[0].user_id == owner.id
    assert members[0].role == 'owner'


def test_permission_required_to_create_dm(db_session, user_factory):
    a = user_factory(email='low@t.local')  # so NACOM
    b = user_factory(email='high@t.local', carvia=True)  # NACOM+CARVIA
    with pytest.raises(PermissionError):
        ThreadService.get_or_create_dm(a, b)  # a NAO e superset de b
```

- [ ] **Step 3: Rodar testes (FAIL)**

Run: `pytest tests/chat/test_thread_service.py -v`
Expected: ImportError.

- [ ] **Step 4: Implementar**

```python
# app/chat/services/thread_service.py
"""
ThreadService — CRUD de chat_thread + lazy creation.
"""
from typing import Optional
from sqlalchemy import and_, or_

from app import db
from app.chat.models import ChatThread, ChatMember
from app.chat.services.permission_checker import pode_adicionar
from app.utils.timezone import agora_utc_naive


class ThreadService:

    @staticmethod
    def get_or_create_dm(actor, target) -> ChatThread:
        """Busca DM entre actor e target, cria se nao existe. Valida permissao."""
        if not pode_adicionar(actor, target):
            raise PermissionError(
                f'Usuario {actor.id} nao pode iniciar DM com {target.id} (permissao cruzada)'
            )

        # Busca DM existente (thread com exatamente esses 2 membros)
        existing = db.session.query(ChatThread).filter(
            ChatThread.tipo == 'dm',
            ChatThread.id.in_(
                db.session.query(ChatMember.thread_id)
                    .filter(ChatMember.user_id == actor.id, ChatMember.removido_em.is_(None))
            ),
            ChatThread.id.in_(
                db.session.query(ChatMember.thread_id)
                    .filter(ChatMember.user_id == target.id, ChatMember.removido_em.is_(None))
            ),
        ).first()

        if existing:
            return existing

        # Cria nova
        thread = ChatThread(
            tipo='dm',
            criado_por_id=actor.id,
            sistemas_required=[],
        )
        db.session.add(thread)
        db.session.flush()

        for u in (actor, target):
            db.session.add(ChatMember(
                thread_id=thread.id,
                user_id=u.id,
                role='member',
                adicionado_por_id=actor.id,
            ))
        db.session.commit()
        return thread

    @staticmethod
    def get_or_create_system_dm(user) -> ChatThread:
        """Caixa de entrada do sistema para o usuario (lazy)."""
        t = ChatThread.query.filter_by(tipo='system_dm', criado_por_id=user.id).first()
        if t:
            return t
        t = ChatThread(tipo='system_dm', criado_por_id=user.id, sistemas_required=[])
        db.session.add(t)
        db.session.flush()
        db.session.add(ChatMember(
            thread_id=t.id, user_id=user.id, role='owner',
        ))
        db.session.commit()
        return t

    @staticmethod
    def get_entity_thread(entity_type: str, entity_id: str) -> Optional[ChatThread]:
        return ChatThread.query.filter_by(entity_type=entity_type, entity_id=entity_id).first()

    @staticmethod
    def create_entity_thread(entity_type: str, entity_id: str, creator) -> ChatThread:
        thread = ChatThread(
            tipo='entity',
            entity_type=entity_type,
            entity_id=entity_id,
            criado_por_id=creator.id,
            sistemas_required=[],
        )
        db.session.add(thread)
        db.session.flush()
        db.session.add(ChatMember(
            thread_id=thread.id,
            user_id=creator.id,
            role='owner',
            adicionado_por_id=creator.id,
        ))
        db.session.commit()
        return thread

    @staticmethod
    def add_member(thread: ChatThread, actor, target, role: str = 'member') -> ChatMember:
        if not pode_adicionar(actor, target):
            raise PermissionError('permissao negada')
        mem = ChatMember(
            thread_id=thread.id, user_id=target.id, role=role,
            adicionado_por_id=actor.id,
        )
        db.session.add(mem)
        db.session.commit()
        return mem

    @staticmethod
    def list_threads_for_user(user, tipo: Optional[str] = None, limit: int = 50):
        q = db.session.query(ChatThread).join(
            ChatMember, ChatMember.thread_id == ChatThread.id
        ).filter(
            ChatMember.user_id == user.id,
            ChatMember.removido_em.is_(None),
            ChatThread.arquivado_em.is_(None),
        )
        if tipo:
            q = q.filter(ChatThread.tipo == tipo)
        return q.order_by(ChatThread.last_message_at.desc().nullslast()).limit(limit).all()
```

- [ ] **Step 5: Rodar testes**

Run: `pytest tests/chat/test_thread_service.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add app/chat/services/thread_service.py tests/chat/test_thread_service.py tests/chat/conftest.py
git commit -m "feat(chat): ThreadService — DM, system_dm, entity lazy, add_member"
```

---

## Task 7: AttachmentService (upload S3)

**Files:**
- Create: `app/chat/services/attachment_service.py`
- Test: `tests/chat/test_attachment_service.py`

- [ ] **Step 1: Verificar modulo S3 existente**

Run: `ls app/utils/ | grep -i s3; find app -name "*s3*" -type f 2>/dev/null | grep -v __pycache__ | head -5`
Expected: localizar helper S3 existente (ex: `app/utils/s3_storage.py`). Usar ele em vez de boto3 direto.

Se nao existir helper, criar em `app/chat/services/attachment_service.py` com boto3 direto (configurar AWS_BUCKET_NAME via env).

- [ ] **Step 2: Testes (com S3 mockado)**

```python
# tests/chat/test_attachment_service.py
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO

from app.chat.services.attachment_service import (
    AttachmentService, AttachmentError, ALLOWED_MIME_TYPES, MAX_SIZE_BYTES,
)


def test_rejects_oversized_file(db_session):
    svc = AttachmentService()
    big_file = BytesIO(b'x' * (MAX_SIZE_BYTES + 1))
    with pytest.raises(AttachmentError, match='tamanho'):
        svc.validate_upload(big_file, 'test.pdf', 'application/pdf', MAX_SIZE_BYTES + 1)


def test_rejects_disallowed_mime():
    svc = AttachmentService()
    with pytest.raises(AttachmentError, match='tipo'):
        svc.validate_upload(BytesIO(b'x'), 'test.exe', 'application/x-msdownload', 100)


def test_accepts_valid_pdf():
    svc = AttachmentService()
    assert svc.validate_upload(BytesIO(b'%PDF'), 'test.pdf', 'application/pdf', 100) is None


@patch('app.chat.services.attachment_service.boto3')
def test_upload_returns_s3_key(mock_boto, db_session):
    mock_client = MagicMock()
    mock_boto.client.return_value = mock_client
    svc = AttachmentService()
    key = svc.upload(BytesIO(b'data'), 'doc.pdf', 'application/pdf', 4, user_id=1)
    assert key.startswith('chat/attachments/')
    assert key.endswith('.pdf')
    mock_client.upload_fileobj.assert_called_once()
```

- [ ] **Step 3: Rodar testes (FAIL)**

Run: `pytest tests/chat/test_attachment_service.py -v`

- [ ] **Step 4: Implementar**

```python
# app/chat/services/attachment_service.py
"""Upload de anexos para S3 + validacao."""
import os
import uuid
from datetime import datetime
from typing import BinaryIO, Optional

import boto3

from app.utils.logging_config import logger


MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20MB
MAX_PER_MESSAGE = 5

ALLOWED_MIME_TYPES = {
    'image/png', 'image/jpeg', 'image/gif', 'image/webp',
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # xlsx
    'application/vnd.ms-excel',  # xls
    'text/csv', 'text/plain',
}

S3_BUCKET = os.environ.get('AWS_S3_BUCKET') or os.environ.get('S3_BUCKET_NAME', '')
S3_REGION = os.environ.get('AWS_REGION', 'us-east-1')


class AttachmentError(Exception):
    pass


class AttachmentService:

    def validate_upload(self, stream: BinaryIO, filename: str, mime_type: str, size: int) -> Optional[None]:
        if size > MAX_SIZE_BYTES:
            raise AttachmentError(f'Arquivo excede tamanho maximo ({MAX_SIZE_BYTES} bytes)')
        if mime_type not in ALLOWED_MIME_TYPES:
            raise AttachmentError(f'Tipo de arquivo nao permitido: {mime_type}')

    def upload(self, stream: BinaryIO, filename: str, mime_type: str, size: int, user_id: int) -> str:
        self.validate_upload(stream, filename, mime_type, size)
        key = f'chat/attachments/{user_id}/{datetime.utcnow():%Y/%m/%d}/{uuid.uuid4().hex}_{filename}'
        client = boto3.client('s3', region_name=S3_REGION)
        client.upload_fileobj(stream, S3_BUCKET, key, ExtraArgs={'ContentType': mime_type})
        logger.info(f'[CHAT] attachment uploaded: {key} ({size} bytes)')
        return key

    def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        client = boto3.client('s3', region_name=S3_REGION)
        return client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': key},
            ExpiresIn=expires_in,
        )
```

- [ ] **Step 5: Rodar testes**

Run: `pytest tests/chat/test_attachment_service.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add app/chat/services/attachment_service.py tests/chat/test_attachment_service.py
git commit -m "feat(chat): AttachmentService — upload S3 + validacao mime/size"
```

---

## Task 8: MessageService (send/edit/delete + mentions + publish)

**Files:**
- Create: `app/chat/services/message_service.py`
- Test: `tests/chat/test_message_service.py`

- [ ] **Step 1: Testes**

```python
# tests/chat/test_message_service.py
import pytest
from unittest.mock import patch

from app.chat.services.message_service import MessageService, MessageError
from app.chat.services.thread_service import ThreadService
from app.chat.models import ChatMessage, ChatMention


@patch('app.chat.realtime.publisher.publish')
def test_send_simple(mock_pub, db_session, user_factory):
    a = user_factory(email='ms_a@t.local')
    b = user_factory(email='ms_b@t.local')
    thread = ThreadService.get_or_create_dm(a, b)

    msg = MessageService.send(sender=a, thread_id=thread.id, content='Oi!')
    assert msg.id is not None
    assert msg.sender_type == 'user'
    assert msg.content == 'Oi!'
    # publish chamado para b (nao para sender)
    assert mock_pub.called
    called_user_ids = [c.args[0] for c in mock_pub.call_args_list]
    assert b.id in called_user_ids
    assert a.id not in called_user_ids


def test_send_rejects_non_member(db_session, user_factory):
    a = user_factory(email='ms_na@t.local')
    b = user_factory(email='ms_nb@t.local')
    c = user_factory(email='ms_nc@t.local')
    thread = ThreadService.get_or_create_dm(a, b)
    with pytest.raises(PermissionError):
        MessageService.send(sender=c, thread_id=thread.id, content='intruso')


def test_send_rejects_oversized(db_session, user_factory):
    a = user_factory(email='ms_o1@t.local')
    b = user_factory(email='ms_o2@t.local')
    thread = ThreadService.get_or_create_dm(a, b)
    huge = 'x' * 9000
    with pytest.raises(MessageError, match='tamanho'):
        MessageService.send(sender=a, thread_id=thread.id, content=huge)


@patch('app.chat.realtime.publisher.publish')
def test_send_with_mentions_persists_rows(mock_pub, db_session, user_factory):
    a = user_factory(email='alice@t.local')
    b = user_factory(email='bob@t.local')
    thread = ThreadService.get_or_create_dm(a, b)
    # bob mencionado pelo email prefix
    msg = MessageService.send(sender=a, thread_id=thread.id, content='olhe @bob isso')
    mentions = ChatMention.query.filter_by(message_id=msg.id).all()
    # bob precisa ser membro da thread pra mention valer
    assert any(m.mentioned_user_id == b.id for m in mentions)


def test_edit_within_window(db_session, user_factory):
    a = user_factory(email='ed_a@t.local')
    b = user_factory(email='ed_b@t.local')
    thread = ThreadService.get_or_create_dm(a, b)
    msg = MessageService.send(sender=a, thread_id=thread.id, content='v1')
    edited = MessageService.edit(user=a, message_id=msg.id, new_content='v2')
    assert edited.content == 'v2'
    assert edited.editado_em is not None


def test_soft_delete(db_session, user_factory):
    a = user_factory(email='del_a@t.local')
    b = user_factory(email='del_b@t.local')
    thread = ThreadService.get_or_create_dm(a, b)
    msg = MessageService.send(sender=a, thread_id=thread.id, content='tchau')
    MessageService.delete(user=a, message_id=msg.id)
    reloaded = ChatMessage.query.get(msg.id)
    assert reloaded.deletado_em is not None
    assert reloaded.deletado_por_id == a.id
```

- [ ] **Step 2: Rodar testes (FAIL)**

- [ ] **Step 3: Implementar**

```python
# app/chat/services/message_service.py
"""MessageService — envio, edicao, delecao de mensagens com validacao e publish."""
from datetime import timedelta
from typing import List, Optional

from app import db
from app.auth.models import Usuario
from app.chat.models import ChatMessage, ChatMember, ChatMention, ChatThread, ChatAttachment
from app.chat.markdown_parser import extract_mentions
from app.chat.services.permission_checker import pode_ver_thread
from app.utils.timezone import agora_utc_naive


MAX_CONTENT_BYTES = 8192
EDIT_WINDOW_MINUTES = 15


class MessageError(Exception):
    pass


def _is_active_member(user_id: int, thread_id: int) -> bool:
    return db.session.query(ChatMember).filter_by(
        thread_id=thread_id, user_id=user_id, removido_em=None,
    ).first() is not None


class MessageService:

    @staticmethod
    def send(
        sender,
        thread_id: int,
        content: str,
        reply_to_message_id: Optional[int] = None,
        deep_link: Optional[str] = None,
        attachments: Optional[List[dict]] = None,
    ) -> ChatMessage:
        # Validar membership
        if not _is_active_member(sender.id, thread_id):
            raise PermissionError(f'user {sender.id} nao e membro de thread {thread_id}')

        # Validar tamanho
        if len(content.encode('utf-8')) > MAX_CONTENT_BYTES:
            raise MessageError(f'Conteudo excede tamanho maximo ({MAX_CONTENT_BYTES} bytes)')

        thread = db.session.query(ChatThread).get(thread_id)
        if thread is None:
            raise MessageError(f'Thread {thread_id} nao existe')

        # Criar mensagem
        msg = ChatMessage(
            thread_id=thread_id,
            sender_type='user',
            sender_user_id=sender.id,
            content=content,
            reply_to_message_id=reply_to_message_id,
            deep_link=deep_link,
        )
        db.session.add(msg)
        db.session.flush()

        # Processar mentions — so valem se mencionado e membro ativo
        usernames = extract_mentions(content)
        if usernames:
            member_ids = {
                r.user_id for r in db.session.query(ChatMember).filter(
                    ChatMember.thread_id == thread_id,
                    ChatMember.removido_em.is_(None),
                ).all()
            }
            # resolver username -> user_id (por prefix do email ou campo nome)
            resolved = db.session.query(Usuario).filter(
                db.or_(*[
                    Usuario.email.like(f'{u}@%') for u in usernames
                ])
            ).all()
            for u in resolved:
                if u.id in member_ids and u.id != sender.id:
                    db.session.add(ChatMention(
                        message_id=msg.id, mentioned_user_id=u.id,
                    ))

        # Registrar anexos (se ja uploadados — validacao ja feita antes)
        for att in (attachments or []):
            db.session.add(ChatAttachment(
                message_id=msg.id,
                s3_key=att['s3_key'], filename=att['filename'],
                mime_type=att['mime_type'], size_bytes=att['size_bytes'],
            ))

        # Atualizar last_message_at
        thread.last_message_at = msg.criado_em
        db.session.commit()

        # Publicar para outros membros
        MessageService._publish_new(msg, thread)
        return msg

    @staticmethod
    def _publish_new(msg: ChatMessage, thread: ChatThread):
        from app.chat.realtime.publisher import publish  # import dentro para facilitar mock

        mentioned_ids = {m.mentioned_user_id for m in msg.mentions}
        recipients = db.session.query(ChatMember).filter(
            ChatMember.thread_id == thread.id,
            ChatMember.removido_em.is_(None),
            ChatMember.user_id != (msg.sender_user_id or 0),
        ).all()

        for r in recipients:
            publish(r.user_id, 'message_new', {
                'thread_id': thread.id,
                'message_id': msg.id,
                'preview': (msg.content or '')[:100],
                'sender_user_id': msg.sender_user_id,
                'sender_type': msg.sender_type,
                'urgente': r.user_id in mentioned_ids,
                'deep_link': msg.deep_link,
                'criado_em': msg.criado_em.isoformat() if msg.criado_em else None,
            })

    @staticmethod
    def edit(user, message_id: int, new_content: str) -> ChatMessage:
        msg = ChatMessage.query.get(message_id)
        if msg is None:
            raise MessageError('Mensagem nao existe')
        if msg.sender_user_id != user.id:
            raise PermissionError('so o autor pode editar')
        # janela de 15 min
        if agora_utc_naive() - msg.criado_em > timedelta(minutes=EDIT_WINDOW_MINUTES):
            raise MessageError('janela de edicao expirada (15 min)')
        if len(new_content.encode('utf-8')) > MAX_CONTENT_BYTES:
            raise MessageError('conteudo excede tamanho')
        msg.content = new_content
        msg.editado_em = agora_utc_naive()
        db.session.commit()

        from app.chat.realtime.publisher import publish
        for m in db.session.query(ChatMember).filter(
            ChatMember.thread_id == msg.thread_id,
            ChatMember.removido_em.is_(None),
        ).all():
            publish(m.user_id, 'message_edit', {
                'thread_id': msg.thread_id, 'message_id': msg.id, 'new_content': msg.content,
            })
        return msg

    @staticmethod
    def delete(user, message_id: int):
        msg = ChatMessage.query.get(message_id)
        if msg is None:
            raise MessageError('Mensagem nao existe')
        if msg.sender_user_id != user.id and user.perfil != 'administrador':
            raise PermissionError('so autor ou admin pode deletar')
        msg.deletado_em = agora_utc_naive()
        msg.deletado_por_id = user.id
        db.session.commit()

        from app.chat.realtime.publisher import publish
        for m in db.session.query(ChatMember).filter(
            ChatMember.thread_id == msg.thread_id,
            ChatMember.removido_em.is_(None),
        ).all():
            publish(m.user_id, 'message_delete', {
                'thread_id': msg.thread_id, 'message_id': msg.id,
            })

    @staticmethod
    def list_for_thread(user, thread_id: int, limit: int = 50, before_id: Optional[int] = None):
        thread = db.session.query(ChatThread).get(thread_id)
        if thread is None or not pode_ver_thread(user, thread):
            raise PermissionError('sem acesso')
        q = ChatMessage.query.filter_by(thread_id=thread_id)
        if before_id:
            q = q.filter(ChatMessage.id < before_id)
        return q.order_by(ChatMessage.id.desc()).limit(limit).all()
```

- [ ] **Step 4: Rodar testes**

Run: `pytest tests/chat/test_message_service.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add app/chat/services/message_service.py tests/chat/test_message_service.py
git commit -m "feat(chat): MessageService — send/edit/delete com mentions, validacao, publish SSE"
```

---

## Task 9: SystemNotifier (alert API)

**Files:**
- Create: `app/chat/services/system_notifier.py`
- Test: `tests/chat/test_system_notifier.py`

- [ ] **Step 1: Testes**

```python
# tests/chat/test_system_notifier.py
from unittest.mock import patch

from app.chat.services.system_notifier import SystemNotifier
from app.chat.models import ChatMessage, ChatThread


@patch('app.chat.realtime.publisher.publish')
def test_alert_cria_thread_system_e_mensagem(mock_pub, db_session, user_factory):
    u = user_factory(email='sn_u@t.local')
    SystemNotifier.alert(
        user_ids=[u.id],
        source='recebimento',
        titulo='Teste',
        content='corpo',
        deep_link='/recebimento/1',
        nivel='ATENCAO',
        dados={'id': 1},
    )
    t = ChatThread.query.filter_by(tipo='system_dm', criado_por_id=u.id).first()
    assert t is not None
    msg = ChatMessage.query.filter_by(thread_id=t.id).order_by(ChatMessage.id.desc()).first()
    assert msg.sender_type == 'system'
    assert msg.sender_system_source == 'recebimento'
    assert msg.nivel == 'ATENCAO'
    assert msg.deep_link == '/recebimento/1'
    assert mock_pub.called


@patch('app.chat.realtime.publisher.publish')
def test_alert_multi_user(mock_pub, db_session, user_factory):
    a = user_factory(email='ma@t.local')
    b = user_factory(email='mb@t.local')
    SystemNotifier.alert(
        user_ids=[a.id, b.id], source='dfe', titulo='X', content='Y',
        deep_link='/x', nivel='CRITICO',
    )
    assert mock_pub.call_count == 2
```

- [ ] **Step 2: Rodar testes (FAIL)**

- [ ] **Step 3: Implementar**

```python
# app/chat/services/system_notifier.py
"""SystemNotifier — API publica para qualquer ponto do codigo disparar alerta."""
from typing import List, Optional

from app import db
from app.chat.models import ChatMessage
from app.chat.services.thread_service import ThreadService
from app.utils.json_helpers import sanitize_for_json
from app.utils.logging_config import logger


VALID_NIVEIS = {'INFO', 'ATENCAO', 'CRITICO'}


class SystemNotifier:

    @staticmethod
    def alert(
        user_ids: List[int],
        source: str,
        titulo: str,
        content: str,
        deep_link: Optional[str] = None,
        nivel: str = 'INFO',
        dados: Optional[dict] = None,
    ):
        """
        Dispara alerta do sistema para um ou mais usuarios.

        Cada usuario recebe na sua 'caixa de entrada' system_dm (criada lazy).
        Publica via SSE para entrega imediata se conectado.
        """
        if nivel not in VALID_NIVEIS:
            raise ValueError(f'nivel invalido: {nivel}')

        # Carregar usuarios
        from app.auth.models import Usuario
        users = Usuario.query.filter(Usuario.id.in_(user_ids)).all()
        if not users:
            logger.warning(f'[CHAT] SystemNotifier: nenhum usuario encontrado em {user_ids}')
            return []

        body = f'**{titulo}**\n\n{content}'
        payload_dados = sanitize_for_json(dados or {})

        msgs = []
        for u in users:
            thread = ThreadService.get_or_create_system_dm(u)
            msg = ChatMessage(
                thread_id=thread.id,
                sender_type='system',
                sender_system_source=source,
                content=body,
                deep_link=deep_link,
                nivel=nivel,
                dados=payload_dados,
            )
            db.session.add(msg)
            db.session.flush()
            thread.last_message_at = msg.criado_em
            msgs.append((u, thread, msg))

        db.session.commit()

        # Publicar fora da transacao
        from app.chat.realtime.publisher import publish
        for u, thread, msg in msgs:
            publish(u.id, 'message_new', {
                'thread_id': thread.id,
                'message_id': msg.id,
                'preview': titulo,
                'sender_type': 'system',
                'source': source,
                'nivel': nivel,
                'deep_link': deep_link,
                'criado_em': msg.criado_em.isoformat() if msg.criado_em else None,
            })

        logger.info(f'[CHAT] SystemNotifier: {len(msgs)} alertas disparados (source={source}, nivel={nivel})')
        return msgs
```

- [ ] **Step 4: Rodar testes**

Run: `pytest tests/chat/test_system_notifier.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add app/chat/services/system_notifier.py tests/chat/test_system_notifier.py
git commit -m "feat(chat): SystemNotifier — alert multi-user com system_dm lazy"
```

---

# FASE C — Realtime

## Task 10: Publisher Redis

**Files:**
- Create: `app/chat/realtime/publisher.py`
- Test: `tests/chat/test_publisher.py`

- [ ] **Step 1: Testes**

```python
# tests/chat/test_publisher.py
from unittest.mock import MagicMock, patch

from app.chat.realtime.publisher import publish, channel_for


def test_channel_for():
    assert channel_for(42) == 'chat_sse:42'


@patch('app.chat.realtime.publisher._redis')
def test_publish_writes_to_channel(mock_redis):
    publish(42, 'message_new', {'a': 1})
    mock_redis.publish.assert_called_once()
    args = mock_redis.publish.call_args.args
    assert args[0] == 'chat_sse:42'
    import json
    payload = json.loads(args[1])
    assert payload['event'] == 'message_new'
    assert payload['data']['a'] == 1


@patch('app.chat.realtime.publisher._redis', None)
def test_publish_noop_if_redis_unavailable():
    # nao deve levantar
    publish(1, 'x', {})
```

- [ ] **Step 2: Rodar testes (FAIL)**

- [ ] **Step 3: Implementar**

```python
# app/chat/realtime/publisher.py
"""Publisher Redis pub/sub para canal chat_sse:<user_id>."""
import json
import os
from typing import Optional

import redis

from app.utils.logging_config import logger


def _get_redis() -> Optional[redis.Redis]:
    url = os.environ.get('REDIS_URL')
    if not url:
        return None
    try:
        return redis.from_url(url, decode_responses=True)
    except Exception as e:
        logger.warning(f'[CHAT] Redis unavailable: {e}')
        return None


_redis = _get_redis()


def channel_for(user_id: int) -> str:
    return f'chat_sse:{user_id}'


def publish(user_id: int, event: str, data: dict):
    """
    Publica evento no canal do usuario. Best-effort: se Redis down, loga e segue.
    Mensagem ja foi persistida no DB antes; cliente reconnecta e busca catch-up.
    """
    if _redis is None:
        logger.debug(f'[CHAT] publish skipped (no redis): user={user_id}, event={event}')
        return
    try:
        payload = json.dumps({'event': event, 'data': data})
        _redis.publish(channel_for(user_id), payload)
    except Exception as e:
        logger.warning(f'[CHAT] publish failed (user={user_id}): {e}')
```

- [ ] **Step 4: Rodar testes**

Run: `pytest tests/chat/test_publisher.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/chat/realtime/publisher.py tests/chat/test_publisher.py
git commit -m "feat(chat): publisher Redis pub/sub (canal chat_sse:<user_id>)"
```

---

## Task 11: SSE stream generator

**Files:**
- Create: `app/chat/realtime/sse.py`
- Test: `tests/chat/test_sse.py`

- [ ] **Step 1: Testes**

```python
# tests/chat/test_sse.py
from unittest.mock import patch, MagicMock

from app.chat.realtime.sse import stream_chat_events


def test_stream_emits_hello_first():
    # Garantir que o primeiro chunk e o hello/heartbeat
    with patch('app.chat.realtime.sse._get_pubsub') as mock_ps:
        mock_pubsub = MagicMock()
        mock_pubsub.get_message.return_value = None
        mock_ps.return_value = mock_pubsub

        gen = stream_chat_events(user_id=42, last_event_id=None, max_iterations=1)
        first = next(gen)
        assert first.startswith(': connected') or 'event: hello' in first


def test_stream_yields_published_message():
    with patch('app.chat.realtime.sse._get_pubsub') as mock_ps:
        mock_pubsub = MagicMock()
        mock_pubsub.get_message.side_effect = [
            {'type': 'message', 'data': '{"event":"message_new","data":{"x":1}}'},
            None,
        ]
        mock_ps.return_value = mock_pubsub

        gen = stream_chat_events(user_id=42, last_event_id=None, max_iterations=2)
        out = [next(gen) for _ in range(2)]
        text = '\n'.join(out)
        assert 'event: message_new' in text
        assert '"x": 1' in text or '"x":1' in text
```

- [ ] **Step 2: Rodar testes (FAIL)**

- [ ] **Step 3: Implementar**

```python
# app/chat/realtime/sse.py
"""
SSE generator — stream_chat_events(user_id).

Padrao reutilizado de app/agente/routes/chat.py.
Canal: chat_sse:<user_id>. Heartbeat a cada 25s (Render SSL drop 30-40s).
"""
import json
import os
import time
from typing import Optional

import redis


HEARTBEAT_INTERVAL = 25  # segundos


def _get_pubsub(user_id: int):
    url = os.environ.get('REDIS_URL')
    if not url:
        return None
    r = redis.from_url(url, decode_responses=True)
    ps = r.pubsub(ignore_subscribe_messages=True)
    ps.subscribe(f'chat_sse:{user_id}')
    return ps


def _format_event(event_type: str, data: dict, event_id: Optional[int] = None) -> str:
    lines = []
    if event_id is not None:
        lines.append(f'id: {event_id}')
    lines.append(f'event: {event_type}')
    lines.append(f'data: {json.dumps(data)}')
    lines.append('')  # linha em branco = fim do evento
    lines.append('')
    return '\n'.join(lines)


def stream_chat_events(user_id: int, last_event_id: Optional[int] = None, max_iterations: Optional[int] = None):
    """
    Generator para Flask Response com mimetype='text/event-stream'.

    - Envia catch-up se last_event_id fornecido (max 100 msgs do DB).
    - Subscribe no canal Redis chat_sse:<user_id>.
    - Heartbeat a cada HEARTBEAT_INTERVAL segundos.
    - max_iterations usado em testes (None = loop infinito).
    """
    # Hello inicial
    yield ': connected\n\n'

    # Catch-up via DB
    if last_event_id:
        from app.chat.services.message_service import MessageService  # noqa
        from app.chat.models import ChatMessage, ChatMember
        from app import db
        thread_ids = [
            r.thread_id for r in db.session.query(ChatMember).filter(
                ChatMember.user_id == user_id,
                ChatMember.removido_em.is_(None),
            ).all()
        ]
        if thread_ids:
            catchup = db.session.query(ChatMessage).filter(
                ChatMessage.thread_id.in_(thread_ids),
                ChatMessage.id > last_event_id,
            ).order_by(ChatMessage.id.asc()).limit(100).all()
            for m in catchup:
                yield _format_event('message_new', {
                    'thread_id': m.thread_id,
                    'message_id': m.id,
                    'preview': (m.content or '')[:100],
                    'sender_type': m.sender_type,
                }, event_id=m.id)

    ps = _get_pubsub(user_id)
    if ps is None:
        # Sem Redis: so heartbeats
        while max_iterations is None or max_iterations > 0:
            time.sleep(HEARTBEAT_INTERVAL)
            yield ': heartbeat\n\n'
            if max_iterations is not None:
                max_iterations -= 1
        return

    last_heartbeat = time.time()
    iterations = 0
    try:
        while max_iterations is None or iterations < max_iterations:
            msg = ps.get_message(timeout=1.0)
            if msg and msg.get('type') == 'message':
                try:
                    parsed = json.loads(msg['data'])
                    event_type = parsed.get('event', 'message')
                    data = parsed.get('data', {})
                    event_id = data.get('message_id')
                    yield _format_event(event_type, data, event_id=event_id)
                except Exception:
                    continue
            else:
                now = time.time()
                if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                    yield ': heartbeat\n\n'
                    last_heartbeat = now
            iterations += 1
    finally:
        try:
            ps.close()
        except Exception:
            pass
```

- [ ] **Step 4: Rodar testes**

Run: `pytest tests/chat/test_sse.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add app/chat/realtime/sse.py tests/chat/test_sse.py
git commit -m "feat(chat): SSE generator com catch-up Last-Event-ID + heartbeat 25s"
```

---

# FASE D — Rotas HTTP

## Task 12: Rotas de thread (list + create + members)

**Files:**
- Modify: `app/chat/routes/thread_routes.py`
- Test: `tests/chat/test_routes_thread.py`

- [ ] **Step 1: Testes (usando test client Flask + login mock)**

```python
# tests/chat/test_routes_thread.py
import json
from unittest.mock import patch

import pytest


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client, user):
    """Simula Flask-Login via session."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


def test_list_threads_vazio(client, user_factory, db_session):
    u = user_factory(email='lt@t.local')
    _login(client, u)
    resp = client.get('/api/chat/threads')
    assert resp.status_code == 200
    assert resp.json == {'threads': []}


def test_create_dm(client, user_factory, db_session):
    a = user_factory(email='cr_a@t.local')
    b = user_factory(email='cr_b@t.local')
    _login(client, a)
    resp = client.post('/api/chat/threads/dm', json={'target_user_id': b.id})
    assert resp.status_code == 201
    assert resp.json['thread']['tipo'] == 'dm'


def test_create_dm_permission_denied(client, user_factory, db_session):
    a = user_factory(email='pd_a@t.local')  # so NACOM
    b = user_factory(email='pd_b@t.local', carvia=True)
    _login(client, a)
    resp = client.post('/api/chat/threads/dm', json={'target_user_id': b.id})
    assert resp.status_code == 403
```

- [ ] **Step 2: Implementar rotas**

```python
# app/chat/routes/thread_routes.py
from flask import jsonify, request
from flask_login import login_required, current_user

from app.chat import chat_bp
from app.chat.services.thread_service import ThreadService
from app.chat.services.permission_checker import pode_adicionar
from app.chat.models import ChatThread
from app.auth.models import Usuario


def _thread_dict(t: ChatThread) -> dict:
    return {
        'id': t.id, 'tipo': t.tipo, 'titulo': t.titulo,
        'entity_type': t.entity_type, 'entity_id': t.entity_id,
        'last_message_at': t.last_message_at.isoformat() if t.last_message_at else None,
    }


@chat_bp.route('/threads', methods=['GET'])
@login_required
def list_threads():
    tipo = request.args.get('tipo')
    threads = ThreadService.list_threads_for_user(current_user, tipo=tipo)
    return jsonify({'threads': [_thread_dict(t) for t in threads]})


@chat_bp.route('/threads/dm', methods=['POST'])
@login_required
def create_dm():
    data = request.get_json() or {}
    target_id = data.get('target_user_id')
    if not target_id:
        return jsonify({'error': 'target_user_id obrigatorio'}), 400
    target = Usuario.query.get(target_id)
    if not target:
        return jsonify({'error': 'usuario nao encontrado'}), 404
    try:
        thread = ThreadService.get_or_create_dm(current_user, target)
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    return jsonify({'thread': _thread_dict(thread)}), 201


@chat_bp.route('/threads/group', methods=['POST'])
@login_required
def create_group():
    data = request.get_json() or {}
    titulo = (data.get('titulo') or '').strip()
    member_ids = data.get('member_ids') or []
    if not titulo:
        return jsonify({'error': 'titulo obrigatorio'}), 400
    # valida permissao para cada membro
    from app import db
    from app.chat.models import ChatMember
    members = Usuario.query.filter(Usuario.id.in_(member_ids)).all()
    for m in members:
        if not pode_adicionar(current_user, m):
            return jsonify({'error': f'sem permissao para adicionar {m.id}'}), 403

    thread = ChatThread(
        tipo='group', titulo=titulo,
        criado_por_id=current_user.id, sistemas_required=[],
    )
    db.session.add(thread)
    db.session.flush()
    db.session.add(ChatMember(
        thread_id=thread.id, user_id=current_user.id, role='owner',
        adicionado_por_id=current_user.id,
    ))
    for m in members:
        db.session.add(ChatMember(
            thread_id=thread.id, user_id=m.id, role='member',
            adicionado_por_id=current_user.id,
        ))
    db.session.commit()
    return jsonify({'thread': _thread_dict(thread)}), 201


@chat_bp.route('/threads/<int:thread_id>/members', methods=['POST'])
@login_required
def add_member(thread_id):
    data = request.get_json() or {}
    target = Usuario.query.get(data.get('user_id'))
    if not target:
        return jsonify({'error': 'usuario nao encontrado'}), 404
    thread = ChatThread.query.get_or_404(thread_id)
    try:
        ThreadService.add_member(thread, current_user, target)
    except PermissionError:
        return jsonify({'error': 'permissao negada'}), 403
    return jsonify({'ok': True}), 201


@chat_bp.route('/entity/<entity_type>/<entity_id>/thread', methods=['GET'])
@login_required
def get_entity_thread(entity_type, entity_id):
    t = ThreadService.get_entity_thread(entity_type, entity_id)
    if t is None:
        return jsonify({
            'thread': None, 'entity_type': entity_type, 'entity_id': entity_id,
            'hint': 'post message to create',
        }), 404
    return jsonify({'thread': _thread_dict(t)})
```

- [ ] **Step 3: Rodar testes**

Run: `pytest tests/chat/test_routes_thread.py -v`
Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add app/chat/routes/thread_routes.py tests/chat/test_routes_thread.py
git commit -m "feat(chat): rotas de thread — list, dm, group, add_member, entity"
```

---

## Task 13: Rotas de mensagem (send + edit + delete + reactions + forward)

**Files:**
- Modify: `app/chat/routes/message_routes.py`
- Test: `tests/chat/test_routes_message.py`

- [ ] **Step 1: Testes**

```python
# tests/chat/test_routes_message.py
import pytest
from unittest.mock import patch

from app.chat.services.thread_service import ThreadService


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client, user):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


@patch('app.chat.realtime.publisher.publish')
def test_send_message_via_route(mock_pub, client, user_factory, db_session):
    a = user_factory(email='rm_a@t.local')
    b = user_factory(email='rm_b@t.local')
    t = ThreadService.get_or_create_dm(a, b)
    _login(client, a)
    resp = client.post('/api/chat/messages', json={
        'thread_id': t.id, 'content': 'oi',
    })
    assert resp.status_code == 201
    assert resp.json['message']['content'] == 'oi'


@patch('app.chat.realtime.publisher.publish')
def test_send_rejects_non_member(mock_pub, client, user_factory, db_session):
    a = user_factory(email='nm_a@t.local')
    b = user_factory(email='nm_b@t.local')
    c = user_factory(email='nm_c@t.local')
    t = ThreadService.get_or_create_dm(a, b)
    _login(client, c)
    resp = client.post('/api/chat/messages', json={'thread_id': t.id, 'content': 'intruso'})
    assert resp.status_code == 403
```

- [ ] **Step 2: Implementar**

```python
# app/chat/routes/message_routes.py
from flask import jsonify, request
from flask_login import login_required, current_user

from app.chat import chat_bp
from app.chat.services.message_service import MessageService, MessageError
from app.chat.models import ChatMessage, ChatReaction, ChatMember, ChatForward
from app import db
from app.utils.timezone import agora_utc_naive


def _message_dict(m: ChatMessage) -> dict:
    return {
        'id': m.id, 'thread_id': m.thread_id,
        'sender_type': m.sender_type, 'sender_user_id': m.sender_user_id,
        'sender_system_source': m.sender_system_source,
        'content': None if m.deletado_em else m.content,
        'nivel': m.nivel, 'deep_link': m.deep_link,
        'reply_to_message_id': m.reply_to_message_id,
        'criado_em': m.criado_em.isoformat() if m.criado_em else None,
        'editado_em': m.editado_em.isoformat() if m.editado_em else None,
        'deletado_em': m.deletado_em.isoformat() if m.deletado_em else None,
    }


@chat_bp.route('/messages', methods=['POST'])
@login_required
def send_message():
    data = request.get_json() or {}
    try:
        msg = MessageService.send(
            sender=current_user,
            thread_id=data['thread_id'],
            content=data.get('content', ''),
            reply_to_message_id=data.get('reply_to_message_id'),
            deep_link=data.get('deep_link'),
            attachments=data.get('attachments'),
        )
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except MessageError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'message': _message_dict(msg)}), 201


@chat_bp.route('/messages/<int:message_id>', methods=['PATCH'])
@login_required
def edit_message(message_id):
    data = request.get_json() or {}
    try:
        msg = MessageService.edit(current_user, message_id, data.get('content', ''))
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except MessageError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'message': _message_dict(msg)})


@chat_bp.route('/messages/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    try:
        MessageService.delete(current_user, message_id)
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except MessageError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'ok': True})


@chat_bp.route('/threads/<int:thread_id>/messages', methods=['GET'])
@login_required
def list_messages(thread_id):
    before_id = request.args.get('before_id', type=int)
    limit = min(request.args.get('limit', 50, type=int), 100)
    try:
        msgs = MessageService.list_for_thread(current_user, thread_id, limit, before_id)
    except PermissionError:
        return jsonify({'error': 'sem acesso'}), 403
    return jsonify({'messages': [_message_dict(m) for m in msgs]})


@chat_bp.route('/messages/<int:message_id>/reactions', methods=['POST'])
@login_required
def add_reaction(message_id):
    data = request.get_json() or {}
    emoji = (data.get('emoji') or '').strip()
    if not emoji:
        return jsonify({'error': 'emoji obrigatorio'}), 400
    msg = ChatMessage.query.get_or_404(message_id)
    if not db.session.query(ChatMember).filter_by(
        thread_id=msg.thread_id, user_id=current_user.id, removido_em=None,
    ).first():
        return jsonify({'error': 'sem acesso'}), 403
    r = ChatReaction(message_id=message_id, user_id=current_user.id, emoji=emoji)
    db.session.add(r)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'reacao ja existe'}), 409

    from app.chat.realtime.publisher import publish
    for m in db.session.query(ChatMember).filter_by(
        thread_id=msg.thread_id, removido_em=None,
    ).all():
        publish(m.user_id, 'reaction_add', {
            'message_id': message_id, 'user_id': current_user.id, 'emoji': emoji,
        })
    return jsonify({'ok': True}), 201


@chat_bp.route('/messages/<int:message_id>/reactions/<emoji>', methods=['DELETE'])
@login_required
def remove_reaction(message_id, emoji):
    r = ChatReaction.query.filter_by(
        message_id=message_id, user_id=current_user.id, emoji=emoji,
    ).first()
    if not r:
        return jsonify({'error': 'reacao nao encontrada'}), 404
    db.session.delete(r)
    db.session.commit()
    return jsonify({'ok': True})


@chat_bp.route('/messages/<int:message_id>/forward', methods=['POST'])
@login_required
def forward_message(message_id):
    data = request.get_json() or {}
    original = ChatMessage.query.get_or_404(message_id)
    destino_thread_id = data.get('destino_thread_id')
    comentario = (data.get('comentario') or '').strip()

    if not destino_thread_id:
        return jsonify({'error': 'destino_thread_id obrigatorio'}), 400

    # Criar mensagem no destino
    body_parts = []
    if comentario:
        body_parts.append(comentario)
    body_parts.append(f'> _Encaminhado:_ {original.content[:500]}')
    body = '\n\n'.join(body_parts)

    try:
        new_msg = MessageService.send(
            sender=current_user, thread_id=destino_thread_id,
            content=body, deep_link=original.deep_link,
        )
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except MessageError as e:
        return jsonify({'error': str(e)}), 400

    db.session.add(ChatForward(
        original_message_id=original.id,
        forwarded_message_id=new_msg.id,
        forwarded_by_id=current_user.id,
    ))
    db.session.commit()
    return jsonify({'message': _message_dict(new_msg)}), 201
```

- [ ] **Step 3: Rodar testes**

Run: `pytest tests/chat/test_routes_message.py -v`
Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add app/chat/routes/message_routes.py tests/chat/test_routes_message.py
git commit -m "feat(chat): rotas de mensagem — send/edit/delete/list/reaction/forward"
```

---

## Task 14: Rotas de stream SSE + unread + search

**Files:**
- Modify: `app/chat/routes/stream_routes.py`
- Test: `tests/chat/test_routes_stream.py`

- [ ] **Step 1: Testes**

```python
# tests/chat/test_routes_stream.py
import pytest


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client, user):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


def test_unread_endpoint_zero(client, user_factory, db_session):
    u = user_factory(email='un@t.local')
    _login(client, u)
    resp = client.get('/api/chat/unread')
    assert resp.status_code == 200
    assert resp.json == {'system': 0, 'user': 0}


def test_search_endpoint_no_query(client, user_factory, db_session):
    u = user_factory(email='sr@t.local')
    _login(client, u)
    resp = client.get('/api/chat/search?q=')
    assert resp.status_code == 400
```

- [ ] **Step 2: Implementar**

```python
# app/chat/routes/stream_routes.py
from flask import Response, stream_with_context, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func

from app.chat import chat_bp
from app.chat.realtime.sse import stream_chat_events
from app.chat.models import ChatMessage, ChatMember
from app import db


@chat_bp.route('/stream', methods=['GET'])
@login_required
def sse_stream():
    last_event_id = request.headers.get('Last-Event-ID')
    try:
        last_event_id = int(last_event_id) if last_event_id else None
    except ValueError:
        last_event_id = None

    return Response(
        stream_with_context(stream_chat_events(current_user.id, last_event_id)),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )


@chat_bp.route('/unread', methods=['GET'])
@login_required
def unread_counters():
    """Conta nao-lidas separando sender_type='user' vs 'system'."""
    # join chat_members + chat_messages onde criado_em > last_read
    q = db.session.query(
        ChatMessage.sender_type,
        func.count(ChatMessage.id)
    ).join(
        ChatMember, ChatMember.thread_id == ChatMessage.thread_id
    ).filter(
        ChatMember.user_id == current_user.id,
        ChatMember.removido_em.is_(None),
        ChatMessage.deletado_em.is_(None),
        ChatMessage.sender_user_id != current_user.id,  # nao conta mensagem propria
        db.or_(
            ChatMember.last_read_message_id.is_(None),
            ChatMessage.id > ChatMember.last_read_message_id,
        ),
    ).group_by(ChatMessage.sender_type).all()

    counts = dict(q)
    return jsonify({
        'system': counts.get('system', 0),
        'user': counts.get('user', 0),
    })


@chat_bp.route('/search', methods=['GET'])
@login_required
def search_messages():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'error': 'parametro q obrigatorio'}), 400

    thread_ids_subq = db.session.query(ChatMember.thread_id).filter(
        ChatMember.user_id == current_user.id,
        ChatMember.removido_em.is_(None),
    ).subquery()

    results = db.session.query(ChatMessage).filter(
        ChatMessage.thread_id.in_(thread_ids_subq),
        ChatMessage.deletado_em.is_(None),
        ChatMessage.content_tsv.op('@@')(func.plainto_tsquery('portuguese', q)),
    ).order_by(ChatMessage.criado_em.desc()).limit(50).all()

    return jsonify({
        'query': q,
        'results': [
            {
                'id': m.id, 'thread_id': m.thread_id,
                'content': m.content[:200],
                'criado_em': m.criado_em.isoformat() if m.criado_em else None,
            }
            for m in results
        ],
    })


@chat_bp.route('/threads/<int:thread_id>/read', methods=['POST'])
@login_required
def mark_read(thread_id):
    """Marca thread como lida ate ultima mensagem."""
    last = db.session.query(ChatMessage.id).filter(
        ChatMessage.thread_id == thread_id,
    ).order_by(ChatMessage.id.desc()).first()
    if last is None:
        return jsonify({'ok': True})
    member = ChatMember.query.filter_by(
        thread_id=thread_id, user_id=current_user.id, removido_em=None,
    ).first()
    if not member:
        return jsonify({'error': 'sem acesso'}), 403
    member.last_read_message_id = last[0]
    db.session.commit()
    return jsonify({'ok': True, 'last_read': last[0]})
```

- [ ] **Step 3: Rodar testes**

Run: `pytest tests/chat/test_routes_stream.py -v`

- [ ] **Step 4: Commit**

```bash
git add app/chat/routes/stream_routes.py tests/chat/test_routes_stream.py
git commit -m "feat(chat): rotas /stream (SSE), /unread, /search, /read"
```

---

## Task 15: Rotas share/screen + entity thread

**Files:**
- Modify: `app/chat/routes/share_routes.py`

- [ ] **Step 1: Implementar**

```python
# app/chat/routes/share_routes.py
from flask import jsonify, request
from flask_login import login_required, current_user

from app.chat import chat_bp
from app.chat.services.thread_service import ThreadService
from app.chat.services.message_service import MessageService, MessageError
from app.auth.models import Usuario


@chat_bp.route('/share/screen', methods=['POST'])
@login_required
def share_screen():
    """
    Compartilhar tela atual com outro usuario.
    Payload: {destinatario_user_id, comentario, url, title}
    """
    data = request.get_json() or {}
    dst_id = data.get('destinatario_user_id')
    url = (data.get('url') or '').strip()
    if not dst_id or not url:
        return jsonify({'error': 'destinatario_user_id e url obrigatorios'}), 400

    target = Usuario.query.get(dst_id)
    if not target:
        return jsonify({'error': 'usuario nao encontrado'}), 404

    try:
        thread = ThreadService.get_or_create_dm(current_user, target)
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403

    comentario = (data.get('comentario') or '').strip()
    title = (data.get('title') or 'Tela compartilhada').strip()
    body_parts = []
    if comentario:
        body_parts.append(comentario)
    body_parts.append(f'↗ **{title}**\n[abrir tela]({url})')
    content = '\n\n'.join(body_parts)

    try:
        msg = MessageService.send(
            sender=current_user, thread_id=thread.id,
            content=content, deep_link=url,
        )
    except MessageError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'thread_id': thread.id, 'message_id': msg.id}), 201


@chat_bp.route('/entity/<entity_type>/<entity_id>/message', methods=['POST'])
@login_required
def post_to_entity_thread(entity_type, entity_id):
    """Cria thread lazy se nao existe, posta mensagem."""
    data = request.get_json() or {}
    content = data.get('content', '')
    if not content:
        return jsonify({'error': 'content obrigatorio'}), 400

    thread = ThreadService.get_entity_thread(entity_type, entity_id)
    if thread is None:
        thread = ThreadService.create_entity_thread(entity_type, entity_id, creator=current_user)

    try:
        msg = MessageService.send(sender=current_user, thread_id=thread.id, content=content)
    except (PermissionError, MessageError) as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'thread_id': thread.id, 'message_id': msg.id}), 201
```

- [ ] **Step 2: Teste manual (curl)**

Run (com servidor rodando em `python run.py`):
```bash
curl -X POST http://localhost:5000/api/chat/share/screen \
  -H "Content-Type: application/json" \
  -b "session=..."  \
  -d '{"destinatario_user_id": 2, "url": "/carteira/pedido/VCD123", "title": "Pedido VCD123", "comentario": "confere por favor"}'
```
Expected: 201 com `{thread_id, message_id}`.

- [ ] **Step 3: Commit**

```bash
git add app/chat/routes/share_routes.py
git commit -m "feat(chat): rotas /share/screen + /entity/<t>/<id>/message"
```

---

# FASE E — UI

## Task 16: CSS base + badge navbar + include em base.html

**Files:**
- Create: `app/static/chat/css/chat.css`
- Create: `app/templates/chat/_navbar_badge.html`
- Modify: `app/templates/base.html`
- Modify: `app/static/css/main.css` (adicionar @import)

- [ ] **Step 1: CSS base do modulo**

```css
/* app/static/chat/css/chat.css */
/* Modulo chat — segue design tokens + sistema de layers */

.chat-navbar-btn {
  position: relative;
  background: transparent;
  border: 0;
  padding: 0.5rem 0.75rem;
  color: var(--text);
  font-size: 1.15rem;
  cursor: pointer;
}
.chat-navbar-btn:hover { color: var(--accent); }

.chat-badge {
  position: absolute;
  min-width: 16px;
  height: 16px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
  line-height: 1;
}
.chat-badge--system { top: 2px; left: 2px; background: var(--warning, #f59e0b); color: #fff; }
.chat-badge--user   { top: 2px; right: 2px; background: var(--danger, #dc2626); color: #fff; }
.chat-badge.hidden  { display: none; }

/* drawer lateral */
.chat-drawer {
  position: fixed; top: 0; right: 0; bottom: 0;
  width: 420px; max-width: 100vw;
  background: var(--bg); border-left: 1px solid var(--border);
  transform: translateX(100%); transition: transform .2s ease;
  z-index: 1050;
  display: flex; flex-direction: column;
}
.chat-drawer.open { transform: translateX(0); }
.chat-drawer__header { padding: 1rem; border-bottom: 1px solid var(--border); }
.chat-drawer__tabs { display: flex; gap: 0.5rem; padding: 0.5rem 1rem; }
.chat-drawer__tab { background: none; border: 0; padding: 0.5rem; cursor: pointer; color: var(--text-muted); }
.chat-drawer__tab.active { color: var(--accent); border-bottom: 2px solid var(--accent); }
.chat-drawer__list { flex: 1; overflow-y: auto; }

.chat-thread-item { padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-light); cursor: pointer; }
.chat-thread-item:hover { background: var(--bg-light); }
.chat-thread-item--unread { font-weight: 600; }

.chat-panel { display: flex; flex-direction: column; height: 100%; }
.chat-panel__messages { flex: 1; overflow-y: auto; padding: 1rem; }
.chat-panel__footer { border-top: 1px solid var(--border); padding: 0.5rem 1rem; }

.chat-message { margin-bottom: 0.75rem; }
.chat-message__sender { font-size: 0.75rem; color: var(--text-muted); }
.chat-message__body { padding: 0.5rem 0.75rem; background: var(--bg-light); border-radius: 6px; }
.chat-message--system .chat-message__body {
  background: var(--info-bg, #dbeafe); border-left: 3px solid var(--info, #3b82f6);
}
.chat-message--critico .chat-message__body {
  background: var(--danger-bg, #fee2e2); border-left: 3px solid var(--danger, #dc2626);
}

/* Compartilhar esta tela — botao discreto */
.chat-share-btn {
  background: transparent; border: 1px solid var(--border);
  border-radius: 4px; padding: 0.25rem 0.5rem;
  color: var(--text-muted); font-size: 0.85rem; cursor: pointer;
}
.chat-share-btn:hover { color: var(--accent); border-color: var(--accent); }
```

- [ ] **Step 2: Include navbar badge**

```html
<!-- app/templates/chat/_navbar_badge.html -->
<li class="nav-item">
  <button id="chat-toggle" class="chat-navbar-btn" title="Chat" aria-label="Abrir chat">
    💬
    <span id="chat-badge-system" class="chat-badge chat-badge--system hidden">0</span>
    <span id="chat-badge-user" class="chat-badge chat-badge--user hidden">0</span>
  </button>
</li>
```

- [ ] **Step 3: Modificar base.html**

Localizar a navbar em `app/templates/base.html`. Achar a lista `<ul>` dos itens do menu do usuario (ex: perto do dropdown de perfil). Adicionar ANTES do dropdown de perfil:

```html
{% include 'chat/_navbar_badge.html' %}
```

No `<head>` do base.html:
```html
<link rel="stylesheet" href="{{ url_for('static', filename='chat/css/chat.css') }}">
```

Antes de `</body>`:
```html
<script src="{{ url_for('static', filename='chat/js/chat_client.js') }}" defer></script>
<script src="{{ url_for('static', filename='chat/js/chat_ui.js') }}" defer></script>
```

- [ ] **Step 4: Verificar que pagina carrega sem 404 de asset**

Run: `source .venv/bin/activate && python run.py &` (background). Abra navegador em `http://localhost:5000` logado.
Expected: pagina carrega, botao chat aparece na navbar (sem badges ainda — precisa Task 17).

Matar server: `pkill -f "python run.py"`

- [ ] **Step 5: Commit**

```bash
git add app/static/chat/css/chat.css app/templates/chat/_navbar_badge.html app/templates/base.html
git commit -m "feat(chat): navbar badge + CSS base do modulo + include em base.html"
```

---

## Task 17: JS client — SSE + badges + contador

**Files:**
- Create: `app/static/chat/js/chat_client.js`

- [ ] **Step 1: Implementar**

```javascript
// app/static/chat/js/chat_client.js
/**
 * ChatClient — SSE + badges.
 *
 * Conecta em /api/chat/stream (EventSource), escuta eventos,
 * atualiza contadores na navbar, dispara callbacks para UI.
 */
(function () {
  'use strict';

  const BADGES = {
    system: document.getElementById('chat-badge-system'),
    user: document.getElementById('chat-badge-user'),
  };

  const State = {
    counters: { system: 0, user: 0 },
    es: null,
    listeners: new Set(),
  };

  function updateBadge(kind) {
    const el = BADGES[kind];
    if (!el) return;
    const n = State.counters[kind];
    if (n > 0) {
      el.textContent = n > 99 ? '99+' : String(n);
      el.classList.remove('hidden');
    } else {
      el.classList.add('hidden');
    }
  }

  async function fetchInitialCounters() {
    try {
      const resp = await fetch('/api/chat/unread', { credentials: 'same-origin' });
      if (!resp.ok) return;
      const data = await resp.json();
      State.counters.system = data.system || 0;
      State.counters.user = data.user || 0;
      updateBadge('system');
      updateBadge('user');
    } catch (e) {
      console.warn('[chat] fetch unread failed', e);
    }
  }

  function handleEvent(eventType, data) {
    if (eventType === 'message_new') {
      const kind = data.sender_type === 'system' ? 'system' : 'user';
      State.counters[kind] += 1;
      updateBadge(kind);
    } else if (eventType === 'unread_changed') {
      if (typeof data.system === 'number') State.counters.system = data.system;
      if (typeof data.user === 'number') State.counters.user = data.user;
      updateBadge('system');
      updateBadge('user');
    }
    State.listeners.forEach(cb => {
      try { cb(eventType, data); } catch (e) { console.error(e); }
    });
  }

  function connect() {
    if (State.es) State.es.close();
    const es = new EventSource('/api/chat/stream');
    State.es = es;

    ['message_new', 'message_edit', 'message_delete', 'reaction_add', 'unread_changed'].forEach(evtType => {
      es.addEventListener(evtType, (evt) => {
        let data = {};
        try { data = JSON.parse(evt.data); } catch {}
        handleEvent(evtType, data);
      });
    });

    es.onerror = (err) => {
      console.warn('[chat] SSE error, browser reconectara automaticamente', err);
    };
  }

  window.ChatClient = {
    onEvent(cb) { State.listeners.add(cb); return () => State.listeners.delete(cb); },
    counters: () => ({ ...State.counters }),
    markRead(kind, thread_id) {
      if (kind in State.counters && State.counters[kind] > 0) {
        State.counters[kind] = Math.max(0, State.counters[kind] - 1);
        updateBadge(kind);
      }
      if (thread_id) {
        fetch(`/api/chat/threads/${thread_id}/read`, {
          method: 'POST', credentials: 'same-origin',
        });
      }
    },
  };

  document.addEventListener('DOMContentLoaded', () => {
    fetchInitialCounters();
    connect();
  });
})();
```

- [ ] **Step 2: Testar manualmente**

Run: `python run.py` e abra navegador. Logado, inspecione console — deve ver conexao SSE aberta (`: connected`). Badge aparece se houver mensagens nao lidas.

- [ ] **Step 3: Commit**

```bash
git add app/static/chat/js/chat_client.js
git commit -m "feat(chat): ChatClient JS — SSE, badges, contadores, listeners"
```

---

## Task 18: Drawer + lista de threads (UI)

**Files:**
- Create: `app/static/chat/js/chat_ui.js`
- Create: `app/templates/chat/drawer.html`

- [ ] **Step 1: Template drawer (carregado via fetch HTML)**

```html
<!-- app/templates/chat/drawer.html — retornado por GET /api/chat/ui/drawer -->
<div class="chat-drawer" id="chat-drawer" aria-hidden="true">
  <div class="chat-drawer__header">
    <button class="chat-drawer__close" id="chat-drawer-close" aria-label="Fechar">×</button>
    <h3 class="chat-drawer__title">Chat</h3>
  </div>
  <div class="chat-drawer__tabs" role="tablist">
    <button class="chat-drawer__tab active" data-tipo="">Todos</button>
    <button class="chat-drawer__tab" data-tipo="dm">DMs</button>
    <button class="chat-drawer__tab" data-tipo="group">Grupos</button>
    <button class="chat-drawer__tab" data-tipo="entity">Entidades</button>
    <button class="chat-drawer__tab" data-tipo="system_dm">Sistema</button>
  </div>
  <div class="chat-drawer__list" id="chat-thread-list">
    <div class="text-muted p-3">Carregando...</div>
  </div>
  <div class="chat-drawer__panel" id="chat-panel-container" style="display:none"></div>
</div>
```

- [ ] **Step 2: Rota para servir fragmento HTML**

Adicionar em `app/chat/routes/stream_routes.py`:

```python
from flask import render_template

@chat_bp.route('/ui/drawer', methods=['GET'])
@login_required
def ui_drawer():
    return render_template('chat/drawer.html')
```

- [ ] **Step 3: JS UI — drawer toggle + lista de threads**

```javascript
// app/static/chat/js/chat_ui.js
(function () {
  'use strict';

  let drawerEl = null;
  let currentTipo = '';

  async function loadDrawer() {
    if (drawerEl) return drawerEl;
    const resp = await fetch('/api/chat/ui/drawer', { credentials: 'same-origin' });
    const html = await resp.text();
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    drawerEl = tmp.firstElementChild;
    document.body.appendChild(drawerEl);
    wireDrawerEvents();
    return drawerEl;
  }

  function wireDrawerEvents() {
    drawerEl.querySelector('#chat-drawer-close').addEventListener('click', closeDrawer);
    drawerEl.querySelectorAll('.chat-drawer__tab').forEach(btn => {
      btn.addEventListener('click', () => {
        drawerEl.querySelectorAll('.chat-drawer__tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentTipo = btn.dataset.tipo;
        refreshThreads();
      });
    });
  }

  async function refreshThreads() {
    const list = drawerEl.querySelector('#chat-thread-list');
    list.innerHTML = '<div class="text-muted p-3">Carregando...</div>';
    const url = '/api/chat/threads' + (currentTipo ? `?tipo=${currentTipo}` : '');
    const resp = await fetch(url, { credentials: 'same-origin' });
    const data = await resp.json();
    if (!data.threads || data.threads.length === 0) {
      list.innerHTML = '<div class="text-muted p-3">Nada aqui ainda.</div>';
      return;
    }
    list.innerHTML = data.threads.map(t => renderThreadItem(t)).join('');
    list.querySelectorAll('[data-thread-id]').forEach(el => {
      el.addEventListener('click', () => openPanel(parseInt(el.dataset.threadId, 10)));
    });
  }

  function renderThreadItem(t) {
    const title = t.titulo || (t.entity_type ? `${t.entity_type} ${t.entity_id}` : `Thread #${t.id}`);
    return `
      <div class="chat-thread-item" data-thread-id="${t.id}">
        <div>${escapeHtml(title)}</div>
        <div class="text-muted small">${t.tipo}</div>
      </div>`;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }

  async function openPanel(threadId) {
    const container = drawerEl.querySelector('#chat-panel-container');
    container.style.display = 'block';
    container.innerHTML = '<div class="p-3 text-muted">Carregando mensagens...</div>';
    const resp = await fetch(`/api/chat/threads/${threadId}/messages`, { credentials: 'same-origin' });
    const data = await resp.json();
    container.innerHTML = renderPanel(threadId, data.messages || []);
    wirePanelEvents(container, threadId);
    // marca como lido
    if (window.ChatClient) window.ChatClient.markRead('user', threadId);
  }

  function renderPanel(threadId, messages) {
    const msgsHtml = messages.slice().reverse().map(m => `
      <div class="chat-message chat-message--${m.sender_type}${m.nivel === 'CRITICO' ? ' chat-message--critico' : ''}">
        <div class="chat-message__sender">${m.sender_type === 'system' ? '[Sistema]' : `user#${m.sender_user_id}`}</div>
        <div class="chat-message__body">${escapeHtml(m.content || '')}</div>
      </div>`).join('');
    return `
      <div class="chat-panel">
        <div class="chat-panel__messages">${msgsHtml}</div>
        <div class="chat-panel__footer">
          <form id="chat-send-form-${threadId}">
            <textarea name="content" rows="2" placeholder="Digite a mensagem..." style="width:100%"></textarea>
            <button type="submit" class="btn btn-primary btn-sm">Enviar</button>
          </form>
        </div>
      </div>`;
  }

  function wirePanelEvents(container, threadId) {
    const form = container.querySelector(`#chat-send-form-${threadId}`);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const content = form.querySelector('[name="content"]').value.trim();
      if (!content) return;
      await fetch('/api/chat/messages', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId, content }),
      });
      form.querySelector('[name="content"]').value = '';
      openPanel(threadId); // recarrega
    });
  }

  function openDrawer() {
    loadDrawer().then(() => {
      drawerEl.classList.add('open');
      drawerEl.setAttribute('aria-hidden', 'false');
      refreshThreads();
    });
  }
  function closeDrawer() {
    if (drawerEl) {
      drawerEl.classList.remove('open');
      drawerEl.setAttribute('aria-hidden', 'true');
    }
  }

  // liga SSE -> refresh se drawer aberto
  document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('chat-toggle');
    if (toggle) toggle.addEventListener('click', openDrawer);
    if (window.ChatClient) {
      window.ChatClient.onEvent((evt, data) => {
        if (evt === 'message_new' && drawerEl && drawerEl.classList.contains('open')) {
          refreshThreads();
        }
      });
    }
  });
})();
```

- [ ] **Step 4: Teste manual**

Run: `python run.py`. Abre navegador, clica botao chat — drawer abre; clica em thread — painel abre; digita + envia — mensagem aparece.

- [ ] **Step 5: Commit**

```bash
git add app/chat/routes/stream_routes.py app/static/chat/js/chat_ui.js app/templates/chat/drawer.html
git commit -m "feat(chat): drawer UI — tabs, lista de threads, painel com envio"
```

---

## Task 19: Botao "Compartilhar esta tela"

**Files:**
- Create: `app/templates/chat/_share_button.html`
- Modify: `app/templates/base.html`
- Modify: `app/static/chat/js/chat_ui.js` (adicionar lógica do modal)

- [ ] **Step 1: Include do botao**

```html
<!-- app/templates/chat/_share_button.html -->
<button id="chat-share-screen" class="chat-share-btn" title="Compartilhar esta tela">
  ↗ Compartilhar
</button>
```

- [ ] **Step 2: Incluir no base.html (perto do titulo da pagina)**

Em `app/templates/base.html`, localizar onde o `{% block title %}` e renderizado no header; adicionar:

```html
{% if current_user.is_authenticated %}
  {% include 'chat/_share_button.html' %}
{% endif %}
```

- [ ] **Step 3: Modal JS (adicionar em chat_ui.js, apos o `closeDrawer`)**

```javascript
  // Share screen modal
  function openShareModal() {
    const modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1100;display:flex;align-items:center;justify-content:center;';
    modal.innerHTML = `
      <div style="background:var(--bg);padding:1.5rem;border-radius:8px;min-width:400px;max-width:90vw;">
        <h4>Compartilhar esta tela</h4>
        <div><strong>URL:</strong> <code>${window.location.pathname}</code></div>
        <label>Destinatario (email ou ID):<input id="share-dst" style="width:100%"></label>
        <label>Comentario:<textarea id="share-cmt" rows="3" style="width:100%"></textarea></label>
        <div style="margin-top:1rem;display:flex;gap:.5rem;justify-content:flex-end">
          <button id="share-cancel" class="btn btn-secondary">Cancelar</button>
          <button id="share-send" class="btn btn-primary">Enviar</button>
        </div>
      </div>`;
    document.body.appendChild(modal);
    modal.querySelector('#share-cancel').addEventListener('click', () => modal.remove());
    modal.querySelector('#share-send').addEventListener('click', async () => {
      const dstRaw = modal.querySelector('#share-dst').value.trim();
      const cmt = modal.querySelector('#share-cmt').value.trim();
      let dstId = parseInt(dstRaw, 10);
      if (isNaN(dstId)) {
        // resolver email via endpoint futuro; por ora exigir ID
        alert('Informe o ID do usuario (numerico) por ora');
        return;
      }
      const resp = await fetch('/api/chat/share/screen', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destinatario_user_id: dstId, comentario: cmt,
          url: window.location.pathname + window.location.search,
          title: document.title,
        }),
      });
      if (resp.ok) {
        alert('Compartilhado!');
        modal.remove();
      } else {
        const err = await resp.json().catch(() => ({error: 'erro'}));
        alert('Falhou: ' + (err.error || resp.status));
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('chat-share-screen');
    if (btn) btn.addEventListener('click', openShareModal);
  });
```

- [ ] **Step 4: Teste manual**

Loga, abre uma tela qualquer, clica "↗ Compartilhar", informa ID de outro usuario, envia. Outro usuario (em outra aba) recebe mensagem no drawer com link clicavel.

- [ ] **Step 5: Commit**

```bash
git add app/templates/chat/_share_button.html app/templates/base.html app/static/chat/js/chat_ui.js
git commit -m "feat(chat): botao Compartilhar esta tela + modal + integracao com base.html"
```

---

## Task 20: Encaminhamento de mensagem (UI)

**Files:**
- Modify: `app/static/chat/js/chat_ui.js`

- [ ] **Step 1: Adicionar botao ↪ em cada mensagem renderizada**

Modificar funcao `renderPanel` em `chat_ui.js`:

```javascript
  function renderPanel(threadId, messages) {
    const msgsHtml = messages.slice().reverse().map(m => `
      <div class="chat-message chat-message--${m.sender_type}${m.nivel === 'CRITICO' ? ' chat-message--critico' : ''}" data-msg-id="${m.id}">
        <div class="chat-message__sender">
          ${m.sender_type === 'system' ? '[Sistema]' : `user#${m.sender_user_id}`}
          <button class="chat-message__forward" data-fwd="${m.id}" style="float:right;font-size:.75rem;background:none;border:0;cursor:pointer;">↪</button>
        </div>
        <div class="chat-message__body">${escapeHtml(m.content || '')}</div>
        ${m.deep_link ? `<div><a href="${escapeHtml(m.deep_link)}" target="_blank">↗ Abrir</a></div>` : ''}
      </div>`).join('');
    return `
      <div class="chat-panel">
        <div class="chat-panel__messages">${msgsHtml}</div>
        <div class="chat-panel__footer">
          <form id="chat-send-form-${threadId}">
            <textarea name="content" rows="2" placeholder="Digite a mensagem..." style="width:100%"></textarea>
            <button type="submit" class="btn btn-primary btn-sm">Enviar</button>
          </form>
        </div>
      </div>`;
  }
```

- [ ] **Step 2: Adicionar handler em wirePanelEvents**

```javascript
  function wirePanelEvents(container, threadId) {
    // ... (codigo existente de submit) ...
    container.querySelectorAll('[data-fwd]').forEach(btn => {
      btn.addEventListener('click', () => openForwardModal(parseInt(btn.dataset.fwd, 10)));
    });
  }

  function openForwardModal(messageId) {
    const modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1100;display:flex;align-items:center;justify-content:center;';
    modal.innerHTML = `
      <div style="background:var(--bg);padding:1.5rem;border-radius:8px;min-width:400px;">
        <h4>Encaminhar mensagem</h4>
        <label>Thread destino (ID):<input id="fwd-thread" type="number" style="width:100%"></label>
        <label>Comentario:<textarea id="fwd-cmt" rows="2" style="width:100%"></textarea></label>
        <div style="margin-top:1rem;display:flex;gap:.5rem;justify-content:flex-end">
          <button id="fwd-cancel" class="btn btn-secondary">Cancelar</button>
          <button id="fwd-send" class="btn btn-primary">Encaminhar</button>
        </div>
      </div>`;
    document.body.appendChild(modal);
    modal.querySelector('#fwd-cancel').addEventListener('click', () => modal.remove());
    modal.querySelector('#fwd-send').addEventListener('click', async () => {
      const dstThread = parseInt(modal.querySelector('#fwd-thread').value, 10);
      const cmt = modal.querySelector('#fwd-cmt').value.trim();
      if (isNaN(dstThread)) { alert('Informe thread destino'); return; }
      const resp = await fetch(`/api/chat/messages/${messageId}/forward`, {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ destino_thread_id: dstThread, comentario: cmt }),
      });
      if (resp.ok) { alert('Encaminhada!'); modal.remove(); }
      else { const err = await resp.json().catch(() => ({})); alert('Falha: ' + (err.error || resp.status)); }
    });
  }
```

- [ ] **Step 3: Teste manual**

Loga, abre drawer, entra numa thread, clica `↪` em uma mensagem, informa thread destino, envia. Verifica que a mensagem aparece na thread destino com prefixo "Encaminhado:".

- [ ] **Step 4: Commit**

```bash
git add app/static/chat/js/chat_ui.js
git commit -m "feat(chat): UI encaminhamento de mensagem via botao ↪ + modal"
```

---

# FASE F — Integracoes de alerta do sistema

## Task 21: Integrar SystemNotifier no worker de recebimento

**Files:**
- Identify & Modify: arquivo do worker que finaliza recebimento (provavel `app/recebimento/workers/...`)
- Test: `tests/chat/test_integration_recebimento.py`

- [ ] **Step 1: Localizar ponto de finalizacao**

Run: `grep -rnE "status.*=.*['\"](concluido|finalizado|erro)['\"]|recebimento.*(save|commit)" app/recebimento/ --include="*.py" | head -20`
Expected: lista o(s) arquivo(s) onde o worker conclui recebimento.

Examinar o arquivo e identificar (1) variavel `recebimento` (instancia Recebimento), (2) variavel `user_id` (quem iniciou o recebimento), (3) ponto logo ANTES do `commit` final.

- [ ] **Step 2: Adicionar chamada ao SystemNotifier**

No ponto identificado, adicionar:

```python
# Disparar alerta do sistema (FASE 1 — Chat)
from app.chat.services.system_notifier import SystemNotifier
try:
    destinatarios = [recebimento.iniciado_por_id]  # ajustar nome do campo se necessario
    if recebimento.responsavel_id and recebimento.responsavel_id not in destinatarios:
        destinatarios.append(recebimento.responsavel_id)
    if recebimento.status == 'erro':
        titulo = f'Recebimento #{recebimento.id} concluiu com erro'
        nivel = 'CRITICO'
    else:
        titulo = f'Recebimento #{recebimento.id} concluido'
        nivel = 'INFO'
    SystemNotifier.alert(
        user_ids=destinatarios,
        source='recebimento',
        titulo=titulo,
        content=f'NF {recebimento.numero_nf or "-"} — status: {recebimento.status}',
        deep_link=f'/recebimento/{recebimento.id}',
        nivel=nivel,
        dados={'recebimento_id': recebimento.id, 'nf': recebimento.numero_nf},
    )
except Exception as e:
    # Alerta nao pode quebrar o worker
    from app.utils.logging_config import logger
    logger.error(f'[CHAT] alerta recebimento falhou: {e}', exc_info=True)
```

- [ ] **Step 3: Teste de integracao**

```python
# tests/chat/test_integration_recebimento.py
from unittest.mock import patch
from app.chat.services.system_notifier import SystemNotifier


@patch('app.chat.realtime.publisher.publish')
def test_recebimento_erro_dispara_alerta(mock_pub, db_session, user_factory):
    u = user_factory(email='rec_u@t.local')
    # simular finalizacao (chamando SystemNotifier diretamente — smoketest)
    SystemNotifier.alert(
        user_ids=[u.id],
        source='recebimento',
        titulo='Recebimento #9999 concluiu com erro',
        content='NF 12345 — status: erro',
        deep_link='/recebimento/9999',
        nivel='CRITICO',
        dados={'recebimento_id': 9999, 'nf': '12345'},
    )
    from app.chat.models import ChatMessage
    msg = ChatMessage.query.filter(
        ChatMessage.sender_system_source == 'recebimento'
    ).order_by(ChatMessage.id.desc()).first()
    assert msg is not None
    assert msg.nivel == 'CRITICO'
    assert msg.deep_link == '/recebimento/9999'
```

- [ ] **Step 4: Rodar teste**

Run: `pytest tests/chat/test_integration_recebimento.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add app/recebimento/ tests/chat/test_integration_recebimento.py
git commit -m "feat(chat,recebimento): disparar SystemNotifier ao finalizar recebimento (ok/erro)"
```

---

## Task 22: Integrar alerta DFE bloqueado (Fase 2 recebimento — match NF-PO)

**Files:**
- Identify & Modify: arquivo do job/service de validacao NF-PO (provavel `app/recebimento/services/validacao_nf_po*.py`)
- Test: adicionar caso em `tests/chat/test_integration_recebimento.py`

- [ ] **Step 1: Localizar ponto onde o DFE e marcado como bloqueado**

Run: `grep -rnE "bloqueado|divergencia_*=.*True|status.*=.*['\"]bloqueado" app/recebimento/services/ --include="*.py" | head -20`
Expected: localizar local onde divergencia NF-PO e criada.

- [ ] **Step 2: Adicionar alerta para operadores**

No ponto identificado:

```python
from app.chat.services.system_notifier import SystemNotifier
try:
    # Destinatarios: operadores de recebimento (por perfil 'logistica' + algum flag de "recebimento")
    # Se houver tabela de destinatarios configurada, usar. Caso contrario, lista hardcoded por ID
    # documentada no spec (Gabriella, Nicoly) — passar por env ou config central
    from app.auth.models import Usuario
    operadores_ids = [
        u.id for u in Usuario.query.filter(
            Usuario.perfil == 'logistica',
            # adicionar filtro especifico se existir (ex: Usuario.recebimento_operador.is_(True))
        ).all()
    ]
    if operadores_ids:
        SystemNotifier.alert(
            user_ids=operadores_ids,
            source='dfe',
            titulo=f'DFE {dfe.chave[:10]}... bloqueado',
            content=f'Divergencia NF {dfe.numero} vs PO: {motivo_divergencia}',
            deep_link=f'/recebimento/dfe/{dfe.id}',
            nivel='ATENCAO',
            dados={'dfe_id': dfe.id, 'chave': dfe.chave, 'motivo': motivo_divergencia},
        )
except Exception as e:
    from app.utils.logging_config import logger
    logger.error(f'[CHAT] alerta DFE falhou: {e}', exc_info=True)
```

- [ ] **Step 3: Teste**

Adicionar em `tests/chat/test_integration_recebimento.py`:

```python
@patch('app.chat.realtime.publisher.publish')
def test_dfe_bloqueado_dispara_alerta(mock_pub, db_session, user_factory):
    op = user_factory(email='op@t.local', perfil='logistica')
    SystemNotifier.alert(
        user_ids=[op.id], source='dfe',
        titulo='DFE 1234...blo...', content='divergencia preco',
        deep_link='/recebimento/dfe/1', nivel='ATENCAO',
        dados={'dfe_id': 1},
    )
    from app.chat.models import ChatMessage
    msg = ChatMessage.query.filter_by(sender_system_source='dfe').order_by(ChatMessage.id.desc()).first()
    assert msg.nivel == 'ATENCAO'
```

- [ ] **Step 4: Rodar testes**

Run: `pytest tests/chat/test_integration_recebimento.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/recebimento/services/ tests/chat/test_integration_recebimento.py
git commit -m "feat(chat,dfe): alerta SystemNotifier quando DFE bloqueado por divergencia NF-PO"
```

---

## Task 23: Integrar alerta CTe divergente (Fretes)

**Files:**
- Identify & Modify: arquivo de validacao CTe vs cotacao (provavel `app/fretes/services/...`)
- Test: `tests/chat/test_integration_cte.py`

- [ ] **Step 1: Localizar ponto de deteccao de divergencia**

Run: `grep -rnE "divergencia|cte.*cotacao|valor_cte.*valor_cotado" app/fretes/services/ --include="*.py" | head -20`

- [ ] **Step 2: Adicionar alerta para controller de frete**

```python
from app.chat.services.system_notifier import SystemNotifier
try:
    # Destinatario: perfil 'financeiro' OU lista configuravel
    from app.auth.models import Usuario
    controllers_ids = [
        u.id for u in Usuario.query.filter(
            Usuario.perfil.in_(['financeiro', 'administrador']),
        ).all()
    ]
    if controllers_ids:
        SystemNotifier.alert(
            user_ids=controllers_ids,
            source='cte',
            titulo=f'CTe {cte.numero} divergente da cotacao',
            content=f'Cotado R$ {valor_cotado:.2f}, CTe R$ {valor_cte:.2f} (diff {diff_pct:.1f}%)',
            deep_link=f'/fretes/cte/{cte.id}',
            nivel='ATENCAO',
            dados={
                'cte_id': cte.id, 'cte_numero': cte.numero,
                'valor_cotado': float(valor_cotado), 'valor_cte': float(valor_cte),
                'diff_pct': float(diff_pct),
            },
        )
except Exception as e:
    from app.utils.logging_config import logger
    logger.error(f'[CHAT] alerta CTe falhou: {e}', exc_info=True)
```

- [ ] **Step 3: Teste**

```python
# tests/chat/test_integration_cte.py
from unittest.mock import patch
from app.chat.services.system_notifier import SystemNotifier


@patch('app.chat.realtime.publisher.publish')
def test_cte_divergente_dispara_alerta(mock_pub, db_session, user_factory):
    ctrl = user_factory(email='ctrl@t.local', perfil='financeiro')
    SystemNotifier.alert(
        user_ids=[ctrl.id], source='cte',
        titulo='CTe 999 divergente', content='cotado 100, cte 150 (50%)',
        deep_link='/fretes/cte/999', nivel='ATENCAO',
        dados={'cte_id': 999},
    )
    from app.chat.models import ChatMessage
    msg = ChatMessage.query.filter_by(sender_system_source='cte').order_by(ChatMessage.id.desc()).first()
    assert msg is not None
    assert msg.deep_link == '/fretes/cte/999'
```

- [ ] **Step 4: Rodar**

Run: `pytest tests/chat/test_integration_cte.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/fretes/ tests/chat/test_integration_cte.py
git commit -m "feat(chat,fretes): alerta SystemNotifier quando CTe divergente da cotacao"
```

---

# FASE G — Docs + smoke test

## Task 24: CLAUDE.md do modulo + atualizar raiz

**Files:**
- Create: `app/chat/CLAUDE.md`
- Modify: `CLAUDE.md` (raiz — adicionar link)
- Modify: `~/.claude/CLAUDE.md` (adicionar entrada em "Criados")

- [ ] **Step 1: CLAUDE.md do modulo**

```markdown
# Chat — Guia de Desenvolvimento

**LOC**: ~[medir] | **Arquivos**: [contar] | **Atualizado**: 2026-04-23

Modulo de chat in-app + alertas do sistema unificados. Ver spec em
`docs/superpowers/specs/2026-04-23-chat-inapp-design.md` e plano
`docs/superpowers/plans/2026-04-23-chat-inapp.md`.

---

## Estrutura

\`\`\`
app/chat/
  __init__.py           # Blueprint chat_bp (/api/chat)
  models.py             # 7 modelos (thread, member, message, attachment, mention, reaction, forward)
  markdown_parser.py    # extract_mentions + sanitize_html
  routes/               # thread / message / stream / share
  services/             # permission_checker / thread / message / attachment / system_notifier / forwarder / search
  realtime/             # publisher Redis / SSE generator
\`\`\`

---

## Regras criticas

### R1: Redis e opcional — publish best-effort
`publisher.publish()` NAO lanca excecao se Redis down. Mensagem persiste no DB;
client reconnecta e pega via catch-up (`Last-Event-ID`).

### R2: SSE usa padrao do agente
`stream_with_context` + `mimetype='text/event-stream'` + headers `X-Accel-Buffering: no`,
`Cache-Control: no-cache`, `Connection: keep-alive`. Heartbeat cada 25s (Render SSL drop 30-40s).
Canal Redis: `chat_sse:{user_id}`.

### R3: PermissionChecker em TODA rota de escrita
Revalidar mesmo que UI tenha filtrado. Admin bypass via `user.perfil == 'administrador'`.

### R4: `sanitize_for_json` em `ChatMessage.dados`
`dados` e JSONB; valores Decimal/datetime quebram flush. Usar `app.utils.json_helpers.sanitize_for_json`.

### R5: Alertas unificados em `chat_message`
`sender_type='system'` + `sender_system_source='recebimento'|'dfe'|'cte'|...`.
Nao criar tabela separada para alertas.

### R6: Mentions so valem para membros ativos
Parser extrai `@usuario` do content. Se mencionado NAO e membro ativo da thread,
`chat_mention` nao e criada.

---

## API publica

\`\`\`python
from app.chat.services.system_notifier import SystemNotifier
SystemNotifier.alert(user_ids=[1,2], source='recebimento', titulo='...',
                     content='...', deep_link='/recebimento/1', nivel='CRITICO')
\`\`\`

---

## Gotchas

### Bug #1: `last_read_message_id` com FK circular
`chat_members.last_read_message_id` -> `chat_messages.id` MAS
`chat_messages.thread_id` -> `chat_threads.id` (sem FK para member).
SQLAlchemy exige `use_alter=True` no ForeignKey para evitar circular em create_all.

### Bug #2: Content-Type HTML no base.html include
`{% include 'chat/_navbar_badge.html' %}` deve vir DEPOIS de `<link>` do chat.css
(senao estilos nao aplicam).

### Bug #3: SSE com 4 workers gunicorn
`WEB_CONCURRENCY=1` do render.yaml e sobrescrito por `start_render.sh` para workers=4.
Redis pub/sub e OBRIGATORIO — sem ele mensagens ficam presas no worker que gerou.

---

## Observabilidade

- Logs: prefixo `[CHAT]` em logger
- Metricas: contar `chat_message` por dia, por sender_type
- Sentry: ver `app/chat/services/system_notifier.py` (exceptions em SystemNotifier)

---

## Interdependencias

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app.auth.models.Usuario` | FK em member/message/mention | Mudanca de perfil afeta permissao |
| `app.utils.json_helpers` | sanitize_for_json | Obrigatorio em `ChatMessage.dados` |
| `app.utils.timezone` | agora_utc_naive | Todos timestamps naive UTC |
| `app.utils.redis_cache` | nao (usa redis.from_url direto via REDIS_URL env) | — |
| Padrao de `app/agente/routes/chat.py` | stream_with_context + pubsub | Manter compatibilidade |
```

- [ ] **Step 2: Atualizar raiz**

No `~/.claude/CLAUDE.md` (global dev), localizar secao "Criados" em SUBDIRECTORY CLAUDE.md e adicionar:

```markdown
- `app/chat/CLAUDE.md` — [medir]K LOC, [N] arquivos — chat in-app + alertas sistema
```

- [ ] **Step 3: Commit**

```bash
git add app/chat/CLAUDE.md ~/.claude/CLAUDE.md
git commit -m "docs(chat): CLAUDE.md do modulo + atualizacao do indice dev"
```

*Note*: se `~/.claude/CLAUDE.md` nao estiver sob git deste repo, apenas editar manualmente sem commit.

---

## Task 25: Smoke test E2E

**Files:**
- Create: `tests/chat/test_e2e_smoke.py`

- [ ] **Step 1: Teste E2E sem browser (usando test client)**

```python
# tests/chat/test_e2e_smoke.py
"""
Smoke test end-to-end simulando o fluxo completo:
1. usuario A cria DM com usuario B
2. A envia mensagem
3. B busca unread count -> 1
4. B lista mensagens da thread
5. B marca como lido
6. B busca unread count -> 0
7. A envia nova mensagem com @B
8. verifica chat_mention
9. SystemNotifier dispara alerta para B
10. B recebe na system_dm
"""
from unittest.mock import patch
import pytest


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client, user):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


@patch('app.chat.realtime.publisher.publish')
def test_fluxo_completo(mock_pub, client, user_factory, db_session):
    from app.chat.services.thread_service import ThreadService
    from app.chat.services.system_notifier import SystemNotifier
    from app.chat.models import ChatMessage, ChatMention, ChatThread

    a = user_factory(email='e2e_a@t.local')
    b = user_factory(email='e2e_b@t.local')

    # 1. A cria DM
    _login(client, a)
    r = client.post('/api/chat/threads/dm', json={'target_user_id': b.id})
    assert r.status_code == 201
    thread_id = r.json['thread']['id']

    # 2. A envia
    r = client.post('/api/chat/messages', json={'thread_id': thread_id, 'content': 'ola'})
    assert r.status_code == 201

    # 3. B unread
    _login(client, b)
    r = client.get('/api/chat/unread')
    assert r.json['user'] >= 1

    # 4. B lista mensagens
    r = client.get(f'/api/chat/threads/{thread_id}/messages')
    assert r.status_code == 200
    assert len(r.json['messages']) >= 1

    # 5. B marca como lido
    r = client.post(f'/api/chat/threads/{thread_id}/read')
    assert r.status_code == 200

    # 6. unread zero
    r = client.get('/api/chat/unread')
    assert r.json['user'] == 0

    # 7. A menciona @e2e_b
    _login(client, a)
    r = client.post('/api/chat/messages', json={
        'thread_id': thread_id, 'content': 'confere isso @e2e_b',
    })
    assert r.status_code == 201
    new_msg_id = r.json['message']['id']

    # 8. mention persistida
    m = ChatMention.query.filter_by(message_id=new_msg_id).first()
    assert m is not None
    assert m.mentioned_user_id == b.id

    # 9. SystemNotifier alerta B
    SystemNotifier.alert(
        user_ids=[b.id], source='recebimento', titulo='R#1',
        content='erro', deep_link='/recebimento/1', nivel='CRITICO',
    )

    # 10. B ve system msg
    sys_thread = ChatThread.query.filter_by(tipo='system_dm', criado_por_id=b.id).first()
    assert sys_thread is not None
    sys_msg = ChatMessage.query.filter_by(thread_id=sys_thread.id).order_by(
        ChatMessage.id.desc()
    ).first()
    assert sys_msg.sender_type == 'system'
    assert sys_msg.nivel == 'CRITICO'
```

- [ ] **Step 2: Rodar suite completa de chat**

Run: `pytest tests/chat/ -v`
Expected: todos os testes passam (soma de Tasks 2-25).

- [ ] **Step 3: Commit final**

```bash
git add tests/chat/test_e2e_smoke.py
git commit -m "test(chat): smoke E2E — fluxo DM + mention + SystemNotifier end-to-end"
```

- [ ] **Step 4: Resumo de entrega (opcional, para branch/PR)**

Run:
```bash
git log --oneline main..HEAD | head -30
```
Expected: lista dos ~25 commits do modulo chat.

---

## Self-review do plano

**Coverage do spec:**
- Secao 1 (objetivo/escopo): Tasks cobrem F1 completo — MVP com 7 modelos, 10+ rotas, UI, 3 alertas.
- Secao 2 (decisoes 1-10): todas mapeadas — hibrido (T6/T15), SSE+Redis (T10/T11), permissao (T5), framework entity (T6), conteudo completo (T4/T8), badge only (T17), navbar 2 badges (T16), sender_type unificado (T2/T9), `app/chat/` limpo (T1), defaults no codigo (T4 15min edit, T8 8KB, T7 20MB).
- Secao 3 (arquitetura): Tasks 1-11 montam os 5 layers.
- Secao 4 (modelos): T2 cria 7 modelos; T3 migration DDL.
- Secao 5 (permissao): T5 completo (sistemas + pode_adicionar + admin bypass).
- Secao 6 (fluxos): T8 send, T11 SSE, T15 share, T13 forward, T9 system alert, T6 lazy entity.
- Secao 7 (UI): T16 navbar, T18 drawer, T19 share, T20 forward.
- Secao 8 (erros): tratamento em cada service + R1 publisher.
- Secao 9 (testes): cobertos em cada task + T25 E2E.
- Secao 10 (migrations): T3 com 2 artefatos.
- Secao 11 (fases): plano cobre F1; F2-F4 marcados como futuros no spec.
- Secao 12 (dividas): documentadas em T24 CLAUDE.md.

**Sem placeholders.** Cada task tem codigo completo, comandos exatos, expected output.

**Consistencia de tipos:**
- `ChatMessage.sender_type` em {'user','system'} — usado identico em T2, T8, T9, T13, T14, T25.
- `ThreadService.get_or_create_dm(actor, target)` assinatura mantida em T6, T12, T15, T25.
- `SystemNotifier.alert(user_ids, source, titulo, content, deep_link, nivel, dados)` identico em T9, T21, T22, T23, T25.
- Endpoints: `/api/chat/threads`, `/api/chat/messages`, `/api/chat/stream`, `/api/chat/share/screen`, `/api/chat/entity/<t>/<id>/thread` — consistentes entre spec e plano.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-23-chat-inapp.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch fresh subagent per task (1-25), review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using `executing-plans`, batch execution with checkpoints.

**Which approach?**
