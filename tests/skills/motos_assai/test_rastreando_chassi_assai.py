"""Testes para rastreando-chassi-assai."""
import json
import re
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


def test_recibo_origem_so_acessa_atributos_existentes(app):
    """Regressao IMP-2026-06-26-002: o script montava recibo_origem com
    `recibo.data_recebimento`, atributo inexistente em AssaiReciboMotochefe
    (o campo real e `data_recibo`) -> AttributeError / exit_code=2 para todo
    chassi com recibo vinculado. Garante que TODO atributo `recibo.<x>` lido
    do model existe de fato (trava a regressao sem precisar montar dados)."""
    from app.motos_assai.models import AssaiReciboMotochefe  # noqa: F401

    source = SCRIPT.read_text(encoding='utf-8')
    attrs = set(re.findall(r'\brecibo\.([a-z_]+)', source))
    assert attrs, 'esperava acessos recibo.<attr> no script'
    faltando = sorted(a for a in attrs if not hasattr(AssaiReciboMotochefe, a))
    assert not faltando, (
        f'script acessa atributos inexistentes em AssaiReciboMotochefe: {faltando}'
    )
