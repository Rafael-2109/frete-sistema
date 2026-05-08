"""Testes para acompanhando-saida-assai."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / '.claude/skills/acompanhando-saida-assai/scripts/acompanhando_saida_assai.py'


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=30,
    )


def _parse_json_stdout(stdout: str) -> dict:
    lines = stdout.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('{'):
            return json.loads('\n'.join(lines[i:]))
    raise ValueError(f'No JSON found. stdout: {stdout[:300]!r}')


def test_somente_abertas(app):
    r = _run('--somente-abertas')
    assert r.returncode == 0
    data = _parse_json_stdout(r.stdout)
    assert 'separacoes' in data
    assert 'nfs_qpa' in data


def test_help():
    r = _run('--help')
    assert r.returncode == 0
