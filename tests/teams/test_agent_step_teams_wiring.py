"""Wiring do `agent_step` no canal Teams — Onda 0 / S0a-teams.

Prova que _gravar_agent_step_teams():
  1. Grava exatamente 1 linha em agent_step com channel='teams' após um turno
     (turn_seq derivado de data['messages'] após add_user/add_assistant).
  2. É idempotente: 2 chamadas com o mesmo (session, turn_seq) gravam 1 linha só
     (simula PRIMARY + FALLBACK do canal Teams — INV-3).

Setup segue o mesmo padrão do teste web (test_agent_step_wiring.py):
  - cria AgentSession real no DB de teste com session_id via uuid
  - user_id=1 (Rafael, FK sempre presente — evita violação de FK)
  - db.session.rollback() no fim de cada teste (isolamento)
"""
import uuid
from dataclasses import dataclass
from typing import Optional, List

import pytest

from app import create_app, db as _db


@pytest.fixture(scope='module')
def app_ctx():
    """Flask app + app_context (escopo de módulo, espelha test_agent_step_wiring.py)."""
    _app = create_app()
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    with _app.app_context():
        yield _app


@dataclass
class _FakeSyncResult:
    """Simula o _sync_result retornado por _obter_resposta_agente no Teams."""
    resposta_texto: str = 'resposta do agente via teams'
    input_tokens: int = 120
    output_tokens: int = 60
    tools_used: Optional[List[str]] = None
    sdk_session_id: Optional[str] = None
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


def _make_session(session_id: str, user_id: int = 1):
    """Cria AgentSession real no DB com user_message + assistant_message já aplicados.

    O turno é pré-populado porque _gravar_agent_step_teams deriva turn_seq DEPOIS
    de add_user_message + add_assistant_message (mesmo comportamento do PRIMARY real).
    """
    from app.agente.models import AgentSession
    sess = AgentSession(
        session_id=session_id,
        user_id=user_id,
        data={
            'messages': [
                {'role': 'user', 'content': 'mensagem de teste teams'},
                {'role': 'assistant', 'content': 'resposta do agente via teams'},
            ]
        },
    )
    _db.session.add(sess)
    _db.session.flush()
    return sess


def test_grava_um_step_canal_teams(app_ctx):
    """Persistir 1 turno via _gravar_agent_step_teams → exatamente 1 agent_step
    com channel='teams', joinável com a AgentSession."""
    from app.teams.services import _gravar_agent_step_teams
    from app.agente.models import AgentStep

    our_session_id = f'teams_test_conv_{uuid.uuid4().hex}'
    user_id = 1
    fake = _FakeSyncResult()

    sess = _make_session(our_session_id, user_id)
    _gravar_agent_step_teams(sess, user_id, 'claude-opus-4-8', fake)

    steps = AgentStep.query.filter_by(session_id=our_session_id).all()
    assert len(steps) == 1, f"esperado 1 step, encontrado {len(steps)}"

    step = steps[0]
    assert step.channel == 'teams'
    assert step.model == 'claude-opus-4-8'
    assert step.input_tokens == 120
    assert step.output_tokens == 60
    assert step.user_id == user_id
    # data['messages'] tem 1 role=='user' → turn_seq == 1
    assert step.step_uid == f'{our_session_id}:1'

    # Joinável: AgentSession com o mesmo session_id existe
    from app.agente.models import AgentSession
    found_sess = AgentSession.get_by_session_id(our_session_id)
    assert found_sess is not None
    assert found_sess.session_id == step.session_id

    _db.session.rollback()


def test_idempotencia_primario_fallback(app_ctx):
    """Simula PRIMARY + FALLBACK: 2 chamadas com o mesmo (session, turn_seq)
    → 1 step apenas (UNIQUE step_uid previne duplicata via SAVEPOINT)."""
    from app.teams.services import _gravar_agent_step_teams
    from app.agente.models import AgentStep

    our_session_id = f'teams_test_idem_{uuid.uuid4().hex}'
    user_id = 1
    fake = _FakeSyncResult()

    sess = _make_session(our_session_id, user_id)

    # Chamada 1 — simula bloco PRIMARY
    _gravar_agent_step_teams(sess, user_id, 'claude-opus-4-8', fake)
    # Chamada 2 — simula bloco FALLBACK (re-fetch pós SSL-drop, mesma session)
    _gravar_agent_step_teams(sess, user_id, 'claude-opus-4-8', fake)

    steps = AgentStep.query.filter_by(session_id=our_session_id).all()
    assert len(steps) == 1, (
        f"idempotência violada: esperado 1 step, encontrado {len(steps)} "
        "(PRIMARY + FALLBACK não devem duplicar o step)"
    )
    assert steps[0].step_uid == f'{our_session_id}:1'

    _db.session.rollback()


def test_nao_grava_se_session_none(app_ctx):
    """best-effort: session=None → helper retorna sem gravar e sem exceção."""
    from app.teams.services import _gravar_agent_step_teams
    from app.agente.models import AgentStep

    marker_id = f'teams_test_none_{uuid.uuid4().hex}'
    fake = _FakeSyncResult()

    # Não deve lançar exceção
    _gravar_agent_step_teams(None, 1, 'claude-opus-4-8', fake)

    steps = AgentStep.query.filter_by(session_id=marker_id).all()
    assert len(steps) == 0

    _db.session.rollback()


def test_grava_step_mesmo_sem_resposta_texto(app_ctx):
    """Simetria com o canal web: turno sem texto final (so-tools/erro) ainda gera
    1 agent_step — captura o turno + tokens p/ o flywheel (Onda 1). O guard so
    pula quando session is None."""
    from app.teams.services import _gravar_agent_step_teams
    from app.agente.models import AgentStep, AgentSession

    our_session_id = f'teams_test_empty_{uuid.uuid4().hex}'
    user_id = 1
    # Turno real sem texto: data tem so a mensagem do usuario (add_assistant_message
    # nao roda quando resposta_texto e' vazio no fluxo real).
    sess = AgentSession(
        session_id=our_session_id,
        user_id=user_id,
        data={'messages': [{'role': 'user', 'content': 'so tools, sem texto'}]},
    )
    _db.session.add(sess)
    _db.session.flush()
    fake = _FakeSyncResult(resposta_texto=None)  # type: ignore[arg-type]

    _gravar_agent_step_teams(sess, user_id, 'claude-opus-4-8', fake)

    steps = AgentStep.query.filter_by(session_id=our_session_id).all()
    assert len(steps) == 1
    assert steps[0].step_uid == f'{our_session_id}:1'
    assert steps[0].channel == 'teams'

    _db.session.rollback()
