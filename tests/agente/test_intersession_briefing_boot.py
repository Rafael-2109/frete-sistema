"""F4.1 + F4.5 PAD-CTX — Briefing inter-sessao: relocacao de blocos nao-operacionais.

PAD-CTX ("Hook dinamico — layout, orcamento e ordem"): excluidos do boot operacional
`stale_empresa`, `improvement_responses` e `intelligence_report` (acessiveis on-demand
via tela admin /agente/memorias e rotas D7/D8). Excecao condicional (4.5):
improvement_response de skill_bug ATIVO volta ao hook SOMENTE no turno que usa a
skill afetada (PreToolUse Skill — mesmo veiculo dos lembretes de skill).
"""
import uuid
from unittest.mock import patch

import pytest

from app import create_app, db
from app.agente.services import intersession_briefing as ib


@pytest.fixture(scope='module')
def app_ctx():
    _app = create_app()
    _app.config.update({'TESTING': True, 'SQLALCHEMY_TRACK_MODIFICATIONS': False})
    with _app.app_context():
        yield _app


# =====================================================================
# 4.1 — stale_empresa + intelligence_report FORA do boot
# =====================================================================

class TestBriefingRelocacao:
    def test_stale_empresa_removido_do_modulo(self):
        """Bloco relocado para consulta on-demand (tela admin) — a funcao sai do
        modulo (regra dev: codigo substituido e removido; info re-derivavel via SQL)."""
        assert not hasattr(ib, '_check_stale_empresa_memories')

    def test_intelligence_report_removido_do_modulo(self):
        """PAD-CTX exclui intelligence_report do boot operacional (D7 segue
        acessivel via rota propria + tela admin)."""
        assert not hasattr(ib, '_check_intelligence_report')

    def test_briefing_nao_injeta_stale_nem_intelligence(self, app_ctx, monkeypatch):
        """Comportamental: mesmo com dados disponiveis, o briefing de boot nao
        carrega <stale_empresa> nem <intelligence_report>."""
        out = ib.build_intersession_briefing(user_id=999999) or ''
        assert '<stale_empresa' not in out
        assert '<intelligence_report' not in out


# =====================================================================
# 4.1 — improvement_responses: flag de INJECAO separada do DIALOGO
# =====================================================================

class TestImprovementInjectBootFlag:
    def _fake_responses_xml(self):
        return '<improvement_responses count="1">fake</improvement_responses>'

    def test_dialogo_on_inject_off_nao_injeta(self, app_ctx, monkeypatch):
        """AGENT_IMPROVEMENT_DIALOGUE governa o DIALOGO (D8); a INJECAO no boot
        tem controle proprio AGENT_IMPROVEMENT_INJECT_BOOT, default OFF."""
        monkeypatch.setenv('AGENT_IMPROVEMENT_DIALOGUE', 'true')
        monkeypatch.delenv('AGENT_IMPROVEMENT_INJECT_BOOT', raising=False)
        with patch.object(ib, '_check_improvement_responses',
                          return_value=self._fake_responses_xml()) as mock_check:
            out = ib.build_intersession_briefing(user_id=999999) or ''
        assert '<improvement_responses' not in out
        mock_check.assert_not_called()

    def test_dialogo_on_inject_on_injeta(self, app_ctx, monkeypatch):
        monkeypatch.setenv('AGENT_IMPROVEMENT_DIALOGUE', 'true')
        monkeypatch.setenv('AGENT_IMPROVEMENT_INJECT_BOOT', 'true')
        with patch.object(ib, '_check_improvement_responses',
                          return_value=self._fake_responses_xml()):
            out = ib.build_intersession_briefing(user_id=999999) or ''
        assert '<improvement_responses' in out


# =====================================================================
# 4.5 — Excecao condicional: skill_bug ATIVO no turno que usa a skill
# =====================================================================

