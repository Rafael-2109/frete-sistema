"""Smoke da rota admin_teams (F2 — dashboard observabilidade Teams).

Cobre registro de endpoints + auth admin-only. A logica de dados e coberta por
tests/agente/services/test_teams_observability_service.py.
"""

API_ENDPOINTS = ("overview", "timeseries", "users", "stuck", "recent", "cost", "tools", "skills")


def test_admin_teams_endpoints_registrados(app):
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/agente/admin/teams" in rules
    for ep in API_ENDPOINTS:
        assert f"/agente/api/admin/teams/{ep}" in rules, f"falta endpoint {ep}"


def test_admin_teams_api_exige_admin(client):
    # LOGIN_DISABLED=True -> current_user anonimo -> _require_admin retorna 403
    resp = client.get("/agente/api/admin/teams/overview")
    assert resp.status_code == 403


def test_admin_teams_page_sem_admin_403(client):
    resp = client.get("/agente/admin/teams")
    assert resp.status_code == 403


def test_admin_teams_overview_caminho_feliz(client, app):
    """Admin logado -> 200 com estrutura esperada (rota -> service -> jsonify)."""
    import pytest
    from app.auth.models import Usuario
    with app.app_context():
        admin = Usuario.query.filter_by(perfil="administrador").first()
        if not admin:
            pytest.skip("sem usuario admin no banco local")
        admin_id = admin.id
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_id)
        sess["_fresh"] = True
    resp = client.get("/agente/api/admin/teams/overview?period=7d")
    assert resp.status_code == 200
    j = resp.get_json()
    assert j["success"] is True
    assert "total" in j["data"] and "by_status" in j["data"]
    # endpoint de custo/qualidade tambem responde
    resp2 = client.get("/agente/api/admin/teams/cost?period=7d")
    assert resp2.status_code == 200
    assert "num_turnos" in resp2.get_json()["data"]
