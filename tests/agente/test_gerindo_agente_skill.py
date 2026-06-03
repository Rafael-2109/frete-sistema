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

SCRIPTS = ['common', 'memoria', 'sessao', 'padrao', 'grafo', 'diagnostico', 'manutencao',
           'loop', 'eval', 'melhorias']

# Onda 1 (camada de evolucao/qualidade) — subcomandos novos em diagnostico.py.
NOVOS_DIAGNOSTICO = {'step-quality', 'step-coverage', 'rule-adhesion', 'routing', 'recommendations'}

# Onda 3 fase 3a (flywheel READ) — scripts novos e seus subcomandos READ.
ONDA3_LOOP = {'directives', 'corrections', 'loop-health'}
ONDA3_EVAL = {'scores', 'cases'}
ONDA3_MELHORIAS = {'list-open', 'show', 'intelligence-report'}

# Onda 3 fase 3b (flywheel WRITE) — subcomandos de ESCRITA, todos atras de --confirm.
ONDA3_WRITE = {
    'loop': {'approve', 'reject', 'promote-batch'},
    'eval': {'review', 'run'},
    'melhorias': {'respond'},
}
ONDA3_READ = {
    'loop': ONDA3_LOOP,
    'eval': ONDA3_EVAL,
    'melhorias': ONDA3_MELHORIAS,
}


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


@pytest.mark.parametrize('name', ['memoria', 'sessao', 'padrao', 'grafo', 'diagnostico', 'manutencao',
                                  'loop', 'eval', 'melhorias'])
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


# ─────────────────────────────────────────────────────────────────────────
# Onda 2 — P7 (status agregador) + P8 (common.py: run_handler / success_output
# envelope / format_datetime TZ-safe + fim do contexto-duplo em padrao).
# Tudo ZERO-DB: importlib + inspect, sem create_app/token.
# ─────────────────────────────────────────────────────────────────────────


def test_diagnostico_status_registrado_onda2():
    """O agregador 'status' (P7) esta registrado, com handler callable e --days/--all."""
    d = _load('diagnostico')
    assert 'status' in d.SUBCOMMANDS, "status ausente de SUBCOMMANDS"
    assert 'status' in d.HANDLERS and callable(d.HANDLERS['status'])
    argnames = {a['name'] for a in d.SUBCOMMANDS['status']['args']}
    assert {'--days', '--all'} <= argnames, f"status sem --days/--all: {argnames}"


def test_status_chama_get_insights_data_uma_vez():
    """P7: o agregador NAO pode reintroduzir a duplicacao — get_insights_data 1x."""
    d = _load('diagnostico')
    src = inspect.getsource(d.handle_status)
    assert src.count('get_insights_data(') == 1, (
        "status deve chamar get_insights_data UMA unica vez e fatiar (nao N vezes)"
    )


def test_common_success_output_envelope():
    """P8: success_output revivido produz o envelope canonico {ok,command,data,warnings,errors}."""
    c = _load('common')
    env = c.success_output('cmd-x', {'a': 1}, json_mode=False, warnings=['w'])
    assert env == {
        'ok': True, 'command': 'cmd-x', 'data': {'a': 1},
        'warnings': ['w'], 'errors': [],
    }
    # ok=False quando ha erros.
    env_err = c.success_output('cmd-y', None, errors=['boom'])
    assert env_err['ok'] is False and env_err['errors'] == ['boom']


def test_common_format_datetime_tz_safe():
    """P8: format_datetime e TZ-safe — naive inalterado, aware convertido para BRT."""
    from datetime import datetime, timezone
    c = _load('common')
    assert c.format_datetime(None) == '-'
    # naive: formatado como esta (convencao Brasil-naive).
    assert c.format_datetime(datetime(2026, 6, 3, 14, 30)) == '03/06/2026 14:30'
    # aware UTC: convertido para America/Sao_Paulo (UTC-3) antes de formatar.
    aware = datetime(2026, 6, 3, 14, 30, tzinfo=timezone.utc)
    assert c.format_datetime(aware) == '03/06/2026 11:30'


def test_common_run_handler_contrato():
    """P8: run_handler existe e expoe o contrato (description, subcommands, handlers, no_resolve)."""
    c = _load('common')
    assert callable(c.run_handler)
    params = inspect.signature(c.run_handler).parameters
    assert list(params)[:3] == ['description', 'subcommands', 'handlers']
    assert 'no_resolve_subcommands' in params
    assert params['no_resolve_subcommands'].default == ()


