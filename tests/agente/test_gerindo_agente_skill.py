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
           'loop', 'eval', 'melhorias', 'infra']

# Onda 1 (camada de evolucao/qualidade) — subcomandos novos em diagnostico.py.
NOVOS_DIAGNOSTICO = {'step-quality', 'step-coverage', 'rule-adhesion', 'routing', 'recommendations'}

# Onda 3 fase 3a (flywheel READ) — scripts novos e seus subcomandos READ.
ONDA3_LOOP = {'directives', 'corrections', 'loop-health'}
ONDA3_EVAL = {'scores', 'cases'}
ONDA3_MELHORIAS = {'list-open', 'show', 'intelligence-report'}

# Onda 3 fase 3b (flywheel WRITE) — subcomandos de ESCRITA, todos atras de --confirm.
# eval.run removido (estrategia R2, 2026-06-12): deletado junto com o eval_runner/A3.
ONDA3_WRITE = {
    'loop': {'approve', 'reject', 'promote-batch'},
    'eval': {'review'},
    'melhorias': {'respond'},
}
ONDA3_READ = {
    'loop': ONDA3_LOOP,
    'eval': ONDA3_EVAL,
    'melhorias': ONDA3_MELHORIAS,
}

# Onda 4 (P10) — observabilidade de infra/seguranca (infra.py), TODOS READ.
ONDA4_INFRA = {'flags', 'gates', 'worker-status'}


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
                                  'loop', 'eval', 'melhorias', 'infra'])
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
    EFEITOS = ('session.commit(', 'run_directive_promotion_batch(', 'upsert_response(')
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


# ─────────────────────────────────────────────────────────────────────────
# Onda 4 — P10: observabilidade de infra/seguranca (infra.py). 3 subcomandos
# TODOS READ (flags/gates/worker-status). Tudo ZERO-DB: importlib + inspect.
# ─────────────────────────────────────────────────────────────────────────


def test_infra_onda4_registrado():
    """infra.py: flags/gates/worker-status registrados, callable e em paridade."""
    m = _load('infra')
    assert ONDA4_INFRA <= set(m.SUBCOMMANDS), f"faltam em SUBCOMMANDS: {ONDA4_INFRA - set(m.SUBCOMMANDS)}"
    assert ONDA4_INFRA <= set(m.HANDLERS), f"faltam em HANDLERS: {ONDA4_INFRA - set(m.HANDLERS)}"
    for sub in ONDA4_INFRA:
        assert callable(m.HANDLERS[sub])


def test_infra_main_delega_run_handler():
    """infra usa o padrao Onda 2 (run_handler) — sem parse/contexto manual."""
    m = _load('infra')
    assert 'run_handler(' in inspect.getsource(m.main), "infra.main deveria delegar a run_handler"


def test_infra_handlers_sem_contexto_duplo():
    """Handlers de infra NAO reabrem app context (get_app_context) — run_handler ja cuida."""
    m = _load('infra')
    for fn in m.HANDLERS.values():
        code = '\n'.join(l for l in inspect.getsource(fn).splitlines() if not l.lstrip().startswith('#'))
        assert 'get_app_context(' not in code, (
            f"infra.{fn.__name__}: contexto-duplo (get_app_context) nao deveria existir"
        )


def test_infra_handlers_sao_read_only():
    """P10 e READ: nenhum handler de infra commita/add/delete (so rollback defensivo)."""
    m = _load('infra')
    for sub in ONDA4_INFRA:
        code = '\n'.join(l for l in inspect.getsource(m.HANDLERS[sub]).splitlines()
                         if not l.lstrip().startswith('#'))
        assert 'session.commit(' not in code, f"infra.{sub}: handler READ nao pode commitar"
        assert 'session.add(' not in code, f"infra.{sub}: handler READ nao pode add()"
        assert 'session.delete(' not in code, f"infra.{sub}: handler READ nao pode delete()"


def test_infra_flags_tem_days():
    """infra.flags declara --days (janela da evidencia time-bound)."""
    m = _load('infra')
    argnames = {a['name'] for a in m.SUBCOMMANDS['flags']['args']}
    assert '--days' in argnames, "infra.flags sem --days"


