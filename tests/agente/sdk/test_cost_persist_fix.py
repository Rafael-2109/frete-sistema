"""TDD do fix de persistencia de custo (T0.2 CORRIGIDO, 2026-06-05).

Causa raiz REAL (o diagnostico anterior do T0.2 estava ERRADO — culpou a flag):
`cost_tracker._persist_to_db` chamava `AgentSessionCost.insert_entry`
(begin_nested/SAVEPOINT) de DENTRO do loop de streaming, cujo app_context NAO
consolida o savepoint. Por contraste, `AgentSession.total_cost_usd` SEMPRE
persistiu porque `_save_messages_to_db` tem app_context dedicado + commit()
EXPLICITO (e `AgentInvocationMetric`/A1 idem). Resultado: agent_session_costs
ficava VAZIA mesmo com a flag ON.

Fix: a persistencia per-message foi movida para `_persist_session_cost`, chamada
DE DENTRO de `_save_messages_to_db` (mesmo context+commit comprovado). Estes
testes travam: (1) reproducao da causa; (2) o fix persiste com breakdown de
cache; (3) idempotencia; (4) flag OFF nao persiste.
"""
from unittest.mock import patch

from app import db
from app.agente.models import AgentSessionCost

_FLAG = 'app.agente.config.feature_flags.USE_COST_TRACKER_PERSIST'


def _cleanup(app, mid):
    with app.app_context():
        AgentSessionCost.query.filter_by(message_id=mid).delete()
        db.session.commit()


def test_repro_savepoint_sem_commit_nao_persiste(app):
    """Causa raiz: o SAVEPOINT (begin_nested) do insert_entry e' perdido se o
    context faz rollback / nao commita — exatamente o do loop de streaming."""
    mid = 'repro-nocommit-1'
    _cleanup(app, mid)
    try:
        with app.app_context():
            AgentSessionCost.insert_entry(
                message_id=mid, input_tokens=10, output_tokens=5, cost_usd=0.01,
                session_id='s', user_id=1,
            )
            db.session.rollback()  # context que NAO consolida o savepoint
        with app.app_context():
            assert AgentSessionCost.query.filter_by(message_id=mid).first() is None
    finally:
        _cleanup(app, mid)


def test_fix_persist_session_cost_com_commit(app):
    """O fix persiste o breakdown de cache quando chamado em context que commita."""
    from app.agente.routes.chat import _persist_session_cost
    mid = 'fix-persist-1'
    _cleanup(app, mid)
    try:
        with patch(_FLAG, True):
            with app.app_context():
                _persist_session_cost(
                    message_id=mid, session_id='sess-fix', user_id=1,
                    input_tokens=100, output_tokens=50,
                    cache_read_tokens=900, cache_creation_tokens=10,
                    cost_usd=0.05, model='claude-opus-4-8',
                )
                db.session.commit()
        with app.app_context():
            row = AgentSessionCost.query.filter_by(message_id=mid).first()
            assert row is not None, 'cost nao persistido no context que commita'
            assert row.cache_read_tokens == 900
            assert row.session_id == 'sess-fix'
            assert float(row.cost_usd) == 0.05
    finally:
        _cleanup(app, mid)


def test_fix_idempotente_message_id(app):
    from app.agente.routes.chat import _persist_session_cost
    mid = 'fix-idem-1'
    _cleanup(app, mid)
    try:
        with patch(_FLAG, True):
            with app.app_context():
                _persist_session_cost(message_id=mid, session_id='s', user_id=1,
                    input_tokens=1, output_tokens=1, cache_read_tokens=0,
                    cache_creation_tokens=0, cost_usd=0.01, model='m')
                db.session.commit()
                _persist_session_cost(message_id=mid, session_id='s', user_id=1,
                    input_tokens=99, output_tokens=99, cache_read_tokens=0,
                    cache_creation_tokens=0, cost_usd=0.99, model='m')
                db.session.commit()
        with app.app_context():
            assert AgentSessionCost.query.filter_by(message_id=mid).count() == 1
    finally:
        _cleanup(app, mid)


def test_fix_flag_off_nao_persiste(app):
    from app.agente.routes.chat import _persist_session_cost
    mid = 'fix-off-1'
    _cleanup(app, mid)
    try:
        with patch(_FLAG, False):
            with app.app_context():
                _persist_session_cost(message_id=mid, session_id='s', user_id=1,
                    input_tokens=1, output_tokens=1, cache_read_tokens=0,
                    cache_creation_tokens=0, cost_usd=0.01, model='m')
                db.session.commit()
        with app.app_context():
            assert AgentSessionCost.query.filter_by(message_id=mid).first() is None
    finally:
        _cleanup(app, mid)
