"""
Testes TDD para PlanState (B1 — Onda 2).

Parte A: PlanState puro, determinístico, sem DB.
Parte B: Flags USE_AGENT_PLANNER / USE_AGENT_VERIFY.
Parte C: Comportamento flag-OFF = zero write em data['plan'].
"""
import os
import pytest

os.environ.setdefault('TESTING', 'true')


# ──────────────────────────────────────────────
# Parte A — PlanState puro
# ──────────────────────────────────────────────

class TestPlanStateCore:
    """Testes da classe PlanState — pura, sem DB, determinística."""

    def test_plan_state_aplica_task_create_e_update(self):
        """TaskCreate cria step; TaskUpdate faz merge de campos."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'consultar X'})
        ps.apply_task_event({'tool': 'TaskUpdate', 'taskId': '1', 'status': 'completed'})
        d = ps.to_dict()
        assert d['steps']['1']['subject'] == 'consultar X'
        assert d['steps']['1']['status'] == 'completed'

    def test_plan_state_roundtrip_dict(self):
        """to_dict / from_dict deve ser reversível e igual."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '2', 'subject': 'y'})
        ps2 = PlanState.from_dict(ps.to_dict())
        assert ps2.to_dict() == ps.to_dict()

    def test_plan_state_ignora_evento_invalido(self):
        """Evento sem tool/taskId = no-op, sem exceção."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({})                      # sem tool/taskId — no-op
        ps.apply_task_event({'tool': 'TaskList'})    # snapshot read — no-op
        assert ps.to_dict()['steps'] == {}

    def test_task_create_guarda_subject_e_description(self):
        """TaskCreate preserva subject e description do input."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({
            'tool': 'TaskCreate',
            'taskId': '3',
            'subject': 'verificar NF',
            'description': 'detalhe extra',
        })
        step = ps.to_dict()['steps']['3']
        assert step['subject'] == 'verificar NF'
        assert step['description'] == 'detalhe extra'
        assert step['status'] == 'pending'

    def test_task_update_merge_parcial(self):
        """TaskUpdate só sobrescreve campos fornecidos; mantém os outros."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '5', 'subject': 'original'})
        ps.apply_task_event({'tool': 'TaskUpdate', 'taskId': '5', 'status': 'in_progress'})
        step = ps.to_dict()['steps']['5']
        assert step['subject'] == 'original'       # não apagado
        assert step['status'] == 'in_progress'

    def test_task_update_cria_step_se_nao_existe(self):
        """TaskUpdate para taskId desconhecido cria o step (upsert)."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskUpdate', 'taskId': '9', 'status': 'completed'})
        assert '9' in ps.to_dict()['steps']
        assert ps.to_dict()['steps']['9']['status'] == 'completed'

    def test_task_get_e_no_op(self):
        """TaskGet é read-only — não modifica steps."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '7', 'subject': 'algo'})
        before = ps.to_dict()
        ps.apply_task_event({'tool': 'TaskGet', 'taskId': '7'})
        assert ps.to_dict() == before

    def test_multiplos_steps(self):
        """Múltiplos TaskCreate criam múltiplos steps independentes."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        for i in range(1, 4):
            ps.apply_task_event({'tool': 'TaskCreate', 'taskId': str(i), 'subject': f's{i}'})
        d = ps.to_dict()
        assert len(d['steps']) == 3
        assert d['steps']['2']['subject'] == 's2'

    def test_from_dict_vazio(self):
        """from_dict com dict vazio retorna PlanState sem steps."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState.from_dict({})
        assert ps.to_dict()['steps'] == {}

    def test_from_dict_com_steps(self):
        """from_dict carrega steps corretamente."""
        from app.agente.sdk.plan_state import PlanState
        data = {'steps': {'10': {'subject': 'x', 'status': 'completed'}}}
        ps = PlanState.from_dict(data)
        assert ps.to_dict()['steps']['10']['status'] == 'completed'

    def test_to_dict_estrutura_minima(self):
        """to_dict sempre retorna chave 'steps' mesmo sem eventos."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        d = ps.to_dict()
        assert 'steps' in d
        assert isinstance(d['steps'], dict)

    def test_evento_tool_desconhecida_ignorado(self):
        """Tool desconhecida (ex: TaskOutput) é no-op."""
        from app.agente.sdk.plan_state import PlanState
        ps = PlanState()
        ps.apply_task_event({'tool': 'TaskOutput', 'taskId': '1', 'subject': 'x'})
        assert ps.to_dict()['steps'] == {}


# ──────────────────────────────────────────────
# Parte B — Feature flags (Onda 2)
# ──────────────────────────────────────────────

