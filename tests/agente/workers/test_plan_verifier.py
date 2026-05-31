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


# ═══════════════════════════════════════════════════════════════════════════════
# T2b — verify_step_shadow (3 verifiers combinados) + enqueue_pending_verifies
# ═══════════════════════════════════════════════════════════════════════════════
# Espelha o pattern de step_judge (judge_step + enqueue_pending_judges).
# verify_step_shadow roda os 3 verifiers (adversarial/arithmetic/domain) em
# best-effort e grava em outcome_signal['verify'] com as 3 sub-chaves.
# enqueue_pending_verifies é o varredor RQ batch (gate USE_AGENT_VERIFY).

from unittest.mock import MagicMock, patch  # noqa: E402


def _mk_session_with_response(session_id: str, user_text: str, assistant_text: str):
    """Cria e COMMITA uma AgentSession com 1 turno (user→assistant).

    O turn_seq do step é a CONTAGEM de msgs role=='user' (ver chat.py:1836).
    1 user msg → turn_seq=1 → step_uid '{session_id}:1' aponta para o 1º
    assistant message. Limpa via _cleanup_session.
    """
    from app.agente.models import AgentSession
    sess, _ = AgentSession.get_or_create(session_id=session_id, user_id=1)
    sess.add_user_message(user_text)
    sess.add_assistant_message(assistant_text)
    _db.session.commit()
    return sess


def _cleanup_session(session_id: str):
    from app.agente.models import AgentSession
    AgentSession.query.filter_by(session_id=session_id).delete()
    _db.session.commit()


# ─── verify_step_shadow ───────────────────────────────────────────────────────

def test_verify_step_shadow_grava_3_subchaves_e_commita(app_ctx, monkeypatch):
    """verify_step_shadow grava outcome_signal['verify'] com adversarial,
    arithmetic e domain, e chama db.session.commit() (CRITICAL-1)."""
    from app.agente.workers import plan_verifier
    from app.agente.sdk import verifiers
    from app.agente import tools as _tools_pkg  # noqa: F401
    from app.agente.models import AgentStep, AgentSession

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    _mk_session_with_response(sid, 'qual o frete?', 'O total é R$ 100,00.')

    # Plano com 1 step contendo entidades (aciona verify_domain)
    sess = AgentSession.query.filter_by(session_id=sid).first()
    sess.data['plan'] = {'steps': {'1': {'subject': 's', 'entities': ['Atacadao'], 'status': 'done'}}}
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(sess, 'data')
    _db.session.commit()

    # Mocks dos 3 verifiers (helpers mockáveis):
    monkeypatch.setattr(plan_verifier, '_call_haiku_verifier',
                        lambda prompt: json.dumps({'refuted': False, 'reason': 'ok'}))
    monkeypatch.setattr(verifiers, '_call_sonnet_verifier', lambda prompt: 'OK')
    import app.agente.tools.ontology_query_tool as _oqt
    monkeypatch.setattr(_oqt, 'query_ontology_entities',
                        lambda **kw: [{'name': 'Atacadao'}])
    monkeypatch.setattr(plan_verifier, 'create_app', lambda: app_ctx)

    # Spy no commit
    calls = []
    real_commit = _db.session.commit

    def _spy_commit():
        calls.append(1)
        real_commit()

    monkeypatch.setattr(_db.session, 'commit', _spy_commit)

    try:
        plan_verifier.verify_step_shadow(uid)

        assert len(calls) >= 1, "verify_step_shadow NAO chamou commit (CRITICAL-1)"

        _db.session.expire_all()
        step = AgentStep.query.filter_by(step_uid=uid).first()
        verify = (step.outcome_signal or {}).get('verify', {})
        assert 'adversarial' in verify
        assert 'arithmetic' in verify
        assert 'domain' in verify
    finally:
        monkeypatch.undo()
        _cleanup_step(uid)
        _cleanup_session(sid)


def test_verify_step_shadow_uid_inexistente_nao_crasha(app_ctx, monkeypatch):
    """step_uid inexistente → no-op seguro, não levanta exceção."""
    from app.agente.workers import plan_verifier

    monkeypatch.setattr(plan_verifier, 'create_app', lambda: app_ctx)
    plan_verifier.verify_step_shadow('uid-inexistente-shadow-nunca:777')


