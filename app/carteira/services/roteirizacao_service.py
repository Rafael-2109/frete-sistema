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


def _chunk_waypoints(paradas, tam=23):
    """Divide paradas em blocos de ate `tam` com overlap de 1 ponto entre blocos
    (fim de um = inicio do proximo), para concatenar trechos sem buraco. Limite
    Directions = 25 waypoints (origin+destination+23 intermediarios)."""
    if len(paradas) <= tam:
        return [list(paradas)]
    chunks, i = [], 0
    while i < len(paradas):
        bloco = paradas[i:i + tam]
        chunks.append(bloco)
        if i + tam >= len(paradas):
            break
        i = i + tam - 1  # overlap de 1
    return chunks


def otimizar_rota(paradas, origem, inclui_volta=False, respeitar_ordem=False, backend=None):
    """Otimiza (ou apenas mede, se `respeitar_ordem`) a sequencia das paradas.

    `backend(origem, destino, waypoints, inclui_volta, respeitar_ordem) ->
     {ordem_indices, distancia_km, tempo_min, polyline, trechos, legs, bounds}`.
    Default backend = default_backend (Route Optimization/Directions+chunking).
    `respeitar_ordem=True` mede a ordem recebida sem reordenar (drag-and-drop).
    Retorna tambem `legs` (trechos com duracao_s/distancia_m) e `bounds`, que
    alimentam o desenho da rota e o "tempo ate aqui" — unificando desenho+custo."""
    if not paradas:
        return {'ordem': [], 'distancia_km': 0.0, 'tempo_min': 0.0,
                'polyline': '', 'trechos': 0, 'legs': [], 'bounds': None}
    if backend is None:
        from app.carteira.services.roteirizacao_backends import default_backend
        backend = default_backend

    destino = origem if inclui_volta else None
    res = backend(origem, destino, paradas, inclui_volta, respeitar_ordem=respeitar_ordem)
    ordem = [paradas[i]['id'] for i in res['ordem_indices']]
    return {
        'ordem': ordem,
        'distancia_km': round(res.get('distancia_km', 0.0), 2),
        'tempo_min': round(res.get('tempo_min', 0.0), 1),
        'polyline': res.get('polyline', ''),
        'trechos': res.get('trechos', 1),
        'legs': res.get('legs', []),
        'bounds': res.get('bounds'),
    }


def selecionar_veiculo(peso, pallets=0, m3=0):
    """Menor veiculo ativo que comporta peso + pallets + m3. Capacidade None
    = dimensao nao restringe. Fallback: maior por peso entre os ativos."""
    from app.veiculos.models import Veiculo

    candidatos = (
        Veiculo.query.filter(Veiculo.ativo.is_(True))
        .order_by(Veiculo.peso_maximo.asc())
        .all()
    )
    for v in candidatos:
        if v.peso_maximo < (peso or 0):
            continue
        if pallets and v.capacidade_pallets is not None and v.capacidade_pallets < pallets:
            continue
        if m3 and v.capacidade_m3 is not None and v.capacidade_m3 < m3:
            continue
        return v
    return candidatos[-1] if candidatos else None
