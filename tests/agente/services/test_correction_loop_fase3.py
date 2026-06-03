"""Fase 3 do loop corretivo pessoal:
- 3.2A: _save_personal_insight persiste error_signature; reincidencia herda assinatura.
- 3.2B: _reframe_as_compiled_memory (frame imperativo) puro + aplicado na promocao.
- 3.3: sinal harmful (regra dura reincidiu) no write-path.
Sem custo de API (dedup mockado / funcao pura)."""
import pytest
from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentMemory
from app.agente.services.directive_promotion_service import (
    _reframe_as_compiled_memory,
    promover_correcoes_recorrentes,
    demote_stale_rules,
)
from app.agente.routes._helpers import _track_outcome_by_recurrence


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def test_user(app):
    user = Usuario.query.filter_by(email='test_fase3@test.com').first()
    if user:
        return user
    user = Usuario(email='test_fase3@test.com', nome='Test Fase3', perfil='agente', status='ativo')
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
                   importance=0.7, error_signature=None, harmful_count=0, usage_count=0):
    mem = AgentMemory.create_file(user_id, path, content)
    mem.priority = priority
    mem.correction_count = correction_count
    mem.importance_score = importance
    mem.error_signature = error_signature
    mem.harmful_count = harmful_count
    mem.usage_count = usage_count
    db.session.commit()
    return mem


# ───────────────────────── 3.2B: _reframe_as_compiled_memory (puro) ─────────────────────────

def test_reframe_gera_frame_imperativo_sempre():
    out = _reframe_as_compiled_memory('[correcao] agente trocou de escopo\nDO: confirmar o cluster antes de consultar')
    assert out.startswith('SEMPRE:')
    assert 'WHEN:' in out
    assert 'DO:' in out
    assert 'confirmar o cluster antes de consultar' in out


def test_reframe_usa_nunca_para_negacao():
    out = _reframe_as_compiled_memory('[correcao] executou padrao vetado\nDO: nao processar padrao que o usuario vetou')
    assert out.startswith('NUNCA:')


def test_reframe_e_idempotente():
    base = '[correcao] x\nDO: usar tabela plana'
    um = _reframe_as_compiled_memory(base)
    dois = _reframe_as_compiled_memory(um)
    assert um == dois  # ja imperativo -> nao reprocessa


def test_reframe_preserva_vazio():
    assert _reframe_as_compiled_memory('') == ''
    assert _reframe_as_compiled_memory(None) is None


# ───────────────────────── 3.2A: error_signature no write-path ─────────────────────────

def test_save_correcao_persiste_error_signature(app, cleanup, monkeypatch):
    """Nova correcao com error_signature -> coluna preenchida."""
    ids, user_id = cleanup
    import app.agente.tools.memory_mcp_tool as mm
    monkeypatch.setattr(mm, '_check_memory_duplicate', lambda uid, content, current_path='': None)

    from app.agente.services.pattern_analyzer import _save_personal_insight
    ok = _save_personal_insight(
        user_id, 'correcao',
        'agente respondeu sobre o cluster errado de novo',
        'confirmar qual cluster antes de buscar dados',
        error_signature='respondeu_cluster_errado',
    )
    assert ok is True
    mem = AgentMemory.query.filter(
        AgentMemory.user_id == user_id,
        AgentMemory.error_signature == 'respondeu_cluster_errado',
    ).first()
    assert mem is not None
    ids.append(mem.id)


