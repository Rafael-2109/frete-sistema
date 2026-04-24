from unittest.mock import patch

from app.chat.realtime.publisher import publish, channel_for


def test_channel_for():
    assert channel_for(42) == 'chat_sse:42'


@patch('app.chat.realtime.publisher._redis')
def test_publish_writes_to_channel(mock_redis):
    publish(42, 'message_new', {'a': 1})
    mock_redis.publish.assert_called_once()
    args = mock_redis.publish.call_args.args
    assert args[0] == 'chat_sse:42'
    import json
    payload = json.loads(args[1])
    assert payload['event'] == 'message_new'
    assert payload['data']['a'] == 1


@patch('app.chat.realtime.publisher._redis', None)
def test_publish_noop_if_redis_unavailable():
    # Should not raise
    publish(1, 'x', {})
