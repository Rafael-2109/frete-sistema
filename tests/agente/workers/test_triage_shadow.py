"""
Testa job RQ de triage shadow — Tarefa 2c (B-TRIAGE wiring em SHADOW).

Espelha o pattern de test_plan_verifier (T2b): job orquestrador
(triage_step_shadow) + varredor RQ batch (enqueue_pending_triages), gateados
pela flag USE_AGENT_PLANNER (OFF por default).

Cobertura:
- test_triage_step_shadow_grava_triage_e_commita: fluxo feliz — grava
  outcome_signal['triage'] com steps/grounded_entities + commit (spy CRITICAL-1)
- test_triage_step_shadow_uid_inexistente_nao_crasha: step inexistente → no-op
- test_triage_step_shadow_sem_meta_grava_skipped: sessão sem user msg → grava
  skipped='no_meta' sem crash (não re-tenta steps sem texto de usuário)
- test_enqueue_triages_acha_step_sem_triage: varredor enfileira step sem 'triage'
- test_enqueue_triages_ignora_step_com_triage: step com 'triage' NÃO é re-enfileirado
- test_enqueue_triages_flag_off_nao_enfileira: USE_AGENT_PLANNER=False → não toca fila
- test_enqueue_triages_job_id_sem_dois_pontos_rq_safe: job_id RQ-safe (sem ':')
- test_enqueue_triages_wiring_produtor_consumidor: 2 steps → só o sem-triage enfileirado
- test_enqueue_triages_redis_down_best_effort: Redis down → skipped='redis_error', sem raise
"""
import json
import uuid
import pytest

from app import create_app, db as _db


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def app_ctx():
    """Flask app context para testes do triage_shadow (escopo de módulo)."""
    _app = create_app()
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    with _app.app_context():
        yield _app


def _mk_sid():
    return f'tr-{uuid.uuid4().hex}'


