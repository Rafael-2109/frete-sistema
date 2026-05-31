"""
Onda 3 / A3 — Eval Runner + Gate D8 (report-only).

Testa `app/agente/services/eval_gate_service.py`:
- load_golden_dataset: parseia YAML real dos datasets, retorna lista de casos
- _judge_case: com judge_fn mockado (pass e fail) -> status correto
- run_evals: com invoke_fn + judge_fn mockados -> score agregado correto
- eval_gate: report-only nunca bloqueia (blocked=False mesmo com regressao)
- eval_gate enforce: bloqueia quando candidate < baseline - threshold

SEAM injetavel: invoke_fn e judge_fn sao parametros — testes NUNCA chamam API real.
"""
import os
import pathlib
import pytest


# ---------------------------------------------------------------------------
# Paths de datasets reais
# ---------------------------------------------------------------------------

_WORKTREE = pathlib.Path(__file__).parent.parent.parent.parent
_EVALS_DIR = _WORKTREE / ".claude" / "evals" / "subagents"


# ---------------------------------------------------------------------------
# Testes: load_golden_dataset
# ---------------------------------------------------------------------------

class TestLoadGoldenDataset:
    def test_parseia_dataset_analista_carteira(self):
        """Parseia YAML real do analista-carteira e retorna lista de casos."""
        from app.agente.services.eval_gate_service import load_golden_dataset
        dataset_path = _EVALS_DIR / "analista-carteira" / "dataset.yaml"
        cases = load_golden_dataset(str(dataset_path))
        assert isinstance(cases, list)
        assert len(cases) > 0

    def test_casos_tem_campos_obrigatorios(self):
        """Cada caso tem id, input e expected_behavior."""
        from app.agente.services.eval_gate_service import load_golden_dataset
        dataset_path = _EVALS_DIR / "analista-carteira" / "dataset.yaml"
        cases = load_golden_dataset(str(dataset_path))
        for case in cases:
            assert "id" in case, f"Caso sem 'id': {case}"
            assert "input" in case, f"Caso sem 'input': {case['id']}"
            assert "expected_behavior" in case, f"Caso sem 'expected_behavior': {case['id']}"

    def test_must_not_pode_estar_ausente(self):
        """must_not e' opcional — nao deve causar KeyError."""
        from app.agente.services.eval_gate_service import load_golden_dataset
        dataset_path = _EVALS_DIR / "analista-carteira" / "dataset.yaml"
        cases = load_golden_dataset(str(dataset_path))
        # Simplesmente nao deve explodir
        for case in cases:
            _ = case.get("must_not", [])

    def test_arquivo_ausente_retorna_lista_vazia(self):
        """Arquivo ausente -> [] (tolerante)."""
        from app.agente.services.eval_gate_service import load_golden_dataset
        cases = load_golden_dataset("/nao/existe/dataset.yaml")
        assert cases == []

    def test_parseia_todos_os_datasets(self):
        """Todos os 4 datasets existentes sao parseados sem erro."""
        from app.agente.services.eval_gate_service import load_golden_dataset
        dataset_names = [
            "analista-carteira",
            "auditor-financeiro",
            "controlador-custo-frete",
            "gestor-motos-assai",
        ]
        for name in dataset_names:
            path = _EVALS_DIR / name / "dataset.yaml"
            if path.exists():
                cases = load_golden_dataset(str(path))
                assert isinstance(cases, list), f"Falhou para {name}"
                assert len(cases) > 0, f"Dataset vazio para {name}"


# ---------------------------------------------------------------------------
# Testes: _judge_case
# ---------------------------------------------------------------------------