def test_verify_step_shadow_best_effort_um_verifier_falha(app_ctx, monkeypatch):
    """Se um verifier levanta exceção, os outros ainda gravam (best-effort).

    Mocka adversarial para LEVANTAR; arithmetic e domain seguem normais.
    Prova que outcome_signal['verify'] ainda é gravado com as sub-chaves
    dos verifiers que não falharam."""
    from app.agente.workers import plan_verifier
    from app.agente.sdk import verifiers
    from app.agente.models import AgentStep

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    _mk_session_with_response(sid, 'pergunta', 'resposta sem numeros')

    # adversarial LEVANTA dentro de _verify_core (via _call_haiku_verifier)
    def _boom(prompt):
        raise RuntimeError('haiku indisponivel')

    monkeypatch.setattr(plan_verifier, '_call_haiku_verifier', _boom)
    monkeypatch.setattr(verifiers, '_call_sonnet_verifier', lambda prompt: 'OK')
    monkeypatch.setattr(plan_verifier, 'create_app', lambda: app_ctx)

    try:
        # Não deve crashar
        plan_verifier.verify_step_shadow(uid)

        _db.session.expire_all()
        step = AgentStep.query.filter_by(step_uid=uid).first()
        verify = (step.outcome_signal or {}).get('verify', {})
        # Pelo menos arithmetic gravou (o verifier que não falhou)
        assert 'arithmetic' in verify
        assert verify['arithmetic'].get('ok') is True
    finally:
        _cleanup_step(uid)
        _cleanup_session(sid)


def test_verify_step_shadow_sem_resposta_skipa_arithmetic(app_ctx, monkeypatch):
    """Sessão sem resposta de assistente → arithmetic marcado skipped."""
    from app.agente.workers import plan_verifier
    from app.agente.models import AgentStep, AgentSession

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    # Sessão SEM mensagens de assistente
    sess, _ = AgentSession.get_or_create(session_id=sid, user_id=1)
    sess.add_user_message('só pergunta, sem resposta')
    _db.session.commit()

    monkeypatch.setattr(plan_verifier, '_call_haiku_verifier',
                        lambda prompt: json.dumps({'refuted': False, 'reason': 'ok'}))
    monkeypatch.setattr(plan_verifier, 'create_app', lambda: app_ctx)

    try:
        plan_verifier.verify_step_shadow(uid)

        _db.session.expire_all()
        step = AgentStep.query.filter_by(step_uid=uid).first()
        verify = (step.outcome_signal or {}).get('verify', {})
        assert verify.get('arithmetic', {}).get('skipped') == 'no_response_text'
    finally:
        _cleanup_step(uid)
        _cleanup_session(sid)


def test_verify_step_shadow_sem_plano_skipa_domain(app_ctx, monkeypatch):
    """Sessão sem plano → domain marcado skipped='no_plan'."""
    from app.agente.workers import plan_verifier
    from app.agente.sdk import verifiers
    from app.agente.models import AgentStep

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    _mk_session_with_response(sid, 'pergunta', 'resposta')  # sem data['plan']

    monkeypatch.setattr(plan_verifier, '_call_haiku_verifier',
                        lambda prompt: json.dumps({'refuted': False, 'reason': 'ok'}))
    monkeypatch.setattr(verifiers, '_call_sonnet_verifier', lambda prompt: 'OK')
    monkeypatch.setattr(plan_verifier, 'create_app', lambda: app_ctx)

    try:
        plan_verifier.verify_step_shadow(uid)

        _db.session.expire_all()
        step = AgentStep.query.filter_by(step_uid=uid).first()
        verify = (step.outcome_signal or {}).get('verify', {})
        assert verify.get('domain', {}).get('skipped') == 'no_plan'
    finally:
        _cleanup_step(uid)
        _cleanup_session(sid)


# ─── enqueue_pending_verifies ─────────────────────────────────────────────────

def test_enqueue_verifies_acha_step_sem_verify(app_ctx):
    """enqueue_pending_verifies enfileira verify_step_shadow com step_uid +
    job_id corretos para step recente sem outcome_signal['verify']."""
    from app.agente.workers import plan_verifier

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    mock_queue = MagicMock()

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_VERIFY', True):
            result = plan_verifier.enqueue_pending_verifies(queue=mock_queue)

        uids_chamados = []
        for call in mock_queue.enqueue.call_args_list:
            assert call.args[0] == 'app.agente.workers.plan_verifier.verify_step_shadow'
            uids_chamados.append(call.args[1])
            assert call.kwargs.get('job_id') == f"verify-step-{call.args[1].replace(':', '-')}"
            assert call.kwargs.get('job_timeout') == 180

        assert uid in uids_chamados
        assert result['enfileirados'] >= 1
    finally:
        _cleanup_step(uid)


