"""
A3 Fase 1, sub-task 3b — testes de build_subprocess_invoke_fn.

Wira a invocacao REAL do agente (`claude -p --agent ...`) como invoke_fn do
eval gate. Os testes NUNCA chamam o CLI real: `subprocess.run` e' mockado.

Cobertura:
- closure retorna stdout.strip() em rc=0
- comando contem `--agent <nome>` + `--permission-mode bypassPermissions` + `-p`
- model opcional adiciona `--model <model>` so' quando passado
- rc != 0 -> RuntimeError com stderr truncado
- TimeoutExpired -> propaga (vira caso 'error' no run_evals)
- as 2 excecoes acima viram caso 'error' per-caso em run_evals (sem interromper)

SEAM: build_subprocess_invoke_fn produz a closure que e' passada como invoke_fn.
"""
import subprocess
from unittest.mock import patch, MagicMock

import pytest


class TestBuildSubprocessInvokeFn:
    def test_retorna_stdout_strip_em_rc0(self):
        from app.agente.services.eval_gate_service import build_subprocess_invoke_fn

        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='  resposta do agente  \n', stderr=''
        )
        with patch('subprocess.run', return_value=fake) as m_run:
            invoke = build_subprocess_invoke_fn('analista-carteira')
            out = invoke('qual o saldo do pedido X?')

        assert out == 'resposta do agente'
        assert m_run.call_count == 1

    def test_comando_contem_agent_e_bypass(self):
        from app.agente.services.eval_gate_service import build_subprocess_invoke_fn

        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout='ok', stderr='')
        with patch('subprocess.run', return_value=fake) as m_run:
            invoke = build_subprocess_invoke_fn('auditor-financeiro')
            invoke('input qualquer')

        cmd = m_run.call_args.args[0]
        assert cmd[0] == 'claude'
        assert '-p' in cmd
        assert '--agent' in cmd
        assert cmd[cmd.index('--agent') + 1] == 'auditor-financeiro'
        assert '--permission-mode' in cmd
        assert cmd[cmd.index('--permission-mode') + 1] == 'bypassPermissions'
        # user_input vai como ultimo argumento
        assert cmd[-1] == 'input qualquer'

    def test_model_ausente_nao_adiciona_flag(self):
        from app.agente.services.eval_gate_service import build_subprocess_invoke_fn

        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout='ok', stderr='')
        with patch('subprocess.run', return_value=fake) as m_run:
            invoke = build_subprocess_invoke_fn('analista-carteira')  # model=None default
            invoke('x')

        cmd = m_run.call_args.args[0]
        assert '--model' not in cmd

    def test_model_presente_adiciona_flag(self):
        from app.agente.services.eval_gate_service import build_subprocess_invoke_fn

        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout='ok', stderr='')
        with patch('subprocess.run', return_value=fake) as m_run:
            invoke = build_subprocess_invoke_fn('analista-carteira', model='claude-opus-4-8')
            invoke('x')

        cmd = m_run.call_args.args[0]
        assert '--model' in cmd
        assert cmd[cmd.index('--model') + 1] == 'claude-opus-4-8'

    def test_passa_timeout_e_capture(self):
        from app.agente.services.eval_gate_service import build_subprocess_invoke_fn

        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout='ok', stderr='')
        with patch('subprocess.run', return_value=fake) as m_run:
            invoke = build_subprocess_invoke_fn('analista-carteira', timeout=99)
            invoke('x')

        kwargs = m_run.call_args.kwargs
        assert kwargs.get('timeout') == 99
        assert kwargs.get('capture_output') is True
        assert kwargs.get('text') is True

    def test_rc_diferente_de_zero_levanta_runtimeerror(self):
        from app.agente.services.eval_gate_service import build_subprocess_invoke_fn

        fake = subprocess.CompletedProcess(
            args=[], returncode=2, stdout='', stderr='boom detalhado do CLI'
        )
        with patch('subprocess.run', return_value=fake):
            invoke = build_subprocess_invoke_fn('analista-carteira')
            with pytest.raises(RuntimeError) as exc:
                invoke('x')

        assert 'rc=2' in str(exc.value)
        assert 'boom detalhado do CLI' in str(exc.value)

    def test_timeout_expired_propaga(self):
        from app.agente.services.eval_gate_service import build_subprocess_invoke_fn

        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='claude', timeout=120)):
            invoke = build_subprocess_invoke_fn('analista-carteira', timeout=120)
            with pytest.raises(subprocess.TimeoutExpired):
                invoke('x')

    def test_excecoes_viram_caso_error_em_run_evals(self, tmp_path):
        """As excecoes da closure (RuntimeError, TimeoutExpired) viram caso
        'error' per-caso em run_evals SEM interromper os demais."""
        from app.agente.services.eval_gate_service import build_subprocess_invoke_fn, run_evals

        ds = tmp_path / "dataset.yaml"
        ds.write_text(
            "cases:\n"
            "  - id: c1\n"
            "    input: pergunta 1\n"
            "    expected_behavior: [resposta]\n"
            "  - id: c2\n"
            "    input: pergunta 2\n"
            "    expected_behavior: [resposta]\n",
            encoding='utf-8',
        )

        # 1o caso: rc!=0 -> RuntimeError; 2o caso: rc=0 -> ok (julgado pass)
        fakes = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout='', stderr='falha'),
            subprocess.CompletedProcess(args=[], returncode=0, stdout='resposta boa', stderr=''),
        ]
        with patch('subprocess.run', side_effect=fakes):
            invoke = build_subprocess_invoke_fn('analista-carteira')
            # n_runs=1: este teste valida o contrato "invoke sempre falha -> status
            # 'error'" (1 fake por caso). Com o default n_runs=3 (A3-R1) seriam 3
            # invokes/caso = 6 fakes; aqui a intencao e' o comportamento single-run
            # do erro de invoke, nao a agregacao N-runs (coberta em TestRunEvalsNRuns).
            result = run_evals(
                agent_name='analista-carteira',
                dataset_path=str(ds),
                invoke_fn=invoke,
                judge_fn=lambda p: 'pass',
                n_runs=1,
            )

        assert result['total'] == 2
        # 1o caso = error (invoke falhou), 2o caso = pass (nao interrompido)
        statuses = {c['id']: c['status'] for c in result['cases']}
        assert statuses['c1'] == 'error'
        assert statuses['c2'] == 'pass'
