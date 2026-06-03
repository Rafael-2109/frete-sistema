"""Fase 2 do loop corretivo pessoal: write-path UPDATE (reforco da reincidencia) +
promocao recorrente de correcao a 'mandatory'. Sem custo de API (dedup mockado / SQL puro)."""
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
    user = Usuario.query.filter_by(email='test_fase2@test.com').first()
    if user:
        return user
    user = Usuario(email='test_fase2@test.com', nome='Test Fase2', perfil='agente', status='ativo')
    user.set_senha('test_password_123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def cleanup(app, test_user):
    ids = []
    yield ids, test_user.id
    try:
        db.session.rollback()
    except Exception:
        pass
    for mid in ids:
        m = AgentMemory.query.get(mid)
        if m:
            db.session.delete(m)
    db.session.commit()


def _nova_correcao(user_id, path, content, *, priority='contextual', correction_count=0,
                   importance=0.7):
    """Cria uma correcao e COMMITA (evita colisao de diretorio-pai no proximo create_file)."""
    mem = AgentMemory.create_file(user_id, path, content)
    mem.priority = priority
    mem.correction_count = correction_count
    mem.importance_score = importance
    db.session.commit()
    return mem


def test_reincidencia_de_correcao_reforca_em_vez_de_descartar(app, cleanup, monkeypatch):
    """Fase 2-A: correcao reincidente faz UPDATE (correction_count++), nao descarta (era return False)."""
    ids, user_id = cleanup
    canonica = _nova_correcao(
        user_id, '/memories/corrections/erro-escopo.xml',
        '[correcao] agente trocou de escopo\nDO: confirmar cluster', importance=0.7,
    )
    ids.append(canonica.id)
    assert canonica.correction_count == 0

    # Mock do dedup: a nova correcao e' "similar" a canonica (isola a logica de reforco)
    import app.agente.tools.memory_mcp_tool as mm
    monkeypatch.setattr(
        mm, '_check_memory_duplicate',
        lambda uid, content, current_path='': '/memories/corrections/erro-escopo.xml',
    )

    from app.agente.services.pattern_analyzer import _save_personal_insight
    result = _save_personal_insight(user_id, 'correcao', 'agente trocou de escopo de novo', 'confirmar cluster')

    assert result is True  # reforco conta como salvo (sinal nao some)
    db.session.refresh(canonica)
    assert canonica.correction_count == 1   # reforcado, nao descartado nem duplicado
    assert canonica.importance_score == pytest.approx(0.75)  # subiu 0.05


def test_promove_correcoes_recorrentes_por_threshold(app, cleanup):
    """Fase 2-B: correcao com correction_count >= threshold vira 'mandatory'; abaixo nao."""
    ids, user_id = cleanup
    baixa = _nova_correcao(user_id, '/memories/corrections/baixa.xml', '[correcao] c1\nDO: x', correction_count=1)
    ids.append(baixa.id)
    alta = _nova_correcao(user_id, '/memories/corrections/alta.xml', '[correcao] c2\nDO: y', correction_count=3)
    ids.append(alta.id)

    from app.agente.services.directive_promotion_service import promover_correcoes_recorrentes
    out = promover_correcoes_recorrentes(threshold=2, user_id=user_id)

    db.session.refresh(baixa)
    db.session.refresh(alta)
    assert alta.priority == 'mandatory'    # cc=3 >= 2 -> entra no canal duro
    assert baixa.priority != 'mandatory'   # cc=1 < 2 -> fica como esta
    assert out['promovidas'] == 1


def test_promocao_e_idempotente(app, cleanup):
    """Rodar 2x nao re-promove (correcao ja 'mandatory' e ignorada pelo filtro)."""
    ids, user_id = cleanup
    alta = _nova_correcao(user_id, '/memories/corrections/alta2.xml', '[correcao] c3\nDO: z', correction_count=5)
    ids.append(alta.id)

    from app.agente.services.directive_promotion_service import promover_correcoes_recorrentes
    out1 = promover_correcoes_recorrentes(threshold=2, user_id=user_id)
    out2 = promover_correcoes_recorrentes(threshold=2, user_id=user_id)

    db.session.refresh(alta)
    assert alta.priority == 'mandatory'
    assert out1['promovidas'] == 1
    assert out2['promovidas'] == 0  # idempotente
