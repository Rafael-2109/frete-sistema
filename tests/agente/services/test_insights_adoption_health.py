"""Pacote UX /agente/insights (2026-06-12) — adocao real + health decomposto.

Cobre:
(a) `_calc_adoption_rate` com o modelo REAL (Usuario.status == 'ativo' — o bug
    original usava `Usuario.ativo`, coluna inexistente -> AttributeError mudo
    -> adocao 0% na tela) + delta de adocao em `_compute_deltas`/`_null_deltas`
    + adoption_rate presente em `_compute_all` (sem isso o delta seria sempre
    None: o periodo anterior nunca teria a chave).
(b) `_health_score_breakdown`: soma das contribuicoes == score, pesos corretos,
    compat com `_calc_health_score`.
+ wiring do template (deterministico, sem DB) das features novas.

DB via fixture `db` do conftest raiz (savepoint + rollback automatico).
"""
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.utils.timezone import agora_utc_naive

TEMPLATE = Path('app/agente/templates/agente/insights.html')


def _mk_usuario(db, status='ativo'):
    from app.auth.models import Usuario
    u = Usuario(
        nome=f'Adocao Teste {uuid.uuid4().hex[:6]}',
        email=f'adocao_{uuid.uuid4().hex[:10]}@test.com',
        perfil='vendedor',
        status=status,
    )
    u.set_senha('senha_de_teste_123')
    db.session.add(u)
    db.session.flush()
    return u


class _FakeSession:
    """Sessao minima com os atributos que _compute_all consome."""

    def __init__(self, user_id):
        self.user_id = user_id
        self.message_count = 4
        self.total_cost_usd = 1.0
        self.created_at = agora_utc_naive()
        self.summary = None
        self.data = None
        self.model = 'claude-opus-4-8'
        self.session_id = f'fake-{uuid.uuid4().hex[:8]}'
        self.title = 'Sessao de teste'

    def get_messages(self):
        return []


# ───────────────────────── (a) adocao ─────────────────────────

class TestAdoptionRate:

    def test_calc_adoption_rate_usa_status_ativo(self, db):
        """Regressao do bug raiz: o codigo antigo estourava AttributeError em
        `Usuario.ativo` (coluna inexistente) e retornava 0.0 MUDO para qualquer
        entrada. Com denominador = usuarios status='ativo' e numerador =
        usuarios distintos do agente, a formula real tem que aparecer.

        Nota: o DB local pode ter milhares de usuarios ativos (residuo de
        testes) — 1 usuario do agente arredondaria para 0.0. Por isso o caso
        "todos adotaram" (numerador == denominador) prova rate == 100.0."""
        from app.auth.models import Usuario
        from app.agente.services.insights_service import _calc_adoption_rate

        u = _mk_usuario(db, status='ativo')
        total_ativos = Usuario.query.filter(Usuario.status == 'ativo').count()
        assert total_ativos >= 1

        # precisao: 1 usuario do agente -> 1/total (formula exata)
        rate_um = _calc_adoption_rate([SimpleNamespace(user_id=u.id)])
        assert rate_um == round((1 / total_ativos) * 100, 1)

        # regressao (nao pode ser 0.0 mudo): adocao plena -> 100%
        sessions_todos = [
            SimpleNamespace(user_id=i) for i in range(1, total_ativos + 1)
        ]
        assert _calc_adoption_rate(sessions_todos) == 100.0

    def test_usuario_pendente_nao_entra_no_denominador(self, db):
        """Usuarios 'pendente'/'bloqueado' nao contam como base de adocao."""
        from app.agente.services.insights_service import _calc_adoption_rate

        u_ativo = _mk_usuario(db, status='ativo')
        sessions = [SimpleNamespace(user_id=u_ativo.id)]
        rate_antes = _calc_adoption_rate(sessions)

        _mk_usuario(db, status='pendente')
        _mk_usuario(db, status='bloqueado')
        rate_depois = _calc_adoption_rate(sessions)

        assert rate_depois == rate_antes

    def test_compute_all_inclui_adoption_rate(self, db):
        """adoption_rate calculada em _compute_all — pre-requisito para o
        periodo ANTERIOR ter o valor e o delta de adocao nao ser sempre None."""
        from app.agente.services.insights_service import _compute_all

        u = _mk_usuario(db, status='ativo')
        result = _compute_all([_FakeSession(u.id)], days=7)

        assert 'adoption_rate' in result
        assert isinstance(result['adoption_rate'], float)
        assert result['adoption_rate'] >= 0


