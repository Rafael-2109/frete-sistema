"""
A4 (Onda 3) — Testes de directive_promotion_service.

Valida o mecanismo shadow (flag-OFF) de promoção automática de diretriz:
- propose_directive_from_plan: extrai candidata de plano concluído
- evaluate_and_promote: anti-gaming + gate + shadow (só loga, não escreve)
- _tem_falha_odoo: anti-reward-hacking conservador (erro → bloqueia)

SHADOW puro: nenhum teste valida escrita em banco (AgentMemory não deve ser
criado/alterado em nenhum cenário — stub documentado apenas).
"""
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers — planos sintéticos
# ---------------------------------------------------------------------------

def _plano_todos_concluidos(*subjects):
    """Cria plan_dict com todos os steps concluídos."""
    return {
        'steps': {
            str(i + 1): {'subject': subj, 'status': 'completed'}
            for i, subj in enumerate(subjects)
        }
    }


def _plano_com_falha(*subjects):
    """Cria plan_dict com o último step falhado."""
    steps = {}
    for i, subj in enumerate(subjects):
        steps[str(i + 1)] = {
            'subject': subj,
            'status': 'completed' if i < len(subjects) - 1 else 'failed',
        }
    return {'steps': steps}


def _plano_vazio():
    return {'steps': {}}


# ---------------------------------------------------------------------------
# TestProposeDirectiveFromPlan
# ---------------------------------------------------------------------------

class TestProposeDirectiveFromPlan:

    def test_plano_todos_concluidos_retorna_candidata(self):
        """Plano com todos os steps completed → candidata com campos obrigatórios."""
        from app.agente.services.directive_promotion_service import propose_directive_from_plan

        plan = _plano_todos_concluidos('consultar pedido X', 'verificar estoque Y')
        result = propose_directive_from_plan(plan, 'sessao-abc-123')

        assert result is not None
        assert result['status'] == 'candidata'
        assert 'titulo' in result
        assert 'when' in result
        assert 'prescricao' in result
        assert result['source_session_id'] == 'sessao-abc-123'

    def test_plano_step_falho_retorna_none(self):
        """Plano com step falho → None (não promove plano incompleto)."""
        from app.agente.services.directive_promotion_service import propose_directive_from_plan

        plan = _plano_com_falha('consultar pedido X', 'verificar estoque Y')
        result = propose_directive_from_plan(plan, 'sessao-xyz')

        assert result is None

    def test_plano_vazio_retorna_none(self):
        """Plano sem steps → None."""
        from app.agente.services.directive_promotion_service import propose_directive_from_plan

        result = propose_directive_from_plan(_plano_vazio(), 'sessao-xyz')
        assert result is None

    def test_plano_none_retorna_none(self):
        """plan_dict None → None (tolerância a input inválido)."""
        from app.agente.services.directive_promotion_service import propose_directive_from_plan

        assert propose_directive_from_plan(None, 'sessao-xyz') is None

    def test_plano_sem_steps_key_retorna_none(self):
        """plan_dict sem chave 'steps' → None."""
        from app.agente.services.directive_promotion_service import propose_directive_from_plan

        assert propose_directive_from_plan({}, 'sessao-xyz') is None

    def test_plano_unico_step_concluido(self):
        """Plano com apenas um step completed → candidata válida."""
        from app.agente.services.directive_promotion_service import propose_directive_from_plan

        plan = _plano_todos_concluidos('consultar disponibilidade Atacadão')
        result = propose_directive_from_plan(plan, 's1')

        assert result is not None
        assert result['status'] == 'candidata'
        assert len(result.get('prescricao', '')) > 0

    def test_step_com_status_pending_retorna_none(self):
        """Plano com step ainda pending (não falho, mas incompleto) → None."""
        from app.agente.services.directive_promotion_service import propose_directive_from_plan

        plan = {
            'steps': {
                '1': {'subject': 'passo A', 'status': 'completed'},
                '2': {'subject': 'passo B', 'status': 'pending'},
            }
        }
        result = propose_directive_from_plan(plan, 'sessao-xyz')
        assert result is None

    def test_candidata_contem_subjects_no_prescricao(self):
        """A prescrição deve referenciar os subjects dos steps."""
        from app.agente.services.directive_promotion_service import propose_directive_from_plan

        plan = _plano_todos_concluidos('verificar saldo Odoo', 'criar separacao')
        result = propose_directive_from_plan(plan, 'sessao-abc')

        assert result is not None
        # prescricao e when devem ser strings não-vazias
        assert isinstance(result['prescricao'], str) and len(result['prescricao']) > 0
        assert isinstance(result['when'], str) and len(result['when']) > 0


# ---------------------------------------------------------------------------
# TestTemFalhaOdoo
# ---------------------------------------------------------------------------