def test_infra_evolution_flags_bem_formada():
    """A tabela EVOLUTION_FLAGS e consistente: tuplas de 6, env vars unicas, grupos validos.

    Trava a CONSISTENCIA INTERNA da enumeracao. O confronto contra feature_flags.py (nome/default
    reais) e' feito por test_infra_evolution_flags_confronta_feature_flags.
    """
    m = _load('infra')
    flags = m.EVOLUTION_FLAGS
    assert len(flags) >= 12, "esperado >= 12 flags de evolucao (Ondas 0-4 + atuador)"
    env_vars = [t[1] for t in flags]
    assert len(env_vars) == len(set(env_vars)), "env vars duplicadas em EVOLUTION_FLAGS"
    grupos_validos = {'Onda 0', 'Onda 1', 'Onda 2', 'Onda 3', 'Onda 4', 'Atuador', 'Loop corretivo'}
    for attr, env_var, default, grupo, ev_key, ev_kind in flags:
        assert isinstance(attr, str) and attr, "attr vazio"
        assert env_var.startswith('AGENT_') or env_var.startswith('USE_'), f"env var atipica: {env_var}"
        assert isinstance(default, bool), f"default de {env_var} nao e bool"
        assert grupo in grupos_validos, f"grupo invalido: {grupo}"
        assert ev_kind in (None, 'activity', 'readiness'), f"evidence_kind invalido em {env_var}: {ev_kind}"
        # invariante: key e kind andam juntos (sem rastro => sem kind, e vice-versa).
        assert (ev_key is None) == (ev_kind is None), (
            f"{env_var}: evidence_key e evidence_kind devem ser ambos None ou ambos preenchidos"
        )


def test_infra_evidence_keys_existem_nas_metricas():
    """Toda evidence_key referenciada em EVOLUTION_FLAGS existe no dict de metricas.

    Defende contra typo que faria _evidence_for sempre retornar value=None (signal=unknown)
    silenciosamente — quebrando a inferencia db_evidence que e o coracao do P10.
    """
    m = _load('infra')
    metricas_validas = {
        'agent_step_frustration', 'agent_step_judged', 'agent_step_verified',
        'planstate_with_plan', 'planstate_total', 'eval_scores', 'eval_cases',
        'directives_shadow', 'directives_injetaveis', 'corrections_mandatory',
        'mandatory_rules_total', 'outcome_populated',
    }
    for attr, env_var, default, grupo, ev_key, ev_kind in m.EVOLUTION_FLAGS:
        if ev_key is not None:
            assert ev_key in metricas_validas, (
                f"evidence_key '{ev_key}' de {env_var} nao existe nas metricas de _compute_evidence"
            )


def test_infra_evolution_flags_confronta_feature_flags():
    """MED-6: confronta EVOLUTION_FLAGS contra feature_flags.py por TEXTO (ZERO import/DB).

    Cada (attr, env_var, default) deve existir no arquivo fonte com o MESMO nome de env var e o
    MESMO default. Pega drift real (renomear flag, mudar default) sem importar app (preserva ZERO-DB).
    """
    import re
    m = _load('infra')
    ff_path = (Path(__file__).resolve().parents[2]
               / 'app' / 'agente' / 'config' / 'feature_flags.py')
    ff_src = ff_path.read_text(encoding='utf-8')
    for attr, env_var, default, grupo, ev_key, ev_kind in m.EVOLUTION_FLAGS:
        # 1) o attr e' atribuido como simbolo de modulo em feature_flags.py.
        assert re.search(rf'(?m)^{re.escape(attr)}\s*=', ff_src), (
            f"EVOLUTION_FLAGS: '{attr}' nao e atribuido em feature_flags.py (drift de nome de simbolo?)"
        )
        # 2) o env var e' lido (os.getenv legado OU _env_bool helper) com o default
        #    esperado ('true'/'false'). _env_bool (canonico desde 042705ddc2) envolve
        #    os.getenv com o mesmo default string — ambos validos.
        default_str = 'true' if default else 'false'
        pat = rf'(?:os\.getenv|_env_bool)\(\s*["\']{re.escape(env_var)}["\']\s*,\s*["\']({default_str})["\']'
        assert re.search(pat, ff_src, re.IGNORECASE), (
            f"feature_flags.py: nao achei os.getenv('{env_var}', '{default_str}') — "
            f"drift de env var ou default de {attr}?"
        )