class TestAdoptionDelta:

    def test_compute_deltas_inclui_adoption_rate(self):
        from app.agente.services.insights_service import _compute_deltas

        current = {'overview': {}, 'resolution_rate': 0, 'adoption_rate': 30.0}
        previous = {'overview': {}, 'resolution_rate': 0, 'adoption_rate': 20.0}

        d = _compute_deltas(current, previous)
        assert d['adoption_rate'] == 50.0  # (30-20)/20 * 100

    def test_compute_deltas_adoption_previous_zero_e_none(self):
        from app.agente.services.insights_service import _compute_deltas

        d = _compute_deltas(
            {'overview': {}, 'adoption_rate': 30.0},
            {'overview': {}, 'adoption_rate': 0.0},
        )
        assert d['adoption_rate'] is None

    def test_null_deltas_inclui_adoption_rate(self):
        from app.agente.services.insights_service import _null_deltas

        nd = _null_deltas()
        assert 'adoption_rate' in nd
        assert nd['adoption_rate'] is None


# ───────────────────────── (b) health decomposto ─────────────────────────

class TestHealthScoreBreakdown:

    def test_pesos_nomes_e_soma_igual_score(self):
        from app.agente.services.insights_service import (
            _calc_health_score, _health_score_breakdown,
        )

        bd = _health_score_breakdown(
            resolution_rate=72.0, friction_score=30.0,
            cost_delta=10.0, adoption_rate=26.0,
        )
        comps = bd['componentes']

        assert [c['nome'] for c in comps] == [
            'Resolucao', 'Baixa friccao', 'Estabilidade de custo', 'Adocao',
        ]
        assert [c['peso'] for c in comps] == [0.35, 0.25, 0.20, 0.20]

        # contribuicao = valor * peso (por componente)
        for c in comps:
            assert c['contribuicao'] == round(c['valor'] * c['peso'], 1)

        # soma das contribuicoes == score
        soma = round(sum(c['contribuicao'] for c in comps), 1)
        assert soma == bd['score'] == 62.9  # 25.2 + 17.5 + 15.0 + 5.2

        # compat: a assinatura existente retorna o MESMO score
        assert _calc_health_score(72.0, 30.0, 10.0, 26.0) == bd['score']

    @pytest.mark.parametrize('cost_delta,esperado', [
        (None, 70.0),    # neutro (sem periodo anterior)
        (-5.0, 100.0),   # custo desceu
        (10.0, 75.0),    # subiu pouco
        (40.0, 50.0),    # subiu moderado
        (80.0, 25.0),    # subiu muito
        (150.0, 0.0),    # disparou
    ])
    def test_cost_stability_tiers(self, cost_delta, esperado):
        from app.agente.services.insights_service import _health_score_breakdown

        bd = _health_score_breakdown(
            resolution_rate=0.0, friction_score=0.0,
            cost_delta=cost_delta, adoption_rate=0.0,
        )
        custo = next(c for c in bd['componentes'] if c['nome'] == 'Estabilidade de custo')
        assert custo['valor'] == esperado

    def test_score_clampado_0_100(self):
        from app.agente.services.insights_service import _health_score_breakdown

        bd = _health_score_breakdown(
            resolution_rate=100.0, friction_score=0.0,
            cost_delta=-10.0, adoption_rate=100.0,
        )
        assert bd['score'] == 100.0


# ───────────────────── wiring do template (sem DB) ─────────────────────

@pytest.fixture(scope='module')
def html():
    return TEMPLATE.read_text(encoding='utf-8')


class TestTemplateWiring:

    def test_delta_adocao_usa_adoption_rate(self, html):
        # bug original: o card de Adocao exibia o delta de unique_users
        assert "renderDelta('kpiAdoptionDelta', d.adoption_rate" in html
        assert "renderDelta('kpiAdoptionDelta', d.unique_users" not in html

    def test_health_breakdown_renderizado(self, html):
        assert 'id="healthBreakdown"' in html
        assert 'function renderHealthBreakdown(' in html
        assert 'data.health_breakdown' in html

    def test_drilldown_usuarios_para_sessoes(self, html):
        assert 'function drillToUserSessions(' in html
        assert 'function clearUserFilter(' in html
        assert 'id="userFilterPill"' in html

    def test_card_judge_mostra_data_origem_e_pergunta(self, html):
        assert 'formatDateShort(' in html
        assert 'c.origem' in html
        assert 'truncate(pergunta, 80)' in html

    def test_tooltip_badge_adversarial(self, html):
        assert 'Julgue o JUDGE, nao o refutador' in html

    def test_kpis_tem_tooltips(self, html):
        # 1 frase por KPI com a formula real (title= no .kpi-card)
        assert html.count('fa-circle-info') >= 6
        assert "status 'ativo'" in html

    def test_subtitulo_reincidencia(self, html):
        assert 'Mesmo erro voltou a acontecer?' in html

    def test_contexto_card_calibracao(self, html):
        assert 'Voce audita o avaliador automatico' in html
