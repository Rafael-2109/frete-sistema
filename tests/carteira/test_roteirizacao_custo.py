from app.carteira.services.roteirizacao_service import calcular_custo_operacional


class _V:  # stub simples de veiculo
    def __init__(self, custo_km=0, custo_motorista_dia=0, custo_fixo_dia=0, depreciacao_mensal=0):
        self.custo_km = custo_km
        self.custo_motorista_dia = custo_motorista_dia
        self.custo_fixo_dia = custo_fixo_dia
        self.depreciacao_mensal = depreciacao_mensal


def test_combustivel_por_km():
    r = calcular_custo_operacional(100, 120, _V(custo_km=3.0))
    assert r['custo_combustivel'] == 300.0


def test_dias_informado_domina_estimativa():
    r = calcular_custo_operacional(100, 600, _V(custo_motorista_dia=200), dias_viagem=3)
    assert r['dias'] == 3
    assert r['custo_motorista'] == 600.0


def test_dias_estimado_por_tempo_e_jornada():
    # 1500 min = 25h; jornada 10h/dia => ceil(2.5) = 3 dias
    r = calcular_custo_operacional(100, 1500, _V(custo_motorista_dia=100), jornada_horas_dia=10)
    assert r['dias'] == 3


def test_depreciacao_rateada_por_dia():
    r = calcular_custo_operacional(0, 60, _V(depreciacao_mensal=3000), dias_viagem=2)
    assert r['custo_depreciacao'] == 200.0  # 3000/30 * 2


def test_campos_none_viram_zero():
    r = calcular_custo_operacional(50, 60, _V(), dias_viagem=1)
    assert r['custo_operacional'] == 0.0


def test_operacional_soma_componentes():
    v = _V(custo_km=2.0, custo_motorista_dia=150, custo_fixo_dia=40, depreciacao_mensal=3000)
    r = calcular_custo_operacional(100, 60, v, dias_viagem=2)
    # 200 + 300 + 80 + 200 = 780
    assert r['custo_operacional'] == 780.0
