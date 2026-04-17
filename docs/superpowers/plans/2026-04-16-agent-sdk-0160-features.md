# Agent SDK 0.1.60 Features — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar 6 features aproveitando `list_subagents()` / `get_subagent_messages()` do SDK 0.1.60: endpoint admin de debug forense, UI inline expansivel no chat, cost tracking granular, memory mining cross-subagent, migracao soft do protocolo `/tmp/subagent-findings/` e validacao anti-alucinacao assincrona.

**Architecture:** Fundacao comum em `sdk/subagent_reader.py` + `utils/pii_masker.py` — todos consumidores leem por aqui. Pipeline SSE 3-layer (client → routes → chat.js) estendido com eventos `subagent_summary` e `subagent_validation`. Persistencia em `AgentSession.data` (JSONB) + indice GIN. Validacao async via RQ reaproveitando workers existentes (`worker_render.py`, `worker_atacadao.py`). Todas as features atras de feature flags `USE_SUBAGENT_*` com rollback via env var.

**Tech Stack:** Python 3.12 · Flask · PostgreSQL (JSONB + GIN) · Redis + RQ · claude-agent-sdk 0.1.60 · anthropic SDK (Haiku 4.5) · pytest · SSE · Jinja2 · vanilla JS + CSS design tokens.

**Spec:** `docs/superpowers/specs/2026-04-16-agent-sdk-0160-features-design.md`

---

## Visao Geral das Fases

| Fase | Escopo | Tasks | Checkpoint |
|------|--------|-------|------------|
| **1. Fundacao** | `subagent_reader`, `pii_masker`, endpoint admin #1, cost granular #3, migration GIN | 1.1 – 1.6 | apos 1.6 |
| **2. UI + Mining** | Feature flags, emit SSE, rota user-facing, CSS/JS linha inline #6, memory mining #5 | 2.1 – 2.7 | apos 2.7 |
| **3. Migracao Docs** | Helper findings, SUBAGENT_RELIABILITY.md, CLAUDE.md raiz #2 | 3.1 – 3.2 | apos 3.2 |
| **4. Validacao** | Worker validator #4, hook enqueue, SSE event, workers queue, UX warning | 4.1 – 4.6 | apos 4.6 |

**Auto mode:** executar tasks sequencialmente dentro de cada fase. Pausar entre fases para revisao humana. Cada fase termina com commit + testes verdes + checkpoint explicito.

---

## Fase 1 — Fundacao (backend/leitura)

### Task 1.1: Modulo base `subagent_reader.py`

**Files:**
- Create: `app/agente/sdk/subagent_reader.py`
- Test: `tests/agente/sdk/test_subagent_reader.py`

- [ ] **Step 1: Criar arquivo de teste com testes falhando**

Criar `tests/agente/sdk/test_subagent_reader.py`:

```python
"""Testes para subagent_reader — wrapper do SDK 0.1.60."""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_session_message():
    """Mock de SessionMessage retornado pelo SDK."""
    def _make(role, content, timestamp=None):
        msg = MagicMock()
        msg.role = role
        msg.content = content
        msg.timestamp = timestamp or datetime(2026, 4, 16, 14, 22, 0)
        return msg
    return _make


def test_list_session_subagents_returns_list_of_ids():
    """list_session_subagents wrapper chama SDK e retorna lista de agent_ids."""
    from app.agente.sdk.subagent_reader import list_session_subagents

    with patch('app.agente.sdk.subagent_reader.list_subagents') as mock:
        mock.return_value = ['agent-uuid-1', 'agent-uuid-2']
        result = list_session_subagents('session-uuid')

    assert result == ['agent-uuid-1', 'agent-uuid-2']
    mock.assert_called_once_with('session-uuid', directory=None)


def test_list_session_subagents_empty_when_no_subagents():
    """Retorna lista vazia quando nao ha subagentes."""
    from app.agente.sdk.subagent_reader import list_session_subagents

    with patch('app.agente.sdk.subagent_reader.list_subagents', return_value=[]):
        assert list_session_subagents('session-uuid') == []


def test_get_subagent_summary_parses_tools_and_cost(mock_session_message):
    """get_subagent_summary extrai tools, cost, tokens do transcript."""
    from app.agente.sdk.subagent_reader import get_subagent_summary

    messages = [
        mock_session_message('user', 'Analise a carteira do Atacadao'),
        mock_session_message('assistant', [
            {'type': 'tool_use', 'id': 't1', 'name': 'query_sql',
             'input': {'query': 'SELECT * FROM pedidos'}},
        ]),
        mock_session_message('user', [
            {'type': 'tool_result', 'tool_use_id': 't1',
             'content': '24 pedidos em aberto'},
        ]),
        mock_session_message('assistant', [
            {'type': 'text', 'text': 'Encontrei 24 pedidos em aberto.'}
        ]),
    ]

    with patch('app.agente.sdk.subagent_reader.get_subagent_messages',
               return_value=messages), \
         patch('app.agente.sdk.subagent_reader._read_result_metadata',
               return_value={'cost_usd': 0.012, 'duration_ms': 8234,
                             'num_turns': 4, 'input_tokens': 1200,
                             'output_tokens': 400, 'stop_reason': 'end_turn'}):
        summary = get_subagent_summary('session-uuid', 'agent-uuid-1',
                                        agent_type='analista-carteira')

    assert summary.agent_id == 'agent-uuid-1'
    assert summary.agent_type == 'analista-carteira'
    assert summary.status == 'done'
    assert len(summary.tools_used) == 1
    assert summary.tools_used[0]['name'] == 'query_sql'
    assert summary.cost_usd == 0.012
    assert summary.input_tokens == 1200
    assert summary.output_tokens == 400
    assert 'Encontrei 24 pedidos' in summary.findings_text


def test_get_subagent_summary_empty_when_agent_not_found():
    """Retorna SubagentSummary com status='error' quando SDK nao encontra."""
    from app.agente.sdk.subagent_reader import get_subagent_summary

    with patch('app.agente.sdk.subagent_reader.get_subagent_messages',
               return_value=[]):
        summary = get_subagent_summary('session-uuid', 'missing-id',
                                        agent_type='analista-carteira')

    assert summary.status == 'error'
    assert summary.tools_used == []
    assert summary.findings_text == ''


def test_get_subagent_summary_masks_pii_when_include_pii_false(
    mock_session_message
):
    """Quando include_pii=False, aplica pii_masker em tool args/results/findings."""
    from app.agente.sdk.subagent_reader import get_subagent_summary

    messages = [
        mock_session_message('assistant', [
            {'type': 'tool_use', 'id': 't1', 'name': 'query_sql',
             'input': {'cnpj': '12.345.678/0001-90'}},
        ]),
        mock_session_message('assistant', [
            {'type': 'text', 'text': 'Cliente 12.345.678/0001-90 tem 5 pedidos'}
        ]),
    ]

    with patch('app.agente.sdk.subagent_reader.get_subagent_messages',
               return_value=messages), \
         patch('app.agente.sdk.subagent_reader._read_result_metadata',
               return_value={'cost_usd': 0, 'duration_ms': 0, 'num_turns': 1,
                             'input_tokens': 0, 'output_tokens': 0,
                             'stop_reason': 'end_turn'}):
        summary = get_subagent_summary('s', 'a1', agent_type='test',
                                        include_pii=False)

    assert '12.345.678/0001-90' not in summary.findings_text
    assert '**.***.***' in summary.findings_text


def test_get_session_subagents_summary_batch():
    """get_session_subagents_summary combina list + get em batch."""
    from app.agente.sdk.subagent_reader import get_session_subagents_summary

    with patch('app.agente.sdk.subagent_reader.list_session_subagents',
               return_value=['a1', 'a2']), \
         patch('app.agente.sdk.subagent_reader.get_subagent_summary') as mock_get:
        mock_get.return_value = MagicMock(agent_id='mock')
        result = get_session_subagents_summary('session-uuid')

    assert len(result) == 2
    assert mock_get.call_count == 2
```

- [ ] **Step 2: Rodar testes e verificar que falham**

Run: `source .venv/bin/activate && pytest tests/agente/sdk/test_subagent_reader.py -v`
Expected: `ImportError: cannot import name 'list_session_subagents' from 'app.agente.sdk.subagent_reader'`

- [ ] **Step 3: Criar `app/agente/sdk/subagent_reader.py` com implementacao minima**

```python
"""
Wrapper do Claude Agent SDK 0.1.60 para inspecionar transcripts de subagentes.

Encapsula list_subagents() e get_subagent_messages() do SDK em uma API
orientada a dominio — retorna SubagentSummary pronto para serializacao,
com suporte opcional a mascaramento de PII.

Todos os consumidores (endpoint admin, UI, cost tracking, memory mining,
validacao anti-alucinacao) leem por aqui. Ponto unico de adaptacao para
futuras mudancas da API do SDK.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from claude_agent_sdk import get_subagent_messages, list_subagents

from app.agente.utils.pii_masker import mask_pii
from app.utils.timezone import agora_brasil_naive

logger = logging.getLogger('sistema_fretes')

Status = Literal['running', 'done', 'error']


@dataclass
class SubagentSummary:
    """Resumo estruturado de um subagente para serializacao JSON."""
    agent_id: str
    agent_type: str
    status: Status
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_ms: Optional[int]
    tools_used: list[dict] = field(default_factory=list)
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    num_turns: int = 0
    findings_text: str = ''
    stop_reason: Optional[str] = None

    def to_dict(self, include_cost: bool = True) -> dict:
        """Serializa para dict. Se include_cost=False, remove cost_usd."""
        d = {
            'agent_id': self.agent_id,
            'agent_type': self.agent_type,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration_ms': self.duration_ms,
            'tools_used': self.tools_used,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'cache_read_tokens': self.cache_read_tokens,
            'num_turns': self.num_turns,
            'findings_text': self.findings_text,
            'stop_reason': self.stop_reason,
        }
        if include_cost:
            d['cost_usd'] = self.cost_usd
        return d


def list_session_subagents(
    session_id: str,
    directory: Optional[str] = None,
) -> list[str]:
    """Wrapper de list_subagents(). Retorna lista de agent_ids."""
    try:
        return list(list_subagents(session_id, directory=directory))
    except Exception as e:
        logger.debug(f"[subagent_reader] list_subagents falhou: {e}")
        return []


def _read_result_metadata(transcript_path: Optional[str]) -> dict:
    """
    Parseia a ultima ResultMessage do JSONL para extrair cost/tokens/duration.

    Retorna dict com: cost_usd, duration_ms, num_turns, input_tokens,
    output_tokens, cache_read_tokens, stop_reason. Campos ausentes = 0.
    """
    default = {
        'cost_usd': 0.0, 'duration_ms': 0, 'num_turns': 0,
        'input_tokens': 0, 'output_tokens': 0, 'cache_read_tokens': 0,
        'stop_reason': None,
    }
    if not transcript_path or not Path(transcript_path).exists():
        return default

    try:
        last_result = None
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    if msg.get('type') == 'result':
                        last_result = msg
                except json.JSONDecodeError:
                    continue

        if not last_result:
            return default

        usage = last_result.get('usage', {}) or {}
        return {
            'cost_usd': last_result.get('total_cost_usd') or 0.0,
            'duration_ms': last_result.get('duration_ms') or 0,
            'num_turns': last_result.get('num_turns') or 0,
            'input_tokens': usage.get('input_tokens') or 0,
            'output_tokens': usage.get('output_tokens') or 0,
            'cache_read_tokens': usage.get('cache_read_input_tokens') or 0,
            'stop_reason': last_result.get('stop_reason'),
        }
    except (OSError, IOError) as e:
        logger.debug(f"[subagent_reader] transcript inacessivel: {e}")
        return default


def _resolve_transcript_path(
    session_id: str,
    agent_id: str,
    directory: Optional[str] = None,
) -> Optional[str]:
    """Resolve caminho do JSONL do subagente em ~/.claude/projects/.../subagents/."""
    base = Path(directory) if directory else Path.home() / '.claude' / 'projects'
    if directory is None:
        # Busca cross-project (SDK default behavior)
        for proj_dir in base.iterdir():
            if not proj_dir.is_dir():
                continue
            sub_dir = proj_dir / session_id / 'subagents'
            if sub_dir.exists():
                for f in sub_dir.rglob(f'{agent_id}*.jsonl'):
                    return str(f)
    return None


def _summarize_tool_call(
    block: dict,
    result_content: Optional[str] = None,
    max_chars: int = 500,
    include_pii: bool = False,
) -> dict:
    """Condensa tool_use + tool_result em entrada para SubagentSummary.tools_used."""
    name = block.get('name', 'unknown')
    input_str = json.dumps(block.get('input', {}), ensure_ascii=False)[:max_chars]
    result_str = (result_content or '')[:max_chars]

    if not include_pii:
        input_str = mask_pii(input_str)
        result_str = mask_pii(result_str)

    return {
        'name': name,
        'args_summary': input_str,
        'result_summary': result_str,
        'tool_use_id': block.get('id', ''),
    }


def get_subagent_summary(
    session_id: str,
    agent_id: str,
    agent_type: str = '',
    directory: Optional[str] = None,
    include_pii: bool = False,
    max_tool_chars: int = 500,
) -> SubagentSummary:
    """
    Le mensagens do transcript + metadata do ResultMessage e monta summary.

    Se o subagente nao for encontrado, retorna SubagentSummary com status='error'.
    """
    try:
        messages = list(get_subagent_messages(session_id, agent_id,
                                               directory=directory))
    except Exception as e:
        logger.debug(f"[subagent_reader] get_subagent_messages falhou: {e}")
        messages = []

    if not messages:
        return SubagentSummary(
            agent_id=agent_id, agent_type=agent_type, status='error',
            started_at=None, ended_at=None, duration_ms=None,
        )

    # Mapeia tool_use_id -> conteudo do tool_result
    tool_results: dict[str, str] = {}
    for msg in messages:
        content = getattr(msg, 'content', None)
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'tool_result':
                    tid = block.get('tool_use_id', '')
                    res = block.get('content', '')
                    if isinstance(res, list):
                        res = ' '.join(
                            b.get('text', '') for b in res
                            if isinstance(b, dict)
                        )
                    tool_results[tid] = str(res)

    # Extrai tool_calls e findings_text em ordem cronologica
    tools_used: list[dict] = []
    findings_parts: list[str] = []

    for msg in messages:
        content = getattr(msg, 'content', None)
        if not isinstance(content, list):
            if isinstance(content, str):
                findings_parts.append(content)
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get('type')
            if btype == 'tool_use':
                tid = block.get('id', '')
                tools_used.append(_summarize_tool_call(
                    block,
                    result_content=tool_results.get(tid),
                    max_chars=max_tool_chars,
                    include_pii=include_pii,
                ))
            elif btype == 'text':
                findings_parts.append(block.get('text', ''))

    findings_text = '\n'.join(findings_parts).strip()
    if not include_pii:
        findings_text = mask_pii(findings_text)

    # Metadata do ResultMessage
    transcript_path = _resolve_transcript_path(session_id, agent_id, directory)
    meta = _read_result_metadata(transcript_path)

    started_at = getattr(messages[0], 'timestamp', None)
    ended_at = getattr(messages[-1], 'timestamp', None)

    return SubagentSummary(
        agent_id=agent_id,
        agent_type=agent_type,
        status='done',
        started_at=started_at,
        ended_at=ended_at,
        duration_ms=meta['duration_ms'] or None,
        tools_used=tools_used,
        cost_usd=meta['cost_usd'],
        input_tokens=meta['input_tokens'],
        output_tokens=meta['output_tokens'],
        cache_read_tokens=meta['cache_read_tokens'],
        num_turns=meta['num_turns'],
        findings_text=findings_text,
        stop_reason=meta['stop_reason'],
    )


def get_session_subagents_summary(
    session_id: str,
    directory: Optional[str] = None,
    include_pii: bool = False,
) -> list[SubagentSummary]:
    """Batch helper — summary de todos os subagentes da sessao."""
    agent_ids = list_session_subagents(session_id, directory=directory)
    return [
        get_subagent_summary(session_id, aid, directory=directory,
                              include_pii=include_pii)
        for aid in agent_ids
    ]


def get_subagent_findings(
    session_id: str,
    agent_type: str,
    directory: Optional[str] = None,
) -> Optional[str]:
    """
    Retorna findings_text do subagente mais recente do agent_type na sessao.

    Usado pelo parent como alternativa canonica ao /tmp/subagent-findings/.
    Retorna None se SDK nao encontrou nada (caller deve fallback para /tmp/).
    """
    summaries = get_session_subagents_summary(session_id, directory=directory,
                                               include_pii=True)
    matching = [s for s in summaries if s.agent_type == agent_type
                and s.status == 'done']
    if not matching:
        return None
    # Mais recente primeiro (ended_at desc)
    matching.sort(key=lambda s: s.ended_at or agora_brasil_naive(), reverse=True)
    return matching[0].findings_text
```

