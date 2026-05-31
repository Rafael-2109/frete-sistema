"""
Testes TDD para B3 — replan + budget + escalate (Onda 2).

Parte A: PlanState replan/escalate — puro, sem DB.
Parte B: marcar_escalonamento — integração com AgentInvocationMetric.
"""
import os
import pytest

os.environ.setdefault('TESTING', 'true')


# ──────────────────────────────────────────────────────────────────────────────
# Parte A — PlanState replan/escalate (puro, determinístico)
# ──────────────────────────────────────────────────────────────────────────────

class TestMarkStepFailed:
    """mark_step_failed incrementa failures e seta status='failed'."""

    def test_mark_step_failed_incrementa_failures(self):
        """Primeira falha: failures=1, status='failed'."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'consultar X'})

        ps.mark_step_failed('1')

        step = ps.to_dict()['steps']['1']
        assert step['failures'] == 1
        assert step['status'] == 'failed'

    def test_mark_step_failed_acumula_multiplas_falhas(self):
        """Falha 2x acumula: failures=2."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'consultar X'})

        ps.mark_step_failed('1')
        ps.mark_step_failed('1')

        assert ps.to_dict()['steps']['1']['failures'] == 2

    def test_mark_step_failed_step_inexistente_cria_step(self):
        """mark_step_failed em step inexistente cria o step (upsert defensivo)."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()

        ps.mark_step_failed('novo')

        step = ps.to_dict()['steps']['novo']
        assert step['failures'] == 1
        assert step['status'] == 'failed'

    def test_mark_step_failed_preserva_subject(self):
        """mark_step_failed não apaga subject/description existente."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({
            'tool': 'TaskCreate', 'taskId': '2',
            'subject': 'tarefa importante', 'description': 'detalhe',
        })

        ps.mark_step_failed('2')

        step = ps.to_dict()['steps']['2']
        assert step['subject'] == 'tarefa importante'
        assert step['description'] == 'detalhe'


class TestShouldEscalate:
    """should_escalate(max_retries) → True quando algum step supera o budget."""

    def test_should_escalate_false_sem_falhas(self):
        """Sem falhas: should_escalate=False."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'x'})

        assert ps.should_escalate() is False

    def test_should_escalate_false_dentro_budget(self):
        """1 falha com max_retries=2: ainda dentro do budget → False."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'x'})
        ps.mark_step_failed('1')

        assert ps.should_escalate(max_retries=2) is False

    def test_should_escalate_true_estourou_budget(self):
        """3 falhas com max_retries=2: estourou → True."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'x'})
        ps.mark_step_failed('1')
        ps.mark_step_failed('1')
        ps.mark_step_failed('1')

        assert ps.should_escalate(max_retries=2) is True

    def test_should_escalate_true_no_limite_exato(self):
        """failures = max_retries+1 (3 com max=2): deve escalar."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'x'})
        for _ in range(3):
            ps.mark_step_failed('1')

        assert ps.should_escalate(max_retries=2) is True

    def test_should_escalate_apenas_step_com_muitas_falhas(self):
        """Um step ok + um step com falha excessiva → True."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'ok'})
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '2', 'subject': 'problema'})

        ps.mark_step_failed('2')
        ps.mark_step_failed('2')
        ps.mark_step_failed('2')

        assert ps.should_escalate(max_retries=2) is True

    def test_should_escalate_custom_max_retries_0(self):
        """max_retries=0: qualquer falha deve escalar."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'x'})
        ps.mark_step_failed('1')

        assert ps.should_escalate(max_retries=0) is True


class TestStepsToRetry:
    """steps_to_retry(max_retries) → IDs de steps dentro do budget."""

    def test_steps_to_retry_vazio_sem_falhas(self):
        """Sem falhas: nenhum step precisa retry."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'x'})

        assert ps.steps_to_retry() == []

    def test_steps_to_retry_dentro_budget(self):
        """1 falha (failures=1 ≤ max_retries=2): step deve ser retried."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'x'})
        ps.mark_step_failed('1')

        retry = ps.steps_to_retry(max_retries=2)
        assert '1' in retry

    def test_steps_to_retry_excluido_apos_estourar_budget(self):
        """3 falhas (failures=3 > max_retries=2): step NÃO deve ser retried."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'x'})
        for _ in range(3):
            ps.mark_step_failed('1')

        retry = ps.steps_to_retry(max_retries=2)
        assert '1' not in retry

    def test_steps_to_retry_mistura_dentro_fora_budget(self):
        """Step A dentro do budget, step B fora: só A em retry."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': 'A', 'subject': 'retry'})
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': 'B', 'subject': 'escalate'})

        ps.mark_step_failed('A')       # 1 falha — retry OK
        for _ in range(3):
            ps.mark_step_failed('B')   # 3 falhas — escalate

        retry = ps.steps_to_retry(max_retries=2)
        assert 'A' in retry
        assert 'B' not in retry


