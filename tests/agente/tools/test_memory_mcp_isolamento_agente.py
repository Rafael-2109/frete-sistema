"""E2.6 — Isolamento de leitura/listagem/clear de memória por agente em memory_mcp_tool.

Verifica que as operações de READ/LIST/CLEAR do motor MCP isolam por agente,
do mesmo modo que a ESCRITA já isola desde F2 Fase 1. Cobre:
  - _build_memory_index: retorna apenas memórias do agente atual.
  - AgentMemory.list_directory_for_agent: lista filtrada por agente.
  - AgentMemory.clear_all_for_user(uid, agente=X): remove só o agente X.
  - AgentMemory.get_by_path_for_agent: sanity de get isolado (já existia).
"""
import pytest

from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentMemory


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def test_user(app):
    email = 'test_mcp_isolamento@test.com'
    user = Usuario.query.filter_by(email=email).first()
    if user:
        return user
    user = Usuario(email=email, nome='Test MCP Isolamento', perfil='agente', status='ativo')
    user.set_senha('x')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def limpa(app, test_user):
    """Remove memórias do prefixo de teste antes e depois."""
    prefix = '/memories/_pytest_mcp'

    def _cleanup():
        AgentMemory.query.filter(
            AgentMemory.user_id == test_user.id,
            AgentMemory.path.like(f'{prefix}%'),
        ).delete(synchronize_session=False)
        db.session.commit()

    _cleanup()
    yield prefix
    _cleanup()


def test_build_memory_index_isola_por_agente(app, limpa, test_user):
    """_build_memory_index deve retornar apenas memórias do agente atual."""
    from app.agente.config import permissions
    from app.agente.tools.memory_mcp_tool import _build_memory_index

    # Seed: 1 memória de cada agente
    path_web = f'{limpa}/w.xml'
    path_lojas = f'{limpa}/l.xml'
    AgentMemory.create_file(test_user.id, path_web, 'SEGREDO_WEB', agente='web')
    AgentMemory.create_file(test_user.id, path_lojas, 'DADO_LOJA', agente='lojas')
    db.session.commit()

    # Agente lojas: vê l.xml, NÃO vê w.xml
    permissions.set_current_agent_id('lojas')
    try:
        texto, struct = _build_memory_index(test_user.id)
    finally:
        permissions.clear_current_agent_id()

    paths_encontrados = [e['path'] for e in struct['memories']]
    assert path_lojas in paths_encontrados, f"lojas deve ver {path_lojas}"
    assert path_web not in paths_encontrados, f"lojas NAO deve ver {path_web}"
    assert 'SEGREDO_WEB' not in texto

    # Agente web: vê w.xml, NÃO vê l.xml
    permissions.set_current_agent_id('web')
    try:
        texto2, struct2 = _build_memory_index(test_user.id)
    finally:
        permissions.clear_current_agent_id()

    paths_encontrados2 = [e['path'] for e in struct2['memories']]
    assert path_web in paths_encontrados2, f"web deve ver {path_web}"
    assert path_lojas not in paths_encontrados2, f"web NAO deve ver {path_lojas}"


def test_list_directory_for_agent_isola(app, limpa, test_user):
    """list_directory_for_agent deve retornar apenas filhos do agente especificado."""
    path_web = f'{limpa}/w.xml'
    path_lojas = f'{limpa}/l.xml'
    AgentMemory.create_file(test_user.id, path_web, 'web_content', agente='web')
    AgentMemory.create_file(test_user.id, path_lojas, 'lojas_content', agente='lojas')
    db.session.commit()

    itens_lojas = AgentMemory.list_directory_for_agent(test_user.id, limpa, 'lojas')
    paths_lojas = [i.path for i in itens_lojas]
    assert path_lojas in paths_lojas, f"list_directory_for_agent('lojas') deve retornar {path_lojas}"
    assert path_web not in paths_lojas, f"list_directory_for_agent('lojas') NAO deve retornar {path_web}"

    itens_web = AgentMemory.list_directory_for_agent(test_user.id, limpa, 'web')
    paths_web = [i.path for i in itens_web]
    assert path_web in paths_web, f"list_directory_for_agent('web') deve retornar {path_web}"
    assert path_lojas not in paths_web, f"list_directory_for_agent('web') NAO deve retornar {path_lojas}"


