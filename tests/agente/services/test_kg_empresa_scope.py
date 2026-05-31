"""Onda 1 / D0.5 — escopo empresa (user_id=0) ja' implementado; blindar com teste."""
import inspect
from app.agente.services import knowledge_graph_service as kg


def test_query_inclui_user_id_zero_empresa():
    src = inspect.getsource(kg.query_graph_memories)
    assert "user_id, 0" in src or "[user_id, 0]" in src, \
        "query_graph_memories deve unir user_id com escopo empresa (0)"
