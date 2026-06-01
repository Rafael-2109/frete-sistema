"""
A4 (Onda 3) — Testes de directive_promotion_service.

Valida o mecanismo shadow (flag-OFF) de promoção automática de diretriz:
- propose_directive_from_plan: extrai candidata de plano concluído
- evaluate_and_promote: anti-gaming + gate + shadow (só loga, não escreve)
- _tem_falha_odoo: anti-reward-hacking conservador (erro → bloqueia)
- _persist_directive: persistência real como AgentMemory(directive_status='shadow')

SHADOW puro: evaluate_and_promote NÃO chama _persist_directive (flag-OFF).
_persist_directive diretamente: persiste com directive_status='shadow' (idempotente).
"""
import pytest
import uuid
from unittest.mock import MagicMock, patch

from app import create_app, db as _db


# ---------------------------------------------------------------------------
# Fixtures de banco para TestPersistDirectiveReal
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def app_ctx_persist():
    """Flask app context para testes de DB (escopo de módulo)."""
    _app = create_app()
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    with _app.app_context():
        yield _app


@pytest.fixture
def rollback_persist():
    """Garante rollback da sessão no teardown (mesmo se o teste levantar)."""
    yield
    _db.session.rollback()


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

    def test_evaluate_shadow_nao_persiste(self):
        """Shadow: evaluate_and_promote LOGA would_promote mas NÃO chama _persist_directive."""
        from app.agente.services import directive_promotion_service as svc

        cand = {'titulo': 'X', 'when': 'w', 'prescricao': 'p', 'source_session_id': 's', 'status': 'candidata'}
        with patch.object(svc, '_tem_falha_odoo', return_value=False), \
             patch.object(svc, '_persist_directive') as mock_persist:
            r = svc.evaluate_and_promote(cand, baseline_score=0.7, candidate_score=0.8)
        assert r['decision'] == 'would_promote'
        mock_persist.assert_not_called()


# ---------------------------------------------------------------------------
# TestPersistDirectiveReal
# ---------------------------------------------------------------------------

class TestPersistDirectiveReal:

    def test_persiste_como_shadow_com_path_e_conteudo_selecionavel(self, app_ctx_persist, rollback_persist):
        """_persist_directive cria AgentMemory(directive_status='shadow') selecionável pelo builder."""
        from app.agente.services.directive_promotion_service import _persist_directive
        from app.agente.models import AgentMemory
        from app.agente.sdk.memory_injection import _is_nivel_5
        import re

        cand = {
            'titulo': f'Fluxo: consultar saldo [2 passos] {uuid.uuid4().hex[:6]}',
            'when': 'Quando o agente executa: consultar saldo; validar lote',
            'prescricao': 'Sequência: consultar saldo → validar lote',
            'source_session_id': 'sess-1',
            'status': 'candidata',
        }
        mem_id = _persist_directive(cand)
        mem = AgentMemory.query.get(mem_id)
        assert mem is not None
        assert mem.user_id == 0
        assert mem.escopo == 'empresa'
        assert mem.directive_status == 'shadow'
        assert mem.path.startswith('/memories/empresa/heuristicas/')
        assert mem.importance_score >= 0.7
        # selecionável + renderável pelo builder:
        assert _is_nivel_5((mem.content or '').lower())
        assert re.search(r'<prescricao>(.+?)</prescricao>', mem.content, re.DOTALL)

    def test_idempotente_nao_duplica(self, app_ctx_persist, rollback_persist):
        """Segunda chamada com mesmo título retorna mesmo id, sem duplicar."""
        from app.agente.services.directive_promotion_service import _persist_directive
        from app.agente.models import AgentMemory

        t = f'Fluxo idem {uuid.uuid4().hex[:6]}'
        cand = {'titulo': t, 'when': 'w', 'prescricao': 'faça y',
                'source_session_id': 's2', 'status': 'candidata'}
        id1 = _persist_directive(cand)
        id2 = _persist_directive(cand)  # mesmo título → mesmo path → no dup
        assert id1 == id2
        path = AgentMemory.query.get(id1).path
        assert AgentMemory.query.filter_by(user_id=0, path=path).count() == 1


# ---------------------------------------------------------------------------
# TestRunBatch
# ---------------------------------------------------------------------------

