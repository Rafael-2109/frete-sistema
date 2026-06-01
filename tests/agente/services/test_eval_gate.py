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
                n_runs=1,  # judge_fn stateful (conta chamadas) -> preserva intencao single-run
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
            n_runs=1,  # invoke_fn stateful (1a chamada explode) -> single-run preserva intencao
        )
        # Nao deve propagar excecao — retorna resultado parcial
        assert result["total"] > 0
        # O primeiro caso deve ter status 'error' (invoke falhou)
        assert result["cases"][0]["status"] == "error"


# ---------------------------------------------------------------------------
# Testes: BUG-1 — judge GRANULAR (score parcial por item)
# ---------------------------------------------------------------------------

class TestJudgeCaseGranular:
    """_judge_case com judge_fn granular (retorna dict {passed_items, total_items, failing})."""

    def _make_case(self, case_id="ac-03"):
        return {
            "id": case_id,
            "input": "Analise o pedido VCD001.",
            "expected_behavior": [
                "Identifica como P2/FOB",
                "Decisao: aguardar producao",
                "Menciona estoque",
                "Cita prazo",
                "Sem envio parcial",
            ],
            "must_not": ["Sugere envio parcial"],
        }

    def test_granular_4_de_5_status_pass(self):
        """judge_fn dict {4/5} -> case_score 0.8 -> status 'pass' (>= PASS_THRESHOLD)."""
        from app.agente.services.eval_gate_service import _judge_case

        def mock_judge_fn(prompt: str) -> dict:
            return {"passed_items": 4, "total_items": 5, "failing": ["Cita prazo"]}

        result = _judge_case(self._make_case(), agent_output="Resposta.", judge_fn=mock_judge_fn)
        assert abs(result["case_score"] - 0.8) < 1e-9
        assert result["status"] == "pass"
        assert result["id"] == "ac-03"

    def test_granular_2_de_5_status_fail(self):
        """judge_fn dict {2/5} -> case_score 0.4 -> status 'fail' (< PASS_THRESHOLD)."""
        from app.agente.services.eval_gate_service import _judge_case

        def mock_judge_fn(prompt: str) -> dict:
            return {"passed_items": 2, "total_items": 5, "failing": ["a", "b", "c"]}

        result = _judge_case(self._make_case(), agent_output="Resposta.", judge_fn=mock_judge_fn)
        assert abs(result["case_score"] - 0.4) < 1e-9
        assert result["status"] == "fail"

    def test_granular_total_items_zero_sem_excecao(self):
        """total_items=0 -> case_score 0.0 (sem ZeroDivisionError) -> status 'fail'."""
        from app.agente.services.eval_gate_service import _judge_case

        def mock_judge_fn(prompt: str) -> dict:
            return {"passed_items": 0, "total_items": 0, "failing": ["parse_error"]}

        result = _judge_case(self._make_case(), agent_output="Resposta.", judge_fn=mock_judge_fn)
        assert result["case_score"] == 0.0
        assert result["status"] == "fail"

    def test_granular_passed_maior_que_total_capa_em_1(self):
        """HIGH-1: Haiku miscount (passed > total) -> case_score capado em 1.0.

        Sem o cap, case_score viraria >1.0 e envenenaria o baseline (gate
        nunca dispararia regressao). Blinda contra LLM que conta errado.
        """
        from app.agente.services.eval_gate_service import _judge_case

        def mock_judge_fn(prompt: str) -> dict:
            return {"passed_items": 6, "total_items": 5, "failing": []}

        result = _judge_case(self._make_case(), agent_output="Resposta.", judge_fn=mock_judge_fn)
        assert result["case_score"] == 1.0  # capado, NUNCA 1.2
        assert result["status"] == "pass"

    def test_granular_threshold_exato_passa(self):
        """case_score == PASS_THRESHOLD (0.80) -> status 'pass' (limite inclusivo)."""
        from app.agente.services.eval_gate_service import _judge_case

        def mock_judge_fn(prompt: str) -> dict:
            return {"passed_items": 8, "total_items": 10, "failing": ["x", "y"]}

        result = _judge_case(self._make_case(), agent_output="Resposta.", judge_fn=mock_judge_fn)
        assert abs(result["case_score"] - 0.80) < 1e-9
        assert result["status"] == "pass"

    def test_granular_evidence_legivel(self):
        """evidence granular resume passed/total e itens faltantes."""
        from app.agente.services.eval_gate_service import _judge_case

        def mock_judge_fn(prompt: str) -> dict:
            return {"passed_items": 4, "total_items": 5, "failing": ["Cita prazo"]}

        result = _judge_case(self._make_case(), agent_output="Resposta.", judge_fn=mock_judge_fn)
        assert "4/5" in result["evidence"]
        assert "Cita prazo" in result["evidence"]


