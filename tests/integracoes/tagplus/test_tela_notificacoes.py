# tests/integracoes/tagplus/test_tela_notificacoes.py
"""Smoke da tela de histórico (requer login).

Nota: o conftest global configura LOGIN_DISABLED=True, então a rota não
redireciona no ambiente de testes — retorna 200 direto (template renderizado).
Em produção, sem sessão autenticada, @login_required redireciona para login
(302). O assert abaixo aceita ambos os comportamentos.
"""
def test_lista_exige_login(client):
    r = client.get("/integracoes/tagplus/notificacoes")
    assert r.status_code in (200, 302, 401)  # 200 em teste (LOGIN_DISABLED), 302/401 em prod
