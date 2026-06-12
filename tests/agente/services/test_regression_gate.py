"""
Testes de regression_gate.eval_gate — gate puro de regressão (baseline × candidate).

Migrados de tests/agente/services/test_eval_gate.py (classe TestEvalGate) na
estratégia R2 (2026-06-12): o eval_gate_service/A3 foi removido; a função pura
eval_gate sobreviveu em app/agente/services/regression_gate.py (caller vivo:
directive_promotion_service.evaluate_and_promote, sempre report_only).

PUROS (sem DB/LLM/app context).
"""


class TestEvalGate:
    """eval_gate: report_only nunca bloqueia; enforce bloqueia em regressao."""

    def test_report_only_nunca_bloqueia_sem_regressao(self):
        """mode=report_only: blocked=False mesmo sem regressao."""
        from app.agente.services.regression_gate import eval_gate
        result = eval_gate(baseline_score=0.9, candidate_score=0.95, mode="report_only")
        assert result["blocked"] is False
        assert result["regression"] is False

    def test_report_only_nunca_bloqueia_com_regressao(self):
        """mode=report_only: blocked=False MESMO com regressao grave (invariante central)."""
        from app.agente.services.regression_gate import eval_gate
        result = eval_gate(baseline_score=0.9, candidate_score=0.5, mode="report_only")
        assert result["blocked"] is False
        assert result["regression"] is True  # detecta, mas NAO bloqueia

    def test_report_only_detecta_delta(self):
        """mode=report_only retorna delta correto."""
        from app.agente.services.regression_gate import eval_gate
        result = eval_gate(baseline_score=0.8, candidate_score=0.6, mode="report_only")
        assert abs(result["delta"] - (0.6 - 0.8)) < 0.001

    def test_enforce_bloqueia_em_regressao(self):
        """mode=enforce: blocked=True quando candidate < baseline - threshold."""
        from app.agente.services.regression_gate import eval_gate
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
        from app.agente.services.regression_gate import eval_gate
        result = eval_gate(
            baseline_score=0.9,
            candidate_score=0.87,  # delta = -0.03, threshold = 0.05 -> OK
            threshold=0.05,
            mode="enforce",
        )
        assert result["blocked"] is False

    def test_enforce_nao_bloqueia_melhoria(self):
        """mode=enforce: blocked=False quando candidate > baseline."""
        from app.agente.services.regression_gate import eval_gate
        result = eval_gate(
            baseline_score=0.8,
            candidate_score=0.95,
            mode="enforce",
        )
        assert result["blocked"] is False
        assert result["regression"] is False

    def test_threshold_customizado(self):
        """threshold customizado e' respeitado."""
        from app.agente.services.regression_gate import eval_gate
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
        from app.agente.services.regression_gate import eval_gate
        result = eval_gate(baseline_score=0.8, candidate_score=0.7)
        assert "regression" in result
        assert "blocked" in result
        assert "delta" in result

    def test_default_mode_e_report_only(self):
        """Sem mode explicito, default e report_only (blocked sempre False)."""
        from app.agente.services.regression_gate import eval_gate
        # Regressao grave sem mode explicito
        result = eval_gate(baseline_score=1.0, candidate_score=0.0)
        assert result["blocked"] is False