class TestJudgeCaseRetrocompat:
    """_judge_case mantem retrocompat com judge_fn que retorna str 'pass'/'fail'."""

    def _make_case(self):
        return {
            "id": "rc-01",
            "input": "x",
            "expected_behavior": ["a"],
            "must_not": [],
        }

    def test_retrocompat_str_pass_score_1(self):
        """str 'pass' -> case_score 1.0, status 'pass'."""
        from app.agente.services.eval_gate_service import _judge_case
        result = _judge_case(self._make_case(), agent_output="ok", judge_fn=lambda p: "pass")
        assert result["case_score"] == 1.0
        assert result["status"] == "pass"

    def test_retrocompat_str_fail_score_0(self):
        """str 'fail' -> case_score 0.0, status 'fail'."""
        from app.agente.services.eval_gate_service import _judge_case
        result = _judge_case(self._make_case(), agent_output="ok", judge_fn=lambda p: "fail")
        assert result["case_score"] == 0.0
        assert result["status"] == "fail"

    def test_retrocompat_str_qualquer_outro_score_0(self):
        """str que nao e 'pass' -> case_score 0.0, status 'fail'."""
        from app.agente.services.eval_gate_service import _judge_case
        result = _judge_case(self._make_case(), agent_output="ok", judge_fn=lambda p: "lixo")
        assert result["case_score"] == 0.0
        assert result["status"] == "fail"


class TestRunEvalsGranular:
    """run_evals com judge_fn granular -> score agregado = media dos case_scores."""

    def _two_case_dataset_path(self):
        import tempfile, yaml as _yaml
        cases = [
            {"id": "g1", "input": "a", "expected_behavior": ["x", "y", "z", "w", "v"]},
            {"id": "g2", "input": "b", "expected_behavior": ["x", "y", "z", "w", "v"]},
        ]
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        _yaml.dump({"cases": cases}, tmp)
        tmp.close()
        return tmp.name

    def test_run_evals_media_0_8_e_0_4(self):
        """2 casos (0.8 e 0.4) -> score agregado == 0.6 (media), passed==1."""
        from app.agente.services.eval_gate_service import run_evals
        import os

        path = self._two_case_dataset_path()
        judge_calls = [0]

        def judge_fn(prompt: str) -> dict:
            judge_calls[0] += 1
            if judge_calls[0] == 1:
                return {"passed_items": 4, "total_items": 5, "failing": ["x"]}
            return {"passed_items": 2, "total_items": 5, "failing": ["a", "b", "c"]}

        try:
            result = run_evals(
                agent_name="g",
                dataset_path=path,
                invoke_fn=lambda x: "out",
                judge_fn=judge_fn,
                n_runs=1,  # judge_fn stateful (conta chamadas) -> single-run preserva intencao
            )
        finally:
            os.unlink(path)

        assert result["total"] == 2
        assert abs(result["score"] - 0.6) < 1e-9  # media (0.8 + 0.4) / 2
        assert result["passed"] == 1  # apenas g1 (0.8) >= 0.80
        scores = sorted(c["case_score"] for c in result["cases"])
        assert abs(scores[0] - 0.4) < 1e-9
        assert abs(scores[1] - 0.8) < 1e-9

    def test_run_evals_case_score_em_cada_caso(self):
        """Cada item de cases[] ganha o campo case_score."""
        from app.agente.services.eval_gate_service import run_evals
        import os

        path = self._two_case_dataset_path()
        try:
            result = run_evals(
                agent_name="g",
                dataset_path=path,
                invoke_fn=lambda x: "out",
                judge_fn=lambda p: {"passed_items": 5, "total_items": 5, "failing": []},
            )
        finally:
            os.unlink(path)

        for c in result["cases"]:
            assert "case_score" in c
            assert c["case_score"] == 1.0

    def test_run_evals_invoke_error_case_score_zero_conta_media(self):
        """Caso com status 'error' (invoke falhou) -> case_score 0.0 e conta na media."""
        from app.agente.services.eval_gate_service import run_evals
        import os

        path = self._two_case_dataset_path()
        call = [0]

        def invoke_que_falha(x):
            call[0] += 1
            if call[0] == 1:
                raise RuntimeError("boom")
            return "out"

        try:
            result = run_evals(
                agent_name="g",
                dataset_path=path,
                invoke_fn=invoke_que_falha,
                judge_fn=lambda p: {"passed_items": 5, "total_items": 5, "failing": []},
                n_runs=1,  # invoke_fn stateful (1a chamada explode) -> single-run preserva intencao
            )
        finally:
            os.unlink(path)

        assert result["total"] == 2
        # 1 erro (0.0) + 1 perfeito (1.0) -> media 0.5
        assert abs(result["score"] - 0.5) < 1e-9
        err_case = [c for c in result["cases"] if c["status"] == "error"][0]
        assert err_case["case_score"] == 0.0


