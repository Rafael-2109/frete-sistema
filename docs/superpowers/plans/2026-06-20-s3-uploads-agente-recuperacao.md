<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-20
-->
# Persistência S3 + Recuperação de Uploads do Agente — Implementation Plan

> **Papel:** plano de implementacao (task-by-task, TDD) da feature de persistencia S3 dos uploads do agente + recuperacao entre sessoes (IMP-2026-06-19-007), para execucao em worktree dedicada.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persistir os anexos do chat do Agente Web no S3 (hoje só em `/tmp` efêmero) e dar ao agente a capacidade de listar e recuperar uploads de sessões anteriores, eliminando a causa-raiz de IMP-2026-06-20-002 / IMP-2026-06-19-008 (anexos somem na rotação de sessão).

**Architecture:** Dual-write no `POST /api/upload` — o arquivo continua salvo em `/tmp` (uso imediato da sessão atual) **e** é persistido no S3 via `get_file_storage()`, com um manifesto `filename→s3_key` numa tabela nova `agente_upload` (escopo por `user_id`). A recuperação entre sessões é exposta como **2 MCP tools** adicionadas ao server `mcp__sessions__` existente (não como skill — ver Decisão D), reusando o user-scoping (`set_current_user_id`) que esse server já tem. O `resume_notice` (já editado no D8 2026-06-20) passa a apontar a tool de recuperação.

**Tech Stack:** Flask 3.1 + Flask-SQLAlchemy 2.0 · `app/utils/file_storage.py` (boto3, flag `USE_S3`) · Claude Agent SDK MCP (`create_enhanced_mcp_server` + `@tool`) · PostgreSQL.

## Indice

