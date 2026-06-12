"""Schema das tools MCP de memoria aceita target_user_id (follow-up do IMP-2026-06-09-002).

O fix do D8 2026-06-12 corrigiu os schemas de session_search_tool.py, mas as 13 tools
de memory_mcp_tool.py tinham a MESMA causa raiz: handlers leem args.get('target_user_id')
via _resolve_user_id(args), porem o input_schema dict-simples fazia o factory
(_mcp_enhanced.create_enhanced_mcp_server) marcar TODOS os campos como required e
adicionar additionalProperties:false — qualquer chamada com target_user_id era rejeitada
na validacao ANTES do handler. Isso contradizia app/agente/CLAUDE.md ("TODAS as 12 tools
aceitam target_user_id=N") e quebrava o acesso cross-user admin de memoria.

Tambem corrigido: save_memory ganhou 'category' (lido pelo handler, ausente do schema);
campos com default no handler deixaram de ser required (ex: limit, severity, evidence).

Este teste trava o schema corrigido. Deterministico (sem LLM).
"""
import importlib

import pytest

mt = importlib.import_module("app.agente.tools.memory_mcp_tool")


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


def _all_tools():
    return (
        mt.view_memories,
        mt.save_memory,
        mt.update_memory,
        mt.delete_memory,
        mt.list_memories,
        mt.clear_memories,
        mt.search_cold_memories,
        mt.view_memory_history,
        mt.restore_memory_version,
        mt.resolve_pendencia,
        mt.log_system_pitfall,
        mt.query_knowledge_graph,
        mt.register_improvement,
    )


@pytest.mark.skipif(mt.memory_server is None, reason="claude_agent_sdk indisponivel")
class TestMemoryMcpSchema:
    def test_target_user_id_em_todas_as_13_tools(self):
        for tool in _all_tools():
            props = _final_schema(tool)["properties"]
            assert "target_user_id" in props, f"{tool.name} sem target_user_id no schema"
            assert props["target_user_id"]["type"] == "integer", tool.name

    def test_required_segue_validacao_do_handler(self):
        # required = exatamente o que o handler rejeita com erro quando ausente;
        # campos com default no handler sao opcionais (espelha o criterio do fix D8).
        esperado = {
            "view_memories": [],                       # path tem default '/memories'
            "save_memory": ["path", "content"],        # priority/category tem default
            "update_memory": ["path", "old_str"],      # new_str default '' (deleta trecho)
            "delete_memory": ["path"],
            "list_memories": [],                       # todos os filtros opcionais
            "clear_memories": [],
            "search_cold_memories": ["query"],
            "view_memory_history": ["path"],           # limit default 5
            "restore_memory_version": ["path", "version"],
            "resolve_pendencia": ["description"],
            "log_system_pitfall": ["area", "description"],
            "query_knowledge_graph": ["entity_name"],  # entity_type/max_hops opcionais
            "register_improvement": ["category", "title", "description"],  # severity default info; evidencia nao bloqueia
        }
        for tool in _all_tools():
            assert _final_schema(tool).get("required", []) == esperado[tool.name], tool.name

    def test_save_memory_expoe_category_com_enum(self):
        # handler le args.get('category') desde sempre, mas o campo nao existia no schema
        props = _final_schema(mt.save_memory)["properties"]
        assert "category" in props
        assert props["category"]["enum"] == ["permanent", "structural", "operational", "contextual"]
        assert props["priority"]["enum"] == ["mandatory", "advisory", "contextual"]

    def test_register_improvement_enums(self):
        props = _final_schema(mt.register_improvement)["properties"]
        assert props["category"]["enum"] == [
            "skill_bug", "skill_suggestion", "instruction_request",
            "prompt_feedback", "gotcha_report", "memory_feedback",
        ]
        assert props["severity"]["enum"] == ["critical", "warning", "info"]

    def test_query_kg_filtros_opcionais_nao_required(self):
        # antes o factory forcava entity_type/max_hops (Annotated[Optional]) como required
        schema = _final_schema(mt.query_knowledge_graph)
        assert "entity_type" in schema["properties"]
        assert "max_hops" in schema["properties"]
        assert schema["required"] == ["entity_name"]

    def test_additional_properties_false(self):
        for tool in _all_tools():
            assert _final_schema(tool)["additionalProperties"] is False, tool.name
