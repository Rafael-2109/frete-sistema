"""P3: Cotar Frete pelo mapa deve incluir lotes CarVia.

Causa-raiz do bug: o endpoint convertia num_pedido -> separacao_lote_id via
tabela `separacao`, mas pedidos CarVia NAO tem registro em Separacao, entao
seus lotes (CARVIA-*) desapareciam e nunca entravam na cotacao. O fix faz o
front enviar os proprios separacao_lote_id (NACOM + CarVia) e o backend aceitar
`lotes` direto, mantendo `pedidos` (num_pedido) como fallback legado.
"""
import json


def _post_cotar(client, payload):
    return client.post('/carteira/mapa/api/cotar-frete',
                        data=json.dumps(payload),
                        content_type='application/json')


def test_cotar_frete_mapa_preserva_lotes_carvia(client, db):
    """Enviando lotes direto, NACOM + CarVia chegam intactos a sessao de cotacao."""
    lotes = ['CARVIA-PED-99', 'LOTE_20260101_000000_001']
    r = _post_cotar(client, {'lotes': lotes})
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body['sucesso'] is True
    assert set(body['lotes']) == set(lotes)
    assert body['total_lotes'] == 2
    with client.session_transaction() as sess:
        assert 'CARVIA-PED-99' in sess['cotacao_lotes']  # CarVia NAO foi perdido
        assert sess['cotacao_pedidos'] == sess['cotacao_lotes']  # retrocompat


def test_cotar_frete_mapa_dedupe_preserva_ordem(client, db):
    """Lotes repetidos/vazios sao limpos preservando a ordem da selecao."""
    r = _post_cotar(client, {'lotes': ['A', 'A', 'B', '', None]})
    assert r.status_code == 200
    assert r.get_json()['lotes'] == ['A', 'B']


def test_cotar_frete_mapa_vazio_400(client, db):
    r = _post_cotar(client, {})
    assert r.status_code == 400


def test_cotar_frete_mapa_legado_pedidos_via_separacao(client, db):
    """Retrocompat: sem `lotes`, resolve num_pedido -> separacao_lote_id (so Nacom)."""
    from app.separacao.models import Separacao
    sep = Separacao(
        separacao_lote_id='LOTE_TEST_LEGADO_1',
        num_pedido='PEDLEGADO1',
        cod_uf='SP',
        sincronizado_nf=False,
    )
    db.session.add(sep)
    db.session.commit()

    r = _post_cotar(client, {'pedidos': ['PEDLEGADO1']})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()['lotes'] == ['LOTE_TEST_LEGADO_1']
