"""Testa query agregada top_subagents_by_cost."""
import pytest
from app.agente.models import AgentSession
from app import db


@pytest.fixture(scope='module')
def app():
    """Flask app para testes de modelos."""
    from app import create_app
    _app = create_app()
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    return _app


def test_top_subagents_by_cost_aggregates_correctly(app):
    with app.app_context():
        # cleanup primeiro para isolar
        AgentSession.query.filter(
            AgentSession.session_id.in_(['test-top-1', 'test-top-2'])
        ).delete(synchronize_session=False)
        db.session.commit()

        s1 = AgentSession(
            session_id='test-top-1', user_id=1, title='t', data={
                'subagent_costs': {'version': 1, 'entries': [
                    {'agent_type': 'analista-carteira', 'cost_usd': 0.012},
                    {'agent_type': 'raio-x-pedido', 'cost_usd': 0.005},
                ]}
            }
        )
        s2 = AgentSession(
            session_id='test-top-2', user_id=1, title='t', data={
                'subagent_costs': {'version': 1, 'entries': [
                    {'agent_type': 'analista-carteira', 'cost_usd': 0.008},
                ]}
            }
        )
        db.session.add_all([s1, s2])
        db.session.commit()

        top = AgentSession.top_subagents_by_cost(days=30, limit=5)
        # Filtra so os que sao de nossos test-ids
        top_relevant = [t for t in top if t['agent_type']
                         in ('analista-carteira', 'raio-x-pedido')]

        assert len(top_relevant) >= 2
        ac = next(t for t in top_relevant if t['agent_type'] == 'analista-carteira')
        assert abs(ac['total_cost'] - 0.020) < 1e-6
        assert ac['invocacoes'] == 2

        # cleanup
        db.session.delete(s1)
        db.session.delete(s2)
        db.session.commit()
