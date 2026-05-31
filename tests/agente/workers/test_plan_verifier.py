"""
Testa job RQ de verifier adversarial — Parte B (B2, Onda 2).

Cobertura:
- test_verify_plan_adversarial_persiste_veredito: fluxo feliz — veredito persiste em outcome_signal['verify']
- test_verify_plan_adversarial_commita(spy): CRITICAL-1 — db.session.commit() é chamado (spy passthrough)
- test_verify_core_haiku_refuta: Haiku retorna refuted=true → _verify_core retorna dict correto
- test_verify_core_haiku_ok: Haiku retorna refuted=false → ok (não refutado)
- test_verify_core_json_invalido: JSON inválido → best-effort, retorna None
- test_verify_plan_adversarial_uid_inexistente: no-op seguro quando step não existe
- test_default_cetico: quando Haiku retorna JSON sem 'refuted', padrão é refuted=True (cético)
"""
import json
import uuid
import pytest

from app import create_app, db as _db


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def app_ctx():
    """Flask app context para testes do plan_verifier (escopo de módulo)."""
    _app = create_app()
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    with _app.app_context():
        yield _app


def _mk_sid():
    return f'pv-{uuid.uuid4().hex}'


def _mk_step(app_ctx, session_id: str, tools=None):
    """Insere e COMMITA um AgentStep de teste.

    Commita de propósito: plan_verifier abre um app_context aninhado
    (via create_app mockado) — só enxerga dados committados no banco.
    Limpa via _cleanup_step ao final do teste.
    """
    from app.agente.models import AgentStep
    uid = f'{session_id}:1'
    AgentStep.insert_step(
        step_uid=uid,
        session_id=session_id,
        user_id=1,
        channel='web',
        model='claude-opus-4-8',
        tools_used=tools or ['cotando-frete'],
    )
    _db.session.commit()
    step = AgentStep.query.filter_by(step_uid=uid).first()
    return uid, step


def _cleanup_step(step_uid: str):
    """Remove AgentStep de teste — evita órfãos no banco."""
    from app.agente.models import AgentStep
    AgentStep.query.filter_by(step_uid=step_uid).delete()
    _db.session.commit()


# ─── Testes unitários (sem DB) ───────────────────────────────────────────────

def test_verify_core_haiku_refuta(monkeypatch):
    """_verify_core retorna refuted=True quando Haiku refuta a conclusão."""
    from app.agente.workers import plan_verifier

    class _FakeStep:
        step_uid = 'sess-fake-pv:1'
        session_id = 'sess-fake-pv'
        tools_used = ['cotando-frete']
        outcome_signal = None

    haiku_resp = json.dumps({'refuted': True, 'reason': 'Frete calculado sem considerar peso cubado'})
    monkeypatch.setattr(plan_verifier, '_call_haiku_verifier', lambda prompt: haiku_resp)

    result = plan_verifier._verify_core(_FakeStep())

    assert result is not None
    assert result['refuted'] is True
    assert 'reason' in result
    assert len(result['reason']) > 0


def test_verify_core_haiku_ok(monkeypatch):
    """_verify_core retorna refuted=False quando Haiku não consegue refutar."""
    from app.agente.workers import plan_verifier

    class _FakeStep:
        step_uid = 'sess-fake-pv2:1'
        session_id = 'sess-fake-pv2'
        tools_used = ['consultando-sql']
        outcome_signal = None

    haiku_resp = json.dumps({'refuted': False, 'reason': 'Conclusão consistente com dados disponíveis'})
    monkeypatch.setattr(plan_verifier, '_call_haiku_verifier', lambda prompt: haiku_resp)

    result = plan_verifier._verify_core(_FakeStep())

    assert result is not None
    assert result['refuted'] is False


def test_verify_core_json_invalido(monkeypatch):
    """JSON inválido do Haiku → best-effort, _verify_core retorna None."""
    from app.agente.workers import plan_verifier

    class _FakeStep:
        step_uid = 'sess-fake-pv3:1'
        session_id = 'sess-fake-pv3'
        tools_used = []
        outcome_signal = None

    monkeypatch.setattr(plan_verifier, '_call_haiku_verifier', lambda prompt: 'nao e json valido')

    result = plan_verifier._verify_core(_FakeStep())

    assert result is None