def test_infra_gerindo_write_blocked_em_sincronia_com_permissions():
    """LOW-15: GERINDO_WRITE_BLOCKED (gates) deve espelhar o regex _GERINDO_WRITE_REGEX de
    permissions.py. Se o gate ganhar/perder um subcomando WRITE e a lista nao acompanhar, o
    subcomando `gates` mente. Confronto por TEXTO (ZERO import/DB)."""
    import re
    m = _load('infra')
    perm_path = (Path(__file__).resolve().parents[2]
                 / 'app' / 'agente' / 'config' / 'permissions.py')
    perm_src = perm_path.read_text(encoding='utf-8')
    # Extrai o 2o grupo da alternancia do regex: (approve|reject|promote-batch|review|run|respond)
    mt = re.search(r'\((approve(?:\|[\w-]+)+)\)', perm_src)
    assert mt, "nao localizei o grupo de subcomandos WRITE no regex de permissions.py"
    regex_set = set(mt.group(1).split('|'))
    assert regex_set == set(m.GERINDO_WRITE_BLOCKED), (
        f"GERINDO_WRITE_BLOCKED fora de sincronia com permissions.py: "
        f"so no regex={regex_set - set(m.GERINDO_WRITE_BLOCKED)}, "
        f"so na lista={set(m.GERINDO_WRITE_BLOCKED) - regex_set}"
    )


def test_infra_evidence_for_shape_homogeneo():
    """LOW-9/MED-7: _evidence_for SEMPRE retorna dict {metric,kind,value,signal} (nunca None).

    Shape homogeneo impede o snapshot P12 de colapsar o campo polimorfico e mascarar regressao.
    Cobre os ramos none/unknown/active/idle/ready/empty. _verdict aceita todos sem crash. ZERO-DB.
    """
    m = _load('infra')
    KEYS = {'metric', 'kind', 'value', 'signal'}
    casos = [
        (m._evidence_for(None, None, {}), 'none', None),
        (m._evidence_for('x', 'activity', {'x': None}), 'unknown', None),
        (m._evidence_for('x', 'activity', {'x': 5}), 'active', 5),
        (m._evidence_for('x', 'activity', {'x': 0}), 'idle', 0),
        (m._evidence_for('x', 'readiness', {'x': 3}), 'ready', 3),
        (m._evidence_for('x', 'readiness', {'x': 0}), 'empty', 0),
    ]
    for ev, sig, val in casos:
        assert isinstance(ev, dict) and set(ev) == KEYS, f"shape errado: {ev}"
        assert ev['signal'] == sig, f"signal esperado {sig}, veio {ev['signal']}"
        assert ev['value'] == val
        assert isinstance(m._verdict(True, ev), str) and isinstance(m._verdict(False, ev), str)


# ─────────────────────────────────────────────────────────────────────────
# T1.4 (trilho memoria→reference) — fila de promocao (diagnostico.py
# promotion-candidates) + aposentadoria manual (memoria.py aposentar).
# Tudo ZERO-DB: importlib + inspect + parser real via sys.argv monkeypatch.
# ─────────────────────────────────────────────────────────────────────────


def test_promotion_candidates_registrada_t14():
    """promotion-candidates registrado em diagnostico com handler callable e args do contrato."""
    d = _load('diagnostico')
    assert 'promotion-candidates' in d.SUBCOMMANDS, "promotion-candidates ausente de SUBCOMMANDS"
    assert 'promotion-candidates' in d.HANDLERS and callable(d.HANDLERS['promotion-candidates'])
    args_cfg = {a['name']: a for a in d.SUBCOMMANDS['promotion-candidates']['args']}
    assert '--min-effective' in args_cfg, "promotion-candidates sem --min-effective"
    assert '--idade-dias' in args_cfg, "promotion-candidates sem --idade-dias"
    assert '--limit' in args_cfg, "promotion-candidates deve sobrescrever --limit (default 30)"
    assert '--user-id' in args_cfg and args_cfg['--user-id'].get('default') == 0, (
        "--user-id deve ter default 0 (fila e sempre de memorias empresa)"
    )


