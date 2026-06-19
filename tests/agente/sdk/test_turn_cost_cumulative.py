"""TDD do fix de double-counting de custo do agente (2026-06-19).

`ResultMessage.total_cost_usd` e o custo ACUMULADO da sessao SDK (cresce a cada
turno). O codigo somava esse acumulado a cada turno -> `agent_sessions.total_cost_usd`
e `agent_session_costs.cost_usd` inflados ~Nx (N = turnos). Caso real: sessao da
Rayssa reportada $223.59, real $31.92 (13 turnos, fator 7x); $102.90 vs $19.22.

`turn_cost_from_cumulative` converte o acumulado no custo do TURNO (delta),
detectando reset de sessao SDK (resume/nova sessao zera o baseline).
"""
from app.agente.sdk.pricing import turn_cost_from_cumulative


def test_primeiro_turno_delta_e_o_acumulado_inteiro():
    # 1o turno: prev=0, sdk anterior None -> delta = acumulado inteiro
    assert turn_cost_from_cumulative(0.82, 0.0, None, "sidA") == 0.82


def test_turno_seguinte_mesma_sessao_e_delta():
    # acumulado 5.72, anterior 0.82, mesmo sdk_session -> turno custou 4.90
    assert round(turn_cost_from_cumulative(5.72, 0.82, "sidA", "sidA"), 2) == 4.90


def test_reset_por_queda_do_acumulado():
    # nova sessao SDK: acumulado caiu 7.33 -> 1.58 = delta e o proprio 1.58
    assert turn_cost_from_cumulative(1.58, 7.33, "sidA", "sidB") == 1.58


def test_reset_por_troca_de_sdk_session_id():
    # acumulado maior, mas sdk_session_id mudou -> segmento novo, delta = inteiro
    assert turn_cost_from_cumulative(2.0, 1.0, "sidA", "sidB") == 2.0


def test_acumulado_zero_ou_negativo_nao_conta():
    assert turn_cost_from_cumulative(0.0, 5.0, "sidA", "sidA") == 0.0
    assert turn_cost_from_cumulative(-1.0, 5.0, "sidA", "sidA") == 0.0


def test_curr_sid_none_nao_forca_reset():
    # sdk_id indisponivel nesse turno (None): segue pela comparacao de valor
    assert round(turn_cost_from_cumulative(6.0, 4.0, "sidA", None), 2) == 2.0


def test_sequencia_rayssa_soma_dos_deltas_bate_com_real():
    # os 13 acumulados reais da sessao 17b68633 (estritamente crescentes)
    cumul = [0.82, 5.72, 6.42, 8.93, 14.87, 15.41, 16.59, 20.20,
             20.68, 25.06, 27.34, 29.64, 31.92]
    prev, total = 0.0, 0.0
    for c in cumul:
        total += turn_cost_from_cumulative(c, prev, "sidA", "sidA")
        prev = c
    # soma telescopica dos deltas = ultimo acumulado, NAO a soma dos acumulados
    assert round(total, 2) == 31.92
    # o que o bug somava (~7x o real): a lista acima e arredondada a 2 casas e
    # soma 223.60; no banco, com 6 casas, e 223.589750 (= o $223.59 reportado).
    assert round(sum(cumul), 2) == 223.60


def test_sequencia_com_reset_soma_dos_segmentos():
    # sessao 92516689: 2 segmentos SDK (reset em 1.58)
    seg = [
        (2.36, "A"), (4.56, "A"), (6.28, "A"), (7.33, "A"),   # seg A -> 7.33
        (1.58, "B"), (3.89, "B"), (11.89, "B"),               # seg B -> 11.89
    ]
    prev, prev_sid, total = 0.0, None, 0.0
    for cum, sid in seg:
        total += turn_cost_from_cumulative(cum, prev, prev_sid, sid)
        prev, prev_sid = cum, sid
    # custo real = pico de cada segmento: 7.33 + 11.89
    assert round(total, 2) == 19.22
