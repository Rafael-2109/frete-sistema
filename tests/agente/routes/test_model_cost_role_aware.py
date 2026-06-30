"""8b passo 6: model routing + baseline de custo POR PAPEL.

(a) O bloco model_router consulta get_pooled_client(session_id, role=agent_role)
    (papel ativo); should_switch_model ja' usa o client do papel (passo 4).
(b) O baseline de custo (_sdk_cost_by_role) e por papel: cada papel tem sua
    PROPRIA sessao SDK -> seu PROPRIO total_cost_usd acumulado. Sem isto, alternar
    principal<->especialista flipa o sdk_session_id a cada turno e
    turn_cost_from_cumulative zeraria o baseline (falso reset) -> inflacao.
"""
import inspect
import uuid
from unittest.mock import patch

from app import db
from app.agente.models import AgentSession
from app.agente.routes import chat as chat_mod


def _save(app, sid, sdk_uuid, role, sdk_cost):
    with patch.object(chat_mod, 'run_post_session_processing', lambda **k: None):
        return chat_mod._save_messages_to_db(
            app=app, our_session_id=sid, sdk_session_id=sdk_uuid,
            user_id=1, user_message='u', assistant_message='a',
            input_tokens=1, output_tokens=1, tools_used=[],
            model='claude-opus-4-8', session_expired=False,
            sdk_cost_usd=sdk_cost, agent_role=role,
        )


def test_baseline_custo_por_papel_nao_infla_na_alternancia(app):
    sid = 't-cost-role-1'
    u_principal = str(uuid.uuid4())
    u_espec = str(uuid.uuid4())
    # Turno 1 principal: acumulado SDK 1.0 -> delta 1.0
    _save(app, sid, u_principal, 'principal', 1.0)
    # Turno 2 especialista: sessao SDK PROPRIA, acumulado 0.5 -> delta 0.5
    _save(app, sid, u_espec, 'gestor-recebimento', 0.5)
    # Turno 3 principal: acumulado do principal cresceu 1.0 -> 2.0 -> delta 1.0
    # (NAO 2.0 — sem o fix, o sid do especialista no slot unico forcaria reset).
    _save(app, sid, u_principal, 'principal', 2.0)
    with app.app_context():
        r = AgentSession.query.filter_by(session_id=sid).first()
        total = float(r.total_cost_usd or 0)
        # 1.0 + 0.5 + 1.0 = 2.5  (logica single-slot daria 1.0+0.5+2.0 = 3.5)
        assert abs(total - 2.5) < 1e-6, f"total inflado: {total}"
        # baseline por papel persistido
        by_role = (r.data or {}).get('_sdk_cost_by_role') or {}
        assert by_role.get('principal', {}).get('cumulative') == 2.0
        assert by_role.get('gestor-recebimento', {}).get('cumulative') == 0.5
        AgentSession.query.filter_by(session_id=sid).delete()
        db.session.commit()


def test_retrocompat_principal_herda_slot_legado(app):
    """Sessao em andamento (slots legados _sdk_cost_*) nao perde o baseline do
    principal no 1o turno pos-8b."""
    sid = 't-cost-role-2'
    u = str(uuid.uuid4())
    with app.app_context():
        s = AgentSession(session_id=sid, user_id=1, data={
            '_sdk_cost_cumulative': 3.0, '_sdk_cost_session_id': u,
        })
        db.session.add(s)
        db.session.commit()
    # Mesmo sid SDK, acumulado cresceu 3.0 -> 4.0 -> delta 1.0 (herdou baseline 3.0)
    _save(app, sid, u, 'principal', 4.0)
    with app.app_context():
        r = AgentSession.query.filter_by(session_id=sid).first()
        assert abs(float(r.total_cost_usd or 0) - 1.0) < 1e-6
        AgentSession.query.filter_by(session_id=sid).delete()
        db.session.commit()


def test_model_block_consulta_client_do_papel():
    src = inspect.getsource(chat_mod.api_chat)
    assert 'get_pooled_client(session_id, role=agent_role)' in src
    # agent_role resolvido ANTES da consulta role-aware ao pool (model_router).
    assert (src.index('agent_role = _resolve_agent_role')
            < src.index('get_pooled_client(session_id, role=agent_role)'))
