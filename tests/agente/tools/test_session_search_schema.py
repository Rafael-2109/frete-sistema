"""Schema das tools MCP de sessao aceita target_user_id/channel (IMP-2026-06-09-002).

As tools search_sessions / list_recent_sessions / semantic_search_sessions DESCREVIAM
no texto "em debug mode use target_user_id ... channel" e seus handlers ja liam
args.get('target_user_id') / args.get('channel') — mas o input_schema exposto so tinha
{query}/{limit} com additionalProperties:false. Resultado: qualquer chamada com
target_user_id era rejeitada na validacao do cliente ANTES de chegar ao handler, e o
admin (debug on) ficava tecnicamente incapaz de inspecionar sessao de outro usuario.

Este teste trava o schema corrigido. Determinístico (sem LLM).
"""
import importlib

import pytest

st = importlib.import_module("app.agente.tools.session_search_tool")


def _final_schema(tool_def):
    """Replica a transformacao do factory (_mcp_enhanced.create_enhanced_mcp_server).

    Para input_schema ja' em formato dict-completo (type+properties), o factory apenas
    garante additionalProperties=False e PRESERVA o required declarado.
    """
    isc = tool_def.input_schema
    assert isinstance(isc, dict) and "type" in isc and "properties" in isc, (
        f"{tool_def.name}: input_schema deve ser dict-completo para controlar required"
    )
    schema = dict(isc)
    schema.setdefault("additionalProperties", False)
    return schema


@pytest.mark.skipif(st.sessions_server is None, reason="claude_agent_sdk indisponivel")
class TestSessionSearchSchema:
    def test_target_user_id_em_todas_as_tres_tools(self):
        for tool in (st.search_sessions, st.list_recent_sessions, st.semantic_search_sessions):
            props = _final_schema(tool)["properties"]
            assert "target_user_id" in props, f"{tool.name} sem target_user_id no schema"
            assert props["target_user_id"]["type"] == "integer"

    def test_channel_em_search_e_list_nao_em_semantic(self):
        # search_sessions e list_recent_sessions filtram por canal; semantic NAO usa channel
        assert "channel" in _final_schema(st.search_sessions)["properties"]
        assert "channel" in _final_schema(st.list_recent_sessions)["properties"]
        assert "channel" not in _final_schema(st.semantic_search_sessions)["properties"]

    def test_channel_enum_web_teams(self):
        ch = _final_schema(st.search_sessions)["properties"]["channel"]
        assert ch.get("enum") == ["web", "teams"]

    def test_query_obrigatorio_target_user_id_opcional(self):
        # query continua obrigatorio; target_user_id/channel sao opcionais (nao quebram chamada normal)
        assert _final_schema(st.search_sessions).get("required") == ["query"]
        assert _final_schema(st.semantic_search_sessions).get("required") == ["query"]
        # list_recent: limit tem default no handler -> nada obrigatorio
        assert _final_schema(st.list_recent_sessions).get("required", []) == []

    def test_additional_properties_false(self):
        # additionalProperties:false e' mantido (strict schema), mas agora com os campos certos
        for tool in (st.search_sessions, st.list_recent_sessions, st.semantic_search_sessions):
            assert _final_schema(tool)["additionalProperties"] is False

    def test_get_subagent_transcript_opcionais_nao_required(self):
        # follow-up 2026-06-12: dict-simples forcava include_tools_detail/target_user_id
        # como required (factory all-required); handler so exige session_id + agent_type
        schema = _final_schema(st.get_subagent_transcript)
        assert schema["required"] == ["session_id", "agent_type"]
        assert "include_tools_detail" in schema["properties"]
        assert "target_user_id" in schema["properties"]

    def test_list_session_users_limit_opcional(self):
        # limit tem default 20 no handler -> nada obrigatorio
        schema = _final_schema(st.list_session_users)
        assert schema.get("required", []) == []
        assert schema["properties"]["limit"]["type"] == "integer"

    def test_get_session_transcript_so_session_id_required(self):
        # recuperacao do transcript cru (Bash/scripts): so session_id obrigatorio;
        # filter_tool/include_odoo/target_user_id opcionais (dict-completo, nao all-required)
        schema = _final_schema(st.get_session_transcript)
        assert schema["required"] == ["session_id"]
        for opt in ("filter_tool", "include_odoo", "target_user_id"):
            assert opt in schema["properties"], f"falta {opt} no schema"
