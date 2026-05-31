"""
Testa job RQ de JUDGE de passo (Process Reward Model) — Onda 1 E2/A1.

Cobertura:
- test_judge_step_grava_veredito: fluxo feliz, veredito persiste em outcome_signal
- test_judge_step_dominancia_ambiental: FALHA_ODOO forca score <= 35 mesmo com Haiku 90
- test_judge_core_sem_odoo_ops: degrada graciosamente quando sem auditoria ambiental
- test_parse_judge_json_tolerante: JSON tolerante a prefixos/sufixos
- test_parse_judge_json_invalido: retorna None para JSON invalido
- test_judge_step_uid_inexistente: no-op seguro quando step nao encontrado
- test_judge_step_haiku_json_invalido: best-effort, nao crasha com JSON invalido
"""
import json
import uuid
import pytest

from app import create_app, db as _db


@pytest.fixture(scope='module')
def app_ctx():
    """Flask app context para testes do judge (escopo de modulo)."""
    _app = create_app()
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    with _app.app_context():
        yield _app


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _mk_sid():
    return f'judge-{uuid.uuid4().hex}'


def _mk_step(app_ctx, session_id: str, tools=None):
    """Insere e COMMITA um AgentStep de teste, retornando (step_uid, step).

    Commita para que o step seja visivel em novos app_contexts criados por judge_step.
    O rollback de limpeza acontece no teardown de cada teste.
    """
    from app.agente.models import AgentStep
    uid = f'{session_id}:1'
    AgentStep.insert_step(
        step_uid=uid,
        session_id=session_id,
        user_id=1,
        channel='web',
        model='claude-opus-4-8',
        tools_used=tools or ['consultando-sql'],
    )
    _db.session.commit()
    step = AgentStep.query.filter_by(step_uid=uid).first()
    return uid, step


def _fake_odoo_falha():
    """Retorna um objeto simulando OperacaoOdooAuditoria com status FALHA_ODOO."""
    class _FakeOp:
        status = 'FALHA_ODOO'
        modelo_odoo = 'stock.picking'
        metodo_odoo = 'button_validate'
        contexto_origem = 'execute_kw_hook'
    return _FakeOp()


def _fake_odoo_ok():
    """Retorna um objeto simulando OperacaoOdooAuditoria com status EXECUTADO."""
    class _FakeOp:
        status = 'EXECUTADO'
        modelo_odoo = 'account.move'
        metodo_odoo = 'action_post'
        contexto_origem = 'execute_kw_hook'
    return _FakeOp()


# ─── Testes unitários (sem DB) ────────────────────────────────────────────────

def test_parse_judge_json_tolerante():
    """_parse_judge_json e tolerante a prefixos/sufixos de texto."""
    from app.agente.workers.step_judge import _parse_judge_json

    raw = 'Aqui esta o resultado: {"score": 75, "label": "partial", "componente_culpado": null, "evidencia": "ok"}'
    result = _parse_judge_json(raw)
    assert result is not None
    assert result['score'] == 75
    assert result['label'] == 'partial'


def test_parse_judge_json_invalido():
    """_parse_judge_json retorna None para texto sem JSON valido."""
    from app.agente.workers.step_judge import _parse_judge_json

    assert _parse_judge_json('') is None
    assert _parse_judge_json('sem json aqui') is None
    assert _parse_judge_json('{"score": 50') is None  # malformed


def test_parse_judge_json_faltando_chaves_obrigatorias():
    """_parse_judge_json retorna None se faltam chaves score ou label."""
    from app.agente.workers.step_judge import _parse_judge_json

    # Sem 'score'
    assert _parse_judge_json('{"label": "success", "componente_culpado": null, "evidencia": "x"}') is None
    # Sem 'label'
    assert _parse_judge_json('{"score": 80, "componente_culpado": null, "evidencia": "x"}') is None


def test_build_judge_prompt_sem_odoo_ops():
    """_build_judge_prompt menciona ausencia de auditoria ambiental quando sem ops."""
    from app.agente.workers.step_judge import _build_judge_prompt

    class _FakeStep:
        tools_used = ['consultando-sql', 'Bash']
        outcome_signal = None
        session_id = 'sess-fake-001'

    prompt = _build_judge_prompt(_FakeStep(), [])
    assert 'sem auditoria ambiental' in prompt.lower() or 'sem auditoria' in prompt


def test_build_judge_prompt_com_odoo_ops():
    """_build_judge_prompt inclui resumo das operacoes Odoo quando disponivel."""
    from app.agente.workers.step_judge import _build_judge_prompt

    class _FakeStep:
        tools_used = ['ajustando-quant-odoo']
        outcome_signal = None
        session_id = 'sess-fake-002'

    ops = [_fake_odoo_ok(), _fake_odoo_falha()]
    prompt = _build_judge_prompt(_FakeStep(), ops)
    assert 'FALHA_ODOO' in prompt
    assert 'EXECUTADO' in prompt


# ─── Testes de integração (com DB) ───────────────────────────────────────────

