from app.veiculos.models import Veiculo


def test_criar_veiculo_com_custos(client, db):
    resp = client.post('/veiculos/criar', data={
        'nome': 'TESTE_CRUD_TOCO', 'peso_maximo': '6500',
        'custo_km': '3.50', 'custo_motorista_dia': '200',
        'custo_fixo_dia': '40', 'depreciacao_mensal': '3000',
        'capacidade_pallets': '14', 'capacidade_m3': '42', 'velocidade_media_kmh': '55',
    })
    assert resp.status_code in (200, 302)
    v = Veiculo.query.filter_by(nome='TESTE_CRUD_TOCO').first()
    assert v is not None
    assert float(v.custo_km) == 3.5
    assert v.capacidade_pallets == 14
    assert v.ativo is True


def test_api_lista_expoe_custos(client, db):
    v = Veiculo(nome='TESTE_API_LISTA', peso_maximo=6500, custo_km=2.5,
                custo_motorista_dia=180, capacidade_pallets=14, ativo=True)
    db.session.add(v)
    db.session.flush()
    r = client.get('/veiculos/api/lista')
    assert r.status_code == 200
    item = next((x for x in r.get_json() if x['nome'] == 'TESTE_API_LISTA'), None)
    assert item is not None
    assert item['custo_km'] == 2.5
    assert item['capacidade_pallets'] == 14
    assert item['ativo'] is True
