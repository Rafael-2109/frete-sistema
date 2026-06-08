# tests/agente/test_approval_inbox.py
"""
TDD — Inbox de Aprovacao unificada (Task 11: service, Task 12: rotas).

GOTCHA: db.session.commit() no service escapa do savepoint da fixture db.
Usar UUIDs/paths unicos por run + cleanup explicito ao final de cada teste.
"""
import uuid as _uuid


# ---------------------------------------------------------------------------
# Task 11: Inbox — service
# ---------------------------------------------------------------------------

def test_list_pending_includes_shadow_and_proposed(db):
    from app.agente.models import AgentMemory, AgentImprovementDialogue
    from app.agente.services import approval_inbox_service as inbox

    # Usa paths unicos para evitar colisao entre re-runs
    _unique = _uuid.uuid4().hex[:8]
    _path = f"/memories/empresa/lembretes_skill/x-{_unique}.xml"

    m = AgentMemory(user_id=0, path=_path,
                    content="<x/>", is_directory=False, escopo="empresa",
                    directive_status="shadow", priority="mandatory")
    db.session.add(m)
    d = AgentImprovementDialogue.create_suggestion(
        category="skill_bug", severity="info",
        title=f"t-{_unique}", description=f"d-{_unique}")
    db.session.commit()

    try:
        items = inbox.list_pending_approvals()
        kinds = {it["kind"] for it in items}
        assert "memory" in kinds and "dialogue" in kinds
    finally:
        # Cleanup — commita após assertions para nao poluir banco
        AgentMemory.query.filter_by(path=_path).delete()
        AgentImprovementDialogue.query.filter_by(id=d.id).delete()
        db.session.commit()


def test_approve_memory_activates(db):
    from app.agente.models import AgentMemory
    from app.agente.services import approval_inbox_service as inbox

    _unique = _uuid.uuid4().hex[:8]
    _path = f"/memories/empresa/lembretes_skill/y-{_unique}.xml"

    m = AgentMemory(user_id=0, path=_path,
                    content="<x/>", is_directory=False, escopo="empresa",
                    directive_status="shadow", priority="mandatory")
    db.session.add(m)
    db.session.commit()

    try:
        ok = inbox.approve_item("memory", m.id, reviewer_user_id=1)
        assert ok is True
        refreshed = AgentMemory.query.get(m.id)
        assert refreshed.directive_status == "ativa"
    finally:
        AgentMemory.query.filter_by(id=m.id).delete()
        db.session.commit()


def test_reject_dialogue(db):
    from app.agente.models import AgentImprovementDialogue
    from app.agente.services import approval_inbox_service as inbox

    _unique = _uuid.uuid4().hex[:8]
    d = AgentImprovementDialogue.create_suggestion(
        category="skill_bug", severity="info",
        title=f"t-{_unique}", description=f"d-{_unique}")
    db.session.commit()

    try:
        ok = inbox.reject_item("dialogue", d.id, reviewer_user_id=1)
        assert ok is True
        refreshed = AgentImprovementDialogue.query.get(d.id)
        assert refreshed.status == "rejected"
    finally:
        AgentImprovementDialogue.query.filter_by(id=d.id).delete()
        db.session.commit()


# ---------------------------------------------------------------------------
# Task 12: Inbox — rotas
# ---------------------------------------------------------------------------

def test_route_list_approvals(client, db, monkeypatch):
    """GET /agente/api/memories/approvals deve retornar items (admin mock)."""
    import app.agente.routes.memories as mem_routes
    # _require_admin_json retorna None quando admin
    monkeypatch.setattr(mem_routes, "_require_admin_json", lambda: None)
    monkeypatch.setattr(
        "app.agente.services.approval_inbox_service.list_pending_approvals",
        lambda: [{"kind": "memory", "id": 1, "title": "x"}]
    )
    resp = client.get("/agente/api/memories/approvals")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["items"][0]["kind"] == "memory"


def test_route_approve_memory(client, monkeypatch):
    """PUT /agente/api/memories/approvals/memory/5/approve deve chamar approve_item."""
    import app.agente.routes.memories as mem_routes
    monkeypatch.setattr(mem_routes, "_require_admin_json", lambda: None)
    called = {}
    monkeypatch.setattr(
        "app.agente.services.approval_inbox_service.approve_item",
        lambda kind, iid, reviewer_user_id: called.setdefault("a", (kind, iid)) or True
    )
    resp = client.put("/agente/api/memories/approvals/memory/5/approve")
    assert resp.status_code == 200
    assert called["a"] == ("memory", 5)


def test_route_reject_item(client, monkeypatch):
    """PUT /agente/api/memories/approvals/dialogue/7/reject deve chamar reject_item."""
    import app.agente.routes.memories as mem_routes
    monkeypatch.setattr(mem_routes, "_require_admin_json", lambda: None)
    called = {}
    monkeypatch.setattr(
        "app.agente.services.approval_inbox_service.reject_item",
        lambda kind, iid, reviewer_user_id: called.setdefault("r", (kind, iid)) or True
    )
    resp = client.put("/agente/api/memories/approvals/dialogue/7/reject")
    assert resp.status_code == 200
    assert called["r"] == ("dialogue", 7)


def test_route_approve_non_admin_denied(client, monkeypatch):
    """Sem _require_admin_json patchado, usuario nao-admin deve receber 403."""
    from flask import jsonify
    # Simula o comportamento real do helper quando nao-admin:
    # retorna (Response, 403). O route faz "if guard: return guard".
    import app.agente.routes.memories as mem_routes

    def _fake_require_admin():
        return (jsonify({'success': False, 'error': 'Acesso restrito a administradores'}), 403)

    monkeypatch.setattr(mem_routes, "_require_admin_json", _fake_require_admin)
    resp = client.get("/agente/api/memories/approvals")
    assert resp.status_code == 403