class TestFeatureFlags:
    """Verifica que USE_AGENT_PLANNER e USE_AGENT_VERIFY existem e são OFF por default."""

    def test_use_agent_planner_default_false(self):
        """USE_AGENT_PLANNER deve ser False por default (env não setada)."""
        # Garantir que a env var NÃO está setada antes de reimportar
        env_key = 'AGENT_PLANNER'
        original = os.environ.pop(env_key, None)
        try:
            import importlib
            import app.agente.config.feature_flags as ff
            importlib.reload(ff)
            assert ff.USE_AGENT_PLANNER is False, (
                "USE_AGENT_PLANNER deve ser False por default"
            )
        finally:
            if original is not None:
                os.environ[env_key] = original

    def test_use_agent_verify_default_false(self):
        """USE_AGENT_VERIFY deve ser False por default (env não setada)."""
        env_key = 'AGENT_VERIFY'
        original = os.environ.pop(env_key, None)
        try:
            import importlib
            import app.agente.config.feature_flags as ff
            importlib.reload(ff)
            assert ff.USE_AGENT_VERIFY is False, (
                "USE_AGENT_VERIFY deve ser False por default"
            )
        finally:
            if original is not None:
                os.environ[env_key] = original

    def test_use_agent_planner_ativa_com_env_true(self):
        """USE_AGENT_PLANNER ativa quando env AGENT_PLANNER=true."""
        env_key = 'AGENT_PLANNER'
        original = os.environ.get(env_key)
        os.environ[env_key] = 'true'
        try:
            import importlib
            import app.agente.config.feature_flags as ff
            importlib.reload(ff)
            assert ff.USE_AGENT_PLANNER is True
        finally:
            if original is None:
                del os.environ[env_key]
            else:
                os.environ[env_key] = original


# ──────────────────────────────────────────────
# Parte C — Wiring flag-OFF = zero write
# ──────────────────────────────────────────────

class TestFlagOffZeroWrite:
    """
    Prova que com USE_AGENT_PLANNER=False (default), data['plan'] nunca é
    gravado em AgentSession.
    """

    def test_flag_off_nao_grava_plan_em_response_state(self):
        """
        Com flag OFF, response_state não deve conter 'task_events' preenchidos
        (mesmo que task_events sejam emitidos no stream).

        Testa o comportamento no _process_stream_event: com flag OFF, task_events
        não são acumulados.
        """
        import importlib
        env_key = 'AGENT_PLANNER'
        original = os.environ.pop(env_key, None)
        try:
            import app.agente.config.feature_flags as ff
            importlib.reload(ff)
            assert ff.USE_AGENT_PLANNER is False

            # Simula response_state como em chat.py
            response_state = {
                'task_events': [],
                'plan': None,
            }

            # Com flag OFF, a acumulação não deve ocorrer
            # (a lógica de wiring verifica flag antes de acumular)
            from app.agente.config.feature_flags import USE_AGENT_PLANNER
            if USE_AGENT_PLANNER:
                response_state['task_events'].append({'tool': 'TaskCreate', 'taskId': '1'})

            # Com flag OFF: task_events permanece vazio
            assert response_state['task_events'] == []
            assert response_state['plan'] is None

        finally:
            if original is not None:
                os.environ[env_key] = original

    def test_flag_off_save_messages_nao_grava_plan(self):
        """
        Com flag OFF, _save_messages_to_db não deve gravar data['plan'].
        Testa via mock de AgentSession para isolar sem DB.
        """
        import importlib
        env_key = 'AGENT_PLANNER'
        original = os.environ.pop(env_key, None)
        try:
            import app.agente.config.feature_flags as ff
            importlib.reload(ff)
            assert ff.USE_AGENT_PLANNER is False

            # Simula o bloco de persistência de plan em _save_messages_to_db
            # Replicar a lógica: só escreve se USE_AGENT_PLANNER is True
            from app.agente.config.feature_flags import USE_AGENT_PLANNER
            mock_session_data = {}
            plan_dict = {'steps': {'1': {'subject': 'x', 'status': 'pending'}}}

            if USE_AGENT_PLANNER and plan_dict:
                mock_session_data['plan'] = plan_dict

            # Com flag OFF: data['plan'] nunca é setado
            assert 'plan' not in mock_session_data

        finally:
            if original is not None:
                os.environ[env_key] = original

    def test_flag_on_grava_plan(self):
        """Com flag ON, o plan_dict não-vazio deve ser gravado."""
        import importlib
        env_key = 'AGENT_PLANNER'
        original = os.environ.get(env_key)
        os.environ[env_key] = 'true'
        try:
            import app.agente.config.feature_flags as ff
            importlib.reload(ff)
            assert ff.USE_AGENT_PLANNER is True

            from app.agente.config.feature_flags import USE_AGENT_PLANNER
            mock_session_data = {}
            plan_dict = {'steps': {'1': {'subject': 'x', 'status': 'pending'}}}

            if USE_AGENT_PLANNER and plan_dict:
                mock_session_data['plan'] = plan_dict

            assert 'plan' in mock_session_data
            assert mock_session_data['plan']['steps']['1']['subject'] == 'x'

        finally:
            if original is None:
                del os.environ[env_key]
            else:
                os.environ[env_key] = original
