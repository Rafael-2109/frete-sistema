"""
Testes do módulo sticky_session — registry Redis para session affinity.

Mitiga Anthropic Issue #61862 (Vj3 over-fires interrupted_turn).
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from app.agente.sdk import sticky_session


@pytest.fixture(autouse=True)
def reset_worker_id():
    """Reset cache do worker_id entre testes."""
    sticky_session._worker_id_cache = None
    yield
    sticky_session._worker_id_cache = None


@pytest.fixture
def enable_sticky(monkeypatch):
    """Liga a feature flag para o teste."""
    monkeypatch.setenv("AGENT_STICKY_SESSION_ENABLED", "true")


@pytest.fixture
def disable_sticky(monkeypatch):
    """Desliga a feature flag para o teste."""
    monkeypatch.setenv("AGENT_STICKY_SESSION_ENABLED", "false")


@pytest.fixture
def mock_redis():
    """Mock do redis_cache.client com comportamento controlado."""
    mock_client = MagicMock()
    mock_cache = MagicMock()
    mock_cache.disponivel = True
    mock_cache.client = mock_client
    with patch("app.utils.redis_cache.redis_cache", mock_cache):
        yield mock_client


@pytest.fixture
def mock_redis_unavailable():
    """Mock do redis_cache com disponivel=False (fail-open)."""
    mock_cache = MagicMock()
    mock_cache.disponivel = False
    mock_cache.client = None
    with patch("app.utils.redis_cache.redis_cache", mock_cache):
        yield


# ─────────────────────────────────────────────────────────────────
# worker_id
# ─────────────────────────────────────────────────────────────────

def test_get_worker_id_format():
    """worker_id = pid@hostname"""
    wid = sticky_session.get_worker_id()
    assert "@" in wid
    pid_str, host = wid.split("@", 1)
    assert pid_str.isdigit()
    assert int(pid_str) == os.getpid()
    assert len(host) > 0


def test_get_worker_id_cached():
    """worker_id é cacheado por processo."""
    wid1 = sticky_session.get_worker_id()
    wid2 = sticky_session.get_worker_id()
    assert wid1 == wid2
    assert wid1 is wid2  # mesmo objeto string (cached)


# ─────────────────────────────────────────────────────────────────
# claim_ownership
# ─────────────────────────────────────────────────────────────────

def test_claim_returns_true_when_disabled(disable_sticky, mock_redis):
    """Flag off → fail-open, retorna True sem tocar Redis."""
    result = sticky_session.claim_ownership("session-123")
    assert result is True
    mock_redis.set.assert_not_called()


def test_claim_returns_true_when_redis_unavailable(enable_sticky, mock_redis_unavailable):
    """Redis off → fail-open."""
    result = sticky_session.claim_ownership("session-123")
    assert result is True


def test_claim_returns_true_when_empty_session_id(enable_sticky, mock_redis):
    """session_id vazio → True (não tenta affinity)."""
    assert sticky_session.claim_ownership("") is True
    assert sticky_session.claim_ownership(None) is True  # type: ignore[arg-type]
    mock_redis.set.assert_not_called()


def test_claim_new_session_succeeds(enable_sticky, mock_redis):
    """SET NX EX retorna True → reivindicamos."""
    mock_redis.set.return_value = True
    result = sticky_session.claim_ownership("session-abc")
    assert result is True
    mock_redis.set.assert_called_once()
    args, kwargs = mock_redis.set.call_args
    assert args[0] == "agent:session:owner:session-abc"
    assert "@" in args[1]  # worker_id
    assert kwargs["nx"] is True
    assert kwargs["ex"] == 1800  # default TTL


def test_claim_already_owned_by_me(enable_sticky, mock_redis):
    """Já era nosso → renova TTL e retorna True."""
    me = sticky_session.get_worker_id()
    mock_redis.set.return_value = None  # NX falhou (já existe)
    mock_redis.get.return_value = me  # mas sou eu
    result = sticky_session.claim_ownership("session-xyz")
    assert result is True
    mock_redis.expire.assert_called_once_with("agent:session:owner:session-xyz", 1800)


def test_claim_owned_by_other_worker(enable_sticky, mock_redis):
    """Outro worker é dono → False (caller deve retornar 409)."""
    other_worker = "99999@other-host"
    mock_redis.set.return_value = None
    mock_redis.get.return_value = other_worker
    result = sticky_session.claim_ownership("session-disputed")
    assert result is False


def test_claim_fail_open_on_redis_exception(enable_sticky, mock_redis):
    """Qualquer exceção do Redis → True (fail-open)."""
    mock_redis.set.side_effect = Exception("Redis down")
    result = sticky_session.claim_ownership("session-err")
    assert result is True


def test_claim_owner_bytes_decoded(enable_sticky, mock_redis):
    """Compatibilidade: alguns clients retornam bytes em vez de str."""
    me = sticky_session.get_worker_id()
    mock_redis.set.return_value = None
    mock_redis.get.return_value = me.encode("utf-8")  # bytes!
    result = sticky_session.claim_ownership("session-bytes")
    assert result is True  # devemos reconhecer como nós


def test_claim_handles_race_expired_between_set_and_get(enable_sticky, mock_redis):
    """Edge: SET NX falhou mas GET retorna None (expirou no meio)."""
    mock_redis.set.return_value = None
    mock_redis.get.return_value = None  # expirou
    result = sticky_session.claim_ownership("session-race")
    assert result is True
    # Deveria ter feito segundo SET (sem NX, força)
    assert mock_redis.set.call_count == 2


# ─────────────────────────────────────────────────────────────────
# get_owner / is_owned_by_me
# ─────────────────────────────────────────────────────────────────

def test_get_owner_returns_none_when_disabled(disable_sticky, mock_redis):
    assert sticky_session.get_owner("session-x") is None
    mock_redis.get.assert_not_called()


def test_get_owner_returns_string(enable_sticky, mock_redis):
    mock_redis.get.return_value = "12345@host-a"
    assert sticky_session.get_owner("session-x") == "12345@host-a"


def test_is_owned_by_me_true_when_no_owner(enable_sticky, mock_redis):
    """Sem dono = True (livre para reivindicar)."""
    mock_redis.get.return_value = None
    assert sticky_session.is_owned_by_me("session-x") is True


def test_is_owned_by_me_false_when_other(enable_sticky, mock_redis):
    mock_redis.get.return_value = "99999@other"
    assert sticky_session.is_owned_by_me("session-x") is False


# ─────────────────────────────────────────────────────────────────
# release_ownership
# ─────────────────────────────────────────────────────────────────

def test_release_uses_lua_cas(enable_sticky, mock_redis):
    """release usa Lua script para compare-and-delete atômico."""
    mock_redis.eval.return_value = 1  # deletou
    sticky_session.release_ownership("session-abc")
    mock_redis.eval.assert_called_once()
    args = mock_redis.eval.call_args[0]
    assert "redis.call('DEL'" in args[0]  # Lua script
    assert args[1] == 1  # numkeys
    assert args[2] == "agent:session:owner:session-abc"  # KEYS[1]
    assert "@" in args[3]  # ARGV[1] = worker_id


def test_release_noop_when_disabled(disable_sticky, mock_redis):
    sticky_session.release_ownership("session-x")
    mock_redis.eval.assert_not_called()


def test_release_swallows_exceptions(enable_sticky, mock_redis):
    """release nunca propaga exception (chamado em finally/atexit)."""
    mock_redis.eval.side_effect = Exception("Redis blew up")
    # Não deve raise
    sticky_session.release_ownership("session-err")


# ─────────────────────────────────────────────────────────────────
# cleanup_owned_sessions (atexit)
# ─────────────────────────────────────────────────────────────────

def test_cleanup_scans_and_deletes_our_keys(enable_sticky, mock_redis):
    """cleanup percorre keys de ownership e deleta as nossas."""
    me = sticky_session.get_worker_id()
    other = "9999@other-host"
    # scan iterator: 2 batches, depois cursor=0
    mock_redis.scan.side_effect = [
        (1, ["agent:session:owner:s1", "agent:session:owner:s2"]),
        (0, ["agent:session:owner:s3"]),
    ]
    mock_redis.get.side_effect = [me, other, me]  # s1=me, s2=other, s3=me

    count = sticky_session.cleanup_owned_sessions()

    assert count == 2  # deletou s1 e s3
    delete_calls = [c for c in mock_redis.delete.call_args_list]
    deleted_keys = [c[0][0] for c in delete_calls]
    assert "agent:session:owner:s1" in deleted_keys
    assert "agent:session:owner:s3" in deleted_keys
    assert "agent:session:owner:s2" not in deleted_keys


def test_cleanup_returns_zero_when_disabled(disable_sticky, mock_redis):
    assert sticky_session.cleanup_owned_sessions() == 0
    mock_redis.scan.assert_not_called()
