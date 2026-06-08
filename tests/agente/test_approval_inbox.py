# tests/agente/test_approval_inbox.py
"""
TDD — Inbox de Aprovacao unificada (Task 11: service, Task 12: rotas).

GOTCHA: db.session.commit() no service escapa do savepoint da fixture db.
Usar UUIDs/paths unicos por run + cleanup explicito ao final de cada teste.

Padrao para rotas: patch('flask_login.utils._get_user') com MagicMock admin/normal
(ver tests/agente/routes/test_memorias_routes.py).
"""
import uuid as _uuid
from unittest.mock import MagicMock, patch


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
        # Cleanup — commita apos assertions para nao poluir banco
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
# Padrao: patch('flask_login.utils._get_user') com MagicMock admin/normal
# (ver tests/agente/routes/test_memorias_routes.py).
# ---------------------------------------------------------------------------

def _admin_user():
    u = MagicMock()
    u.is_authenticated = True
    u.perfil = 'administrador'
    u.id = 1
    u.nome = 'Admin Teste'
    u.email = 'admin@test.com'
    return u


def _normal_user():
    u = MagicMock()
    u.is_authenticated = True
    u.perfil = 'vendedor'
    u.id = 2
    u.nome = 'Vendedor'
    u.email = 'v@test.com'
    return u


def test_route_list_approvals(client, monkeypatch):
    """GET /agente/api/memories/approvals deve retornar items (admin)."""
    monkeypatch.setattr(
        "app.agente.services.approval_inbox_service.list_pending_approvals",
        lambda: [{"kind": "memory", "id": 1, "title": "x"}]
    )
    with patch('flask_login.utils._get_user', return_value=_admin_user()):
        resp = client.get("/agente/api/memories/approvals")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["items"][0]["kind"] == "memory"


def test_route_approve_memory(client, monkeypatch):
    """PUT /agente/api/memories/approvals/memory/5/approve deve chamar approve_item."""
    called = {}
    monkeypatch.setattr(
        "app.agente.services.approval_inbox_service.approve_item",
        lambda kind, iid, reviewer_user_id: called.setdefault("a", (kind, iid)) or True
    )
    with patch('flask_login.utils._get_user', return_value=_admin_user()):
        resp = client.put("/agente/api/memories/approvals/memory/5/approve")
    assert resp.status_code == 200
    assert called["a"] == ("memory", 5)


def test_route_reject_item(client, monkeypatch):
    """PUT /agente/api/memories/approvals/dialogue/7/reject deve chamar reject_item."""
    called = {}
    monkeypatch.setattr(
        "app.agente.services.approval_inbox_service.reject_item",
        lambda kind, iid, reviewer_user_id: called.setdefault("r", (kind, iid)) or True
    )
    with patch('flask_login.utils._get_user', return_value=_admin_user()):
        resp = client.put("/agente/api/memories/approvals/dialogue/7/reject")
    assert resp.status_code == 200
    assert called["r"] == ("dialogue", 7)


def test_route_approvals_non_admin_denied(client):
    """Usuario nao-admin deve receber 403 na inbox."""
    with patch('flask_login.utils._get_user', return_value=_normal_user()):
        resp = client.get("/agente/api/memories/approvals")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Task 14: Ajuste do improvement_suggester (D8) — separacao de competencias
# ---------------------------------------------------------------------------

def test_d8_prompt_separates_competencies():
    """O system prompt do batch D8 deve instruir separacao de competencias:
    descrever o problema, nao prescrever a solucao."""
    import app.agente.services.improvement_suggester as m
    blob = " ".join(str(v) for v in vars(m).values() if isinstance(v, str)).lower()
    assert ("pedido de ajuda" in blob) or ("nao prescrev" in blob) or ("descreva o problema" in blob)
