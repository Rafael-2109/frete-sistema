"""Servico de roteirizacao: custo parametrico, selecao de veiculo e motor de
otimizacao (abstracao de backend). Separa responsabilidade de mapa_service.py
(geocoding/agrupamento)."""
import math
import logging

logger = logging.getLogger(__name__)


def _f(v):
    """Converte Numeric/None em float (None -> 0.0)."""
    return float(v) if v is not None else 0.0


def calcular_custo_operacional(distancia_km, tempo_min, veiculo,
                               dias_viagem=0, jornada_horas_dia=10.0):
    """Custo operacional da rota (SEM pedagio). Tudo parametrico do tipo de veiculo.

    dias_viagem > 0 domina; senao estima por tempo de direcao / jornada diaria.
    """
    if dias_viagem and dias_viagem > 0:
        dias = int(dias_viagem)
    else:
        horas = (tempo_min or 0) / 60.0
        dias = max(1, math.ceil(horas / jornada_horas_dia)) if horas else 1

    custo_combustivel = round(_f(distancia_km) * _f(veiculo.custo_km), 2)
    custo_motorista = round(dias * _f(veiculo.custo_motorista_dia), 2)
    custo_fixo = round(dias * _f(veiculo.custo_fixo_dia), 2)
    custo_depreciacao = round(dias * (_f(veiculo.depreciacao_mensal) / 30.0), 2)
    custo_operacional = round(
        custo_combustivel + custo_motorista + custo_fixo + custo_depreciacao, 2
    )
    return {
        'dias': dias,
        'custo_combustivel': custo_combustivel,
        'custo_motorista': custo_motorista,
        'custo_fixo': custo_fixo,
        'custo_depreciacao': custo_depreciacao,
        'custo_operacional': custo_operacional,
    }