def _mk_step(app_ctx, session_id: str, tools=None):
    """Insere e COMMITA um AgentStep de teste.

    Commita de propósito: triage_step_shadow abre um app_context aninhado
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


def _mk_session_with_user_msg(session_id: str, user_text: str, assistant_text: str = None):
    """Cria e COMMITA uma AgentSession com 1 turno (user[→assistant]).

    O turn_seq do step é a CONTAGEM de msgs role=='user' (ver chat.py:1836).
    1 user msg → turn_seq=1 → o meta do turno 1 é a 1ª msg role=='user'.
    Limpa via _cleanup_session.
    """
    from app.agente.models import AgentSession
    sess, _ = AgentSession.get_or_create(session_id=session_id, user_id=1)
    sess.add_user_message(user_text)
    if assistant_text is not None:
        sess.add_assistant_message(assistant_text)
    _db.session.commit()
    return sess


def _cleanup_session(session_id: str):
    from app.agente.models import AgentSession
    AgentSession.query.filter_by(session_id=session_id).delete()
    _db.session.commit()


# ─── triage_step_shadow ───────────────────────────────────────────────────────

def test_triage_step_shadow_grava_triage_e_commita(app_ctx, monkeypatch):
    """triage_step_shadow grava outcome_signal['triage'] com steps/grounded_entities
    e chama db.session.commit() (CRITICAL-1)."""
    from app.agente.workers import triage_shadow
    from app.agente.sdk import plan_triage
    from app.agente.models import AgentStep

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    _mk_session_with_user_msg(sid, 'Ver pedidos do Atacadao em aberto', 'Resposta.')

    # Mocks: triage_meta usa _call_llm_triage + query_ontology_entities (ambos
    # importados/mockáveis no módulo plan_triage).
    haiku_resp = json.dumps({
        'steps': [{'subject': 'Consultar pedidos do Atacadao', 'entities': ['Atacadao']}]
    })
    monkeypatch.setattr(plan_triage, '_call_llm_triage', lambda prompt: haiku_resp)
    monkeypatch.setattr(
        plan_triage, 'query_ontology_entities',
        lambda **kw: [{'entity_type': 'cliente', 'entity_name': 'Atacadao', 'entity_key': 'atacadao'}],
    )
    monkeypatch.setattr(triage_shadow, 'create_app', lambda: app_ctx)

    # Spy no commit (passthrough)
    calls = []
    real_commit = _db.session.commit

    def _spy_commit():
        calls.append(1)
        real_commit()

    monkeypatch.setattr(_db.session, 'commit', _spy_commit)

    try:
        triage_shadow.triage_step_shadow(uid)

        assert len(calls) >= 1, "triage_step_shadow NAO chamou commit (CRITICAL-1)"

        _db.session.expire_all()
        step = AgentStep.query.filter_by(step_uid=uid).first()
        triage = (step.outcome_signal or {}).get('triage', {})
        assert 'steps' in triage
        assert 'grounded_entities' in triage
        assert len(triage['steps']) == 1
        assert triage['steps'][0]['subject'] == 'Consultar pedidos do Atacadao'
        assert len(triage['grounded_entities']) == 1
    finally:
        monkeypatch.undo()
        _cleanup_step(uid)
        _cleanup_session(sid)


def test_triage_step_shadow_uid_inexistente_nao_crasha(app_ctx, monkeypatch):
    """step_uid inexistente → no-op seguro, não levanta exceção."""
    from app.agente.workers import triage_shadow

    monkeypatch.setattr(triage_shadow, 'create_app', lambda: app_ctx)
    triage_shadow.triage_step_shadow('uid-inexistente-triage-nunca:777')


def test_triage_step_shadow_sem_meta_grava_skipped(app_ctx, monkeypatch):
    """Sessão sem mensagem de usuário → meta None → grava skipped='no_meta'
    (não re-tenta no próximo ciclo) sem crash."""
    from app.agente.workers import triage_shadow
    from app.agente.models import AgentStep, AgentSession

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    # Sessão SEM mensagens de usuário (só existe, vazia)
    AgentSession.get_or_create(session_id=sid, user_id=1)
    _db.session.commit()

    monkeypatch.setattr(triage_shadow, 'create_app', lambda: app_ctx)

    try:
        triage_shadow.triage_step_shadow(uid)

        _db.session.expire_all()
        step = AgentStep.query.filter_by(step_uid=uid).first()
        triage = (step.outcome_signal or {}).get('triage', {})
        assert triage.get('skipped') == 'no_meta'
        # mantém shape de veredito válido (não re-tenta)
        assert triage.get('steps') == []
        assert triage.get('grounded_entities') == []
    finally:
        _cleanup_step(uid)
        _cleanup_session(sid)


# ─── enqueue_pending_triages ──────────────────────────────────────────────────

def test_enqueue_triages_acha_step_sem_triage(app_ctx):
    """enqueue_pending_triages enfileira triage_step_shadow com step_uid +
    job_id corretos para step recente sem outcome_signal['triage']."""
    from app.agente.workers import triage_shadow
    from unittest.mock import MagicMock, patch

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    mock_queue = MagicMock()

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_PLANNER', True):
            result = triage_shadow.enqueue_pending_triages(queue=mock_queue)

        uids_chamados = []
        for call in mock_queue.enqueue.call_args_list:
            assert call.args[0] == 'app.agente.workers.triage_shadow.triage_step_shadow'
            uids_chamados.append(call.args[1])
            assert call.kwargs.get('job_id') == f"triage-step-{call.args[1].replace(':', '-')}"
            assert call.kwargs.get('job_timeout') == 120

        assert uid in uids_chamados
        assert result['enfileirados'] >= 1
    finally:
        _cleanup_step(uid)


def test_enqueue_triages_ignora_step_com_triage(app_ctx):
    """Step que já tem outcome_signal['triage'] NÃO é re-enfileirado."""
    from app.agente.workers import triage_shadow
    from app.agente.models import AgentStep
    from unittest.mock import MagicMock, patch

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    AgentStep.update_outcome(uid, {'triage': {'steps': [], 'grounded_entities': []}})
    _db.session.commit()

    mock_queue = MagicMock()

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_PLANNER', True):
            triage_shadow.enqueue_pending_triages(queue=mock_queue)

        uids_chamados = [c.args[1] for c in mock_queue.enqueue.call_args_list]
        assert uid not in uids_chamados
    finally:
        _cleanup_step(uid)


def test_enqueue_triages_flag_off_nao_enfileira(app_ctx):
    """Com USE_AGENT_PLANNER=False, gate corta antes de tocar a fila."""
    from app.agente.workers import triage_shadow
    from unittest.mock import MagicMock, patch

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    mock_queue = MagicMock()

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_PLANNER', False):
            result = triage_shadow.enqueue_pending_triages(queue=mock_queue)

        mock_queue.enqueue.assert_not_called()
        assert result['enfileirados'] == 0
        assert result['skipped'] == 'flag_off'
    finally:
        _cleanup_step(uid)


def test_enqueue_triages_job_id_sem_dois_pontos_rq_safe(app_ctx):
    """RQ-safe: job_id gerado NÃO pode conter ':' (RQ 2.6.1 Job.set_id
    levanta ValueError se ':' in id). FALHARIA contra job_id=f'triage-step:{uid}'."""
    from app.agente.workers import triage_shadow
    from unittest.mock import MagicMock, patch

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    assert ':' in uid, "fixture inválida: step_uid deveria conter ':'"

    mock_queue = MagicMock()

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_PLANNER', True):
            triage_shadow.enqueue_pending_triages(queue=mock_queue)

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
        assert job_id == f"triage-step-{uid.replace(':', '-')}"
    finally:
        _cleanup_step(uid)


def test_enqueue_triages_wiring_produtor_consumidor(app_ctx):
    """INTEGRAÇÃO: 2 steps (um sem triage, um com), o varredor enfileira SÓ
    o sem-triage, com o step_uid exato."""
    from app.agente.workers import triage_shadow
    from app.agente.models import AgentStep
    from unittest.mock import MagicMock, patch

    sid_sem = _mk_sid()
    sid_com = _mk_sid()
    uid_sem, _ = _mk_step(app_ctx, sid_sem)
    uid_com, _ = _mk_step(app_ctx, sid_com)
    AgentStep.update_outcome(uid_com, {'triage': {'steps': [], 'grounded_entities': []}})
    _db.session.commit()

    mock_queue = MagicMock()

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_PLANNER', True):
            triage_shadow.enqueue_pending_triages(queue=mock_queue)

        uids_chamados = [c.args[1] for c in mock_queue.enqueue.call_args_list]
        assert uid_sem in uids_chamados
        assert uid_com not in uids_chamados
    finally:
        _cleanup_step(uid_sem)
        _cleanup_step(uid_com)


def test_enqueue_triages_redis_down_best_effort(app_ctx):
    """Sem queue injetada + Redis indisponível → NÃO levanta, retorna
    skipped='redis_error' (INV-6 best-effort)."""
    from app.agente.workers import triage_shadow
    from unittest.mock import patch

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_PLANNER', True), \
             patch('redis.from_url', side_effect=Exception('redis down')):
            result = triage_shadow.enqueue_pending_triages(queue=None)

        assert result['enfileirados'] == 0
        assert result.get('skipped') == 'redis_error'
        assert result['candidatos'] >= 1
    finally:
        _cleanup_step(uid)
