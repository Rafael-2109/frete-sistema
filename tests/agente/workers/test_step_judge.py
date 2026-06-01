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

    Commita de proposito: judge_step abre um app_context ANINHADO (via
    create_app mockado p/ retornar o app_ctx do pytest), e o Flask cria uma
    sessao nova nesse escopo que NAO enxerga dados de SAVEPOINT pendentes (so'
    enxerga o que foi committado). Esse e' justamente o cenario de PRODUCAO:
    o step ja' esta committado no banco pelo caminho upstream quando o job RQ
    roda. Limpeza explicita via `_cleanup_step` no fim de cada teste — session_id
    e' uuid unico, sem cross-contaminacao.
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


def _cleanup_step(step_uid: str):
    """Remove o AgentStep committado de teste (evita orfaos no banco)."""
    from app.agente.models import AgentStep
    AgentStep.query.filter_by(step_uid=step_uid).delete()
    _db.session.commit()


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

    try:
        # commit REAL acontece dentro de judge_step (CRITICAL-1) — o veredito
        # e' consolidado no banco e fica visivel ao recarregar.
        step_judge.judge_step(uid)

        _db.session.expire_all()
        step = AgentStep.query.filter_by(step_uid=uid).first()
        assert step is not None
        assert step.outcome_signal is not None
        judge_data = step.outcome_signal.get('judge', {})
        assert judge_data.get('score') == 85
        assert judge_data.get('label') == 'success'
    finally:
        _cleanup_step(uid)


def test_judge_step_commita_veredito(app_ctx, monkeypatch):
    """
    CRITICAL-1 (code-review Onda 1): judge_step DEVE chamar db.session.commit()
    apos AgentStep.update_outcome.

    update_outcome usa begin_nested()+flush() (SAVEPOINT) — sem o commit
    explicito, o flush nunca e' consolidado e o veredito e' DESCARTADO quando
    o app_context do job RQ morre (transacao pai inexistente). Este teste
    ESPIONA db.session.commit e prova que e' chamado ao fim do fluxo feliz.

    O spy chama o commit REAL por baixo (passthrough) para que o veredito de
    fato persista — provando tanto a CHAMADA quanto a PERSISTENCIA. Limpeza
    explicita via _cleanup_step no fim.
    """
    from app.agente.workers import step_judge
    from app.agente.models import AgentStep

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)

    haiku_response = json.dumps({
        'score': 60,
        'label': 'partial',
        'componente_culpado': None,
        'evidencia': 'ok',
    }).replace(': None', ': null')

    monkeypatch.setattr(step_judge, '_call_haiku_judge', lambda *a, **k: haiku_response)
    monkeypatch.setattr(step_judge, 'create_app', lambda: app_ctx)

    # Spy: conta chamadas a commit E executa o commit REAL (passthrough),
    # provando a chamada (CRITICAL-1) e a persistencia do veredito.
    calls = []
    real_commit = _db.session.commit

    def _spy_commit():
        calls.append(1)
        real_commit()

    monkeypatch.setattr(_db.session, 'commit', _spy_commit)

    import app.agente.workers.step_judge as _sj
    original_judge_core = _sj._judge_core

    def _judge_core_sem_odoo(step, odoo_ops):
        return original_judge_core(step, [])

    monkeypatch.setattr(step_judge, '_judge_core', _judge_core_sem_odoo)

    try:
        step_judge.judge_step(uid)

        # PROVA: o commit foi chamado (sem isso o veredito sumiria em producao)
        assert len(calls) >= 1, (
            "judge_step NAO chamou db.session.commit() — veredito seria descartado "
            "quando o app_context do job RQ morre (CRITICAL-1)."
        )

        # E o veredito de fato persistiu (commit real executado via passthrough)
        _db.session.expire_all()
        step = AgentStep.query.filter_by(step_uid=uid).first()
        assert step.outcome_signal.get('judge', {}).get('score') == 60
    finally:
        # restaura commit real para o cleanup nao re-entrar no spy
        monkeypatch.undo()
        _cleanup_step(uid)


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

    try:
        # commit REAL dentro de judge_step (CRITICAL-1) consolida o veredito.
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
    finally:
        _cleanup_step(uid)


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

    try:
        # _judge_core retorna None (JSON invalido) -> judge_step retorna ANTES
        # do commit, sem gravar veredito.
        step_judge.judge_step(uid)

        _db.session.expire_all()
        step = AgentStep.query.filter_by(step_uid=uid).first()
        # outcome_signal pode ser None ou pode ter outros campos, mas NAO 'judge'
        if step.outcome_signal is not None:
            assert 'judge' not in step.outcome_signal
    finally:
        _cleanup_step(uid)


