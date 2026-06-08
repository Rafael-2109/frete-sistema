"""
Testes do teams_observability_service — dashboard de observabilidade do Teams.

Cobre duas fontes:
  - OPERACIONAL: teams_tasks (volume, status, latencia, fila, usuarios, travadas)
  - CUSTO/QUALIDADE: agent_steps (channel='teams') + agent_skill_effectiveness
    (sessoes Teams via session_id LIKE 'teams_%')

Padrao de fixtures: tests/conftest.py (db = savepoint nested + rollback).
"""
from datetime import timedelta

import pytest

from app.utils.timezone import agora_utc_naive


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

def _two_user_ids():
    """Dois user_id reais do banco local (FK exige usuario existente)."""
    from app.auth.models import Usuario
    ids = [u.id for u in Usuario.query.order_by(Usuario.id).limit(2).all()]
    if len(ids) < 2:
        pytest.skip("Banco local sem >= 2 usuarios para teste de FK")
    return ids[0], ids[1]


def _mk_task(db, *, status, created_offset_min=0, completed_offset_min=None,
             updated_offset_min=None, user_id=None, mensagem="oi", conv="conv-1"):
    """Cria uma TeamsTask com timestamps relativos a agora (minutos no passado)."""
    from app.teams.models import TeamsTask
    now = agora_utc_naive()
    created = now - timedelta(minutes=created_offset_min)
    task = TeamsTask(
        conversation_id=conv,
        user_name=f"User {user_id}",
        user_id=user_id,
        status=status,
        mensagem=mensagem,
        created_at=created,
        updated_at=created if updated_offset_min is None
        else now - timedelta(minutes=updated_offset_min),
        completed_at=None if completed_offset_min is None
        else now - timedelta(minutes=completed_offset_min),
    )
    db.session.add(task)
    db.session.flush()
    return task


def _mk_step(db, *, channel, input_tokens=100, output_tokens=50,
             model="claude-opus-4-8", tools=None, created_offset_min=0,
             user_id=None, session_id="teams_conv-1", suffix="a"):
    """Cria um AgentStep (turno) com channel explicito."""
    from app.agente.models import AgentStep
    now = agora_utc_naive()
    step = AgentStep(
        step_uid=f"{session_id}:{suffix}",
        session_id=session_id,
        user_id=user_id,
        channel=channel,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        tools_used=tools or [],
        created_at=now - timedelta(minutes=created_offset_min),
    )
    db.session.add(step)
    db.session.flush()
    return step


def _mk_skill_eff(db, *, session_id, skill_name, resolveu, anchor="m1",
                  ramo="lembrete_usuario", user_id=None):
    """Cria um AgentSkillEffectiveness (1 avaliacao de skill)."""
    from app.agente.models import AgentSkillEffectiveness
    row = AgentSkillEffectiveness(
        user_id=user_id,
        session_id=session_id,
        skill_name=skill_name,
        anchor_msg_id=f"{session_id}:{anchor}",
        stage_reached=2,
        resolveu=resolveu,
        ramo=ramo,
    )
    db.session.add(row)
    db.session.flush()
    return row


# ---------------------------------------------------------------------------
# Isolamento: limpa as tabelas-alvo DENTRO do savepoint (revertido no rollback)
# para que as agregacoes sejam deterministas independente de dados pre-existentes.
# ---------------------------------------------------------------------------

@pytest.fixture
def clean(db):
    from app.teams.models import TeamsTask
    from app.agente.models import AgentStep, AgentSkillEffectiveness
    for M in (TeamsTask, AgentStep, AgentSkillEffectiveness):
        M.query.delete(synchronize_session=False)
    db.session.flush()
    return db


# ---------------------------------------------------------------------------
# _resolve_period_hours
# ---------------------------------------------------------------------------

def test_resolve_period_hours():
    from app.agente.services import teams_observability_service as svc
    assert svc._resolve_period_hours("24h") == 24
    assert svc._resolve_period_hours("7d") == 24 * 7
    assert svc._resolve_period_hours("30d") == 24 * 30
    # default seguro para valor invalido
    assert svc._resolve_period_hours("xpto") == 24 * 7


# ---------------------------------------------------------------------------
# count_by_status
# ---------------------------------------------------------------------------

