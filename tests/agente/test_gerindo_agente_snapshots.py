"""
Rede de seguranca P12 (Onda 2) — SNAPSHOT do shape `--json` dos subcomandos READ
da skill `gerindo-agente`.

Por que existe: a Onda 2 refatora `common.py` (P8: run_handler / success_output /
format_datetime). Este snapshot trava o CONTRATO de saida (esqueleto de tipos das
chaves, NAO os valores) ANTES do refactor, para que uma regressao acidental no
caminho real `main()` -> handler -> format_json seja detectada.

Caracteristicas (deliberadas):
- DB-BOUND e FIEL: cada subcomando roda via subprocess pelo MESMO caminho de
  producao (`python <script>.py <sub> --user-id N --json`). E exatamente o codigo
  que o P8 altera. Por isso NAO usa o caminho in-process (que pularia main()).
- SKIPa com graca quando nao ha banco local (sem .env / DATABASE_URL postgres /
  conexao). Assim o fast-path ZERO-DB (test_gerindo_agente_skill.py) nunca quebra.
- Cobre SO subcomandos READ de shape ESTAVEL (envelope fixo). Destrutivos, que
  chamam Sonnet, ou cujo shape depende de exists/nao-exists ficam de fora — esses
  sao cobertos pelo contrato deterministico em test_gerindo_agente_skill.py.
- Comparacao TOLERANTE a dados: lista vazia (`<empty>`) casa com qualquer shape de
  lista; `null` casa com qualquer tipo (campos nullable). Detecta chave
  adicionada/removida/retipada — que e o que um refactor de common.py poderia quebrar.

Regravar o golden (apos mudanca INTENCIONAL de shape):
    GERINDO_SNAPSHOT_RECORD=1 pytest tests/agente/test_gerindo_agente_snapshots.py

Rodar (precisa do banco local postgres via .env):
    pytest tests/agente/test_gerindo_agente_snapshots.py -v
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / '.claude' / 'skills' / 'gerindo-agente' / 'scripts'
GOLDEN = Path(__file__).resolve().parent / 'snapshots' / 'gerindo_agente_json_shapes.json'

# user_id com dados no banco local (Rafael). Apenas para EXERCITAR os ramos; o
# snapshot compara SHAPE, nunca valores — entao qual usuario nao muda o contrato.
SNAPSHOT_USER_ID = int(os.environ.get('GERINDO_SNAPSHOT_USER_ID', '1'))
RECORD = os.environ.get('GERINDO_SNAPSHOT_RECORD') == '1'

# Subcomandos READ de shape ESTAVEL (script, subcomando, args extras).
# Ordem: agrupada por script. NAO incluir destrutivos nem exists/nao-exists.
READ_CASES = [
    # diagnostico — camada classica + camada de evolucao (Onda 1) + status (Onda 2)
    ('diagnostico', 'insights', ['--days', '30']),
    ('diagnostico', 'memory-metrics', ['--days', '30']),
    ('diagnostico', 'health', ['--days', '30']),
    ('diagnostico', 'effectiveness', []),
    ('diagnostico', 'cold-candidates', []),
    ('diagnostico', 'conflicts', []),
    ('diagnostico', 'embedding-coverage', []),
    ('diagnostico', 'friction', ['--days', '30']),
    ('diagnostico', 'briefing', []),
    ('diagnostico', 'step-quality', ['--days', '30']),
    ('diagnostico', 'step-coverage', ['--days', '30']),
    ('diagnostico', 'rule-adhesion', ['--days', '30']),
    ('diagnostico', 'routing', ['--days', '30']),
    ('diagnostico', 'recommendations', ['--days', '30']),
    ('diagnostico', 'status', ['--days', '30']),
    # memoria
    ('memoria', 'list', []),
    ('memoria', 'search-cold', ['--query', 'frete']),
    ('memoria', 'stats', []),
    # sessao
    ('sessao', 'list', []),
    ('sessao', 'users', []),
    ('sessao', 'search', ['--query', 'frete']),
    # padrao
    ('padrao', 'empresa', []),
    # grafo
    ('grafo', 'entities', []),
    ('grafo', 'relations', []),
    ('grafo', 'stats', []),
    ('grafo', 'query', ['--prompt', 'transportadora']),
]

CASE_IDS = [f"{s}.{sub}" for s, sub, _ in READ_CASES]


# ───────────────────────── esqueleto de tipos ──────────────────────────────

# Dicts cujas CHAVES sao derivadas de DADOS (categorias, escopos, modelos, tipos
# de entidade...) — variam de banco para banco. Colapsamos para o sentinela
# '<map>' para nao gerar falso-positivo quando os dados mudam. Um BUG que troque
# o dict por outro tipo (ex: lista) ainda e pego (skeleton != '<map>').
OPEN_MAP_KEYS = {
    'por_categoria', 'por_escopo', 'by_scope',
    'entities_by_type', 'model_distribution', 'categories',
    'knowledge_type_distribution', 'distribution',
}


def skeleton(obj):
    """Reduz um objeto JSON ao seu esqueleto de tipos (valores descartados).

    dict -> {chave: skeleton(valor)} (chaves ordenadas); chave em OPEN_MAP_KEYS
            com valor dict colapsa para '<map>' (chaves data-driven ignoradas).
    list -> [skeleton mesclado dos elementos] ou ['<empty>'] se vazia
    None -> 'null'   |   escalares -> nome do tipo ('int','float','str','bool')
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in sorted(obj.items()):
            out[k] = '<map>' if (k in OPEN_MAP_KEYS and isinstance(v, dict)) else skeleton(v)
        return out
    if isinstance(obj, list):
        if not obj:
            return ['<empty>']
        if all(isinstance(e, dict) for e in obj):
            merged = {}
            for e in obj:
                for k, v in e.items():
                    merged[k] = skeleton(v)
            return [{k: merged[k] for k in sorted(merged)}]
        return [skeleton(obj[0])]
    if obj is None:
        return 'null'
    if isinstance(obj, bool):
        return 'bool'
    return type(obj).__name__


