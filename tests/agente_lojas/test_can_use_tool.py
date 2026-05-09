"""Testes do can_use_tool callback do Agente Lojas HORA.

Cobre:
    - Bash com pattern destrutivo eh negado
    - Bash seguro eh permitido
    - Write/Edit fora de /tmp eh negado
    - Write/Edit em /tmp eh permitido
    - AskUserQuestion sem session_id eh negado
    - AskUserQuestion sem event_queue eh negado (graceful)
"""
import asyncio
import pytest

from claude_agent_sdk import (
    PermissionResultAllow,
    PermissionResultDeny,
)

from app.agente_lojas.config.permissions import (
    can_use_tool,
    set_current_session_id,
    set_event_queue,
    cleanup_session_context,
    _DANGEROUS_BASH_PATTERNS,
)


def _run(coro):
    """Helper para rodar coroutine em test sync."""
    return asyncio.get_event_loop().run_until_complete(coro) \
        if not asyncio.iscoroutine(coro) else asyncio.new_event_loop().run_until_complete(coro)


class TestBashPatterns:
    """Patterns destrutivos em Bash devem ser bloqueados."""

    @pytest.mark.parametrize("dangerous_cmd", [
        "DROP TABLE hora_moto",
        "drop table hora_moto;",
        "DELETE FROM hora_pedido WHERE 1=1",
        "rm -rf /tmp",
        "rm -fr /var",
        "TRUNCATE hora_moto_evento",
        "DROP DATABASE frete_sistema",
        "mkfs.ext4 /dev/sda1",
        "dd if=/dev/zero of=/dev/sda",
    ])
    def test_dangerous_bash_negado(self, dangerous_cmd):
        result = asyncio.new_event_loop().run_until_complete(
            can_use_tool('Bash', {'command': dangerous_cmd}, None)
        )
        assert isinstance(result, PermissionResultDeny), \
            f"Comando destrutivo deveria ser negado: {dangerous_cmd}"
        assert 'destrutivo' in result.message.lower() or \
               'bloqueado' in result.message.lower()

    @pytest.mark.parametrize("safe_cmd", [
        "ls /tmp",
        "python -c 'print(1)'",
        "psql -c 'SELECT * FROM hora_moto LIMIT 5'",  # SELECT eh seguro
        "echo hello",
        "git status",
    ])
    def test_safe_bash_permitido(self, safe_cmd):
        result = asyncio.new_event_loop().run_until_complete(
            can_use_tool('Bash', {'command': safe_cmd}, None)
        )
        assert isinstance(result, PermissionResultAllow), \
            f"Comando seguro deveria ser permitido: {safe_cmd}"

    def test_dangerous_patterns_count(self):
        """_DANGEROUS_BASH_PATTERNS deve cobrir patterns minimos esperados."""
        patterns_lower = [p.lower() for p in _DANGEROUS_BASH_PATTERNS]
        for required in ['drop table', 'delete from hora_', 'rm -rf']:
            assert any(required in p for p in patterns_lower), \
                f"Pattern obrigatorio ausente: {required}"


class TestWriteEdit:
    """Write/Edit limitados a /tmp."""

    @pytest.mark.parametrize("tool_name", ['Write', 'Edit', 'MultiEdit'])
    @pytest.mark.parametrize("path", [
        '/etc/passwd',
        '/home/user/file.txt',
        '/var/log/app.log',
        '/app/config.py',
    ])
    def test_write_fora_tmp_negado(self, tool_name, path):
        result = asyncio.new_event_loop().run_until_complete(
            can_use_tool(tool_name, {'file_path': path}, None)
        )
        assert isinstance(result, PermissionResultDeny)
        assert '/tmp' in result.message

    @pytest.mark.parametrize("tool_name", ['Write', 'Edit', 'MultiEdit'])
    @pytest.mark.parametrize("path", [
        '/tmp/output.json',
        '/tmp/agente_files/report.txt',
        '/tmp/sub/dir/file.csv',
    ])
    def test_write_em_tmp_permitido(self, tool_name, path):
        result = asyncio.new_event_loop().run_until_complete(
            can_use_tool(tool_name, {'file_path': path}, None)
        )
        assert isinstance(result, PermissionResultAllow)

    def test_write_path_traversal_bloqueado(self):
        """Path traversal via '..' eh normalizado e bloqueado."""
        result = asyncio.new_event_loop().run_until_complete(
            can_use_tool('Write', {'file_path': '/tmp/../etc/passwd'}, None)
        )
        # Apos normpath/abspath, vira /etc/passwd — fora de /tmp
        assert isinstance(result, PermissionResultDeny)


class TestAskUserQuestion:
    """AskUserQuestion: deve ter session_id E event_queue."""

    def test_sem_session_id_negado(self):
        # Garante ContextVar limpa
        try:
            cleanup_session_context('any-session')
        except Exception:
            pass

        result = asyncio.new_event_loop().run_until_complete(
            can_use_tool('AskUserQuestion', {'questions': []}, None)
        )
        assert isinstance(result, PermissionResultDeny)
        assert 'sessao' in result.message.lower() or \
               'session' in result.message.lower()

    def test_sem_event_queue_negado(self):
        """Mesmo com session_id, sem event_queue retorna deny graceful."""
        # Setup: registra session mas sem event_queue
        set_current_session_id('test-session-no-queue')
        try:
            result = asyncio.new_event_loop().run_until_complete(
                can_use_tool(
                    'AskUserQuestion',
                    {'questions': [{'question': 'Q?', 'options': []}]},
                    None,
                )
            )
            assert isinstance(result, PermissionResultDeny)
            assert 'interativ' in result.message.lower()
        finally:
            cleanup_session_context('test-session-no-queue')


class TestOutrasTools:
    """Tools sem regra especifica (Skill, Task, Read, Glob, Grep, TodoWrite)
    devem ser permitidas."""

    @pytest.mark.parametrize("tool_name", [
        'Skill', 'Task', 'Read', 'Glob', 'Grep', 'TodoWrite',
    ])
    def test_outras_tools_permitidas(self, tool_name):
        result = asyncio.new_event_loop().run_until_complete(
            can_use_tool(tool_name, {}, None)
        )
        assert isinstance(result, PermissionResultAllow)