def test_reincidencia_em_regra_dura_conta_harmful(app, cleanup, monkeypatch):
    """3.3: canonica JA 'mandatory' + reincidencia -> harmful_count++ + herda assinatura."""
    ids, user_id = cleanup
    canonica = _nova_correcao(
        user_id, '/memories/corrections/escopo-dura.xml',
        '[correcao] trocou de escopo\nDO: confirmar cluster',
        priority='mandatory', correction_count=2, error_signature=None,
    )
    ids.append(canonica.id)
    assert (canonica.harmful_count or 0) == 0

    import app.agente.tools.memory_mcp_tool as mm
    monkeypatch.setattr(
        mm, '_check_memory_duplicate',
        lambda uid, content, current_path='': '/memories/corrections/escopo-dura.xml',
    )
    from app.agente.services.pattern_analyzer import _save_personal_insight
    ok = _save_personal_insight(
        user_id, 'correcao', 'trocou de escopo outra vez', 'confirmar cluster',
        error_signature='troca_de_escopo',
    )
    assert ok is True
    db.session.refresh(canonica)
    assert canonica.correction_count == 3          # reforcada
    assert canonica.harmful_count == 1             # regra dura falhou em prevenir
    assert canonica.error_signature == 'troca_de_escopo'  # backfill da assinatura


# ───────────────────────── 3.2B aplicado na promocao ─────────────────────────

def test_promocao_reescreve_em_frame_imperativo(app, cleanup):
    """Ao promover a 'mandatory', o content vira frame imperativo (Compiled Memory)."""
    ids, user_id = cleanup
    mem = _nova_correcao(
        user_id, '/memories/corrections/reframe.xml',
        '[correcao] agente expandiu o escopo\nDO: manter o escopo definido pelo usuario',
        correction_count=3,
    )
    ids.append(mem.id)

    out = promover_correcoes_recorrentes(threshold=2, user_id=user_id)
    db.session.refresh(mem)
    assert mem.priority == 'mandatory'
    assert mem.content.startswith('SEMPRE:') or mem.content.startswith('NUNCA:')
    assert 'WHEN:' in mem.content
    assert out['promovidas'] == 1
    assert out.get('reescritas', 0) == 1


# ───────────────────────── 3.6: demote_stale_rules ─────────────────────────

def test_demote_flag_off_nao_rebaixa(app, cleanup, monkeypatch):
    """Default OFF: nenhuma regra e rebaixada (seguro por padrao)."""
    monkeypatch.setattr('app.agente.config.feature_flags.AGENT_CORRECTION_DEMOTION', False)
    ids, user_id = cleanup
    m = _nova_correcao(user_id, '/memories/corrections/dur-falha-off.xml', '[correcao] x\nDO: y',
                       priority='mandatory', harmful_count=5)
    ids.append(m.id)
    out = demote_stale_rules(user_id=user_id)
    db.session.refresh(m)
    assert m.priority == 'mandatory'  # intacta
    assert out['rebaixadas'] == 0


def test_demote_rebaixa_regra_dura_harmful(app, cleanup, monkeypatch):
    """Flag ON: regra dura com harmful_count >= threshold vira contextual + cold (fora de circulacao)."""
    monkeypatch.setattr('app.agente.config.feature_flags.AGENT_CORRECTION_DEMOTION', True)
    ids, user_id = cleanup
    harmful = _nova_correcao(user_id, '/memories/corrections/dur-falha.xml', '[correcao] a\nDO: b',
                             priority='mandatory', harmful_count=2)
    ids.append(harmful.id)
    limpa = _nova_correcao(user_id, '/memories/corrections/dur-limpa.xml', '[correcao] c\nDO: d',
                           priority='mandatory', harmful_count=0)
    ids.append(limpa.id)

    out = demote_stale_rules(harmful_threshold=2, user_id=user_id)
    db.session.refresh(harmful)
    db.session.refresh(limpa)
    assert harmful.priority == 'contextual'   # rebaixada
    assert harmful.is_cold is True            # fora de circulacao
    assert limpa.priority == 'mandatory'      # harmful_count=0 -> intacta
    assert out['rebaixadas'] == 1


