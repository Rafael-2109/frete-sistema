"""Testes para registrando-evento-moto-assai (skill WRITE)."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / '.claude/skills/registrando-evento-moto-assai/scripts/registrando_evento_moto_assai.py'


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


def test_sem_user_id_falha(app):
    """Sem --user-id argparse deve falhar (required=True)."""
    r = _run('--montar', '--chassi', 'TESTE_CHASSI_X')
    assert r.returncode != 0


def test_dry_run_montar(app):
    """--montar sem --confirmar retorna preview (exit 4) ou 1 se chassi nao existe.

    Comportamento aceitavel: dry-run preview sempre antes de validacao do
    chassi (exit 4). Se em execucao real chassi nao existir e validacao
    intervir antes (exit 1), tambem e aceitavel — ambos validos para
    indicar 'sem efetivacao'.
    """
    r = _run('--montar', '--chassi', 'CHASSI_NAO_EXISTE_TESTE', '--user-id', '1')
    # Nao deve ser 0 (sucesso): nao foi efetivado
    assert r.returncode != 0
    # Aceita exit 4 (dry-run), 1 (validacao) ou 3 (sem autorizacao se user 1 nao puder)
    assert r.returncode in (1, 3, 4), f'returncode={r.returncode}, stdout={r.stdout[:300]}'
    data = _parse_json_stdout(r.stdout)
    if r.returncode == 4:
        assert data.get('dry_run') is True
        assert data.get('comando') == 'montar'
    elif r.returncode == 3:
        assert data.get('tipo_erro') == 'autorizacao'


def test_help():
    """--help deve retornar 0."""
    r = _run('--help')
    assert r.returncode == 0
    # Sanity check: ajuda menciona pelo menos 1 dos comandos
    assert '--montar' in r.stdout or '--separar' in r.stdout


def test_comando_nao_especificado(app):
    """Sem nenhum dos 8 comandos deve falhar."""
    r = _run('--user-id', '1')
    assert r.returncode != 0
    data = _parse_json_stdout(r.stdout)
    assert data.get('ok') is False