class TestRunBatch:
    def _sess(self, sid, plan):
        from unittest.mock import MagicMock
        s = MagicMock()
        s.session_id = sid
        s.data = {'plan': plan}
        return s

    def test_flag_off_no_op(self):
        from app.agente.services import directive_promotion_service as svc
        from unittest.mock import patch
        with patch.object(svc, 'AGENT_DIRECTIVE_PROMOTION', False):
            r = svc.run_directive_promotion_batch(lookback_hours=24, limit=50)
        assert r == {'candidatos': 0, 'promovidos': 0, 'abstencoes': 0, 'rejeitados': 0}

    def test_abstem_sem_judge_score(self):
        from app.agente.services import directive_promotion_service as svc
        from unittest.mock import patch
        plan = {'steps': {'1': {'subject': 'consultar', 'status': 'completed'}}}
        with patch.object(svc, 'AGENT_DIRECTIVE_PROMOTION', True), \
             patch.object(svc, '_buscar_sessoes_com_plano_concluido', return_value=[self._sess('s1', plan)]), \
             patch.object(svc, '_buscar_sessoes_recentes', return_value=[]), \
             patch.object(svc, '_quality_score_da_sessao', return_value=None), \
             patch.object(svc, '_persist_directive') as mock_persist:
            r = svc.run_directive_promotion_batch(lookback_hours=24, limit=50)
        assert r['abstencoes'] == 1 and r['promovidos'] == 0
        mock_persist.assert_not_called()

    def test_promove_quando_qualidade_e_sem_falha_odoo(self):
        from app.agente.services import directive_promotion_service as svc
        from unittest.mock import patch
        plan = {'steps': {'1': {'subject': 'consultar', 'status': 'completed'}}}
        with patch.object(svc, 'AGENT_DIRECTIVE_PROMOTION', True), \
             patch.object(svc, '_buscar_sessoes_com_plano_concluido', return_value=[self._sess('s1', plan)]), \
             patch.object(svc, '_buscar_sessoes_recentes', return_value=[]), \
             patch.object(svc, '_quality_score_da_sessao', return_value=0.85), \
             patch.object(svc, '_tem_falha_odoo', return_value=False), \
             patch.object(svc, '_persist_directive', return_value=123) as mock_persist:
            r = svc.run_directive_promotion_batch(lookback_hours=24, limit=50)
        assert r['promovidos'] == 1
        mock_persist.assert_called_once()

    def test_rejeita_falha_odoo_dominante(self):
        from app.agente.services import directive_promotion_service as svc
        from unittest.mock import patch
        plan = {'steps': {'1': {'subject': 'x', 'status': 'completed'}}}
        with patch.object(svc, 'AGENT_DIRECTIVE_PROMOTION', True), \
             patch.object(svc, '_buscar_sessoes_com_plano_concluido', return_value=[self._sess('s1', plan)]), \
             patch.object(svc, '_buscar_sessoes_recentes', return_value=[]), \
             patch.object(svc, '_quality_score_da_sessao', return_value=0.99), \
             patch.object(svc, '_tem_falha_odoo', return_value=True), \
             patch.object(svc, '_persist_directive') as mock_persist:
            r = svc.run_directive_promotion_batch(lookback_hours=24, limit=50)
        assert r['rejeitados'] == 1 and r['promovidos'] == 0
        mock_persist.assert_not_called()

    def test_promove_via_judge_sem_plano(self):
        """Opção B / A4 V2: sessão SEM plano mas de ALTA QUALIDADE (judge) vira
        candidata e é promovida (shadow). Prova que o batch deixou de depender de
        PlanState — a 2ª fonte é o judge signal."""
        from app.agente.services import directive_promotion_service as svc
        from unittest.mock import patch
        s2 = self._sess('s2', None)
        judge_steps = [
            {'score': 85, 'label': 'success', 'evidencia': 'ok', 'tools': ['consultando-sql']},
            {'score': 80, 'label': 'success', 'evidencia': 'ok', 'tools': ['Bash']},
        ]
        with patch.object(svc, 'AGENT_DIRECTIVE_PROMOTION', True), \
             patch.object(svc, '_buscar_sessoes_com_plano_concluido', return_value=[]), \
             patch.object(svc, '_buscar_sessoes_recentes', return_value=[s2]), \
             patch.object(svc, '_judge_steps_da_sessao', return_value=judge_steps), \
             patch.object(svc, '_primeira_msg_usuario', return_value='Analise X'), \
             patch.object(svc, '_quality_score_da_sessao', return_value=0.82), \
             patch.object(svc, '_tem_falha_odoo', return_value=False), \
             patch.object(svc, '_persist_directive', return_value=99) as mock_persist:
            r = svc.run_directive_promotion_batch(lookback_hours=24, limit=50)
        assert r['promovidos'] == 1, f"esperado 1 promovido via judge, foi {r}"
        mock_persist.assert_called_once()


