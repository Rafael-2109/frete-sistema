"""8b passo 4: pool role-aware no stream (_stream_response_persistent).

O especialista quente obtem/cria seu PROPRIO PooledClient sob a chave
'{session_id}::{role}' (F1 ja deu role= a get_pooled_client/get_or_create_client).
No 1o turno do especialista o slot do papel esta vazio (sdk_session_id=None vindo
do save role-aware) -> resume_id None -> sessao SDK NOVA, sem --resume (reusa a
defesa probe_failed->fallback). O caminho 'principal' (default) e identico.

Como o generator async exige subprocess SDK + setup pesado, o passo 4 trava a
COSTURA (role threadado nas chamadas de pool); a prova comportamental ponta-a-
ponta do swap vem no passo 8 (teste e2e com cliente mockado).
"""
import inspect

from app.agente.sdk.client import AgentClient
from app.agente.sdk import client_pool as cp


def _persistent_src():
    return inspect.getsource(AgentClient._stream_response_persistent)


def test_get_pooled_client_chamado_com_role():
    src = _persistent_src()
    assert 'get_pooled_client(pool_key, role=agent_role)' in src


def test_get_or_create_client_chamado_com_role():
    src = _persistent_src()
    # Ambas as chamadas (criacao + retry sem resume) passam role=agent_role.
    assert src.count('role=agent_role') >= 3  # 1 get_pooled + 2 get_or_create


def test_eviction_usa_chave_composta_por_papel():
    """Os 3 sites de eviction de cliente morto popavam a chave NUA (pool_key),
    mas o registry e' keyed por '{session_id}::{role}' (F1) -> eviction era no-op
    (bug latente). O 8b corrige para _pool_key(pool_key, agent_role)."""
    src = _persistent_src()
    assert '_registry.pop(pool_key, None)' not in src
    assert src.count('_registry.pop(_pool_key(pool_key, agent_role), None)') == 3


def test_pool_isola_principal_e_especialista_mesma_sessao():
    """Garantia de base (F1) que o passo 4 depende: chaves divergem por papel."""
    cp._registry.clear()
    principal = cp.PooledClient(client=object(), session_id='s8b', role='principal')
    espec = cp.PooledClient(client=object(), session_id='s8b', role='gestor-recebimento')
    with cp._registry_lock:
        cp._registry[cp._pool_key('s8b', 'principal')] = principal
        cp._registry[cp._pool_key('s8b', 'gestor-recebimento')] = espec
    assert cp.get_pooled_client('s8b', role='principal') is principal
    assert cp.get_pooled_client('s8b', role='gestor-recebimento') is espec
    cp._registry.clear()
