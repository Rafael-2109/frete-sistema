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


# ---------------------------------------------------------------------------
# Helpers de fixture: entries sinteticas no formato JSONL do SDK
# ---------------------------------------------------------------------------

def _tu(name, tid, **inp):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": tid, "name": name, "input": inp}]}}


def _tr(tid, is_error=False):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": tid, "is_error": is_error}]}}


def _user(texto):
    return {"type": "user", "message": {"content": texto}}


class TestParser:
    def test_extrai_bash_com_skill_e_retry(self):
        from app.agente.services.adhoc_capture_service import extract_adhoc_candidates
        entries = [
            _user("exporta as 3 carteiras em abas"),
            _tu("Skill", "t1", skill="exportando-arquivos"),
            _tr("t1"),
            _tu("Bash", "t2", command="python -c 'tenta1'" + "x" * 300),
            _tr("t2", is_error=True),
            _tu("Bash", "t3", command="python -c 'tenta2'" + "x" * 300),
            _tr("t3"),
        ]
        cands = extract_adhoc_candidates(entries)
        assert len(cands) == 2
        assert cands[0]["skill_ativa"] == "exportando-arquivos"
        assert cands[0]["user_msg"] == "exporta as 3 carteiras em abas"
        assert cands[0]["teve_erro"] is True
        assert cands[1]["teve_erro"] is False

    def test_sem_skill_anterior(self):
        from app.agente.services.adhoc_capture_service import extract_adhoc_candidates
        entries = [_user("soma os fretes"),
                   _tu("Bash", "t1", command="python -c 'x'" + "y" * 300), _tr("t1")]
        cands = extract_adhoc_candidates(entries)
        assert cands[0]["skill_ativa"] is None

    def test_user_msg_em_blocks(self):
        from app.agente.services.adhoc_capture_service import extract_adhoc_candidates
        entries = [
            {"type": "user", "message": {"content": [{"type": "text", "text": "oi"}]}},
            _tu("Bash", "t1", command="psql -c 'SELECT 1'" + "z" * 300), _tr("t1"),
        ]
        assert extract_adhoc_candidates(entries)[0]["user_msg"] == "oi"


class TestFiltro:
    @pytest.mark.parametrize("cmd,esperado", [
        ("python -c 'import pandas; ...'", True),
        ("psql $DATABASE_URL -c \"SELECT count(*) FROM fretes\"", True),
        ("python << 'EOF'\nimport app\nEOF", True),
        ("x" * 250, True),                                     # longo = substantivo
        ("ls -la", False),
        ("git status", False),
        ("cat arquivo.txt", False),
        ("python .claude/skills/consultando-sql/scripts/consultar.py --q 'x'", False),  # script de skill
        ("source .venv/bin/activate && python app/odoo/scripts/foo.py", False),         # script persistido
    ])
    def test_substantivo(self, cmd, esperado):
        from app.agente.services.adhoc_capture_service import is_substantive
        assert is_substantive(cmd) is esperado


