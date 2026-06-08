# tests/agente/test_skill_effectiveness.py
import importlib

import pytest


def _reload_flags():
    import app.agente.config.feature_flags as ff
    return importlib.reload(ff)


def test_skill_eval_flags_default_off(monkeypatch):
    for var in ["AGENT_SKILL_EVAL", "AGENT_SKILL_EVAL_SONNET",
                "AGENT_SKILL_EVAL_APPLY_USER"]:
        monkeypatch.delenv(var, raising=False)
    ff = _reload_flags()
    assert ff.AGENT_SKILL_EVAL is False
    # apply_user e sonnet default ON (so atuam quando AGENT_SKILL_EVAL liga o pipeline)
    assert ff.AGENT_SKILL_EVAL_APPLY_USER is True
    assert ff.AGENT_SKILL_EVAL_SONNET is True


def test_skill_eval_flag_on(monkeypatch):
    monkeypatch.setenv("AGENT_SKILL_EVAL", "true")
    ff = _reload_flags()
    assert ff.AGENT_SKILL_EVAL is True


# ---------------------------------------------------------------------------
# Task 2: Modelo AgentSkillEffectiveness
# ---------------------------------------------------------------------------
from sqlalchemy.exc import IntegrityError


def test_skill_effectiveness_unique_anchor(db):
    """Mesma (session_id, anchor_msg_id) nao pode duplicar."""
    from app.agente.models import AgentSkillEffectiveness

    r1 = AgentSkillEffectiveness(
        user_id=1, session_id="sess-A", skill_name="cotando-frete",
        anchor_msg_id="msg-1", stage_reached=0, resolveu=True,
    )
    db.session.add(r1)
    db.session.flush()  # dispara a constraint sem fechar o savepoint da fixture

    r2 = AgentSkillEffectiveness(
        user_id=1, session_id="sess-A", skill_name="cotando-frete",
        anchor_msg_id="msg-1", stage_reached=0, resolveu=True,
    )
    db.session.add(r2)
    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()


# ---------------------------------------------------------------------------
# Task 3: Montagem da janela ancorada
# ---------------------------------------------------------------------------
def test_build_skill_windows_anchors_and_window():
    from app.agente.services.skill_effectiveness_service import build_skill_windows
    msgs = [
        {"id": "u0", "role": "user", "content": "qual frete pra SP?"},
        {"id": "a0", "role": "assistant", "content": "vou cotar", "tools_used": ["Skill:cotando-frete"]},
        {"id": "u1", "role": "user", "content": "nao era isso, ta errado"},
        {"id": "a1", "role": "assistant", "content": "desculpe, corrigindo"},
        {"id": "u2", "role": "user", "content": "agora sim"},
        {"id": "a2", "role": "assistant", "content": "otimo"},
    ]
    wins = build_skill_windows(msgs)
    assert len(wins) == 1
    w = wins[0]
    assert w.skill_name == "cotando-frete"
    assert w.anchor_msg_id == "a0"
    assert w.msg_anterior["id"] == "u0"
    assert [m["id"] for m in w.proximas_user] == ["u1", "u2"]
    assert [m["id"] for m in w.proximas_assistant] == ["a1", "a2"]
    assert w.janela_fechada is True


def test_build_skill_windows_open_window():
    from app.agente.services.skill_effectiveness_service import build_skill_windows
    msgs = [
        {"id": "u0", "role": "user", "content": "x"},
        {"id": "a0", "role": "assistant", "content": "y", "tools_used": ["Skill:cotando-frete"]},
        {"id": "u1", "role": "user", "content": "z"},  # so 1 proxima user -> aberta
    ]
    wins = build_skill_windows(msgs)
    assert wins[0].janela_fechada is False


# ---------------------------------------------------------------------------
# Task 4: Estagio 0 — sinal custo-zero
# ---------------------------------------------------------------------------
from app.agente.services.skill_effectiveness_service import SkillWindow, stage0_has_signal


def _win(prox_user_texts, prox_asst=None):
    return SkillWindow(
        skill_name="cotando-frete", anchor_msg_id="a0",
        msg_anterior={"id": "u0", "role": "user", "content": "frete sp"},
        resposta_invocacao={"id": "a0", "role": "assistant", "content": "cotando"},
        proximas_user=[{"id": f"u{i}", "role": "user", "content": t} for i, t in enumerate(prox_user_texts, 1)],
        proximas_assistant=prox_asst or [],
        janela_fechada=True,
    )


