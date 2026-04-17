"""Testa job RQ de validacao anti-alucinacao (#4)."""
import json
import pytest
from unittest.mock import patch


@pytest.fixture
def sample_summary():
    from app.agente.sdk.subagent_reader import SubagentSummary
    return SubagentSummary(
        agent_id='a1', agent_type='analista-carteira', status='done',
        started_at=None, ended_at=None, duration_ms=100,
        tools_used=[
            {'name': 'query_sql', 'args_summary': 'SELECT COUNT(*) FROM pedidos',
             'result_summary': '24', 'tool_use_id': 't1'}
        ],
        findings_text='Ha 30 pedidos em aberto.',  # inconsistencia: 24 vs 30
        num_turns=2,
    )


def test_validator_parses_haiku_json_and_persists(app, sample_summary):
    from app.agente.workers.subagent_validator import validate_subagent_output
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        # Cleanup para idempotencia
        AgentSession.query.filter_by(session_id='sess-val-1').delete()
        db.session.commit()

        sess = AgentSession(
            session_id='sess-val-1', user_id=1, title='t', data={}
        )
        db.session.add(sess)
        db.session.commit()

        haiku_response = json.dumps({
            'score': 40,
            'reason': 'Resposta menciona 30, SQL retornou 24',
            'flagged_claims': ['30 pedidos em aberto'],
        })

        with patch('app.agente.workers.subagent_validator.get_subagent_summary',
                   return_value=sample_summary), \
             patch('app.agente.workers.subagent_validator._call_haiku',
                   return_value=haiku_response), \
             patch('app.agente.workers.subagent_validator._push_validation_event') as mock_push, \
             patch('app.agente.workers.subagent_validator.create_app',
                   return_value=app):
            validate_subagent_output(
                session_id='sess-val-1', agent_id='a1', threshold=70
            )

        db.session.refresh(sess)
        assert 'subagent_validations' in sess.data
        entries = sess.data['subagent_validations']['entries']
        assert len(entries) == 1
        assert entries[0]['score'] == 40
        assert entries[0]['agent_id'] == 'a1'
        mock_push.assert_called_once()  # score < threshold -> push SSE

        db.session.delete(sess)
        db.session.commit()


def test_validator_no_push_when_score_above_threshold(app, sample_summary):
    from app.agente.workers.subagent_validator import validate_subagent_output
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        AgentSession.query.filter_by(session_id='sess-val-2').delete()
        db.session.commit()

        sess = AgentSession(
            session_id='sess-val-2', user_id=1, title='t', data={}
        )
        db.session.add(sess)
        db.session.commit()

        good_response = json.dumps({
            'score': 90, 'reason': 'Consistente', 'flagged_claims': [],
        })

        with patch('app.agente.workers.subagent_validator.get_subagent_summary',
                   return_value=sample_summary), \
             patch('app.agente.workers.subagent_validator._call_haiku',
                   return_value=good_response), \
             patch('app.agente.workers.subagent_validator._push_validation_event') as mock_push, \
             patch('app.agente.workers.subagent_validator.create_app',
                   return_value=app):
            validate_subagent_output(
                session_id='sess-val-2', agent_id='a1', threshold=70
            )

        mock_push.assert_not_called()  # score >= threshold

        db.session.delete(sess)
        db.session.commit()


def test_validator_summary_error_aborts_gracefully(app):
    """Se get_subagent_summary retorna error, job aborta sem crash."""
    from app.agente.workers.subagent_validator import validate_subagent_output
    from app.agente.sdk.subagent_reader import SubagentSummary

    bad_summary = SubagentSummary(
        agent_id='missing', agent_type='', status='error',
        started_at=None, ended_at=None, duration_ms=None,
    )

    with patch('app.agente.workers.subagent_validator.get_subagent_summary',
               return_value=bad_summary), \
         patch('app.agente.workers.subagent_validator._call_haiku') as mock_haiku:
        # Nao deve chamar Haiku nem levantar excecao
        validate_subagent_output(session_id='s', agent_id='missing', threshold=70)

    mock_haiku.assert_not_called()


def test_validator_invalid_json_haiku_response(app, sample_summary):
    """Haiku retorna JSON invalido → job aborta sem persistir."""
    from app.agente.workers.subagent_validator import validate_subagent_output
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        AgentSession.query.filter_by(session_id='sess-val-3').delete()
        db.session.commit()

        sess = AgentSession(
            session_id='sess-val-3', user_id=1, title='t', data={}
        )
        db.session.add(sess)
        db.session.commit()

        with patch('app.agente.workers.subagent_validator.get_subagent_summary',
                   return_value=sample_summary), \
             patch('app.agente.workers.subagent_validator._call_haiku',
                   return_value='not a json at all'), \
             patch('app.agente.workers.subagent_validator.create_app',
                   return_value=app):
            validate_subagent_output(
                session_id='sess-val-3', agent_id='a1', threshold=70
            )

        db.session.refresh(sess)
        # Sem entries persistidas
        assert sess.data.get('subagent_validations') is None

        db.session.delete(sess)
        db.session.commit()