class TestExtracao:
    def test_haiku_ok(self, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        monkeypatch.setattr(svc, "_call_anthropic",
            lambda model, system, user, max_tokens=300:
                '{"problema": "exportar excel multi-aba", "motivo_fallback": "exportar.py so gera 1 aba"}')
        prob, motivo = svc.extract_problema(
            command="python -c '...'", user_msg="exporta em 3 abas",
            skill_ativa="exportando-arquivos")
        assert prob == "exportar excel multi-aba"
        assert motivo == "exportar.py so gera 1 aba"

    def test_fallback_truncate(self, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        def _boom(*a, **k):
            raise RuntimeError("api down")
        monkeypatch.setattr(svc, "_call_anthropic", _boom)
        prob, motivo = svc.extract_problema(
            command="python -c 'x'", user_msg="m" * 300, skill_ativa=None)
        assert prob == "m" * 100
        assert motivo is None

    def test_trunca_limites(self, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        monkeypatch.setattr(svc, "_call_anthropic",
            lambda *a, **k: '{"problema": "' + "p" * 200 + '", "motivo_fallback": "' + "q" * 300 + '"}')
        prob, motivo = svc.extract_problema("cmd", "msg", "skill-x")
        assert len(prob) <= 100 and len(motivo) <= 150


def _vec(direcao: int) -> list:
    """Vetor 1024-dim quase-unitario numa 'direcao' sintetica."""
    v = [0.001] * 1024
    v[direcao] = 1.0
    return v


class TestCluster:
    def test_primeiro_vira_proprio_cluster(self, db):
        pytest.importorskip("pgvector")
        from app.agente.services.adhoc_capture_service import assign_cluster
        from app.agente.models import AgentAdhocScript
        row = AgentAdhocScript(session_id="s-c1", user_id=1, command_masked="x",
                               embedding=_vec(0))
        db.session.add(row); db.session.flush()
        assign_cluster(row)
        assert row.cluster_id == row.id
        db.session.rollback()

    def test_vizinho_proximo_herda(self, db):
        pytest.importorskip("pgvector")
        from app.agente.services.adhoc_capture_service import assign_cluster
        from app.agente.models import AgentAdhocScript
        a = AgentAdhocScript(session_id="s-c2", user_id=1, command_masked="a",
                             embedding=_vec(5))
        db.session.add(a); db.session.flush()
        a.cluster_id = a.id; db.session.flush()
        b = AgentAdhocScript(session_id="s-c2", user_id=1, command_masked="b",
                             embedding=_vec(5))  # identico -> sim 1.0
        db.session.add(b); db.session.flush()
        assign_cluster(b)
        assert b.cluster_id == a.id
        db.session.rollback()

    def test_distante_abre_cluster(self, db):
        pytest.importorskip("pgvector")
        from app.agente.services.adhoc_capture_service import assign_cluster
        from app.agente.models import AgentAdhocScript
        a = AgentAdhocScript(session_id="s-c3", user_id=1, command_masked="a",
                             embedding=_vec(10))
        db.session.add(a); db.session.flush()
        a.cluster_id = a.id; db.session.flush()
        b = AgentAdhocScript(session_id="s-c3", user_id=1, command_masked="b",
                             embedding=_vec(900))  # ortogonal -> sim ~0
        db.session.add(b); db.session.flush()
        assign_cluster(b)
        assert b.cluster_id == b.id
        db.session.rollback()

    def test_sem_embedding_cluster_proprio(self, db):
        from app.agente.services.adhoc_capture_service import assign_cluster
        from app.agente.models import AgentAdhocScript
        row = AgentAdhocScript(session_id="s-c4", user_id=1, command_masked="x")
        db.session.add(row); db.session.flush()
        assign_cluster(row)
        assert row.cluster_id == row.id
        db.session.rollback()


class TestDisparo:
    def _mk(self, db, cluster_id, n, user_id=1, **kw):
        from app.agente.models import AgentAdhocScript
        rows = []
        for i in range(n):
            r = AgentAdhocScript(session_id=f"s-d{cluster_id}-{i}", user_id=user_id,
                                 command_masked=f"cmd{i}", problema=f"prob {cluster_id}",
                                 cluster_id=cluster_id, **kw)
            db.session.add(r); rows.append(r)
        db.session.flush()
        return rows

    def test_threshold_user_dispara_dialogue(self, db, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        from app.agente.models import AgentImprovementDialogue
        monkeypatch.setattr(svc, "_call_anthropic", lambda *a, **k:
            '{"vale_skill": true, "tipo_gap": "sem_skill", "titulo": "skill p/ X", "descricao": "cluster de 3"}')
        rows = self._mk(db, cluster_id=777001, n=3)
        ref = svc.maybe_fire_suggestion(rows[-1])
        assert ref and ref.startswith("dialogue:")
        d = AgentImprovementDialogue.query.filter_by(
            suggestion_key="adhoc-cluster-777001").first()
        assert d is not None and d.category == "skill_suggestion"
        assert d.evidence_json["tipo_gap"] == "sem_skill"
        db.session.rollback()

    def test_abaixo_threshold_nao_dispara(self, db, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        called = []
        monkeypatch.setattr(svc, "_call_anthropic", lambda *a, **k: called.append(1) or "{}")
        rows = self._mk(db, cluster_id=777002, n=2)
        assert svc.maybe_fire_suggestion(rows[-1]) is None
        assert not called  # Sonnet nem foi chamado
        db.session.rollback()

    def test_bypass_gap_nomeado(self, db, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        monkeypatch.setattr(svc, "_call_anthropic", lambda *a, **k:
            '{"vale_skill": true, "tipo_gap": "skill_insuficiente", "titulo": "estender exportar", "descricao": "1 aba"}')
        rows = self._mk(db, cluster_id=777003, n=1,
                        skill_relacionada="exportando-arquivos",
                        tipo_gap="skill_insuficiente", motivo_fallback="so 1 aba")
        ref = svc.maybe_fire_suggestion(rows[-1])
        assert ref is not None  # 1 ocorrencia ja basta
        db.session.rollback()

    def test_dedup_suggestion_key(self, db, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        monkeypatch.setattr(svc, "_call_anthropic", lambda *a, **k:
            '{"vale_skill": true, "tipo_gap": "sem_skill", "titulo": "t", "descricao": "d"}')
        rows = self._mk(db, cluster_id=777004, n=3)
        assert svc.maybe_fire_suggestion(rows[-1]) is not None
        assert svc.maybe_fire_suggestion(rows[-1]) is None  # 2a vez trava
        db.session.rollback()

    def test_veto_sonnet_marca_one_off(self, db, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        monkeypatch.setattr(svc, "_call_anthropic", lambda *a, **k:
            '{"vale_skill": false, "tipo_gap": "one_off", "titulo": "", "descricao": ""}')
        rows = self._mk(db, cluster_id=777005, n=3)
        assert svc.maybe_fire_suggestion(rows[-1]) is None
        assert all(r.tipo_gap == "one_off" for r in rows)
        db.session.rollback()