@pytest.fixture
def dialogues(app_ctx):
    """Cria registros AgentImprovementDialogue de teste e limpa ao final."""
    from app.agente.models import AgentImprovementDialogue
    created = []

    def _mk(category, status, title, description, evidence=None, author='claude_code'):
        row = AgentImprovementDialogue(
            suggestion_key=f'TST-{uuid.uuid4().hex[:10]}',
            version=1,
            author=author,
            status=status,
            category=category,
            severity='info',
            title=title,
            description=description,
            evidence_json=evidence or {},
        )
        db.session.add(row)
        db.session.commit()
        created.append(row.id)
        return row

    yield _mk
    for rid in created:
        obj = db.session.get(AgentImprovementDialogue, rid)
        if obj:
            db.session.delete(obj)
    db.session.commit()


class TestSkillBugResponsesForSkill:
    def test_match_por_evidence_json_skill(self, app_ctx, dialogues):
        dialogues('skill_bug', 'responded', 'Bug no full.reconcile',
                  'Script trava no campo account.full.reconcile',
                  evidence={'skill': 'rastreando-odoo'})
        out = ib.get_skill_bug_responses_for_skill('rastreando-odoo')
        assert out and 'full.reconcile' in out

    def test_match_por_mencao_no_texto(self, app_ctx, dialogues):
        dialogues('skill_bug', 'responded', 'Fix na skill cotando-frete',
                  'Corrigido calculo de peso cubado na cotando-frete')
        out = ib.get_skill_bug_responses_for_skill('cotando-frete')
        assert out and 'peso cubado' in out

    def test_nao_retorna_proposed_nem_outra_categoria(self, app_ctx, dialogues):
        dialogues('skill_bug', 'proposed', 'Ainda sem resposta',
                  'Bug aberto na rastreando-odoo', evidence={'skill': 'rastreando-odoo'},
                  author='agent_sdk')
        dialogues('gotcha_report', 'responded', 'Gotcha generico',
                  'Mencao a rastreando-odoo mas nao e skill_bug')
        out = ib.get_skill_bug_responses_for_skill('rastreando-odoo')
        assert out is None or ('Ainda sem resposta' not in out
                               and 'Gotcha generico' not in out)

    def test_skill_sem_responses_retorna_none(self, app_ctx, dialogues):
        assert ib.get_skill_bug_responses_for_skill('skill-inexistente-xyz') is None


class TestPreToolSkillContext:
    """Wiring no PreToolUse (hooks.py): lembrete aprendido + skill_bug response
    compoem o contexto pre-execucao da Skill tool."""

    def test_compoe_reminder_e_skill_bug(self):
        from app.agente.sdk.hooks import _build_skill_pretool_context
        with patch('app.agente.sdk.memory_injection.get_skill_reminders_for_session',
                   return_value={'cotando-frete': 'lembre do peso cubado'}), \
             patch('app.agente.services.intersession_briefing.get_skill_bug_responses_for_skill',
                   return_value='<improvement_responses>fix aplicado</improvement_responses>'), \
             patch('app.agente.config.feature_flags.AGENT_SKILL_EVAL', True):
            out = _build_skill_pretool_context(user_id=5, skill='cotando-frete')
        assert out and 'peso cubado' in out
        assert 'fix aplicado' in out

    def test_skill_bug_independente_de_skill_eval(self):
        """A excecao 4.5 nao depende da flag AGENT_SKILL_EVAL (que gata so os
        lembretes aprendidos)."""
        from app.agente.sdk.hooks import _build_skill_pretool_context
        with patch('app.agente.sdk.memory_injection.get_skill_reminders_for_session',
                   return_value={}), \
             patch('app.agente.services.intersession_briefing.get_skill_bug_responses_for_skill',
                   return_value='<improvement_responses>fix aplicado</improvement_responses>'), \
             patch('app.agente.config.feature_flags.AGENT_SKILL_EVAL', False):
            out = _build_skill_pretool_context(user_id=5, skill='cotando-frete')
        assert out and 'fix aplicado' in out

    def test_sem_nada_retorna_none(self):
        from app.agente.sdk.hooks import _build_skill_pretool_context
        with patch('app.agente.sdk.memory_injection.get_skill_reminders_for_session',
                   return_value={}), \
             patch('app.agente.services.intersession_briefing.get_skill_bug_responses_for_skill',
                   return_value=None), \
             patch('app.agente.config.feature_flags.AGENT_SKILL_EVAL', True):
            out = _build_skill_pretool_context(user_id=5, skill='qualquer')
        assert out is None