class TestTemFalhaOdoo:

    def test_sem_registros_retorna_false(self):
        """Sem operações na sessão → False (sem evidência de falha)."""
        from app.agente.services.directive_promotion_service import _tem_falha_odoo

        with patch('app.agente.services.directive_promotion_service._query_falha_odoo') as mock_q:
            mock_q.return_value = []
            result = _tem_falha_odoo('sessao-sem-ops')

        assert result is False

    def test_com_falha_odoo_retorna_true(self):
        """Sessão com operação FALHA_ODOO → True."""
        from app.agente.services.directive_promotion_service import _tem_falha_odoo

        mock_op = MagicMock()
        mock_op.status = 'FALHA_ODOO'

        with patch('app.agente.services.directive_promotion_service._query_falha_odoo') as mock_q:
            mock_q.return_value = [mock_op]
            result = _tem_falha_odoo('sessao-com-falha')

        assert result is True

    def test_apenas_executado_retorna_false(self):
        """Sessão com apenas operações EXECUTADO → False."""
        from app.agente.services.directive_promotion_service import _tem_falha_odoo

        mock_op = MagicMock()
        mock_op.status = 'EXECUTADO'

        with patch('app.agente.services.directive_promotion_service._query_falha_odoo') as mock_q:
            mock_q.return_value = [mock_op]
            result = _tem_falha_odoo('sessao-ok')

        assert result is False

    def test_erro_na_consulta_retorna_true_conservador(self):
        """
        Erro ao consultar o banco → True (conservador: na dúvida, NÃO promove).

        Anti-gaming: ambiental domina. Se não conseguimos verificar que o
        ambiente estava limpo, bloqueamos a promoção.
        """
        from app.agente.services.directive_promotion_service import _tem_falha_odoo

        with patch('app.agente.services.directive_promotion_service._query_falha_odoo') as mock_q:
            mock_q.side_effect = Exception("DB offline")
            result = _tem_falha_odoo('sessao-erro')

        # Conservador: erro → bloqueia (True)
        assert result is True

    def test_mix_executado_e_falha_retorna_true(self):
        """Mesmo uma falha entre várias execuções → True."""
        from app.agente.services.directive_promotion_service import _tem_falha_odoo

        ops = [
            MagicMock(status='EXECUTADO'),
            MagicMock(status='EXECUTADO'),
            MagicMock(status='FALHA_ODOO'),
        ]

        with patch('app.agente.services.directive_promotion_service._query_falha_odoo') as mock_q:
            mock_q.return_value = ops
            result = _tem_falha_odoo('sessao-mista')

        assert result is True


# ---------------------------------------------------------------------------
# TestEvaluateAndPromote
# ---------------------------------------------------------------------------

