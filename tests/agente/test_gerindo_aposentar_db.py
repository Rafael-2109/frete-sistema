"""T1.4 — teste DB-bound do subcomando `memoria.py aposentar` (gerindo-agente).

Contrato coberto (pelo caminho REAL main() -> handler, via subprocess):
  1. dry-run (default, sem --confirmar) NAO muta a memoria;
  2. --confirmar muta: is_cold=True + meta['promovida_para'] + versao criada
     (AgentMemoryVersion via save_version ANTES da mutacao).

Padrao espelhado de test_gerindo_agente_snapshots.py: SKIPa com graca sem
DATABASE_URL postgres no .env (fast-path ZERO-DB fica em
test_gerindo_agente_skill.py). A memoria de teste e criada e removida pelo
proprio teste (user_id=1, path proprio — nao toca memorias reais).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / '.claude' / 'skills' / 'gerindo-agente' / 'scripts'

TEST_USER_ID = '1'
TEST_PATH = '/memories/system/t14_aposentar_smoke_test.xml'
TEST_ARTEFATO = '.claude/references/EXEMPLO_T14.md'


def _database_url():
    env_file = REPO / '.env'
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = line.strip()
        if line.startswith('DATABASE_URL=') and 'postgres' in line:
            return line.split('=', 1)[1].strip()
    return None


def _run(script, args, db_url):
    """Roda subcomando via subprocess (cwd=raiz) e devolve (exit, stdout)."""
    cmd = [sys.executable, str(SCRIPTS / f"{script}.py"), *args]
    env = dict(os.environ)
    env['DATABASE_URL'] = db_url
    env['SKIP_DB_CREATE'] = 'true'
    env['TESTING'] = 'false'
    proc = subprocess.run(cmd, cwd=str(REPO), env=env,
                          capture_output=True, text=True, timeout=180)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _json_payload(out):
    """Extrai o ultimo bloco JSON do stdout (scripts imprimem so o JSON em --json)."""
    start = max(out.rfind('\n{'), out.rfind('\n['))
    return json.loads(out[start + 1:] if start >= 0 else out)


@pytest.fixture(scope='module')
def db_url():
    url = _database_url()
    if not url:
        pytest.skip("Sem DATABASE_URL postgres no .env — teste requer banco local.")
    return url


@pytest.fixture()
def memoria_teste(db_url):
    """Cria a memoria de teste e garante cleanup (delete --confirm) ao final."""
    rc, out, err = _run('memoria', [
        'save', '--user-id', TEST_USER_ID, '--path', TEST_PATH,
        '--content', 'T1.4 smoke: memoria descartavel para teste de aposentadoria.',
        '--skip-dedup', '--json',
    ], db_url)
    assert rc == 0, f"setup save falhou: {err or out}"
    yield TEST_PATH
    _run('memoria', ['delete', '--user-id', TEST_USER_ID, '--path', TEST_PATH,
                     '--confirm'], db_url)


def _view(db_url):
    rc, out, err = _run('memoria', ['view', '--user-id', TEST_USER_ID,
                                    '--path', TEST_PATH, '--json'], db_url)
    assert rc == 0, f"view falhou: {err or out}"
    return _json_payload(out)


def _versions_count(db_url):
    rc, out, err = _run('memoria', ['versions', '--user-id', TEST_USER_ID,
                                    '--path', TEST_PATH, '--json'], db_url)
    assert rc == 0, f"versions falhou: {err or out}"
    return _json_payload(out).get('total_versions', 0)


def test_aposentar_dry_run_nao_muta_e_confirmar_muta(db_url, memoria_teste):
    # Estado inicial: nao-cold, sem versoes.
    antes = _view(db_url)
    assert antes['is_cold'] is False
    versoes_antes = _versions_count(db_url)

    # 1) dry-run (default): exit 0, NADA muda.
    rc, out, err = _run('memoria', [
        'aposentar', '--user-id', TEST_USER_ID, '--path', TEST_PATH,
        '--promovida-para', TEST_ARTEFATO, '--json',
    ], db_url)
    assert rc == 0, f"aposentar dry-run falhou: {err or out}"
    payload = _json_payload(out)
    assert payload.get('dry_run') is True
    depois_dry = _view(db_url)
    assert depois_dry['is_cold'] is False, "dry-run NAO pode mutar is_cold"
    assert _versions_count(db_url) == versoes_antes, "dry-run NAO pode criar versao"

    # 2) --confirmar: muta is_cold + meta.promovida_para + cria versao.
    rc, out, err = _run('memoria', [
        'aposentar', '--user-id', TEST_USER_ID, '--path', TEST_PATH,
        '--promovida-para', TEST_ARTEFATO, '--confirmar', '--json',
    ], db_url)
    assert rc == 0, f"aposentar --confirmar falhou: {err or out}"
    payload = _json_payload(out)
    assert payload.get('dry_run') is False
    assert payload['after']['is_cold'] is True
    assert payload['after']['promovida_para'] == TEST_ARTEFATO
    depois = _view(db_url)
    assert depois['is_cold'] is True, "--confirmar deve setar is_cold=True"
    assert _versions_count(db_url) == versoes_antes + 1, (
        "--confirmar deve versionar o conteudo ANTES de mutar"
    )


def test_aposentar_path_inexistente_erro_limpo(db_url):
    rc, out, err = _run('memoria', [
        'aposentar', '--user-id', TEST_USER_ID,
        '--path', '/memories/system/nao_existe_t14.xml',
        '--promovida-para', TEST_ARTEFATO,
    ], db_url)
    assert rc != 0, "path inexistente deve falhar"
    assert 'nao encontrada' in (err + out).lower()
