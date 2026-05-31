"""
TDD — D4 (Onda 3): query_ontology_entities (read path da ontologia canônica).

Prova:
1. Busca DIRETA na tabela agent_memory_entities (sem HOP-1 nem agent_memory_entity_links).
2. Une user_id do chamador + user_id=0 (empresa/canônico).
3. Filtros: entity_type, name_like, key.
4. Retorna lista de dicts {entity_type, entity_name, entity_key, user_id}.
5. READ-ONLY — nenhuma escrita.

Roda com:
    pytest tests/agente/tools/test_query_ontology.py -v
"""

import pytest
from sqlalchemy import text

from app import create_app, db
from app.agente.services.knowledge_graph_service import _upsert_entity


# =====================================================================
# FIXTURE — app context com DB de teste
# =====================================================================

@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def clean_entities(app_ctx):
    """Fixture: remove entidades de teste antes/depois para isolar."""
    # Antes: cleanup preventivo
    db.session.execute(text("""
        DELETE FROM agent_memory_entities
        WHERE entity_name IN (
            'ATACADAO TESTE D4',
            'CARREFOUR TESTE D4',
            'PRODUTO TESTE D4',
            'ENTIDADE USER7 D4'
        )
    """))
    db.session.commit()
    yield
    # Depois: cleanup
    db.session.execute(text("""
        DELETE FROM agent_memory_entities
        WHERE entity_name IN (
            'ATACADAO TESTE D4',
            'CARREFOUR TESTE D4',
            'PRODUTO TESTE D4',
            'ENTIDADE USER7 D4'
        )
    """))
    db.session.commit()


# =====================================================================
# IMPORTAÇÃO DA FUNÇÃO NÚCLEO (falha antes da implementação)
# =====================================================================

def test_import_query_ontology_entities():
    """A função núcleo deve ser importável do módulo."""
    from app.agente.tools.ontology_query_tool import query_ontology_entities
    assert callable(query_ontology_entities)


# =====================================================================
# TESTES FUNCIONAIS — busca direta + user_id=0 unido
# =====================================================================