def test_count_by_status_conta_no_periodo(db, clean):
    from app.agente.services import teams_observability_service as svc
    u1, _ = _two_user_ids()
    _mk_task(db, status="completed", created_offset_min=10, user_id=u1)
    _mk_task(db, status="completed", created_offset_min=20, user_id=u1)
    _mk_task(db, status="error", created_offset_min=30, user_id=u1)
    # fora do periodo de 24h -> nao conta
    _mk_task(db, status="completed", created_offset_min=60 * 48, user_id=u1)

    counts = svc.count_by_status("24h")
    assert counts.get("completed") == 2
    assert counts.get("error") == 1
    assert "timeout" not in counts  # nenhuma timeout no periodo


# ---------------------------------------------------------------------------
# get_overview
# ---------------------------------------------------------------------------

def test_overview_taxas_e_total(db, clean):
    from app.agente.services import teams_observability_service as svc
    u1, _ = _two_user_ids()
    _mk_task(db, status="completed", created_offset_min=5, completed_offset_min=4, user_id=u1)
    _mk_task(db, status="completed", created_offset_min=6, completed_offset_min=4, user_id=u1)
    _mk_task(db, status="error", created_offset_min=7, completed_offset_min=6, user_id=u1)
    _mk_task(db, status="timeout", created_offset_min=8, completed_offset_min=3, user_id=u1)

    ov = svc.get_overview("24h")
    assert ov["total"] == 4
    assert ov["by_status"]["completed"] == 2
    assert ov["taxa_sucesso"] == pytest.approx(50.0, abs=0.1)
    assert ov["taxa_erro"] == pytest.approx(25.0, abs=0.1)
    assert ov["taxa_timeout"] == pytest.approx(25.0, abs=0.1)


def test_overview_latencia(db, clean):
    from app.agente.services import teams_observability_service as svc
    u1, _ = _two_user_ids()
    # created 10min atras, completou 8min atras -> latencia 2min = 120s
    _mk_task(db, status="completed", created_offset_min=10, completed_offset_min=8, user_id=u1)
    # created 20min atras, completou 16min atras -> latencia 4min = 240s
    _mk_task(db, status="completed", created_offset_min=20, completed_offset_min=16, user_id=u1)

    ov = svc.get_overview("24h")
    # media (120+240)/2 = 180s
    assert ov["latencia_media_s"] == pytest.approx(180.0, abs=1.0)


def test_overview_usuarios_ativos_distintos(db, clean):
    from app.agente.services import teams_observability_service as svc
    u1, u2 = _two_user_ids()
    _mk_task(db, status="completed", created_offset_min=5, user_id=u1)
    _mk_task(db, status="completed", created_offset_min=6, user_id=u1)
    _mk_task(db, status="error", created_offset_min=7, user_id=u2)
    ov = svc.get_overview("24h")
    assert ov["usuarios_ativos"] == 2


# ---------------------------------------------------------------------------
# get_stuck_tasks (snapshot — independe de period)
# ---------------------------------------------------------------------------

def test_stuck_tasks_detecta_awaiting_antigo(db, clean):
    from app.agente.services import teams_observability_service as svc
    u1, _ = _two_user_ids()
    # awaiting ha 30min (travada), threshold 10min -> aparece
    _mk_task(db, status="awaiting_user_input", created_offset_min=40,
             updated_offset_min=30, user_id=u1, conv="travada")
    # awaiting ha 2min (recente) -> NAO aparece
    _mk_task(db, status="awaiting_user_input", created_offset_min=5,
             updated_offset_min=2, user_id=u1, conv="recente")
    # completed antiga -> NAO aparece (nao e estado de espera)
    _mk_task(db, status="completed", created_offset_min=60,
             updated_offset_min=60, user_id=u1, conv="done")

    stuck = svc.get_stuck_tasks(threshold_min=10)
    convs = {t["conversation_id"] for t in stuck}
    assert "travada" in convs
    assert "recente" not in convs
    assert "done" not in convs


# ---------------------------------------------------------------------------
# get_top_users
# ---------------------------------------------------------------------------

def test_top_users_ordena_por_volume(db, clean):
    from app.agente.services import teams_observability_service as svc
    u1, u2 = _two_user_ids()
    for i in range(3):
        _mk_task(db, status="completed", created_offset_min=5 + i, user_id=u1)
    _mk_task(db, status="completed", created_offset_min=9, user_id=u2)
    top = svc.get_top_users("24h", limit=10)
    assert top[0]["user_id"] == u1
    assert top[0]["count"] == 3


# ---------------------------------------------------------------------------
# CUSTO / QUALIDADE — agent_steps channel='teams'
# ---------------------------------------------------------------------------

