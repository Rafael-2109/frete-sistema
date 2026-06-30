"""
Testes para pool multi-papel: PooledClient.role + chave composta _pool_key.

Task 3 (F1 T3) — PooledClient.role e _pool_key().
"""
from app.agente.sdk import client_pool as cp


def test_pool_key_compoe_session_e_role():
    assert cp._pool_key("sess-1", "principal") == "sess-1::principal"
    assert cp._pool_key("sess-1", "gestor-recebimento") == "sess-1::gestor-recebimento"

def test_pool_key_default_principal():
    assert cp._pool_key("sess-1") == "sess-1::principal"

def test_pooled_client_tem_role_default_principal():
    pc = cp.PooledClient(client=object(), session_id="s")
    assert pc.role == "principal"

def test_get_pooled_client_isola_por_papel():
    cp._registry.clear()
    principal = cp.PooledClient(client=object(), session_id="s", role="principal")
    especialista = cp.PooledClient(client=object(), session_id="s", role="gestor-recebimento")
    with cp._registry_lock:
        cp._registry[cp._pool_key("s", "principal")] = principal
        cp._registry[cp._pool_key("s", "gestor-recebimento")] = especialista
    assert cp.get_pooled_client("s", role="principal") is principal
    assert cp.get_pooled_client("s", role="gestor-recebimento") is especialista
    assert cp.get_pooled_client("s") is principal  # retrocompat
    cp._registry.clear()
