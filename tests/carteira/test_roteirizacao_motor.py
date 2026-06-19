from app.carteira.services.roteirizacao_service import _chunk_waypoints, otimizar_rota


def test_chunk_sem_overlap_quando_cabe():
    paradas = [{'id': str(i), 'lat': 0, 'lng': i} for i in range(5)]
    chunks = _chunk_waypoints(paradas, tam=23)
    assert len(chunks) == 1
    assert len(chunks[0]) == 5


def test_chunk_com_overlap_quando_excede():
    paradas = [{'id': str(i), 'lat': 0, 'lng': i} for i in range(50)]
    chunks = _chunk_waypoints(paradas, tam=23)
    assert len(chunks) >= 2
    assert chunks[0][-1]['id'] == chunks[1][0]['id']  # overlap


def test_otimizar_usa_backend_injetado():
    paradas = [{'id': 'A', 'lat': -23.4, 'lng': -46.8},
               {'id': 'B', 'lat': -23.5, 'lng': -46.6}]

    def fake_backend(origem, destino, waypoints, inclui_volta, respeitar_ordem=False):
        return {'ordem_indices': list(range(len(waypoints))),
                'distancia_km': 42.0, 'tempo_min': 60.0, 'polyline': ['xyz'], 'trechos': 1}

    r = otimizar_rota(paradas, origem='CD', inclui_volta=False, backend=fake_backend)
    assert r['distancia_km'] == 42.0
    assert r['ordem'] == ['A', 'B']
    assert r['polyline'] == ['xyz']


def test_otimizar_vazio_retorna_zerado():
    r = otimizar_rota([], origem='CD')
    assert r['ordem'] == []
    assert r['distancia_km'] == 0.0
    assert r['trechos'] == 0