class TestJudgeCase:
    """_judge_case com judge_fn mockado (sem chamada real a API)."""

    def _make_case(self, case_id="test-01", extra_must_not=None):
        return {
            "id": case_id,
            "input": "Analise o pedido VCD001.",
            "expected_behavior": [
                "Identifica como P2/FOB",
                "Decisao: aguardar producao",
            ],
            "must_not": extra_must_not or [
                "Sugere envio parcial",
            ],
        }

    def test_judge_pass_quando_judge_fn_retorna_pass(self):
        """Quando judge_fn retorna 'pass', status deve ser 'pass'."""
        from app.agente.services.eval_gate_service import _judge_case

        def mock_judge_fn(prompt: str) -> str:
            return "pass"

        case = self._make_case()
        result = _judge_case(case, agent_output="O pedido eh FOB, aguardar producao.", judge_fn=mock_judge_fn)
        assert result["status"] == "pass"
        assert result["id"] == "test-01"

    def test_judge_fail_quando_judge_fn_retorna_fail(self):
        """Quando judge_fn retorna 'fail', status deve ser 'fail'."""
        from app.agente.services.eval_gate_service import _judge_case

        def mock_judge_fn(prompt: str) -> str:
            return "fail"

        case = self._make_case()
        result = _judge_case(case, agent_output="Pode enviar parcial.", judge_fn=mock_judge_fn)
        assert result["status"] == "fail"
        assert result["id"] == "test-01"

    def test_retorno_tem_campos_obrigatorios(self):
        """Resultado sempre tem id, status e evidence."""
        from app.agente.services.eval_gate_service import _judge_case

        def mock_judge_fn(prompt: str) -> str:
            return "pass"

        case = self._make_case("ev-01")
        result = _judge_case(case, agent_output="Resposta qualquer.", judge_fn=mock_judge_fn)
        assert "id" in result
        assert "status" in result
        assert "evidence" in result
        assert result["id"] == "ev-01"

    def test_judge_prompt_recebe_expected_behavior(self):
        """O prompt enviado ao judge_fn deve conter o expected_behavior."""
        from app.agente.services.eval_gate_service import _judge_case
        prompts_recebidos = []

        def capturing_judge(prompt: str) -> str:
            prompts_recebidos.append(prompt)
            return "pass"

        case = self._make_case()
        _judge_case(case, agent_output="Resposta.", judge_fn=capturing_judge)
        assert len(prompts_recebidos) == 1
        assert "Identifica como P2/FOB" in prompts_recebidos[0]

    def test_judge_prompt_recebe_must_not(self):
        """O prompt enviado ao judge_fn deve conter o must_not quando presente."""
        from app.agente.services.eval_gate_service import _judge_case
        prompts_recebidos = []

        def capturing_judge(prompt: str) -> str:
            prompts_recebidos.append(prompt)
            return "pass"

        case = self._make_case(extra_must_not=["Ignora regra FOB"])
        _judge_case(case, agent_output="Resposta.", judge_fn=capturing_judge)
        assert "Ignora regra FOB" in prompts_recebidos[0]

    def test_caso_sem_must_not_nao_explode(self):
        """Caso sem must_not deve funcionar normalmente."""
        from app.agente.services.eval_gate_service import _judge_case

        case = {
            "id": "no-must-not",
            "input": "Alguma pergunta.",
            "expected_behavior": ["Responde corretamente"],
            # sem must_not
        }

        def mock_judge(prompt: str) -> str:
            return "pass"

        result = _judge_case(case, agent_output="Responde.", judge_fn=mock_judge)
        assert result["status"] == "pass"


# ---------------------------------------------------------------------------
# Testes: run_evals
# ---------------------------------------------------------------------------