def test_padrao_sem_contexto_duplo():
    """P8: padrao migrou para run_handler e os 3 handlers usam current_app (sem contexto-duplo)."""
    p = _load('padrao')
    # main() delega a run_handler (nao reabre parse/contexto na mao).
    main_src = inspect.getsource(p.main)
    assert 'run_handler(' in main_src, "padrao.main deveria delegar a run_handler"
    # Os handlers que precisam de app NAO podem mais chamar get_app_context().
    for fn in (p.handle_analyze, p.handle_extract, p.handle_profile):
        src = inspect.getsource(fn)
        code = '\n'.join(l for l in src.splitlines() if not l.lstrip().startswith('#'))
        assert 'get_app_context(' not in code, (
            f"{fn.__name__}: contexto-duplo (get_app_context) deveria ter sido removido"
        )
        assert 'current_app' in code, (
            f"{fn.__name__}: deveria reutilizar o contexto via current_app"
        )
    # padrao nao deve mais importar get_app_context (run_handler cuida do contexto).
    mod_src = inspect.getsource(p)
    assert 'get_app_context' not in mod_src.split('def handle_')[0], (
        "padrao nao deveria mais importar get_app_context"
    )


# ─────────────────────────────────────────────────────────────────────────
# Onda 3 — flywheel WRITE, fase 3a (READ-first): 3 scripts novos
# (loop/eval/melhorias), so subcomandos de LEITURA. Tudo ZERO-DB.
# ─────────────────────────────────────────────────────────────────────────


def test_loop_onda3_registrado():
    """loop.py: directives/corrections/loop-health registrados e callable."""
    m = _load('loop')
    assert ONDA3_LOOP <= set(m.SUBCOMMANDS), f"faltam em SUBCOMMANDS: {ONDA3_LOOP - set(m.SUBCOMMANDS)}"
    assert ONDA3_LOOP <= set(m.HANDLERS), f"faltam em HANDLERS: {ONDA3_LOOP - set(m.HANDLERS)}"
    for sub in ONDA3_LOOP:
        assert callable(m.HANDLERS[sub])


def test_loop_scope_subcommands_tem_days_e_all():
    """loop.corrections e loop-health declaram --days e --all (escopo sistema vs usuario)."""
    m = _load('loop')
    for sub in ('corrections', 'loop-health'):
        argnames = {a['name'] for a in m.SUBCOMMANDS[sub]['args']}
        assert '--days' in argnames, f"loop.{sub} sem --days"
        assert '--all' in argnames, f"loop.{sub} sem --all"


def test_loop_directives_tem_status():
    """loop.directives declara --status (filtro do funil)."""
    m = _load('loop')
    argnames = {a['name'] for a in m.SUBCOMMANDS['directives']['args']}
    assert '--status' in argnames, "loop.directives sem --status"


def test_eval_onda3_registrado():
    """eval.py: scores/cases registrados e callable."""
    m = _load('eval')
    assert ONDA3_EVAL <= set(m.SUBCOMMANDS), f"faltam em SUBCOMMANDS: {ONDA3_EVAL - set(m.SUBCOMMANDS)}"
    assert ONDA3_EVAL <= set(m.HANDLERS), f"faltam em HANDLERS: {ONDA3_EVAL - set(m.HANDLERS)}"
    for sub in ONDA3_EVAL:
        assert callable(m.HANDLERS[sub])


def test_melhorias_onda3_registrado():
    """melhorias.py: list-open/show/intelligence-report registrados e callable."""
    m = _load('melhorias')
    assert ONDA3_MELHORIAS <= set(m.SUBCOMMANDS), (
        f"faltam em SUBCOMMANDS: {ONDA3_MELHORIAS - set(m.SUBCOMMANDS)}"
    )
    assert ONDA3_MELHORIAS <= set(m.HANDLERS), f"faltam em HANDLERS: {ONDA3_MELHORIAS - set(m.HANDLERS)}"
    for sub in ONDA3_MELHORIAS:
        assert callable(m.HANDLERS[sub])


def test_melhorias_show_exige_key():
    """melhorias.show exige --key (required) — sem chave nao ha o que mostrar."""
    m = _load('melhorias')
    key_arg = next((a for a in m.SUBCOMMANDS['show']['args'] if a['name'] == '--key'), None)
    assert key_arg is not None, "melhorias.show sem --key"
    assert key_arg.get('required') is True, "melhorias.show --key deveria ser required"


@pytest.mark.parametrize('name', ['loop', 'eval', 'melhorias'])
def test_onda3_main_delega_run_handler(name):
    """Os 3 scripts novos usam o padrao Onda 2 (run_handler) — sem parse/contexto manual."""
    m = _load(name)
    main_src = inspect.getsource(m.main)
    assert 'run_handler(' in main_src, f"{name}.main deveria delegar a run_handler"