class TestCallHaikuEvalGranular:
    """_call_haiku_eval_granular: parse tolerante + best-effort em falha."""

    def test_parse_json_com_prefixo_sufixo(self, monkeypatch):
        """Parse tolerante a prefixo/sufixo (find('{')/rfind('}'))."""
        from app.agente.services import eval_gate_service as svc

        class _Block:
            type = "text"
            text = 'Aqui esta: {"passed_items": 3, "total_items": 5, "failing": ["a", "b"]} fim'

        class _Resp:
            content = [_Block()]

        class _Messages:
            def create(self, **kwargs):
                return _Resp()

        class _Client:
            messages = _Messages()

        monkeypatch.setattr(svc.anthropic, "Anthropic", lambda *a, **k: _Client())
        out = svc._call_haiku_eval_granular("prompt")
        assert out == {"passed_items": 3, "total_items": 5, "failing": ["a", "b"]}

    def test_parse_invalido_retorna_best_effort(self, monkeypatch):
        """JSON invalido/ausente -> {passed_items:0, total_items:0, failing:['parse_error']}."""
        from app.agente.services import eval_gate_service as svc

        class _Block:
            type = "text"
            text = "isso nao e json nenhum"

        class _Resp:
            content = [_Block()]

        class _Messages:
            def create(self, **kwargs):
                return _Resp()

        class _Client:
            messages = _Messages()

        monkeypatch.setattr(svc.anthropic, "Anthropic", lambda *a, **k: _Client())
        out = svc._call_haiku_eval_granular("prompt")
        assert out == {"passed_items": 0, "total_items": 0, "failing": ["parse_error"]}


class TestRunEvalsDefaultJudgeGranular:
    """run_evals default judge_fn agora e _call_haiku_eval_granular (BUG-1)."""

    def test_default_judge_fn_e_granular(self):
        from app.agente.services import eval_gate_service as svc
        import inspect

        sig = inspect.signature(svc.run_evals)
        # judge_fn continua Optional com default None (resolvido internamente)
        assert sig.parameters["judge_fn"].default is None

    def test_default_judge_resolvido_para_granular(self, monkeypatch):
        """Sem judge_fn explicito, run_evals usa _call_haiku_eval_granular."""
        from app.agente.services import eval_gate_service as svc
        import os, tempfile, yaml as _yaml

        capturado = []

        def fake_granular(prompt: str) -> dict:
            capturado.append(prompt)
            return {"passed_items": 5, "total_items": 5, "failing": []}

        monkeypatch.setattr(svc, "_call_haiku_eval_granular", fake_granular)

        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        _yaml.dump({"cases": [{"id": "d1", "input": "a", "expected_behavior": ["x"]}]}, tmp)
        tmp.close()

        try:
            result = svc.run_evals(
                agent_name="d",
                dataset_path=tmp.name,
                invoke_fn=lambda x: "out",
                n_runs=1,  # conta chamadas do judge (capturado) -> single-run preserva intencao
                # judge_fn ausente -> deve usar _call_haiku_eval_granular
            )
        finally:
            os.unlink(tmp.name)

        assert len(capturado) == 1  # granular foi chamado
        assert result["score"] == 1.0


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


