"""
Regressao TMPDIR (sessao #787, 2026-06-03 — "arquivo vazio" no download de Excel).

INVARIANTE: a GRAVACAO (skill `exportar.py`, que roda como subprocesso Bash do CLI
com TMPDIR=/tmp/claude-{uid}) e a LEITURA (rota de download via
`_constants.UPLOAD_FOLDER`, no gunicorn SEM esse TMPDIR) DEVEM resolver o MESMO
diretorio base. Antes do fix, ambos usavam `tempfile.gettempdir()` e divergiam
(/tmp/claude-{uid}/agente_files na escrita vs /tmp/agente_files na leitura) -> 404.
Fix: ambos os lados usam `AGENTE_FILES_ROOT` (default /tmp), ignorando TMPDIR.

Carrega os modulos por path (importlib) para NAO puxar o pacote `app` inteiro
(evita create_app/DATABASE_URL). Roda via pytest OU standalone (`python <arquivo>`).
"""
import os
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PATHS = {
    'constants': os.path.join(ROOT, 'app/agente/routes/_constants.py'),
    'exportar': os.path.join(ROOT, '.claude/skills/exportando-arquivos/scripts/exportar.py'),
    'ler': os.path.join(ROOT, '.claude/skills/lendo-arquivos/scripts/ler.py'),
    'ler_doc': os.path.join(ROOT, '.claude/skills/lendo-documentos/scripts/ler_doc.py'),
}


def _load(key, suffix=''):
    spec = importlib.util.spec_from_file_location(f'_aft_{key}{suffix}', PATHS[key])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _set_env(tmpdir_val, root_val):
    for var, val in (('TMPDIR', tmpdir_val), ('AGENTE_FILES_ROOT', root_val)):
        if val is None:
            os.environ.pop(var, None)
        else:
            os.environ[var] = val


def test_default_ignora_tmpdir_do_cli():
    # CLI seta TMPDIR=/tmp/claude-1000; sem AGENTE_FILES_ROOT o base e /tmp (gunicorn).
    _set_env('/tmp/claude-1000', None)
    c = _load('constants', '_a')
    assert c.UPLOAD_FOLDER == '/tmp/agente_files', c.UPLOAD_FOLDER


def test_gravacao_e_leitura_apontam_o_mesmo_base():
    # TMPDIR divergente (como no subprocesso CLI) NAO pode afetar o base resolvido.
    import tempfile as _t
    shared = os.path.join(_t.mkdtemp(), 'shared')
    _set_env(os.path.join(_t.mkdtemp(), 'cli-claude-1000'), shared)
    c = _load('constants', '_b')
    exportar = _load('exportar', '_b')
    base_leitura = c.UPLOAD_FOLDER                                 # rota (gunicorn)
    base_escrita = os.path.dirname(exportar.get_upload_folder())   # skill (CLI subproc)
    esperado = os.path.join(shared, 'agente_files')
    assert base_leitura == esperado, base_leitura
    assert base_escrita == esperado, base_escrita
    assert base_leitura == base_escrita  # invariante: download encontra o arquivo


def test_skills_de_leitura_encontram_arquivo_gravado():
    # Simula upload gravado em {root}/agente_files/default e confere que as skills
    # de leitura (ler.py / ler_doc.py) resolvem o MESMO caminho mesmo com TMPDIR != root.
    import tempfile as _t
    shared = os.path.join(_t.mkdtemp(), 'shared')
    _set_env(os.path.join(_t.mkdtemp(), 'cli'), shared)
    base = os.path.join(shared, 'agente_files', 'default')
    os.makedirs(base, exist_ok=True)
    fpath = os.path.join(base, 'x.csv')
    with open(fpath, 'w') as f:
        f.write('a,b\n1,2\n')
    ler = _load('ler', '_c')
    ler_doc = _load('ler_doc', '_c')
    assert ler.url_para_caminho('/agente/api/files/default/x.csv') == fpath
    assert ler_doc.url_para_caminho('/agente/api/files/default/x.csv') == fpath


if __name__ == '__main__':
    _failures = 0
    for _name, _fn in sorted(globals().items()):
        if _name.startswith('test_') and callable(_fn):
            try:
                _fn()
                print(f'PASS {_name}')
            except AssertionError as _e:
                _failures += 1
                print(f'FAIL {_name}: {_e}')
            except Exception as _e:  # noqa: BLE001
                _failures += 1
                print(f'ERROR {_name}: {type(_e).__name__}: {_e}')
    raise SystemExit(1 if _failures else 0)