def test_enqueue_verifies_ignora_step_com_verify(app_ctx):
    """Step que já tem outcome_signal['verify'] NÃO é re-enfileirado."""
    from app.agente.workers import plan_verifier
    from app.agente.models import AgentStep

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    AgentStep.update_outcome(uid, {'verify': {'adversarial': {'refuted': False}}})
    _db.session.commit()

    mock_queue = MagicMock()

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_VERIFY', True):
            plan_verifier.enqueue_pending_verifies(queue=mock_queue)

        uids_chamados = [c.args[1] for c in mock_queue.enqueue.call_args_list]
        assert uid not in uids_chamados
    finally:
        _cleanup_step(uid)


def test_enqueue_verifies_flag_off_nao_enfileira(app_ctx):
    """Com USE_AGENT_VERIFY=False, gate corta antes de tocar a fila."""
    from app.agente.workers import plan_verifier

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    mock_queue = MagicMock()

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_VERIFY', False):
            result = plan_verifier.enqueue_pending_verifies(queue=mock_queue)

        mock_queue.enqueue.assert_not_called()
        assert result['enfileirados'] == 0
        assert result['skipped'] == 'flag_off'
    finally:
        _cleanup_step(uid)


def test_enqueue_verifies_job_id_sem_dois_pontos_rq_safe(app_ctx):
    """RQ-safe: job_id gerado NÃO pode conter ':' (RQ 2.6.1 Job.set_id
    levanta ValueError se ':' in id). FALHARIA contra job_id=f'verify-step:{uid}'."""
    from app.agente.workers import plan_verifier

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    assert ':' in uid, "fixture inválida: step_uid deveria conter ':'"

    mock_queue = MagicMock()

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_VERIFY', True):
            plan_verifier.enqueue_pending_verifies(queue=mock_queue)

        nossa = next(
            (c for c in mock_queue.enqueue.call_args_list if c.args[1] == uid), None
        )
        assert nossa is not None
        job_id = nossa.kwargs.get('job_id')
        assert job_id is not None
        assert ':' not in job_id, (
            f"job_id '{job_id}' contém ':' — RQ 2.6.1 Job.set_id levantaria "
            f"ValueError e o enqueue falharia silenciosamente."
        )
        assert job_id == f"verify-step-{uid.replace(':', '-')}"
    finally:
        _cleanup_step(uid)


def test_enqueue_verifies_wiring_produtor_consumidor(app_ctx):
    """INTEGRAÇÃO: 2 steps (um sem verify, um com), o varredor enfileira SÓ
    o sem-verify, com o step_uid exato."""
    from app.agente.workers import plan_verifier
    from app.agente.models import AgentStep

    sid_sem = _mk_sid()
    sid_com = _mk_sid()
    uid_sem, _ = _mk_step(app_ctx, sid_sem)
    uid_com, _ = _mk_step(app_ctx, sid_com)
    AgentStep.update_outcome(uid_com, {'verify': {'adversarial': {'refuted': True}}})
    _db.session.commit()

    mock_queue = MagicMock()

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_VERIFY', True):
            plan_verifier.enqueue_pending_verifies(queue=mock_queue)

        uids_chamados = [c.args[1] for c in mock_queue.enqueue.call_args_list]
        assert uid_sem in uids_chamados
        assert uid_com not in uids_chamados
    finally:
        _cleanup_step(uid_sem)
        _cleanup_step(uid_com)


def test_enqueue_verifies_redis_down_best_effort(app_ctx):
    """Sem queue injetada + Redis indisponível → NÃO levanta, retorna
    skipped='redis_error' (INV-6 best-effort)."""
    from app.agente.workers import plan_verifier

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_VERIFY', True), \
             patch('redis.from_url', side_effect=Exception('redis down')):
            result = plan_verifier.enqueue_pending_verifies(queue=None)

        assert result['enfileirados'] == 0
        assert result.get('skipped') == 'redis_error'
        assert result['candidatos'] >= 1
    finally:
        _cleanup_step(uid)