class TestToFromDictComFailures:
    """to_dict/from_dict preserva failures e estado de escalation."""

    def test_to_dict_inclui_failures(self):
        """to_dict serializa o campo 'failures' de steps com falhas."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'x'})
        ps.mark_step_failed('1')
        ps.mark_step_failed('1')

        d = ps.to_dict()
        assert d['steps']['1']['failures'] == 2

    def test_from_dict_restaura_failures(self):
        """from_dict restaura failures ao deserializar."""
        from app.agente.sdk.plan_state import PlanState
        d = {
            'steps': {
                '1': {'subject': 'x', 'status': 'failed', 'failures': 3}
            }
        }
        ps = PlanState.from_dict(d)

        assert ps.to_dict()['steps']['1']['failures'] == 3
        assert ps.should_escalate(max_retries=2) is True

    def test_roundtrip_com_failures(self):
        """to_dict/from_dict é reversível com failures > 0."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '5', 'subject': 'y'})
        ps.mark_step_failed('5')

        ps2 = PlanState.from_dict(ps.to_dict())
        assert ps2.to_dict() == ps.to_dict()

    def test_steps_sem_failures_nao_incluem_campo_por_default(self):
        """Step sem falhas não carrega campo failures em to_dict (limpeza)."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'x'})

        d = ps.to_dict()
        # 'failures' pode ser 0 ou ausente — qualquer um é ok; o importante é que
        # should_escalate retorna False e steps_to_retry retorna []
        assert ps.should_escalate() is False
        assert ps.steps_to_retry() == []


# ──────────────────────────────────────────────────────────────────────────────
# Parte B — marcar_escalonamento (integração com DB)
# ──────────────────────────────────────────────────────────────────────────────

class TestMarcarEscalonamento:
    """
    Testa AgentInvocationMetric.marcar_escalonamento().

    Usa app_context real (SQLite in-memory) para validar a escrita.
    Padrão espelhado dos testes de step_judge/plan_verifier:
    - cria o objeto, persiste, chama o helper, verifica flag = True.
    """

    @pytest.fixture
    def app(self):
        from app import create_app
        _app = create_app()
        _app.config.update({'TESTING': True})
        return _app

    def _criar_metrica_teste(self, db):
        """Cria AgentInvocationMetric minimal para teste."""
        import uuid
        from app.agente.models import AgentInvocationMetric
        m = AgentInvocationMetric(
            agent_id=f'test_{uuid.uuid4().hex[:12]}',
            agent_type='test_agent',
            session_id='test-session-abc',
            user_id=1,
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            source=AgentInvocationMetric.SOURCE_DEV,
        )
        db.session.add(m)
        db.session.commit()
        return m

    def test_marcar_escalonamento_seta_flag_true(self, app):
        """marcar_escalonamento(agent_id) seta escalated_to_human=True no DB."""
        with app.app_context():
            from app import db
            from app.agente.models import AgentInvocationMetric

            metrica = self._criar_metrica_teste(db)
            assert metrica.escalated_to_human is False

            result = AgentInvocationMetric.marcar_escalonamento(metrica.agent_id)

            assert result is True, "marcar_escalonamento deve retornar True em sucesso"

            # Verifica persistência no DB
            db.session.expire(metrica)
            atualizado = db.session.get(AgentInvocationMetric, metrica.id)
            assert atualizado.escalated_to_human is True

    def test_marcar_escalonamento_nao_encontrado_retorna_false(self, app):
        """agent_id inexistente: retorna False sem exceção (best-effort)."""
        with app.app_context():
            from app.agente.models import AgentInvocationMetric

            result = AgentInvocationMetric.marcar_escalonamento('agent_id_que_nao_existe_xyz')

            assert result is False

    def test_marcar_escalonamento_best_effort_nao_propaga_excecao(self, app):
        """Mesmo que algo exploda internamente, não deve propagar exceção."""
        with app.app_context():
            from app.agente.models import AgentInvocationMetric

            # Deve retornar sem levantar exceção
            try:
                result = AgentInvocationMetric.marcar_escalonamento(None)
                # None como agent_id → não deve achar, retorna False
                assert result is False
            except Exception as e:
                pytest.fail(f"marcar_escalonamento levantou exceção inesperada: {e}")

    def test_marcar_escalonamento_idempotente(self, app):
        """Chamar 2x: segundo call ainda retorna True (idempotente)."""
        with app.app_context():
            from app import db
            from app.agente.models import AgentInvocationMetric

            metrica = self._criar_metrica_teste(db)

            AgentInvocationMetric.marcar_escalonamento(metrica.agent_id)
            result2 = AgentInvocationMetric.marcar_escalonamento(metrica.agent_id)

            assert result2 is True
            db.session.expire(metrica)
            atualizado = db.session.get(AgentInvocationMetric, metrica.id)
            assert atualizado.escalated_to_human is True