def test_demote_flap_free_nao_repromove(app, cleanup, monkeypatch):
    """Regra rebaixada (is_cold) NAO e re-promovida pela fonte 3 (filtra is_cold==False)."""
    monkeypatch.setattr('app.agente.config.feature_flags.AGENT_CORRECTION_DEMOTION', True)
    ids, user_id = cleanup
    # cc alto (re-promoveria) MAS harmful -> demote -> cold -> promocao ignora
    m = _nova_correcao(user_id, '/memories/corrections/flap.xml', '[correcao] e\nDO: f',
                       priority='mandatory', correction_count=9, harmful_count=2)
    ids.append(m.id)

    demote_stale_rules(harmful_threshold=2, user_id=user_id)
    db.session.refresh(m)
    assert m.is_cold is True and m.priority == 'contextual'

    out = promover_correcoes_recorrentes(threshold=2, user_id=user_id)
    db.session.refresh(m)
    assert m.priority == 'contextual'   # NAO re-promovida (flap-free)
    assert out['promovidas'] == 0


# ───────────────────────── 3.3: helpful via _track_outcome_by_recurrence ─────────────────────────

def test_helpful_credita_regra_dura_limpa_a_cada_k(app, cleanup, monkeypatch):
    """Regra dura injetada, harmful_count=0, usage_count multiplo de K -> helpful_count++."""
    monkeypatch.setattr('app.agente.config.feature_flags.AGENT_OUTCOME_TRACKING', True)
    monkeypatch.setattr('app.agente.config.feature_flags.AGENT_OUTCOME_HELPFUL_K_SESSIONS', 3)
    ids, user_id = cleanup
    mem = _nova_correcao(user_id, '/memories/corrections/help.xml', '[correcao] a\nDO: b',
                         priority='mandatory', harmful_count=0, usage_count=3)
    ids.append(mem.id)

    _track_outcome_by_recurrence(user_id, [mem.id])
    db.session.refresh(mem)
    assert mem.helpful_count == 1


def test_helpful_nao_credita_fora_do_multiplo_de_k(app, cleanup, monkeypatch):
    """usage_count nao multiplo de K -> sem credito (bounded)."""
    monkeypatch.setattr('app.agente.config.feature_flags.AGENT_OUTCOME_TRACKING', True)
    monkeypatch.setattr('app.agente.config.feature_flags.AGENT_OUTCOME_HELPFUL_K_SESSIONS', 3)
    ids, user_id = cleanup
    mem = _nova_correcao(user_id, '/memories/corrections/help2.xml', '[correcao] a\nDO: b',
                         priority='mandatory', harmful_count=0, usage_count=4)
    ids.append(mem.id)

    _track_outcome_by_recurrence(user_id, [mem.id])
    db.session.refresh(mem)
    assert mem.helpful_count == 0


def test_helpful_nao_credita_regra_harmful(app, cleanup, monkeypatch):
    """harmful_count > 0 -> nunca credita helpful (regra nao confiavel)."""
    monkeypatch.setattr('app.agente.config.feature_flags.AGENT_OUTCOME_TRACKING', True)
    monkeypatch.setattr('app.agente.config.feature_flags.AGENT_OUTCOME_HELPFUL_K_SESSIONS', 3)
    ids, user_id = cleanup
    mem = _nova_correcao(user_id, '/memories/corrections/help3.xml', '[correcao] a\nDO: b',
                         priority='mandatory', harmful_count=1, usage_count=3)
    ids.append(mem.id)

    _track_outcome_by_recurrence(user_id, [mem.id])
    db.session.refresh(mem)
    assert mem.helpful_count == 0


def test_helpful_flag_off_nao_credita(app, cleanup, monkeypatch):
    """AGENT_OUTCOME_TRACKING OFF -> nenhum credito."""
    monkeypatch.setattr('app.agente.config.feature_flags.AGENT_OUTCOME_TRACKING', False)
    ids, user_id = cleanup
    mem = _nova_correcao(user_id, '/memories/corrections/help4.xml', '[correcao] a\nDO: b',
                         priority='mandatory', harmful_count=0, usage_count=3)
    ids.append(mem.id)

    _track_outcome_by_recurrence(user_id, [mem.id])
    db.session.refresh(mem)
    assert mem.helpful_count == 0