# ─── E2 — Varredor RQ (enqueue_pending_judges) ────────────────────────────────
# WIRING da Onda 3 / A3: torna funcional o varredor batch que enfileira judge_step
# para steps recentes sem veredito. Padrao de mock de Queue/Redis espelhado de
# tests/agente/sdk/test_hooks_enqueue_validation.py.

from unittest.mock import MagicMock, patch  # noqa: E402


def test_enqueue_acha_step_sem_judge(app_ctx):
    """enqueue_pending_judges enfileira judge_step com step_uid + job_id corretos
    para um step recente que ainda nao tem veredito 'judge'."""
    from app.agente.workers import step_judge

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    mock_queue = MagicMock()

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_STEP_JUDGE', True):
            result = step_judge.enqueue_pending_judges(queue=mock_queue)

        # O step de teste deve estar entre os enfileirados
        chamadas = mock_queue.enqueue.call_args_list
        uids_chamados = []
        for call in chamadas:
            # args[0] = dotted-path, args[1] = step_uid
            assert call.args[0] == 'app.agente.workers.step_judge.judge_step'
            uids_chamados.append(call.args[1])
            # job_id deterministico e RQ-safe (sem ':' — ver C1)
            assert call.kwargs.get('job_id') == f"judge-step-{call.args[1].replace(':', '-')}"
            assert call.kwargs.get('job_timeout') == 120

        assert uid in uids_chamados, (
            f"step {uid} sem judge deveria ter sido enfileirado; "
            f"enfileirados={uids_chamados}"
        )
        assert result['enfileirados'] >= 1
    finally:
        _cleanup_step(uid)


def test_enqueue_ignora_step_com_judge(app_ctx):
    """Step que ja tem outcome_signal['judge'] NAO e re-enfileirado."""
    from app.agente.workers import step_judge
    from app.agente.models import AgentStep

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    # Marca o step como ja julgado
    AgentStep.update_outcome(uid, {'judge': {'score': 50, 'label': 'partial'}})
    _db.session.commit()

    mock_queue = MagicMock()

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_STEP_JUDGE', True):
            step_judge.enqueue_pending_judges(queue=mock_queue)

        uids_chamados = [c.args[1] for c in mock_queue.enqueue.call_args_list]
        assert uid not in uids_chamados, (
            f"step {uid} JA julgado nao deveria ser re-enfileirado; "
            f"enfileirados={uids_chamados}"
        )
    finally:
        _cleanup_step(uid)


def test_enqueue_flag_off_nao_enfileira(app_ctx):
    """Com USE_AGENT_STEP_JUDGE=False, gate corta antes de tocar a fila."""
    from app.agente.workers import step_judge

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    mock_queue = MagicMock()

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_STEP_JUDGE', False):
            result = step_judge.enqueue_pending_judges(queue=mock_queue)

        mock_queue.enqueue.assert_not_called()
        assert result['enfileirados'] == 0
        assert result['skipped'] == 'flag_off'
    finally:
        _cleanup_step(uid)


def test_enqueue_ignora_step_fora_da_janela(app_ctx):
    """Step com created_at anterior ao lookback NAO entra na janela e nao e
    enfileirado. Controlamos a janela passando `now` deterministicamente."""
    import datetime
    from app.agente.workers import step_judge

    sid = _mk_sid()
    uid, step = _mk_step(app_ctx, sid)
    mock_queue = MagicMock()

    try:
        # 'now' 100h depois do created_at do step -> com lookback=6h, fora da janela.
        future_now = step.created_at + datetime.timedelta(hours=100)
        with patch('app.agente.config.feature_flags.USE_AGENT_STEP_JUDGE', True):
            step_judge.enqueue_pending_judges(
                queue=mock_queue, now=future_now, lookback_hours=6
            )

        uids_chamados = [c.args[1] for c in mock_queue.enqueue.call_args_list]
        assert uid not in uids_chamados, (
            f"step {uid} fora da janela (>6h) nao deveria ser enfileirado; "
            f"enfileirados={uids_chamados}"
        )
    finally:
        _cleanup_step(uid)


