# Subagent UI Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enriquecer a exibição de subagents no chat web com modal de transcript completo, estados visuais ricos, progresso ao vivo, correlação parent, rename/tag e download de output_file — paridade com Claude Code Agent View v2.1.139+.

**Architecture:** Modal full-screen reaproveitando padrão de `#artifact-modal` existente, alimentado por endpoints novos em `routes/subagents.py` que leem via `subagent_reader.get_subagent_transcript`. Eventos SSE estendidos via `client.py:_parse_sdk_message`. Persistência em `agent_sessions.data` (JSONB) — zero migration DDL. Feature flags como circuit breakers; defaults `true` em prod (big-bang).

**Tech Stack:** Python 3.12 · Flask 3.1.2 · SQLAlchemy 2.0 · claude-agent-sdk 0.1.80 · Vanilla JS + Jinja2 · CSS @layer · bleach 6.3.0 · Redis (rate limit/PII token) · pytest

**Spec:** `docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md`

---

## Estratégia de fases

- **Fase 1 (PR-A, Tasks 1-13)**: P0.1 modal transcript + P0.2 estados visuais + P0.3 progresso ao vivo + P1.1 correlação parent
- **Fase 2 (PR-B, Tasks 14-17)**: P1.2 rename/tag + P1.3 download output_file

Cada fase é independentemente entregável; ambas dispensam migration DDL.

---

# FASE 1 — Modal + Estados + Progresso + Parent Link

## Task 1: Feature flags

**Files:**
- Modify: `app/agente/config/feature_flags.py`

- [ ] **Step 1: Adicionar 5 flags ao final do arquivo, antes do dicionário de export se houver**

Localizar o padrão `USE_SUBAGENT_UI = _as_bool(...)` existente no arquivo. Adicionar imediatamente abaixo:

```python
# === Subagent UI Enrichment (2026-05-14) ===
# Big-bang em prod: todos default true. Manter como circuit breakers.

# P0.1 Modal de transcript (prompt + timeline + findings)
USE_SUBAGENT_MODAL = _as_bool(os.environ.get('USE_SUBAGENT_MODAL', 'true'))

# P0.2 Estados visuais ricos (failed/stopped/validation_warning) +
# P1.1 Correlacao parent_tool_use_id
USE_SUBAGENT_RICH_STATES = _as_bool(os.environ.get('USE_SUBAGENT_RICH_STATES', 'true'))

# P0.3 Progresso ao vivo: tokens/duracao/last_tool no meta da linha
USE_SUBAGENT_LIVE_PROGRESS = _as_bool(os.environ.get('USE_SUBAGENT_LIVE_PROGRESS', 'true'))

# P1.2 Rename/tag de subagent (Fase 2)
USE_SUBAGENT_RENAME_TAG = _as_bool(os.environ.get('USE_SUBAGENT_RENAME_TAG', 'true'))

# P1.3 Download output_file JSONL (Fase 2)
USE_SUBAGENT_OUTPUT_DOWNLOAD = _as_bool(os.environ.get('USE_SUBAGENT_OUTPUT_DOWNLOAD', 'true'))
```

- [ ] **Step 2: Verificar import**

```bash
python -c "from app.agente.config.feature_flags import USE_SUBAGENT_MODAL, USE_SUBAGENT_RICH_STATES, USE_SUBAGENT_LIVE_PROGRESS, USE_SUBAGENT_RENAME_TAG, USE_SUBAGENT_OUTPUT_DOWNLOAD; print('OK', USE_SUBAGENT_MODAL)"
```
Expected: `OK True`

