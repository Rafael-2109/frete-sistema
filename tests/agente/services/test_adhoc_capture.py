"""Testes da Fase 2 — captura de scripts ad-hoc (spec 2026-06-12).

Plano: docs/superpowers/plans/2026-06-12-aprendizado-adhoc-fase2.md
"""
import pytest


class TestModel:
    def test_model_roundtrip(self, db):
        from app.agente.models import AgentAdhocScript
        row = AgentAdhocScript(
            session_id="sess-test-adhoc-1", user_id=1,
            problema="exportar excel multi-aba",
            command_masked="python -c 'import pandas...'",
            contexto_user_msg="exporta em 3 abas",
            skill_relacionada="exportando-arquivos",
            tipo_gap="skill_insuficiente",
            motivo_fallback="exportar.py so gera 1 aba",
            retries_sessao=2,
        )
        db.session.add(row)
        db.session.flush()
        assert row.id is not None
        assert row.cluster_id is None  # setado pelo clustering, nao pelo insert
        db.session.rollback()