def test_enqueue_redis_down_best_effort(app_ctx):
    """Sem queue injetada + Redis indisponivel -> NAO levanta excecao,
    retorna dict com skipped='redis_error' (INV-6 best-effort)."""
    from app.agente.workers import step_judge

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_STEP_JUDGE', True), \
             patch('redis.from_url', side_effect=Exception('redis down')):
            # queue=None forca construcao real da fila (que falha no Redis)
            result = step_judge.enqueue_pending_judges(queue=None)

        assert result['enfileirados'] == 0
        assert result.get('skipped') == 'redis_error'
        assert result['candidatos'] >= 1
    finally:
        _cleanup_step(uid)


def test_enqueue_wiring_produtor_consumidor(app_ctx):
    """INTEGRACAO (DoD): com DOIS steps commitados (um sem judge, um com judge),
    o varredor enfileira SO o sem-judge, com o step_uid exato."""
    from app.agente.workers import step_judge
    from app.agente.models import AgentStep

    sid_sem = _mk_sid()
    sid_com = _mk_sid()
    uid_sem, _ = _mk_step(app_ctx, sid_sem)
    uid_com, _ = _mk_step(app_ctx, sid_com)
    # Marca o segundo como ja julgado
    AgentStep.update_outcome(uid_com, {'judge': {'score': 90, 'label': 'success'}})
    _db.session.commit()

    mock_queue = MagicMock()

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_STEP_JUDGE', True):
            step_judge.enqueue_pending_judges(queue=mock_queue)

        uids_chamados = [c.args[1] for c in mock_queue.enqueue.call_args_list]
        assert uid_sem in uids_chamados, (
            f"step sem judge {uid_sem} deveria ser enfileirado"
        )
        assert uid_com not in uids_chamados, (
            f"step com judge {uid_com} NAO deveria ser enfileirado"
        )
    finally:
        _cleanup_step(uid_sem)
        _cleanup_step(uid_com)


def test_enqueue_job_id_sem_dois_pontos_rq_safe(app_ctx):
    """C1 (CRITICAL): o job_id gerado NAO pode conter ':'.

    step_uid e '{session_id}:{turn_seq}' (sempre tem ':'). RQ 2.6.1
    Job.set_id faz `if ':' in value: raise ValueError` — logo um job_id
    com ':' levantaria a cada enqueue e o try/except por-step engoliria
    silenciosamente (enfileirados=0, feature inerte). Este teste prova
    que o id gerado e RQ-safe SEM depender de Redis/fakeredis (o MagicMock
    nao valida; a garantia vem da asserção sobre o id).

    FALHARIA contra o codigo antigo (job_id=f'judge-step:{step_uid}').
    """
    from app.agente.workers import step_judge

    sid = _mk_sid()
    uid, _ = _mk_step(app_ctx, sid)
    # Pre-condicao do teste: o step_uid realmente contem ':'
    assert ':' in uid, "fixture invalida: step_uid de teste deveria conter ':'"

    mock_queue = MagicMock()

    try:
        with patch('app.agente.config.feature_flags.USE_AGENT_STEP_JUDGE', True):
            step_judge.enqueue_pending_judges(queue=mock_queue)

        # Localiza a chamada referente ao nosso step
        nossa_chamada = next(
            (c for c in mock_queue.enqueue.call_args_list if c.args[1] == uid),
            None,
        )
        assert nossa_chamada is not None, (
            f"step {uid} deveria ter sido enfileirado"
        )
        job_id = nossa_chamada.kwargs.get('job_id')
        assert job_id is not None, "job_id ausente no enqueue"
        assert ':' not in job_id, (
            f"job_id '{job_id}' contem ':' — RQ 2.6.1 Job.set_id levantaria "
            f"ValueError e o enqueue falharia silenciosamente (C1)."
        )
        # E o id deve permanecer rastreavel ao step (derivado do step_uid)
        assert job_id == f"judge-step-{uid.replace(':', '-')}"
    finally:
        _cleanup_step(uid)
