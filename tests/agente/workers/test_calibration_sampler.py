"""
Testa o sampler de calibração do ONLINE judge (E3 re-apontado — GATE-1).

Após a aposentadoria do A3 (2026-06-03), a calibração do judge deixa de ser
alimentada pelo eval_runner (morto) e passa a popular `agent_eval_case` a partir
dos vereditos do online judge gravados em `agent_step.outcome_signal['judge']`.

Cobertura:
- _map_judge_to_case_fields: mapeia o veredito do judge -> campos de AgentEvalCase
  (função pura, sem DB), incluindo a flag de PRIORIDADE quando há discordância
  judge=success x adversarial.refuted (achado da Task 3 — alto valor de calibração).
"""


def _fake_step(step_uid, outcome_signal):
    class _S:
        pass
    s = _S()
    s.step_uid = step_uid
    s.outcome_signal = outcome_signal
    return s


class TestMapJudgeToCaseFields:
    """Mapeamento puro judge -> AgentEvalCase (sem DB)."""

    def test_sem_judge_retorna_none(self):
        from app.agente.workers.calibration_sampler import _map_judge_to_case_fields
        assert _map_judge_to_case_fields(_fake_step("sess-a:1", {})) is None
        assert _map_judge_to_case_fields(_fake_step("sess-a:1", None)) is None

    def test_mapeia_success(self):
        from app.agente.workers.calibration_sampler import _map_judge_to_case_fields
        s = _fake_step("sess-a:1", {"judge": {"label": "success", "score": 85, "evidencia": "tudo certo"}})
        f = _map_judge_to_case_fields(s)
        assert f["agent_name"] == "__online_judge__"
        assert f["case_id"] == "sess-a:1"
        assert f["case_score"] == 0.85
        assert f["status"] == "pass"          # score >= 70
        assert "success" in f["evidence"] and "85" in f["evidence"]
        assert f["prioridade"] is False        # sem discordância adversarial

    def test_mapeia_failure(self):
        from app.agente.workers.calibration_sampler import _map_judge_to_case_fields
        f = _map_judge_to_case_fields(
            _fake_step("sess-b:2", {"judge": {"label": "failure", "score": 15, "evidencia": "ruim"}})
        )
        assert f["status"] == "fail"           # score < 70
        assert f["case_score"] == 0.15

    def test_prioridade_quando_judge_success_e_adversarial_refuta(self):
        # Achado Task 3: discordância de ALTO VALOR (judge diz bom, adversarial refuta).
        from app.agente.workers.calibration_sampler import _map_judge_to_case_fields
        s = _fake_step("sess-c:3", {
            "judge": {"label": "success", "score": 90, "evidencia": "ok"},
            "verify": {"adversarial": {"refuted": True, "reason": "nao confirmou export real"}},
        })
        f = _map_judge_to_case_fields(s)
        assert f["prioridade"] is True
        assert "ADVERSARIAL" in f["evidence"].upper()
        assert "export" in f["evidence"]

    def test_sem_prioridade_quando_concordam_que_e_ruim(self):
        # judge=failure + adversarial refuta = CONCORDAM (ruim) -> não é alto valor.
        from app.agente.workers.calibration_sampler import _map_judge_to_case_fields
        s = _fake_step("sess-d:4", {
            "judge": {"label": "failure", "score": 10, "evidencia": "ruim"},
            "verify": {"adversarial": {"refuted": True, "reason": "x"}},
        })
        f = _map_judge_to_case_fields(s)
        assert f["prioridade"] is False

    def test_score_ausente_degrada_seguro(self):
        from app.agente.workers.calibration_sampler import _map_judge_to_case_fields
        # judge sem score numérico -> case_score 0.0, status 'fail', sem quebrar.
        f = _map_judge_to_case_fields(
            _fake_step("sess-e:5", {"judge": {"label": "partial", "evidencia": "meio"}})
        )
        assert f is not None
        assert f["case_score"] == 0.0
        assert f["status"] == "fail"


class TestPopulateCalibrationCasesGate:
    """INV-6: flag OFF = no-op (não toca DB)."""

    def test_flag_off_e_noop(self, monkeypatch):
        import app.agente.config.feature_flags as ff
        monkeypatch.setattr(ff, 'USE_AGENT_EVAL_CALIBRATION', False)
        from app.agente.workers.calibration_sampler import populate_calibration_cases
        result = populate_calibration_cases()
        assert result.get('skipped') == 'flag_off'
        assert result['inseridos'] == 0
