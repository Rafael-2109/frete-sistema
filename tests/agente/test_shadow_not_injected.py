"""Regressao: memorias directive_status='shadow' NUNCA sao injetadas no contexto.

Contexto (A4): uma diretriz 'shadow' e candidata EM AVALIACAO — so deve entrar no
contexto do agente apos promocao manual para 'ativa'. O criterio canonico ja existe
em _build_operational_directives (memory_injection.py:504-505): so legado (NULL) ou
'ativa' sao injetaveis.

Bug coberto: os tiers de DESCOBERTA (Tier 2 semantico, Tier 2b KG, fallback recencia)
materializavam AgentMemory por id SEM filtrar directive_status -> shadow vazava por
similaridade (ex: /heuristicas/abordagem-validada-pelo-judge-bom-dia.xml, recuperada
quando o usuario diz "bom dia", nunca efetiva -> infla zero-efficacy).

Fix: filtro na fonte no Tier 2 semantico + guard unico pos-coleta (defesa em
profundidade que cobre KG/fallback e qualquer tier futuro).
"""
import uuid
from unittest.mock import patch

import pytest

from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentMemory
from app.agente.sdk import memory_injection


@pytest.fixture
def app():
    _app = create_app()
    with _app.app_context():
        yield _app


@pytest.fixture
def test_user(app):
    user = Usuario.query.filter_by(email='test_shadow_inject@test.com').first()
    if not user:
        user = Usuario(
            email='test_shadow_inject@test.com',
            nome='Test Shadow Inject',
            perfil='agente',
            status='ativo',
        )
        user.set_senha('test_password_123')
        db.session.add(user)
        db.session.commit()
    return user


@pytest.fixture
def mems(app, test_user):
    """Coleta ids criados e limpa ao final (+ limpa cache de injecao)."""
    created = []
    yield created, test_user.id
    for mid in created:
        obj = AgentMemory.query.get(mid)
        if obj:
            db.session.delete(obj)
    db.session.commit()
    memory_injection._SESSION_INJECTION_CACHE.clear()


def _mk(user_id, slug, status, created):
    """Cria heuristica empresa com directive_status definido."""
    mem = AgentMemory.create_file(
        user_id,
        f'/memories/empresa/heuristicas/{slug}-{uuid.uuid4().hex[:6]}.xml',
        f'<nivel>5</nivel><prescricao>conteudo de teste {slug}</prescricao>',
    )
    mem.directive_status = status
    db.session.commit()
    created.append(mem.id)
    return mem


def test_shadow_excluded_from_semantic_tier(app, mems):
    """Tier 2 semantico (filtro na fonte): shadow/despromovida nao injetada; ativa/legado sim.

    'despromovida' e o estado REAL observado em PROD no cluster
    /heuristicas/abordagem-validada-pelo-judge-* (ids 848/856/864...): diretrizes
    despromovidas que continuavam recuperadas por similaridade (usage alto, efic ~0)
    porque o retrieval nao filtrava directive_status.
    """
    created, user_id = mems
    shadow = _mk(user_id, 'judge-bom-dia', 'shadow', created)
    desprom = _mk(user_id, 'judge-despromovida', 'despromovida', created)
    ativa = _mk(user_id, 'regra-ativa', 'ativa', created)
    legado = _mk(user_id, 'legado-null', None, created)

    fake_semantic = [
        {'memory_id': shadow.id, 'similarity': 0.95},
        {'memory_id': desprom.id, 'similarity': 0.95},
        {'memory_id': ativa.id, 'similarity': 0.95},
        {'memory_id': legado.id, 'similarity': 0.95},
    ]

    with patch('app.embeddings.config.MEMORY_SEMANTIC_SEARCH', True), \
         patch('app.embeddings.memory_search.buscar_memorias_semantica',
               return_value=fake_semantic), \
         patch('app.agente.services.knowledge_graph_service.query_graph_memories',
               return_value=[]):
        _, _, injected_ids = memory_injection._load_user_memories_for_context(
            user_id=user_id, prompt='bom dia', model_name='claude-opus-4-8',
        )

    assert shadow.id not in injected_ids, "shadow vazou via Tier 2 semantico"
    assert desprom.id not in injected_ids, "despromovida vazou via Tier 2 semantico"
    assert ativa.id in injected_ids, "diretriz 'ativa' deveria ser injetada"
    assert legado.id in injected_ids, "memoria legado (NULL) deveria ser injetada"


def test_shadow_excluded_from_kg_tier(app, mems):
    """Tier 2b KG (guard unico pos-coleta): shadow nao injetada; ativa sim."""
    created, user_id = mems
    shadow = _mk(user_id, 'judge-ola', 'shadow', created)
    ativa = _mk(user_id, 'regra-kg-ativa', 'ativa', created)

    fake_kg = [
        {'memory_id': shadow.id, 'similarity': 0.9},
        {'memory_id': ativa.id, 'similarity': 0.9},
    ]

    with patch('app.embeddings.config.MEMORY_SEMANTIC_SEARCH', True), \
         patch('app.embeddings.memory_search.buscar_memorias_semantica',
               return_value=[]), \
         patch('app.agente.services.knowledge_graph_service.query_graph_memories',
               return_value=fake_kg):
        _, _, injected_ids = memory_injection._load_user_memories_for_context(
            user_id=user_id, prompt='ola', model_name='claude-opus-4-8',
        )

    assert shadow.id not in injected_ids, "shadow vazou via Tier 2b KG (guard falhou)"
    assert ativa.id in injected_ids, "diretriz 'ativa' deveria ser injetada via KG"
