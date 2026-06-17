"""Acumular lotes numa rota (RotaSalva) a partir de lista_pedidos, com filtros
diferentes, e resgatar no mapa via ?rota_id= (item #6)."""
import json
from app.carteira.models import RotaSalva


def test_rota_acumular_cria_e_anexa(client, db):
    # 1a selecao (de um filtro) cria a rota
    r1 = client.post('/carteira/mapa/api/rota/acumular',
                     data=json.dumps({'nome': 'Acum', 'lotes': ['L1', 'L2']}),
                     content_type='application/json')
    assert r1.status_code == 200
    b1 = r1.get_json()
    rid = b1['id']
    assert b1['total_lotes'] == 2
    # 2a selecao (outro filtro) anexa a MESMA rota, deduplicando L2
    r2 = client.post('/carteira/mapa/api/rota/acumular',
                     data=json.dumps({'rota_id': rid, 'lotes': ['L2', 'L3']}),
                     content_type='application/json')
    b2 = r2.get_json()
    assert b2['id'] == rid
    assert b2['total_lotes'] == 3
    assert set(RotaSalva.query.get(rid).lotes) == {'L1', 'L2', 'L3'}


def test_rota_acumular_sem_lotes_400(client, db):
    r = client.post('/carteira/mapa/api/rota/acumular',
                    data=json.dumps({'nome': 'X'}), content_type='application/json')
    assert r.status_code == 400


def test_visualizar_mapa_resgata_por_rota_id(client, db):
    rota = RotaSalva(nome='Resgate', lotes=['LA', 'LB'], status='rascunho')
    db.session.add(rota)
    db.session.commit()
    resp = client.get(f'/carteira/mapa/visualizar?rota_id={rota.id}')
    assert resp.status_code == 200
    # os lotes da rota chegam ao template (injetados em lotesSelecionados)
    assert b'LA' in resp.data and b'LB' in resp.data
