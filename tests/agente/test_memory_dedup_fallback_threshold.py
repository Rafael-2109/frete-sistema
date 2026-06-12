"""Fix incidente 2026-06-12: fallback do dedup de memorias bloqueava assuntos
distintos do mesmo dominio (sim 0.80-0.81 < novo threshold 0.92)."""


class TestDedupFallbackThreshold:
    def test_default_092(self):
        from app.agente.tools.memory_mcp_tool import _dedup_fallback_threshold
        assert _dedup_fallback_threshold() == 0.92

    def test_le_flag(self, monkeypatch):
        from app.agente.config import feature_flags as ff
        from app.agente.tools.memory_mcp_tool import _dedup_fallback_threshold
        monkeypatch.setattr(ff, "AGENT_MEMORY_DEDUP_FALLBACK_SIM", 0.95)
        assert _dedup_fallback_threshold() == 0.95

    def test_caso_real_incidente_nao_bloqueia(self):
        """Similaridades medidas no incidente (0.802/0.804/0.807) ficam ABAIXO."""
        from app.agente.tools.memory_mcp_tool import _dedup_fallback_threshold
        for sim in (0.802, 0.804, 0.807):
            assert sim < _dedup_fallback_threshold()