def test_promotion_candidates_query_contrato_t14():
    """A query da fila respeita o contrato T1.4: user_id=0 (empresa), nao-cold,
    nao-diretorio, contadores OR, idade minima e exclusao de ja-promovidas
    (meta ? 'promovida_para'). Confronto por TEXTO (ZERO-DB)."""
    d = _load('diagnostico')
    src = inspect.getsource(d.handle_promotion_candidates)
    code = '\n'.join(l for l in src.splitlines() if not l.lstrip().startswith('#'))
    assert 'user_id == 0' in code, "fila deve consultar user_id=0 (memorias empresa)"
    assert 'is_cold == False' in code, "fila deve excluir tier frio"
    assert 'is_directory == False' in code, "fila deve excluir diretorios"
    assert 'correction_count' in code and 'effective_count' in code, "contadores ausentes"
    assert 'promovida_para' in code, "fila deve excluir memorias ja promovidas (meta.promovida_para)"
    assert 'created_at' in code, "fila deve filtrar por idade minima (created_at)"


def test_aposentar_registrada_t14():
    """aposentar registrado em memoria com handler callable e args do contrato
    (--path/--promovida-para obrigatorios, --confirmar opt-in, --user-id default 0)."""
    mem = _load('memoria')
    assert 'aposentar' in mem.SUBCOMMANDS, "aposentar ausente de SUBCOMMANDS"
    assert 'aposentar' in mem.HANDLERS and callable(mem.HANDLERS['aposentar'])
    args_cfg = {a['name']: a for a in mem.SUBCOMMANDS['aposentar']['args']}
    assert '--path' in args_cfg and args_cfg['--path'].get('required'), "--path deve ser obrigatorio"
    assert '--promovida-para' in args_cfg and args_cfg['--promovida-para'].get('required'), (
        "--promovida-para deve ser obrigatorio"
    )
    assert '--confirmar' in args_cfg, "aposentar sem --confirmar (dry-run default)"
    assert '--user-id' in args_cfg and args_cfg['--user-id'].get('default') == 0, (
        "--user-id deve ter default 0 (memorias empresa)"
    )


def test_aposentar_dry_run_default_e_versiona_antes_t14():
    """Contrato de seguranca: a ESCRITA (save_version/is_cold/meta/commit) fica atras
    do guard `if not args.confirmar` (dry-run default), versiona ANTES de mutar e usa
    flag_modified no meta (R7 JSONB). Confronto por TEXTO (ZERO-DB)."""
    mem = _load('memoria')
    src = inspect.getsource(mem.handle_aposentar)
    code = '\n'.join(l for l in src.splitlines() if not l.lstrip().startswith('#'))
    guard_pos = code.find('if not args.confirmar')
    assert guard_pos != -1, "handler sem guard dry-run `if not args.confirmar`"
    for token in ('save_version(', 'is_cold = True', 'flag_modified(', 'commit()'):
        pos = code.find(token)
        assert pos != -1, f"handler sem '{token}'"
        assert pos > guard_pos, f"'{token}' deve vir DEPOIS do guard dry-run"
    # Versionamento ANTES da mutacao (padrao memory_mcp_tool.py:2074).
    assert code.find('save_version(') < code.find('is_cold = True'), (
        "save_version deve rodar ANTES de mutar is_cold/meta"
    )
    assert "'promovida_para'" in code or '"promovida_para"' in code, (
        "handler deve gravar meta['promovida_para']"
    )


def test_parser_overrides_comuns_t14(monkeypatch):
    """parse_args_with_subcommands permite OVERRIDE de arg comum por subcomando
    (conflict_handler='resolve'): aposentar --user-id default 0; promotion-candidates
    --limit default 30. Parser real via sys.argv (ZERO-DB)."""
    mem = _load('memoria')
    c = _load('common')
    monkeypatch.setattr(
        sys, 'argv',
        ['memoria.py', 'aposentar', '--path', '/memories/x.xml', '--promovida-para', 'docs/ref.md'],
    )
    args, sub = c.parse_args_with_subcommands('t', mem.SUBCOMMANDS)
    assert sub == 'aposentar'
    assert args.user_id == 0, "aposentar sem --user-id deve cair no default 0"
    assert args.confirmar is False, "dry-run deve ser o default"

    d = _load('diagnostico')
    monkeypatch.setattr(sys, 'argv', ['diagnostico.py', 'promotion-candidates'])
    args, sub = c.parse_args_with_subcommands('t', d.SUBCOMMANDS)
    assert sub == 'promotion-candidates'
    assert args.user_id == 0, "promotion-candidates sem --user-id deve cair no default 0"
    assert args.limit == 30, "promotion-candidates deve sobrescrever --limit para default 30"
    assert args.min_effective == 2 and args.idade_dias == 30