- [Contexto](#contexto)
- [Decisões de Design](#decisões-de-design-batidas-com-o-rafael-em-2026-06-20)
- [Global Constraints](#global-constraints)
- [File Structure](#file-structure)
- [Task 1 — Model AgenteUpload + migration](#task-1-model-agenteupload--migration)
- [Task 2 — Service + dual-write no upload](#task-2-service-de-persistência--dual-write-no-upload)
- [Task 3 — MCP tools de recuperação](#task-3-mcp-tools-list_session_uploads--recover_upload)
- [Task 4 — Wiring do resume_notice](#task-4-wiring-do-resume_notice-para-apontar-a-tool)
- [Task 5 — TTL + doc S3](#task-5-ttllifecycle--atualizar-doc-s3)
- [Self-Review](#self-review-feita-ao-escrever)
- [Execução](#execução)

## Contexto

Os anexos (PDF/xlsx/XML) que o usuário envia no chat do Agente Web são gravados só em `/tmp/agente_files/{user_id}/{session_id}/` — efêmero, **NÃO** S3 (`.claude/references/S3_STORAGE.md:111`). Na rotação de sessão por idle o `session_id` muda e os arquivos ficam órfãos; isso bloqueou import+faturamento de 6 NFs (~R$824k) da Rayssa (IMP-2026-06-20-002 / IMP-2026-06-19-008). O D8 de 2026-06-20 entregou apenas a **mitigação textual** (aviso no `resume_notice`, commit `37ca214cc`). **IMP-2026-06-19-007** é a correção **estrutural** — este plano: persistir no S3 + recuperar entre sessões, transformando o aviso em rede de segurança.

## Global Constraints

- **Migration = par DDL + Python** (regra CLAUDE.md): toda mudança de schema tem `.sql` + revisão Flask-Migrate em `migrations/versions/`.
- **Timezone Brasil naive**: usar `from app.utils.timezone import agora_brasil_naive` para qualquer datetime (regra `.claude/references/REGRAS_TIMEZONE.md`). Nunca `datetime.now()` cru.
- **S3 condicional a `USE_S3`**: `get_file_storage().use_s3` é `bool(USE_S3) and S3_AVAILABLE` (`app/utils/file_storage.py:86,118`). Com `USE_S3` off (dev), `save_file`/`download_file` revertem para disco local automaticamente — a feature degrada para no-op de persistência, sem quebrar.
- **Quota de upload (preexistente)**: `MAX_FILE_SIZE=10MB`, `MAX_FILES_PER_SESSION=20`, `MAX_TOTAL_SIZE_PER_SESSION=50MB` (`app/agente/routes/_constants.py:35,39,41`). O dual-write NÃO altera a quota de `/tmp`; a tabela de manifesto tem sua própria retenção (TTL ~90d, Decisão C).
- **PAD-CTX / orçamento de tools**: ao adicionar tool ao agente, consultar `.claude/references/ARQUITETURA_CONTEXTO_AGENTE.md`. As 2 tools entram no contexto fixo — manter descrições curtas. **NÃO usar skill**: o listing de skills do agente está em 7971/8000 chars (medido no pre-commit de 2026-06-20); uma skill nova estouraria o orçamento.
- **Sem `[skip render]`** em nenhum commit (regra). Commits frequentes.
- **Onde implementar**: worktree dedicada via `superpowers:using-git-worktrees` (NÃO na árvore principal). A worktree de manutenção `frete_sistema_manutencao` é exclusiva dos crons D8/semanal — não usar para esta feature.

## Decisões de Design (batidas com o Rafael em 2026-06-20)

| # | Decisão | Resolvido |
|---|---|---|
| A | Onde mora o manifesto `filename→s3_key` | **Tabela nova `agente_upload`** (query por `user_id`, rastreável, suporta TTL) |
| B | Escopo da recuperação entre sessões | **Por `user_id`, últimos N dias** (default 7) — reusa user-scoping do `sessions_server` |
| C | TTL/lifecycle do prefixo S3 | **Expira em ~90d** (`expira_em` na tabela + nota de lifecycle rule no bucket) |
| D | Como o agente recupera | **MCP tools** `list_session_uploads` + `recover_upload` no `mcp__sessions__` (não skill) |

---

## File Structure

- **Create** `app/agente/models.py` → adicionar classe `AgenteUpload` (manifesto). Responsabilidade: 1 linha por upload persistido no S3, com escopo `user_id` e TTL.
- **Create** `migrations/versions/<rev>_agente_upload.py` + `scripts/migrations/2026_06_2x_agente_upload.sql` (par DDL+Python).
- **Modify** `app/agente/routes/files.py:236-355` (`api_upload_file`) → dual-write S3 + registro no manifesto, após `file.save(file_path)` (linha 334).
- **Create** `app/agente/services/upload_recovery_service.py` → lógica de persistência S3 e recuperação (reuso entre route e tools; mantém a route fina).
- **Modify** `app/agente/tools/session_search_tool.py` → +2 tools (`list_session_uploads`, `recover_upload`) + registro no `sessions_server` (linha 1170-1177) + `set_current_session_id` ContextVar.
- **Modify** `app/agente/sdk/hooks.py` (`_build_resume_fallback_notice`, bloco `aviso_anexos` ~139-146) → apontar a tool de recuperação.
- **Modify** `.claude/references/S3_STORAGE.md` (módulo 1) → uploads do chat agora vão para S3.
- **Test** `tests/agente/test_agente_upload_model.py`, `tests/agente/test_upload_recovery_service.py`, `tests/agente/tools/test_upload_recovery_tools.py`.

---

## Task 1: Model `AgenteUpload` + migration

**Files:**
- Modify: `app/agente/models.py` (adicionar classe ao fim)
- Create: `scripts/migrations/2026_06_2x_agente_upload.sql`
- Create: `migrations/versions/<rev>_agente_upload.py` (via `flask db migrate`)
- Test: `tests/agente/test_agente_upload_model.py`

**Interfaces:**
- Produces: `AgenteUpload` ORM model com colunas `id, user_id, session_id, file_id, original_name, safe_name, s3_key, file_type, size_bytes, criado_em, expira_em, ativo` e `UNIQUE(user_id, safe_name)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agente/test_agente_upload_model.py
from datetime import timedelta
from app.utils.timezone import agora_brasil_naive


def test_agente_upload_persiste_e_consulta_por_user(db):
    from app.agente.models import AgenteUpload
    now = agora_brasil_naive()
    up = AgenteUpload(
        user_id=78, session_id='sess-abc', file_id='ab12cd34',
        original_name='nf_abril.xlsx', safe_name='ab12cd34_nf_abril.xlsx',
        s3_key='agente-uploads/78/ab12cd34_nf_abril.xlsx',
        file_type='excel', size_bytes=12345,
        criado_em=now, expira_em=now + timedelta(days=90), ativo=True,
    )
    db.session.add(up)
    db.session.flush()
    achados = AgenteUpload.query.filter_by(user_id=78, ativo=True).all()
    assert len(achados) == 1
    assert achados[0].s3_key == 'agente-uploads/78/ab12cd34_nf_abril.xlsx'


def test_agente_upload_unique_user_safe_name(db):
    import pytest
    from sqlalchemy.exc import IntegrityError
    from app.agente.models import AgenteUpload
    now = agora_brasil_naive()
    kw = dict(user_id=78, session_id='s', file_id='x', original_name='a.pdf',
              safe_name='x_a.pdf', s3_key='k', file_type='pdf',
              size_bytes=1, criado_em=now)
    db.session.add(AgenteUpload(**kw)); db.session.flush()
    db.session.add(AgenteUpload(**kw))
    with pytest.raises(IntegrityError):
        db.session.flush()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agente/test_agente_upload_model.py -q`
Expected: FAIL com `ImportError`/`cannot import name 'AgenteUpload'`.

- [ ] **Step 3: Add the model**

```python
# app/agente/models.py  (ao fim do arquivo)
class AgenteUpload(db.Model):
    """Manifesto de uploads do chat persistidos no S3 (IMP-2026-06-19-007).

    1 linha por arquivo enviado em /api/upload. Permite recuperar anexos de
    sessoes anteriores quando a rotacao de sessao orfana o /tmp local.
    """
    __tablename__ = 'agente_upload'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    file_id = db.Column(db.String(16), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    safe_name = db.Column(db.String(280), nullable=False)
    s3_key = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(20), nullable=True)
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    criado_em = db.Column(db.DateTime, nullable=False)
    expira_em = db.Column(db.DateTime, nullable=True, index=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'safe_name', name='uq_agente_upload_user_safe'),
    )
```

- [ ] **Step 4: Generate migration (par DDL + Python)**

Run: `flask db migrate -m "agente_upload (manifesto S3 de uploads do chat)"`
Então criar o `.sql` espelho em `scripts/migrations/2026_06_2x_agente_upload.sql`:

```sql
CREATE TABLE agente_upload (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL,
    session_id    VARCHAR(64) NOT NULL,
    file_id       VARCHAR(16) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    safe_name     VARCHAR(280) NOT NULL,
    s3_key        VARCHAR(512) NOT NULL,
    file_type     VARCHAR(20),
    size_bytes    INTEGER NOT NULL DEFAULT 0,
    criado_em     TIMESTAMP NOT NULL,
    expira_em     TIMESTAMP,
    ativo         BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_agente_upload_user_safe UNIQUE (user_id, safe_name)
);
CREATE INDEX ix_agente_upload_user_id ON agente_upload (user_id);
CREATE INDEX ix_agente_upload_session_id ON agente_upload (session_id);
CREATE INDEX ix_agente_upload_expira_em ON agente_upload (expira_em);
CREATE INDEX ix_agente_upload_ativo ON agente_upload (ativo);
```

Revisar o `.py` gerado para bater com este DDL (mesmas colunas/índices/constraint).

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/agente/test_agente_upload_model.py -q`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add app/agente/models.py migrations/versions/ scripts/migrations/2026_06_2x_agente_upload.sql tests/agente/test_agente_upload_model.py
git commit -m "feat(agente): tabela agente_upload (manifesto S3 de uploads do chat)"
```

---

## Task 2: Service de persistência + dual-write no upload

**Files:**
- Create: `app/agente/services/upload_recovery_service.py`
- Modify: `app/agente/routes/files.py:329-355` (após `file.save(file_path)`)
- Test: `tests/agente/test_upload_recovery_service.py`

**Interfaces:**
- Consumes: `AgenteUpload` (Task 1); `get_file_storage` (`app/utils/file_storage.py:521`); `save_file(file, folder, filename=None)` retorna o path/key (`:135,169`).
- Produces:
  - `persistir_upload_s3(file, *, user_id, session_id, file_id, original_name, safe_name, file_type, size_bytes) -> AgenteUpload | None` — grava no S3 (se `use_s3`) e cria/atualiza a linha do manifesto. Retorna `None` se `use_s3` off (sem persistência, não-fatal).
  - `listar_uploads_usuario(user_id, *, dias=7) -> list[dict]`
  - `recuperar_upload(user_id, file_id, *, target_session_id) -> str | None` — baixa do S3 para `_get_session_folder(target_session_id)`, retorna path local.

- [ ] **Step 1: Write the failing test**

```python
# tests/agente/test_upload_recovery_service.py
from app.utils.timezone import agora_brasil_naive


def test_listar_uploads_usuario_filtra_por_recencia(db):
    from datetime import timedelta
    from app.agente.models import AgenteUpload
    from app.agente.services.upload_recovery_service import listar_uploads_usuario
    now = agora_brasil_naive()
    db.session.add(AgenteUpload(
        user_id=78, session_id='s1', file_id='a', original_name='novo.pdf',
        safe_name='a_novo.pdf', s3_key='k1', file_type='pdf', size_bytes=1,
        criado_em=now, expira_em=now + timedelta(days=90), ativo=True))
    db.session.add(AgenteUpload(
        user_id=78, session_id='s0', file_id='b', original_name='velho.pdf',
        safe_name='b_velho.pdf', s3_key='k2', file_type='pdf', size_bytes=1,
        criado_em=now - timedelta(days=30), ativo=True))
    db.session.flush()
    achados = listar_uploads_usuario(78, dias=7)
    nomes = {u['original_name'] for u in achados}
    assert 'novo.pdf' in nomes and 'velho.pdf' not in nomes
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agente/test_upload_recovery_service.py -q`
Expected: FAIL com `ModuleNotFoundError: app.agente.services.upload_recovery_service`.

- [ ] **Step 3: Write the service**

```python
# app/agente/services/upload_recovery_service.py
"""Persistencia S3 + recuperacao de uploads do chat (IMP-2026-06-19-007)."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import List, Dict, Optional

from app import db
from app.agente.models import AgenteUpload
from app.utils.file_storage import get_file_storage
from app.utils.timezone import agora_brasil_naive

logger = logging.getLogger(__name__)

TTL_DIAS = 90
S3_PREFIXO = 'agente-uploads'


def persistir_upload_s3(file, *, user_id, session_id, file_id, original_name,
                        safe_name, file_type, size_bytes) -> Optional[AgenteUpload]:
    storage = get_file_storage()
    if not storage.use_s3:
        return None  # dev / USE_S3 off — sem persistencia, nao-fatal
    folder = f"{S3_PREFIXO}/{user_id}"
    file.seek(0)
    s3_key = storage.save_file(file, folder, filename=safe_name)  # retorna folder/filename
    now = agora_brasil_naive()
    existente = AgenteUpload.query.filter_by(user_id=user_id, safe_name=safe_name).first()
    if existente:
        existente.s3_key = s3_key
        existente.ativo = True
        existente.criado_em = now
        existente.expira_em = now + timedelta(days=TTL_DIAS)
        db.session.flush()
        return existente
    up = AgenteUpload(
        user_id=user_id, session_id=session_id, file_id=file_id,
        original_name=original_name, safe_name=safe_name, s3_key=s3_key,
        file_type=file_type, size_bytes=size_bytes, criado_em=now,
        expira_em=now + timedelta(days=TTL_DIAS), ativo=True)
    db.session.add(up)
    db.session.flush()
    return up


def listar_uploads_usuario(user_id, *, dias=7) -> List[Dict]:
    corte = agora_brasil_naive() - timedelta(days=dias)
    rows = (AgenteUpload.query
            .filter(AgenteUpload.user_id == user_id, AgenteUpload.ativo.is_(True),
                    AgenteUpload.criado_em >= corte)
            .order_by(AgenteUpload.criado_em.desc()).all())
    return [{
        'file_id': r.file_id, 'original_name': r.original_name,
        'file_type': r.file_type, 'size_bytes': r.size_bytes,
        'session_id': r.session_id, 's3_key': r.s3_key,
        'criado_em': r.criado_em.isoformat() if r.criado_em else None,
    } for r in rows]


def recuperar_upload(user_id, file_id, *, target_session_id) -> Optional[str]:
    import os
    from app.agente.routes.files import _get_session_folder
    row = (AgenteUpload.query
           .filter_by(user_id=user_id, file_id=file_id, ativo=True)
           .order_by(AgenteUpload.criado_em.desc()).first())
    if not row:
        return None
    storage = get_file_storage()
    conteudo = storage.download_file(row.s3_key)  # bytes
    if conteudo is None:
        return None
    destino_dir = _get_session_folder(target_session_id)
    os.makedirs(destino_dir, exist_ok=True)
    destino = os.path.join(destino_dir, row.safe_name)
    with open(destino, 'wb') as fh:
        fh.write(conteudo)
    return destino
```

> ⚠️ Confirmar o tipo de retorno de `storage.download_file` (`app/utils/file_storage.py:423`) — se retorna `bytes`, o código acima está certo; se retorna um path/stream, ajustar a gravação. Confirmar também o retorno de `save_file` (`:169` retorna `{folder}/{filename}`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agente/test_upload_recovery_service.py -q`
Expected: PASS.

- [ ] **Step 5: Wire o dual-write na route**

Em `app/agente/routes/files.py`, logo após `file.save(file_path)` (linha 334):

```python
        # IMP-2026-06-19-007: persiste no S3 + manifesto (recuperavel entre sessoes).
        # Nao-fatal: se USE_S3 off ou S3 falhar, o upload local segue valido.
        try:
            from app.agente.services.upload_recovery_service import persistir_upload_s3
            persistir_upload_s3(
                file, user_id=current_user.id, session_id=session_id,
                file_id=file_id, original_name=original_name, safe_name=safe_name,
                file_type=_get_file_type(original_name), size_bytes=file_size)
            db.session.commit()
        except Exception as s3_err:
            db.session.rollback()
            logger.warning(f"[AGENTE] Persistencia S3 do upload falhou (nao fatal): {s3_err}")
```

(Confirmar que `db` e `current_user` estão importados em `files.py`; `current_user` já é usado em `_get_session_folder`.)

- [ ] **Step 6: Run tests + commit**

```bash
python -m pytest tests/agente/test_upload_recovery_service.py tests/agente/test_agente_upload_model.py -q
git add app/agente/services/upload_recovery_service.py app/agente/routes/files.py tests/agente/test_upload_recovery_service.py
git commit -m "feat(agente): dual-write S3 de uploads do chat + service de recuperacao"
```

---

## Task 3: MCP tools `list_session_uploads` + `recover_upload`

**Files:**
- Modify: `app/agente/tools/session_search_tool.py` (adicionar 2 tools + ao `tools=[...]` em `:1170`; adicionar `set_current_session_id`)
- Test: `tests/agente/tools/test_upload_recovery_tools.py`

**Interfaces:**
- Consumes: `listar_uploads_usuario`, `recuperar_upload` (Task 2); `_resolve_user_id(args)` e `_execute_with_context` (`session_search_tool.py:61,113`).
- Produces: tools MCP `mcp__sessions__list_session_uploads(dias?)` e `mcp__sessions__recover_upload(file_id, target_session_id)`.

- [ ] **Step 1: Write the failing test** (testa a lógica de recência via service; as tools são wrappers finos)

```python
# tests/agente/tools/test_upload_recovery_tools.py
from app.utils.timezone import agora_brasil_naive
from datetime import timedelta


def test_recover_upload_inexistente_retorna_none(db):
    from app.agente.services.upload_recovery_service import recuperar_upload
    assert recuperar_upload(78, 'nao-existe', target_session_id='s9') is None
```

- [ ] **Step 2: Run test to verify it fails / passes baseline**

Run: `python -m pytest tests/agente/tools/test_upload_recovery_tools.py -q`
Expected: PASS (valida o caminho `None` do service antes de wirar a tool).

- [ ] **Step 3: Add the tools** (espelhar EXATAMENTE o decorator de `search_sessions`, `session_search_tool.py:248-261`: `@tool("nome","desc",{input_schema}, annotations=ToolAnnotations(readOnlyHint=...), output_schema=...)`, função `async def`, retorno `{"content":[...], "structuredContent": {...}}`)

```python
    # --- IMP-2026-06-19-007: recuperacao de uploads entre sessoes ---
    UPLOADS_LIST_SCHEMA = {
        "type": "object",
        "properties": {
            "count": {"type": "integer"},
            "uploads": {"type": "array", "items": {"type": "object", "properties": {
                "file_id": {"type": "string"}, "original_name": {"type": "string"},
                "file_type": {"type": ["string", "null"]}, "size_bytes": {"type": "integer"},
                "session_id": {"type": "string"}, "criado_em": {"type": ["string", "null"]},
            }}},
        },
        "required": ["count", "uploads"],
    }

    @tool(
        "list_session_uploads",
        "Lista anexos (PDF/xlsx/XML) que o usuario enviou em sessoes ANTERIORES e que "
        "podem ter sumido do /tmp na rotacao de sessao. Use quando o usuario disser que "
        "perdeu arquivos ou apos aviso de rotacao. Retorna file_id para recuperar.",
        {"type": "object", "properties": {
            "dias": {"type": "integer", "description": "Janela em dias (default 7)"}},
         "required": []},
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                                    idempotentHint=True, openWorldHint=False),
        output_schema=UPLOADS_LIST_SCHEMA,
    )
    async def list_session_uploads(args: Dict[str, Any]) -> Dict[str, Any]:
        """Lista uploads anteriores do usuario (por user_id, recencia)."""
        try:
            user_id = _resolve_user_id(args)
        except (RuntimeError, PermissionError) as e:
            return {"content": [{"type": "text", "text": f"Erro: {e}"}], "is_error": True}
        dias = int(args.get("dias") or 7)

        def _run():
            from app.agente.services.upload_recovery_service import listar_uploads_usuario
            return listar_uploads_usuario(user_id, dias=dias)
        uploads = _execute_with_context(_run)
        structured = {"count": len(uploads), "uploads": uploads}
        if not uploads:
            return {"content": [{"type": "text", "text": "Nenhum upload anterior encontrado."}],
                    "structuredContent": structured}
        linhas = [f"- {u['original_name']} (file_id={u['file_id']}, {u['file_type']}, "
                  f"{u['size_bytes']} bytes, {u['criado_em']})" for u in uploads]
        return {"content": [{"type": "text", "text": "\n".join(linhas)}],
                "structuredContent": structured}

    @tool(
        "recover_upload",
        "Recupera para a sessao ATUAL um anexo enviado numa sessao anterior (baixa do S3 "
        "para /tmp). Passe o file_id obtido de list_session_uploads e o session_id atual.",
        {"type": "object", "properties": {
            "file_id": {"type": "string", "description": "file_id do upload (de list_session_uploads)"},
            "target_session_id": {"type": "string", "description": "session_id da conversa atual"}},
         "required": ["file_id", "target_session_id"]},
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                    idempotentHint=True, openWorldHint=False),
    )
    async def recover_upload(args: Dict[str, Any]) -> Dict[str, Any]:
        """Baixa um upload anterior para o /tmp da sessao atual."""
        try:
            user_id = _resolve_user_id(args)
        except (RuntimeError, PermissionError) as e:
            return {"content": [{"type": "text", "text": f"Erro: {e}"}], "is_error": True}
        file_id = (args.get("file_id") or "").strip()
        target = (args.get("target_session_id") or "").strip()
        if not file_id or not target:
            return {"content": [{"type": "text", "text": "Erro: file_id e target_session_id obrigatorios."}],
                    "is_error": True}

        def _run():
            from app.agente.services.upload_recovery_service import recuperar_upload
            return recuperar_upload(user_id, file_id, target_session_id=target)
        path = _execute_with_context(_run)
        if not path:
            return {"content": [{"type": "text", "text": f"Upload {file_id} nao encontrado ou indisponivel."}],
                    "is_error": True}
        return {"content": [{"type": "text", "text": f"Arquivo recuperado para a sessao atual: {path}"}]}
```

Adicionar ambas ao registro em `session_search_tool.py:1170`:

```python
        tools=[
            search_sessions,
            list_recent_sessions,
            semantic_search_sessions,
            list_session_users,
            get_subagent_transcript,
            get_session_transcript,
            list_session_uploads,   # IMP-19-007
            recover_upload,         # IMP-19-007
        ],
```

E atualizar o log (`:1180`) de `6 tools` → `8 tools`.

- [ ] **Step 4: Run tests + sanity import**

Run: `python -c "import app.agente.tools.session_search_tool"` (sem erro de sintaxe/import)
Run: `python -m pytest tests/agente/tools/test_upload_recovery_tools.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agente/tools/session_search_tool.py tests/agente/tools/test_upload_recovery_tools.py
git commit -m "feat(agente): tools mcp__sessions__ list_session_uploads + recover_upload"
```

---

## Task 4: Wiring do `resume_notice` para apontar a tool

**Files:**
- Modify: `app/agente/sdk/hooks.py` (bloco `aviso_anexos`, ~139-146)
- Test: `tests/agente/routes/test_rotation_continuity.py` (assert do texto)

**Interfaces:**
- Consumes: o `aviso_anexos` já existente (editado no commit `37ca214cc`).

- [ ] **Step 1: Add the failing assert**

```python
# em tests/agente/routes/test_rotation_continuity.py, na classe TestResumeFallbackNotice
def test_resume_notice_aponta_tool_de_recuperacao():
    from app.agente.sdk.hooks import _build_resume_fallback_notice
    for reason in ('rotated', 'resume_failed'):
        notice = _build_resume_fallback_notice(reason)
        assert 'list_session_uploads' in notice
        assert 'recover_upload' in notice
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/agente/routes/test_rotation_continuity.py -q`
Expected: FAIL (texto ainda não menciona as tools).

- [ ] **Step 3: Update `aviso_anexos`** (acrescentar 1 frase ao texto existente, em ambos os ramos): "Para anexos de sessoes anteriores, use `list_session_uploads` e depois `recover_upload`."

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/agente/routes/test_rotation_continuity.py -q`
Expected: PASS (incluindo os asserts já existentes).

- [ ] **Step 5: Commit**

```bash
git add app/agente/sdk/hooks.py tests/agente/routes/test_rotation_continuity.py
git commit -m "feat(agente): resume_notice aponta tools de recuperacao de upload"
```

---

## Task 5: TTL/lifecycle + atualizar doc S3

**Files:**
- Modify: `.claude/references/S3_STORAGE.md` (módulo 1 deixa de ser "NÃO usa S3")
- Create/Modify: nota de lifecycle rule do prefixo `agente-uploads/` (infra — registrar no doc + cron de limpeza opcional)

- [ ] **Step 1:** Atualizar `S3_STORAGE.md` módulo 1: "Upload de arquivos do chat" agora grava dual (`/tmp` + `s3://.../agente-uploads/{user_id}/{safe_name}`), com manifesto `agente_upload` e TTL 90d (`expira_em`). Atualizar a linha de lifecycle (`S3_STORAGE.md:423`) registrando `agente-uploads/` como candidato a expiração de 90d.
- [ ] **Step 2:** (Opcional, baixo ROI) cron/limpeza: job que marca `ativo=False` e remove do S3 onde `expira_em < agora`. Pode ficar para um plano futuro — registrar como follow-up se não implementar.
- [ ] **Step 3: Commit**

```bash
git add .claude/references/S3_STORAGE.md
git commit -m "docs(s3): uploads do chat agora persistem em S3 (agente-uploads/, TTL 90d)"
```

---

## Self-Review (feita ao escrever)

- **Cobertura das decisões:** A→Task 1 (tabela); B→Task 2/3 (`dias`, user-scoping); C→Task 1/2/5 (`expira_em`, TTL 90d); D→Task 3 (tools no `sessions_server`). ✓
- **Liga com o D8:** Task 4 conecta o `resume_notice` (mitigação textual já mergeada) à correção estrutural. ✓
- **Pontos a confirmar em runtime** (sinalizados inline, não placeholders): retorno de `download_file`/`save_file` (`file_storage.py:169,423`); imports de `db`/`current_user` em `files.py`. A próxima sessão valida no Step de cada task.
- **Degradação segura:** com `USE_S3` off (dev), `persistir_upload_s3` retorna `None` e nada quebra; as tools listam vazio. ✓

## Execução

Implementar em **worktree dedicada** (`superpowers:using-git-worktrees`), não na árvore principal nem na worktree de manutenção. Ordem: Task 1 → 5 (cada uma com deliverable testável). Migration (Task 1) exige `flask db migrate` + revisão do `.py` contra o `.sql`.