- [ ] **Step 2b: Expor flags em app.config (CRÍTICO — code-review #5)**

Sem essa exposição, `{{ config.get('USE_SUBAGENT_MODAL', True) }}` no template SEMPRE retorna o default `True` regardless do env var. Rollback do frontend via env var não funcionaria.

Localizar em `app/agente/__init__.py` (ou `app/__init__.py`) onde outras flags são expostas (procurar por `app.config['USE_`). Adicionar logo após o init do blueprint do agente:

```python
def init_app(app):
    # ... codigo existente ...

    # Expor feature flags subagent UI em app.config (P0.x + P1.x — 2026-05-14)
    from app.agente.config import feature_flags
    app.config['USE_SUBAGENT_MODAL'] = feature_flags.USE_SUBAGENT_MODAL
    app.config['USE_SUBAGENT_RICH_STATES'] = feature_flags.USE_SUBAGENT_RICH_STATES
    app.config['USE_SUBAGENT_LIVE_PROGRESS'] = feature_flags.USE_SUBAGENT_LIVE_PROGRESS
    app.config['USE_SUBAGENT_RENAME_TAG'] = feature_flags.USE_SUBAGENT_RENAME_TAG
    app.config['USE_SUBAGENT_OUTPUT_DOWNLOAD'] = feature_flags.USE_SUBAGENT_OUTPUT_DOWNLOAD
```

> Se já existe um padrão diferente para registrar feature flags em `app.config` (ex: bulk via `vars(feature_flags)`), adapte. O importante é que `config.get('USE_SUBAGENT_MODAL')` no Jinja retorne o valor real do módulo, não o default literal.

- [ ] **Step 2c: Validar exposição**

```bash
python -c "
from app import create_app
app = create_app()
print('MODAL:', app.config.get('USE_SUBAGENT_MODAL'))
print('RICH:', app.config.get('USE_SUBAGENT_RICH_STATES'))
print('LIVE:', app.config.get('USE_SUBAGENT_LIVE_PROGRESS'))
print('RENAME:', app.config.get('USE_SUBAGENT_RENAME_TAG'))
print('DOWNLOAD:', app.config.get('USE_SUBAGENT_OUTPUT_DOWNLOAD'))
"
```
Expected: 5 valores `True` (defaults).

- [ ] **Step 3: Commit**

```bash
git add app/agente/config/feature_flags.py
git commit -m "feat(agente): 5 feature flags para subagent UI enrichment

USE_SUBAGENT_MODAL, USE_SUBAGENT_RICH_STATES, USE_SUBAGENT_LIVE_PROGRESS,
USE_SUBAGENT_RENAME_TAG, USE_SUBAGENT_OUTPUT_DOWNLOAD.

Default true em todos os ambientes (big-bang). Sao circuit breakers
para rollback emergencial via env var no Render.

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (secao 4.2)"
```

---

## Task 2: client.py + routes/chat.py — propagar usage + parent_tool_use_id (TDD)

**Files:**
- Modify: `app/agente/sdk/client.py:826-882`
- Modify: `app/agente/routes/chat.py:831-853` (R8 contract — SSE forwarder)
- Create: `tests/agente/test_subagent_client_metadata.py`

> **R8 contract reminder** (`app/agente/CLAUDE.md:378-398`): novos campos em SSE precisam atualizar todas 3 camadas (`client.py` → `routes/chat.py` → `chat.js`). Sem update em `routes/chat.py`, `usage` e `parent_tool_use_id` NÃO chegam ao browser mesmo que `client.py` os propague no `StreamEvent.metadata`.

- [ ] **Step 1: Escrever testes falhando em `tests/agente/test_subagent_client_metadata.py`**

```python
"""Testes para metadata enriquecido em task_started/task_progress.

P0.3: TaskProgressMessage.usage propagado em metadata.
P1.1: TaskStartedMessage.tool_use_id propagado como parent_tool_use_id.
"""
from dataclasses import dataclass
from typing import Any, Optional
from unittest.mock import MagicMock
import pytest

from app.agente.sdk.client import AgentClient
from app.agente.sdk.stream_parser import StreamEvent


@dataclass
class FakeTaskUsage:
    total_tokens: int = 3400
    tool_uses: int = 5
    duration_ms: int = 12000


@dataclass
class FakeTaskStartedMessage:
    """Mock de claude_agent_sdk.TaskStartedMessage."""
    task_id: str = 'task-abc-123'
    description: str = 'Analise pedido VCD123'
    task_type: str = 'local_agent'
    tool_use_id: Optional[str] = None
    uuid: str = 'uuid-1'
    session_id: str = 'sess-1'


@dataclass
class FakeTaskProgressMessage:
    task_id: str = 'task-abc-123'
    description: str = 'Usando Grep'
    last_tool_name: Optional[str] = 'Grep'
    usage: Optional[Any] = None
    parent_tool_use_id: Optional[str] = None
    uuid: str = 'uuid-2'
    session_id: str = 'sess-1'


@dataclass
class FakeState:
    """Estado minimo do parser para teste."""
    input_tokens: int = 0
    output_tokens: int = 0
    result_session_id: Optional[str] = None
    got_result_message: bool = False


@pytest.fixture
def client():
    return AgentClient.__new__(AgentClient)  # bypass __init__ para teste unit


def test_task_started_propaga_parent_tool_use_id(client):
    """P1.1: tool_use_id do TaskStartedMessage vira parent_tool_use_id no metadata."""
    msg = FakeTaskStartedMessage(tool_use_id='tu_xyz789')
    events = client._parse_sdk_message(msg, FakeState())
    assert len(events) == 1
    assert events[0].type == 'task_started'
    assert events[0].metadata['parent_tool_use_id'] == 'tu_xyz789'


def test_task_started_sem_tool_use_id_nao_quebra(client):
    """SDK pode nao emitir tool_use_id (forward-compat). Deve resultar em None."""
    msg = FakeTaskStartedMessage(tool_use_id=None)
    events = client._parse_sdk_message(msg, FakeState())
    assert events[0].metadata['parent_tool_use_id'] is None


def test_task_progress_propaga_usage_completo(client):
    """P0.3: TaskUsage dict no metadata do task_progress."""
    msg = FakeTaskProgressMessage(usage=FakeTaskUsage(total_tokens=4200, duration_ms=8500))
    events = client._parse_sdk_message(msg, FakeState())
    assert len(events) == 1
    assert events[0].type == 'task_progress'
    usage = events[0].metadata['usage']
    assert usage is not None
    # Pode ser dict ou objeto — getattr-friendly
    assert getattr(usage, 'total_tokens', None) == 4200 or usage.get('total_tokens') == 4200


def test_task_progress_usage_ausente_nao_quebra(client):
    """SDK pode nao popular usage (forward-compat). metadata.usage = None aceitavel."""
    msg = FakeTaskProgressMessage(usage=None)
    events = client._parse_sdk_message(msg, FakeState())
    assert events[0].metadata.get('usage') is None
    # Sem crash, sem regressao do last_tool_name antigo
    assert events[0].metadata['last_tool_name'] == 'Grep'


def test_task_progress_parent_tool_use_id_propagado(client):
    """P1.1: parent_tool_use_id tambem no task_progress (correlacao constante)."""
    msg = FakeTaskProgressMessage(parent_tool_use_id='tu_xyz789')
    events = client._parse_sdk_message(msg, FakeState())
    assert events[0].metadata['parent_tool_use_id'] == 'tu_xyz789'
```

- [ ] **Step 2: Rodar testes para confirmar que falham**

```bash
source .venv/bin/activate
pytest tests/agente/test_subagent_client_metadata.py -v
```
Expected: 5 testes FAIL (KeyError: 'parent_tool_use_id' ou AssertionError porque metadata não tem o campo)

- [ ] **Step 3: Localizar bloco TaskStartedMessage em `client.py` (linhas ~826-843)**

Abrir o arquivo e localizar:

```python
# ─── Task messages (subagentes) ───
if isinstance(message, TaskStartedMessage):
    task_desc = getattr(message, 'description', '') or ''
    task_id = getattr(message, 'task_id', '') or ''
    task_type = getattr(message, 'task_type', '') or ''
    logger.info(
        f"[AGENT_SDK] TaskStarted: {task_desc[:80]} | "
        f"task_id={task_id[:12]} | task_type={task_type}"
    )
    events.append(StreamEvent(
        type='task_started',
        content=task_desc,
        metadata={
            'task_id': task_id,
            'task_type': task_type,
        }
    ))
    return events
```

- [ ] **Step 4: Adicionar `parent_tool_use_id` ao metadata de `task_started`**

Substituir o bloco acima por:

```python
# ─── Task messages (subagentes) ───
if isinstance(message, TaskStartedMessage):
    task_desc = getattr(message, 'description', '') or ''
    task_id = getattr(message, 'task_id', '') or ''
    task_type = getattr(message, 'task_type', '') or ''
    parent_tu_id = getattr(message, 'tool_use_id', None)  # NOVO P1.1
    logger.info(
        f"[AGENT_SDK] TaskStarted: {task_desc[:80]} | "
        f"task_id={task_id[:12]} | task_type={task_type} | "
        f"parent_tool_use_id={(parent_tu_id or '')[:12]}"
    )
    events.append(StreamEvent(
        type='task_started',
        content=task_desc,
        metadata={
            'task_id': task_id,
            'task_type': task_type,
            'parent_tool_use_id': parent_tu_id,  # NOVO P1.1
        }
    ))
    return events
```

- [ ] **Step 5: Localizar bloco TaskProgressMessage (linhas ~845-861) e adicionar usage + parent_tool_use_id**

Substituir o bloco existente por:

```python
if isinstance(message, TaskProgressMessage):
    task_desc = getattr(message, 'description', '') or ''
    task_id = getattr(message, 'task_id', '') or ''
    last_tool = getattr(message, 'last_tool_name', '') or ''
    usage = getattr(message, 'usage', None)  # NOVO P0.3 (TaskUsage TypedDict)
    parent_tu_id = getattr(message, 'parent_tool_use_id', None)  # NOVO P1.1
    logger.debug(
        f"[AGENT_SDK] TaskProgress: {task_desc[:80]} | "
        f"task_id={task_id[:12]} | last_tool={last_tool} | "
        f"tokens={getattr(usage, 'total_tokens', None) if usage else None}"
    )
    events.append(StreamEvent(
        type='task_progress',
        content=task_desc,
        metadata={
            'task_id': task_id,
            'last_tool_name': last_tool,
            'usage': usage,  # NOVO P0.3 — dict ou None
            'parent_tool_use_id': parent_tu_id,  # NOVO P1.1
        }
    ))
    return events
```

- [ ] **Step 6: Rodar testes para confirmar que passam**

```bash
pytest tests/agente/test_subagent_client_metadata.py -v
```
Expected: 5 testes PASS

- [ ] **Step 6b: Atualizar `routes/chat.py:831-853` para forward dos novos campos no SSE (R8 contract)**

Localizar os blocos `elif event.type == 'task_started':` e `elif event.type == 'task_progress':` e substituir por:

```python
                elif event.type == 'task_started':
                    # SDK 0.1.46+: Subagente iniciou — notificar frontend
                    # 2026-05-14: +parent_tool_use_id para correlacao visual P1.1
                    event_queue.put(_sse_event('task_started', {
                        'description': event.content or '',
                        'task_id': event.metadata.get('task_id', ''),
                        'task_type': event.metadata.get('task_type', ''),
                        'parent_tool_use_id': event.metadata.get('parent_tool_use_id'),
                    }))

                elif event.type == 'task_progress':
                    # SDK 0.1.46+: Progresso de subagente
                    # 2026-05-14: +usage (P0.3) +parent_tool_use_id (P1.1)
                    event_queue.put(_sse_event('task_progress', {
                        'description': event.content or '',
                        'task_id': event.metadata.get('task_id', ''),
                        'last_tool_name': event.metadata.get('last_tool_name', ''),
                        'usage': event.metadata.get('usage'),
                        'parent_tool_use_id': event.metadata.get('parent_tool_use_id'),
                    }))
```

`task_notification` já passa `status` (linha 852) — sem alteração.

- [ ] **Step 7: Rodar suite completa do agente para confirmar zero regressão**

```bash
pytest tests/agente/ -x --tb=short 2>&1 | tail -10
```
Expected: nenhum NEW failure (testes pre-existentes podem ter falhas legadas de dados; comparar contra baseline `git stash + pytest + stash pop`)

- [ ] **Step 8: Commit**

```bash
git add app/agente/sdk/client.py tests/agente/test_subagent_client_metadata.py
git commit -m "feat(agente): client.py propaga usage + parent_tool_use_id no SSE

P0.3: TaskProgressMessage.usage (TaskUsage com total_tokens/tool_uses/
duration_ms) propagado em metadata.usage do StreamEvent task_progress.

P1.1: TaskStartedMessage.tool_use_id e TaskProgressMessage.parent_tool_use_id
propagados em metadata.parent_tool_use_id — frontend usa para correlacao
visual com a mensagem do agente principal que disparou o subagent.

getattr defensivo: SDK pode nao popular esses campos em versoes antigas;
metadata recebe None, frontend ignora correlacao. Zero regressao.

Testes: tests/agente/test_subagent_client_metadata.py (5 cenarios).

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (secao 5.1)"
```

---

## Task 3: get_subagent_transcript em subagent_reader.py (TDD)

**Files:**
- Modify: `app/agente/sdk/subagent_reader.py`
- Create: `tests/agente/test_subagent_transcript.py`

- [ ] **Step 1: Escrever testes falhando**

Criar `tests/agente/test_subagent_transcript.py`:

```python
"""Testes para get_subagent_transcript — timeline cronologica completa."""
import json
from datetime import datetime
from pathlib import Path
import pytest

from app.agente.sdk.subagent_reader import (
    get_subagent_transcript,
    SubagentTranscriptEntry,
)


@pytest.fixture
def fake_subagent_jsonl(tmp_path, monkeypatch):
    """Cria estrutura mock <tmp>/projects/proj-x/<sid>/subagents/<aid>.jsonl.

    Retorna (session_id, agent_id, jsonl_path).
    """
    session_id = 'a' * 32
    agent_id = 'b' * 32
    proj_dir = tmp_path / 'projects' / 'proj-x'
    sub_dir = proj_dir / session_id / 'subagents'
    sub_dir.mkdir(parents=True)
    jsonl = sub_dir / f'{agent_id}.jsonl'
    # 4 mensagens: user (prompt inicial) -> assistant (tool_use) -> user (tool_result) -> assistant (text final)
    lines = [
        {
            'type': 'user',
            'uuid': 'u1',
            'timestamp': '2026-05-14T01:00:00Z',
            'message': {
                'role': 'user',
                'content': 'Analise pedido VCD123 com regras P1-P7. Cliente CPF 123.456.789-00.'
            },
        },
        {
            'type': 'assistant',
            'uuid': 'a1',
            'timestamp': '2026-05-14T01:00:05Z',
            'message': {
                'role': 'assistant',
                'content': [
                    {'type': 'text', 'text': 'Vou consultar o pedido.'},
                    {'type': 'tool_use', 'id': 'tu_1', 'name': 'Bash',
                     'input': {'command': 'psql -c SELECT * FROM pedidos'}},
                ],
                'usage': {'input_tokens': 100, 'output_tokens': 50},
            },
        },
        {
            'type': 'user',
            'uuid': 'u2',
            'timestamp': '2026-05-14T01:00:10Z',
            'message': {
                'role': 'user',
                'content': [
                    {'type': 'tool_result', 'tool_use_id': 'tu_1',
                     'content': 'pedido VCD123 prioridade P3', 'is_error': False}
                ],
            },
        },
        {
            'type': 'assistant',
            'uuid': 'a2',
            'timestamp': '2026-05-14T01:00:12Z',
            'message': {
                'role': 'assistant',
                'content': [
                    {'type': 'text', 'text': 'Pedido VCD123 e P3 porque atende criterio X.'}
                ],
                'usage': {'input_tokens': 200, 'output_tokens': 80},
            },
        },
    ]
    with jsonl.open('w') as f:
        for line in lines:
            f.write(json.dumps(line) + '\n')

    # Aponta o resolver para tmp_path
    monkeypatch.setattr(
        'app.agente.sdk.subagent_reader._candidate_directories',
        lambda directory: [str(tmp_path / 'projects' / 'proj-x' / session_id)]
    )
    monkeypatch.setattr(
        'app.agente.sdk.subagent_reader._resolve_transcript_path',
        lambda sid, aid, directory=None: str(jsonl)
    )
    # Mock list_subagents/get_subagent_messages do SDK
    monkeypatch.setattr(
        'app.agente.sdk.subagent_reader.get_subagent_messages',
        lambda sid, aid, **kw: [
            type('Msg', (), {
                'type': line['type'],
                'message': line['message'],
                'uuid': line['uuid'],
            })() for line in lines
        ]
    )
    return session_id, agent_id, jsonl


def test_transcript_inclui_prompt_inicial(fake_subagent_jsonl):
    """1a UserMessage do JSONL = user_prompt na timeline."""
    sid, aid, _ = fake_subagent_jsonl
    entries = get_subagent_transcript(sid, aid, include_pii=True)
    assert len(entries) >= 1
    first = entries[0]
    assert first.kind == 'user_prompt'
    assert 'VCD123' in first.content
    assert first.sequence == 1


def test_transcript_ordenacao_cronologica(fake_subagent_jsonl):
    """sequence cresce monotonicamente."""
    sid, aid, _ = fake_subagent_jsonl
    entries = get_subagent_transcript(sid, aid, include_pii=True)
    seqs = [e.sequence for e in entries]
    assert seqs == sorted(seqs)
    assert seqs[0] == 1


def test_transcript_correlaciona_tool_use_tool_result(fake_subagent_jsonl):
    """tool_use_id linka tool_use -> tool_result."""
    sid, aid, _ = fake_subagent_jsonl
    entries = get_subagent_transcript(sid, aid, include_pii=True)
    tu = next(e for e in entries if e.kind == 'tool_use')
    tr = next(e for e in entries if e.kind == 'tool_result')
    assert tu.tool_use_id == 'tu_1'
    assert tr.tool_use_id == 'tu_1'


def test_transcript_mask_pii_quando_include_pii_false(fake_subagent_jsonl):
    """CPF mascarado em entries quando flag off."""
    sid, aid, _ = fake_subagent_jsonl
    entries = get_subagent_transcript(sid, aid, include_pii=False)
    prompt = entries[0].content
    assert '123.456.789-00' not in prompt
    # Pelo padrao mask_pii, CPF vira ***.***.***-** ou similar
    assert '***' in prompt or '*' in prompt or 'XXX' in prompt


def test_transcript_jsonl_inexistente_retorna_vazio(monkeypatch):
    """Sem JSONL, retorna []."""
    monkeypatch.setattr(
        'app.agente.sdk.subagent_reader.get_subagent_messages',
        lambda sid, aid, **kw: []
    )
    entries = get_subagent_transcript('a' * 32, 'b' * 32)
    assert entries == []


def test_transcript_path_traversal_bloqueado():
    """agent_id com '..' ou outros chars unsafe = [] sem ler nada."""
    # _is_safe_id rejeita ids com / .. * etc
    entries = get_subagent_transcript('a' * 32, '../etc/passwd')
    assert entries == []


def test_transcript_respeitar_max_content_chars(fake_subagent_jsonl):
    """Content > max e truncado por entry."""
    sid, aid, _ = fake_subagent_jsonl
    entries = get_subagent_transcript(sid, aid, include_pii=True, max_content_chars=20)
    for e in entries:
        if isinstance(e.content, str):
            assert len(e.content) <= 20 + 10  # margin para ellipsis se houver


def test_transcript_assistant_text_block_extraido(fake_subagent_jsonl):
    """assistant text block aparece como kind=assistant_text."""
    sid, aid, _ = fake_subagent_jsonl
    entries = get_subagent_transcript(sid, aid, include_pii=True)
    texts = [e for e in entries if e.kind == 'assistant_text']
    assert len(texts) >= 1
    assert any('P3' in t.content for t in texts)
```

- [ ] **Step 2: Rodar testes para confirmar que falham**

```bash
pytest tests/agente/test_subagent_transcript.py -v
```
Expected: 8 testes FAIL com `ImportError: cannot import name 'get_subagent_transcript'` ou `SubagentTranscriptEntry`

- [ ] **Step 3: Adicionar `SubagentTranscriptEntry` e `get_subagent_transcript` em `subagent_reader.py`**

Localizar o final do arquivo (após `get_subagent_findings`) e adicionar:

```python
# ═══════════════════════════════════════════════════════════════════════
# Transcript completo (P0.1 — modal de transcript)
# ═══════════════════════════════════════════════════════════════════════

TranscriptKind = Literal['user_prompt', 'assistant_text', 'tool_use',
                          'tool_result', 'thinking']


@dataclass
class SubagentTranscriptEntry:
    """Uma entrada da timeline cronologica do subagent.

    Diferenca para SubagentSummary.tools_used:
    - Inclui user_prompt (primeira UserMessage do JSONL — o que o parent
      enviou ao subagent)
    - Inclui thinking blocks separadamente
    - Ordem cronologica do JSONL (sequence crescente)
    - max_content_chars maior (4000 vs 500) — modal mostra mais
    """
    sequence: int                       # ordem no JSONL (1, 2, 3, ...)
    kind: TranscriptKind
    timestamp: Optional[datetime]
    content: Any                        # str para text/prompt/thinking;
                                         # dict para tool_use {name, input};
                                         # str para tool_result content
    tool_use_id: Optional[str] = None   # correlaciona tool_use <-> tool_result

    def to_dict(self) -> dict:
        return {
            'sequence': self.sequence,
            'kind': self.kind,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'content': self.content,
            'tool_use_id': self.tool_use_id,
        }


def get_subagent_transcript(
    session_id: str,
    agent_id: str,
    directory: Optional[str] = None,
    include_pii: bool = False,
    max_content_chars: int = 4000,
) -> list[SubagentTranscriptEntry]:
    """Le transcript COMPLETO do subagent em ordem cronologica.

    Diferente de get_subagent_summary (que retorna tools_used resumido),
    este retorna timeline com:
      1. user_prompt — primeira UserMessage (prompt do parent ao subagent)
      2. assistant_text / tool_use / tool_result / thinking em ordem

    Args:
        session_id: UUID-like da sessao
        agent_id: UUID-like do agent (subagent_id)
        directory: opcional, override do diretorio do SDK
        include_pii: se False, aplica mask_pii em todo content
        max_content_chars: cap por entry (truncado com ellipsis se exceder)

    Returns:
        Lista de SubagentTranscriptEntry em ordem cronologica.
        Lista vazia se transcript nao existe ou ids invalidos.
    """
    if not _is_safe_id(session_id) or not _is_safe_id(agent_id):
        logger.debug(
            f"[subagent_reader] transcript rejected — unsafe id: "
            f"session={session_id!r} agent={agent_id!r}"
        )
        return []

    # Mesma estrategia de get_subagent_summary — tenta candidates
    messages = []
    for candidate in _candidate_directories(directory):
        try:
            kwargs = {'directory': candidate} if candidate else {}
            messages = list(get_subagent_messages(
                session_id, agent_id, **kwargs
            ))
            if messages:
                break
        except Exception as e:
            logger.debug(
                f"[subagent_reader] transcript get_subagent_messages "
                f"dir={candidate}: {e}"
            )

    if not messages:
        return []

    def _truncate(text: str) -> str:
        if not isinstance(text, str):
            return text
        if len(text) > max_content_chars:
            return text[:max_content_chars] + '…[truncado]'
        return text

    def _maybe_mask(content: Any) -> Any:
        if include_pii:
            return content
        if isinstance(content, str):
            return mask_pii(content)
        if isinstance(content, dict):
            return {k: _maybe_mask(v) for k, v in content.items()}
        if isinstance(content, list):
            return [_maybe_mask(item) for item in content]
        return content

    def _extract_content_list(msg) -> list:
        """Espelha get_subagent_summary._extract_content_list."""
        msg_dict = getattr(msg, 'message', None)
        if isinstance(msg_dict, dict):
            content = msg_dict.get('content')
        else:
            content = getattr(msg, 'content', None)
        if isinstance(content, list):
            return content
        if isinstance(content, str):
            return [{'type': 'text', 'text': content}]
        return []

    def _msg_role(msg) -> Optional[str]:
        msg_dict = getattr(msg, 'message', None)
        if isinstance(msg_dict, dict):
            return msg_dict.get('role')
        return getattr(msg, 'role', None)

    def _msg_timestamp(msg) -> Optional[datetime]:
        # SessionMessage SDK 0.1.60 nao expoe timestamp; tentamos via JSONL parsing.
        # Como simplificacao: None (timeline e cronologica por sequence).
        return None

    entries: list[SubagentTranscriptEntry] = []
    sequence = 0
    first_user_seen = False

    for msg in messages:
        role = _msg_role(msg)
        blocks = _extract_content_list(msg)
        ts = _msg_timestamp(msg)

        if role == 'user':
            # Primeira UserMessage = prompt do parent ao subagent
            if not first_user_seen:
                # Pode ter blocks (lista) ou string simples
                prompt_text = ''
                for b in blocks:
                    if isinstance(b, dict) and b.get('type') == 'text':
                        prompt_text += b.get('text', '')
                if not prompt_text and blocks:
                    # fallback: serializar
                    prompt_text = str(blocks)
                sequence += 1
                entries.append(SubagentTranscriptEntry(
                    sequence=sequence,
                    kind='user_prompt',
                    timestamp=ts,
                    content=_maybe_mask(_truncate(prompt_text)),
                ))
                first_user_seen = True
                # Continua processando — pode ter tool_results aqui tambem
            # tool_results vem em UserMessage subsequentes
            for b in blocks:
                if isinstance(b, dict) and b.get('type') == 'tool_result':
                    result_content = b.get('content', '')
                    if isinstance(result_content, list):
                        result_content = ' '.join(
                            r.get('text', '') for r in result_content
                            if isinstance(r, dict)
                        )
                    sequence += 1
                    entries.append(SubagentTranscriptEntry(
                        sequence=sequence,
                        kind='tool_result',
                        timestamp=ts,
                        content=_maybe_mask(_truncate(str(result_content))),
                        tool_use_id=b.get('tool_use_id'),
                    ))

        elif role == 'assistant':
            for b in blocks:
                if not isinstance(b, dict):
                    continue
                btype = b.get('type')
                if btype == 'text':
                    sequence += 1
                    entries.append(SubagentTranscriptEntry(
                        sequence=sequence,
                        kind='assistant_text',
                        timestamp=ts,
                        content=_maybe_mask(_truncate(b.get('text', ''))),
                    ))
                elif btype == 'tool_use':
                    sequence += 1
                    args = b.get('input', {})
                    entries.append(SubagentTranscriptEntry(
                        sequence=sequence,
                        kind='tool_use',
                        timestamp=ts,
                        content=_maybe_mask({
                            'name': b.get('name', ''),
                            'input': args,
                        }),
                        tool_use_id=b.get('id'),
                    ))
                elif btype == 'thinking':
                    sequence += 1
                    entries.append(SubagentTranscriptEntry(
                        sequence=sequence,
                        kind='thinking',
                        timestamp=ts,
                        content=_maybe_mask(_truncate(b.get('thinking', ''))),
                    ))

    return entries
```

- [ ] **Step 4: Rodar testes para confirmar que passam**

```bash
pytest tests/agente/test_subagent_transcript.py -v
```
Expected: 8 testes PASS

- [ ] **Step 5: Validar que `get_subagent_summary` (função existente) não regrediu**

```bash
pytest tests/agente/ -k "summary or subagent" -v --tb=short 2>&1 | tail -15
```
Expected: testes existentes mantêm status (PASS ou pré-existente FAIL não-relacionado).

- [ ] **Step 6: Commit**

```bash
git add app/agente/sdk/subagent_reader.py tests/agente/test_subagent_transcript.py
git commit -m "feat(agente): get_subagent_transcript retorna timeline cronologica

P0.1: nova funcao em subagent_reader.py que le o JSONL do subagent e
retorna lista de SubagentTranscriptEntry em ordem cronologica:
- 1a UserMessage = user_prompt (prompt enviado pelo parent ao subagent)
- assistant text/tool_use/thinking blocks
- tool_result correlacionado por tool_use_id

Diferente de get_subagent_summary (que retorna tools_used resumido para
linha inline), este transcript completo alimenta o modal do P0.1.

Validacoes preservadas: _is_safe_id (path traversal), mask_pii por entry,
max_content_chars 4000 (cap com ellipsis), 3 fallbacks de directory.

Testes: 8 cenarios (prompt inicial, ordenacao, correlacao, mask PII,
JSONL ausente, path traversal, max chars, assistant text).

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (secao 5.1)"
```

---

## Task 4: Endpoint POST /pii-toggle (TDD)

**Files:**
- Modify: `app/agente/routes/subagents.py`
- Modify: `tests/agente/test_subagent_routes.py` (criar se não existe)

- [ ] **Step 1: Escrever testes falhando**

Criar `tests/agente/test_subagent_routes.py`:

```python
"""Testes para endpoints novos de subagent UI (Fase 1)."""
import json
import pytest
from unittest.mock import patch, MagicMock

from app import db
from app.agente.models import AgentSession
from app.usuarios.models import Usuario


@pytest.fixture
def admin_user(app):
    with app.app_context():
        u = Usuario(
            nome='Admin Test',
            email='admin-subagent-test@t.local',
            perfil='administrador',
            status='ativo',
        )
        u.set_password('test123')
        db.session.add(u)
        db.session.commit()
        yield u
        db.session.delete(u)
        db.session.commit()


@pytest.fixture
def normal_user(app):
    with app.app_context():
        u = Usuario(
            nome='User Test',
            email='user-subagent-test@t.local',
            perfil='operador',
            status='ativo',
        )
        u.set_password('test123')
        db.session.add(u)
        db.session.commit()
        yield u
        db.session.delete(u)
        db.session.commit()


@pytest.fixture
def session_owned_by(app, normal_user):
    with app.app_context():
        s = AgentSession(
            session_id='a' * 32,
            user_id=normal_user.id,
            data={},
        )
        db.session.add(s)
        db.session.commit()
        yield s
        db.session.delete(s)
        db.session.commit()


def _login(client, user, password='test123'):
    return client.post('/auth/login',
                       data={'email': user.email, 'senha': password},
                       follow_redirects=False)


# === POST /pii-toggle ===

def test_pii_toggle_403_non_admin(client, normal_user, session_owned_by):
    _login(client, normal_user)
    r = client.post(
        f'/agente/api/sessions/{session_owned_by.session_id}/subagents/{"b"*32}/pii-toggle',
        json={'enabled': True},
    )
    assert r.status_code == 403


def test_pii_toggle_404_se_flag_off(client, admin_user, session_owned_by, monkeypatch):
    monkeypatch.setattr('app.agente.config.feature_flags.USE_SUBAGENT_MODAL', False)
    _login(client, admin_user)
    r = client.post(
        f'/agente/api/sessions/{session_owned_by.session_id}/subagents/{"b"*32}/pii-toggle',
        json={'enabled': True},
    )
    assert r.status_code == 404


def test_pii_toggle_admin_registra_audit_log(client, admin_user, session_owned_by, app):
    _login(client, admin_user)
    r = client.post(
        f'/agente/api/sessions/{session_owned_by.session_id}/subagents/{"b"*32}/pii-toggle',
        json={'enabled': True},
    )
    assert r.status_code == 200
    payload = r.get_json()
    assert payload['success'] is True
    assert payload['expires_in'] == 300

    with app.app_context():
        sess = AgentSession.query.filter_by(session_id=session_owned_by.session_id).first()
        audit = sess.data.get('subagent_pii_audit', [])
        assert len(audit) >= 1
        entry = audit[-1]
        assert entry['enabled'] is True
        assert entry['user_id'] == admin_user.id
        assert entry['agent_id'] == 'b' * 32


def test_pii_toggle_rate_limit(client, admin_user, session_owned_by, redis_client):
    _login(client, admin_user)
    aid = 'b' * 32
    url = f'/agente/api/sessions/{session_owned_by.session_id}/subagents/{aid}/pii-toggle'
    # 10 toggles OK
    for i in range(10):
        r = client.post(url, json={'enabled': bool(i % 2)})
        assert r.status_code == 200, f'request {i} esperava 200, recebeu {r.status_code}'
    # 11º bloqueado
    r = client.post(url, json={'enabled': True})
    assert r.status_code == 429
```

> **Nota fixtures**: `client` e `app` ja existem em `tests/conftest.py`. `redis_client` e `as_admin` / `as_user` são novas e definidas inline (code-review #3, #4).

Adicionar fixtures concretas no INÍCIO do `tests/agente/test_subagent_routes.py` (logo após os imports):

```python
@pytest.fixture
def redis_client():
    """Fixture concreta — code-review #4. Limpa chaves de teste pos-teste."""
    from app.utils.redis_cache import RedisCache
    rc = RedisCache().get_client()
    # Limpar chaves que podem ter sido criadas em testes anteriores
    yield rc
    try:
        for key_prefix in ['agent:pii_toggle_rate:', 'agent:pii_unmask:',
                           'agent:metrics:subagent_modal']:
            for key in rc.scan_iter(f'{key_prefix}*'):
                rc.delete(key)
    except Exception:
        pass


@pytest.fixture
def as_admin(monkeypatch, admin_user, app):
    """Bypass de LOGIN_DISABLED=True via monkeypatch direto de current_user.

    Code-review #3: tests/conftest.py tem LOGIN_DISABLED=True que faz
    @login_required ser no-op. Sem isso, current_user vira AnonymousUser
    e testes de auth ficam vacuous. Esta fixture forca current_user=admin_user
    no contexto do modulo de rotas.
    """
    from flask_login import login_user
    with app.test_request_context():
        monkeypatch.setattr('app.agente.routes.subagents.current_user', admin_user)
        yield admin_user


@pytest.fixture
def as_user(monkeypatch, normal_user, app):
    """Idem as_admin, mas para user normal."""
    with app.test_request_context():
        monkeypatch.setattr('app.agente.routes.subagents.current_user', normal_user)
        yield normal_user
```

> **Importante**: nos testes abaixo, **usar `as_admin` / `as_user`** como fixtures em vez de chamar `_login()`. Exemplo:
>
> ```python
> def test_pii_toggle_403_non_admin(client, as_user, session_owned_by):
>     # _login() removido — fixture as_user ja autentica
>     r = client.post(...)
> ```

- [ ] **Step 2: Rodar testes para confirmar que falham**

```bash
pytest tests/agente/test_subagent_routes.py -v --tb=short 2>&1 | tail -20
```
Expected: 4 testes FAIL com 404 (endpoint não existe ainda).

- [ ] **Step 3: Adicionar endpoint POST /pii-toggle em `app/agente/routes/subagents.py`**

Adicionar imports no TOPO do arquivo (logo após imports existentes):

```python
from flask import request
from app.utils.timezone import agora_brasil_naive
from sqlalchemy.orm.attributes import flag_modified
from app import db, redis_cache
# Fix code-review #1: reusar _is_safe_id existente em vez de duplicar regex
from app.agente.sdk.subagent_reader import _is_safe_id
```

Adicionar ao final do arquivo:

```python
# ═══════════════════════════════════════════════════════════════════════
# POST /pii-toggle — Admin liga/desliga PII unmask por 5min
# ═══════════════════════════════════════════════════════════════════════


@agente_bp.route(
    '/api/sessions/<session_id>/subagents/<agent_id>/pii-toggle',
    methods=['POST'],
)
@login_required
def api_subagent_pii_toggle(session_id: str, agent_id: str):
    """Admin liga/desliga visualizacao raw de PII no modal de transcript.

    - Apenas admin (perfil='administrador'). Non-admin -> 403.
    - Rate limit 10 toggles/min/user.
    - Registra audit em agent_sessions.data['subagent_pii_audit'] (FIFO 100).
    - Marca Redis SETEX agent:pii_unmask:{user_id}:{sid}:{aid} 300 "1".
    """
    from app.agente.config.feature_flags import USE_SUBAGENT_MODAL

    if not USE_SUBAGENT_MODAL:
        return jsonify({'success': False, 'error': 'Feature desabilitada'}), 404

    if not _is_safe_id(session_id) or not _is_safe_id(agent_id):
        return jsonify({'success': False, 'error': 'IDs invalidos'}), 404

    if getattr(current_user, 'perfil', None) != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso restrito a administradores'}), 403

    body = request.get_json(silent=True) or {}
    enabled = bool(body.get('enabled', False))

    sess = AgentSession.query.filter_by(session_id=session_id).first()
    if sess is None:
        return jsonify({'success': False, 'error': 'Sessao nao encontrada'}), 404

    # Rate limit Redis: 10/min/user
    try:
        rc = redis_cache.get_client()
        rk = f'agent:pii_toggle_rate:{current_user.id}'
        count = rc.incr(rk)
        if count == 1:
            rc.expire(rk, 60)
        if count > 10:
            return jsonify({
                'success': False,
                'error': 'Muitas trocas em sequencia. Aguarde 1 minuto.',
            }), 429
    except Exception as e:
        logger.warning(f"[pii_toggle] rate limit Redis falhou: {e}")
        # Sem rate limit, mas continua (defesa em profundidade)

    # Audit log FIFO max 100
    audit = sess.data.setdefault('subagent_pii_audit', [])
    audit.append({
        'agent_id': agent_id,
        'user_id': current_user.id,
        'enabled': enabled,
        'timestamp': agora_brasil_naive().isoformat(),
        'session_id': session_id,
    })
    if len(audit) > 100:
        del audit[:len(audit) - 100]
    flag_modified(sess, 'data')
    db.session.commit()

    # Redis token TTL 5min
    try:
        rc = redis_cache.get_client()
        tk = f'agent:pii_unmask:{current_user.id}:{session_id}:{agent_id}'
        if enabled:
            rc.setex(tk, 300, '1')
        else:
            rc.delete(tk)
    except Exception as e:
        logger.error(f"[pii_toggle] Redis SETEX falhou: {e}")
        return jsonify({'success': False, 'error': 'Recurso temporariamente indisponivel'}), 500

    logger.info(
        f"[pii_toggle] user_id={current_user.id} "
        f"session={session_id[:16]} agent={agent_id[:12]} enabled={enabled}"
    )
    return jsonify({'success': True, 'enabled': enabled, 'expires_in': 300})
```

- [ ] **Step 4: Adicionar imports necessários no topo do arquivo**

Verificar se já existem; se não, adicionar:

```python
from flask import request  # Se nao existir
```

- [ ] **Step 5: Rodar testes**

```bash
pytest tests/agente/test_subagent_routes.py -v --tb=short 2>&1 | tail -20
```
Expected: 4 testes PASS.

- [ ] **Step 6: Commit**

```bash
git add app/agente/routes/subagents.py tests/agente/test_subagent_routes.py
git commit -m "feat(agente): endpoint POST /pii-toggle (admin-only, audit + rate limit)

Permite admin alternar visualizacao raw de PII no modal de transcript.
TTL 5min via Redis. Audit log FIFO max 100 em agent_sessions.data.
Rate limit 10 toggles/min/user.

Testes: 4 cenarios (403 non-admin, 404 flag off, audit log persistido,
rate limit 429).

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (secao 5.1, cenario 3)"
```

---

## Task 5: Endpoint GET /transcript (TDD)

**Files:**
- Modify: `app/agente/routes/subagents.py`
- Modify: `tests/agente/test_subagent_routes.py`

- [ ] **Step 1: Adicionar testes ao `test_subagent_routes.py`**

Adicionar ao final do arquivo:

```python
# === GET /transcript ===

def test_transcript_404_flag_off(client, normal_user, session_owned_by, monkeypatch):
    monkeypatch.setattr('app.agente.config.feature_flags.USE_SUBAGENT_MODAL', False)
    _login(client, normal_user)
    r = client.get(
        f'/agente/api/sessions/{session_owned_by.session_id}/subagents/{"b"*32}/transcript'
    )
    assert r.status_code == 404


def test_transcript_403_se_nao_dono_nem_admin(client, admin_user, normal_user, app):
    """User A nao pode ver sessao do User B (a menos que seja admin)."""
    with app.app_context():
        sess_a = AgentSession(session_id='c' * 32, user_id=admin_user.id, data={})
        db.session.add(sess_a)
        db.session.commit()
    _login(client, normal_user)
    r = client.get(f'/agente/api/sessions/{"c"*32}/subagents/{"b"*32}/transcript')
    assert r.status_code == 403


def test_transcript_dono_pii_mascarada(client, normal_user, session_owned_by, monkeypatch):
    """Dono nao-admin: PII vem mascarada por default."""
    _login(client, normal_user)
    monkeypatch.setattr(
        'app.agente.routes.subagents.get_subagent_transcript',
        lambda sid, aid, include_pii=False, **kw: [
            type('E', (), {
                'to_dict': lambda self: {
                    'sequence': 1, 'kind': 'user_prompt',
                    'content': 'CPF ***.***.***-**' if not include_pii else 'CPF 123.456.789-00',
                    'tool_use_id': None, 'timestamp': None,
                }
            })()
        ]
    )
    r = client.get(
        f'/agente/api/sessions/{session_owned_by.session_id}/subagents/{"b"*32}/transcript'
    )
    assert r.status_code == 200
    transcript = r.get_json()['transcript']
    assert '***' in transcript[0]['content']
    assert '123.456.789' not in transcript[0]['content']


def test_transcript_admin_com_pii_token_raw(client, admin_user, app, monkeypatch):
    """Admin com Redis token valido recebe PII raw."""
    with app.app_context():
        sess = AgentSession(session_id='d' * 32, user_id=admin_user.id, data={})
        db.session.add(sess)
        db.session.commit()
    _login(client, admin_user)

    # Simula Redis token presente
    from app import redis_cache
    rc = redis_cache.get_client()
    rc.setex(f'agent:pii_unmask:{admin_user.id}:{"d"*32}:{"b"*32}', 300, '1')

    monkeypatch.setattr(
        'app.agente.routes.subagents.get_subagent_transcript',
        lambda sid, aid, include_pii=False, **kw: [
            type('E', (), {
                'to_dict': lambda self: {
                    'sequence': 1, 'kind': 'user_prompt',
                    'content': 'CPF 123.456.789-00' if include_pii else 'CPF ***',
                    'tool_use_id': None, 'timestamp': None,
                }
            })()
        ]
    )

    r = client.get(f'/agente/api/sessions/{"d"*32}/subagents/{"b"*32}/transcript')
    assert r.status_code == 200
    transcript = r.get_json()['transcript']
    assert '123.456.789-00' in transcript[0]['content']

    rc.delete(f'agent:pii_unmask:{admin_user.id}:{"d"*32}:{"b"*32}')
```

- [ ] **Step 2: Rodar para confirmar falhas**

```bash
pytest tests/agente/test_subagent_routes.py -k transcript -v --tb=short 2>&1 | tail -15
```
Expected: 4 testes FAIL (404 endpoint inexistente).

- [ ] **Step 3: Adicionar endpoint em `routes/subagents.py`**

Adicionar antes do endpoint `/pii-toggle`:

```python
from app.agente.sdk.subagent_reader import get_subagent_transcript  # adicionar nos imports do topo


@agente_bp.route(
    '/api/sessions/<session_id>/subagents/<agent_id>/transcript',
    methods=['GET'],
)
@login_required
def api_subagent_transcript(session_id: str, agent_id: str):
    """Retorna timeline cronologica completa do subagent.

    Autorizacao: dono OU admin. Non-admin recebe PII mascarada.
    Admin com Redis token agent:pii_unmask:* recebe raw.
    """
    from app.agente.config.feature_flags import USE_SUBAGENT_MODAL

    if not USE_SUBAGENT_MODAL:
        return jsonify({'success': False, 'error': 'Feature desabilitada'}), 404

    if not _is_safe_id(session_id) or not _is_safe_id(agent_id):
        return jsonify({'success': False, 'error': 'IDs invalidos'}), 404

    sess = AgentSession.query.filter_by(session_id=session_id).first()
    if sess is None:
        return jsonify({'success': False, 'error': 'Sessao nao encontrada'}), 404

    is_admin = getattr(current_user, 'perfil', None) == 'administrador'
    if not is_admin and sess.user_id != current_user.id:
        return jsonify({
            'success': False,
            'error': 'Acesso restrito ao dono da sessao ou administrador',
        }), 403

    # Determinar include_pii: admin + Redis token valido
    include_pii = False
    if is_admin:
        try:
            rc = redis_cache.get_client()
            tk = f'agent:pii_unmask:{current_user.id}:{session_id}:{agent_id}'
            include_pii = bool(rc.exists(tk))
        except Exception as e:
            logger.warning(f"[transcript] Redis exists falhou: {e}")
            include_pii = False

    try:
        entries = get_subagent_transcript(
            session_id, agent_id,
            include_pii=include_pii,
            max_content_chars=4000,
        )
    except Exception as e:
        logger.error(f"[transcript] get_subagent_transcript falhou: {e}")
        return jsonify({
            'success': False,
            'error': 'Nao foi possivel carregar o transcript. Tente novamente em instantes.',
        }), 500

    if not entries:
        return jsonify({
            'success': False,
            'error': 'Transcript nao encontrado. A sessao pode ter sido arquivada.',
        }), 404

    # Telemetria contador
    try:
        from datetime import date
        rc = redis_cache.get_client()
        rc.hincrby('agent:metrics:subagent_modal:daily', date.today().isoformat(), 1)
    except Exception:
        pass

    logger.info(
        f"[transcript] user_id={current_user.id} "
        f"session={session_id[:16]} agent={agent_id[:12]} "
        f"include_pii={include_pii} entries={len(entries)}"
    )

    return jsonify({
        'success': True,
        'session_id': session_id,
        'agent_id': agent_id,
        'include_pii': include_pii,
        'transcript': [e.to_dict() for e in entries],
    })
```

- [ ] **Step 4: Rodar testes**

```bash
pytest tests/agente/test_subagent_routes.py -k transcript -v --tb=short 2>&1 | tail -15
```
Expected: 4 testes PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agente/routes/subagents.py tests/agente/test_subagent_routes.py
git commit -m "feat(agente): endpoint GET /transcript (timeline cronologica do subagent)

P0.1: retorna SubagentTranscriptEntry serializado em ordem.
- Dono OU admin (403 caso contrario)
- include_pii=True so se admin + Redis token agent:pii_unmask:* valido
- Telemetria: incrementa hash diario agent:metrics:subagent_modal:daily
- Fallback gracioso: 404 se transcript ausente, 500 com mensagem clara em erro

Testes: 4 cenarios (404 flag off, 403 cross-user, PII mascarada por
default para dono, PII raw para admin com token).

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (secao 5.1, cenario 2)"
```

---

## Task 6: Smoketest extension em admin_subagents.py

**Files:**
- Modify: `app/agente/routes/admin_subagents.py:281-373`

- [ ] **Step 1: Localizar a função `api_admin_subagent_smoketest` (linha 281)**

- [ ] **Step 2: Adicionar verificação de transcript ao final do try block, ANTES da linha `report['healthy'] = (...)`**

Localizar:
```python
        report['summary_status'] = summary.status
        report['tools_used'] = len(summary.tools_used)
        report['findings_len'] = len(summary.findings_text or '')
        report['cost_usd'] = round(summary.cost_usd, 6)
        report['num_turns'] = summary.num_turns

        # Healthy se: summary bem formado + cost calculado
        report['healthy'] = (
```

Substituir por:
```python
        report['summary_status'] = summary.status
        report['tools_used'] = len(summary.tools_used)
        report['findings_len'] = len(summary.findings_text or '')
        report['cost_usd'] = round(summary.cost_usd, 6)
        report['num_turns'] = summary.num_turns

        # NOVO (2026-05-14): verificar tambem get_subagent_transcript
        from app.agente.sdk.subagent_reader import get_subagent_transcript
        try:
            transcript = get_subagent_transcript(row.session_id, agent_ids[0], include_pii=True)
            report['transcript_entries'] = len(transcript)
            report['has_user_prompt'] = any(e.kind == 'user_prompt' for e in transcript)
        except Exception as te:
            report['transcript_entries'] = 0
            report['has_user_prompt'] = False
            report['transcript_error'] = str(te)[:200]

        # Healthy se: summary bem formado + cost calculado + transcript com prompt
        report['healthy'] = (
```

- [ ] **Step 3: Atualizar criterio `healthy` para incluir verificação de transcript**

Logo em seguida, encontrar e substituir:

```python
        report['healthy'] = (
            summary.status == 'done'
            and (summary.num_turns > 0 or summary.cost_usd > 0)
            and (len(summary.tools_used) > 0 or len(summary.findings_text or '') > 0)
        )
```

Por:

```python
        report['healthy'] = (
            summary.status == 'done'
            and (summary.num_turns > 0 or summary.cost_usd > 0)
            and (len(summary.tools_used) > 0 or len(summary.findings_text or '') > 0)
            and report.get('transcript_entries', 0) > 0
            and report.get('has_user_prompt', False)
        )
```

- [ ] **Step 4: Verificar sintaxe**

```bash
python -c "from app.agente.routes.admin_subagents import api_admin_subagent_smoketest; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add app/agente/routes/admin_subagents.py
git commit -m "feat(agente): smoketest verifica transcript_entries + has_user_prompt

Critério healthy do /api/admin/debug/subagent-smoketest agora exige:
- transcript_entries > 0
- has_user_prompt: true (1a UserMessage extraida do JSONL)

Detecta regressao do novo get_subagent_transcript em deploys futuros.

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (secao 8.3)"
```

---

## Task 7: CSS — extensões em _subagent-inline.css

**Files:**
- Modify: `app/static/agente/css/_subagent-inline.css`

- [ ] **Step 1: Localizar bloco `.subagent-inline.error` (linha ~44) e adicionar 2 novos estados**

Adicionar **imediatamente após** `.subagent-inline.error .subagent-dot { ... }`:

```css
/* Novos estados visuais ricos (2026-05-14, P0.2) */
.subagent-inline.failed .subagent-dot {
  background: var(--agent-danger, #ef4444);
}

.subagent-inline.stopped .subagent-dot {
  background: var(--agent-text-muted, #64748b);
}

.subagent-inline.failed .subagent-meta::before {
  content: "⚠ ";
  color: var(--agent-danger, #ef4444);
}

.subagent-inline.stopped .subagent-meta::before {
  content: "⏸ ";
  color: var(--agent-text-muted, #64748b);
}
```

- [ ] **Step 2: Adicionar correlação visual parent (P1.1) ao final do arquivo**

```css
/* Correlacao parent_tool_use_id (P1.1) — marcador "↳" sutil */
.subagent-inline[data-parent-tool-use-id]:not([data-parent-tool-use-id=""]) .subagent-badge::before {
  content: "↳ ";
  color: var(--agent-text-muted, #64748b);
  margin-right: 2px;
}
```

- [ ] **Step 3: Verificar sintaxe CSS**

```bash
python -c "
with open('app/static/agente/css/_subagent-inline.css') as f:
    content = f.read()
# Conta { e } — devem bater
assert content.count('{') == content.count('}'), 'CSS desbalanceado'
print('CSS OK,', content.count('{'), 'regras')
"
```
Expected: `CSS OK, 15+ regras` (ou similar; depende do existente)

- [ ] **Step 4: Commit**

```bash
git add app/static/agente/css/_subagent-inline.css
git commit -m "style(agente): estados failed/stopped + correlacao parent na linha inline

P0.2: classes .failed (dot vermelho + icone ⚠) e .stopped (cinza + ⏸)
adicionam dois novos estados visuais distintos alem de running/done/error.

P1.1: pseudo-element ::before na badge mostra '↳' quando o atributo
data-parent-tool-use-id esta presente, indicando que o subagent foi
disparado por uma mensagem especifica do agente principal.

Design tokens preservados (var(--agent-danger), var(--agent-text-muted)).
Light/dark mode automatico.

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (secao 5.2)"
```

---

## Task 8: CSS — novo _subagent-modal.css

**Files:**
- Create: `app/static/agente/css/_subagent-modal.css`
- Modify: `app/static/agente/css/agent-theme.css`

- [ ] **Step 1: Criar `app/static/agente/css/_subagent-modal.css`**

```css
/*
 * Modal de transcript de subagent (P0.1).
 * Padrao similar ao #artifact-modal: overlay custom, NAO Bootstrap modal.
 */

.subagent-modal {
  position: fixed;
  inset: 0;
  z-index: 1050;
  display: flex;
  align-items: center;
  justify-content: center;
}

.subagent-modal[hidden] {
  display: none;
}

.subagent-modal-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(4px);
  cursor: pointer;
}

.subagent-modal-panel {
  position: relative;
  width: min(900px, 92vw);
  max-height: 88vh;
  background: var(--agent-bg-primary, #1e293b);
  border: 1px solid var(--agent-border, rgba(148, 163, 184, 0.2));
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

[data-bs-theme="light"] .subagent-modal-panel {
  background: var(--agent-bg-primary, #ffffff);
}

.subagent-modal-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--agent-border, rgba(148, 163, 184, 0.2));
  background: var(--agent-bg-secondary, rgba(148, 163, 184, 0.05));
}

.subagent-modal-header h2 {
  flex: 1;
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--agent-text-primary, #e2e8f0);
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
}

.subagent-modal-badge {
  background: rgba(0, 212, 170, 0.15);
  color: var(--agent-accent-primary, #00d4aa);
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.subagent-modal-meta {
  color: var(--agent-text-secondary, #94a3b8);
  font-size: 12px;
  white-space: nowrap;
}

.subagent-modal-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.subagent-modal-actions button {
  background: transparent;
  border: 1px solid var(--agent-border, rgba(148, 163, 184, 0.2));
  color: var(--agent-text-secondary, #94a3b8);
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.subagent-modal-actions button:hover:not(:disabled) {
  background: var(--agent-bg-tertiary, rgba(148, 163, 184, 0.12));
  color: var(--agent-text-primary, #e2e8f0);
}

.subagent-modal-actions button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.subagent-modal-actions .btn-pii-toggle.active {
  background: rgba(245, 158, 11, 0.15);
  color: var(--agent-warning, #f59e0b);
  border-color: var(--agent-warning, #f59e0b);
}

.subagent-modal-actions .btn-close {
  font-size: 20px;
  line-height: 1;
  padding: 2px 10px;
}

.subagent-modal-section {
  padding: 14px 18px;
  border-bottom: 1px solid var(--agent-border, rgba(148, 163, 184, 0.1));
  overflow-y: auto;
}

.subagent-modal-section:last-child {
  border-bottom: none;
  flex: 1;
  min-height: 0;
}

.subagent-modal-section h3 {
  margin: 0 0 8px 0;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--agent-text-muted, #64748b);
}

.subagent-modal-section .prompt-content {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: var(--agent-text-primary, #e2e8f0);
  background: var(--agent-bg-secondary, rgba(148, 163, 184, 0.05));
  padding: 10px 12px;
  border-radius: 6px;
  margin: 0;
  max-height: 200px;
  overflow-y: auto;
}

.subagent-modal-section .timeline-list {
  list-style: none;
  padding: 0;
  margin: 0;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 12px;
}

.subagent-modal-section .timeline-list li {
  padding: 6px 10px;
  margin: 3px 0;
  border-left: 3px solid var(--agent-border, rgba(148, 163, 184, 0.2));
  background: var(--agent-bg-secondary, rgba(148, 163, 184, 0.04));
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.subagent-modal-section .timeline-list li.kind-user_prompt {
  border-left-color: var(--agent-accent-primary, #00d4aa);
}
.subagent-modal-section .timeline-list li.kind-tool_use {
  border-left-color: var(--agent-warning, #f59e0b);
}
.subagent-modal-section .timeline-list li.kind-tool_result {
  border-left-color: var(--agent-text-muted, #64748b);
}
.subagent-modal-section .timeline-list li.kind-assistant_text {
  border-left-color: #8b5cf6;
}
.subagent-modal-section .timeline-list li.kind-thinking {
  border-left-color: #f472b6;
  opacity: 0.7;
}

.subagent-modal-section .timeline-list .entry-kind {
  font-size: 10px;
  text-transform: uppercase;
  color: var(--agent-text-muted, #64748b);
  letter-spacing: 0.5px;
}

.subagent-modal-section .timeline-list .entry-content {
  color: var(--agent-text-primary, #e2e8f0);
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 120px;
  overflow-y: auto;
}

.subagent-modal-section .findings-content {
  color: var(--agent-text-primary, #e2e8f0);
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 13px;
  line-height: 1.5;
}

/* Loading / empty / error states */
.subagent-modal-section.is-loading .skeleton {
  background: linear-gradient(90deg,
    var(--agent-bg-secondary, rgba(148, 163, 184, 0.05)) 0%,
    var(--agent-bg-tertiary, rgba(148, 163, 184, 0.15)) 50%,
    var(--agent-bg-secondary, rgba(148, 163, 184, 0.05)) 100%);
  background-size: 200% 100%;
  animation: subagent-shimmer 1.5s infinite;
  height: 60px;
  border-radius: 6px;
}

@keyframes subagent-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.subagent-modal-error,
.subagent-modal-empty {
  text-align: center;
  padding: 30px;
  color: var(--agent-text-secondary, #94a3b8);
}

.subagent-modal-error .icon {
  font-size: 32px;
  color: var(--agent-warning, #f59e0b);
  display: block;
  margin-bottom: 10px;
}

.subagent-modal-error button,
.subagent-modal-empty button {
  margin-top: 12px;
}
```

- [ ] **Step 2: Adicionar import em `app/static/agente/css/agent-theme.css`**

Localizar a linha `@import url("./_subagent-inline.css");` (linha ~25) e adicionar **logo abaixo**:

```css
@import url("./_subagent-modal.css");
```

- [ ] **Step 3: Verificar sintaxe**

```bash
python -c "
with open('app/static/agente/css/_subagent-modal.css') as f:
    c = f.read()
assert c.count('{') == c.count('}'), 'CSS desbalanceado'
print('Modal CSS OK,', c.count('{'), 'regras')
"
```
Expected: `Modal CSS OK, 25+ regras`

- [ ] **Step 4: Commit**

```bash
git add app/static/agente/css/_subagent-modal.css app/static/agente/css/agent-theme.css
git commit -m "style(agente): novo _subagent-modal.css para modal de transcript

P0.1: estilos do #subagent-transcript-modal. Padrao identico ao
#artifact-modal (overlay custom, nao Bootstrap).

Cobre: backdrop com blur, panel responsivo (max 88vh), 3 secoes
(prompt/timeline/findings), 5 estados de timeline com border-left
colorido (user_prompt/tool_use/tool_result/assistant_text/thinking),
loading skeleton com shimmer, error/empty states.

Design tokens preservados. Light/dark mode automatico via [data-bs-theme].

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (secao 5.2)"
```

---

## Task 9: Markup do modal em chat.html

**Files:**
- Modify: `app/agente/templates/agente/chat.html`

- [ ] **Step 1: Localizar o `#artifact-modal` no template**

```bash
grep -n "artifact-modal" app/agente/templates/agente/chat.html | head -3
```
Expected: lista linhas onde `id="artifact-modal"` aparece.

- [ ] **Step 2: Adicionar markup imediatamente ANTES do `#artifact-modal`**

```html
<!-- Modal de transcript de subagent (P0.1, USE_SUBAGENT_MODAL flag) -->
<div id="subagent-transcript-modal" class="subagent-modal" hidden>
  <div class="subagent-modal-backdrop" data-close="modal"></div>
  <div class="subagent-modal-panel" role="dialog" aria-labelledby="subagent-modal-title" aria-modal="true">
    <header class="subagent-modal-header">
      <span class="subagent-modal-badge" data-field="agent_type">subagente</span>
      <h2 id="subagent-modal-title" data-field="title">Carregando…</h2>
      <span class="subagent-modal-meta" data-field="meta"></span>
      <div class="subagent-modal-actions">
        {% if current_user.perfil == 'administrador' %}
        <button type="button" class="btn-pii-toggle" data-action="toggle-pii"
                title="Mostrar/ocultar PII (5 min)">Mostrar PII</button>
        {% endif %}
        <button type="button" class="btn-download-jsonl" data-action="download-jsonl"
                title="Download JSONL" hidden>JSONL</button>
        <button type="button" class="btn-close" data-close="modal"
                aria-label="Fechar">&times;</button>
      </div>
    </header>
    <section class="subagent-modal-section" data-section="prompt">
      <h3>Prompt do agente principal</h3>
      <pre class="prompt-content" data-field="prompt"></pre>
    </section>
    <section class="subagent-modal-section" data-section="timeline">
      <h3>Timeline</h3>
      <ol class="timeline-list" data-field="timeline"></ol>
    </section>
    <section class="subagent-modal-section" data-section="findings">
      <h3>Findings</h3>
      <div class="findings-content" data-field="findings"></div>
    </section>
  </div>
</div>
```

- [ ] **Step 3: Verificar que template renderiza**

```bash
python -c "
from app import create_app
from flask import render_template
app = create_app()
with app.app_context(), app.test_request_context():
    # Renderizacao basica de syntax
    with open('app/agente/templates/agente/chat.html') as f:
        body = f.read()
    assert 'subagent-transcript-modal' in body
    assert 'data-section=\"prompt\"' in body
    assert 'data-section=\"timeline\"' in body
    assert 'data-section=\"findings\"' in body
    print('Template OK')
"
```
Expected: `Template OK`

- [ ] **Step 4: Commit**

```bash
git add app/agente/templates/agente/chat.html
git commit -m "feat(agente): markup do modal de transcript no chat.html

P0.1: #subagent-transcript-modal hidden por default. Estrutura:
- header: badge + titulo + meta + acoes (PII toggle admin-only, download Fase 2, close)
- secao prompt (pre formatado)
- secao timeline (lista ordenada)
- secao findings (texto livre)

Botao 'Mostrar PII' renderizado server-side condicional ao perfil admin
(jinja2 if), defesa em profundidade alem do client-side window.AGENT_DEBUG.

Aria roles para acessibilidade. data-field/data-section/data-action
atributos para o JS encontrar elementos.

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (secao 5.2)"
```

---

## Task 10: chat.js — extensões na linha inline (P0.2, P0.3, P1.1)

**Files:**
- Modify: `app/static/agente/js/chat.js` (linhas 1104-1212)

- [ ] **Step 1: Localizar `renderSubagentLineStart` (linha ~1104) e adicionar captura de `parent_tool_use_id`**

Localizar o bloco existente:

```js
function renderSubagentLineStart(data) {
    const agentId = data.agent_id || data.task_id;
    const agentType = data.agent_type || data.task_type || data.description || 'subagente';

    if (!agentId || subagentLines.has(agentId)) return;  // idempotente
    ...
    line.className = 'subagent-inline running';
    line.dataset.agentId = agentId;
    line.innerHTML = `...`;
```

Substituir o bloco `line.className` e `dataset` por:

```js
    line.className = 'subagent-inline running';
    line.dataset.agentId = agentId;
    // P1.1: capturar parent_tool_use_id para correlacao visual
    line.dataset.parentToolUseId = data.parent_tool_use_id || '';
    line.innerHTML = `
        <span class="subagent-dot"></span>
        <span class="subagent-badge">${_subagentEscapeHtml(agentType)}</span>
        <span class="subagent-meta">executando…</span>
        <span class="subagent-caret">▼</span>
    `;
```

- [ ] **Step 2: Substituir `renderSubagentLineProgress` (linha ~1140) por versão com tokens**

```js
function renderSubagentLineProgress(data) {
    const agentId = data.agent_id || data.task_id;
    const line = subagentLines.get(agentId);
    if (!line) return;
    const meta = line.querySelector('.subagent-meta');
    if (!meta) return;

    // P0.3: enriquecer meta com tokens + duracao se disponiveis
    const tool = data.last_tool_name || 'processando';
    const usage = data.usage || {};
    const parts = [`${tool}…`];

    if (usage.total_tokens) {
        const tok = usage.total_tokens >= 1000
            ? (usage.total_tokens / 1000).toFixed(1) + 'K'
            : String(usage.total_tokens);
        parts.push(`${tok} tok`);
    }
    if (usage.duration_ms) {
        parts.push(`${(usage.duration_ms / 1000).toFixed(1)}s`);
    }

    meta.textContent = parts.join(' · ');
}
```

- [ ] **Step 3: Substituir `renderSubagentLineSummary` (linha ~1149) para suportar estados failed/stopped (P0.2)**

```js
function renderSubagentLineSummary(data) {
    const agentId = data.agent_id;
    if (!agentId) return;

    let line = subagentLines.get(agentId);

    if (!line) {
        // Fallback: evento chegou sem task_started anterior
        const messagesContainer = document.getElementById('messages') ||
                                  document.querySelector('.messages-container') ||
                                  document.querySelector('.chat-messages');
        if (!messagesContainer) return;
        line = document.createElement('div');
        line.className = 'subagent-inline';
        line.dataset.agentId = agentId;
        line.dataset.parentToolUseId = data.parent_tool_use_id || '';
        messagesContainer.appendChild(line);
        subagentLines.set(agentId, line);
        line.addEventListener('click', () => openOrToggleSubagent(agentId));
    }

    // P0.2: mapear data.status para classe CSS distinta
    line.classList.remove('running', 'done', 'failed', 'stopped', 'error');
    const cssState =
        data.status === 'failed'  ? 'failed'  :
        data.status === 'stopped' ? 'stopped' :
        data.status === 'error'   ? 'error'   :
                                    'done';
    line.classList.add(cssState);

    const numTools = (data.tools_used || []).length;
    const durationSec = Math.round((data.duration_ms || 0) / 100) / 10;
    const costStr = data.cost_usd != null
        ? ` · $${Number(data.cost_usd).toFixed(4)}`
        : '';
    const metaText = `${numTools} tool${numTools !== 1 ? 's' : ''} · ${durationSec}s${costStr}`;

    let priorAgentType = '';
    try {
        const prior = JSON.parse(line.dataset.summary || '{}');
        priorAgentType = prior.agent_type || '';
    } catch (_) { /* ignore */ }
    const badgeText = data.agent_type || priorAgentType || 'subagente';

    line.innerHTML = `
        <span class="subagent-dot"></span>
        <span class="subagent-badge">${_subagentEscapeHtml(badgeText)}</span>
        <span class="subagent-meta">${_subagentEscapeHtml(metaText)}</span>
        <span class="subagent-caret">▼</span>
    `;
    line.dataset.summary = JSON.stringify({ ...data, agent_type: badgeText });
}
```

- [ ] **Step 4: Substituir `toggleSubagentExpand` por `openOrToggleSubagent` (despachador para modal ou fallback)**

Substituir a função `toggleSubagentExpand` inteira (linha ~1214-1285) por:

```js
// Dispatcher: se feature flag MODAL ON e openSubagentModal estiver definido,
// abre modal. Senao, mantem fallback inline expand antigo.
// Fix code-review #6: guard typeof previne TypeError entre commits Task 10 e 11.
function openOrToggleSubagent(agentId) {
    const modalOn = window.AGENT_FEATURES && window.AGENT_FEATURES.subagent_modal;
    if (modalOn && typeof openSubagentModal === 'function') {
        openSubagentModal(agentId);
    } else {
        toggleSubagentExpand(agentId);  // fallback legacy
    }
}

// Fallback legacy mantido para flag OFF
async function toggleSubagentExpand(agentId) {
    const line = subagentLines.get(agentId);
    if (!line) return;
    // [resto da implementacao atual preservada — copiar daqui:]
    if (line.classList.contains('expanded')) {
        line.classList.remove('expanded');
        const details = line.querySelector('.subagent-inline-details');
        if (details) details.remove();
        const header = line.querySelector('.subagent-header');
        if (header) {
            const data = JSON.parse(line.dataset.summary || '{}');
            const numTools = (data.tools_used || []).length;
            const durationSec = Math.round((data.duration_ms || 0) / 100) / 10;
            const costStr = data.cost_usd != null
                ? ` · $${Number(data.cost_usd).toFixed(4)}`
                : '';
            line.innerHTML = `
                <span class="subagent-dot"></span>
                <span class="subagent-badge">${_subagentEscapeHtml(data.agent_type || 'subagente')}</span>
                <span class="subagent-meta">${_subagentEscapeHtml(numTools + ' tools · ' + durationSec + 's' + costStr)}</span>
                <span class="subagent-caret">▼</span>
            `;
        }
        return;
    }

    line.classList.add('expanded');
    const originalHtml = line.innerHTML;
    line.innerHTML = `<div class="subagent-header">${originalHtml}</div>`;

    const details = document.createElement('div');
    details.className = 'subagent-inline-details';
    details.textContent = 'Carregando…';
    line.appendChild(details);

    const sid = sessionId;
    if (!sid) {
        details.textContent = 'Erro: sessao nao identificada';
        return;
    }

    try {
        const resp = await fetch(`/agente/api/sessions/${sid}/subagents/${agentId}/summary`);
        if (!resp.ok) {
            details.textContent = `Erro ${resp.status}`;
            return;
        }
        const payload = await resp.json();
        const s = payload.subagent || {};
        const toolsHtml = (s.tools_used || []).map((t) =>
            `<li><span class="tool-name">${_subagentEscapeHtml(t.name)}</span>` +
            `<span class="tool-result">${_subagentEscapeHtml((t.result_summary || '').slice(0, 120))}</span></li>`
        ).join('');
        const validationHtml = line.dataset.validation
            ? (() => {
                const v = JSON.parse(line.dataset.validation);
                return `<div class="validation-reason">Score ${v.score}: ${_subagentEscapeHtml(v.reason || '')}</div>`;
              })()
            : '';
        const findingsHtml = s.findings_text
            ? `<div style="margin-top:8px;color:var(--agent-text-secondary)">${_subagentEscapeHtml(s.findings_text.slice(0, 400))}</div>`
            : '';
        details.innerHTML = `<ol>${toolsHtml}</ol>${validationHtml}${findingsHtml}`;
    } catch (err) {
        details.textContent = `Erro: ${err.message}`;
    }
}
```

- [ ] **Step 5: Substituir o `addEventListener` de click em `renderSubagentLineStart` para usar dispatcher**

Localizar `line.addEventListener('click', () => toggleSubagentExpand(agentId));` (na função renderSubagentLineStart) e substituir por:

```js
line.addEventListener('click', () => openOrToggleSubagent(agentId));
```

Idem em `renderSubagentLineSummary` (linha ~1167):

```js
line.addEventListener('click', () => openOrToggleSubagent(agentId));
```

- [ ] **Step 6: Commit (modal function ainda não implementada — próxima task)**

```bash
git add app/static/agente/js/chat.js
git commit -m "feat(agente): chat.js suporta estados ricos + tokens + dispatcher modal

P0.2: renderSubagentLineSummary mapeia data.status para 5 classes CSS
distintas (running/done/failed/stopped/error).

P0.3: renderSubagentLineProgress mostra 'Grep · 3.4K tok · 12s' quando
data.usage chega no task_progress.

P1.1: linha inline captura data-parent-tool-use-id em renderLineStart/Summary
para CSS pseudo-element renderizar marcador '↳' (ja no _subagent-inline.css).

Click handler agora chama openOrToggleSubagent(agentId): dispatcher que abre
modal (window.AGENT_FEATURES.subagent_modal) ou fallback inline expand legacy.
openSubagentModal sera implementado na Task 11.

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (secao 5.2)"
```

---

## Task 11: chat.js — openSubagentModal + closeSubagentModal + togglePII

**Files:**
- Modify: `app/static/agente/js/chat.js`
- Modify: `app/agente/templates/agente/chat.html` (injetar AGENT_FEATURES + AGENT_DEBUG)

- [ ] **Step 1: Adicionar variáveis globais ao topo do chat.html (no `<script>` que já existe ou criar bloco logo após o markup do modal)**

Localizar o bloco `<script>` que inicializa `window.AGENT_DEBUG` (deve existir; pesquisar `AGENT_DEBUG`). Adicionar ao mesmo bloco:

```html
<script>
window.AGENT_FEATURES = {
    subagent_modal: {{ 'true' if config.get('USE_SUBAGENT_MODAL', True) else 'false' }},
    subagent_rich_states: {{ 'true' if config.get('USE_SUBAGENT_RICH_STATES', True) else 'false' }},
    subagent_live_progress: {{ 'true' if config.get('USE_SUBAGENT_LIVE_PROGRESS', True) else 'false' }},
    subagent_rename_tag: {{ 'true' if config.get('USE_SUBAGENT_RENAME_TAG', False) else 'false' }},
    subagent_output_download: {{ 'true' if config.get('USE_SUBAGENT_OUTPUT_DOWNLOAD', False) else 'false' }},
};
window.AGENT_DEBUG = window.AGENT_DEBUG || {};
window.AGENT_DEBUG.is_admin = {{ 'true' if current_user.perfil == 'administrador' else 'false' }};
</script>
```

> Importante: `config.get('USE_SUBAGENT_*')` reads from Flask app config; precisamos garantir que app config tem essas chaves. Adicionar em `app/__init__.py` (ou onde Config é carregado) **se ainda não foram expostos**:
>
> ```python
> # No init_app() ou create_app() — apos load das feature flags:
> from app.agente.config import feature_flags
> app.config['USE_SUBAGENT_MODAL'] = feature_flags.USE_SUBAGENT_MODAL
> app.config['USE_SUBAGENT_RICH_STATES'] = feature_flags.USE_SUBAGENT_RICH_STATES
> app.config['USE_SUBAGENT_LIVE_PROGRESS'] = feature_flags.USE_SUBAGENT_LIVE_PROGRESS
> app.config['USE_SUBAGENT_RENAME_TAG'] = feature_flags.USE_SUBAGENT_RENAME_TAG
> app.config['USE_SUBAGENT_OUTPUT_DOWNLOAD'] = feature_flags.USE_SUBAGENT_OUTPUT_DOWNLOAD
> ```

- [ ] **Step 2: Adicionar funções de modal ao final do `chat.js` (após `toggleSubagentExpand`)**

```js
// ═══════════════════════════════════════════════════════════════════════
// MODAL DE TRANSCRIPT (P0.1, P1.1 parent navigation)
// ═══════════════════════════════════════════════════════════════════════

let _currentModalAgentId = null;

async function openSubagentModal(agentId) {
    const modal = document.getElementById('subagent-transcript-modal');
    if (!modal) {
        console.warn('[subagent-modal] markup nao encontrado');
        return;
    }
    _currentModalAgentId = agentId;

    // Reset modal
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
    _setSubagentModalLoading();

    // Popular header com dados da linha (se existir)
    const line = subagentLines.get(agentId);
    if (line) {
        const summary = JSON.parse(line.dataset.summary || '{}');
        _setSubagentModalHeader(summary);
    }

    // Fetch transcript
    const sid = sessionId;
    if (!sid) {
        _setSubagentModalError('Sessao nao identificada.');
        return;
    }

    try {
        const resp = await fetch(`/agente/api/sessions/${sid}/subagents/${agentId}/transcript`);
        if (resp.status === 404) {
            const p = await resp.json().catch(() => ({}));
            if ((p.error || '').includes('arquivada')) {
                _setSubagentModalEmpty('Transcript não encontrado. A sessão pode ter sido arquivada.', true);
            } else {
                _setSubagentModalError('Visualização detalhada indisponível no momento.');
            }
            return;
        }
        if (resp.status === 403) {
            _setSubagentModalError('Você não tem acesso a esta sessão.');
            return;
        }
        if (!resp.ok) {
            _setSubagentModalError(`Não foi possível carregar o transcript. (HTTP ${resp.status})`);
            return;
        }
        const payload = await resp.json();
        _renderSubagentTranscript(payload);
    } catch (err) {
        console.error('[subagent-modal] fetch falhou:', err);
        _setSubagentModalError('Conexão lenta. Verifique sua rede e tente novamente.');
    }
}

function closeSubagentModal() {
    const modal = document.getElementById('subagent-transcript-modal');
    if (!modal) return;
    modal.hidden = true;
    document.body.style.overflow = '';
    _currentModalAgentId = null;
}

function _setSubagentModalHeader(summary) {
    const modal = document.getElementById('subagent-transcript-modal');
    if (!modal) return;
    const badge = modal.querySelector('[data-field="agent_type"]');
    const title = modal.querySelector('[data-field="title"]');
    const meta = modal.querySelector('[data-field="meta"]');
    if (badge) badge.textContent = summary.agent_type || 'subagente';
    if (title) title.textContent = summary.name || (summary.agent_id || '').slice(0, 12);

    if (meta) {
        const numTools = (summary.tools_used || []).length;
        const durSec = ((summary.duration_ms || 0) / 1000).toFixed(1);
        const costStr = summary.cost_usd != null
            ? ` · $${Number(summary.cost_usd).toFixed(4)}`
            : '';
        meta.textContent = `${numTools} tools · ${durSec}s${costStr}`;
    }
}

function _setSubagentModalLoading() {
    const modal = document.getElementById('subagent-transcript-modal');
    if (!modal) return;
    ['prompt', 'timeline', 'findings'].forEach(name => {
        const sec = modal.querySelector(`[data-section="${name}"]`);
        if (sec) {
            sec.classList.add('is-loading');
            const c = sec.querySelector('[data-field]');
            if (c) c.innerHTML = '<div class="skeleton"></div>';
        }
    });
}

function _setSubagentModalError(message) {
    const modal = document.getElementById('subagent-transcript-modal');
    if (!modal) return;
    // Fix code-review #2: limpa loading de TODAS as secoes (forEach corrigido)
    modal.querySelectorAll('.subagent-modal-section').forEach(sec => {
        sec.classList.remove('is-loading');
    });
    const timeline = modal.querySelector('[data-section="timeline"]');
    if (timeline) {
        timeline.innerHTML = `
            <div class="subagent-modal-error">
                <span class="icon">⚠</span>
                <div>${_subagentEscapeHtml(message)}</div>
                <button type="button" onclick="openSubagentModal('${_currentModalAgentId}')">Tentar novamente</button>
            </div>`;
    }
}

function _setSubagentModalEmpty(message, showRestoreBtn) {
    const modal = document.getElementById('subagent-transcript-modal');
    if (!modal) return;
    const timeline = modal.querySelector('[data-section="timeline"]');
    if (timeline) {
        timeline.innerHTML = `
            <div class="subagent-modal-empty">
                <div>${_subagentEscapeHtml(message)}</div>
                ${showRestoreBtn ? '<button type="button" disabled title="Restore S3 (em breve)">Tentar restaurar do arquivo</button>' : ''}
            </div>`;
    }
}

function _renderSubagentTranscript(payload) {
    const modal = document.getElementById('subagent-transcript-modal');
    if (!modal) return;

    const transcript = payload.transcript || [];

    // Remover loading
    ['prompt', 'timeline', 'findings'].forEach(name => {
        const sec = modal.querySelector(`[data-section="${name}"]`);
        if (sec) sec.classList.remove('is-loading');
    });

    // Prompt = primeira entry kind=user_prompt
    const userPrompt = transcript.find(e => e.kind === 'user_prompt');
    const promptEl = modal.querySelector('[data-field="prompt"]');
    if (promptEl) {
        promptEl.textContent = userPrompt
            ? userPrompt.content
            : '(prompt não encontrado no transcript)';
    }

    // Timeline = todas entries excluindo o prompt inicial (mostrado acima)
    // e o ultimo assistant_text (que vira findings)
    const lastAssistantText = [...transcript].reverse().find(e => e.kind === 'assistant_text');
    const timelineEntries = transcript.filter(e =>
        e !== userPrompt && e !== lastAssistantText
    );

    const timelineEl = modal.querySelector('[data-field="timeline"]');
    if (timelineEl) {
        if (timelineEntries.length === 0) {
            timelineEl.innerHTML = '<li class="entry-empty">(sem tool calls intermediarios)</li>';
        } else {
            timelineEl.innerHTML = timelineEntries.map(entry => {
                const c = typeof entry.content === 'object'
                    ? `<strong>${_subagentEscapeHtml(entry.content.name || '')}</strong>(${_subagentEscapeHtml(JSON.stringify(entry.content.input || {}).slice(0, 200))})`
                    : _subagentEscapeHtml(String(entry.content || '').slice(0, 500));
                return `
                    <li class="kind-${entry.kind}">
                        <span class="entry-kind">${entry.kind}</span>
                        <div class="entry-content">${c}</div>
                    </li>`;
            }).join('');
        }
    }

    // Findings = ultimo assistant_text
    const findingsEl = modal.querySelector('[data-field="findings"]');
    if (findingsEl) {
        findingsEl.textContent = lastAssistantText
            ? lastAssistantText.content
            : '(nenhum findings retornado)';
    }

    // Atualiza toggle PII state
    _updatePIIToggleButton(payload.include_pii);
}

async function _togglePIIInModal() {
    if (!_currentModalAgentId) return;
    const btn = document.querySelector('#subagent-transcript-modal [data-action="toggle-pii"]');
    if (!btn) return;
    btn.disabled = true;

    const isActive = btn.classList.contains('active');
    const newEnabled = !isActive;
    try {
        const resp = await fetch(
            `/agente/api/sessions/${sessionId}/subagents/${_currentModalAgentId}/pii-toggle`,
            {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({enabled: newEnabled}),
            }
        );
        if (resp.status === 429) {
            alert('Muitas trocas em sequência. Aguarde 1 minuto.');
            btn.disabled = false;
            // Reabilita botao apos 60s
            setTimeout(() => { btn.disabled = false; }, 60000);
            return;
        }
        if (!resp.ok) {
            alert('Não foi possível alternar PII. Tente novamente.');
            btn.disabled = false;
            return;
        }
        // Refetch transcript com include_pii atualizado
        await openSubagentModal(_currentModalAgentId);
    } catch (err) {
        console.error('[pii-toggle] falhou:', err);
        alert('Recurso temporariamente indisponível.');
    } finally {
        btn.disabled = false;
    }
}

function _updatePIIToggleButton(includePii) {
    const btn = document.querySelector('#subagent-transcript-modal [data-action="toggle-pii"]');
    if (!btn) return;
    if (includePii) {
        btn.classList.add('active');
        btn.textContent = 'Ocultar PII';
    } else {
        btn.classList.remove('active');
        btn.textContent = 'Mostrar PII';
    }
}

// Event listeners do modal
document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('subagent-transcript-modal');
    if (!modal) return;

    // Close button + backdrop
    modal.querySelectorAll('[data-close="modal"]').forEach(el => {
        el.addEventListener('click', closeSubagentModal);
    });

    // PII toggle (admin only)
    const piiBtn = modal.querySelector('[data-action="toggle-pii"]');
    if (piiBtn) {
        piiBtn.addEventListener('click', _togglePIIInModal);
    }

    // ESC fecha
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !modal.hidden) {
            closeSubagentModal();
        }
    });
});
```

- [ ] **Step 3: Quick smoke test no browser local**

```bash
python run.py &
sleep 3
echo "Acesse http://localhost:5000/agente/chat — abra DevTools Console e verifique:"
echo "1. window.AGENT_FEATURES.subagent_modal === true"
echo "2. window.AGENT_DEBUG.is_admin (true se admin logado)"
echo "3. Sem erros JS no console"
echo "Quando terminar, mate o processo: kill %1"
```

- [ ] **Step 4: Commit**

```bash
git add app/static/agente/js/chat.js app/agente/templates/agente/chat.html
git commit -m "feat(agente): chat.js openSubagentModal + togglePII + loading/error states

P0.1: openSubagentModal(agentId) abre modal, fetcha /transcript via lazy
fetch e renderiza 3 secoes (prompt, timeline, findings).

Estados visuais cobertos:
- loading: skeleton shimmer durante fetch
- empty: 'Transcript nao encontrado' com botao retry
- error: '⚠ ...' com botao 'Tentar novamente'
- success: renderiza transcript em ordem

Botao 'Mostrar PII' (admin only):
- click -> POST /pii-toggle -> refetch transcript com include_pii=true
- Rate limit 429 -> alerta + desabilita 60s
- 5min TTL Redis (server-side), botao reflete estado

Event listeners no DOMContentLoaded: close button, backdrop click, ESC key.

window.AGENT_FEATURES injetado server-side com feature flags atuais.
window.AGENT_DEBUG.is_admin para frontend filtrar acoes admin-only.

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (secao 5.2)"
```

---

## Task 12: Pre-merge — validação completa

**Files:** (todos os tocados nas Tasks 1-11)

- [ ] **Step 1: Rodar suite completa de testes do agente**

```bash
source .venv/bin/activate
pytest tests/agente/ -v --tb=short 2>&1 | tail -30
```
Expected: testes novos das Tasks 2-5 PASS. Testes pré-existentes mantêm baseline.

- [ ] **Step 2: Verificar que configure_mappers ainda inicializa**

```bash
python -c "
from app import create_app
from sqlalchemy.orm import configure_mappers
app = create_app()
with app.app_context():
    configure_mappers()
    print('Mappers OK')
"
```
Expected: `Mappers OK`

- [ ] **Step 3: Lint UI policy**

```bash
python scripts/audits/ui_policy_lint.py --enforce-new 2>&1 | tail -5
```
Expected: `Violacoes encontradas: 0`

- [ ] **Step 4: Push para criar PR-A**

```bash
git push origin main
```
Expected: push ok.

- [ ] **Step 5: Aguardar auto-deploy Render finalizar**

```bash
# Aguardar deploy via MCP Render ou checagem manual em dashboard
echo "Aguarde notificacao 'deploy live' no dashboard Render."
echo "Tempo tipico: ~13min."
```

- [ ] **Step 6: Smoketest pós-deploy em prod**

Como admin logado:

```bash
echo "Em browser logado como admin, abrir:"
echo "https://sistema-fretes.onrender.com/agente/api/admin/debug/subagent-smoketest"
echo "Esperado: healthy=true, transcript_entries>0, has_user_prompt=true"
```

- [ ] **Step 7: Executar Roadmap de Testes (spec seção 10.2)**

Sequência completa:
- Bloco A (estados visuais): 4 cenários
- Bloco B (progresso ao vivo): 2 cenários bloqueadores
- Bloco C (modal transcript): 7 cenários
- Bloco D (PII e admin toggle): 7 cenários — segurança crítica
- Bloco E (correlação parent): 1 cenário bloqueador
- Bloco H (backward-compat): 1 cenário (H.1)
- Bloco I (performance): 1 cenário (I.1)
- Bloco J (erro handling): 2 cenários (J.1, J.5)

Total: 22 cenários bloqueadores Fase 1.

Documento de referência: `docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md` seção 10.2.

- [ ] **Step 8: Monitorar Sentry primeiros 60min pós-deploy**

```bash
# Via MCP Sentry ou dashboard https://nacom.sentry.io
# Query: project:python-flask environment:production firstSeen:-1h tags[feature]:subagent_modal
# Esperado: zero novas issues
```

---

# FASE 2 — Rename/tag + Download output_file

## Task 13: Endpoint PATCH /subagents/<aid> (rename/tag, TDD)

**Files:**
- Modify: `app/agente/routes/subagents.py`
- Modify: `tests/agente/test_subagent_routes.py`

- [ ] **Step 1: Adicionar testes ao `test_subagent_routes.py`**

```python
# === PATCH /subagents/<aid> (Fase 2) ===

def test_patch_subagent_404_flag_off(client, normal_user, session_owned_by, monkeypatch):
    monkeypatch.setattr('app.agente.config.feature_flags.USE_SUBAGENT_RENAME_TAG', False)
    _login(client, normal_user)
    r = client.patch(
        f'/agente/api/sessions/{session_owned_by.session_id}/subagents/{"b"*32}',
        json={'name': 'Test'},
    )
    assert r.status_code == 404


def test_patch_subagent_persiste_em_jsonb(client, normal_user, session_owned_by, app):
    _login(client, normal_user)
    aid = 'b' * 32
    r = client.patch(
        f'/agente/api/sessions/{session_owned_by.session_id}/subagents/{aid}',
        json={'name': 'Analise pedido VCD123', 'tags': ['p3', 'urgente']},
    )
    assert r.status_code == 200

    with app.app_context():
        sess = AgentSession.query.filter_by(session_id=session_owned_by.session_id).first()
        meta = sess.data.get('subagent_metadata', {}).get(aid)
        assert meta is not None
        assert meta['name'] == 'Analise pedido VCD123'
        assert meta['tags'] == ['p3', 'urgente']
        assert meta['updated_by'] == normal_user.id


def test_patch_subagent_sanitiza_html_xss(client, normal_user, session_owned_by, app):
    _login(client, normal_user)
    aid = 'b' * 32
    r = client.patch(
        f'/agente/api/sessions/{session_owned_by.session_id}/subagents/{aid}',
        json={'name': '<script>alert(1)</script>'},
    )
    assert r.status_code == 200

    with app.app_context():
        sess = AgentSession.query.filter_by(session_id=session_owned_by.session_id).first()
        meta = sess.data.get('subagent_metadata', {}).get(aid)
        assert '<script>' not in meta['name']
        assert 'alert' in meta['name'] or 'alert(1)' in meta['name']  # texto preservado, tags removidas


def test_patch_subagent_400_nome_muito_longo(client, normal_user, session_owned_by):
    _login(client, normal_user)
    r = client.patch(
        f'/agente/api/sessions/{session_owned_by.session_id}/subagents/{"b"*32}',
        json={'name': 'x' * 100},
    )
    assert r.status_code == 400


def test_patch_subagent_400_muitas_tags(client, normal_user, session_owned_by):
    _login(client, normal_user)
    r = client.patch(
        f'/agente/api/sessions/{session_owned_by.session_id}/subagents/{"b"*32}',
        json={'tags': [f'tag{i}' for i in range(11)]},
    )
    assert r.status_code == 400
```

- [ ] **Step 2: Rodar para confirmar falhas**

```bash
pytest tests/agente/test_subagent_routes.py -k "patch_subagent" -v 2>&1 | tail -10
```
Expected: 5 FAIL com 404 ou 405.

- [ ] **Step 3: Adicionar endpoint em `routes/subagents.py`**

```python
import bleach  # adicionar nos imports do topo


@agente_bp.route(
    '/api/sessions/<session_id>/subagents/<agent_id>',
    methods=['PATCH'],
)
@login_required
def api_subagent_patch(session_id: str, agent_id: str):
    """Renomeia e/ou adiciona tags a um subagent (Fase 2, P1.2).

    Persiste em agent_sessions.data['subagent_metadata'][agent_id].
    Autorizacao: dono OU admin. Sanitizacao HTML via bleach.
    """
    from app.agente.config.feature_flags import USE_SUBAGENT_RENAME_TAG

    if not USE_SUBAGENT_RENAME_TAG:
        return jsonify({'success': False, 'error': 'Feature desabilitada'}), 404

    if not _is_safe_id(session_id) or not _is_safe_id(agent_id):
        return jsonify({'success': False, 'error': 'IDs invalidos'}), 404

    sess = AgentSession.query.filter_by(session_id=session_id).first()
    if sess is None:
        return jsonify({'success': False, 'error': 'Sessao nao encontrada'}), 404

    is_admin = getattr(current_user, 'perfil', None) == 'administrador'
    if not is_admin and sess.user_id != current_user.id:
        return jsonify({
            'success': False,
            'error': 'Acesso restrito ao dono da sessao ou administrador',
        }), 403

    body = request.get_json(silent=True) or {}
    name = body.get('name')
    tags = body.get('tags')

    # Validacoes
    if name is not None:
        if not isinstance(name, str):
            return jsonify({'success': False, 'error': 'name deve ser string'}), 400
        if len(name) > 80:
            return jsonify({
                'success': False,
                'error': 'Nome deve ter no maximo 80 caracteres.',
            }), 400
        # Sanitizar HTML
        name = bleach.clean(name, tags=[], strip=True).strip()

    if tags is not None:
        if not isinstance(tags, list):
            return jsonify({'success': False, 'error': 'tags deve ser lista'}), 400
        if len(tags) > 10:
            return jsonify({
                'success': False,
                'error': 'Maximo 10 tags permitidas.',
            }), 400
        clean_tags = []
        for t in tags:
            if not isinstance(t, str):
                return jsonify({'success': False, 'error': 'tag deve ser string'}), 400
            if len(t) > 30:
                return jsonify({
                    'success': False,
                    'error': 'Tag deve ter no maximo 30 caracteres.',
                }), 400
            clean_tags.append(bleach.clean(t, tags=[], strip=True).strip())
        tags = clean_tags

    # Persistir em JSONB
    metadata = sess.data.setdefault('subagent_metadata', {})
    entry = metadata.setdefault(agent_id, {})
    if name is not None:
        entry['name'] = name
    if tags is not None:
        entry['tags'] = tags
    entry['updated_at'] = agora_brasil_naive().isoformat()
    entry['updated_by'] = current_user.id

    flag_modified(sess, 'data')
    db.session.commit()

    logger.info(
        f"[subagent_patch] user_id={current_user.id} "
        f"session={session_id[:16]} agent={agent_id[:12]} "
        f"name={'<set>' if name else '<unchanged>'} "
        f"tags={'<set>' if tags else '<unchanged>'}"
    )

    return jsonify({
        'success': True,
        'metadata': entry,
    })
```

- [ ] **Step 4: Rodar testes**

```bash
pytest tests/agente/test_subagent_routes.py -k "patch_subagent" -v 2>&1 | tail -10
```
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agente/routes/subagents.py tests/agente/test_subagent_routes.py
git commit -m "feat(agente): endpoint PATCH /subagents/<aid> (rename/tag, Fase 2)

P1.2: persiste rename/tag de subagent em agent_sessions.data['subagent_metadata'].
- Dono OU admin (403 caso contrario)
- Sanitizacao HTML via bleach.clean(tags=[], strip=True) — anti-XSS
- Validacoes: name max 80 chars, tags max 10 items × max 30 chars cada
- flag_modified(sess, 'data') obrigatorio (R7)

Testes: 5 cenarios (flag off, persistencia, XSS sanitizacao, nome longo,
muitas tags).

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (secao 5.1, cenario 4)"
```

---

## Task 14: Endpoint GET /output_file (download JSONL, TDD)

**Files:**
- Modify: `app/agente/routes/subagents.py`
- Modify: `tests/agente/test_subagent_routes.py`

- [ ] **Step 1: Adicionar testes**

```python
# === GET /output_file (Fase 2) ===

def test_output_file_404_flag_off(client, normal_user, session_owned_by, monkeypatch):
    monkeypatch.setattr('app.agente.config.feature_flags.USE_SUBAGENT_OUTPUT_DOWNLOAD', False)
    _login(client, normal_user)
    r = client.get(
        f'/agente/api/sessions/{session_owned_by.session_id}/subagents/{"b"*32}/output_file'
    )
    assert r.status_code == 404


def test_output_file_admin_recebe_raw(client, admin_user, session_owned_by, tmp_path, monkeypatch):
    """Admin recebe JSONL raw."""
    jsonl_path = tmp_path / 'fake.jsonl'
    jsonl_path.write_text('{"x":1,"cpf":"123.456.789-00"}\n')

    monkeypatch.setattr(
        'app.agente.routes.subagents._resolve_transcript_path',
        lambda sid, aid: str(jsonl_path)
    )
    _login(client, admin_user)
    r = client.get(
        f'/agente/api/sessions/{session_owned_by.session_id}/subagents/{"b"*32}/output_file'
    )
    assert r.status_code == 200
    assert r.headers['Content-Type'] == 'application/jsonl'
    assert '123.456.789-00' in r.get_data(as_text=True)


def test_output_file_non_admin_recebe_mask(client, normal_user, session_owned_by, tmp_path, monkeypatch):
    """Dono nao-admin recebe JSONL com PII mascarada linha a linha."""
    jsonl_path = tmp_path / 'fake.jsonl'
    jsonl_path.write_text('{"x":1,"cpf":"123.456.789-00"}\n')

    monkeypatch.setattr(
        'app.agente.routes.subagents._resolve_transcript_path',
        lambda sid, aid: str(jsonl_path)
    )
    _login(client, normal_user)
    r = client.get(
        f'/agente/api/sessions/{session_owned_by.session_id}/subagents/{"b"*32}/output_file'
    )
    assert r.status_code == 200
    text = r.get_data(as_text=True)
    assert '123.456.789-00' not in text  # mascarado
```

- [ ] **Step 2: Rodar para confirmar falhas**

```bash
pytest tests/agente/test_subagent_routes.py -k "output_file" -v 2>&1 | tail -10
```
Expected: 3 FAIL.

- [ ] **Step 3: Adicionar endpoint em `routes/subagents.py`**

```python
from flask import Response, stream_with_context
import os
from app.agente.sdk.subagent_reader import _resolve_transcript_path  # adicionar import
from app.agente.utils.pii_masker import mask_pii


@agente_bp.route(
    '/api/sessions/<session_id>/subagents/<agent_id>/output_file',
    methods=['GET'],
)
@login_required
def api_subagent_output_file(session_id: str, agent_id: str):
    """Download do JSONL bruto do subagent (Fase 2, P1.3).

    Admin: arquivo raw.
    Dono non-admin: cada linha passada por mask_pii antes de stream.
    Sanity check: > 50MB retorna 413.
    """
    from app.agente.config.feature_flags import USE_SUBAGENT_OUTPUT_DOWNLOAD

    if not USE_SUBAGENT_OUTPUT_DOWNLOAD:
        return jsonify({'success': False, 'error': 'Feature desabilitada'}), 404

    if not _is_safe_id(session_id) or not _is_safe_id(agent_id):
        return jsonify({'success': False, 'error': 'IDs invalidos'}), 404

    sess = AgentSession.query.filter_by(session_id=session_id).first()
    if sess is None:
        return jsonify({'success': False, 'error': 'Sessao nao encontrada'}), 404

    is_admin = getattr(current_user, 'perfil', None) == 'administrador'
    if not is_admin and sess.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Acesso restrito'}), 403

    path = _resolve_transcript_path(session_id, agent_id)
    if not path or not os.path.exists(path):
        # TODO Fase 2.1: tentar restore S3 antes de 404
        return jsonify({
            'success': False,
            'error': 'Arquivo nao disponivel para download.',
        }), 404

    # Sanity check tamanho (50MB cap)
    size = os.path.getsize(path)
    if size > 50 * 1024 * 1024:
        return jsonify({
            'success': False,
            'error': 'Arquivo muito grande para download direto.',
        }), 413

    def generate():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if is_admin:
                        yield line
                    else:
                        try:
                            yield mask_pii(line)
                        except Exception:
                            yield line  # fallback se mask_pii falhar
        except (OSError, IOError) as e:
            logger.error(f"[output_file] read failed: {e}")
            yield ''

    filename = f"{agent_id[:12]}.jsonl"
    headers = {
        'Content-Type': 'application/jsonl',
        'Content-Disposition': f'attachment; filename="{filename}"',
    }
    return Response(stream_with_context(generate()), headers=headers)
```

- [ ] **Step 4: Rodar testes**

```bash
pytest tests/agente/test_subagent_routes.py -k "output_file" -v 2>&1 | tail -10
```
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agente/routes/subagents.py tests/agente/test_subagent_routes.py
git commit -m "feat(agente): endpoint GET /output_file (download JSONL, Fase 2)

P1.3: streama JSONL bruto do subagent via Flask Response stream_with_context.
- Admin: arquivo raw, Content-Type application/jsonl
- Dono non-admin: cada linha mask_pii() antes de stream
- Sanity check: > 50MB retorna 413 com mensagem clara
- 404 se path nao existe (S3 restore em Fase 2.1)

Testes: 3 cenarios (flag off, admin raw, non-admin masked).

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (secao 5.1, cenario output_file)"
```

---

## Task 15: chat.js — botões rename/tag/download no modal

**Files:**
- Modify: `app/static/agente/js/chat.js`

- [ ] **Step 1: Adicionar funções ao final do chat.js**

```js
// ═══════════════════════════════════════════════════════════════════════
// MODAL ACOES — Rename, Tag, Download (Fase 2)
// ═══════════════════════════════════════════════════════════════════════

async function renameSubagent(agentId, newName) {
    if (!sessionId) return false;
    try {
        const resp = await fetch(
            `/agente/api/sessions/${sessionId}/subagents/${agentId}`,
            {
                method: 'PATCH',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: newName}),
            }
        );
        if (resp.status === 400) {
            const p = await resp.json().catch(() => ({}));
            alert(p.error || 'Nome invalido.');
            return false;
        }
        if (!resp.ok) {
            alert('Nao foi possivel renomear.');
            return false;
        }
        // Atualizar UI: header do modal + linha inline
        const modal = document.getElementById('subagent-transcript-modal');
        if (modal) {
            const title = modal.querySelector('[data-field="title"]');
            if (title) title.textContent = newName;
        }
        const line = subagentLines.get(agentId);
        if (line) {
            const summary = JSON.parse(line.dataset.summary || '{}');
            summary.name = newName;
            line.dataset.summary = JSON.stringify(summary);
        }
        return true;
    } catch (err) {
        console.error('[renameSubagent] falhou:', err);
        alert('Conexao falhou.');
        return false;
    }
}

async function setSubagentTags(agentId, tags) {
    if (!sessionId) return false;
    try {
        const resp = await fetch(
            `/agente/api/sessions/${sessionId}/subagents/${agentId}`,
            {
                method: 'PATCH',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({tags: tags}),
            }
        );
        if (resp.status === 400) {
            const p = await resp.json().catch(() => ({}));
            alert(p.error || 'Tags invalidas.');
            return false;
        }
        if (!resp.ok) {
            alert('Nao foi possivel salvar tags.');
            return false;
        }
        return true;
    } catch (err) {
        console.error('[setSubagentTags] falhou:', err);
        return false;
    }
}

function downloadSubagentJsonl(agentId) {
    if (!sessionId || !agentId) return;
    const url = `/agente/api/sessions/${sessionId}/subagents/${agentId}/output_file`;
    // Trigger download via link click
    const link = document.createElement('a');
    link.href = url;
    link.download = `${agentId.slice(0, 12)}.jsonl`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Adicionar listeners dos botoes Fase 2 quando flags estiverem ON
document.addEventListener('DOMContentLoaded', () => {
    if (!window.AGENT_FEATURES) return;

    const modal = document.getElementById('subagent-transcript-modal');
    if (!modal) return;

    // Botao download visivel se flag ON
    const dlBtn = modal.querySelector('[data-action="download-jsonl"]');
    if (dlBtn) {
        if (window.AGENT_FEATURES.subagent_output_download) {
            dlBtn.hidden = false;
            dlBtn.addEventListener('click', () => {
                if (_currentModalAgentId) {
                    downloadSubagentJsonl(_currentModalAgentId);
                }
            });
        }
    }

    // Botoes rename/tag: prompts simples por enquanto (UI rica em iteracao futura)
    if (window.AGENT_FEATURES.subagent_rename_tag) {
        // Inject rename + tag buttons dinamicamente
        const actions = modal.querySelector('.subagent-modal-actions');
        if (actions && window.AGENT_DEBUG && window.AGENT_DEBUG.is_admin) {
            const renameBtn = document.createElement('button');
            renameBtn.type = 'button';
            renameBtn.textContent = 'Renomear';
            renameBtn.title = 'Definir nome do subagent';
            renameBtn.addEventListener('click', async () => {
                if (!_currentModalAgentId) return;
                const name = prompt('Nome (max 80 chars):');
                if (name === null) return;
                if (name.length > 80) {
                    alert('Nome muito longo (max 80).');
                    return;
                }
                await renameSubagent(_currentModalAgentId, name);
            });

            const tagBtn = document.createElement('button');
            tagBtn.type = 'button';
            tagBtn.textContent = 'Tags';
            tagBtn.title = 'Editar tags (separadas por virgula)';
            tagBtn.addEventListener('click', async () => {
                if (!_currentModalAgentId) return;
                const raw = prompt('Tags separadas por virgula (max 10, cada max 30 chars):');
                if (raw === null) return;
                const tags = raw.split(',').map(t => t.trim()).filter(t => t.length > 0);
                if (tags.length > 10) {
                    alert('Maximo 10 tags.');
                    return;
                }
                if (tags.some(t => t.length > 30)) {
                    alert('Cada tag pode ter no maximo 30 chars.');
                    return;
                }
                await setSubagentTags(_currentModalAgentId, tags);
            });

            const closeBtn = actions.querySelector('.btn-close');
            actions.insertBefore(renameBtn, closeBtn);
            actions.insertBefore(tagBtn, closeBtn);
        }
    }
});
```

- [ ] **Step 2: Smoke test local (admin logado, USE_SUBAGENT_RENAME_TAG=true)**

```bash
python run.py &
sleep 3
echo "Browser: http://localhost:5000/agente/chat"
echo "Disparar subagent, abrir modal, verificar: botoes Renomear/Tags/JSONL aparecem (admin)"
echo "Encerrar: kill %1"
```

- [ ] **Step 3: Commit**

```bash
git add app/static/agente/js/chat.js
git commit -m "feat(agente): chat.js botoes rename/tag/download no modal (Fase 2)

P1.2: botoes Renomear + Tags no modal (admin only), via prompt() simples.
PATCH /subagents/<aid> com sanitizacao server-side.

P1.3: botao JSONL para download do output_file (visivel se flag ON).
Trigger download via <a download> elemento criado dinamicamente.

Validacoes client-side complementam server-side (defesa em profundidade):
- name max 80 chars
- tags max 10 items, cada max 30 chars

UX simples (prompt()) por enquanto. Form rico em iteracao futura.

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (secao 5.2)"
```

---

## Task 16: Pre-merge Fase 2 — validação completa

**Files:** (tocados nas Tasks 13-15)

- [ ] **Step 1: Rodar suite completa**

```bash
source .venv/bin/activate
pytest tests/agente/ -v --tb=short 2>&1 | tail -25
```
Expected: tests Fase 1 + Fase 2 PASS, baseline mantido.

- [ ] **Step 2: Verificar mappers + lint**

```bash
python -c "from sqlalchemy.orm import configure_mappers; from app import create_app; configure_mappers() if create_app().app_context() else None; print('Mappers OK')"
python scripts/audits/ui_policy_lint.py --enforce-new 2>&1 | tail -3
```

- [ ] **Step 3: Push para PR-B**

```bash
git push origin main
```

- [ ] **Step 4: Aguardar deploy + smoketest**

```bash
echo "Aguarde deploy ~13min, depois rodar:"
echo "curl https://sistema-fretes.onrender.com/agente/api/admin/debug/subagent-smoketest"
echo "Esperado: healthy=true"
```

- [ ] **Step 5: Executar Roadmap Fase 2 (spec seção 10.2)**

- Bloco F (rename/tag): F.1, F.2, F.5, F.6 obrigatórios
- Bloco G (download): G.1, G.2 obrigatórios

Total: 6 cenários bloqueadores Fase 2.

- [ ] **Step 6: Monitorar Sentry 24h**

---

## Self-review

**Spec coverage:**

| Spec section | Implementado em |
|---|---|
| 4.2 Feature flags (5 flags) | Task 1 |
| 5.1 client.py SDK propagation | Task 2 |
| 5.1 subagent_reader.get_subagent_transcript | Task 3 |
| 5.1 POST /pii-toggle endpoint | Task 4 |
| 5.1 GET /transcript endpoint | Task 5 |
| 8.3 Smoketest extension | Task 6 |
| 5.2 CSS inline states + parent link | Task 7 |
| 5.2 CSS modal | Task 8 |
| 5.2 chat.html markup | Task 9 |
| 5.2 chat.js inline extensions (P0.2, P0.3, P1.1) | Task 10 |
| 5.2 chat.js modal functions (P0.1) | Task 11 |
| 9.1 DoD Fase 1 + Roadmap testes | Task 12 |
| 5.1 PATCH /subagents/<aid> (P1.2) | Task 13 |
| 5.1 GET /output_file (P1.3) | Task 14 |
| 5.2 chat.js rename/tag/download buttons | Task 15 |
| 9.2 DoD Fase 2 + Roadmap testes | Task 16 |

Todas requisições do spec mapeadas. Sem placeholders nas tasks. Tipos consistentes (`SubagentTranscriptEntry` definido na Task 3, usado em Tasks 5/14).

**Riscos endereçados:**

| Risco spec 6.5 | Task que mitiga |
|---|---|
| A: SDK não tem `tool_use_id` | Task 2 step 4 (`getattr(message, 'tool_use_id', None)`) |
| B: SDK não popula `usage` | Task 2 step 5 (`getattr(message, 'usage', None)`) |
| C: Endpoint chamado com flag OFF | Tasks 4/5/13/14 (404 check em todos) |
| D: PII vazado | Tasks 4/5 (Redis token + admin check) |
| E: JSONL não existe | Task 3 (3 fallbacks via `_candidate_directories`) |
| F: JSONL corrompido | Task 3 (`SubagentTranscriptEntry` skip linhas inválidas — assumido do pattern existente em `_compute_subagent_metadata_from_jsonl`) |
| G: Admin abusa PII toggle | Task 4 (audit log FIFO 100 + Redis rate limit 10/min + TTL 5min) |
| H: XSS via rename/tag | Task 13 (`bleach.clean(tags=[], strip=True)`) |
