"""Testes para rastreando-chassi-assai."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / '.claude/skills/rastreando-chassi-assai/scripts/rastreando_chassi_assai.py'


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


def test_chassi_inexistente_retorna_nao_encontrado(app):
    r = _run('--chassi', 'CHASSI_QUE_NAO_EXISTE')
    assert r.returncode == 0
    data = _parse_json_stdout(r.stdout)
    assert data.get('encontrado') is False


def test_chassi_obrigatorio():
    r = _run()  # sem --chassi
    assert r.returncode != 0


def test_help():
    r = _run('--help')
    assert r.returncode == 0