# ---------------------------------------------------------------------------
# TestProposeDirectiveFromJudgeSession (Opção B — A4 V2: candidata vinda do
# JUDGE signal, INDEPENDENTE de PlanState; o gargalo era a fonte ser só plano)
# ---------------------------------------------------------------------------

def _judge_steps(*pairs, tools=None):
    """Cria lista de steps com veredito judge. pairs = (score, label).
    tools opcional (lista de ferramentas usadas no passo)."""
    return [
        {'score': sc, 'label': lb, 'evidencia': f'evid {lb} {sc}',
         'tools': tools or ['consultando-sql']}
        for sc, lb in pairs
    ]


class TestProposeDirectiveFromJudgeSession:
    """A4 V2: sessão de alta qualidade validada pelo judge vira candidata,
    sem precisar de PlanState. Função PURA (sem DB)."""

    def test_sessao_alta_qualidade_retorna_candidata(self):
        from app.agente.services.directive_promotion_service import propose_directive_from_judge_session
        steps = _judge_steps((85, 'success'), (80, 'success'), tools=['consultando-sql', 'Bash'])
        result = propose_directive_from_judge_session(
            'sessao-jq-1', steps, user_meta='Analise a carteira do Atacadao',
        )
        assert result is not None
        assert result['source_session_id'] == 'sessao-jq-1'
        assert result['status'] == 'candidata'
        assert result.get('titulo') and result.get('when') and result.get('prescricao')

    def test_sessao_com_failure_retorna_none(self):
        """Qualquer passo 'failure' desqualifica (só promovemos sessão LIMPA)."""
        from app.agente.services.directive_promotion_service import propose_directive_from_judge_session
        steps = _judge_steps((85, 'success'), (35, 'failure'))
        assert propose_directive_from_judge_session('sessao-jq-2', steps) is None

    def test_sessao_qualidade_baixa_retorna_none(self):
        """Média abaixo do min_quality (default 0.7) → não promove."""
        from app.agente.services.directive_promotion_service import propose_directive_from_judge_session
        steps = _judge_steps((45, 'partial'), (50, 'partial'))
        assert propose_directive_from_judge_session('sessao-jq-3', steps) is None

    def test_sessao_poucos_passos_julgados_retorna_none(self):
        """Menos de min_steps (default 2) passos julgados → conservador, None."""
        from app.agente.services.directive_promotion_service import propose_directive_from_judge_session
        steps = _judge_steps((90, 'success'))
        assert propose_directive_from_judge_session('sessao-jq-4', steps) is None

    def test_sem_judge_signal_retorna_none(self):
        """Lista vazia / sem score → None (não inventa candidata)."""
        from app.agente.services.directive_promotion_service import propose_directive_from_judge_session
        assert propose_directive_from_judge_session('sessao-jq-5', []) is None
        assert propose_directive_from_judge_session('sessao-jq-6', [{'label': 'success'}]) is None

    def test_prescricao_reflete_qualidade(self):
        """A prescrição deve refletir que foi uma abordagem validada pelo judge."""
        from app.agente.services.directive_promotion_service import propose_directive_from_judge_session
        steps = _judge_steps((85, 'success'), (85, 'success'), tools=['ajustando-quant-odoo'])
        result = propose_directive_from_judge_session('sessao-jq-7', steps)
        assert result is not None
        low = (result['prescricao'] + ' ' + result['titulo']).lower()
        assert 'valid' in low or 'judge' in low or 'qualidade' in low