@pytest.mark.parametrize('name', ['loop', 'eval', 'melhorias'])
def test_onda3_handlers_sem_contexto_duplo(name):
    """Handlers READ NAO reabrem app context (get_app_context) — run_handler ja cuida."""
    m = _load(name)
    for fn in m.HANDLERS.values():
        src = inspect.getsource(fn)
        code = '\n'.join(l for l in src.splitlines() if not l.lstrip().startswith('#'))
        assert 'get_app_context(' not in code, (
            f"{name}.{fn.__name__}: contexto-duplo (get_app_context) nao deveria existir"
        )


@pytest.mark.parametrize('name', ['loop', 'eval', 'melhorias'])
def test_onda3_read_handlers_sem_escrita(name):
    """Handlers de LEITURA nunca commitam/add/delete (so rollback defensivo)."""
    m = _load(name)
    for sub in ONDA3_READ[name]:
        fn = m.HANDLERS[sub]
        src = inspect.getsource(fn)
        code = '\n'.join(l for l in src.splitlines() if not l.lstrip().startswith('#'))
        assert 'session.commit(' not in code, f"{name}.{sub}: handler READ nao pode commitar"
        assert 'session.add(' not in code, f"{name}.{sub}: handler READ nao pode add()"
        assert 'session.delete(' not in code, f"{name}.{sub}: handler READ nao pode delete()"


# ─────────────────────────────────────────────────────────────────────────
# Onda 3 fase 3b — flywheel WRITE. Invariante: dry-run e o DEFAULT; toda
# escrita esta atras de --confirm (guard `if not args.confirm:`).
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize('name', ['loop', 'eval', 'melhorias'])
def test_onda3_write_registrado(name):
    """Os subcomandos WRITE estao registrados (SUBCOMMANDS+HANDLERS) e sao callable."""
    m = _load(name)
    write = ONDA3_WRITE[name]
    assert write <= set(m.SUBCOMMANDS), f"{name}: faltam WRITE em SUBCOMMANDS: {write - set(m.SUBCOMMANDS)}"
    assert write <= set(m.HANDLERS), f"{name}: faltam WRITE em HANDLERS: {write - set(m.HANDLERS)}"
    for sub in write:
        assert callable(m.HANDLERS[sub])


@pytest.mark.parametrize('name', ['loop', 'eval', 'melhorias'])
def test_onda3_write_exige_confirm(name):
    """Todo subcomando WRITE declara --confirm (sem ele = dry-run)."""
    m = _load(name)
    for sub in ONDA3_WRITE[name]:
        argnames = {a['name'] for a in m.SUBCOMMANDS[sub]['args']}
        assert '--confirm' in argnames, f"{name}.{sub} (WRITE) deveria declarar --confirm"


@pytest.mark.parametrize('name', ['loop', 'eval', 'melhorias'])
def test_onda3_write_guardado_por_confirm(name):
    """Toda escrita (commit/dispatch) esta atras do guard `if not args.confirm:` (dry-run default).

    Sem o guard, o handler escreveria mesmo em dry-run. Verificamos estruturalmente que cada
    handler WRITE tem o gate de dry-run e que ele faz `return` antes de efetivar.
    """
    EFEITOS = ('session.commit(', 'run_directive_promotion_batch(', 'enqueue_eval_batch(', 'upsert_response(')
    m = _load(name)
    for sub in ONDA3_WRITE[name]:
        fn = m.HANDLERS[sub]
        src = inspect.getsource(fn)
        code = '\n'.join(l for l in src.splitlines() if not l.lstrip().startswith('#'))
        assert 'if not args.confirm:' in code, (
            f"{name}.{sub} (WRITE) sem guard de dry-run `if not args.confirm:`"
        )
        guard_pos = code.index('if not args.confirm:')
        efeito_positions = [code.find(e) for e in EFEITOS if code.find(e) != -1]
        primeiro_efeito = min(efeito_positions) if efeito_positions else len(code)
        # 1) o guard precede qualquer efeito colateral (commit/dispatch).
        assert guard_pos < primeiro_efeito, (
            f"{name}.{sub}: efeito colateral aparece ANTES do guard de dry-run"
        )
        # 2) o bloco dry-run faz `return` ANTES do efeito (senao escreveria em dry-run).
        return_apos_guard = code.find('return', guard_pos)
        assert 0 <= return_apos_guard < primeiro_efeito, (
            f"{name}.{sub}: sem `return` no bloco dry-run antes do efeito (escreveria em dry-run)"
        )
