"""Testes para acompanhando-pedido-compra-assai."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / '.claude/skills/acompanhando-pedido-compra-assai/scripts/acompanhando_pedido_compra_assai.py'


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


def test_listar_abertos(app):
    r = _run('--somente-abertos')
    assert r.returncode == 0
    data = _parse_json_stdout(r.stdout)
    assert 'pedidos' in data
    assert 'compras' in data
    assert isinstance(data['pedidos'], list)
    assert isinstance(data['compras'], list)


def test_pedido_inexistente(app):
    r = _run('--pedido-id', '999999')
    assert r.returncode == 0
    data = _parse_json_stdout(r.stdout)
    assert data['pedidos'] == []


def test_help():
    r = _run('--help')
    assert r.returncode == 0
