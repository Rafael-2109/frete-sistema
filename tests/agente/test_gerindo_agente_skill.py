"""
Cobertura deterministica da skill `gerindo-agente` (scripts CLI).

Por que pytest e nao evals LLM: Rafael vetou evals.json/trigger por custo
(memoria feedback_evals_llm_caros_preferir_pytest). A cobertura sancionada da
skill e este pytest — ZERO DB, ZERO token, ZERO create_app:

- os 6 scripts importam `app` apenas LAZY (dentro de funcoes), entao carregar o
  modulo via importlib executa so o top-level (SUBCOMMANDS/HANDLERS/defs).
- valida o CONTRATO estrutural (subcomandos registrados, handlers callable,
  safety das destrutivas, escopo --all) e os bugfixes da Onda 1.

Roda com: `pytest tests/agente/test_gerindo_agente_skill.py`
"""

import importlib.util
import inspect
import sys
from pathlib import Path

import pytest

SKILL_SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / '.claude' / 'skills' / 'gerindo-agente' / 'scripts'
)

SCRIPTS = ['common', 'memoria', 'sessao', 'padrao', 'grafo', 'diagnostico', 'manutencao']

# Onda 1 (camada de evolucao/qualidade) — subcomandos novos em diagnostico.py.
NOVOS_DIAGNOSTICO = {'step-quality', 'step-coverage', 'rule-adhesion', 'routing', 'recommendations'}


def _load(name):
    """Carrega um script da skill como modulo isolado (sem create_app)."""
    # Os scripts fazem `from common import ...` — precisa do dir no sys.path.
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    spec = importlib.util.spec_from_file_location(
        f"gerindo_{name}", SKILL_SCRIPTS / f"{name}.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize('name', SCRIPTS)
def test_script_importavel(name):
    """Todo script carrega sem erro de sintaxe/import (top-level limpo)."""
    mod = _load(name)
    assert mod is not None


@pytest.mark.parametrize('name', ['memoria', 'sessao', 'padrao', 'grafo', 'diagnostico', 'manutencao'])
def test_subcommands_e_handlers_em_paridade(name):
    """SUBCOMMANDS e HANDLERS NUNCA podem divergir (subcomando sem handler = crash)."""
    mod = _load(name)
    subcommands = set(mod.SUBCOMMANDS)
    handlers = set(mod.HANDLERS)
    assert subcommands == handlers, (
        f"{name}: SUBCOMMANDS e HANDLERS divergem: "
        f"so em SUBCOMMANDS={subcommands - handlers}, so em HANDLERS={handlers - subcommands}"
    )
    for sub, fn in mod.HANDLERS.items():
        assert callable(fn), f"{name}: handler de '{sub}' nao e callable"


def test_diagnostico_onda1_registrada():
    """Os 5 subcomandos da Onda 1 estao registrados e com handler callable."""
    d = _load('diagnostico')
    assert NOVOS_DIAGNOSTICO <= set(d.SUBCOMMANDS), (
        f"faltam em SUBCOMMANDS: {NOVOS_DIAGNOSTICO - set(d.SUBCOMMANDS)}"
    )
    assert NOVOS_DIAGNOSTICO <= set(d.HANDLERS), (
        f"faltam em HANDLERS: {NOVOS_DIAGNOSTICO - set(d.HANDLERS)}"
    )


def test_diagnostico_onda1_contrato_de_args():
    """Cada subcomando da Onda 1 declara --days e --all (escopo sistema vs usuario)."""
    d = _load('diagnostico')
    for sub in NOVOS_DIAGNOSTICO:
        argnames = {a['name'] for a in d.SUBCOMMANDS[sub]['args']}
        assert '--days' in argnames, f"{sub} sem --days"
        assert '--all' in argnames, f"{sub} sem --all"


def test_scope_uid_resolve_all_vs_usuario():
    """--all => escopo None (sistema inteiro); senao o --user-id. Default seguro: o usuario."""
    d = _load('diagnostico')

    class _Args:
        pass

    a = _Args()
    a.user_id = 5
    a.all_users = False
    assert d._scope_uid(a) == 5

    a.all_users = True
    assert d._scope_uid(a) is None

    # Flag ausente nao deve quebrar (getattr default False => escopo do usuario).
    b = _Args()
    b.user_id = 7
    assert d._scope_uid(b) == 7


def test_manutencao_summarize_bugfix():
    """BUGFIX Onda 1: handle_summarize usa summarize_and_save(app, session_id, user_id),
    NAO summarize_session(app, ...) (assinatura real e summarize_session(messages, session_id))."""
    m = _load('manutencao')
    src = inspect.getsource(m.handle_summarize)
    # Ignora comentarios (o comentario do bugfix menciona a funcao antiga de proposito).
    code = '\n'.join(l for l in src.splitlines() if not l.lstrip().startswith('#'))
    assert 'summarize_and_save(' in code, "deve chamar o orquestrador summarize_and_save"
    assert 'summarize_session(' not in code, (
        "bug antigo: summarize_session(app, ...) tem assinatura errada (TypeError)"
    )


def test_destrutivas_exigem_confirm():
    """Contrato de seguranca: delete/clear de memoria e delete de sessao exigem --confirm."""
    mem = _load('memoria')
    for sub in ['delete', 'clear']:
        names = {a['name'] for a in mem.SUBCOMMANDS[sub]['args']}
        assert '--confirm' in names, f"memoria.{sub} deveria exigir --confirm"

    ses = _load('sessao')
    names = {a['name'] for a in ses.SUBCOMMANDS['delete']['args']}
    assert '--confirm' in names, "sessao.delete deveria exigir --confirm"
