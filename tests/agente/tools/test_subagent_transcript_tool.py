"""Testa mcp__session_search__get_subagent_transcript."""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

def _mk_summary(
    agent_type,
    agent_id=None,
    findings="",
    n_tools=2,
    ended_minutes_ago=5,
    status="done",
):
    """Cria SubagentSummary para uso em testes."""
    from app.agente.sdk.subagent_reader import SubagentSummary

    now = datetime(2026, 4, 17, 12, 0)
    return SubagentSummary(
        agent_id=agent_id or f"a-{agent_type}",
        agent_type=agent_type,
        status=status,
        started_at=now - timedelta(minutes=1),
        ended_at=now - timedelta(minutes=ended_minutes_ago),
        duration_ms=60000,
        tools_used=[
            {
                "name": f"tool_{i}",
                "args_summary": "x",
                "result_summary": f"ok_{i}",
                "tool_use_id": str(i),
            }
            for i in range(n_tools)
        ],
        cost_usd=0.01,
        findings_text=findings,
    )


def _mock_session_obj(agent_type, agent_id="abc-123", ended_at=None):
    """Retorna mock de AgentSession com subagent_costs para agent_type."""
    sess_mock = MagicMock()
    sess_mock.data = {
        "subagent_costs": {
            "version": 1,
            "entries": [
                {
                    "agent_id": agent_id,
                    "agent_type": agent_type,
                    "cost_usd": 0.01,
                    "ended_at": ended_at or "2026-04-17T12:00:00",
                }
            ],
        }
    }
    return sess_mock


async def _call_tool(args):
    """Invoca a tool async via .handler (EnhancedMcpTool)."""
    from app.agente.tools.session_search_tool import get_subagent_transcript

    fn = getattr(get_subagent_transcript, "handler", get_subagent_transcript)
    return await fn(args)


def _run(coro):
    return asyncio.run(coro)


def _make_mock_query(sess_obj):
    """Constroi mock chain AgentSession.query.filter_by().first() -> sess_obj."""
    mock_query = MagicMock()
    mock_query.filter_by.return_value.first.return_value = sess_obj
    return mock_query


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


def test_found_returns_subagent_summary():
    """Acha subagent e retorna summary com findings e tools."""
    summary = _mk_summary(
        "analista-carteira", agent_id="abc-123",
        findings="Encontrei 24 pedidos", n_tools=3,
    )
    sess_obj = _mock_session_obj("analista-carteira", agent_id="abc-123")

    with (
        patch("app.agente.tools.session_search_tool._resolve_user_id", return_value=99),
        patch("app.agente.tools.session_search_tool.get_debug_mode", return_value=False,
              create=True),
        patch("app.agente.config.permissions.get_debug_mode", return_value=False),
        patch("app.agente.tools.session_search_tool._execute_with_context",
              side_effect=lambda fn: fn()),
        # Patch AgentSession inside the tool's closure context
        patch("app.agente.models.AgentSession") as mock_cls,
        patch("app.agente.sdk.subagent_reader.get_subagent_summary", return_value=summary),
    ):
        mock_cls.query = _make_mock_query(sess_obj)

        result = _run(_call_tool({
            "session_id": "sess-abc",
            "agent_type": "analista-carteira",
        }))

    assert result["structuredContent"]["found"] is True
    assert result["structuredContent"]["agent_type"] == "analista-carteira"
    assert result["structuredContent"]["num_tools"] == 3
    assert "Encontrei 24 pedidos" in result["structuredContent"]["findings_text"]
    assert len(result["structuredContent"]["tools_used"]) == 3


def test_not_found_returns_error_with_available_types():
    """Agent_type inexistente retorna found=False + lista de disponiveis."""
    # DB has analista-carteira but we search for raio-x-pedido
    sess_obj = _mock_session_obj("analista-carteira", agent_id="abc-123")

    with (
        patch("app.agente.tools.session_search_tool._resolve_user_id", return_value=99),
        patch("app.agente.config.permissions.get_debug_mode", return_value=False),
        patch("app.agente.tools.session_search_tool._execute_with_context",
              side_effect=lambda fn: fn()),
        patch("app.agente.models.AgentSession") as mock_cls,
    ):
        mock_cls.query = _make_mock_query(sess_obj)

        result = _run(_call_tool({
            "session_id": "sess",
            "agent_type": "raio-x-pedido",
        }))

    assert result["structuredContent"]["found"] is False
    assert "analista-carteira" in result["structuredContent"]["error"]


def test_missing_required_args_returns_error():
    """session_id ou agent_type vazio retorna erro sem chamar DB."""
    result = _run(_call_tool({"session_id": "", "agent_type": "x"}))
    assert result["structuredContent"]["found"] is False
    assert "obrigatorios" in result["structuredContent"]["error"].lower()

    result2 = _run(_call_tool({"session_id": "sess-abc", "agent_type": ""}))
    assert result2["structuredContent"]["found"] is False
    assert "obrigatorios" in result2["structuredContent"]["error"].lower()


