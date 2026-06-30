from app.agente.services.specialist_handoff_metrics import (
    compara_baseline, custo_medio_por_sessao)


def test_custo_medio_lista_vazia_nao_explode(app):
    # Guard n=len or 1: lista vazia -> zeros, estrutura completa, sem divisao por zero.
    with app.app_context():
        r = custo_medio_por_sessao([])
        assert r["sessoes"] == 0
        assert r["custo_medio"] == 0.0
        assert set(r) >= {"custo_total", "sessoes", "custo_medio", "cache_hit_rate", "num_turns"}


def test_custo_medio_sessao_inexistente_zera(app):
    # Agregacao real contra o schema (AgentSessionCost.aggregate_summary +
    # AgentInvocationMetric): session_id sem dados -> zeros, sem explodir.
    with app.app_context():
        r = custo_medio_por_sessao(['sessao-que-nao-existe'])
        assert r["sessoes"] == 1
        assert r["custo_medio"] == 0.0
        assert r["num_turns"] == 0.0


def test_gate_passa_quando_custo_cai_cache_ok_e_turns_estavel():
    base = {"custo_medio": 10.0, "cache_hit_rate": 0.5, "num_turns": 8.0}
    atual = {"custo_medio": 7.0, "cache_hit_rate": 0.62, "num_turns": 8.0}
    r = compara_baseline(base, atual)
    assert r["delta_custo_medio"] == -3.0
    assert r["passou_gate"] is True

def test_gate_falha_se_custo_sobe():
    r = compara_baseline({"custo_medio": 10.0, "cache_hit_rate": 0.5},
                         {"custo_medio": 11.0, "cache_hit_rate": 0.6})
    assert r["passou_gate"] is False

def test_gate_falha_se_cache_regride():
    # Custo caiu mas cache_hit_rate caiu (sinal de re-descoberta/contexto perdido).
    r = compara_baseline({"custo_medio": 10.0, "cache_hit_rate": 0.6},
                         {"custo_medio": 9.0, "cache_hit_rate": 0.4})
    assert r["passou_gate"] is False

def test_gate_falha_se_num_turns_sobe():
    # Spec: turns sobe = perdeu contexto = reverter (mesmo com custo menor).
    r = compara_baseline({"custo_medio": 10.0, "cache_hit_rate": 0.6, "num_turns": 8.0},
                         {"custo_medio": 7.0, "cache_hit_rate": 0.6, "num_turns": 12.0})
    assert r["passou_gate"] is False

def test_gate_robusto_a_chaves_ausentes():
    # GIGO: chaves faltando nao explodem (default 0.0) — entrada incompleta = nao passa.
    r = compara_baseline({}, {})
    assert r["passou_gate"] is False


def test_gate_nao_passa_com_atual_degenerado_e_baseline_cache_zero():
    # Furo fechado: baseline com custo real mas cache_hit_rate=0 + 'atual' vazio
    # (zero sessao medida -> custo_medio=0). Sem guard, 0 < custo_baseline daria
    # 'custo caiu' e 0 >= 0 daria 'cache ok' -> gate APROVAVA dados inexistentes.
    r = compara_baseline({"custo_medio": 10.0, "cache_hit_rate": 0.0, "num_turns": 8.0}, {})
    assert r["passou_gate"] is False
