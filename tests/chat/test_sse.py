from unittest.mock import patch, MagicMock

from app.chat.realtime.sse import stream_chat_events


def test_stream_emits_hello_first():
    # First chunk should be the ': connected' heartbeat/hello
    with patch('app.chat.realtime.sse._get_pubsub') as mock_ps:
        mock_pubsub = MagicMock()
        mock_pubsub.get_message.return_value = None
        mock_ps.return_value = mock_pubsub

        gen = stream_chat_events(user_id=42, last_event_id=None, max_iterations=1)
        first = next(gen)
        assert first.startswith(': connected') or 'event: hello' in first


def test_stream_yields_published_message():
    with patch('app.chat.realtime.sse._get_pubsub') as mock_ps:
        mock_pubsub = MagicMock()
        mock_pubsub.get_message.side_effect = [
            {'type': 'message', 'data': '{"event":"message_new","data":{"x":1}}'},
            None,
        ]
        mock_ps.return_value = mock_pubsub

        gen = stream_chat_events(user_id=42, last_event_id=None, max_iterations=2)
        out = [next(gen) for _ in range(2)]
        text = '\n'.join(out)
        assert 'event: message_new' in text
        assert '"x": 1' in text or '"x":1' in text
