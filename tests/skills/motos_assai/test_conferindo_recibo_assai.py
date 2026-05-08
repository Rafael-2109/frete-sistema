"""Testes para conferindo-recibo-assai skill (READ + WRITE)."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[3]
    / '.claude/skills/conferindo-recibo-assai/scripts/conferindo_recibo_assai.py'
)


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=30,
    )


def _parse_json_stdout(stdout: str) -> dict:
    """Extrai JSON do stdout (skips prints de boot do app)."""
    lines = stdout.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('{'):
            return json.loads('\n'.join(lines[i:]))
    raise ValueError(f'No JSON found. stdout: {stdout[:300]!r}')


def test_listar_pendentes_read(app):
    """READ --listar-pendentes deve retornar JSON com chave 'recibos'."""
    r = _run('--listar-pendentes')
    assert r.returncode == 0, f'stderr: {r.stderr}'
    data = _parse_json_stdout(r.stdout)
    assert data.get('modo') == 'listar_pendentes'
    assert 'recibos' in data
    assert isinstance(data['recibos'], list)
    assert 'total' in data


def test_recibo_inexistente_read(app):
    """READ --recibo-id inexistente retorna encontrado=false sem erro."""
    r = _run('--recibo-id', '999999')
    assert r.returncode == 0
    data = _parse_json_stdout(r.stdout)
    assert data.get('modo') == 'detalhe_recibo'
    assert data.get('encontrado') is False


def test_write_sem_user_id_falha(app):
    """WRITE --registrar-chassi sem --user-id deve falhar com exit != 0."""
    r = _run(
        '--registrar-chassi', '--recibo-id', '1',
        '--chassi', 'TESTCHASSI', '--modelo-id', '1', '--cor', 'BRANCA',
    )
    assert r.returncode != 0
    data = _parse_json_stdout(r.stdout)
    assert data.get('ok') is False
    assert 'user-id' in data.get('error', '').lower()


def test_write_dry_run_default(app):
    """WRITE sem --confirmar deve retornar dry_run=true e exit_code=4."""
    r = _run(
        '--registrar-chassi', '--recibo-id', '1',
        '--chassi', 'DRYRUNCHASSI', '--modelo-id', '1', '--cor', 'BRANCA',
        '--user-id', '1',
    )
    # exit_code 4 (dry-run) ou 3 (autorizacao falhou em ambiente vazio sem user)
    assert r.returncode in (3, 4)
    data = _parse_json_stdout(r.stdout)
    assert data.get('modo') == 'registrar_chassi'
    if r.returncode == 4:
        assert data.get('dry_run') is True
        assert 'preview' in data
        assert data['preview'].get('chassi') == 'DRYRUNCHASSI'


def test_help():
    """Script deve responder --help com exit 0."""
    r = _run('--help')
    assert r.returncode == 0
    assert 'conferindo_recibo_assai' in r.stdout.lower() or '--listar-pendentes' in r.stdout
