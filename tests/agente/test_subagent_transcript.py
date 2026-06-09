"""Testes para get_subagent_transcript — timeline cronologica completa.

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (5.1)
"""
import json
import shutil
from pathlib import Path

import pytest
from unittest.mock import MagicMock

from app.agente.sdk.subagent_reader import (
    get_subagent_transcript,
    SubagentTranscriptEntry,
)


def _fake_messages_for_test():
    """4 mensagens mock: user prompt -> assistant tool_use -> tool_result -> assistant final."""
    return [
        # User prompt (parent -> subagent)
        MagicMock(
            type='user',
            uuid='u1',
            message={
                'role': 'user',
                'content': 'Analise pedido VCD123 com regras P1-P7. Cliente CPF 123.456.789-00.'
            },
        ),
        # Assistant: tool_use
        MagicMock(
            type='assistant',
            uuid='a1',
            message={
                'role': 'assistant',
                'content': [
                    {'type': 'text', 'text': 'Vou consultar o pedido.'},
                    {'type': 'tool_use', 'id': 'tu_1', 'name': 'Bash',
                     'input': {'command': 'psql -c SELECT'}},
                ],
                'usage': {'input_tokens': 100, 'output_tokens': 50},
            },
        ),
        # User: tool_result
        MagicMock(
            type='user',
            uuid='u2',
            message={
                'role': 'user',
                'content': [
                    {'type': 'tool_result', 'tool_use_id': 'tu_1',
                     'content': 'pedido VCD123 prioridade P3', 'is_error': False}
                ],
            },
        ),
        # Assistant: text final
        MagicMock(
            type='assistant',
            uuid='a2',
            message={
                'role': 'assistant',
                'content': [
                    {'type': 'text', 'text': 'Pedido VCD123 e P3 porque atende criterio X.'}
                ],
                'usage': {'input_tokens': 200, 'output_tokens': 80},
            },
        ),
    ]


@pytest.fixture
def mocked_sdk_messages(monkeypatch):
    """Mocka get_subagent_messages do SDK."""
    monkeypatch.setattr(
        'app.agente.sdk.subagent_reader.get_subagent_messages',
        lambda sid, aid, **kw: _fake_messages_for_test()
    )


def test_transcript_inclui_prompt_inicial(mocked_sdk_messages):
    """1a UserMessage do JSONL = user_prompt na timeline."""
    entries = get_subagent_transcript('a' * 32, 'b' * 32, include_pii=True)
    assert len(entries) >= 1
    first = entries[0]
    assert first.kind == 'user_prompt'
    assert 'VCD123' in first.content
    assert first.sequence == 1


def test_transcript_ordenacao_cronologica(mocked_sdk_messages):
    """sequence cresce monotonicamente."""
    entries = get_subagent_transcript('a' * 32, 'b' * 32, include_pii=True)
    seqs = [e.sequence for e in entries]
    assert seqs == sorted(seqs)
    assert seqs[0] == 1


def test_transcript_correlaciona_tool_use_tool_result(mocked_sdk_messages):
    """tool_use_id linka tool_use -> tool_result."""
    entries = get_subagent_transcript('a' * 32, 'b' * 32, include_pii=True)
    tool_uses = [e for e in entries if e.kind == 'tool_use']
    tool_results = [e for e in entries if e.kind == 'tool_result']
    assert len(tool_uses) >= 1
    assert len(tool_results) >= 1
    # Ambos devem ter o mesmo tool_use_id
    assert tool_uses[0].tool_use_id == 'tu_1'
    assert tool_results[0].tool_use_id == 'tu_1'


def test_transcript_mask_pii_quando_include_pii_false(mocked_sdk_messages):
    """CPF mascarado em entries quando flag off."""
    entries = get_subagent_transcript('a' * 32, 'b' * 32, include_pii=False)
    prompt = entries[0].content
    # CPF nao deve aparecer raw
    assert '123.456.789-00' not in prompt


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
    entries = get_subagent_transcript('a' * 32, '../etc/passwd')
    assert entries == []


def test_transcript_respeitar_max_content_chars(mocked_sdk_messages):
    """Content > max e truncado por entry."""
    entries = get_subagent_transcript(
        'a' * 32, 'b' * 32,
        include_pii=True,
        max_content_chars=20,
    )
    for e in entries:
        if isinstance(e.content, str):
            # Allow margin pra ellipsis "...[truncado]" sufixo
            assert len(e.content) <= 20 + 20


def test_transcript_assistant_text_block_extraido(mocked_sdk_messages):
    """assistant text block aparece como kind=assistant_text."""
    entries = get_subagent_transcript('a' * 32, 'b' * 32, include_pii=True)
    texts = [e for e in entries if e.kind == 'assistant_text']
    assert len(texts) >= 1
    assert any('P3' in t.content for t in texts)


def test_transcript_to_dict_serializavel():
    """SubagentTranscriptEntry.to_dict retorna estrutura JSON-safe."""
    e = SubagentTranscriptEntry(
        sequence=1, kind='user_prompt', timestamp=None,
        content='test', tool_use_id=None,
    )
    d = e.to_dict()
    # Deve ser JSON-serializavel
    json.dumps(d)
    assert d['sequence'] == 1
    assert d['kind'] == 'user_prompt'


# ── BUG #5: transcript recupera do S3 quando /tmp efemero foi apagado ──────────

def test_transcript_recupera_do_s3_quando_tmp_vazio(monkeypatch):
    """O /tmp do Render e apagado entre deploys. get_subagent_transcript deve
    tentar restore_session_from_s3() e re-buscar no diretorio restaurado ANTES
    de retornar [] — espelhando list_session_subagents."""
    sid = 'a' * 32
    aid = 'b' * 32
    restore_dir = Path('/tmp/agent_archive_restore') / sid
    shutil.rmtree(restore_dir, ignore_errors=True)

    # Candidates vazios; mensagens SO quando buscadas no diretorio restaurado.
    def fake_get_messages(s, a, **kw):
        if 'agent_archive_restore' in str(kw.get('directory') or ''):
            return _fake_messages_for_test()
        return []
    monkeypatch.setattr(
        'app.agente.sdk.subagent_reader.get_subagent_messages', fake_get_messages
    )

    # restore_session_from_s3 -> True e materializa o diretorio esperado.
    def fake_restore(s):
        (Path('/tmp/agent_archive_restore') / s).mkdir(parents=True, exist_ok=True)
        return True
    monkeypatch.setattr(
        'app.agente.sdk.session_archive.restore_session_from_s3', fake_restore
    )

    try:
        entries = get_subagent_transcript(sid, aid, include_pii=True)
        assert len(entries) >= 1, 'deveria recuperar transcript do S3'
        assert any(
            isinstance(e.content, str) and 'VCD123' in e.content for e in entries
        )
    finally:
        shutil.rmtree(restore_dir, ignore_errors=True)


def test_transcript_sem_s3_continua_retornando_vazio(monkeypatch):
    """Quando restore falha (USE_S3=false/sem archive), mantem o contrato []."""
    monkeypatch.setattr(
        'app.agente.sdk.subagent_reader.get_subagent_messages',
        lambda s, a, **kw: []
    )
    monkeypatch.setattr(
        'app.agente.sdk.session_archive.restore_session_from_s3',
        lambda s: False
    )
    entries = get_subagent_transcript('c' * 32, 'd' * 32)
    assert entries == []
