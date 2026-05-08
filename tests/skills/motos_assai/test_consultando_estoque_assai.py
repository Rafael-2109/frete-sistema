"""Testes para consultando-estoque-assai skill."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / '.claude/skills/consultando-estoque-assai/scripts/consultando_estoque_assai.py'


def _run_script(*args):
    """Executa o script como subprocess e parseia JSON."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=30,
    )
    return result


def _parse_json_stdout(stdout: str) -> dict:
    """Extrai JSON do stdout (skips prints de boot do app).

    JSON sempre e a ultima coisa em stdout e comeca com '{' em coluna 0.
    """
    lines = stdout.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('{'):
            return json.loads('\n'.join(lines[i:]))
    raise ValueError(f'No JSON found. stdout: {stdout[:300]!r}')


def test_resumo_retorna_estrutura_basica(app):
    """Resumo deve retornar JSON com chaves totais/por_modelo/por_cd/motos_pendentes."""
    r = _run_script('--resumo')
    assert r.returncode == 0, f'stderr: {r.stderr}'
    data = _parse_json_stdout(r.stdout)
    assert 'totais' in data
    assert 'por_modelo' in data
    assert 'por_cd' in data
    assert 'motos_pendentes' in data
    assert 'vazio' in data


def test_filtro_modelo_invalido_retorna_vazio(app):
    """Modelo inexistente deve retornar listas vazias com flag vazio=true."""
    r = _run_script('--modelo', 'MODELO_INEXISTENTE_XYZ', '--resumo')
    assert r.returncode == 0
    data = _parse_json_stdout(r.stdout)
    assert data['totais'] == {
        'estoque': 0, 'montada': 0, 'pendente': 0,
        'disponivel': 0, 'separada': 0, 'faturada': 0,
    }


def test_help_funciona():
    """Script deve responder --help."""
    r = _run_script('--help')
    assert r.returncode == 0
    assert 'consultando_estoque_assai' in r.stdout.lower() or '--resumo' in r.stdout