def diff_skeleton(golden, current, path=''):
    """Lista incompatibilidades golden vs current. Vazia = compativel.

    Tolerancias (data-driven, nao sao regressao):
      - '<empty>' (lista vazia) casa com qualquer shape de lista.
      - 'null' casa com qualquer tipo (campo nullable).
    """
    problems = []

    # Tolerancia a nullability — SO entre escalar/null (campo nullable de dado esparso).
    # NAO tolera null <-> dict/list: trocar um leaf nullable por um SUBTREE (ou vice-versa)
    # e crescimento ESTRUTURAL e DEVE ser pego (falso-negativo fechado, review Onda 2).
    if golden == 'null' and not isinstance(current, (dict, list)):
        return problems
    if current == 'null' and not isinstance(golden, (dict, list)):
        return problems

    if isinstance(golden, dict) and isinstance(current, dict):
        gk, ck = set(golden), set(current)
        for k in sorted(gk - ck):
            problems.append(f"{path or '<root>'}: chave REMOVIDA '{k}'")
        for k in sorted(ck - gk):
            problems.append(f"{path or '<root>'}: chave NOVA '{k}'")
        for k in sorted(gk & ck):
            problems += diff_skeleton(golden[k], current[k], f"{path}.{k}" if path else k)
        return problems

    if isinstance(golden, list) and isinstance(current, list):
        # lista vazia em qualquer lado = wildcard de elemento
        if golden == ['<empty>'] or current == ['<empty>']:
            return problems
        return diff_skeleton(golden[0], current[0], f"{path}[]")

    if golden != current:
        problems.append(f"{path or '<root>'}: tipo mudou {golden!r} -> {current!r}")
    return problems


# ───────────────────────── execucao via subprocess ─────────────────────────

def _database_url():
    """DATABASE_URL postgres do .env da raiz (pytest.ini forca sqlite — inutil aqui)."""
    env_file = REPO / '.env'
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = line.strip()
        if line.startswith('DATABASE_URL=') and 'postgres' in line:
            return line.split('=', 1)[1].strip()
    return None


