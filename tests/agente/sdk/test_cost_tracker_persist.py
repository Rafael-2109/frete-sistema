"""
Testes T0.2 (2026-06-05) — regressao da persistencia de custo em
agent_session_costs (write-through do cost_tracker, flag AGENT_COST_TRACKER_PERSIST).

CONTEXTO (causa raiz da tabela VAZIA em PROD, 2026-05-09..2026-06-05):
NAO era bug de codigo. O projeto tem commit-on-teardown
(`app/__init__.py:1415` — `@app.teardown_appcontext` faz `db.session.commit()`
quando nao ha excecao), que consolida o `begin_nested()` (SAVEPOINT) do
`insert_entry` no fim de QUALQUER app_context — inclusive o manual da thread
daemon do stream (`chat.py:483`). Ou seja: com a flag LIGADA o cost persiste.
A tabela estava vazia porque `AGENT_COST_TRACKER_PERSIST` estava OFF em PROD.

Hipotese inicial "savepoint orfao na thread daemon" foi REFUTADA pelo TDD +
experimento (flush sem commit explicito persiste localmente porque o teardown
commita). Estes testes travam o comportamento correto: flag ON grava, flag OFF
nao grava, idempotente por message_id.
"""
from unittest.mock import patch

# A flag e importada DENTRO de record_cost (lazy), entao o patch alvo e a origem.
_FLAG = 'app.agente.config.feature_flags.USE_COST_TRACKER_PERSIST'


def _cleanup(app, message_id):
    from app.agente.models import AgentSessionCost
    from app import db
    with app.app_context():
        AgentSessionCost.query.filter_by(message_id=message_id).delete()
        db.session.commit()


def test_record_cost_persists_when_flag_on(app):
    """
    Com a flag LIGADA, record_cost grava a entrada (com breakdown de cache) em
    agent_session_costs. O commit-on-teardown do projeto consolida o write ao
    fechar o app_context — mesmo padrao da thread daemon do stream em PROD.
    """
    from app.agente.sdk.cost_tracker import CostTracker
    from app.agente.models import AgentSessionCost

    msg_id = 'test-t02-on-1'
    _cleanup(app, msg_id)
    try:
        with patch(_FLAG, True):
            with app.app_context():
                tracker = CostTracker()
                tracker.record_cost(
                    message_id=msg_id,
                    input_tokens=100,
                    output_tokens=50,
                    session_id='sess-t02',
                    user_id=1,
                    cache_read_tokens=900,
                    cache_creation_tokens=10,
                )
        with app.app_context():
            row = AgentSessionCost.query.filter_by(message_id=msg_id).first()
            assert row is not None, 'cost nao persistido com flag ON'
            assert row.cache_read_tokens == 900
            assert row.input_tokens == 100
            assert float(row.cost_usd) >= 0
    finally:
        _cleanup(app, msg_id)


def test_record_cost_flag_off_does_not_persist(app):
    """Com a flag OFF (estado de PROD que causou a tabela vazia), nada e gravado."""
    from app.agente.sdk.cost_tracker import CostTracker
    from app.agente.models import AgentSessionCost

    msg_id = 'test-t02-off-1'
    _cleanup(app, msg_id)
    try:
        with patch(_FLAG, False):
            with app.app_context():
                tracker = CostTracker()
                tracker.record_cost(
                    message_id=msg_id,
                    input_tokens=10,
                    output_tokens=5,
                    session_id='sess-off',
                    user_id=1,
                )
        with app.app_context():
            row = AgentSessionCost.query.filter_by(message_id=msg_id).first()
            assert row is None
    finally:
        _cleanup(app, msg_id)


def test_record_cost_idempotent_on_duplicate_message_id(app):
    """message_id duplicado (UNIQUE) nao quebra — 2a persistencia e no-op."""
    from app.agente.sdk.cost_tracker import CostTracker
    from app.agente.models import AgentSessionCost

    msg_id = 'test-t02-dup-1'
    _cleanup(app, msg_id)
    try:
        with patch(_FLAG, True):
            with app.app_context():
                CostTracker().record_cost(
                    message_id=msg_id, input_tokens=10, output_tokens=5,
                    session_id='s', user_id=1,
                )
            with app.app_context():
                # novo tracker -> _seen_message_ids vazio -> tenta persistir de novo
                CostTracker().record_cost(
                    message_id=msg_id, input_tokens=99, output_tokens=99,
                    session_id='s', user_id=1,
                )
        with app.app_context():
            rows = AgentSessionCost.query.filter_by(message_id=msg_id).all()
            assert len(rows) == 1  # UNIQUE message_id -> sem duplicata, sem erro
    finally:
        _cleanup(app, msg_id)
