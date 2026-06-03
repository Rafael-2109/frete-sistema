"""Onda 0 / O0.7: o embed best-effort que FALHA num statement de DB NAO pode envenenar a
sessao SQLAlchemy. Sem o rollback no except, a tx fica abortada e o resto do request quebra
com InFailedSqlTransaction (a memoria ja foi salva antes — sem perda de dado, mas o request
seguinte morre). Bug latente em PROD (so morde em falha transitoria da Voyage/DB)."""
import pytest
from sqlalchemy import text

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
    u = Usuario.query.filter_by(email='test_embed_rb@test.com').first()
    if u:
        return u
    u = Usuario(email='test_embed_rb@test.com', nome='Test Embed RB', perfil='agente', status='ativo')
    u.set_senha('x')
    db.session.add(u)
    db.session.commit()
    return u


def test_embed_db_failure_does_not_poison_session(app, test_user, monkeypatch):
    import app.agente.tools.memory_mcp_tool as mm
    path = '/memories/corrections/embed-rb-test.xml'
    content = '[correcao] x\nDO: y'

    db.session.execute(text("DELETE FROM agent_memories WHERE user_id=:u"), {'u': test_user.id})
    db.session.commit()
    AgentMemory.create_file(test_user.id, path, content)
    db.session.commit()

    # Garante que o caminho do embed roda (semantic ON) sem custo de Sonnet (contextual OFF).
    monkeypatch.setattr('app.embeddings.config.MEMORY_SEMANTIC_SEARCH', True)
    monkeypatch.setattr('app.embeddings.config.MEMORY_CONTEXTUAL_EMBEDDING', False)

    # Forca uma falha REAL de SQL no meio do embed -> aborta a tx PG (simula o caminho de erro:
    # Voyage transitoria nao-graceful, coluna ausente, soluço de DB no insert, etc.).
    from app.embeddings.service import EmbeddingService

    def boom(self, texts, input_type=None):
        db.session.execute(text("SELECT * FROM __tabela_inexistente_embed_rb__"))

    monkeypatch.setattr(EmbeddingService, 'embed_texts', boom)

    # best-effort: NAO deve levantar
    mm._embed_memory_best_effort(test_user.id, path, content)

    # INVARIANTE: a sessao deve estar utilizavel (rollback ocorreu no except do best-effort).
    # Sem o fix: InFailedSqlTransaction aqui.
    assert db.session.execute(text("SELECT 1")).scalar() == 1

    db.session.execute(text("DELETE FROM agent_memories WHERE user_id=:u"), {'u': test_user.id})
    db.session.commit()