- [ ] **Step 4: Rodar testes e verificar que passam**

Run: `pytest tests/agente/sdk/test_subagent_reader.py -v`
Expected: `6 passed` (requer pii_masker — Task 1.2 — mas import sera tardio se pii_masker ja existe; se falhar por pii_masker, executar Task 1.2 primeiro e re-rodar)

- [ ] **Step 5: Commit**

```bash
git add app/agente/sdk/subagent_reader.py tests/agente/sdk/test_subagent_reader.py
git commit -m "$(cat <<'EOF'
feat(agente): subagent_reader wrapper do SDK 0.1.60

Modulo base que encapsula list_subagents + get_subagent_messages
para consumidores (endpoint admin, UI, cost tracking, memory mining,
validacao). Extrai tools em ordem cronologica, parseia ResultMessage
para cost/tokens/duration e aplica mascaramento PII por default.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 1.2: Modulo `pii_masker.py`

**Files:**
- Create: `app/agente/utils/pii_masker.py`
- Test: `tests/agente/utils/test_pii_masker.py`

- [ ] **Step 1: Criar teste**

Criar `tests/agente/utils/test_pii_masker.py`:

```python
"""Testes do mascaramento PII brasileiro (CPF, CNPJ, email)."""
import pytest
from app.agente.utils.pii_masker import mask_pii


def test_mask_cpf_formatado():
    """CPF formatado e mascarado preservando DV."""
    assert mask_pii('CPF: 123.456.789-00') == 'CPF: ***.***.***-00'


def test_mask_cnpj_formatado():
    """CNPJ formatado e mascarado preservando filial e DV."""
    assert mask_pii('CNPJ 12.345.678/0001-90') == 'CNPJ **.***.***/0001-90'


def test_mask_email_preserva_dominio():
    """Email mascara local-part mas preserva dominio."""
    assert mask_pii('contato: joao.silva@nacom.com.br') \
        == 'contato: ***@nacom.com.br'


def test_mask_multiplos_no_mesmo_texto():
    """Mascara multiplos tipos de PII no mesmo texto."""
    texto = 'Cliente 12.345.678/0001-90 (joao@x.com.br) CPF 987.654.321-11'
    resultado = mask_pii(texto)
    assert '12.345.678/0001-90' not in resultado
    assert 'joao@x.com.br' not in resultado
    assert '987.654.321-11' not in resultado
    assert '0001-90' in resultado  # preserva filial
    assert '-11' in resultado      # preserva DV


def test_mask_preserva_texto_sem_pii():
    """Texto sem PII nao e alterado."""
    texto = 'Pedido 123 tem 5 caixas'
    assert mask_pii(texto) == texto


def test_mask_cpf_sem_formatacao_11_digitos():
    """CPF sem pontuacao (11 digitos consecutivos) e mascarado."""
    # Apenas em contextos claros — conservador para evitar falsos positivos
    assert '***********' in mask_pii('CPF 12345678900 registrado')


def test_mask_cnpj_sem_formatacao_14_digitos():
    """CNPJ sem pontuacao (14 digitos consecutivos) e mascarado."""
    assert '**************' in mask_pii('CNPJ 12345678000190')


def test_mask_string_vazia():
    """String vazia retorna vazia."""
    assert mask_pii('') == ''


def test_mask_none_retorna_vazia():
    """None retorna string vazia (defensive)."""
    assert mask_pii(None) == ''
```

- [ ] **Step 2: Rodar teste (falha)**

Run: `pytest tests/agente/utils/test_pii_masker.py -v`
Expected: `ModuleNotFoundError: No module named 'app.agente.utils.pii_masker'`

- [ ] **Step 3: Criar `app/agente/utils/__init__.py` se nao existir e `pii_masker.py`**

Verificar se `app/agente/utils/` ja existe:
```bash
ls app/agente/utils/ 2>/dev/null || mkdir -p app/agente/utils
touch app/agente/utils/__init__.py
```

Criar `app/agente/utils/pii_masker.py`:

```python
"""
Mascaramento de dados sensiveis brasileiros (CPF, CNPJ, email).

Aplicado por default em todos os summaries de subagente visiveis a
usuarios nao-administradores. Preserva DV/filial/dominio para manter
contexto minimo debuggavel sem expor PII completo.

Regex conservadora — em duvida, NAO mascara (falsos negativos sao
preferiveis a falsos positivos que quebram contexto legitimo).
"""
import re
from typing import Optional

# CPF formatado: 123.456.789-00 → ***.***.***-00
_RE_CPF_FMT = re.compile(r'\d{3}\.\d{3}\.\d{3}-(\d{2})')

# CNPJ formatado: 12.345.678/0001-90 → **.***.***/0001-90
_RE_CNPJ_FMT = re.compile(r'\d{2}\.\d{3}\.\d{3}/(\d{4})-(\d{2})')

# Email: joao@x.com.br → ***@x.com.br
_RE_EMAIL = re.compile(r'[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')

# CPF sem pontuacao: 11 digitos consecutivos (word boundary)
_RE_CPF_RAW = re.compile(r'\b\d{11}\b')

# CNPJ sem pontuacao: 14 digitos consecutivos (word boundary)
_RE_CNPJ_RAW = re.compile(r'\b\d{14}\b')


def mask_pii(text: Optional[str]) -> str:
    """Aplica mascaramento em texto. Retorna '' se text for None."""
    if not text:
        return ''

    # Ordem importa: CNPJ formatado antes de CPF formatado (substring)
    # E CNPJ raw antes de CPF raw (14 dig contem 11)
    text = _RE_CNPJ_FMT.sub(r'**.***.***/\1-\2', text)
    text = _RE_CPF_FMT.sub(r'***.***.***-\1', text)
    text = _RE_EMAIL.sub(r'***@\1', text)
    text = _RE_CNPJ_RAW.sub('**************', text)
    text = _RE_CPF_RAW.sub('***********', text)

    return text
```

- [ ] **Step 4: Rodar teste (passa)**

Run: `pytest tests/agente/utils/test_pii_masker.py -v`
Expected: `9 passed`

- [ ] **Step 5: Rodar teste Task 1.1 (agora deve passar totalmente)**

Run: `pytest tests/agente/sdk/test_subagent_reader.py -v`
Expected: `6 passed`

- [ ] **Step 6: Commit**

```bash
git add app/agente/utils/__init__.py app/agente/utils/pii_masker.py tests/agente/utils/test_pii_masker.py
git commit -m "$(cat <<'EOF'
feat(agente): pii_masker — mascaramento CPF/CNPJ/email

Util compartilhado para sanitizar dados sensiveis em summaries de
subagente visiveis a usuarios nao-administradores. Regex conservadora
preserva DV/filial/dominio para debug minimo.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 1.3: Feature flags das 5 features

**Files:**
- Modify: `app/agente/config/feature_flags.py`

- [ ] **Step 1: Editar `feature_flags.py` para adicionar bloco novo ao final**

Localizar o final do arquivo e adicionar:

```python
# ====================================================================
# Features SDK 0.1.60 — Subagent Transparency (2026-04-16)
# ====================================================================
# Todas as 5 flags default=true — ativas imediatamente para rollout.
# Rollback: setar AGENT_SUBAGENT_*=false + restart (sem redeploy).

# #1 Endpoint admin debug forense — drill-down em subagentes de qualquer sessao
USE_SUBAGENT_DEBUG_ENDPOINT = os.getenv(
    "AGENT_SUBAGENT_DEBUG_ENDPOINT", "true"
).lower() == "true"

# #3 Cost tracking granular por subagente — persiste em AgentSession.data JSONB
USE_SUBAGENT_COST_GRANULAR = os.getenv(
    "AGENT_SUBAGENT_COST_GRANULAR", "true"
).lower() == "true"

# #5 Memory mining cross-subagent — pattern_analyzer inclui findings dos especialistas
USE_SUBAGENT_MEMORY_MINING = os.getenv(
    "AGENT_SUBAGENT_MEMORY_MINING", "true"
).lower() == "true"

# #6 UI linha inline expansivel no chat
USE_SUBAGENT_UI = os.getenv("AGENT_SUBAGENT_UI", "true").lower() == "true"

# #4 Validacao anti-alucinacao async (Haiku 4.5 score 0-100)
USE_SUBAGENT_VALIDATION = os.getenv(
    "AGENT_SUBAGENT_VALIDATION", "true"
).lower() == "true"

# #4 Threshold de flag (score abaixo do qual dispara warning)
SUBAGENT_VALIDATION_THRESHOLD = int(
    os.getenv("AGENT_SUBAGENT_VALIDATION_THRESHOLD", "70")
)

# #6 Admin override — permite admin ver PII raw em UI
SUBAGENT_UI_RAW_FOR_ADMIN = os.getenv(
    "AGENT_SUBAGENT_UI_RAW_FOR_ADMIN", "true"
).lower() == "true"
```

- [ ] **Step 2: Verificar import**

```bash
source .venv/bin/activate
python -c "from app.agente.config.feature_flags import USE_SUBAGENT_DEBUG_ENDPOINT, USE_SUBAGENT_COST_GRANULAR, USE_SUBAGENT_MEMORY_MINING, USE_SUBAGENT_UI, USE_SUBAGENT_VALIDATION, SUBAGENT_VALIDATION_THRESHOLD; print('OK', SUBAGENT_VALIDATION_THRESHOLD)"
```

Expected: `OK 70`

- [ ] **Step 3: Commit**