class TestRunEvals:
    """run_evals com invoke_fn e judge_fn mockados (zero API calls)."""

    def _make_dataset_path(self):
        return str(_EVALS_DIR / "analista-carteira" / "dataset.yaml")

    def test_score_todos_pass(self):
        """Todos os casos passando -> score = 1.0."""
        from app.agente.services.eval_gate_service import run_evals

        def invoke_fn(user_input: str) -> str:
            return "Resposta correta para todos os casos."

        def judge_fn(prompt: str) -> str:
            return "pass"

        result = run_evals(
            agent_name="analista-carteira",
            dataset_path=self._make_dataset_path(),
            invoke_fn=invoke_fn,
            judge_fn=judge_fn,
        )
        assert result["agent_name"] == "analista-carteira"
        assert result["score"] == 1.0
        assert result["passed"] == result["total"]
        assert result["total"] > 0

    def test_score_todos_fail(self):
        """Todos os casos falhando -> score = 0.0."""
        from app.agente.services.eval_gate_service import run_evals

        def invoke_fn(user_input: str) -> str:
            return "Resposta incorreta."

        def judge_fn(prompt: str) -> str:
            return "fail"

        result = run_evals(
            agent_name="analista-carteira",
            dataset_path=self._make_dataset_path(),
            invoke_fn=invoke_fn,
            judge_fn=judge_fn,
        )
        assert result["score"] == 0.0
        assert result["passed"] == 0

    def test_score_parcial_2_de_3(self):
        """2 de 3 casos passando -> score = 0.667 (aprox)."""
        from app.agente.services.eval_gate_service import run_evals, load_golden_dataset

        # Carrega 3 primeiros casos reais
        all_cases = load_golden_dataset(self._make_dataset_path())
        # Usa apenas os 3 primeiros para controle
        ids_pass = {all_cases[0]["id"], all_cases[1]["id"]}

        call_count = [0]

        def invoke_fn(user_input: str) -> str:
            call_count[0] += 1
            return f"Resposta para invocacao {call_count[0]}"

        judge_count = [0]

        def judge_fn(prompt: str) -> str:
            judge_count[0] += 1
            # Os 2 primeiros passam, o resto falha
            if judge_count[0] <= 2:
                return "pass"
            return "fail"

        # Carrega dataset completo mas usamos apenas 3
        import yaml as _yaml
        import pathlib as _pathlib
        import tempfile, os

        mini_dataset = all_cases[:3]
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        )
        _yaml.dump({"cases": mini_dataset}, tmp)
        tmp.close()

        try:
            result = run_evals(
                agent_name="test-agent",
                dataset_path=tmp.name,
                invoke_fn=invoke_fn,
                judge_fn=judge_fn,
            )
        finally:
            os.unlink(tmp.name)

        assert result["total"] == 3
        assert result["passed"] == 2
        assert abs(result["score"] - 2/3) < 0.01

    def test_resultado_tem_estrutura_correta(self):
        """Resultado de run_evals tem todos os campos esperados."""
        from app.agente.services.eval_gate_service import run_evals

        result = run_evals(
            agent_name="analista-carteira",
            dataset_path=self._make_dataset_path(),
            invoke_fn=lambda x: "Resposta.",
            judge_fn=lambda p: "pass",
        )
        assert "agent_name" in result
        assert "score" in result
        assert "total" in result
        assert "passed" in result
        assert "cases" in result
        assert isinstance(result["cases"], list)

    def test_invoke_fn_default_levanta_not_implemented(self):
        """Sem invoke_fn, deve levantar NotImplementedError (seam documentado)."""
        from app.agente.services.eval_gate_service import run_evals

        result = run_evals(
            agent_name="analista-carteira",
            dataset_path=self._make_dataset_path(),
            # invoke_fn ausente — usa default que raise NotImplementedError
            judge_fn=lambda p: "pass",
        )
        # best-effort: todos os casos devem registrar erro (status=error ou fail)
        # e score deve ser 0.0 (nenhum passou)
        assert result["score"] == 0.0
        for case_result in result["cases"]:
            assert case_result["status"] in ("fail", "error")

    def test_dataset_vazio_retorna_score_zero(self):
        """Dataset vazio -> score=0.0, total=0."""
        from app.agente.services.eval_gate_service import run_evals
        import tempfile, os, yaml as _yaml

        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        )
        _yaml.dump({"cases": []}, tmp)
        tmp.close()

        try:
            result = run_evals(
                agent_name="vazio",
                dataset_path=tmp.name,
                invoke_fn=lambda x: "ok",
                judge_fn=lambda p: "pass",
            )
        finally:
            os.unlink(tmp.name)

        assert result["total"] == 0
        assert result["score"] == 0.0

    def test_casos_sao_best_effort_invoke_error(self):
        """invoke_fn que explode nao deve interromper os demais casos."""
        from app.agente.services.eval_gate_service import run_evals

        call_count = [0]

        def invoke_fn_que_falha(user_input: str) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Falha simulada no invoke")
            return "Resposta normal."

        result = run_evals(
            agent_name="analista-carteira",
            dataset_path=self._make_dataset_path(),
            invoke_fn=invoke_fn_que_falha,
            judge_fn=lambda p: "pass",
        )
        # Nao deve propagar excecao — retorna resultado parcial
        assert result["total"] > 0
        # O primeiro caso deve ter status 'error' (invoke falhou)
        assert result["cases"][0]["status"] == "error"


