"""Integração: wiring do `agent_step` no PRIMARY — Onda 0 Task 2 (S0a.2).

Prova que o sinal ATRAVESSA: ao persistir um turno pelo caminho protegido do
chat (`_save_messages_dedup` -> `_save_messages_to_db`), exatamente 1 linha em
`agent_step` é gravada no PRIMARY, joinável com a `AgentSession` da sessão, e
que o fluxo REAL (dedup com `_persisted`) NÃO duplica o step.

NUANCE turn_seq (resolvida): o wiring conta as mensagens com `role == 'user'`
em `session.data['messages']` NO PONTO da gravação, que roda DEPOIS de
`add_user_message`. Logo `turn_seq == N` para o N-ésimo turno. É estável no
fluxo real porque `_save_messages_dedup` protege a 2ª chamada via `_persisted`
(R10/INV-1): `_save_messages_to_db` roda 1x por turno, `add_user_message` é
chamado 1x, e o count é determinístico. O teste de idempotência exercita
exatamente esse caminho protegido (PRIMARY + DEFESA chamando dedup com o mesmo
`response_state`), não `_save_messages_to_db` direto.

Isolamento: session_ids via uuid (não depende de banco limpo). Mock de
`run_post_session_processing` no módulo chat para não disparar
summarization/pattern-learning/embeddings (Sonnet/RQ) — fora do escopo deste
sinal. `db.session.rollback()` no fim de cada teste.
"""
import uuid
from threading import Lock
from unittest.mock import patch

import pytest

from app import create_app, db as _db


@pytest.fixture(scope='module')
def app_ctx():
    """Flask app + app_context (escopo de módulo, espelha test_agent_step.py)."""
    _app = create_app()
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    with _app.app_context():
        yield _app


def _build_response_state(our_session_id: str, full_text: str = 'resposta do agente'):
    """Monta o `response_state` mínimo que `_save_messages_dedup` consome."""
    return {
        'full_text': full_text,
        'tools_used': ['Bash'],
        'input_tokens': 100,
        'output_tokens': 50,
        'cache_read_tokens': 0,
        'cache_creation_tokens': 0,
        'sdk_session_id': None,
        'our_session_id': our_session_id,
        'session_expired': False,
        'sdk_cost_usd': 0,
        '_persisted': False,
        '_save_lock': Lock(),
    }


def test_grava_um_step_joinavel(app_ctx):
    """Persistir 1 turno -> exatamente 1 agent_step com channel='web', joinável
    com a AgentSession (sessão existe)."""
    from app.agente.routes import chat as chat_mod
    from app.agente.models import AgentSession, AgentStep

    our_session_id = f'test-wiring-{uuid.uuid4().hex}'
    user_id = 1

    with patch.object(chat_mod, 'run_post_session_processing'):
        saved = chat_mod._save_messages_to_db(
            app=app_ctx,
            our_session_id=our_session_id,
            sdk_session_id=None,
            user_id=user_id,
            user_message='ola agente',
            assistant_message='resposta do agente',
            input_tokens=100,
            output_tokens=50,
            tools_used=['Bash'],
            model='claude-opus-4-8',
            session_expired=False,
        )

    assert saved is True

    steps = AgentStep.query.filter_by(session_id=our_session_id).all()
    assert len(steps) == 1, f"esperado 1 step, encontrado {len(steps)}"

    step = steps[0]
    assert step.channel == 'web'
    assert step.model == 'claude-opus-4-8'
    assert step.input_tokens == 100
    assert step.output_tokens == 50
    assert step.user_id == user_id
    # step_uid = "{session_id}:{turn_seq}"; turn_seq = nº de msgs role=='user'
    # em data['messages'] no ponto da gravação. Sessão NOVA (session_id via
    # uuid) -> data['messages'] só tem o user msg deste turno -> turn_seq == 1.
    assert step.step_uid == f'{our_session_id}:1'

    # Joinável: a AgentSession da mesma session_id existe (FK lógica)
    sess = AgentSession.get_by_session_id(our_session_id)
    assert sess is not None
    assert sess.session_id == step.session_id

    _db.session.rollback()


def test_idempotencia_fluxo_real(app_ctx):
    """Fluxo real: o turno é persistido 2x pelo caminho protegido
    (`_save_messages_dedup`, PRIMARY + DEFESA) com o MESMO `response_state`.
    A 2ª chamada dá skip via `_persisted=True` -> 1 step só (não duplica)."""
    from app.agente.routes import chat as chat_mod
    from app.agente.models import AgentStep

    our_session_id = f'test-wiring-idem-{uuid.uuid4().hex}'
    user_id = 1
    response_state = _build_response_state(our_session_id)

    with patch.object(chat_mod, 'run_post_session_processing'):
        # PRIMARY (thread daemon): persiste e marca _persisted=True
        chat_mod._save_messages_dedup(
            app=app_ctx,
            response_state=response_state,
            original_message='pergunta do usuario',
            user_id=user_id,
            model='claude-opus-4-8',
            source='thread_daemon',
        )
        assert response_state['_persisted'] is True

        # DEFESA (finally do generator): mesmo response_state -> skip via flag
        chat_mod._save_messages_dedup(
            app=app_ctx,
            response_state=response_state,
            original_message='pergunta do usuario',
            user_id=user_id,
            model='claude-opus-4-8',
            source='finally_generator',
        )

    steps = AgentStep.query.filter_by(session_id=our_session_id).all()
    assert len(steps) == 1, (
        f"fluxo real deve gravar 1 step só, encontrado {len(steps)} "
        "(dedup via _persisted não protegeu o agent_step)"
    )
    assert steps[0].step_uid == f'{our_session_id}:1'

    _db.session.rollback()