```bash
git add app/agente/config/feature_flags.py
git commit -m "feat(agente): 7 flags das features SDK 0.1.60 (default=true)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 1.4: Endpoint admin #1 (debug forense)

**Files:**
- Create: `app/agente/routes/admin_subagents.py`
- Modify: `app/agente/routes/__init__.py`
- Test: `tests/agente/routes/test_admin_subagents.py`

- [ ] **Step 1: Criar teste**

Criar `tests/agente/routes/test_admin_subagents.py`:

```python
"""Testes do endpoint admin de debug de subagentes (#1)."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def admin_user():
    user = MagicMock()
    user.is_authenticated = True
    user.perfil = 'administrador'
    user.id = 1
    return user


@pytest.fixture
def normal_user():
    user = MagicMock()
    user.is_authenticated = True
    user.perfil = 'vendedor'
    user.id = 2
    return user


def test_list_subagents_admin_returns_200(client, admin_user):
    """GET /api/admin/sessions/<id>/subagents retorna lista para admin."""
    from app.agente.sdk.subagent_reader import SubagentSummary
    from datetime import datetime

    summary = SubagentSummary(
        agent_id='a1', agent_type='analista-carteira', status='done',
        started_at=datetime(2026, 4, 16), ended_at=datetime(2026, 4, 16),
        duration_ms=8234, cost_usd=0.012, num_turns=4,
        tools_used=[{'name': 'query_sql', 'args_summary': 'SELECT',
                     'result_summary': '24 rows', 'tool_use_id': 't1'}]
    )

    with patch('flask_login.utils._get_user', return_value=admin_user), \
         patch('app.agente.routes.admin_subagents.get_session_subagents_summary',
               return_value=[summary]):
        resp = client.get('/agente/api/admin/sessions/sess-1/subagents')

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert len(data['subagents']) == 1
    assert data['subagents'][0]['agent_type'] == 'analista-carteira'
    assert data['subagents'][0]['cost_usd'] == 0.012  # admin ve custo


def test_list_subagents_non_admin_returns_403(client, normal_user):
    """Non-admin recebe 403."""
    with patch('flask_login.utils._get_user', return_value=normal_user):
        resp = client.get('/agente/api/admin/sessions/sess-1/subagents')

    assert resp.status_code == 403


def test_get_subagent_detail_admin_returns_raw(client, admin_user):
    """GET detail retorna summary com PII raw (include_pii=True) para admin."""
    from app.agente.sdk.subagent_reader import SubagentSummary
    from datetime import datetime

    summary = SubagentSummary(
        agent_id='a1', agent_type='analista-carteira', status='done',
        started_at=datetime(2026, 4, 16), ended_at=datetime(2026, 4, 16),
        duration_ms=100,
        findings_text='Cliente 12.345.678/0001-90 tem 5 pedidos',
    )

    with patch('flask_login.utils._get_user', return_value=admin_user), \
         patch('app.agente.routes.admin_subagents.get_subagent_summary',
               return_value=summary) as mock_get:
        resp = client.get('/agente/api/admin/sessions/sess-1/subagents/a1')

    assert resp.status_code == 200
    # admin chama com include_pii=True
    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert kwargs.get('include_pii') is True


def test_flag_off_returns_404(client, admin_user):
    """Quando USE_SUBAGENT_DEBUG_ENDPOINT=false, rota retorna 404."""
    with patch('flask_login.utils._get_user', return_value=admin_user), \
         patch('app.agente.routes.admin_subagents.USE_SUBAGENT_DEBUG_ENDPOINT',
               False):
        resp = client.get('/agente/api/admin/sessions/sess-1/subagents')

    assert resp.status_code == 404
```

- [ ] **Step 2: Rodar teste (falha por ModuleNotFoundError)**

Run: `pytest tests/agente/routes/test_admin_subagents.py -v`
Expected: `ModuleNotFoundError` ou `ImportError`

- [ ] **Step 3: Criar `app/agente/routes/admin_subagents.py`**

```python
"""
Endpoint admin de debug forense de subagentes (#1, SDK 0.1.60).

Permite admin investigar respostas do agente sem re-executar a sessao:
lista todos os subagentes de uma sessao, mostra tool_calls em ordem
cronologica com args/results raw (sem mascaramento PII), custo e duracao.

Pattern de auth: @login_required + inline check perfil='administrador' → 403.
Flag: USE_SUBAGENT_DEBUG_ENDPOINT (default true).
"""
import logging

from flask import abort, jsonify
from flask_login import current_user, login_required

from app.agente.config.feature_flags import USE_SUBAGENT_DEBUG_ENDPOINT
from app.agente.routes import agente_bp
from app.agente.sdk.subagent_reader import (
    get_session_subagents_summary,
    get_subagent_summary,
)

logger = logging.getLogger('sistema_fretes')


def _require_admin():
    """Aborta 403 se nao for admin. Usar como guard inicial nas rotas."""
    if current_user.perfil != 'administrador':
        abort(403, description='Acesso restrito a administradores')


@agente_bp.route(
    '/api/admin/sessions/<session_id>/subagents',
    methods=['GET'],
)
@login_required
def api_admin_list_subagents(session_id: str):
    """Lista subagentes de uma sessao com metadata resumida."""
    if not USE_SUBAGENT_DEBUG_ENDPOINT:
        abort(404)
    _require_admin()

    summaries = get_session_subagents_summary(session_id, include_pii=True)

    return jsonify({
        'success': True,
        'session_id': session_id,
        'count': len(summaries),
        'subagents': [s.to_dict(include_cost=True) for s in summaries],
    })


@agente_bp.route(
    '/api/admin/sessions/<session_id>/subagents/<agent_id>',
    methods=['GET'],
)
@login_required
def api_admin_subagent_detail(session_id: str, agent_id: str):
    """Detalhe completo de um subagente — tools, findings, cost, tokens."""
    if not USE_SUBAGENT_DEBUG_ENDPOINT:
        abort(404)
    _require_admin()

    summary = get_subagent_summary(
        session_id, agent_id, include_pii=True, max_tool_chars=2000
    )

    if summary.status == 'error':
        return jsonify({
            'success': False,
            'error': f'Subagent {agent_id} nao encontrado na sessao {session_id}',
        }), 404

    return jsonify({
        'success': True,
        'session_id': session_id,
        'subagent': summary.to_dict(include_cost=True),
    })


@agente_bp.route(
    '/api/admin/sessions/<session_id>/subagents/<agent_id>/messages',
    methods=['GET'],
)
@login_required
def api_admin_subagent_messages(session_id: str, agent_id: str):
    """Mensagens brutas do JSONL (para debug profundo)."""
    if not USE_SUBAGENT_DEBUG_ENDPOINT:
        abort(404)
    _require_admin()

    from claude_agent_sdk import get_subagent_messages

    try:
        messages = list(get_subagent_messages(session_id, agent_id))
    except Exception as e:
        logger.error(f"[admin_subagents] get_subagent_messages falhou: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({
        'success': True,
        'session_id': session_id,
        'agent_id': agent_id,
        'count': len(messages),
        'messages': [
            {
                'role': getattr(m, 'role', None),
                'content': getattr(m, 'content', None),
                'timestamp': (
                    getattr(m, 'timestamp', None).isoformat()
                    if getattr(m, 'timestamp', None) else None
                ),
            }
            for m in messages
        ],
    })
```

- [ ] **Step 4: Registrar em `routes/__init__.py`**

Ler `app/agente/routes/__init__.py` para achar a linha onde os sub-modulos sao importados e adicionar:

```python
from . import admin_subagents  # noqa: F401 — registra rotas admin de subagentes
```

(Adicionar depois da linha que importa `admin_learning`.)

- [ ] **Step 5: Rodar teste (passa)**

Run: `pytest tests/agente/routes/test_admin_subagents.py -v`
Expected: `4 passed`

- [ ] **Step 6: Commit**

```bash
git add app/agente/routes/admin_subagents.py app/agente/routes/__init__.py tests/agente/routes/test_admin_subagents.py
git commit -m "$(cat <<'EOF'
feat(agente): endpoint admin debug forense de subagentes (#1)

3 rotas admin-only (login_required + perfil=administrador):
- GET /api/admin/sessions/<id>/subagents — lista
- GET /api/admin/sessions/<id>/subagents/<aid> — detalhe completo
- GET /api/admin/sessions/<id>/subagents/<aid>/messages — raw JSONL

Permite investigar respostas do agente sem re-executar. Flag
USE_SUBAGENT_DEBUG_ENDPOINT controla disponibilidade (default true).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 1.5: Migration do indice GIN (#3)

**Files:**
- Create: `scripts/migrations/agent_session_subagent_costs_idx.py`
- Create: `scripts/migrations/agent_session_subagent_costs_idx.sql`

- [ ] **Step 1: Criar arquivo SQL idempotente**

Criar `scripts/migrations/agent_session_subagent_costs_idx.sql`:

```sql
-- Migration: indice GIN para consultas agregadas em subagent_costs
-- Data: 2026-04-16
-- Spec: docs/superpowers/specs/2026-04-16-agent-sdk-0160-features-design.md #3

CREATE INDEX IF NOT EXISTS idx_agent_sessions_subagent_costs
ON agent_sessions USING GIN ((data -> 'subagent_costs'));

COMMENT ON INDEX idx_agent_sessions_subagent_costs IS
'Suporta queries agregadas "top subagentes por custo no mes" via jsonb_array_elements(data->subagent_costs->entries)';
```

- [ ] **Step 2: Criar Python com verificacao before/after**

Criar `scripts/migrations/agent_session_subagent_costs_idx.py`:

```python
"""
Migration: indice GIN em agent_sessions.data->subagent_costs (feature #3).

Permite queries agregadas de custo por subagente sem full scan. Zero
impacto em escritas (INSERT/UPDATE nao usam o indice — GIN sob JSONB
so e consultado em path queries).

Usage:
    python scripts/migrations/agent_session_subagent_costs_idx.py
"""
import sys

from sqlalchemy import text

from app import create_app, db


def verificar_indice() -> bool:
    """Retorna True se o indice ja existe."""
    result = db.session.execute(text("""
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'agent_sessions'
          AND indexname = 'idx_agent_sessions_subagent_costs'
    """)).scalar()
    return bool(result)


def main() -> int:
    app = create_app()
    with app.app_context():
        if verificar_indice():
            print('[SKIP] indice idx_agent_sessions_subagent_costs ja existe.')
            return 0

        print('[INFO] Criando indice GIN idx_agent_sessions_subagent_costs...')
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_agent_sessions_subagent_costs
            ON agent_sessions USING GIN ((data -> 'subagent_costs'))
        """))
        db.session.execute(text("""
            COMMENT ON INDEX idx_agent_sessions_subagent_costs IS
            'Suporta queries agregadas top subagentes por custo via jsonb_array_elements'
        """))
        db.session.commit()

        if verificar_indice():
            print('[OK] Indice criado com sucesso.')
            return 0
        print('[ERRO] Indice nao aparece em pg_indexes apos commit.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 3: Executar migration em dev local**

```bash
source .venv/bin/activate
python scripts/migrations/agent_session_subagent_costs_idx.py
```

Expected: `[OK] Indice criado com sucesso.` ou `[SKIP] indice ... ja existe.`

- [ ] **Step 4: Commit**

```bash
git add scripts/migrations/agent_session_subagent_costs_idx.py scripts/migrations/agent_session_subagent_costs_idx.sql
git commit -m "$(cat <<'EOF'
feat(migration): indice GIN para subagent_costs em agent_sessions

Suporta queries agregadas de top subagentes por custo sem full scan.
Zero impacto em escritas. Aplicar via:
- Python: python scripts/migrations/agent_session_subagent_costs_idx.py
- SQL Render Shell: scripts/migrations/agent_session_subagent_costs_idx.sql

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 1.6: Cost granular #3 (extensao hooks + models + insights)

**Files:**
- Modify: `app/agente/sdk/hooks.py` (linhas 415-497)
- Modify: `app/agente/models.py`
- Modify: `app/agente/services/insights_service.py`
- Test: `tests/agente/sdk/test_hooks_subagent_cost.py`
- Test: `tests/agente/models/test_top_subagents_by_cost.py`

- [ ] **Step 1: Criar teste do hook extendido**

Criar `tests/agente/sdk/test_hooks_subagent_cost.py`:

```python
"""Testes da extensao do SubagentStop hook para persistir cost granular (#3)."""
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_transcript(tmp_path, cost=0.012, input_t=1200, output_t=400):
    """Helper: cria JSONL com assistant usage + result."""
    p = tmp_path / 'transcript.jsonl'
    with open(p, 'w') as f:
        # assistant message with usage
        f.write(json.dumps({
            'type': 'assistant',
            'message': {
                'usage': {
                    'input_tokens': input_t,
                    'output_tokens': output_t,
                    'cache_read_input_tokens': 100,
                }
            }
        }) + '\n')
        # result message
        f.write(json.dumps({
            'type': 'result',
            'total_cost_usd': cost,
            'duration_ms': 8234,
            'num_turns': 4,
            'usage': {
                'input_tokens': input_t,
                'output_tokens': output_t,
                'cache_read_input_tokens': 100,
            },
            'stop_reason': 'end_turn',
        }) + '\n')
    return str(p)


def test_subagent_stop_persists_cost_to_session_data(tmp_path, app):
    """SubagentStop hook persiste entrada em AgentSession.data['subagent_costs']."""
    from app.agente.models import AgentSession
    from app.agente.sdk.hooks import build_hooks
    from app import db

    with app.app_context():
        sess = AgentSession(
            session_id='sess-test-1', user_id=1, title='test', data={}
        )
        db.session.add(sess)
        db.session.commit()

        transcript = _make_transcript(tmp_path)
        hooks = build_hooks(user_id=1, event_queue=None, done_event=None)

        # Localizar o handler do SubagentStop
        from claude_agent_sdk.types import HookEvent
        stop_matchers = [m for ev, matchers in hooks.items()
                         if ev == 'SubagentStop' for m in matchers]
        assert stop_matchers, 'SubagentStop hook nao registrado'

        import asyncio
        handler = stop_matchers[0].hooks[0]
        asyncio.run(handler({
            'agent_id': 'aid-1',
            'agent_type': 'analista-carteira',
            'agent_transcript_path': transcript,
            'session_id': 'sess-test-1',
        }, None, MagicMock()))

        db.session.refresh(sess)
        assert 'subagent_costs' in sess.data
        entries = sess.data['subagent_costs']['entries']
        assert len(entries) == 1
        assert entries[0]['agent_type'] == 'analista-carteira'
        assert entries[0]['cost_usd'] == 0.012
        assert entries[0]['input_tokens'] == 1200
        assert entries[0]['output_tokens'] == 400


def test_subagent_stop_multiple_subagents_append_entries(tmp_path, app):
    """Dois subagentes na mesma sessao → data['subagent_costs']['entries'] tem 2."""
    from app.agente.models import AgentSession
    from app.agente.sdk.hooks import build_hooks
    from app import db
    from claude_agent_sdk.types import HookEvent

    with app.app_context():
        sess = AgentSession(
            session_id='sess-test-2', user_id=1, title='test', data={}
        )
        db.session.add(sess)
        db.session.commit()

        hooks = build_hooks(user_id=1, event_queue=None, done_event=None)
        import asyncio
        handler = [m for ev, matchers in hooks.items()
                   if ev == 'SubagentStop' for m in matchers][0].hooks[0]

        for i, agent_type in enumerate(['analista-carteira', 'raio-x-pedido']):
            transcript = _make_transcript(tmp_path / f'{i}.jsonl', cost=0.01 + i * 0.005)
            asyncio.run(handler({
                'agent_id': f'aid-{i}',
                'agent_type': agent_type,
                'agent_transcript_path': transcript,
                'session_id': 'sess-test-2',
            }, None, MagicMock()))

        db.session.refresh(sess)
        entries = sess.data['subagent_costs']['entries']
        assert len(entries) == 2
        assert {e['agent_type'] for e in entries} == {'analista-carteira', 'raio-x-pedido'}


def test_subagent_stop_flag_off_does_not_persist(tmp_path, app):
    """Quando USE_SUBAGENT_COST_GRANULAR=false, nao persiste em data."""
    from app.agente.models import AgentSession
    from app.agente.sdk.hooks import build_hooks
    from app import db

    with app.app_context():
        sess = AgentSession(
            session_id='sess-test-3', user_id=1, title='test', data={}
        )
        db.session.add(sess)
        db.session.commit()

        with patch('app.agente.sdk.hooks.USE_SUBAGENT_COST_GRANULAR', False):
            hooks = build_hooks(user_id=1, event_queue=None, done_event=None)
            import asyncio
            handler = [m for ev, matchers in hooks.items()
                       if ev == 'SubagentStop' for m in matchers][0].hooks[0]
            asyncio.run(handler({
                'agent_id': 'aid-x',
                'agent_type': 'x',
                'agent_transcript_path': _make_transcript(tmp_path),
                'session_id': 'sess-test-3',
            }, None, MagicMock()))

        db.session.refresh(sess)
        assert sess.data.get('subagent_costs') is None
```

- [ ] **Step 2: Rodar teste (falha — funcionalidade ainda nao existe)**

Run: `pytest tests/agente/sdk/test_hooks_subagent_cost.py -v`
Expected: `AssertionError` — as entries nao existem em `sess.data`

- [ ] **Step 3: Modificar `hooks.py` para persistir em `AgentSession.data`**

Localizar o `_subagent_stop_hook` (linhas 415-497) e estender. Apos o bloco que registra no `cost_tracker` (linha 492), ANTES do `return {}` final, adicionar:

```python
            # #3 Cost granular — persiste em AgentSession.data (JSONB)
            from ..config.feature_flags import USE_SUBAGENT_COST_GRANULAR
            if USE_SUBAGENT_COST_GRANULAR and session_id and cost_usd is not None:
                try:
                    from app import db
                    from ..models import AgentSession
                    from sqlalchemy.orm.attributes import flag_modified
                    from app.utils.timezone import agora_brasil_naive

                    # Parsear tokens do transcript (ResultMessage.usage)
                    input_tokens = 0
                    output_tokens = 0
                    cache_read = 0
                    if transcript_path and last_result:
                        usage = last_result.get('usage', {}) or {}
                        input_tokens = usage.get('input_tokens') or 0
                        output_tokens = usage.get('output_tokens') or 0
                        cache_read = usage.get('cache_read_input_tokens') or 0

                    sess = AgentSession.query.filter_by(
                        session_id=session_id
                    ).first()
                    if sess is not None:
                        data = sess.data or {}
                        bucket = data.setdefault('subagent_costs', {
                            'version': 1, 'entries': []
                        })
                        bucket['entries'].append({
                            'agent_id': agent_id,
                            'agent_type': agent_type,
                            'cost_usd': float(cost_usd),
                            'input_tokens': int(input_tokens),
                            'output_tokens': int(output_tokens),
                            'cache_read_tokens': int(cache_read),
                            'duration_ms': int(duration_ms or 0),
                            'num_turns': int(num_turns or 0),
                            'stop_reason': stop_reason or 'end_turn',
                            'started_at': None,  # populado em #6 via emit
                            'ended_at': agora_brasil_naive().isoformat(),
                        })
                        sess.data = data
                        flag_modified(sess, 'data')
                        db.session.commit()
                        logger.debug(
                            f"[HOOK:SubagentStop] cost granular persistido "
                            f"em sess.data (agent_type={agent_type})"
                        )
                except Exception as granular_err:
                    logger.debug(
                        f"[HOOK:SubagentStop] cost granular falhou: {granular_err}"
                    )
```

**Observacao**: `session_id` ja existe no escopo como `hook_input.get('session_id', '')` — verificar se esta sendo extraido; se nao, adicionar extracao logo apos linha 425:

```python
            session_id = hook_input.get('session_id', '')
```

- [ ] **Step 4: Rodar teste (passa)**

Run: `pytest tests/agente/sdk/test_hooks_subagent_cost.py -v`
Expected: `3 passed`

- [ ] **Step 5: Adicionar classmethod em `AgentSession` (`models.py`)**

Ler `app/agente/models.py` para achar a classe `AgentSession` e adicionar ao final dela:

```python
    @classmethod
    def top_subagents_by_cost(cls, days: int = 30, limit: int = 10) -> list[dict]:
        """
        Top N subagentes por custo acumulado nos ultimos `days` dias.

        Usa o indice GIN em data->subagent_costs. Retorna:
        [{'agent_type': str, 'total_cost': float, 'invocacoes': int}, ...]
        """
        from sqlalchemy import text
        from app import db

        q = text("""
            SELECT
                e->>'agent_type' AS agent_type,
                SUM((e->>'cost_usd')::numeric) AS total_cost,
                COUNT(*) AS invocacoes
            FROM agent_sessions s,
                 jsonb_array_elements(s.data->'subagent_costs'->'entries') e
            WHERE s.created_at > now() - make_interval(days => :days)
            GROUP BY e->>'agent_type'
            ORDER BY total_cost DESC
            LIMIT :limit
        """)
        rows = db.session.execute(q, {'days': days, 'limit': limit}).fetchall()
        return [
            {
                'agent_type': r.agent_type,
                'total_cost': float(r.total_cost or 0),
                'invocacoes': int(r.invocacoes or 0),
            }
            for r in rows
        ]
```

- [ ] **Step 6: Criar teste do classmethod**

Criar `tests/agente/models/test_top_subagents_by_cost.py`:

```python
"""Testa query agregada top_subagents_by_cost."""
import pytest
from datetime import datetime, timedelta


def test_top_subagents_by_cost_aggregates_correctly(app):
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        s1 = AgentSession(
            session_id='s1', user_id=1, title='t', data={
                'subagent_costs': {'version': 1, 'entries': [
                    {'agent_type': 'analista-carteira', 'cost_usd': 0.012},
                    {'agent_type': 'raio-x-pedido', 'cost_usd': 0.005},
                ]}
            }
        )
        s2 = AgentSession(
            session_id='s2', user_id=1, title='t', data={
                'subagent_costs': {'version': 1, 'entries': [
                    {'agent_type': 'analista-carteira', 'cost_usd': 0.008},
                ]}
            }
        )
        db.session.add_all([s1, s2])
        db.session.commit()

        top = AgentSession.top_subagents_by_cost(days=30, limit=5)

        assert len(top) == 2
        assert top[0]['agent_type'] == 'analista-carteira'
        assert abs(top[0]['total_cost'] - 0.020) < 1e-6
        assert top[0]['invocacoes'] == 2
        assert top[1]['agent_type'] == 'raio-x-pedido'


def test_top_subagents_by_cost_respects_limit(app):
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        sess = AgentSession(session_id='s3', user_id=1, title='t', data={
            'subagent_costs': {'version': 1, 'entries': [
                {'agent_type': f'agent-{i}', 'cost_usd': 0.001 * (i + 1)}
                for i in range(5)
            ]}
        })
        db.session.add(sess)
        db.session.commit()

        top = AgentSession.top_subagents_by_cost(days=30, limit=3)
        assert len(top) == 3
```

- [ ] **Step 7: Rodar teste (passa)**

Run: `pytest tests/agente/models/test_top_subagents_by_cost.py -v`
Expected: `2 passed`

- [ ] **Step 8: Adicionar secao no `insights_service.py`**

Ler `app/agente/services/insights_service.py` e localizar o metodo principal que agrega insights (ex: `gerar_insights_sessao` ou similar). Adicionar uma nova secao/bloco:

```python
    def _get_subagent_cost_section(self, days: int = 30) -> dict:
        """Top subagentes por custo nos ultimos N dias (feature #3)."""
        from app.agente.config.feature_flags import USE_SUBAGENT_COST_GRANULAR
        if not USE_SUBAGENT_COST_GRANULAR:
            return {}

        from app.agente.models import AgentSession
        try:
            top = AgentSession.top_subagents_by_cost(days=days, limit=5)
            total = sum(t['total_cost'] for t in top)
            return {
                'top_subagents': top,
                'total_cost_30d': round(total, 4),
                'period_days': days,
            }
        except Exception as e:
            logger.warning(f"[insights] subagent_cost_section falhou: {e}")
            return {}
```

E no metodo principal que retorna o dict de insights, adicionar:

```python
        result['subagent_costs'] = self._get_subagent_cost_section()
```

**Nota**: a localizacao exata depende da estrutura atual do `insights_service.py`. Se houver ambiguidade, consultar o arquivo e adaptar ao padrao ja existente (procurar por `_get_*_section` similares).

- [ ] **Step 9: Commit**

```bash
git add app/agente/sdk/hooks.py app/agente/models.py app/agente/services/insights_service.py tests/agente/sdk/test_hooks_subagent_cost.py tests/agente/models/test_top_subagents_by_cost.py
git commit -m "$(cat <<'EOF'
feat(agente): cost tracking granular por subagente (#3)

- hooks.py:SubagentStop persiste entry em AgentSession.data['subagent_costs']
  (JSONB versionado) apos registrar no cost_tracker em-memoria.
- models.py: classmethod top_subagents_by_cost(days, limit) usa indice GIN.
- insights_service.py: secao subagent_costs no dashboard.
- Flag USE_SUBAGENT_COST_GRANULAR controla persistencia.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Checkpoint Fase 1

- [ ] **Rodar suite completa de testes da fase 1**

```bash
source .venv/bin/activate
pytest tests/agente/sdk/test_subagent_reader.py \
       tests/agente/sdk/test_hooks_subagent_cost.py \
       tests/agente/utils/test_pii_masker.py \
       tests/agente/routes/test_admin_subagents.py \
       tests/agente/models/test_top_subagents_by_cost.py \
       -v
```

Expected: todos passam (total ~24 testes)

- [ ] **Smoke test manual**

```bash
# 1. Iniciar app local
python run.py &

# 2. Login admin em http://localhost:5000
# 3. Acessar endpoint (substituir <session_id> real):
curl -s http://localhost:5000/agente/api/admin/sessions/<session_id>/subagents | jq
```

- [ ] **Pausa para revisao humana** — Fase 1 completa. Prosseguir para Fase 2 apos aprovacao.

---

## Fase 2 — UI + Memory Mining

### Task 2.1: Emit `subagent_summary` via `client.py`

**Files:**
- Modify: `app/agente/sdk/client.py`
- Test: `tests/agente/sdk/test_emit_subagent_summary.py`

- [ ] **Step 1: Criar teste**

Criar `tests/agente/sdk/test_emit_subagent_summary.py`:

```python
"""Testa emit_subagent_summary no client."""
import pytest
from queue import Queue
from unittest.mock import MagicMock, patch


def test_emit_subagent_summary_puts_stream_event_on_queue():
    from app.agente.sdk.client import _emit_subagent_summary
    from app.agente.sdk.stream_parser import StreamEvent

    q = Queue()
    summary_dict = {
        'agent_id': 'a1',
        'agent_type': 'analista-carteira',
        'status': 'done',
        'duration_ms': 8234,
        'tools_used': [],
        'cost_usd': 0.012,
    }

    _emit_subagent_summary(q, summary_dict)

    assert not q.empty()
    ev = q.get_nowait()
    assert isinstance(ev, StreamEvent)
    assert ev.type == 'subagent_summary'
    assert ev.data['agent_type'] == 'analista-carteira'


def test_emit_subagent_summary_safe_with_none_queue():
    from app.agente.sdk.client import _emit_subagent_summary
    _emit_subagent_summary(None, {'agent_type': 'x'})  # nao levanta
```

- [ ] **Step 2: Rodar teste (falha)**

Run: `pytest tests/agente/sdk/test_emit_subagent_summary.py -v`
Expected: `ImportError: cannot import _emit_subagent_summary`

- [ ] **Step 3: Adicionar funcao em `client.py`**

Ler `app/agente/sdk/client.py`. Localizar o modulo-level (antes de `class ClaudeClient`) e adicionar:

```python
def _emit_subagent_summary(event_queue, summary_dict: dict) -> None:
    """
    Emite StreamEvent('subagent_summary') na event_queue da sessao.

    Chamado pelo _subagent_stop_hook apos persistir cost granular.
    Thread-safe: event_queue e um queue.Queue() protegido por lock interno.
    No-op se event_queue for None.
    """
    if event_queue is None:
        return
    try:
        from .stream_parser import StreamEvent
        event_queue.put_nowait(StreamEvent(
            type='subagent_summary',
            data=summary_dict,
        ))
    except Exception as e:
        logger.debug(f"[emit_subagent_summary] falhou: {e}")
```

- [ ] **Step 4: Rodar teste (passa)**

Run: `pytest tests/agente/sdk/test_emit_subagent_summary.py -v`
Expected: `2 passed`

- [ ] **Step 5: Disparar emit no `_subagent_stop_hook` (hooks.py)**

Apos o bloco de cost granular (ao final do handler), adicionar:

```python
            # #6 UI — emite subagent_summary para o frontend
            from ..config.feature_flags import USE_SUBAGENT_UI
            if USE_SUBAGENT_UI and event_queue is not None:
                try:
                    from .subagent_reader import get_subagent_summary
                    from .client import _emit_subagent_summary
                    summary = get_subagent_summary(
                        session_id=session_id,
                        agent_id=agent_id,
                        agent_type=agent_type,
                        include_pii=True,  # sanitizacao aplicada na camada 2 (routes/chat.py)
                    )
                    _emit_subagent_summary(event_queue, summary.to_dict())
                except Exception as ui_err:
                    logger.debug(f"[HOOK:SubagentStop] emit UI falhou: {ui_err}")
```

**Observacao**: `event_queue` ja esta disponivel no escopo do `build_hooks()` via closure.

- [ ] **Step 6: Commit**

```bash
git add app/agente/sdk/client.py app/agente/sdk/hooks.py tests/agente/sdk/test_emit_subagent_summary.py
git commit -m "$(cat <<'EOF'
feat(agente): emit subagent_summary via event_queue (#6 camada 1)

_emit_subagent_summary() coloca StreamEvent tipo 'subagent_summary' na
event_queue da sessao. Chamado pelo _subagent_stop_hook apos cost
granular. Flag USE_SUBAGENT_UI controla emissao.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2.2: SSE passthrough em `chat.py` (camada 2)

**Files:**
- Modify: `app/agente/routes/chat.py` (`_process_stream_event`)
- Test: `tests/agente/routes/test_chat_subagent_sse.py`

- [ ] **Step 1: Criar teste**

Criar `tests/agente/routes/test_chat_subagent_sse.py`:

```python
"""Testa SSE passthrough de subagent_summary com sanitizacao por perfil."""
import pytest
from unittest.mock import MagicMock, patch


def test_process_stream_event_admin_sees_cost():
    """Admin recebe cost_usd no payload."""
    from app.agente.routes.chat import _sanitize_subagent_summary_for_user

    summary = {
        'agent_type': 'analista-carteira',
        'cost_usd': 0.012,
        'findings_text': 'CNPJ 12.345.678/0001-90 tem 5 pedidos',
        'tools_used': [{'name': 'q', 'args_summary': 'SELECT',
                         'result_summary': '', 'tool_use_id': 't'}],
    }

    admin = MagicMock(perfil='administrador')
    result = _sanitize_subagent_summary_for_user(summary, admin)

    assert result['cost_usd'] == 0.012
    assert '12.345.678/0001-90' in result['findings_text']  # admin ve raw


def test_process_stream_event_user_sanitized():
    """User nao-admin: sem cost_usd + PII mascarada."""
    from app.agente.routes.chat import _sanitize_subagent_summary_for_user

    summary = {
        'agent_type': 'analista-carteira',
        'cost_usd': 0.012,
        'findings_text': 'CNPJ 12.345.678/0001-90 tem 5 pedidos',
        'tools_used': [{'name': 'q', 'args_summary': '12.345.678/0001-90',
                         'result_summary': '', 'tool_use_id': 't'}],
    }

    user = MagicMock(perfil='vendedor')
    result = _sanitize_subagent_summary_for_user(summary, user)

    assert 'cost_usd' not in result
    assert '12.345.678/0001-90' not in result['findings_text']
    assert '**.***.***' in result['findings_text']
    assert '12.345.678/0001-90' not in result['tools_used'][0]['args_summary']
```

- [ ] **Step 2: Rodar teste (falha)**

Run: `pytest tests/agente/routes/test_chat_subagent_sse.py -v`
Expected: `ImportError` — `_sanitize_subagent_summary_for_user` nao existe

- [ ] **Step 3: Adicionar helper em `routes/chat.py`**

Localizar `_process_stream_event` (por volta da linha 560). Adicionar funcao helper no modulo (antes de `_process_stream_event`):

```python
def _sanitize_subagent_summary_for_user(summary: dict, user) -> dict:
    """
    Aplica sanitizacao PII + remove cost_usd se user nao for admin.

    Admin: ve tudo raw. User normal: PII mascarada, sem custo.
    """
    from app.agente.utils.pii_masker import mask_pii

    if getattr(user, 'perfil', None) == 'administrador':
        return dict(summary)  # copia shallow, sem alteracao

    sanitized = dict(summary)
    sanitized.pop('cost_usd', None)
    sanitized['findings_text'] = mask_pii(sanitized.get('findings_text', ''))
    sanitized['tools_used'] = [
        {
            **t,
            'args_summary': mask_pii(t.get('args_summary', '')),
            'result_summary': mask_pii(t.get('result_summary', '')),
        }
        for t in sanitized.get('tools_used', [])
    ]
    return sanitized
```

Dentro de `_process_stream_event`, adicionar branch novo (apos os existentes para `task_*`):

```python
        elif event.type == 'subagent_summary':
            payload = _sanitize_subagent_summary_for_user(
                event.data or {}, current_user
            )
            yield _sse_event('subagent_summary', payload)
```

- [ ] **Step 4: Rodar teste (passa)**

Run: `pytest tests/agente/routes/test_chat_subagent_sse.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add app/agente/routes/chat.py tests/agente/routes/test_chat_subagent_sse.py
git commit -m "$(cat <<'EOF'
feat(agente): SSE passthrough subagent_summary com sanitizacao (#6 camada 2)

_process_stream_event reconhece StreamEvent('subagent_summary') e
aplica _sanitize_subagent_summary_for_user (mascara PII e remove
cost_usd para non-admin).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2.3: Rota user-facing lazy-fetch detalhes

**Files:**
- Create: `app/agente/routes/subagents.py`
- Modify: `app/agente/routes/__init__.py`
- Test: `tests/agente/routes/test_subagents_lazy.py`

- [ ] **Step 1: Criar teste**

Criar `tests/agente/routes/test_subagents_lazy.py`:

```python
"""Testa rota user-facing para lazy-fetch de detalhes do subagent."""
import pytest
from unittest.mock import MagicMock, patch


def test_user_fetches_own_subagent_summary_sanitized(client, normal_user):
    """User le seu proprio subagent — PII mascarada, sem cost."""
    from app.agente.sdk.subagent_reader import SubagentSummary
    from datetime import datetime

    summary = SubagentSummary(
        agent_id='a1', agent_type='analista-carteira', status='done',
        started_at=datetime(2026, 4, 16), ended_at=datetime(2026, 4, 16),
        duration_ms=100, cost_usd=0.012,
        findings_text='CNPJ 12.345.678/0001-90',
    )
    sess_mock = MagicMock(user_id=normal_user.id)

    with patch('flask_login.utils._get_user', return_value=normal_user), \
         patch('app.agente.routes.subagents.AgentSession.query') as qm, \
         patch('app.agente.routes.subagents.get_subagent_summary',
               return_value=summary):
        qm.filter_by.return_value.first.return_value = sess_mock
        resp = client.get('/agente/api/sessions/s1/subagents/a1/summary')

    assert resp.status_code == 200
    data = resp.get_json()
    assert 'cost_usd' not in data['subagent']
    assert '12.345.678/0001-90' not in data['subagent']['findings_text']


def test_user_cannot_read_other_users_session_returns_403(client, normal_user):
    """Sessao de outro usuario retorna 403."""
    sess_mock = MagicMock(user_id=999)  # outro user

    with patch('flask_login.utils._get_user', return_value=normal_user), \
         patch('app.agente.routes.subagents.AgentSession.query') as qm:
        qm.filter_by.return_value.first.return_value = sess_mock
        resp = client.get('/agente/api/sessions/s1/subagents/a1/summary')

    assert resp.status_code == 403


def test_admin_reads_any_session(client, admin_user):
    """Admin le sessao de qualquer usuario + ve cost raw."""
    from app.agente.sdk.subagent_reader import SubagentSummary
    from datetime import datetime

    summary = SubagentSummary(
        agent_id='a1', agent_type='x', status='done',
        started_at=datetime(2026, 4, 16), ended_at=datetime(2026, 4, 16),
        duration_ms=100, cost_usd=0.5,
        findings_text='CNPJ 12.345.678/0001-90',
    )
    sess_mock = MagicMock(user_id=999)  # outro user

    with patch('flask_login.utils._get_user', return_value=admin_user), \
         patch('app.agente.routes.subagents.AgentSession.query') as qm, \
         patch('app.agente.routes.subagents.get_subagent_summary',
               return_value=summary):
        qm.filter_by.return_value.first.return_value = sess_mock
        resp = client.get('/agente/api/sessions/s1/subagents/a1/summary')

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['subagent']['cost_usd'] == 0.5
    assert '12.345.678/0001-90' in data['subagent']['findings_text']
```

- [ ] **Step 2: Rodar teste (falha)**

Run: `pytest tests/agente/routes/test_subagents_lazy.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Criar `app/agente/routes/subagents.py`**

```python
"""
Rota user-facing para lazy-fetch de detalhes de subagente (#6 UI).

Usado quando o usuario clica "expandir" na linha do subagente no chat.
Verifica dono da sessao (ou admin), aplica sanitizacao PII automatica
para non-admin e retorna summary completo.
"""
import logging

from flask import abort, jsonify
from flask_login import current_user, login_required

from app.agente.config.feature_flags import USE_SUBAGENT_UI
from app.agente.models import AgentSession
from app.agente.routes import agente_bp
from app.agente.routes.chat import _sanitize_subagent_summary_for_user
from app.agente.sdk.subagent_reader import get_subagent_summary

logger = logging.getLogger('sistema_fretes')


@agente_bp.route(
    '/api/sessions/<session_id>/subagents/<agent_id>/summary',
    methods=['GET'],
)
@login_required
def api_user_subagent_summary(session_id: str, agent_id: str):
    """
    Lazy-fetch do summary completo do subagent para o frontend.

    Autorizacao: dono da sessao OU admin. Admin ve tudo raw + cost.
    User normal: PII mascarada, cost_usd removido.
    """
    if not USE_SUBAGENT_UI:
        abort(404)

    sess = AgentSession.query.filter_by(session_id=session_id).first()
    if sess is None:
        return jsonify({'success': False, 'error': 'Sessao nao encontrada'}), 404

    is_admin = getattr(current_user, 'perfil', None) == 'administrador'
    if not is_admin and sess.user_id != current_user.id:
        abort(403)

    summary = get_subagent_summary(
        session_id=session_id,
        agent_id=agent_id,
        include_pii=True,  # sanitizacao aplicada abaixo por perfil
        max_tool_chars=1000,
    )

    if summary.status == 'error':
        return jsonify({
            'success': False,
            'error': f'Subagent {agent_id} nao encontrado',
        }), 404

    payload = _sanitize_subagent_summary_for_user(
        summary.to_dict(), current_user
    )
    return jsonify({
        'success': True,
        'session_id': session_id,
        'agent_id': agent_id,
        'subagent': payload,
    })
```

- [ ] **Step 4: Registrar em `routes/__init__.py`**

Adicionar linha apos `admin_subagents`:

```python
from . import subagents  # noqa: F401 — rota user-facing para UI #6
```

- [ ] **Step 5: Rodar teste (passa)**

Run: `pytest tests/agente/routes/test_subagents_lazy.py -v`
Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add app/agente/routes/subagents.py app/agente/routes/__init__.py tests/agente/routes/test_subagents_lazy.py
git commit -m "$(cat <<'EOF'
feat(agente): rota user-facing lazy-fetch subagent summary (#6)

GET /agente/api/sessions/<id>/subagents/<aid>/summary
- Dono ou admin podem acessar
- PII mascarada + cost removido para non-admin (via _sanitize_...)
- Flag USE_SUBAGENT_UI controla disponibilidade

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2.4: CSS `_subagent-inline.css`

**Files:**
- Create: `app/static/agente/css/_subagent-inline.css`
- Modify: `app/static/agente/css/agent-theme.css`

- [ ] **Step 1: Criar CSS**

```css
/*
 * Linha inline expansivel de subagente no chat (#6).
 * Design tokens: var(--agent-*) definidos em agent-theme.css.
 * Estados: running | done | expanded | validation_warning.
 */

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
  color: var(--agent-text-secondary, #94a3b8);
  font-size: 12px;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.subagent-inline:hover {
  background: rgba(148, 163, 184, 0.12);
  border-color: rgba(148, 163, 184, 0.3);
}

.subagent-inline .subagent-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.subagent-inline.running .subagent-dot {
  background: var(--agent-warning, #f59e0b);
  animation: subagent-pulse 1.5s infinite;
}

.subagent-inline.done .subagent-dot {
  background: var(--agent-success, #10b981);
}

.subagent-inline.error .subagent-dot {
  background: var(--agent-danger, #ef4444);
}

@keyframes subagent-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.subagent-inline .subagent-badge {
  background: rgba(0, 212, 170, 0.15);
  color: var(--agent-accent-primary, #00d4aa);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.subagent-inline .subagent-meta {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.subagent-inline .subagent-caret {
  color: var(--agent-text-muted, #64748b);
  font-size: 10px;
  transition: transform 0.2s ease;
}

.subagent-inline.expanded {
  flex-direction: column;
  align-items: stretch;
}

.subagent-inline.expanded .subagent-caret {
  transform: rotate(180deg);
}

.subagent-inline.expanded .subagent-header {
  display: flex;
  gap: 10px;
  align-items: center;
  width: 100%;
}

.subagent-inline-details {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed rgba(148, 163, 184, 0.2);
  font-size: 11px;
  color: var(--agent-text-primary, #e2e8f0);
}

.subagent-inline-details ol {
  padding-left: 18px;
  margin: 4px 0;
}

.subagent-inline-details li {
  margin: 3px 0;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 11px;
  line-height: 1.4;
}

.subagent-inline-details .tool-name {
  color: var(--agent-accent-primary, #00d4aa);
  font-weight: 600;
}

.subagent-inline-details .tool-result {
  color: var(--agent-text-secondary, #94a3b8);
  margin-left: 4px;
}

.subagent-inline .validation-warning {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--agent-warning, #f59e0b);
  font-size: 11px;
  margin-left: 6px;
}

.subagent-inline .validation-warning::before {
  content: "⚠";
}

.subagent-inline-details .validation-reason {
  margin-top: 6px;
  padding: 6px 8px;
  background: rgba(245, 158, 11, 0.08);
  border-left: 2px solid var(--agent-warning, #f59e0b);
  border-radius: 3px;
  color: var(--agent-warning, #f59e0b);
  font-size: 11px;
}
```

- [ ] **Step 2: Adicionar `@import` em `agent-theme.css`**

Ler `app/static/agente/css/agent-theme.css` e adicionar no inicio (apos o bloco `:root` com os tokens):

```css
@import url("./_subagent-inline.css");
```

- [ ] **Step 3: Smoke test visual manual**

```bash
# Iniciar servidor
python run.py
```

Abrir `http://localhost:5000/agente/chat` no navegador e verificar que nenhum CSS existente quebrou (sanity check).

- [ ] **Step 4: Commit**

```bash
git add app/static/agente/css/_subagent-inline.css app/static/agente/css/agent-theme.css
git commit -m "$(cat <<'EOF'
feat(agente): CSS linha inline expansivel de subagente (#6)

- Design tokens --agent-* (dark/light auto via agent-theme.css)
- Estados: running (dot pulsante amarelo) | done (verde) | error (vermelho)
- Expanded: detalhes cronologicos em ol com tool-name + tool-result
- validation-warning: icone amarelo para #4 (anti-alucinacao)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2.5: JS `renderSubagentLine` no `chat.js`

**Files:**
- Modify: `app/static/agente/js/chat.js`

- [ ] **Step 1: Adicionar helper `renderSubagentLine` em `chat.js`**

Ler `chat.js` para localizar o switch case principal (por volta da linha 1165 — onde esta `case 'task_started'`). Adicionar ANTES do switch (ou junto aos outros helpers de render, procurar por `addTimelineItem` ou similar):

```javascript
// ─── Subagent inline expansible line (#6) ────────────────────────────
// Map agent_id -> DOM element para atualizar linha existente ao receber
// eventos subsequentes (task_progress, subagent_summary, subagent_validation).
const subagentLines = new Map();

function renderSubagentLineStart(data) {
    // data: {task_id, task_type, description}
    const agentId = data.task_id || data.agent_id;
    const agentType = data.task_type || data.description || 'subagente';

    if (subagentLines.has(agentId)) return;  // idempotente

    const messagesContainer = document.getElementById('messages');
    if (!messagesContainer) return;

    const line = document.createElement('div');
    line.className = 'subagent-inline running';
    line.dataset.agentId = agentId;
    line.innerHTML = `
        <span class="subagent-dot"></span>
        <span class="subagent-badge">${escapeHtml(agentType)}</span>
        <span class="subagent-meta">executando…</span>
        <span class="subagent-caret">▼</span>
    `;
    line.addEventListener('click', () => toggleSubagentExpand(agentId));
    messagesContainer.appendChild(line);
    subagentLines.set(agentId, line);
}

function renderSubagentLineProgress(data) {
    const agentId = data.task_id || data.agent_id;
    const line = subagentLines.get(agentId);
    if (!line) return;
    const meta = line.querySelector('.subagent-meta');
    const tool = data.last_tool_name || 'processando';
    if (meta) meta.textContent = `usando ${tool}…`;
}

function renderSubagentLineSummary(data) {
    // data: SubagentSummary.to_dict() sanitizado por perfil
    const agentId = data.agent_id;
    let line = subagentLines.get(agentId);

    // Se nao existe (evento perdido), cria novo
    if (!line) {
        const messagesContainer = document.getElementById('messages');
        line = document.createElement('div');
        line.className = 'subagent-inline';
        line.dataset.agentId = agentId;
        messagesContainer.appendChild(line);
        subagentLines.set(agentId, line);
        line.addEventListener('click', () => toggleSubagentExpand(agentId));
    }

    line.classList.remove('running');
    line.classList.add('done');

    const numTools = (data.tools_used || []).length;
    const durationSec = Math.round((data.duration_ms || 0) / 100) / 10;
    const costStr = data.cost_usd != null
        ? ` · $${data.cost_usd.toFixed(4)}`
        : '';
    const metaText = `${numTools} tool${numTools !== 1 ? 's' : ''} · ${durationSec}s${costStr}`;

    line.innerHTML = `
        <span class="subagent-dot"></span>
        <span class="subagent-badge">${escapeHtml(data.agent_type || 'subagente')}</span>
        <span class="subagent-meta">${escapeHtml(metaText)}</span>
        <span class="subagent-caret">▼</span>
    `;
    line.dataset.summary = JSON.stringify(data);
}

function renderSubagentValidationWarning(data) {
    // data: {agent_id, agent_type, score, reason, flagged_claims}
    const line = subagentLines.get(data.agent_id);
    if (!line) return;

    const badge = line.querySelector('.subagent-badge');
    if (badge && !line.querySelector('.validation-warning')) {
        const warn = document.createElement('span');
        warn.className = 'validation-warning';
        warn.title = `Score: ${data.score} — ${data.reason || ''}`;
        badge.after(warn);
    }
    line.dataset.validation = JSON.stringify(data);
}

async function toggleSubagentExpand(agentId) {
    const line = subagentLines.get(agentId);
    if (!line) return;

    if (line.classList.contains('expanded')) {
        // Colapsar
        line.classList.remove('expanded');
        const details = line.querySelector('.subagent-inline-details');
        if (details) details.remove();
        return;
    }

    // Expandir
    line.classList.add('expanded');

    // Reestruturar header
    const originalHtml = line.innerHTML;
    line.innerHTML = `
        <div class="subagent-header">
            ${originalHtml}
        </div>
    `;

    const details = document.createElement('div');
    details.className = 'subagent-inline-details';
    details.textContent = 'Carregando…';
    line.appendChild(details);

    // Lazy-fetch
    try {
        const sessionId = window.currentSessionId || getCurrentSessionId?.();
        if (!sessionId) {
            details.textContent = 'Erro: sessao nao identificada';
            return;
        }
        const resp = await fetch(
            `/agente/api/sessions/${sessionId}/subagents/${agentId}/summary`
        );
        if (!resp.ok) {
            details.textContent = `Erro ${resp.status}`;
            return;
        }
        const payload = await resp.json();
        const s = payload.subagent || {};
        const toolsHtml = (s.tools_used || []).map((t, i) =>
            `<li><span class="tool-name">${escapeHtml(t.name)}</span>` +
            `<span class="tool-result">${escapeHtml((t.result_summary || '').slice(0, 120))}</span></li>`
        ).join('');
        const validationHtml = line.dataset.validation
            ? (() => {
                const v = JSON.parse(line.dataset.validation);
                return `<div class="validation-reason">Score ${v.score}: ${escapeHtml(v.reason || '')}</div>`;
              })()
            : '';
        details.innerHTML = `
            <ol>${toolsHtml}</ol>
            ${validationHtml}
            ${s.findings_text ? `<div style="margin-top:8px;color:var(--agent-text-secondary)">${escapeHtml(s.findings_text.slice(0, 400))}</div>` : ''}
        `;
    } catch (err) {
        details.textContent = `Erro: ${err.message}`;
    }
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = String(str ?? '');
    return div.innerHTML;
}
```

- [ ] **Step 2: Adicionar cases no switch SSE**

Localizar o switch que processa eventos SSE (ex: `case 'task_started':` por volta da linha 1165). Adicionar:

```javascript
        case 'subagent_summary':
            renderSubagentLineSummary(data);
            break;

        case 'subagent_validation':
            renderSubagentValidationWarning(data);
            break;
```

E ajustar os handlers existentes de `task_started` / `task_progress` para chamar as funcoes novas (mantendo comportamento de timeline lateral paralelamente):

```javascript
        case 'task_started':
            // Timeline lateral (existente)
            showTyping(`Delegando: ${data.task_type || data.description}...`);
            addTimelineItem({tool_name: 'Subagente', status: 'pending'});
            // Linha inline (nova)
            renderSubagentLineStart(data);
            break;

        case 'task_progress':
            // Timeline lateral (existente)
            showTyping(`Subagente usando ${data.last_tool_name}...`);
            // Linha inline (nova)
            renderSubagentLineProgress(data);
            break;
```

**NAO remover** comportamento existente de `showTyping`/`addTimelineItem` — a linha inline e COMPLEMENTAR. Tanto a timeline lateral quanto a linha inline ficam ativas.

- [ ] **Step 3: Verificar `window.currentSessionId`**

Buscar no `chat.js` como o session_id e armazenado (pode ser `currentSession.id`, `sessionId`, etc.). Ajustar `toggleSubagentExpand` para usar a variavel correta.

- [ ] **Step 4: Teste manual no browser**

```bash
python run.py
```

1. Abrir chat, fazer pergunta que spawna subagent (ex: "analise carteira Atacadao")
2. Verificar linha inline aparecer em running (dot amarelo)
3. Apos conclusao, verificar linha ficar done (dot verde) com "N tools · Ys · $X.XXXX"
4. Clicar linha → expande com detalhes

- [ ] **Step 5: Commit**

```bash
git add app/static/agente/js/chat.js
git commit -m "$(cat <<'EOF'
feat(agente): chat.js renderiza linha inline expansivel de subagent (#6)

- renderSubagentLineStart: cria linha running ao task_started
- renderSubagentLineProgress: atualiza meta ao task_progress
- renderSubagentLineSummary: finaliza linha ao subagent_summary
- renderSubagentValidationWarning: icone amarelo no subagent_validation (#4)
- toggleSubagentExpand: lazy-fetch em /api/sessions/<id>/subagents/<aid>/summary

Complementar a timeline lateral (nao substitui).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2.6: Memory mining #5

**Files:**
- Modify: `app/agente/services/pattern_analyzer.py`
- Modify: `app/agente/routes/_helpers.py`
- Test: `tests/agente/services/test_pattern_analyzer_subagents.py`

- [ ] **Step 1: Criar teste**

Criar `tests/agente/services/test_pattern_analyzer_subagents.py`:

```python
"""Testa que pattern_analyzer.extrair_conhecimento_sessao inclui subagents."""
import pytest
from unittest.mock import MagicMock, patch


def test_extrair_conhecimento_passes_subagent_findings_to_prompt(app):
    from app.agente.services.pattern_analyzer import extrair_conhecimento_sessao

    # Mock subagent_reader com 2 subagentes
    subagents = [
        MagicMock(agent_type='analista-carteira', tools_used=[
            {'name': 'query_sql', 'args_summary': 'SELECT * FROM pedidos',
             'result_summary': '24 pedidos', 'tool_use_id': 't'}
        ], findings_text='24 pedidos em aberto para Atacadao'),
        MagicMock(agent_type='raio-x-pedido', tools_used=[
            {'name': 'get_pedido', 'args_summary': 'VCD123',
             'result_summary': 'status: separacao', 'tool_use_id': 't2'}
        ], findings_text='VCD123 em separacao, embarque 17/04'),
    ]

    with app.app_context(), \
         patch('app.agente.services.pattern_analyzer.get_session_subagents_summary',
               return_value=subagents) as mock_get, \
         patch('app.agente.services.pattern_analyzer._call_sonnet_extract',
               return_value={'conhecimentos': []}) as mock_sonnet:
        ok = extrair_conhecimento_sessao(
            app=app,
            user_id=1,
            session_messages=[{'role': 'user', 'content': 'oi'}],
            include_subagents=True,
            session_id='sess-abc',
        )

    assert ok
    mock_get.assert_called_once_with('sess-abc', include_pii=False)
    # Verifica que o prompt enviado ao Sonnet contem as descobertas dos subagents
    prompt_arg = mock_sonnet.call_args[0][0]
    assert 'analista-carteira' in prompt_arg
    assert '24 pedidos em aberto' in prompt_arg
    assert 'raio-x-pedido' in prompt_arg
    assert 'VCD123 em separacao' in prompt_arg


def test_flag_off_skips_subagent_fetch(app):
    from app.agente.services.pattern_analyzer import extrair_conhecimento_sessao

    with app.app_context(), \
         patch('app.agente.services.pattern_analyzer.USE_SUBAGENT_MEMORY_MINING',
               False), \
         patch('app.agente.services.pattern_analyzer.get_session_subagents_summary') as mock_get, \
         patch('app.agente.services.pattern_analyzer._call_sonnet_extract',
               return_value={'conhecimentos': []}):
        extrair_conhecimento_sessao(
            app=app, user_id=1,
            session_messages=[{'role': 'user', 'content': 'oi'}],
            include_subagents=True,
            session_id='sess-x',
        )

    mock_get.assert_not_called()
```

- [ ] **Step 2: Rodar teste (falha)**

Run: `pytest tests/agente/services/test_pattern_analyzer_subagents.py -v`
Expected: falha — assinatura de `extrair_conhecimento_sessao` ainda nao aceita `include_subagents`/`session_id`

- [ ] **Step 3: Modificar `pattern_analyzer.py`**

Ler `app/agente/services/pattern_analyzer.py`. Localizar `extrair_conhecimento_sessao`. Alterar assinatura:

```python
def extrair_conhecimento_sessao(
    app,
    user_id: int,
    session_messages: list[dict],
    include_subagents: bool = True,
    session_id: Optional[str] = None,
) -> bool:
```

Adicionar helper no topo do arquivo:

```python
def _format_subagent_findings_for_extraction(
    subagents: list,
    max_chars_per_subagent: int = 2000,
) -> str:
    """Formata findings de subagents para injecao no prompt Sonnet."""
    if not subagents:
        return ''

    parts = ['## Descobertas dos Especialistas (sessao)\n']
    for s in subagents:
        if getattr(s, 'status', None) != 'done':
            continue
        header = f"### {s.agent_type} ({len(s.tools_used)} tools, " \
                 f"{(s.duration_ms or 0) / 1000:.1f}s)"
        parts.append(header)
        for t in s.tools_used[:5]:  # top 5 tools por subagent
            line = f"- {t['name']}: {(t['result_summary'] or '')[:150]}"
            parts.append(line)
        if s.findings_text:
            findings = s.findings_text[:max_chars_per_subagent]
            parts.append(f"\nResultado: {findings}\n")
        parts.append('')

    return '\n'.join(parts)
```

Na funcao `extrair_conhecimento_sessao`, apos formatar mensagens do pai, adicionar injecao:

```python
    # Feature #5 — Memory mining cross-subagent
    from ..config.feature_flags import USE_SUBAGENT_MEMORY_MINING
    from ..sdk.subagent_reader import get_session_subagents_summary

    subagent_section = ''
    if include_subagents and USE_SUBAGENT_MEMORY_MINING and session_id:
        try:
            subagents = get_session_subagents_summary(
                session_id, include_pii=False
            )
            subagent_section = _format_subagent_findings_for_extraction(subagents)
        except Exception as e:
            logger.debug(f"[pattern_analyzer] subagent fetch falhou: {e}")

    # Prepend ao contexto do prompt Sonnet
    prompt_context = subagent_section + '\n\n## Conversa principal\n' + \
                     formatted_messages
    # ... passar prompt_context ao chamador Sonnet
```

**Observacao**: a variavel exata que contem o prompt formatado depende da estrutura atual — procurar pela chamada ao Sonnet (`anthropic.messages.create` ou wrapper `_call_sonnet_extract`) e garantir que `subagent_section` seja concatenada ao conteudo da mensagem de usuario.

- [ ] **Step 4: Modificar caller em `routes/_helpers.py`**

Ler `routes/_helpers.py`. Localizar onde `extrair_conhecimento_sessao` e chamada (possivelmente em daemon thread apos exchange). Passar `session_id`:

```python
# Exemplo: substituir chamada existente
extrair_conhecimento_sessao(
    app=current_app._get_current_object(),
    user_id=user_id,
    session_messages=session_messages,
    include_subagents=True,       # novo
    session_id=session_id,         # novo (ja disponivel no escopo)
)
```

- [ ] **Step 5: Rodar teste (passa)**

Run: `pytest tests/agente/services/test_pattern_analyzer_subagents.py -v`
Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add app/agente/services/pattern_analyzer.py app/agente/routes/_helpers.py tests/agente/services/test_pattern_analyzer_subagents.py
git commit -m "$(cat <<'EOF'
feat(agente): memory mining cross-subagent (#5)

extrair_conhecimento_sessao agora aceita include_subagents=True e
session_id — busca findings dos especialistas via subagent_reader e
injeta como secao "## Descobertas dos Especialistas" ANTES da conversa
principal no prompt Sonnet. Cap 2K chars/subagent.

Flag USE_SUBAGENT_MEMORY_MINING controla ativacao.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2.7: Documentar eventos SSE em `app/agente/CLAUDE.md`

**Files:**
- Modify: `app/agente/CLAUDE.md`

- [ ] **Step 1: Atualizar mapa de eventos SSE**

Localizar a tabela `Mapa de eventos` em `CLAUDE.md` (linha ~330). Adicionar linhas:

```markdown
| `subagent_summary` | StreamEvent | _sse_event | case | SubagentStop hook (#6) |
| `subagent_validation` | StreamEvent (async RQ) | _sse_event | case | validator worker (#4) |
```

- [ ] **Step 2: Adicionar secao sobre as features novas**

Apos a secao `SDK 0.1.60` existente (linha ~394), adicionar sub-secao:

```markdown
### Features adotadas (2026-04-16, fase 1-2):
- **Endpoint admin debug forense** (`routes/admin_subagents.py`): 3 rotas admin-only (`/api/admin/sessions/<id>/subagents[/<aid>[/messages]]`). Flag `USE_SUBAGENT_DEBUG_ENDPOINT`.
- **Cost tracking granular** (`hooks.py` + `models.py` + `insights_service.py`): persiste por subagent em `AgentSession.data['subagent_costs']` (JSONB + indice GIN). Flag `USE_SUBAGENT_COST_GRANULAR`.
- **UI linha inline expansivel** (`chat.js` + `_subagent-inline.css` + `subagents.py`): linha no fluxo da conversa com estados running/done/expanded. Lazy-fetch em `/api/sessions/<id>/subagents/<aid>/summary`. Flag `USE_SUBAGENT_UI`.
- **Memory mining cross-subagent** (`pattern_analyzer.py`): `extrair_conhecimento_sessao(include_subagents=True, session_id=...)` injeta findings dos especialistas no prompt Sonnet. Flag `USE_SUBAGENT_MEMORY_MINING`.

PII mascarada automaticamente para non-admin via `utils/pii_masker.py`. Admin ve raw + custo.
Fonte canonica via `sdk/subagent_reader.py` — todos consumidores leem por aqui.
```

- [ ] **Step 3: Commit**

```bash
git add app/agente/CLAUDE.md
git commit -m "docs(agente): documenta features SDK 0.1.60 fases 1-2

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Checkpoint Fase 2

- [ ] **Suite completa de testes**

```bash
pytest tests/agente/ -v --maxfail=5
```

Expected: todos passam (fase 1 + fase 2 — ~40 testes)

- [ ] **E2E manual no browser**

```bash
python run.py
```

1. Login usuario normal → chat → pergunta "analise carteira Atacadao"
2. Observar:
   - Linha inline aparece com dot amarelo pulsante + "analista-carteira — executando…"
   - Apos alguns segundos, dot vira verde + "N tools · Ys" (**SEM $X.XXXX**)
   - Click expande → detalhes carregam (PII mascarada se houver)
3. Logout → login admin → repetir
4. Observar linha agora mostrando "$X.XXXX"
5. Click expande → detalhes raw (PII visivel)

- [ ] **Pausa para revisao humana** — Fase 2 completa.

---

## Fase 3 — Migracao Documental (#2)

### Task 3.1: Verificar uso atual de `get_subagent_findings`

**Files:**
- Grep/verificar: consumidores atuais do protocolo `/tmp/subagent-findings/`

- [ ] **Step 1: Mapear onde o parent le findings de `/tmp/`**

```bash
grep -rn "subagent-findings" app/agente/ app/teams/ .claude/ 2>/dev/null | head -20
```

Anotar os arquivos que consomem `/tmp/subagent-findings/`. Espera-se: apenas `.claude/references/SUBAGENT_RELIABILITY.md` (documentacao) + possiveis mencoes em prompts de subagentes.

- [ ] **Step 2: Confirmar que a leitura e feita pelo LLM (via Read tool) e nao por codigo Python**

Se **nao** houver consumidores em codigo Python (apenas instrucao ao LLM), a migracao e puramente documental — o helper `get_subagent_findings` ja existe em `subagent_reader.py` (Task 1.1) e fica disponivel como alternativa. Sem alteracao de codigo.

Se houver consumidores Python, adicionar wrapper defensivo:

```python
# Em um util apropriado (possivelmente routes/_helpers.py ou novo utils/findings.py):
def read_findings_preferring_sdk(session_id: str, agent_type: str) -> Optional[str]:
    """Le findings preferindo SDK; fallback para /tmp/."""
    from app.agente.sdk.subagent_reader import get_subagent_findings
    result = get_subagent_findings(session_id, agent_type)
    if result:
        return result
    # Fallback /tmp/
    import glob
    files = glob.glob(f'/tmp/subagent-findings/{agent_type}-*.md')
    if files:
        files.sort(reverse=True)  # mais recente
        try:
            with open(files[0]) as f:
                return f.read()
        except OSError:
            return None
    return None
```

- [ ] **Step 3: Commit (se Python foi modificado)**

```bash
git add -p   # revisar mudancas
git commit -m "feat(agente): leitura de findings preferindo SDK sobre /tmp/ (#2)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 3.2: Atualizar `SUBAGENT_RELIABILITY.md` e `CLAUDE.md`

**Files:**
- Modify: `.claude/references/SUBAGENT_RELIABILITY.md`
- Modify: `CLAUDE.md` (raiz)

- [ ] **Step 1: Adicionar secao "Ordem de leitura" em `SUBAGENT_RELIABILITY.md`**

Ler `.claude/references/SUBAGENT_RELIABILITY.md` e inserir apos a secao M1 (protocolo `/tmp/`):

```markdown
## M1.1 — Ordem de leitura (SDK 0.1.60+, 2026-04-16)

Com o SDK 0.1.60, o projeto ganhou `list_subagents()` + `get_subagent_messages()` — fonte canonica do transcript completo de cada subagente. O protocolo `/tmp/subagent-findings/` continua ativo como fallback escrito.

**Ordem recomendada** ao ler findings de um subagente:

1. **Primeira fonte** — `app.agente.sdk.subagent_reader.get_subagent_findings(session_id, agent_type)` — le do JSONL do SDK. Completo, estruturado, sem precisar parsear markdown.
2. **Fallback** — `/tmp/subagent-findings/{agent_type}-{contexto}.md` — apenas se (1) retornou `None`:
   - SDK nao encontrou o subagent (agent_id invalido)
   - JSONL corrompido (ver `CLAUDE.md:161` para risco conhecido)
   - SDK downgrade temporario

**Nao remover a instrucao de escrita em `/tmp/`** dos 6 agents de acao — e rede de seguranca contra falhas do SDK.
```

- [ ] **Step 2: Atualizar `CLAUDE.md` raiz**

Na tabela "Infraestrutura e Agente", a entrada de `SUBAGENT_RELIABILITY.md` ja existe. Adicionar nota abaixo dela:

```markdown
> **Desde 2026-04-16 (SDK 0.1.60)**: fonte canonica de findings e `sdk/subagent_reader.py:get_subagent_findings()`. `/tmp/subagent-findings/` permanece como fallback escrito.
```

- [ ] **Step 3: Commit**

```bash
git add .claude/references/SUBAGENT_RELIABILITY.md CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: migracao soft /tmp/subagent-findings -> SDK 0.1.60 (#2)

- SUBAGENT_RELIABILITY.md: nova secao M1.1 "Ordem de leitura"
  (SDK transcript primario, /tmp/ fallback)
- CLAUDE.md raiz: nota sobre fonte canonica

/tmp/ permanece ativo como rede de seguranca contra falhas do SDK.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Checkpoint Fase 3

- [ ] **Revisao manual das mudancas documentais**

```bash
git diff HEAD~1 -- .claude/references/SUBAGENT_RELIABILITY.md CLAUDE.md
```

Verificar clareza e consistencia.

- [ ] **Pausa para revisao humana** — Fase 3 completa.

---

## Fase 4 — Validacao Anti-Alucinacao (#4)

### Task 4.1: Job validator

**Files:**
- Create: `app/agente/workers/__init__.py` (se nao existir)
- Create: `app/agente/workers/subagent_validator.py`
- Test: `tests/agente/workers/test_subagent_validator.py`

- [ ] **Step 1: Criar teste**

```bash
mkdir -p tests/agente/workers
touch tests/agente/workers/__init__.py
```

Criar `tests/agente/workers/test_subagent_validator.py`:

```python
"""Testa job RQ de validacao anti-alucinacao (#4)."""
import json
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def sample_summary():
    from app.agente.sdk.subagent_reader import SubagentSummary
    return SubagentSummary(
        agent_id='a1', agent_type='analista-carteira', status='done',
        started_at=None, ended_at=None, duration_ms=100,
        tools_used=[
            {'name': 'query_sql', 'args_summary': 'SELECT COUNT(*) FROM pedidos',
             'result_summary': '24', 'tool_use_id': 't1'}
        ],
        findings_text='Ha 30 pedidos em aberto.',  # inconsistencia: SQL retornou 24
        num_turns=2,
    )


def test_validator_parses_haiku_json_and_persists(app, sample_summary):
    from app.agente.workers.subagent_validator import validate_subagent_output
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        sess = AgentSession(
            session_id='sess-val-1', user_id=1, title='t', data={}
        )
        db.session.add(sess)
        db.session.commit()

        haiku_response = json.dumps({
            'score': 40,
            'reason': 'Resposta menciona 30, SQL retornou 24',
            'flagged_claims': ['30 pedidos em aberto'],
        })

        with patch('app.agente.workers.subagent_validator.get_subagent_summary',
                   return_value=sample_summary), \
             patch('app.agente.workers.subagent_validator._call_haiku',
                   return_value=haiku_response), \
             patch('app.agente.workers.subagent_validator._push_validation_event') as mock_push:
            validate_subagent_output(
                session_id='sess-val-1', agent_id='a1', threshold=70
            )

        db.session.refresh(sess)
        entries = sess.data['subagent_validations']['entries']
        assert len(entries) == 1
        assert entries[0]['score'] == 40
        assert entries[0]['agent_id'] == 'a1'
        mock_push.assert_called_once()  # score < threshold -> push SSE


def test_validator_no_push_when_score_above_threshold(app, sample_summary):
    from app.agente.workers.subagent_validator import validate_subagent_output
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        sess = AgentSession(
            session_id='sess-val-2', user_id=1, title='t', data={}
        )
        db.session.add(sess)
        db.session.commit()

        good_response = json.dumps({
            'score': 90, 'reason': 'Consistente', 'flagged_claims': [],
        })

        with patch('app.agente.workers.subagent_validator.get_subagent_summary',
                   return_value=sample_summary), \
             patch('app.agente.workers.subagent_validator._call_haiku',
                   return_value=good_response), \
             patch('app.agente.workers.subagent_validator._push_validation_event') as mock_push:
            validate_subagent_output(
                session_id='sess-val-2', agent_id='a1', threshold=70
            )

        mock_push.assert_not_called()  # score >= threshold
```

- [ ] **Step 2: Rodar teste (falha)**

Run: `pytest tests/agente/workers/test_subagent_validator.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Criar `app/agente/workers/` e `subagent_validator.py`**

```bash
mkdir -p app/agente/workers
touch app/agente/workers/__init__.py
```

Criar `app/agente/workers/subagent_validator.py`:

```python
"""
Validador anti-alucinacao assincrono (feature #4).

Job RQ executado na queue 'agent_validation' pelos workers existentes
(worker_render.py em producao, worker_atacadao.py em dev). Compara a
resposta final do subagente com o resultado de suas tools usando Haiku
4.5, retorna score 0-100. Se score < threshold, emite SSE event
'subagent_validation' para UI mostrar icone amarelo ⚠.
"""
import json
import logging
from typing import Optional

from app.agente.sdk.subagent_reader import get_subagent_summary
from app.utils.timezone import agora_brasil_naive

logger = logging.getLogger('sistema_fretes')

HAIKU_MODEL = 'claude-haiku-4-5-20251001'

VALIDATION_SYSTEM_PROMPT = """Voce compara o que um especialista fez \
(tool_calls + tool_results) vs o que ele reportou (resposta final).
Retorne EXCLUSIVAMENTE JSON valido no formato:

{"score": int 0-100, "reason": str curta, "flagged_claims": [str]}

Criterios:
- Score >= 80: resposta consistente com tool_results.
- Score 50-79: pequenas inconsistencias ou omissoes.
- Score < 50: resposta contradiz ou inventa informacoes.

flagged_claims = afirmacoes especificas do subagente que NAO estao \
suportadas pelos tool_results. Maximo 3 items."""


def _call_haiku(user_prompt: str) -> str:
    """Chama Haiku 4.5 e retorna texto da resposta."""
    import anthropic
    client = anthropic.Anthropic()  # usa ANTHROPIC_API_KEY do env
    resp = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=500,
        system=VALIDATION_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': user_prompt}],
    )
    # Extrai texto do primeiro content block
    for block in resp.content:
        if getattr(block, 'type', None) == 'text':
            return block.text
    return ''


def _build_user_prompt(summary) -> str:
    """Monta o prompt do usuario para o Haiku."""
    tools_section = []
    for t in summary.tools_used:
        tools_section.append(
            f"Tool: {t['name']}\n"
            f"  Args: {(t.get('args_summary') or '')[:300]}\n"
            f"  Result: {(t.get('result_summary') or '')[:500]}\n"
        )

    return (
        f"## Tools chamadas ({len(summary.tools_used)} total):\n\n"
        + '\n'.join(tools_section)
        + f"\n\n## Resposta final do subagent:\n{summary.findings_text[:3000]}"
    )


def _push_validation_event(session_id: str, event_data: dict) -> None:
    """
    Publica 'subagent_validation' no event_queue da sessao via Redis pub/sub.

    Como o worker RQ roda em processo separado, nao tem acesso direto a
    event_queue do SSE. Usamos Redis publish em canal por sessao; o SSE
    generator em routes/chat.py subscreve esse canal paralelamente a
    event_queue local.
    """
    try:
        import redis
        from app.agente.config.settings import get_settings
        r = redis.from_url(get_settings().redis_url)
        channel = f'agent_sse:{session_id}'
        r.publish(channel, json.dumps({
            'type': 'subagent_validation',
            'data': event_data,
        }))
    except Exception as e:
        logger.error(f"[validator] redis publish falhou: {e}")


def validate_subagent_output(
    session_id: str,
    agent_id: str,
    threshold: int = 70,
) -> None:
    """Job RQ: valida output do subagent, persiste e notifica se score < threshold."""
    logger.info(
        f"[validator] iniciando: session={session_id} agent_id={agent_id[:12]}"
    )

    summary = get_subagent_summary(
        session_id, agent_id, include_pii=True, max_tool_chars=1000
    )
    if summary.status == 'error':
        logger.warning(f"[validator] summary error, abortando")
        return

    # Chamada ao Haiku
    user_prompt = _build_user_prompt(summary)
    try:
        raw = _call_haiku(user_prompt)
    except Exception as e:
        logger.error(f"[validator] Haiku falhou: {e}")
        return

    # Parsear JSON (tolerante a prefixos/sufixos)
    try:
        start = raw.find('{')
        end = raw.rfind('}')
        payload = json.loads(raw[start:end + 1]) if start >= 0 else {}
    except (ValueError, json.JSONDecodeError):
        logger.warning(f"[validator] Haiku retornou JSON invalido: {raw[:200]}")
        return

    score = int(payload.get('score', 100))
    reason = str(payload.get('reason', ''))[:500]
    flagged = list(payload.get('flagged_claims', []))[:5]

    # Persistir em AgentSession.data['subagent_validations']
    try:
        from app import create_app, db
        from sqlalchemy.orm.attributes import flag_modified
        from app.agente.models import AgentSession

        app = create_app()
        with app.app_context():
            sess = AgentSession.query.filter_by(session_id=session_id).first()
            if sess is None:
                logger.warning(f"[validator] session {session_id} nao encontrada")
                return

            data = sess.data or {}
            bucket = data.setdefault(
                'subagent_validations', {'version': 1, 'entries': []}
            )
            entry = {
                'agent_id': agent_id,
                'agent_type': summary.agent_type,
                'score': score,
                'reason': reason,
                'flagged_claims': flagged,
                'validated_at': agora_brasil_naive().isoformat(),
            }
            bucket['entries'].append(entry)
            sess.data = data
            flag_modified(sess, 'data')
            db.session.commit()
    except Exception as e:
        logger.error(f"[validator] persistencia falhou: {e}")
        return

    logger.info(
        f"[validator] concluido: score={score} threshold={threshold} "
        f"agent_type={summary.agent_type}"
    )

    # Se score baixo, emitir SSE para o frontend
    if score < threshold:
        _push_validation_event(session_id, entry)
```

- [ ] **Step 4: Rodar teste (passa)**

Run: `pytest tests/agente/workers/test_subagent_validator.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add app/agente/workers/__init__.py app/agente/workers/subagent_validator.py tests/agente/workers/__init__.py tests/agente/workers/test_subagent_validator.py
git commit -m "$(cat <<'EOF'
feat(agente): job RQ validate_subagent_output com Haiku 4.5 (#4)

Compara tool_results vs findings_text via Haiku 4.5, parseia JSON
{score, reason, flagged_claims} e persiste em AgentSession.data.
Se score < threshold, publica 'subagent_validation' no canal Redis
agent_sse:<session_id> para SSE generator consumir.

Threshold configuravel via AGENT_SUBAGENT_VALIDATION_THRESHOLD.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4.2: Enqueue no `SubagentStop` hook

**Files:**
- Modify: `app/agente/sdk/hooks.py`

- [ ] **Step 1: Adicionar enqueue ao hook (apos emit UI)**

Apos o bloco de emit UI (#6) no `_subagent_stop_hook`, adicionar:

```python
            # #4 Validacao anti-alucinacao async (enfileira job RQ)
            from ..config.feature_flags import (
                USE_SUBAGENT_VALIDATION,
                SUBAGENT_VALIDATION_THRESHOLD,
            )
            if USE_SUBAGENT_VALIDATION and session_id and agent_id:
                try:
                    from rq import Queue
                    import redis
                    from ..config.settings import get_settings

                    r = redis.from_url(get_settings().redis_url)
                    q = Queue('agent_validation', connection=r)
                    q.enqueue(
                        'app.agente.workers.subagent_validator.validate_subagent_output',
                        session_id=session_id,
                        agent_id=agent_id,
                        threshold=SUBAGENT_VALIDATION_THRESHOLD,
                        job_timeout=60,
                    )
                    logger.debug(
                        f"[HOOK:SubagentStop] validacao enfileirada "
                        f"(agent_type={agent_type})"
                    )
                except Exception as val_err:
                    logger.debug(
                        f"[HOOK:SubagentStop] validacao enqueue falhou: {val_err}"
                    )
```

- [ ] **Step 2: Teste manual (precisa Redis + worker rodando)**

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: worker processando queue
python worker_atacadao.py --queues atacadao,agent_validation,high,default

# Terminal 3: app
python run.py
```

Enviar pergunta que spawna subagent. Verificar log do worker:
```
[validator] iniciando: session=... agent_id=...
[validator] concluido: score=... threshold=70 agent_type=...
```

- [ ] **Step 3: Commit**

```bash
git add app/agente/sdk/hooks.py
git commit -m "$(cat <<'EOF'
feat(agente): SubagentStop enfileira validacao async em agent_validation (#4)

Job e enfileirado em queue 'agent_validation' (processada pelos workers
existentes). Zero impacto na latencia da resposta do parent.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4.3: Adicionar queue aos workers existentes

**Files:**
- Modify: `worker_render.py`
- Modify: `worker_atacadao.py`

- [ ] **Step 1: Editar `worker_render.py`**

Localizar linha `default='atacadao,odoo_lancamento,impostos,recebimento,high,default'` (aprox. linha do `@click.option('--queues', ...)`).

Substituir por:
```python
default='atacadao,odoo_lancamento,impostos,recebimento,agent_validation,high,default'
```

- [ ] **Step 2: Editar `worker_atacadao.py`**

Localizar `default='atacadao,high,default'`. Substituir por:
```python
default='atacadao,agent_validation,high,default'
```

- [ ] **Step 3: Smoke test**

```bash
python worker_atacadao.py --help 2>&1 | grep agent_validation
```

Expected: `agent_validation` aparece no default list.

- [ ] **Step 4: Commit**

```bash
git add worker_render.py worker_atacadao.py
git commit -m "$(cat <<'EOF'
feat(workers): adiciona queue agent_validation aos workers existentes (#4)

- worker_render.py (producao): +agent_validation entre recebimento e high
- worker_atacadao.py (dev): +agent_validation entre atacadao e high

Processa job validate_subagent_output. Zero worker novo criado.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4.4: Subscrever canal Redis no SSE generator (camada 2)

**Files:**
- Modify: `app/agente/routes/chat.py` (SSE generator)

- [ ] **Step 1: Adicionar pubsub subscriber ao SSE loop**

Ler `app/agente/routes/chat.py` para localizar o SSE generator (funcao async com `yield _sse_event(...)`). Antes do loop principal, inicializar Redis pubsub:

```python
# Dentro do SSE generator (antes do loop while):
import redis
from app.agente.config.settings import get_settings

_redis_conn = None
_pubsub = None
try:
    _redis_conn = redis.from_url(get_settings().redis_url)
    _pubsub = _redis_conn.pubsub(ignore_subscribe_messages=True)
    _pubsub.subscribe(f'agent_sse:{session_id}')
except Exception as e:
    logger.debug(f"[SSE] pubsub setup falhou: {e}")
```

No loop principal de `event_queue`, apos `yield _sse_event(...)` atual, adicionar poll nao-bloqueante do pubsub:

```python
        # Poll Redis pubsub por eventos async (ex: #4 subagent_validation)
        if _pubsub is not None:
            try:
                msg = _pubsub.get_message(timeout=0.0)
                if msg and msg.get('type') == 'message':
                    payload = json.loads(msg['data'])
                    # payload: {'type': 'subagent_validation', 'data': {...}}
                    sanitized_data = _sanitize_subagent_summary_for_user(
                        payload.get('data', {}), current_user
                    )
                    yield _sse_event(payload['type'], sanitized_data)
            except Exception as ps_err:
                logger.debug(f"[SSE] pubsub poll falhou: {ps_err}")
```

No `finally` do generator:

```python
    finally:
        if _pubsub is not None:
            try:
                _pubsub.close()
            except Exception:
                pass
        # ... (cleanup existente)
```

- [ ] **Step 2: Testar integracao end-to-end**

```bash
# Terminal 1: redis-server
# Terminal 2: python worker_atacadao.py --queues agent_validation,high,default
# Terminal 3: python run.py
```

1. Login como user, abrir chat, fazer pergunta que spawna subagent
2. Se o Haiku determinar score < 70, verificar no frontend aparece icone amarelo ⚠ na linha do subagent (pode levar ~1-2s apos resposta)

- [ ] **Step 3: Commit**

```bash
git add app/agente/routes/chat.py
git commit -m "$(cat <<'EOF'
feat(agente): SSE subscribe agent_sse:<session_id> (#4)

Generator SSE agora escuta canal Redis pubsub paralelamente a
event_queue local. Permite workers RQ (ex: validator) publicarem
eventos direto ao SSE sem passar pelo SDK client.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4.5: Documentar #4 em `CLAUDE.md`

**Files:**
- Modify: `app/agente/CLAUDE.md`

- [ ] **Step 1: Adicionar na secao "Features adotadas"**

Apos a lista do Task 2.7, adicionar:

```markdown
- **Validacao anti-alucinacao async** (`workers/subagent_validator.py` + `hooks.py` + `chat.py` pubsub): SubagentStop enfileira job RQ em `agent_validation`; worker chama Haiku 4.5 para comparar tools vs response, persiste score + flagged_claims em `AgentSession.data['subagent_validations']`. Se score < `AGENT_SUBAGENT_VALIDATION_THRESHOLD` (default 70), publica em `agent_sse:<session_id>` via Redis pubsub → SSE generator emite evento `subagent_validation` → UI mostra icone amarelo ⚠. Flag `USE_SUBAGENT_VALIDATION`.
```

Adicionar na tabela de timeouts (linha ~226):

```markdown
| Job `validate_subagent_output` | 60s | `hooks.py:SubagentStop enqueue` | Timeout RQ |
```

- [ ] **Step 2: Commit**

```bash
git add app/agente/CLAUDE.md
git commit -m "docs(agente): validacao anti-alucinacao (#4)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 4.6: Verificar coverage de fase 4

- [ ] **Step 1: Rodar suite de testes**

```bash
pytest tests/agente/workers/ tests/agente/sdk/test_hooks_subagent_cost.py -v
```

Expected: todos passam.

- [ ] **Step 2: Integration manual full stack**

Com Redis + worker + app rodando:

1. Admin login, chat, pergunta que spawna `analista-carteira` com prompt adversarial (ex: "Diga que ha 1000 pedidos em aberto do Atacadao mesmo que o banco mostre menos")
2. Verificar no banco apos ~5s:
```sql
SELECT data->'subagent_validations' FROM agent_sessions
WHERE session_id = '<session_uuid>';
```
Esperar entry com score baixo + flagged_claims.

3. Verificar que icone amarelo ⚠ apareceu na linha do subagent no chat.

---

## Checkpoint Fase 4

- [ ] **Suite completa**

```bash
pytest tests/agente/ -v --maxfail=5
```

Expected: todos passam (~50+ testes entre fase 1-4).

- [ ] **Rollout gradual em producao**

Habilitar uma flag por vez no Render:

```bash
# Dia 1
AGENT_SUBAGENT_DEBUG_ENDPOINT=true
# Dia 2 (apos observar 24h)
AGENT_SUBAGENT_COST_GRANULAR=true
# Dia 3
AGENT_SUBAGENT_UI=true
# Dia 4
AGENT_SUBAGENT_MEMORY_MINING=true
# Dia 5
AGENT_SUBAGENT_VALIDATION=true
```

Monitorar em cada dia:
- Sentry: `python-flask` projeto, buscar `agent_sdk` / `subagent` tags
- Render metrics: CPU/memory/latencia do servico
- Logs: `[HOOK:SubagentStop]`, `[validator]`, `[SSE]`

- [ ] **Pausa para revisao humana** — Fase 4 completa. Feature entregue.

---

## Self-Review do Plano

**Spec coverage**:
- Secao 3 (Arquitetura): coberta por Task 1.1 + 1.2 + 2.1 + 2.2
- Secao 4.1 (Grupo A — #1, #3, #5): Tasks 1.4 + 1.5 + 1.6 + 2.6
- Secao 4.2 (Grupo B — #6): Tasks 2.1, 2.2, 2.3, 2.4, 2.5
- Secao 4.3 (Grupo C — #2): Tasks 3.1, 3.2
- Secao 4.4 (Grupo D — #4): Tasks 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
- Secao 5 (Feature flags): Task 1.3
- Secao 7 (Testing): TDD em cada task + checkpoints
- Secao 8 (Rollback): checkpoint fase 4 (rollout gradual)

**Placeholder scan**:
- Task 1.6 step 8: "localizacao exata depende da estrutura atual" — aceitavel com instrucao para consultar padrao existente
- Task 2.6 step 3: "a variavel exata que contem o prompt formatado depende" — idem, aceitavel
- Task 3.1: "Se houver consumidores Python, adicionar wrapper" — condicional aceitavel

**Type consistency**:
- `SubagentSummary` dataclass: usado consistentemente em Tasks 1.1, 1.4, 2.1, 2.3, 4.1
- `subagent_summary` event type: Tasks 2.1, 2.2, 2.5, 2.7
- `subagent_validation` event type: Tasks 4.1, 4.4, 4.5
- `USE_SUBAGENT_*` flags: todas declaradas em 1.3, consumidas nas tasks relevantes
- `get_subagent_summary(session_id, agent_id, agent_type='', include_pii=False, max_tool_chars=500)`: assinatura consistente

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-16-agent-sdk-0160-features.md`.**

Para executar, duas opcoes:

**1. Subagent-Driven (recomendado)** — dispatch fresh subagent por task, review entre tasks, iteracao rapida. Usa `superpowers:subagent-driven-development`.

**2. Inline Execution** — executa tasks nesta sessao com checkpoints por fase. Usa `superpowers:executing-plans`.

Qual abordagem?