# =====================================================================
# F5.7 PAD-CTX — Destilacao "top 3 erros recorrentes" no boot (gated >=30d)
# =====================================================================

@pytest.fixture
def skill_eff_rows(app_ctx):
    """Cria avaliacoes de efetividade de skill com datas controladas."""
    from app.agente.models import AgentSkillEffectiveness
    created = []

    def _mk(skill_name, resolveu, created_at, user_id=1):
        row = AgentSkillEffectiveness(
            user_id=user_id,
            session_id=f'tst-{uuid.uuid4().hex[:12]}',
            skill_name=skill_name,
            anchor_msg_id=uuid.uuid4().hex[:16],
            stage_reached=2,
            resolveu=resolveu,
            created_at=created_at,
        )
        db.session.add(row)
        db.session.commit()
        created.append(row.id)
        return row

    yield _mk
    for rid in created:
        obj = db.session.get(AgentSkillEffectiveness, rid)
        if obj:
            db.session.delete(obj)
    db.session.commit()


class TestRecurringErrorsGate:
    def test_gate_fechado_sem_30_dias_de_dados(self, app_ctx, skill_eff_rows):
        """Janela de dados < 30d -> bloco dormante (None), mesmo com falhas."""
        from datetime import timedelta
        from app.utils.timezone import agora_utc_naive
        recente = agora_utc_naive() - timedelta(days=5)
        skill_eff_rows('skill-x', False, recente)
        skill_eff_rows('skill-x', False, recente)
        assert ib._check_recurring_errors() is None

    def test_gate_aberto_destila_top3_recorrentes(self, app_ctx, skill_eff_rows):
        """>=30d de historico: top 3 skills por falhas (resolveu=false) nos
        ultimos 30d; falha unica (nao recorrente) NAO entra."""
        from datetime import timedelta
        from app.utils.timezone import agora_utc_naive
        now = agora_utc_naive()
        antigo = now - timedelta(days=40)   # abre o gate (janela >= 30d)
        recente = now - timedelta(days=3)

        skill_eff_rows('skill-old', True, antigo)
        # 3 falhas skill-a, 2 falhas skill-b, 1 falha skill-c (nao recorrente)
        for _ in range(3):
            skill_eff_rows('skill-a', False, recente)
        for _ in range(2):
            skill_eff_rows('skill-b', False, recente)
        skill_eff_rows('skill-c', False, recente)
        # resolvida nao conta como erro
        skill_eff_rows('skill-d', True, recente)

        out = ib._check_recurring_errors()
        assert out is not None
        assert '<erros_recorrentes' in out
        assert 'skill-a' in out and 'skill-b' in out
        assert 'skill-c' not in out
        assert 'skill-d' not in out
        # ordenacao: skill-a (3) antes de skill-b (2)
        assert out.index('skill-a') < out.index('skill-b')

    def test_briefing_integra_bloco_quando_disponivel(self, app_ctx, monkeypatch):
        fake = '<erros_recorrentes window="30d">fake</erros_recorrentes>'
        with patch.object(ib, '_check_recurring_errors', return_value=fake):
            out = ib.build_intersession_briefing(user_id=999999) or ''
        assert '<erros_recorrentes' in out

    def test_flag_off_nao_consulta(self, app_ctx, monkeypatch):
        monkeypatch.setenv('AGENT_RECURRING_ERRORS_BOOT', 'false')
        with patch.object(ib, '_check_recurring_errors') as mock_check:
            ib.build_intersession_briefing(user_id=999999)
        mock_check.assert_not_called()
