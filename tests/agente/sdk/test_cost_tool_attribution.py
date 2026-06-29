"""Atribuicao de tool_name por turno em agent_session_costs (B7 — spec
handoff-sessao 2026-06-28).

Antes: `_persist_session_cost` gravava `tool_name=None` -> coluna 100% NULL ->
`aggregate_summary.by_tool` sempre vazio -> impossivel saber qual superficie
consome custo. Fix: atribuir UM tool representativo do turno (heuristica
documentada; o custo do ResultMessage e do TURNO, nao por-tool), priorizando o
maior driver de custo do SOT: delegacao a subagente > skill > MCP tool > builtin.
"""
from unittest.mock import patch

from app import db
from app.agente.models import AgentSessionCost
from app.agente.routes.chat import _primary_tool_for_cost, _persist_session_cost

_FLAG = 'app.agente.config.feature_flags.USE_COST_TRACKER_PERSIST'


def test_prioriza_delegacao_subagente():
    tools = ['Skill:consultando-sql', 'mcp__sql__consultar_sql',
             'Agent:gestor-estoque-odoo', 'Agent']
    assert _primary_tool_for_cost(tools) == 'Agent:gestor-estoque-odoo'


def test_skill_acima_de_mcp():
    tools = ['mcp__sql__consultar_sql', 'Skill:cotando-frete', 'Skill']
    assert _primary_tool_for_cost(tools) == 'Skill:cotando-frete'


def test_mcp_acima_de_builtin():
    tools = ['Read', 'Bash', 'mcp__sql__consultar_sql']
    assert _primary_tool_for_cost(tools) == 'mcp__sql__consultar_sql'


def test_builtin_como_fallback():
    assert _primary_tool_for_cost(['Read', 'Bash']) == 'Read'


def test_ignora_marcadores_crus_skill_agent():
    # 'Skill'/'Agent' crus (backward-compat) nao sao atribuicao util sozinhos.
    assert _primary_tool_for_cost(['Skill', 'Agent']) is None


def test_vazio_ou_none_retorna_none():
    assert _primary_tool_for_cost([]) is None
    assert _primary_tool_for_cost(None) is None


def _cleanup(app, mid):
    with app.app_context():
        AgentSessionCost.query.filter_by(message_id=mid).delete()
        db.session.commit()


def test_persist_popula_tool_name_do_turno(app):
    mid = 'b7-tool-attr-1'
    _cleanup(app, mid)
    try:
        with patch(_FLAG, True):
            with app.app_context():
                _persist_session_cost(
                    message_id=mid, session_id='s', user_id=1,
                    input_tokens=10, output_tokens=5,
                    cache_read_tokens=0, cache_creation_tokens=0,
                    cost_usd=0.02, model='claude-opus-4-8',
                    tools_used=['Agent:gestor-recebimento', 'Agent'],
                )
                db.session.commit()
        with app.app_context():
            row = AgentSessionCost.query.filter_by(message_id=mid).first()
            assert row is not None
            assert row.tool_name == 'Agent:gestor-recebimento'
    finally:
        _cleanup(app, mid)


def test_persist_sem_tools_used_mantem_none(app):
    mid = 'b7-tool-attr-2'
    _cleanup(app, mid)
    try:
        with patch(_FLAG, True):
            with app.app_context():
                _persist_session_cost(
                    message_id=mid, session_id='s', user_id=1,
                    input_tokens=10, output_tokens=5,
                    cache_read_tokens=0, cache_creation_tokens=0,
                    cost_usd=0.02, model='claude-opus-4-8',
                )
                db.session.commit()
        with app.app_context():
            row = AgentSessionCost.query.filter_by(message_id=mid).first()
            assert row is not None
            assert row.tool_name is None
    finally:
        _cleanup(app, mid)
