from app.carteira.models import RotaSalva


def test_cotar_por_rota_salva(client, db):
    r = RotaSalva(nome='Rota Cotar', lotes=['LOTE-A', 'LOTE-B'], status='salva')
    db.session.add(r)
    db.session.flush()

    resp = client.post(f'/carteira/mapa/api/rota/{r.id}/cotar')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['sucesso'] is True
    assert set(body['lotes']) == {'LOTE-A', 'LOTE-B'}
    assert 'cotacao' in body['redirect']
    with client.session_transaction() as sess:
        assert set(sess['cotacao_lotes']) == {'LOTE-A', 'LOTE-B'}


def test_cotar_rota_inexistente_404(client, db):
    resp = client.post('/carteira/mapa/api/rota/999999/cotar')
    assert resp.status_code == 404


def test_cotar_rota_sem_lotes_400(client, db):
    r = RotaSalva(nome='Vazia', lotes=[], status='salva')
    db.session.add(r)
    db.session.flush()
    resp = client.post(f'/carteira/mapa/api/rota/{r.id}/cotar')
    assert resp.status_code == 400