def test_stage0_no_signal():
    assert stage0_has_signal(_win(["perfeito, obrigado", "valeu"])) is False


def test_stage0_signal_frustration():
    assert stage0_has_signal(_win(["nao era isso", "ta errado"])) is True


def test_stage0_signal_adhoc_bash():
    w = _win(["e a outra rota?"],
             prox_asst=[{"id": "a1", "role": "assistant", "content": "rodando",
                         "tools_used": ["Bash"]}])
    assert stage0_has_signal(w) is True


# ---------------------------------------------------------------------------
# Task 5: Estagios 1 e 2 — Haiku e Sonnet
# ---------------------------------------------------------------------------
def test_stage1_haiku_parses(monkeypatch):
    import app.agente.services.skill_effectiveness_service as svc
    monkeypatch.setattr(svc, "_call_anthropic",
        lambda *a, **k: '{"resolveu": false, "suspeita_ajuste": true, "motivo": "x", "sinais": ["ajuste"]}')
    out = svc.stage1_haiku(_win(["ajusta isso"]))
    assert out["suspeita_ajuste"] is True
    assert out["resolveu"] is False


def test_stage2_sonnet_routes_branch(monkeypatch):
    import app.agente.services.skill_effectiveness_service as svc
    monkeypatch.setattr(svc, "_call_anthropic",
        lambda *a, **k: '{"ramo": "lembrete_usuario", "titulo": "T", '
                        '"conteudo_lembrete": "sempre confirmar UF", "confianca": 0.9}')
    out = svc.stage2_sonnet(_win(["nao era isso"]))
    assert out["ramo"] == "lembrete_usuario"
    assert out["confianca"] == 0.9


def test_stage2_invalid_branch_falls_to_nada(monkeypatch):
    import app.agente.services.skill_effectiveness_service as svc
    monkeypatch.setattr(svc, "_call_anthropic", lambda *a, **k: '{"ramo": "xpto"}')
    assert svc.stage2_sonnet(_win(["x"]))["ramo"] == "nada"


# ---------------------------------------------------------------------------
# Task 6: Aplicacao dos ramos
# ---------------------------------------------------------------------------
def test_apply_lembrete_usuario_creates_mandatory_memory(db, monkeypatch):
    import app.agente.services.skill_effectiveness_service as svc
    from app.agente.models import AgentMemory
    monkeypatch.setattr(svc, "_invalidate_caches", lambda uid: None)
    decision = {"ramo": "lembrete_usuario", "titulo": "Confirmar UF",
                "conteudo_lembrete": "sempre confirmar UF antes de cotar", "confianca": 0.9}
    ref = svc.apply_decision(decision, _win(["nao era isso"]), user_id=1, session_id="s1")
    assert ref.startswith("memory:")
    mem = AgentMemory.query.filter_by(user_id=1,
        path="/memories/lembretes_skill/cotando-frete.xml").first()
    assert mem is not None and mem.priority == "mandatory" and mem.category == "permanent"


def test_apply_ajuste_codigo_has_no_solution(db):
    import app.agente.services.skill_effectiveness_service as svc
    from app.agente.models import AgentImprovementDialogue
    decision = {"ramo": "ajuste_codigo", "titulo": "skill falha em AM",
                "problema": "nao trata UF AM", "evidencia": "usuario repetiu 2x",
                "categoria_codigo": "skill_bug", "confianca": 0.8}
    ref = svc.apply_decision(decision, _win(["ajusta"]), user_id=1, session_id="s2")
    assert ref.startswith("dialogue:")
    d = AgentImprovementDialogue.query.get(int(ref.split(":")[1]))
    assert d.description == "nao trata UF AM"
    assert d.implementation_notes is None  # avaliador NAO prescreve solucao


def test_apply_low_confidence_user_downgrades(db, monkeypatch):
    import app.agente.services.skill_effectiveness_service as svc
    from app.agente.config import feature_flags as ff
    monkeypatch.setattr(ff, "AGENT_SKILL_EVAL_CONF_MIN", 0.7, raising=False)
    decision = {"ramo": "lembrete_usuario", "titulo": "t", "problema": "p",
                "confianca": 0.3}  # < 0.7 -> vira ajuste_codigo
    ref = svc.apply_decision(decision, _win(["x"]), user_id=1, session_id="s3")
    assert ref.startswith("dialogue:")
