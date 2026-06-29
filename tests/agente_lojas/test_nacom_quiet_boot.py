"""
F1.4: _keep_stream_open (PreToolUse do fork) prefixa cada comando Bash com
`export NACOM_QUIET_BOOT=1; `.

Sem o prefixo, os scripts de skill que fazem `import app` despejam os logs de
boot do Flask/SQLAlchemy no stdout, contaminando o output que o agente tenta
parsear (resultado SQL/JSON). Espelha o agente web (hooks.py:333-354), mas SEM
as vars de auditoria Odoo (dominio Nacom — o agente de lojas nao tem audit hook).
"""
import pytest

from app.agente_lojas.sdk.hooks import _keep_stream_open


@pytest.mark.asyncio
async def test_bash_recebe_prefixo_nacom_quiet_boot():
    out = await _keep_stream_open(
        {'tool_name': 'Bash', 'tool_input': {'command': 'python x.py'}},
        'tuid', None,
    )
    cmd = out['hookSpecificOutput']['updatedInput']['command']
    assert cmd == 'export NACOM_QUIET_BOOT=1; python x.py'
    assert out['continue_'] is True


@pytest.mark.asyncio
async def test_nao_bash_nao_modifica_input():
    out = await _keep_stream_open(
        {'tool_name': 'Read', 'tool_input': {'file_path': '/x'}},
        'tuid', None,
    )
    assert out == {'continue_': True}


@pytest.mark.asyncio
async def test_bash_sem_command_nao_quebra():
    out = await _keep_stream_open(
        {'tool_name': 'Bash', 'tool_input': {}},
        'tuid', None,
    )
    assert out == {'continue_': True}