def test_cost_quality_so_conta_canal_teams(db, clean):
    from app.agente.services import teams_observability_service as svc
    u1, _ = _two_user_ids()
    _mk_step(db, channel="teams", input_tokens=100, output_tokens=50,
             user_id=u1, session_id="teams_c1", suffix="t1", created_offset_min=5)
    _mk_step(db, channel="teams", input_tokens=200, output_tokens=80,
             user_id=u1, session_id="teams_c1", suffix="t2", created_offset_min=6)
    # canal web -> NAO deve entrar
    _mk_step(db, channel="web", input_tokens=999, output_tokens=999,
             user_id=u1, session_id="web_c1", suffix="w1", created_offset_min=5)

    cq = svc.get_cost_quality_overview("24h")
    assert cq["num_turnos"] == 2
    assert cq["total_input_tokens"] == 300
    assert cq["total_output_tokens"] == 130
    assert cq["custo_estimado_usd"] > 0


def test_tools_usage_agrega_do_teams(db, clean):
    from app.agente.services import teams_observability_service as svc
    u1, _ = _two_user_ids()
    _mk_step(db, channel="teams", tools=["mcp__sql__query", "Read"],
             user_id=u1, session_id="teams_c1", suffix="t1", created_offset_min=5)
    _mk_step(db, channel="teams", tools=["mcp__sql__query"],
             user_id=u1, session_id="teams_c1", suffix="t2", created_offset_min=6)
    _mk_step(db, channel="web", tools=["mcp__sql__query"],
             user_id=u1, session_id="web_c1", suffix="w1", created_offset_min=5)

    tools = svc.get_tools_usage("24h", limit=10)
    by_name = {t["tool"]: t["count"] for t in tools}
    assert by_name.get("mcp__sql__query") == 2  # so canal teams
    assert by_name.get("Read") == 1


# ---------------------------------------------------------------------------
# QUALIDADE DE SKILLS POR CANAL — agent_skill_effectiveness (session teams_%)
# ---------------------------------------------------------------------------

def test_skill_effectiveness_so_sessoes_teams(db, clean):
    from app.agente.services import teams_observability_service as svc
    u1, _ = _two_user_ids()
    # Teams: cotando-frete resolveu 2x, nao-resolveu 1x
    _mk_skill_eff(db, session_id="teams_x1", skill_name="cotando-frete",
                  resolveu=True, anchor="a1", user_id=u1)
    _mk_skill_eff(db, session_id="teams_x1", skill_name="cotando-frete",
                  resolveu=True, anchor="a2", user_id=u1)
    _mk_skill_eff(db, session_id="teams_x2", skill_name="cotando-frete",
                  resolveu=False, anchor="a1", user_id=u1)
    # Web: NAO deve contar
    _mk_skill_eff(db, session_id="web_x1", skill_name="cotando-frete",
                  resolveu=True, anchor="a1", user_id=u1)

    eff = svc.get_skill_effectiveness("30d")
    cot = next(e for e in eff if e["skill_name"] == "cotando-frete")
    assert cot["total"] == 3            # so Teams
    assert cot["resolveu"] == 2
    assert cot["taxa_resolucao"] == pytest.approx(66.7, abs=0.5)


# ---------------------------------------------------------------------------
# get_timeseries
# ---------------------------------------------------------------------------

def test_timeseries_soma_e_estrutura(db, clean):
    from app.agente.services import teams_observability_service as svc
    u1, _ = _two_user_ids()
    _mk_task(db, status="completed", created_offset_min=30, user_id=u1)
    _mk_task(db, status="error", created_offset_min=90, user_id=u1)
    _mk_task(db, status="completed", created_offset_min=200, user_id=u1)
    ts = svc.get_timeseries("7d")
    assert sum(r["total"] for r in ts) == 3
    assert sum(r["completed"] for r in ts) == 2
    assert sum(r["error"] for r in ts) == 1
    for r in ts:
        assert {"bucket", "total", "completed", "error", "timeout"} <= set(r.keys())


# ---------------------------------------------------------------------------
# get_recent_tasks
# ---------------------------------------------------------------------------

def test_recent_tasks_ordem_e_filtro(db, clean):
    from app.agente.services import teams_observability_service as svc
    u1, _ = _two_user_ids()
    _mk_task(db, status="completed", created_offset_min=5, user_id=u1, mensagem="nova")
    _mk_task(db, status="error", created_offset_min=50, user_id=u1, mensagem="velha")
    recent = svc.get_recent_tasks(limit=10)
    assert recent[0]["mensagem_preview"].startswith("nova")  # mais recente primeiro
    assert "status" in recent[0] and "created_at" in recent[0]
    # filtro por status
    errs = svc.get_recent_tasks(limit=10, status="error")
    assert all(r["status"] == "error" for r in errs)
    assert len(errs) == 1
