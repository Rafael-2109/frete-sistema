"""Testes da extensao do SubagentStop hook para persistir cost granular (#3)."""
import json
from unittest.mock import MagicMock, patch


def _make_transcript(path, cost=0.012, input_t=1200, output_t=400):
    """Helper: cria JSONL com assistant usage + result."""
    with open(path, 'w') as f:
        f.write(json.dumps({
            'type': 'assistant',
            'message': {
                'usage': {
                    'input_tokens': input_t,
                    'output_tokens': output_t,
                    'cache_read_input_tokens': 100,
                }
            }
        }) + '\n')
        f.write(json.dumps({
            'type': 'result',
            'total_cost_usd': cost,
            'duration_ms': 8234,
            'num_turns': 4,
            'usage': {
                'input_tokens': input_t,
                'output_tokens': output_t,
                'cache_read_input_tokens': 100,
            },
            'stop_reason': 'end_turn',
        }) + '\n')
    return str(path)


def _make_hooks(user_id=1):
    """Cria build_hooks com a assinatura real da funcao."""
    from app.agente.sdk.hooks import build_hooks
    return build_hooks(
        user_id=user_id,
        user_name='test_user',
        tool_failure_counts={},
        get_last_thinking=lambda: None,
        get_model_name=lambda: 'test-model',
        set_injected_ids=lambda x: None,
        resume_state=None,
    )


def _find_stop_handler(hooks):
    """Extrai o handler do SubagentStop do dict retornado por build_hooks."""
    for ev_key, matchers in hooks.items():
        ev_name = ev_key if isinstance(ev_key, str) else getattr(ev_key, 'name', str(ev_key))
        if 'SubagentStop' in ev_name or 'subagent_stop' in ev_name.lower():
            for matcher in matchers:
                if hasattr(matcher, 'hooks') and matcher.hooks:
                    return matcher.hooks[0]
                # matcher pode ser HookMatcher ou callable direto
                if callable(matcher):
                    return matcher
    return None


def test_subagent_stop_persists_cost_to_session_data(tmp_path, app):
    """SubagentStop hook persiste entrada em AgentSession.data['subagent_costs']."""
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        # cleanup antes de criar para evitar duplicatas de runs anteriores
        existing = AgentSession.query.filter_by(session_id='sess-cost-1').first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        sess = AgentSession(
            session_id='sess-cost-1', user_id=1, title='test', data={}
        )
        db.session.add(sess)
        db.session.commit()

        transcript = _make_transcript(tmp_path / 'transcript.jsonl')
        hooks = _make_hooks(user_id=1)

        handler = _find_stop_handler(hooks)
        assert handler is not None, 'SubagentStop handler nao encontrado'

        import asyncio
        asyncio.run(handler({
            'agent_id': 'aid-cost-1',
            'agent_type': 'analista-carteira',
            'agent_transcript_path': transcript,
            'session_id': 'sess-cost-1',
        }, None, MagicMock()))

        db.session.refresh(sess)
        assert 'subagent_costs' in sess.data, f"Expected subagent_costs in {sess.data}"
        entries = sess.data['subagent_costs']['entries']
        assert len(entries) == 1
        assert entries[0]['agent_type'] == 'analista-carteira'
        assert entries[0]['cost_usd'] == 0.012
        assert entries[0]['input_tokens'] == 1200
        assert entries[0]['output_tokens'] == 400

        # cleanup
        db.session.delete(sess)
        db.session.commit()


def test_subagent_stop_multiple_subagents_append_entries(tmp_path, app):
    """Dois subagentes na mesma sessao -> entries tem 2."""
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        # cleanup antes de criar para evitar duplicatas de runs anteriores
        existing = AgentSession.query.filter_by(session_id='sess-cost-2').first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        sess = AgentSession(
            session_id='sess-cost-2', user_id=1, title='test', data={}
        )
        db.session.add(sess)
        db.session.commit()

        hooks = _make_hooks(user_id=1)
        handler = _find_stop_handler(hooks)
        assert handler is not None, 'SubagentStop handler nao encontrado'
        import asyncio
        for i, agent_type in enumerate(['analista-carteira', 'raio-x-pedido']):
            transcript = _make_transcript(
                tmp_path / f'{i}.jsonl',
                cost=0.01 + i * 0.005
            )
            asyncio.run(handler({
                'agent_id': f'aid-m-{i}',
                'agent_type': agent_type,
                'agent_transcript_path': transcript,
                'session_id': 'sess-cost-2',
            }, None, MagicMock()))

        db.session.refresh(sess)
        entries = sess.data['subagent_costs']['entries']
        assert len(entries) == 2
        assert {e['agent_type'] for e in entries} == \
            {'analista-carteira', 'raio-x-pedido'}

        db.session.delete(sess)
        db.session.commit()


def test_subagent_stop_flag_off_does_not_persist(tmp_path, app):
    """Quando USE_SUBAGENT_COST_GRANULAR=false, nao persiste em data."""
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        # cleanup antes de criar para evitar duplicatas de runs anteriores
        existing = AgentSession.query.filter_by(session_id='sess-cost-3').first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        sess = AgentSession(
            session_id='sess-cost-3', user_id=1, title='test', data={}
        )
        db.session.add(sess)
        db.session.commit()

        with patch('app.agente.sdk.hooks.USE_SUBAGENT_COST_GRANULAR', False):
            hooks = _make_hooks(user_id=1)
            handler = _find_stop_handler(hooks)
            assert handler is not None, 'SubagentStop handler nao encontrado'
            import asyncio
            asyncio.run(handler({
                'agent_id': 'aid-off',
                'agent_type': 'x',
                'agent_transcript_path': _make_transcript(tmp_path / 'off.jsonl'),
                'session_id': 'sess-cost-3',
            }, None, MagicMock()))

        db.session.refresh(sess)
        assert sess.data.get('subagent_costs') is None

        db.session.delete(sess)
        db.session.commit()