def test_multiple_matching_picks_most_recent():
    """Dois subagents mesmo type: pega o mais recente (ended_at desc)."""
    sess_obj = MagicMock()
    sess_obj.data = {
        "subagent_costs": {
            "version": 1,
            "entries": [
                {
                    "agent_id": "old-agent",
                    "agent_type": "analista-carteira",
                    "ended_at": "2026-04-17T11:50:00",
                },
                {
                    "agent_id": "new-agent",
                    "agent_type": "analista-carteira",
                    "ended_at": "2026-04-17T11:58:00",
                },
            ],
        }
    }

    new_summary = _mk_summary(
        "analista-carteira", agent_id="new-agent", findings="new findings"
    )

    def fake_get_summary(session_id, agent_id, agent_type="", include_pii=False, **kw):
        assert agent_id == "new-agent", f"Expected new-agent, got {agent_id}"
        return new_summary

    with (
        patch("app.agente.tools.session_search_tool._resolve_user_id", return_value=99),
        patch("app.agente.config.permissions.get_debug_mode", return_value=False),
        patch("app.agente.tools.session_search_tool._execute_with_context",
              side_effect=lambda fn: fn()),
        patch("app.agente.models.AgentSession") as mock_cls,
        patch("app.agente.sdk.subagent_reader.get_subagent_summary",
              side_effect=fake_get_summary),
    ):
        mock_cls.query = _make_mock_query(sess_obj)

        result = _run(_call_tool({
            "session_id": "sess",
            "agent_type": "analista-carteira",
        }))

    assert result["structuredContent"]["found"] is True
    assert "new findings" in result["structuredContent"]["findings_text"]


def test_include_tools_detail_false_omits_tools():
    """include_tools_detail=False retorna tools_used vazio."""
    summary = _mk_summary("analista-carteira", agent_id="abc-123", n_tools=5)
    sess_obj = _mock_session_obj("analista-carteira", agent_id="abc-123")

    with (
        patch("app.agente.tools.session_search_tool._resolve_user_id", return_value=99),
        patch("app.agente.config.permissions.get_debug_mode", return_value=False),
        patch("app.agente.tools.session_search_tool._execute_with_context",
              side_effect=lambda fn: fn()),
        patch("app.agente.models.AgentSession") as mock_cls,
        patch("app.agente.sdk.subagent_reader.get_subagent_summary", return_value=summary),
    ):
        mock_cls.query = _make_mock_query(sess_obj)

        result = _run(_call_tool({
            "session_id": "sess-abc",
            "agent_type": "analista-carteira",
            "include_tools_detail": False,
        }))

    assert result["structuredContent"]["found"] is True
    assert result["structuredContent"]["tools_used"] == []


def test_admin_receives_cost_usd():
    """Debug mode ativo (admin): resposta inclui cost_usd."""
    summary = _mk_summary("analista-carteira", agent_id="abc-123")
    summary.cost_usd = 0.025
    sess_obj = _mock_session_obj("analista-carteira", agent_id="abc-123")

    with (
        patch("app.agente.tools.session_search_tool._resolve_user_id", return_value=1),
        patch("app.agente.config.permissions.get_debug_mode", return_value=True),
        patch("app.agente.tools.session_search_tool._execute_with_context",
              side_effect=lambda fn: fn()),
        patch("app.agente.models.AgentSession") as mock_cls,
        patch("app.agente.sdk.subagent_reader.get_subagent_summary", return_value=summary),
    ):
        mock_cls.query = _make_mock_query(sess_obj)

        result = _run(_call_tool({
            "session_id": "sess-abc",
            "agent_type": "analista-carteira",
        }))

    assert result["structuredContent"]["found"] is True
    assert "cost_usd" in result["structuredContent"]
    assert result["structuredContent"]["cost_usd"] == round(0.025, 6)


def test_non_admin_does_not_receive_cost_usd():
    """Debug mode inativo (user normal): resposta NAO inclui cost_usd."""
    summary = _mk_summary("analista-carteira", agent_id="abc-123")
    sess_obj = _mock_session_obj("analista-carteira", agent_id="abc-123")

    with (
        patch("app.agente.tools.session_search_tool._resolve_user_id", return_value=99),
        patch("app.agente.config.permissions.get_debug_mode", return_value=False),
        patch("app.agente.tools.session_search_tool._execute_with_context",
              side_effect=lambda fn: fn()),
        patch("app.agente.models.AgentSession") as mock_cls,
        patch("app.agente.sdk.subagent_reader.get_subagent_summary", return_value=summary),
    ):
        mock_cls.query = _make_mock_query(sess_obj)

        result = _run(_call_tool({
            "session_id": "sess-abc",
            "agent_type": "analista-carteira",
        }))

    assert result["structuredContent"]["found"] is True
    assert "cost_usd" not in result["structuredContent"]