def test_default_cetico(monkeypatch):
    """Quando Haiku retorna JSON sem 'refuted', padrão é refuted=True (cético)."""
    from app.agente.workers import plan_verifier

    class _FakeStep:
        step_uid = 'sess-fake-pv4:1'
        session_id = 'sess-fake-pv4'
        tools_used = []
        outcome_signal = None

    # JSON válido mas sem campo 'refuted'
    haiku_resp = json.dumps({'reason': 'inconclusivo'})
    monkeypatch.setattr(plan_verifier, '_call_haiku_verifier', lambda prompt: haiku_resp)

    result = plan_verifier._verify_core(_FakeStep())

    # Deve retornar dict (não None) com refuted=True (padrão cético)
    assert result is not None
    assert result['refuted'] is True


def test_verify_plan_adversarial_uid_inexistente_nao_crasha(app_ctx, monkeypatch):
    """step_uid inexistente → no-op seguro, não levanta exceção."""
    from app.agente.workers import plan_verifier

    monkeypatch.setattr(plan_verifier, 'create_app', lambda: app_ctx)

    # Não deve levantar exceção
    plan_verifier.verify_plan_adversarial('uid-inexistente-nunca-pv:999')


# ─── Testes de integração (com DB) ───────────────────────────────────────────

def test_verify_plan_adversarial_persiste_veredito(app_ctx, monkeypatch):
    """Fluxo feliz: verify_plan_adversarial persiste veredito em outcome_signal['verify']."""
    from app.agente.workers import plan_verifier
    from app.agente.models import AgentStep

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)

    haiku_resp = json.dumps({'refuted': True, 'reason': 'Premissa não suportada pelos dados'})

    monkeypatch.setattr(plan_verifier, '_call_haiku_verifier', lambda prompt: haiku_resp)
    monkeypatch.setattr(plan_verifier, 'create_app', lambda: app_ctx)

    try:
        plan_verifier.verify_plan_adversarial(uid)

        _db.session.expire_all()
        step = AgentStep.query.filter_by(step_uid=uid).first()
        assert step is not None
        assert step.outcome_signal is not None
        verify_data = step.outcome_signal.get('verify', {})
        assert verify_data.get('refuted') is True
        assert 'reason' in verify_data
    finally:
        _cleanup_step(uid)


def test_verify_plan_adversarial_commita(app_ctx, monkeypatch):
    """
    CRITICAL-1 (espelha step_judge): verify_plan_adversarial DEVE chamar
    db.session.commit() após update_outcome.

    update_outcome usa begin_nested()+flush() (SAVEPOINT) — sem commit
    explícito, o veredito é DESCARTADO quando o app_context do job RQ morre.
    Este teste ESPIONA db.session.commit (spy passthrough) provando:
    1. A CHAMADA acontece (CRITICAL-1 não regrediu)
    2. A PERSISTÊNCIA é real (commit passthrough consolida o veredito)
    """
    from app.agente.workers import plan_verifier
    from app.agente.models import AgentStep

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)

    haiku_resp = json.dumps({'refuted': False, 'reason': 'Conclusão plausível'})
    monkeypatch.setattr(plan_verifier, '_call_haiku_verifier', lambda prompt: haiku_resp)
    monkeypatch.setattr(plan_verifier, 'create_app', lambda: app_ctx)

    # Spy: conta chamadas + executa commit REAL (passthrough)
    calls = []
    real_commit = _db.session.commit

    def _spy_commit():
        calls.append(1)
        real_commit()

    monkeypatch.setattr(_db.session, 'commit', _spy_commit)

    try:
        plan_verifier.verify_plan_adversarial(uid)

        # PROVA: commit foi chamado (CRITICAL-1 não regredido)
        assert len(calls) >= 1, (
            "verify_plan_adversarial NAO chamou db.session.commit() — "
            "veredito seria descartado quando app_context do job RQ morre (CRITICAL-1)."
        )

        # E o veredito de fato persistiu (commit real via passthrough)
        _db.session.expire_all()
        step = AgentStep.query.filter_by(step_uid=uid).first()
        assert step.outcome_signal.get('verify', {}).get('refuted') is False
    finally:
        monkeypatch.undo()
        _cleanup_step(uid)