# ---------------------------------------------------------------------------
# Testes: eval_gate
# ---------------------------------------------------------------------------

class TestEvalGate:
    """eval_gate: report_only nunca bloqueia; enforce bloqueia em regressao."""

    def test_report_only_nunca_bloqueia_sem_regressao(self):
        """mode=report_only: blocked=False mesmo sem regressao."""
        from app.agente.services.eval_gate_service import eval_gate
        result = eval_gate(baseline_score=0.9, candidate_score=0.95, mode="report_only")
        assert result["blocked"] is False
        assert result["regression"] is False

    def test_report_only_nunca_bloqueia_com_regressao(self):
        """mode=report_only: blocked=False MESMO com regressao grave (invariante central)."""
        from app.agente.services.eval_gate_service import eval_gate
        result = eval_gate(baseline_score=0.9, candidate_score=0.5, mode="report_only")
        assert result["blocked"] is False
        assert result["regression"] is True  # detecta, mas NAO bloqueia

    def test_report_only_detecta_delta(self):
        """mode=report_only retorna delta correto."""
        from app.agente.services.eval_gate_service import eval_gate
        result = eval_gate(baseline_score=0.8, candidate_score=0.6, mode="report_only")
        assert abs(result["delta"] - (0.6 - 0.8)) < 0.001

    def test_enforce_bloqueia_em_regressao(self):
        """mode=enforce: blocked=True quando candidate < baseline - threshold."""
        from app.agente.services.eval_gate_service import eval_gate
        result = eval_gate(
            baseline_score=0.9,
            candidate_score=0.8,  # delta = -0.1, threshold default = 0.05
            threshold=0.05,
            mode="enforce",
        )
        assert result["blocked"] is True
        assert result["regression"] is True

    def test_enforce_nao_bloqueia_dentro_threshold(self):
        """mode=enforce: blocked=False quando candidate >= baseline - threshold."""
        from app.agente.services.eval_gate_service import eval_gate
        result = eval_gate(
            baseline_score=0.9,
            candidate_score=0.87,  # delta = -0.03, threshold = 0.05 -> OK
            threshold=0.05,
            mode="enforce",
        )
        assert result["blocked"] is False

    def test_enforce_nao_bloqueia_melhoria(self):
        """mode=enforce: blocked=False quando candidate > baseline."""
        from app.agente.services.eval_gate_service import eval_gate
        result = eval_gate(
            baseline_score=0.8,
            candidate_score=0.95,
            mode="enforce",
        )
        assert result["blocked"] is False
        assert result["regression"] is False

    def test_threshold_customizado(self):
        """threshold customizado e' respeitado."""
        from app.agente.services.eval_gate_service import eval_gate
        # Com threshold=0.20, delta de -0.10 nao e' regressao
        result = eval_gate(
            baseline_score=0.9,
            candidate_score=0.8,
            threshold=0.20,
            mode="enforce",
        )
        assert result["blocked"] is False
        assert result["regression"] is False

    def test_resultado_tem_campos_obrigatorios(self):
        """Resultado de eval_gate tem regression, blocked e delta."""
        from app.agente.services.eval_gate_service import eval_gate
        result = eval_gate(baseline_score=0.8, candidate_score=0.7)
        assert "regression" in result
        assert "blocked" in result
        assert "delta" in result

    def test_default_mode_e_report_only(self):
        """Sem mode explicito, default e report_only (blocked sempre False)."""
        from app.agente.services.eval_gate_service import eval_gate
        # Regressao grave sem mode explicito
        result = eval_gate(baseline_score=1.0, candidate_score=0.0)
        assert result["blocked"] is False