def _run(script, subcommand, extra_args, db_url):
    """Roda o subcomando via subprocess (cwd=raiz, sem ruido) e devolve o dict --json."""
    cmd = [
        sys.executable, str(SCRIPTS / f"{script}.py"), subcommand,
        '--user-id', str(SNAPSHOT_USER_ID), '--json', *extra_args,
    ]
    env = dict(os.environ)
    env['DATABASE_URL'] = db_url       # sobrepoe o sqlite do pytest.ini
    env['SKIP_DB_CREATE'] = 'true'     # banco local ja tem as tabelas
    env['TESTING'] = 'false'
    proc = subprocess.run(
        cmd, cwd=str(REPO), env=env,
        capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"{script}.{subcommand} exit={proc.returncode}\nSTDERR(tail):\n"
            + '\n'.join(proc.stdout.strip().splitlines()[-5:])
            + '\n' + '\n'.join(proc.stderr.strip().splitlines()[-5:])
        )
    out = proc.stdout.strip()
    # READ subcommands em --json imprimem SO o JSON; pega o ultimo bloco {..}/[..].
    start = max(out.rfind('\n{'), out.rfind('\n['))
    payload = out[start + 1:] if start >= 0 else out
    parsed = json.loads(payload)
    # Hardening (review Onda 2): NAO aceitar shape de ERRO — senao um query_error no
    # momento do RECORD gravaria um contrato errado no golden silenciosamente.
    if isinstance(parsed, dict):
        if parsed.get('status') == 'query_error':
            raise RuntimeError(f"{script}.{subcommand}: handler retornou status=query_error: {parsed.get('error')}")
        if parsed.get('ok') is False and parsed.get('errors'):
            raise RuntimeError(f"{script}.{subcommand}: envelope ok=false errors={parsed.get('errors')}")
    return parsed


@pytest.fixture(scope='session')
def db_url():
    url = _database_url()
    if not url:
        pytest.skip("Sem DATABASE_URL postgres no .env — snapshot requer banco local.")
    return url


@pytest.fixture(scope='session')
def golden():
    if GOLDEN.exists():
        return json.loads(GOLDEN.read_text(encoding='utf-8'))
    return {}


# Acumulador para o modo RECORD (escreve o golden ao final da sessao).
_recorded = {}


@pytest.mark.parametrize('script,subcommand,extra', READ_CASES, ids=CASE_IDS)
def test_json_shape_estavel(script, subcommand, extra, db_url, golden):
    key = f"{script}.{subcommand}"
    # _run levanta RuntimeError com mensagem limpa em exit != 0. NAO silenciamos:
    # um crash do caminho main()/run_handler (alvo do P8) DEVE falhar o snapshot.
    data = _run(script, subcommand, extra, db_url)
    current = skeleton(data)

    if RECORD:
        _recorded[key] = current
        return

    assert key in golden, (
        f"'{key}' ausente do golden. Rode com GERINDO_SNAPSHOT_RECORD=1 para gravar."
    )
    problems = diff_skeleton(golden[key], current)
    assert not problems, (
        f"SHAPE REGREDIU em '{key}':\n  - " + "\n  - ".join(problems)
        + f"\n\nGolden:  {json.dumps(golden[key], ensure_ascii=False)}"
        + f"\nAtual:   {json.dumps(current, ensure_ascii=False)}"
        + "\n\nSe a mudanca for INTENCIONAL: GERINDO_SNAPSHOT_RECORD=1 pytest ..."
    )


@pytest.fixture(scope='session', autouse=True)
def _persist_record():
    yield
    if RECORD and _recorded:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        merged = {}
        if GOLDEN.exists():
            merged = json.loads(GOLDEN.read_text(encoding='utf-8'))
        merged.update(_recorded)
        GOLDEN.write_text(
            json.dumps(merged, indent=2, ensure_ascii=False, sort_keys=True) + '\n',
            encoding='utf-8',
        )
        print(f"\n[snapshot] golden gravado: {len(_recorded)} subcomandos -> {GOLDEN}")
