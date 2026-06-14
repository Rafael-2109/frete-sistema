"""Wiring de `agent_session_costs` no canal Teams — telemetria de custo per-turno.

GAP corrigido 2026-06-14: o path async do Teams (ATIVO em PROD) nunca gravava
agent_session_costs (so o canal web, via chat.py _persist_session_cost). Sem isto:
  - o canal Teams ficava invisivel no dashboard de custo;
  - era impossivel correlacionar MODELO <-> CACHE por turno — o que importa porque
    o prompt cache e MODEL-SCOPED e o smart routing do Teams alterna Sonnet<->Opus.

Prova que _persist_cost_teams():
  1. Grava exatamente 1 linha em agent_session_costs com model + cache breakdown
     (message_id sintetico = teams:{session}:{turn_seq}).
  2. E idempotente: 2 chamadas com o mesmo (session, turn_seq) gravam 1 linha so
     (UNIQUE message_id via SAVEPOINT — espelha PRIMARY+FALLBACK do canal Teams).
  3. best-effort: session=None retorna sem gravar e sem excecao.

Setup espelha tests/teams/test_agent_step_teams_wiring.py.
"""
import uuid
from dataclasses import dataclass
from typing import Optional, List

import pytest

from app import create_app, db as _db


@pytest.fixture(scope='module')
def app_ctx():
    """Flask app + app_context (escopo de módulo, espelha o wiring do agent_step)."""
    _app = create_app()
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    with _app.app_context():
        yield _app


@pytest.fixture(autouse=True)
def _force_cost_flag(monkeypatch):
    """USE_COST_TRACKER_PERSIST e' false no ambiente local (true em PROD, onde o web
    ja' grava). Força ON p/ o teste exercitar o mesmo caminho que roda em PROD.
    Patch no modulo feature_flags porque _persist_cost_teams o importa em runtime."""
    monkeypatch.setattr(
        'app.agente.config.feature_flags.USE_COST_TRACKER_PERSIST', True
    )


@dataclass
class _FakeAgentResult:
    """Simula o agent_result (StreamResult) do path async do Teams, com cache."""
    resposta_texto: str = 'resposta do agente via teams'
    input_tokens: int = 1500
    output_tokens: int = 300
    tools_used: Optional[List[str]] = None
    sdk_session_id: Optional[str] = None
    cache_read_tokens: int = 48000
    cache_creation_tokens: int = 2200


def _make_session(session_id: str, user_id: int = 1):
    """Cria AgentSession real no DB com user_message + assistant_message aplicados
    (turn_seq derivado de data['messages'], igual ao fluxo real)."""
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


def test_grava_um_cost_canal_teams(app_ctx):
    """Persistir 1 turno via _persist_cost_teams → exatamente 1 agent_session_costs
    com model + cache breakdown, message_id sintetico determinístico."""
    from app.teams.services import _persist_cost_teams
    from app.agente.models import AgentSessionCost

    our_session_id = f'teams_cost_{uuid.uuid4().hex}'
    user_id = 1
    fake = _FakeAgentResult()

    sess = _make_session(our_session_id, user_id)
    _persist_cost_teams(sess, user_id, 'claude-sonnet-4-6', fake, cost_usd=0.0123)

    rows = AgentSessionCost.query.filter_by(session_id=our_session_id).all()
    assert len(rows) == 1, f"esperado 1 cost, encontrado {len(rows)}"

    row = rows[0]
    assert row.model == 'claude-sonnet-4-6'
    assert row.input_tokens == 1500
    assert row.output_tokens == 300
    assert row.cache_read_tokens == 48000
    assert row.cache_creation_tokens == 2200
    assert row.user_id == user_id
    # data['messages'] tem 1 role=='user' → turn_seq == 1
    assert row.message_id == f'teams:{our_session_id}:1'

    _db.session.rollback()


def test_idempotencia_primario_fallback(app_ctx):
    """2 chamadas com o mesmo (session, turn_seq) → 1 linha só (UNIQUE message_id)."""
    from app.teams.services import _persist_cost_teams
    from app.agente.models import AgentSessionCost

    our_session_id = f'teams_cost_idem_{uuid.uuid4().hex}'
    user_id = 1
    fake = _FakeAgentResult()

    sess = _make_session(our_session_id, user_id)
    _persist_cost_teams(sess, user_id, 'claude-opus-4-8', fake, cost_usd=0.05)
    _persist_cost_teams(sess, user_id, 'claude-opus-4-8', fake, cost_usd=0.05)

    rows = AgentSessionCost.query.filter_by(session_id=our_session_id).all()
    assert len(rows) == 1, (
        f"idempotência violada: esperado 1, encontrado {len(rows)}"
    )
    assert rows[0].message_id == f'teams:{our_session_id}:1'

    _db.session.rollback()


def test_nao_grava_se_session_none(app_ctx):
    """best-effort: session=None → retorna sem gravar e sem exceção."""
    from app.teams.services import _persist_cost_teams

    fake = _FakeAgentResult()
    # Não deve lançar exceção
    _persist_cost_teams(None, 1, 'claude-opus-4-8', fake, cost_usd=0.0)

    _db.session.rollback()
