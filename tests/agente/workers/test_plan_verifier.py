"""
Testa job RQ de verifier adversarial — Parte B (B2, Onda 2).

Atualizado 2026-06-12 (paridade de matéria + fim do viés cego + Sonnet):
- o adversarial agora recebe pergunta/resposta/auditoria Odoo (paridade com o judge);
- sem matéria (pergunta E resposta indisponíveis) → NÃO chama o LLM e grava
  {'refuted': False, 'skipped': True, 'reason': 'sem_materia'} (chave aditiva);
- JSON sem campo 'refuted' → padrão refuted=False (refutar exige razão explícita);
- modelo: ADVERSARIAL_MODEL (Sonnet) via _call_adversarial_verifier.

Cobertura:
- test_verify_plan_adversarial_persiste_veredito: fluxo feliz — veredito persiste em outcome_signal['verify']
- test_verify_plan_adversarial_commita(spy): CRITICAL-1 — db.session.commit() é chamado (spy passthrough)
- test_verify_core_refuta / _ok / _json_invalido: contrato do núcleo
- test_skip_sem_materia_*: skip-sem-matéria não toca o LLM
- test_prompt_*: paridade de matéria no prompt
- test_system_prompt_sem_vies_cego / test_modelo_adversarial_sonnet
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

class _FakeStepBase:
    step_uid = 'sess-fake-pv:1'
    session_id = 'sess-fake-pv'
    tools_used = ['cotando-frete']
    outcome_signal = None


def test_verify_core_refuta(monkeypatch):
    """_verify_core retorna refuted=True quando o modelo refuta a conclusão."""
    from app.agente.workers import plan_verifier

    resp = json.dumps({'refuted': True, 'reason': 'Frete calculado sem considerar peso cubado'})
    monkeypatch.setattr(plan_verifier, '_call_adversarial_verifier', lambda prompt: resp)

    result = plan_verifier._verify_core(
        _FakeStepBase(), meta='qual o frete?', response='O frete é R$ 100.'
    )

    assert result is not None
    assert result['refuted'] is True
    assert 'reason' in result
    assert len(result['reason']) > 0


def test_verify_core_ok(monkeypatch):
    """_verify_core retorna refuted=False quando o modelo não consegue refutar."""
    from app.agente.workers import plan_verifier

    resp = json.dumps({'refuted': False, 'reason': 'Conclusão consistente com dados disponíveis'})
    monkeypatch.setattr(plan_verifier, '_call_adversarial_verifier', lambda prompt: resp)

    result = plan_verifier._verify_core(
        _FakeStepBase(), meta='qual o frete?', response='O frete é R$ 100.'
    )

    assert result is not None
    assert result['refuted'] is False


def test_verify_core_json_invalido(monkeypatch):
    """JSON inválido do modelo → best-effort, _verify_core retorna None."""
    from app.agente.workers import plan_verifier

    monkeypatch.setattr(plan_verifier, '_call_adversarial_verifier',
                        lambda prompt: 'nao e json valido')

    result = plan_verifier._verify_core(
        _FakeStepBase(), meta='pergunta', response='resposta'
    )

    assert result is None


def test_default_nao_refuta_sem_campo_refuted(monkeypatch):
    """JSON sem 'refuted' → padrão é refuted=False (refutar exige razão
    explícita — fim do viés 'na dúvida, REFUTE')."""
    from app.agente.workers import plan_verifier

    resp = json.dumps({'reason': 'inconclusivo'})
    monkeypatch.setattr(plan_verifier, '_call_adversarial_verifier', lambda prompt: resp)

    result = plan_verifier._verify_core(
        _FakeStepBase(), meta='pergunta', response='resposta'
    )

    assert result is not None
    assert result['refuted'] is False


def test_skip_sem_materia_nao_chama_llm(monkeypatch):
    """Pergunta E resposta indisponíveis → NÃO chama o LLM; grava veredito
    skipped {'refuted': False, 'skipped': True, 'reason': 'sem_materia'}."""
    from app.agente.workers import plan_verifier

    def _explode(prompt):
        raise AssertionError('LLM NAO deveria ser chamado sem matéria')

    monkeypatch.setattr(plan_verifier, '_call_adversarial_verifier', _explode)

    result = plan_verifier._verify_core(_FakeStepBase(), meta=None, response=None)

    assert result == {'refuted': False, 'skipped': True, 'reason': 'sem_materia'}


def test_skip_sem_materia_strings_vazias(monkeypatch):
    """Strings vazias/whitespace contam como matéria indisponível."""
    from app.agente.workers import plan_verifier

    def _explode(prompt):
        raise AssertionError('LLM NAO deveria ser chamado sem matéria')

    monkeypatch.setattr(plan_verifier, '_call_adversarial_verifier', _explode)

    result = plan_verifier._verify_core(_FakeStepBase(), meta='  ', response='')
    assert result['skipped'] is True and result['refuted'] is False


def test_so_pergunta_disponivel_chama_llm(monkeypatch):
    """Com SÓ a pergunta disponível, há matéria parcial → LLM é chamado."""
    from app.agente.workers import plan_verifier

    chamadas = []

    def _fake(prompt):
        chamadas.append(prompt)
        return json.dumps({'refuted': False, 'reason': 'matéria insuficiente'})

    monkeypatch.setattr(plan_verifier, '_call_adversarial_verifier', _fake)

    result = plan_verifier._verify_core(_FakeStepBase(), meta='qual o frete?', response=None)
    assert len(chamadas) == 1
    assert result['refuted'] is False
    assert 'skipped' not in result


def test_prompt_contem_pergunta_resposta_tools_e_auditoria():
    """Paridade de matéria: o prompt do adversarial inclui pergunta (1500c),
    resposta (3000c), tools e auditoria Odoo — mesmo material do judge."""
    from app.agente.workers.plan_verifier import _build_adversarial_prompt

    class _Op:
        status = 'EXECUTADO'
        modelo_odoo = 'stock.picking'
        metodo_odoo = 'button_validate'

    prompt = _build_adversarial_prompt(
        _FakeStepBase(),
        odoo_ops=[_Op()],
        meta='quanto de palmito tem em estoque?',
        response='Ha 1.234 caixas de palmito disponiveis.',
    )

    assert 'quanto de palmito tem em estoque?' in prompt
    assert 'Ha 1.234 caixas de palmito disponiveis.' in prompt
    assert 'cotando-frete' in prompt
    assert 'EXECUTADO: 1' in prompt
    assert 'stock.picking' in prompt


def test_prompt_sem_materia_marca_indisponivel():
    """Sem meta/response o prompt marca explicitamente a indisponibilidade
    (caminho usado apenas quando há matéria parcial)."""
    from app.agente.workers.plan_verifier import _build_adversarial_prompt

    prompt = _build_adversarial_prompt(_FakeStepBase(), meta='pergunta x', response=None)
    assert 'pergunta x' in prompt
    assert '(resposta do agente nao disponivel)' in prompt


def test_prompt_trunca_pergunta_resposta():
    """Orçamento de tokens: pergunta truncada em 1500c e resposta em 3000c."""
    from app.agente.workers.plan_verifier import _build_adversarial_prompt

    prompt = _build_adversarial_prompt(
        _FakeStepBase(), meta='P' * 5000, response='R' * 9000,
    )
    assert 'P' * 1500 in prompt and 'P' * 1501 not in prompt
    assert 'R' * 3000 in prompt and 'R' * 3001 not in prompt


def test_system_prompt_sem_vies_cego():
    """O system prompt NÃO carrega mais o viés 'na dúvida, REFUTE'; exige razão
    concreta, prevê 'matéria insuficiente' e proporcionalidade."""
    from app.agente.workers.plan_verifier import ADVERSARIAL_SYSTEM_PROMPT

    assert 'na dúvida, REFUTE' not in ADVERSARIAL_SYSTEM_PROMPT
    assert 'razão concreta' in ADVERSARIAL_SYSTEM_PROMPT
    assert 'matéria insuficiente' in ADVERSARIAL_SYSTEM_PROMPT
    assert 'Proporcionalidade' in ADVERSARIAL_SYSTEM_PROMPT


def test_modelo_adversarial_sonnet():
    """Doutrina: modelo fraco não audita forte — adversarial roda em Sonnet."""
    from app.agente.workers.plan_verifier import ADVERSARIAL_MODEL

    assert ADVERSARIAL_MODEL == 'claude-sonnet-4-6'


def test_verify_plan_adversarial_uid_inexistente_nao_crasha(app_ctx, monkeypatch):
    """step_uid inexistente → no-op seguro, não levanta exceção."""
    from app.agente.workers import plan_verifier

    monkeypatch.setattr(plan_verifier, 'create_app', lambda: app_ctx)

    # Não deve levantar exceção
    plan_verifier.verify_plan_adversarial('uid-inexistente-nunca-pv:999')


# ─── Testes de integração (com DB) ───────────────────────────────────────────

def test_verify_plan_adversarial_persiste_veredito(app_ctx, monkeypatch):
    """Fluxo feliz: verify_plan_adversarial persiste veredito em outcome_signal['verify'].

    Cria sessão com 1 turno (matéria disponível) — sem ela o verifier skipa
    o LLM (skip-sem-matéria) e o veredito mockado nunca seria usado.
    """
    from app.agente.workers import plan_verifier
    from app.agente.models import AgentStep

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    _mk_session_with_response(sid, 'qual o frete para Manaus?', 'O frete é R$ 100,00.')

    resp = json.dumps({'refuted': True, 'reason': 'Premissa não suportada pelos dados'})

    monkeypatch.setattr(plan_verifier, '_call_adversarial_verifier', lambda prompt: resp)
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
        _cleanup_session(sid)


def test_verify_plan_adversarial_sem_materia_persiste_skip(app_ctx, monkeypatch):
    """Step SEM sessão (sem pergunta/resposta) → persiste o veredito skipped
    sem chamar o LLM: {'refuted': False, 'skipped': True, 'reason': 'sem_materia'}."""
    from app.agente.workers import plan_verifier
    from app.agente.models import AgentStep

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)  # sem AgentSession correspondente

    def _explode(prompt):
        raise AssertionError('LLM NAO deveria ser chamado sem matéria')

    monkeypatch.setattr(plan_verifier, '_call_adversarial_verifier', _explode)
    monkeypatch.setattr(plan_verifier, 'create_app', lambda: app_ctx)

    try:
        plan_verifier.verify_plan_adversarial(uid)

        _db.session.expire_all()
        step = AgentStep.query.filter_by(step_uid=uid).first()
        verify_data = (step.outcome_signal or {}).get('verify', {})
        assert verify_data.get('refuted') is False
        assert verify_data.get('skipped') is True
        assert verify_data.get('reason') == 'sem_materia'
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
    _mk_session_with_response(sid, 'qual o frete?', 'O frete é R$ 50,00.')

    resp = json.dumps({'refuted': False, 'reason': 'Conclusão plausível'})
    monkeypatch.setattr(plan_verifier, '_call_adversarial_verifier', lambda prompt: resp)
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
        assert 'skipped' not in step.outcome_signal.get('verify', {})
    finally:
        monkeypatch.undo()
        _cleanup_step(uid)
        _cleanup_session(sid)


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
    monkeypatch.setattr(plan_verifier, '_call_adversarial_verifier',
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

    # adversarial LEVANTA dentro de _verify_core (via _call_adversarial_verifier)
    def _boom(prompt):
        raise RuntimeError('haiku indisponivel')

    monkeypatch.setattr(plan_verifier, '_call_adversarial_verifier', _boom)
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

    monkeypatch.setattr(plan_verifier, '_call_adversarial_verifier',
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

    monkeypatch.setattr(plan_verifier, '_call_adversarial_verifier',
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
