"""Fase 3.3B do loop corretivo — sinal HARMFUL por error_signature (chave canonica).

ANTES: harmful_count so incrementava quando o dedup-de-CONTEUDO casava
(`_check_memory_duplicate`, overlap 0.65 / embedding 0.85). Reincidencia do MESMO erro
com texto diferente ("mesma intencao, outro caso") escapava -> harmful_count=0 universal
em PROD (medidor cego: nao distingue "regra funcionou" de "nunca mediu").

AGORA: a reincidencia e medida pela `error_signature` (indice ix_agent_memories_user_errsig),
que e a chave projetada para casar o MESMO erro entre sessoes. Cobre:
- `_track_signature_recurrence`: harmful++ na regra dura viva de mesma assinatura;
- anti-dupla-contagem com o caminho legado (dedup-de-conteudo) em `_save_personal_insight`;
- `get_rule_adhesion_panel.contencao`: leitura RETROATIVA por created_at (le hoje, sem
  esperar dados novos).

Determinístico (zero LLM). Sob a flag existente AGENT_OUTCOME_TRACKING (default ON).
"""
from datetime import timedelta

import pytest

from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentMemory
from app.utils.timezone import agora_utc_naive
from app.agente.services.pattern_analyzer import (
    _track_signature_recurrence,
    _save_personal_insight,
)
from app.agente.services.insights_service import get_rule_adhesion_panel


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def user(app):
    u = Usuario.query.filter_by(email='test_outcome_sig@test.com').first()
    if not u:
        u = Usuario(
            email='test_outcome_sig@test.com',
            nome='Test Outcome Sig',
            perfil='agente',
            status='ativo',
        )
        u.set_senha('test_password_123')
        db.session.add(u)
        db.session.commit()
    return u


@pytest.fixture
def limpa(app, user):
    """Remove memorias do user de teste antes e depois (auto-contido)."""
    def _wipe():
        AgentMemory.query.filter_by(user_id=user.id).delete()
        db.session.commit()
    _wipe()
    yield
    _wipe()


def _mk_regra(user_id, sig, priority='mandatory', harmful=0, dias_atras=0,
              path=None, content='[correcao] x\nDO: y'):
    mem = AgentMemory(
        user_id=user_id,
        path=path or f'/memories/corrections/regra_{sig}.xml',
        content=content,
        category='structural',
        priority=priority,
        error_signature=sig,
        harmful_count=harmful,
        is_cold=False,
        is_directory=False,
    )
    db.session.add(mem)
    db.session.flush()
    if dias_atras:
        mem.created_at = agora_utc_naive() - timedelta(days=dias_atras)
    db.session.commit()
    return mem


# ───────────────────── _track_signature_recurrence ─────────────────────

def test_reincidencia_por_signature_incrementa_harmful_na_regra_dura(app, user, limpa):
    regra = _mk_regra(user.id, 'troca_de_escopo', priority='mandatory', harmful=0)
    ok = _track_signature_recurrence(user.id, 'troca_de_escopo')
    assert ok is True
    db.session.refresh(regra)
    assert regra.harmful_count == 1


def test_nao_incrementa_se_regra_e_apenas_contextual(app, user, limpa):
    regra = _mk_regra(user.id, 'erro_leve', priority='contextual', harmful=0)
    ok = _track_signature_recurrence(user.id, 'erro_leve')
    assert ok is False
    db.session.refresh(regra)
    assert regra.harmful_count == 0


def test_nao_incrementa_sem_signature(app, user, limpa):
    assert _track_signature_recurrence(user.id, '') is False


def test_flag_off_nao_incrementa(app, user, limpa, monkeypatch):
    monkeypatch.setattr(
        'app.agente.config.feature_flags.AGENT_OUTCOME_TRACKING', False
    )
    regra = _mk_regra(user.id, 'erro_x', priority='mandatory', harmful=0)
    assert _track_signature_recurrence(user.id, 'erro_x') is False
    db.session.refresh(regra)
    assert regra.harmful_count == 0


# ─────────────── anti-dupla-contagem em _save_personal_insight ───────────────

def test_save_insight_nao_dupla_conta_harmful(app, user, limpa, monkeypatch):
    sig = 'executou_item_vetado'
    regra = _mk_regra(
        user.id, sig, priority='mandatory', harmful=0,
        content='[correcao] usuario vetou X\nDO: nunca executar X',
    )
    # Forca o caminho dedup-de-conteudo a casar a MESMA regra dura (sem depender
    # de embeddings/overlap), para provar que NAO ha dupla-contagem de harmful.
    monkeypatch.setattr(
        'app.agente.tools.memory_mcp_tool._check_memory_duplicate',
        lambda uid, content, current_path='': regra.path,
    )
    _save_personal_insight(
        user.id, 'correcao', 'usuario vetou X', 'nunca executar X',
        error_signature=sig,
    )
    db.session.refresh(regra)
    # signature incrementa 1; o caminho de conteudo NAO re-incrementa (anti-dupla)
    assert regra.harmful_count == 1
    # o reforco por conteudo ainda conta a reincidencia (correction_count)
    assert regra.correction_count == 1


# ───────────────────── painel: contencao retroativa ─────────────────────

def test_painel_contencao_classifica_contida_vs_reincidindo(app, user, limpa):
    # contida: regra dura, ultima correcao ha 60 dias, harmful=0
    _mk_regra(
        user.id, 'sig_contida', priority='mandatory', harmful=0, dias_atras=60,
        path='/memories/corrections/contida.xml',
    )
    # reincidindo: regra dura com harmful>0 (sinal novo) -> falhou
    _mk_regra(
        user.id, 'sig_reincide', priority='mandatory', harmful=2, dias_atras=60,
        path='/memories/corrections/reincide.xml',
    )
    painel = get_rule_adhesion_panel(user_id=user.id)
    cont = painel.get('contencao') or {}
    assert cont.get('promovidas') == 2
    assert cont.get('contidas') == 1
    assert cont.get('reincidindo') == 1
