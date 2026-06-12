"""Gate dev-only (Onda 3 fase 3b): o agente web/Teams NAO pode executar os subcomandos
WRITE da skill gerindo-agente via Bash. `_classify_gerindo_write` (permissions.py) detecta
a invocacao e o branch Bash de can_use_tool a NEGA. Dev (Claude Code CLI) nao passa por
can_use_tool — continua livre.

Importa permissions.py (claude_agent_sdk), NAO cria app nem toca banco.
"""
import pytest

from app.agente.config.permissions import _classify_gerindo_write

B = '.claude/skills/gerindo-agente/scripts'


# ('eval', 'run') removido (estrategia R2, 2026-06-12): subcomando deletado com o eval_runner.
@pytest.mark.parametrize('script,sub', [
    ('loop', 'approve'), ('loop', 'reject'), ('loop', 'promote-batch'),
    ('eval', 'review'), ('melhorias', 'respond'),
])
def test_write_subcomandos_sao_classificados(script, sub):
    """Cada WRITE (com ou sem --confirm) e detectado -> sera NEGADO ao agente web."""
    for extra in ('--confirm', ''):
        cmd = f'python {B}/{script}.py {sub} --user-id 1 {extra}'.strip()
        r = _classify_gerindo_write('Bash', {'command': cmd})
        assert r == {'script': script, 'subcomando': sub}, f"WRITE nao classificado: {cmd}"


@pytest.mark.parametrize('cmd', [
    f'python {B}/loop.py directives --user-id 1',
    f'python {B}/loop.py corrections --user-id 1 --all',
    f'python {B}/loop.py loop-health --user-id 1',
    f'python {B}/eval.py scores --user-id 1',
    f'python {B}/eval.py cases --user-id 1',
    f'python {B}/melhorias.py list-open --user-id 1',
    f'python {B}/melhorias.py show --key X --user-id 1',
    f'python {B}/melhorias.py intelligence-report --user-id 1',
    'python qualquer/outro.py approve --confirm',  # nao e gerindo-agente
    'ls -la .claude/skills/gerindo-agente/',
])
def test_read_e_nao_gerindo_nao_sao_classificados(cmd):
    """Subcomandos READ + comandos fora da skill NAO sao bloqueados (None)."""
    assert _classify_gerindo_write('Bash', {'command': cmd}) is None, f"falso-positivo: {cmd}"


def test_so_bash_e_classificado():
    """Tool != Bash nunca classifica (o WRITE roda via Bash, nao via Skill tool)."""
    assert _classify_gerindo_write('Skill', {'command': f'{B}/loop.py approve --confirm'}) is None
    assert _classify_gerindo_write('Bash', {}) is None  # sem command