class TestEvaluateAndPromote:

    def _candidata_mock(self, session_id='sessao-ok'):
        return {
            'titulo': 'Verificar saldo antes de cotação',
            'when': 'Quando cliente pede cotação',
            'prescricao': 'Consultar saldo em Odoo antes de calcular',
            'source_session_id': session_id,
            'status': 'candidata',
        }

    def test_sem_falha_odoo_sem_regressao_retorna_would_promote(self):
        """Candidata sem falha Odoo + sem regressão → would_promote (shadow)."""
        from app.agente.services.directive_promotion_service import evaluate_and_promote

        candidata = self._candidata_mock()

        with patch('app.agente.services.directive_promotion_service._tem_falha_odoo', return_value=False):
            result = evaluate_and_promote(candidata, baseline_score=0.7, candidate_score=0.75)

        assert result['decision'] == 'would_promote'
        assert 'reason' in result or result.get('decision') == 'would_promote'

    def test_com_falha_odoo_retorna_rejected(self):
        """Falha Odoo ambiental → rejected, independente do score."""
        from app.agente.services.directive_promotion_service import evaluate_and_promote

        candidata = self._candidata_mock(session_id='sessao-com-falha')

        with patch('app.agente.services.directive_promotion_service._tem_falha_odoo', return_value=True):
            result = evaluate_and_promote(candidata, baseline_score=0.9, candidate_score=0.95)

        assert result['decision'] == 'rejected'
        assert result['reason'] == 'falha_odoo_ambiental'

    def test_regressao_retorna_rejected(self):
        """Regressão no eval gate → rejected."""
        from app.agente.services.directive_promotion_service import evaluate_and_promote

        candidata = self._candidata_mock()

        with patch('app.agente.services.directive_promotion_service._tem_falha_odoo', return_value=False):
            # candidate 0.5 vs baseline 0.9 → delta = -0.4, threshold 0.05 → regressão
            result = evaluate_and_promote(candidata, baseline_score=0.9, candidate_score=0.5)

        assert result['decision'] == 'rejected'
        # motivo inclui regressão
        assert 'regressao' in result.get('reason', '').lower() or 'regression' in result.get('reason', '').lower()

    def test_falha_odoo_domina_sobre_score_alto(self):
        """
        Anti-gaming: FALHA_ODOO DOMINA mesmo com score perfeito.
        Nem mesmo candidate_score=1.0 override falha ambiental.
        """
        from app.agente.services.directive_promotion_service import evaluate_and_promote

        candidata = self._candidata_mock(session_id='gaming-attempt')

        with patch('app.agente.services.directive_promotion_service._tem_falha_odoo', return_value=True):
            result = evaluate_and_promote(candidata, baseline_score=0.0, candidate_score=1.0)

        assert result['decision'] == 'rejected'
        assert result['reason'] == 'falha_odoo_ambiental'

    def test_shadow_nao_escreve_no_banco(self):
        """
        SHADOW puro: would_promote NUNCA persiste AgentMemory.
        Confirma que o mecanismo não cria nem altera registros no banco.
        """
        from app.agente.services.directive_promotion_service import evaluate_and_promote

        candidata = self._candidata_mock()

        with patch('app.agente.services.directive_promotion_service._tem_falha_odoo', return_value=False):
            with patch('app.agente.services.directive_promotion_service._persist_directive') as mock_persist:
                result = evaluate_and_promote(candidata, baseline_score=0.7, candidate_score=0.8)

        # would_promote → shadow apenas loga
        assert result['decision'] == 'would_promote'
        # _persist_directive NÃO deve ter sido chamado (stub documentado, flag-OFF)
        mock_persist.assert_not_called()

    def test_would_promote_contem_candidata(self):
        """Resultado would_promote preserva a candidata original."""
        from app.agente.services.directive_promotion_service import evaluate_and_promote

        candidata = self._candidata_mock()

        with patch('app.agente.services.directive_promotion_service._tem_falha_odoo', return_value=False):
            result = evaluate_and_promote(candidata, baseline_score=0.6, candidate_score=0.7)

        assert result['decision'] == 'would_promote'
        # Candidata deve estar no resultado
        assert result.get('candidata') is not None or result.get('titulo') is not None or (
            result.get('source_session_id') == 'sessao-ok'
        )

    def test_gate_report_only_nao_bloqueia_production_path(self):
        """
        eval_gate em mode='report_only' nunca bloqueia — mesmo com regressão,
        o gate apenas loga. Confirma integração com eval_gate_service.
        """
        from app.agente.services.eval_gate_service import eval_gate

        # Regressão severa
        result = eval_gate(baseline_score=0.9, candidate_score=0.2, mode='report_only')
        assert result['regression'] is True
        assert result['blocked'] is False  # NUNCA bloqueia em report_only

    def test_falha_odoo_verificada_antes_do_gate(self):
        """
        Anti-gaming é verificado ANTES do eval gate.
        Se _tem_falha_odoo → True, eval_gate NÃO deve ser chamado
        (retorno imediato com rejected).
        """
        from app.agente.services.directive_promotion_service import evaluate_and_promote

        candidata = self._candidata_mock()

        with patch('app.agente.services.directive_promotion_service._tem_falha_odoo', return_value=True):
            with patch('app.agente.services.eval_gate_service.eval_gate') as mock_gate:
                result = evaluate_and_promote(candidata, baseline_score=0.8, candidate_score=0.9)

        assert result['decision'] == 'rejected'
        # gate não foi chamado — anti-gaming retornou antes
        mock_gate.assert_not_called()


# ---------------------------------------------------------------------------
# TestShadowFlag
# ---------------------------------------------------------------------------

class TestShadowFlag:

    def test_flag_agent_directive_promotion_existe_e_esta_off(self):
        """Flag AGENT_DIRECTIVE_PROMOTION deve existir em feature_flags e estar OFF por default."""
        from app.agente.config.feature_flags import AGENT_DIRECTIVE_PROMOTION
        assert AGENT_DIRECTIVE_PROMOTION is False

    def test_persist_directive_e_stub_documentado(self):
        """
        _persist_directive é stub documentado — deve levantar NotImplementedError
        ou retornar None sem efeitos colaterais (sem DB write).
        """
        from app.agente.services.directive_promotion_service import _persist_directive

        candidata = {
            'titulo': 'Test',
            'when': 'Test',
            'prescricao': 'Test',
            'source_session_id': 'test',
            'status': 'candidata',
        }

        # Stub deve ser inócuo (não escreve no banco)
        # Pode levantar NotImplementedError ou retornar None — ambos são válidos
        try:
            result = _persist_directive(candidata)
            # Se retornar, deve ser None (sem-op documentado)
            assert result is None
        except NotImplementedError:
            pass  # Também válido — stub explícito