# ---------------------------------------------------------------------------
# Testes: A3-R1 — N-RUNS (dominar nao-determinismo do LLM via mediana)
# ---------------------------------------------------------------------------

class TestRunEvalsNRuns:
    """run_evals com n_runs > 1: roda invoke+judge N vezes por caso,
    agrega via MEDIANA (comportamento predominante da spec) e reporta variance.

    Spec: .claude/evals/subagents/run_eval.md:121 — "Rodar 3x e considerar o
    comportamento predominante."
    """

    def _single_case_dataset_path(self):
        """1 caso com 5 expected_behavior (permite scores granulares 0.0..1.0)."""
        import tempfile, yaml as _yaml
        cases = [
            {"id": "n1", "input": "a", "expected_behavior": ["x", "y", "z", "w", "v"]},
        ]
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        _yaml.dump({"cases": cases}, tmp)
        tmp.close()
        return tmp.name

    def test_n_runs_3_outputs_diferentes_judge_deterministico_por_output(self):
        """invoke_fn stateful (outputs diferentes a cada chamada) + judge_fn
        deterministico-por-output -> mediana correta dos 3 case_scores.

        Outputs mapeiam para scores [0.2, 0.6, 1.0] -> mediana = 0.6.
        """
        from app.agente.services.eval_gate_service import run_evals
        import os

        path = self._single_case_dataset_path()

        # invoke retorna 'out0','out1','out2' a cada chamada (stateful via pop)
        retornos = ["out0", "out1", "out2"]
        idx = [0]

        def invoke_fn(user_input: str) -> str:
            r = retornos[idx[0]]
            idx[0] += 1
            return r

        # judge deterministico POR OUTPUT (encontra no prompt qual out apareceu)
        score_por_output = {
            "out0": {"passed_items": 1, "total_items": 5, "failing": ["a"]},  # 0.2
            "out1": {"passed_items": 3, "total_items": 5, "failing": ["b"]},  # 0.6
            "out2": {"passed_items": 5, "total_items": 5, "failing": []},     # 1.0
        }

        def judge_fn(prompt: str) -> dict:
            for out, verdict in score_por_output.items():
                if out in prompt:
                    return verdict
            return {"passed_items": 0, "total_items": 5, "failing": ["nao_achou"]}

        try:
            result = run_evals(
                agent_name="n",
                dataset_path=path,
                invoke_fn=invoke_fn,
                judge_fn=judge_fn,
                n_runs=3,
            )
        finally:
            os.unlink(path)

        caso = result["cases"][0]
        # runs_scores = [0.2, 0.6, 1.0] -> mediana 0.6
        assert sorted(caso["runs_scores"]) == [0.2, 0.6, 1.0]
        assert abs(caso["case_score"] - 0.6) < 1e-9
        assert caso["n_runs"] == 3
        # invoke chamado exatamente 3x
        assert idx[0] == 3

    def test_mediana_robusta_a_outlier(self):
        """3 runs com case_scores [1.0, 0.0, 1.0] -> mediana 1.0 (NAO media 0.667)."""
        from app.agente.services.eval_gate_service import run_evals
        import os

        path = self._single_case_dataset_path()

        # judge alterna: run1=1.0, run2=0.0, run3=1.0
        verdicts = [
            {"passed_items": 5, "total_items": 5, "failing": []},        # 1.0
            {"passed_items": 0, "total_items": 5, "failing": ["a"]},     # 0.0
            {"passed_items": 5, "total_items": 5, "failing": []},        # 1.0
        ]
        jidx = [0]

        def judge_fn(prompt: str) -> dict:
            v = verdicts[jidx[0]]
            jidx[0] += 1
            return v

        try:
            result = run_evals(
                agent_name="n",
                dataset_path=path,
                invoke_fn=lambda x: "out",
                judge_fn=judge_fn,
                n_runs=3,
            )
        finally:
            os.unlink(path)

        caso = result["cases"][0]
        assert sorted(caso["runs_scores"]) == [0.0, 1.0, 1.0]
        # MEDIANA = 1.0 (elemento do meio apos ordenar), NAO media (0.667)
        assert caso["case_score"] == 1.0
        # mediana >= PASS_THRESHOLD -> status pass
        assert caso["status"] == "pass"

    def test_variance_reportada_flaky(self):
        """runs [1.0, 0.0, 1.0] -> pvariance > 0 (sinal de flaky)."""
        from app.agente.services.eval_gate_service import run_evals
        import os

        path = self._single_case_dataset_path()
        verdicts = [
            {"passed_items": 5, "total_items": 5, "failing": []},
            {"passed_items": 0, "total_items": 5, "failing": ["a"]},
            {"passed_items": 5, "total_items": 5, "failing": []},
        ]
        jidx = [0]

        def judge_fn(prompt: str) -> dict:
            v = verdicts[jidx[0]]
            jidx[0] += 1
            return v

        try:
            result = run_evals(
                agent_name="n",
                dataset_path=path,
                invoke_fn=lambda x: "out",
                judge_fn=judge_fn,
                n_runs=3,
            )
        finally:
            os.unlink(path)

        caso = result["cases"][0]
        assert caso["case_score_variance"] > 0.0

    def test_variance_zero_quando_estavel(self):
        """runs [1.0, 1.0, 1.0] -> variance == 0 (estavel/nao-flaky)."""
        from app.agente.services.eval_gate_service import run_evals
        import os

        path = self._single_case_dataset_path()
        try:
            result = run_evals(
                agent_name="n",
                dataset_path=path,
                invoke_fn=lambda x: "out",
                judge_fn=lambda p: {"passed_items": 5, "total_items": 5, "failing": []},
                n_runs=3,
            )
        finally:
            os.unlink(path)

        caso = result["cases"][0]
        assert caso["runs_scores"] == [1.0, 1.0, 1.0]
        assert caso["case_score_variance"] == 0.0
        assert caso["case_score"] == 1.0

    def test_n_runs_1_reproduz_single_run(self):
        """n_runs=1 -> mediana de 1 elemento = ele mesmo, variance 0.

        Reproduz EXATAMENTE o comportamento single-run legado.
        """
        from app.agente.services.eval_gate_service import run_evals
        import os

        path = self._single_case_dataset_path()
        try:
            result = run_evals(
                agent_name="n",
                dataset_path=path,
                invoke_fn=lambda x: "out",
                judge_fn=lambda p: {"passed_items": 3, "total_items": 5, "failing": ["a"]},
                n_runs=1,
            )
        finally:
            os.unlink(path)

        caso = result["cases"][0]
        assert caso["runs_scores"] == [0.6]
        assert abs(caso["case_score"] - 0.6) < 1e-9
        assert caso["case_score_variance"] == 0.0
        assert caso["n_runs"] == 1
        # 0.6 < PASS_THRESHOLD (0.80) -> fail
        assert caso["status"] == "fail"
        assert abs(result["score"] - 0.6) < 1e-9

    def test_best_effort_por_run_um_run_falha_outros_valem(self):
        """invoke_fn falha em 1 dos 3 runs -> esse run conta 0.0, os outros 2 valem.

        runs_scores = [0.0 (run que falhou), 1.0, 1.0] -> mediana 1.0.
        """
        from app.agente.services.eval_gate_service import run_evals
        import os

        path = self._single_case_dataset_path()
        call = [0]

        def invoke_fn(user_input: str) -> str:
            call[0] += 1
            if call[0] == 2:  # segundo run do unico caso explode
                raise RuntimeError("boom no run 2")
            return "out"

        try:
            result = run_evals(
                agent_name="n",
                dataset_path=path,
                invoke_fn=invoke_fn,
                judge_fn=lambda p: {"passed_items": 5, "total_items": 5, "failing": []},
                n_runs=3,
            )
        finally:
            os.unlink(path)

        caso = result["cases"][0]
        # 3 runs: run1=1.0, run2=0.0 (invoke falhou), run3=1.0
        assert sorted(caso["runs_scores"]) == [0.0, 1.0, 1.0]
        # mediana robusta ao run ruim -> 1.0
        assert caso["case_score"] == 1.0
        # caso NAO e' 'error' (nem todos os runs falharam)
        assert caso["status"] == "pass"
        # invoke chamado 3x (1 run falhou mas os outros rodaram)
        assert call[0] == 3

    def test_todos_runs_invoke_falham_status_error(self):
        """Se TODOS os runs deram erro de invoke -> status='error', case_score 0.0."""
        from app.agente.services.eval_gate_service import run_evals
        import os

        path = self._single_case_dataset_path()

        def invoke_sempre_falha(user_input: str) -> str:
            raise RuntimeError("boom sempre")

        try:
            result = run_evals(
                agent_name="n",
                dataset_path=path,
                invoke_fn=invoke_sempre_falha,
                judge_fn=lambda p: {"passed_items": 5, "total_items": 5, "failing": []},
                n_runs=3,
            )
        finally:
            os.unlink(path)

        caso = result["cases"][0]
        assert caso["status"] == "error"
        assert caso["case_score"] == 0.0
        assert caso["runs_scores"] == [0.0, 0.0, 0.0]

    def test_invoke_falha_intermitente_conta_failures_nao_vira_error(self):
        """Caveat I2: invoke falha em ALGUNS runs (nao todos) -> status NAO e' 'error'
        (ha output para julgar), mas invoke_failures conta as falhas de INFRA.

        Distingue 'agente ruim' (score baixo, invoke OK) de 'infra instavel'
        (alguns invokes falharam). 1 sucesso entre 3 -> mediana sobre [0,0,score].
        """
        from app.agente.services.eval_gate_service import run_evals
        import os

        path = self._single_case_dataset_path()

        # invoke: falha nos 2 primeiros runs, sucede no 3o
        chamadas = {'n': 0}

        def invoke_intermitente(user_input: str) -> str:
            chamadas['n'] += 1
            if chamadas['n'] <= 2:
                raise RuntimeError(f"infra instavel run {chamadas['n']}")
            return "output bom"

        try:
            result = run_evals(
                agent_name="n",
                dataset_path=path,
                invoke_fn=invoke_intermitente,
                judge_fn=lambda p: {"passed_items": 5, "total_items": 5, "failing": []},
                n_runs=3,
            )
        finally:
            os.unlink(path)

        caso = result["cases"][0]
        # NAO e' 'error' (1 run produziu output julgavel)
        assert caso["status"] != "error"
        # invoke_failures registra as 2 falhas de infra (caveat I2)
        assert caso["invoke_failures"] == 2
        assert "invoke_failures=2/3" in caso["evidence"]
        # runs_scores = [0.0, 0.0, 1.0] -> mediana 0.0
        assert caso["runs_scores"] == [0.0, 0.0, 1.0]

    def test_campos_novos_presentes_em_cada_caso(self):
        """cases[] ganha n_runs, case_score_variance, runs_scores; mantem id/status/evidence."""
        from app.agente.services.eval_gate_service import run_evals
        import os

        path = self._single_case_dataset_path()
        try:
            result = run_evals(
                agent_name="n",
                dataset_path=path,
                invoke_fn=lambda x: "out",
                judge_fn=lambda p: {"passed_items": 5, "total_items": 5, "failing": []},
                n_runs=3,
            )
        finally:
            os.unlink(path)

        caso = result["cases"][0]
        # campos NOVOS
        assert "n_runs" in caso
        assert "case_score_variance" in caso
        assert "runs_scores" in caso
        assert isinstance(caso["runs_scores"], list)
        assert isinstance(caso["case_score_variance"], float)
        assert isinstance(caso["n_runs"], int)
        # campos EXISTENTES preservados
        assert "id" in caso
        assert "status" in caso
        assert "evidence" in caso
        assert "case_score" in caso

    def test_default_n_runs_e_3(self):
        """run_evals tem n_runs com default 3 na assinatura."""
        from app.agente.services import eval_gate_service as svc
        import inspect

        sig = inspect.signature(svc.run_evals)
        assert "n_runs" in sig.parameters
        assert sig.parameters["n_runs"].default == 3

    def test_default_n_runs_invoca_3x(self):
        """Sem passar n_runs explicito -> default 3 -> invoke chamado 3x por caso."""
        from app.agente.services.eval_gate_service import run_evals
        import os

        path = self._single_case_dataset_path()
        call = [0]

        def invoke_fn(user_input: str) -> str:
            call[0] += 1
            return "out"

        try:
            run_evals(
                agent_name="n",
                dataset_path=path,
                invoke_fn=invoke_fn,
                judge_fn=lambda p: {"passed_items": 5, "total_items": 5, "failing": []},
                # n_runs ausente -> default 3
            )
        finally:
            os.unlink(path)

        assert call[0] == 3