def test_clear_all_for_user_so_remove_o_agente(app, limpa, test_user):
    """clear_all_for_user(uid, agente=X) remove só X; sem agente remove tudo."""
    path_web = f'{limpa}/clr_w.xml'
    path_lojas = f'{limpa}/clr_l.xml'
    AgentMemory.create_file(test_user.id, path_web, 'w', agente='web')
    AgentMemory.create_file(test_user.id, path_lojas, 'l', agente='lojas')
    db.session.commit()

    # Clear apenas lojas
    AgentMemory.clear_all_for_user(test_user.id, agente='lojas')
    db.session.commit()

    remaining = AgentMemory.query.filter(
        AgentMemory.user_id == test_user.id,
        AgentMemory.path.like(f'{limpa}%'),
    ).all()
    paths_remaining = [m.path for m in remaining]

    # lojas foi removida
    assert path_lojas not in paths_remaining, f"{path_lojas} deveria ter sido removida"
    # web permanece
    assert path_web in paths_remaining, f"{path_web} deveria ter permanecido"

    # Clear sem agente remove tudo (compat)
    AgentMemory.clear_all_for_user(test_user.id)
    db.session.commit()

    all_remaining = AgentMemory.query.filter(
        AgentMemory.user_id == test_user.id,
        AgentMemory.path.like(f'{limpa}%'),
    ).all()
    assert all_remaining == [], "clear_all_for_user sem agente deve remover tudo"


def test_get_by_path_for_agent_usado_na_leitura(app, limpa, test_user):
    """get_by_path_for_agent deve isolar por agente no mesmo path."""
    path = f'{limpa}/shared.xml'
    AgentMemory.create_file(test_user.id, path, 'conteudo_web', agente='web')
    AgentMemory.create_file(test_user.id, path, 'conteudo_lojas', agente='lojas')
    db.session.commit()

    mem_lojas = AgentMemory.get_by_path_for_agent(test_user.id, path, 'lojas')
    mem_web = AgentMemory.get_by_path_for_agent(test_user.id, path, 'web')

    assert mem_lojas is not None, "get_by_path_for_agent('lojas') deve encontrar a memória lojas"
    assert mem_web is not None, "get_by_path_for_agent('web') deve encontrar a memória web"
    assert mem_lojas.agente == 'lojas'
    assert mem_web.agente == 'web'
    assert mem_lojas.content == 'conteudo_lojas'
    assert mem_web.content == 'conteudo_web'
    assert mem_lojas.id != mem_web.id, "devem ser registros distintos"


def test_regenerate_pitfalls_xml_grava_com_agente_atual(app, test_user):
    """_regenerate_pitfalls_xml (handler síncrono) grava o XML de pitfalls com o
    agente atual do ContextVar (E2.6 — escrita isolada)."""
    from app.agente.config import permissions
    from app.agente.tools.memory_mcp_tool import _regenerate_pitfalls_xml
    path = '/memories/empresa/armadilhas/system-pitfalls.xml'

    def _clean():
        AgentMemory.query.filter(
            AgentMemory.user_id == test_user.id, AgentMemory.path == path,
        ).delete(synchronize_session=False)
        db.session.commit()

    _clean()
    try:
        permissions.set_current_agent_id('lojas')
        _regenerate_pitfalls_xml(
            test_user.id, [{'area': 'x', 'description': 'd', 'hit_count': 1}]
        )
        db.session.commit()
        mem = AgentMemory.get_by_path_for_agent(test_user.id, path, 'lojas')
        assert mem is not None and mem.agente == 'lojas'
        # web NÃO enxerga a memória escrita pelo agente lojas
        assert AgentMemory.get_by_path_for_agent(test_user.id, path, 'web') is None
    finally:
        permissions.clear_current_agent_id()
        _clean()
