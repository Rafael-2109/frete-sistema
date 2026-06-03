"""Testa que SubagentStop enfileira job de validacao quando flag on."""
import json
from unittest.mock import MagicMock, patch


def _make_transcript(tmp_path, cost=0.012):
    p = tmp_path / 'transcript.jsonl'
    with open(p, 'w') as f:
        f.write(json.dumps({
            'type': 'result', 'total_cost_usd': cost,
            'duration_ms': 100, 'num_turns': 1,
            'usage': {'input_tokens': 100, 'output_tokens': 50,
                      'cache_read_input_tokens': 0},
            'stop_reason': 'end_turn',
        }) + '\n')
    return str(p)


def _find_stop_handler(hooks):
    for ev_key, matchers in hooks.items():
        ev_name = ev_key if isinstance(ev_key, str) else getattr(ev_key, 'name', str(ev_key))
        if 'SubagentStop' in ev_name or 'subagent_stop' in ev_name.lower():
            for matcher in matchers:
                if hasattr(matcher, 'hooks') and matcher.hooks:
                    return matcher.hooks[0]
                if callable(matcher):
                    return matcher
    return None


def _make_hooks(user_id=1):
    """Helper wrapping build_hooks signature changes."""
    from app.agente.sdk.hooks import build_hooks
    return build_hooks(
        user_id=user_id,
        user_name='test',
        tool_failure_counts={},
        get_last_thinking=lambda: None,
        get_model_name=lambda: 'claude-opus-4-8',
        set_injected_ids=lambda x: None,
        resume_state={},
    )


def test_subagent_stop_enqueues_validation_when_flag_on(tmp_path, app):
    """Quando USE_SUBAGENT_VALIDATION=true, hook enfileira job."""
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        AgentSession.query.filter_by(session_id='sess-enq-1').delete()
        db.session.commit()
        sess = AgentSession(
            session_id='sess-enq-1', user_id=1, title='t', data={}
        )
        db.session.add(sess)
        db.session.commit()

        # Mock Queue.enqueue
        mock_queue = MagicMock()

        with patch('rq.Queue', return_value=mock_queue) as mock_q_class, \
             patch('redis.from_url', return_value=MagicMock()):
            hooks = _make_hooks()
            handler = _find_stop_handler(hooks)
            assert handler is not None

            import asyncio
            asyncio.run(handler({
                'agent_id': 'aid-enq-1',
                'agent_type': 'analista-carteira',
                'agent_transcript_path': _make_transcript(tmp_path),
                'session_id': 'sess-enq-1',
            }, None, MagicMock()))

        assert mock_queue.enqueue.called, 'Queue.enqueue nao foi chamado'
        # Valida args
        call = mock_queue.enqueue.call_args
        assert call.kwargs['session_id'] == 'sess-enq-1'
        assert call.kwargs['agent_id'] == 'aid-enq-1'
        assert 'threshold' in call.kwargs

        db.session.delete(sess)
        db.session.commit()


def test_subagent_stop_passes_summary_dict_in_payload(tmp_path, app):
    """Hook computa o summary NO WEB (que tem o transcript em /tmp) e o passa
    no payload do job. O worker RQ roda em container Render separado sem acesso
    a esse /tmp — sem o summary no payload o job aborta (status=error)."""
    from app.agente.models import AgentSession
    from app.agente.sdk.subagent_reader import SubagentSummary
    from app import db

    with app.app_context():
        AgentSession.query.filter_by(session_id='sess-enq-sum').delete()
        db.session.commit()
        sess = AgentSession(
            session_id='sess-enq-sum', user_id=1, title='t', data={}
        )
        db.session.add(sess)
        db.session.commit()

        done_summary = SubagentSummary(
            agent_id='aid-sum', agent_type='analista-carteira', status='done',
            started_at=None, ended_at=None, duration_ms=100,
            tools_used=[{'name': 'query_sql', 'args_summary': 'SELECT 1',
                         'result_summary': '24', 'tool_use_id': 't1'}],
            findings_text='resumo do subagente',
        )

        mock_queue = MagicMock()

        with patch('app.agente.sdk.subagent_reader.get_subagent_summary',
                   return_value=done_summary), \
             patch('rq.Queue', return_value=mock_queue), \
             patch('redis.from_url', return_value=MagicMock()):
            hooks = _make_hooks()
            handler = _find_stop_handler(hooks)
            assert handler is not None
            import asyncio
            asyncio.run(handler({
                'agent_id': 'aid-sum',
                'agent_type': 'analista-carteira',
                'agent_transcript_path': _make_transcript(tmp_path),
                'session_id': 'sess-enq-sum',
            }, None, MagicMock()))

        assert mock_queue.enqueue.called, 'Queue.enqueue nao foi chamado'
        call = mock_queue.enqueue.call_args
        assert 'summary_dict' in call.kwargs, 'summary_dict ausente no payload'
        payload = call.kwargs['summary_dict']
        assert payload is not None, 'summary_dict deveria vir preenchido (status=done)'
        assert payload['agent_type'] == 'analista-carteira'
        assert payload['findings_text'] == 'resumo do subagente'
        assert payload['tools_used'][0]['name'] == 'query_sql'
        # PII no payload -> job falho NAO pode reter no Redis por 1 ano (default RQ)
        assert call.kwargs.get('failure_ttl') == 3600
        # cost_usd nao e usado pelo validador -> nao deve ir no payload
        assert 'cost_usd' not in payload

        db.session.delete(sess)
        db.session.commit()


def test_subagent_stop_skips_enqueue_when_flag_off(tmp_path, app):
    """Quando USE_SUBAGENT_VALIDATION=false, nao enfileira."""
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        AgentSession.query.filter_by(session_id='sess-enq-2').delete()
        db.session.commit()
        sess = AgentSession(
            session_id='sess-enq-2', user_id=1, title='t', data={}
        )
        db.session.add(sess)
        db.session.commit()

        mock_queue = MagicMock()

        with patch('app.agente.config.feature_flags.USE_SUBAGENT_VALIDATION', False), \
             patch('rq.Queue', return_value=mock_queue), \
             patch('redis.from_url', return_value=MagicMock()):
            hooks = _make_hooks()
            handler = _find_stop_handler(hooks)
            assert handler is not None
            import asyncio
            asyncio.run(handler({
                'agent_id': 'aid-enq-off',
                'agent_type': 'x',
                'agent_transcript_path': _make_transcript(tmp_path),
                'session_id': 'sess-enq-2',
            }, None, MagicMock()))

        mock_queue.enqueue.assert_not_called()

        db.session.delete(sess)
        db.session.commit()


def test_subagent_stop_survives_redis_connection_error(tmp_path, app):
    """Redis down → hook nao levanta excecao (R1 best-effort)."""
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        AgentSession.query.filter_by(session_id='sess-enq-3').delete()
        db.session.commit()
        sess = AgentSession(
            session_id='sess-enq-3', user_id=1, title='t', data={}
        )
        db.session.add(sess)
        db.session.commit()

        with patch('redis.from_url', side_effect=Exception('redis down')):
            hooks = _make_hooks()
            handler = _find_stop_handler(hooks)
            assert handler is not None
            import asyncio
            # Nao deve levantar
            asyncio.run(handler({
                'agent_id': 'aid-redis-down',
                'agent_type': 'x',
                'agent_transcript_path': _make_transcript(tmp_path),
                'session_id': 'sess-enq-3',
            }, None, MagicMock()))

        db.session.delete(sess)
        db.session.commit()