def test_judge_step_grava_veredito(app_ctx, monkeypatch):
    """Fluxo feliz: judge_step grava veredito em outcome_signal['judge']."""
    from app.agente.workers import step_judge
    from app.agente.models import AgentStep

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)

    haiku_response = json.dumps({
        'score': 85,
        'label': 'success',
        'componente_culpado': None,
        'evidencia': 'operacoes Odoo bem sucedidas',
    }).replace(': None', ': null')  # JSON null correto

    # Mocks: evitar Haiku real + create_app duplicado + query Odoo
    monkeypatch.setattr(step_judge, '_call_haiku_judge', lambda *a, **k: haiku_response)
    monkeypatch.setattr(step_judge, 'create_app', lambda: app_ctx)

    # Mockar query de odoo_ops para retornar lista vazia (sem auditoria ambiental)
    import app.agente.workers.step_judge as _sj
    original_judge_core = _sj._judge_core

    def _judge_core_sem_odoo(step, odoo_ops):
        return original_judge_core(step, [])

    monkeypatch.setattr(step_judge, '_judge_core', _judge_core_sem_odoo)

    step_judge.judge_step(uid)

    # Verificar que o veredito foi gravado
    _db.session.expire_all()
    step = AgentStep.query.filter_by(step_uid=uid).first()
    assert step is not None
    assert step.outcome_signal is not None
    judge_data = step.outcome_signal.get('judge', {})
    assert judge_data.get('score') == 85
    assert judge_data.get('label') == 'success'

    _db.session.rollback()


def test_judge_step_dominancia_ambiental(app_ctx, monkeypatch):
    """
    DOMINANCIA AMBIENTAL: se ha FALHA_ODOO nas operacoes, o score final
    fica <= 35 e componente_culpado == 'odoo' MESMO com Haiku retornando 90.

    Este e o teste central do Process Reward Model: o sinal ambiental
    (o que de fato aconteceu no ERP) DOMINA o texto da resposta.
    """
    from app.agente.workers import step_judge
    from app.agente.models import AgentStep

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid, tools=['operando-picking-odoo'])

    # Haiku otimista: retorna score 90 (confiante, mas errado)
    haiku_response = json.dumps({
        'score': 90,
        'label': 'success',
        'componente_culpado': None,
        'evidencia': 'resposta parece correta',
    }).replace(': None', ': null')

    monkeypatch.setattr(step_judge, '_call_haiku_judge', lambda *a, **k: haiku_response)
    monkeypatch.setattr(step_judge, 'create_app', lambda: app_ctx)

    # Forcar _judge_core com 1 FALHA_ODOO na lista de ops
    import app.agente.workers.step_judge as _sj
    original_judge_core = _sj._judge_core

    def _judge_core_com_falha(step, odoo_ops):
        return original_judge_core(step, [_fake_odoo_falha()])

    monkeypatch.setattr(step_judge, '_judge_core', _judge_core_com_falha)

    step_judge.judge_step(uid)

    _db.session.expire_all()
    step = AgentStep.query.filter_by(step_uid=uid).first()
    assert step is not None
    judge_data = step.outcome_signal.get('judge', {})

    # INVARIANTE: ambiental domina — score DEVE ser <= 35
    assert judge_data.get('score') <= 35, (
        f"Esperado score <= 35 (dominancia ambiental), mas foi {judge_data.get('score')}. "
        "FALHA_ODOO deve sobrescrever score do Haiku."
    )
    # INVARIANTE: componente_culpado deve ser 'odoo'
    assert judge_data.get('componente_culpado') == 'odoo', (
        f"Esperado componente_culpado='odoo', mas foi {judge_data.get('componente_culpado')}."
    )

    _db.session.rollback()


def test_judge_core_sem_odoo_ops_usa_apenas_haiku(app_ctx, monkeypatch):
    """
    Sem ops Odoo, _judge_core usa apenas o score do Haiku
    sem aplicar cap de dominancia ambiental.
    """
    from app.agente.workers import step_judge

    class _FakeStep:
        tools_used = ['consultando-sql']
        outcome_signal = None
        session_id = 'sess-fake-003'

    haiku_response = json.dumps({
        'score': 72,
        'label': 'partial',
        'componente_culpado': None,
        'evidencia': 'sem operacoes Odoo para validar',
    }).replace(': None', ': null')

    monkeypatch.setattr(step_judge, '_call_haiku_judge', lambda *a, **k: haiku_response)

    veredito = step_judge._judge_core(_FakeStep(), [])
    assert veredito is not None
    assert veredito['score'] == 72  # Haiku domina quando sem ops ambientais
    assert veredito['label'] == 'partial'


def test_judge_step_uid_inexistente_nao_crasha(app_ctx, monkeypatch):
    """step_uid inexistente -> no-op seguro (nao levanta excecao)."""
    from app.agente.workers import step_judge

    monkeypatch.setattr(step_judge, 'create_app', lambda: app_ctx)

    # Nao deve levantar excecao
    step_judge.judge_step('uid-que-nao-existe-nunca:999')


def test_judge_step_haiku_json_invalido_nao_grava(app_ctx, monkeypatch):
    """Haiku retorna JSON invalido -> best-effort, nao grava e nao crasha."""
    from app.agente.workers import step_judge
    from app.agente.models import AgentStep

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)

    monkeypatch.setattr(step_judge, '_call_haiku_judge', lambda *a, **k: 'nao e json')
    monkeypatch.setattr(step_judge, 'create_app', lambda: app_ctx)

    import app.agente.workers.step_judge as _sj
    original_judge_core = _sj._judge_core

    def _judge_core_sem_odoo(step, odoo_ops):
        return original_judge_core(step, [])

    monkeypatch.setattr(step_judge, '_judge_core', _judge_core_sem_odoo)

    step_judge.judge_step(uid)

    _db.session.expire_all()
    step = AgentStep.query.filter_by(step_uid=uid).first()
    # outcome_signal pode ser None ou pode ter outros campos, mas NAO 'judge'
    if step.outcome_signal is not None:
        assert 'judge' not in step.outcome_signal

    _db.session.rollback()