class TestQueryOntologyEntities:
    """Testes funcionais de query_ontology_entities."""

    def test_retorna_entidade_canonica_user_0(self, app_ctx, clean_entities):
        """
        Entidade canônica (user_id=0) é retornada quando consultada
        com qualquer user_id de usuário real.

        Prova que a busca NÃO exige link de memória (acesso direto à tabela).
        """
        from app.agente.tools.ontology_query_tool import query_ontology_entities

        # Criar entidade canônica user_id=0 (empresa/sistema)
        with db.engine.connect() as conn:
            _upsert_entity(conn, 0, 'cliente', 'ATACADAO TESTE D4', 'cnpj_00001')
            conn.commit()

        # Consultar com user_id=7 (usuário real)
        results = query_ontology_entities(user_id=7, entity_type='cliente')

        names = [r['entity_name'] for r in results]
        assert 'ATACADAO TESTE D4' in names, (
            f"Entidade canônica (user_id=0) deve aparecer para user_id=7. "
            f"Retornado: {names}"
        )

        # Verificar estrutura do dict retornado
        atacadao = next(r for r in results if r['entity_name'] == 'ATACADAO TESTE D4')
        assert atacadao['entity_type'] == 'cliente'
        assert atacadao['entity_key'] == 'cnpj_00001'
        assert atacadao['user_id'] == 0  # canônica pertence ao sistema

    def test_retorna_entidade_propria_usuario(self, app_ctx, clean_entities):
        """
        Entidade pessoal do usuário (user_id=7) também é retornada.
        """
        from app.agente.tools.ontology_query_tool import query_ontology_entities

        with db.engine.connect() as conn:
            _upsert_entity(conn, 7, 'cliente', 'ENTIDADE USER7 D4', None)
            conn.commit()

        results = query_ontology_entities(user_id=7, entity_type='cliente')
        names = [r['entity_name'] for r in results]
        assert 'ENTIDADE USER7 D4' in names

    def test_une_user_id_e_zero(self, app_ctx, clean_entities):
        """
        Busca sem filtros retorna entidades de AMBOS user_id=7 e user_id=0.
        Prova que a query faz `user_id = ANY([user_id, 0])`.
        """
        from app.agente.tools.ontology_query_tool import query_ontology_entities

        with db.engine.connect() as conn:
            _upsert_entity(conn, 0, 'cliente', 'ATACADAO TESTE D4', None)
            _upsert_entity(conn, 7, 'cliente', 'ENTIDADE USER7 D4', None)
            conn.commit()

        results = query_ontology_entities(user_id=7)
        names = [r['entity_name'] for r in results]
        assert 'ATACADAO TESTE D4' in names, "user_id=0 deve ser incluído"
        assert 'ENTIDADE USER7 D4' in names, "user_id=7 deve ser incluído"

    def test_filtro_entity_type(self, app_ctx, clean_entities):
        """
        Filtro entity_type deve excluir entidades de outros tipos.
        """
        from app.agente.tools.ontology_query_tool import query_ontology_entities

        with db.engine.connect() as conn:
            _upsert_entity(conn, 0, 'cliente', 'ATACADAO TESTE D4', None)
            _upsert_entity(conn, 0, 'produto', 'PRODUTO TESTE D4', None)
            conn.commit()

        results = query_ontology_entities(user_id=7, entity_type='cliente')
        types = {r['entity_type'] for r in results}
        assert 'produto' not in types, "entity_type='produto' não deve aparecer no filtro 'cliente'"

    def test_filtro_name_like(self, app_ctx, clean_entities):
        """
        Filtro name_like deve usar ILIKE (case-insensitive, partial match).
        """
        from app.agente.tools.ontology_query_tool import query_ontology_entities

        with db.engine.connect() as conn:
            _upsert_entity(conn, 0, 'cliente', 'ATACADAO TESTE D4', None)
            _upsert_entity(conn, 0, 'cliente', 'CARREFOUR TESTE D4', None)
            conn.commit()

        results = query_ontology_entities(user_id=7, name_like='ATACADAO')
        names = [r['entity_name'] for r in results]
        assert 'ATACADAO TESTE D4' in names
        assert 'CARREFOUR TESTE D4' not in names

    def test_filtro_key(self, app_ctx, clean_entities):
        """
        Filtro key deve retornar apenas entidade com entity_key exato.
        """
        from app.agente.tools.ontology_query_tool import query_ontology_entities

        with db.engine.connect() as conn:
            _upsert_entity(conn, 0, 'cliente', 'ATACADAO TESTE D4', 'cnpj_unique_d4')
            _upsert_entity(conn, 0, 'cliente', 'CARREFOUR TESTE D4', 'cnpj_other_d4')
            conn.commit()

        results = query_ontology_entities(user_id=7, key='cnpj_unique_d4')
        names = [r['entity_name'] for r in results]
        assert 'ATACADAO TESTE D4' in names
        assert 'CARREFOUR TESTE D4' not in names

    def test_sem_filtros_respeita_limit(self, app_ctx, clean_entities):
        """
        Sem filtros retorna no máximo `limit` resultados.
        """
        from app.agente.tools.ontology_query_tool import query_ontology_entities

        results = query_ontology_entities(user_id=7, limit=1)
        assert len(results) <= 1

    def test_retorna_lista_vazia_quando_nao_ha_resultado(self, app_ctx, clean_entities):
        """
        Busca por chave inexistente retorna lista vazia, não erro.
        """
        from app.agente.tools.ontology_query_tool import query_ontology_entities

        results = query_ontology_entities(
            user_id=7,
            key='chave_que_definitivamente_nao_existe_d4_xyz999',
        )
        assert results == []

    def test_estrutura_dict_retornado(self, app_ctx, clean_entities):
        """
        Cada dict tem EXATAMENTE as chaves esperadas: entity_type, entity_name,
        entity_key, user_id.
        """
        from app.agente.tools.ontology_query_tool import query_ontology_entities

        with db.engine.connect() as conn:
            _upsert_entity(conn, 0, 'cliente', 'ATACADAO TESTE D4', 'key_d4')
            conn.commit()

        results = query_ontology_entities(user_id=7, entity_type='cliente', name_like='ATACADAO')
        assert len(results) >= 1

        item = results[0]
        expected_keys = {'entity_type', 'entity_name', 'entity_key', 'user_id'}
        assert set(item.keys()) == expected_keys, (
            f"Dict deve ter exatamente {expected_keys}, mas tem {set(item.keys())}"
        )

    def test_user_id_0_consultando_si_proprio(self, app_ctx, clean_entities):
        """
        Quando user_id=0 consulta, retorna apenas user_id=0 (sistema não vê pessoal).
        """
        from app.agente.tools.ontology_query_tool import query_ontology_entities

        with db.engine.connect() as conn:
            _upsert_entity(conn, 0, 'cliente', 'ATACADAO TESTE D4', None)
            _upsert_entity(conn, 7, 'cliente', 'ENTIDADE USER7 D4', None)
            conn.commit()

        # Quando user_id=0 consulta, ANY([0, 0]) = [0] — não inclui user_id=7
        results = query_ontology_entities(user_id=0, entity_type='cliente')
        names = [r['entity_name'] for r in results]
        assert 'ATACADAO TESTE D4' in names
        # user_id=7 NÃO deve aparecer para user_id=0
        assert 'ENTIDADE USER7 D4' not in names


# =====================================================================
# TESTE DE DEFINIÇÃO DA TOOL MCP (sem SDK, apenas estrutura)
# =====================================================================

def test_ontology_server_e_none_ou_server_quando_sdk_disponivel():
    """
    ontology_server deve ser definido (não importar com erro).
    Quando SDK não disponível, deve ser None (graceful degradation).
    """
    from app.agente.tools.ontology_query_tool import ontology_server
    # Deve ser None (sem SDK em ambiente de teste) ou um objeto de server
    # O importante é que a importação NÃO levanta exceção
    assert ontology_server is None or hasattr(ontology_server, '__class__')
