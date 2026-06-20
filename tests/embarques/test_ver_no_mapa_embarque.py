"""P2 — botao "Ver no Mapa" no hub do embarque (visualizar_embarque).

O botao leva os separacao_lote_id dos itens ATIVOS do embarque (NACOM + CarVia)
para /carteira/mapa/visualizar?lotes[]=...  O mapa ja distingue CarVia pelo
prefixo CARVIA- no lote.
"""
import uuid
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse, parse_qs

from sqlalchemy import text

from app.utils.local_cd import LOCAL_CD_VICTORIO_MARCHEZINE, LOCAL_CD_TENENTE_MARQUES


def _user():
    u = MagicMock()
    u.is_authenticated = True
    u.nome = 'Operador Teste'
    return u


def test_url_for_mapa_gera_lotes_repetidos(app):
    """url_for com **{'lotes[]': lista} gera ?lotes[]=A&lotes[]=B (casa com getlist)."""
    from flask import url_for
    with app.test_request_context():
        url = url_for('mapa.visualizar_mapa', **{'lotes[]': ['LOTE_A', 'CARVIA-PED-7']})
    assert urlparse(url).path == '/carteira/mapa/visualizar'
    assert parse_qs(urlparse(url).query)['lotes[]'] == ['LOTE_A', 'CARVIA-PED-7']


def test_botao_ver_no_mapa_renderiza_com_lotes(db, client):
    """A pagina do embarque mostra o botao e o link com os lotes ativos (NACOM + CarVia)."""
    suf = uuid.uuid4().hex[:8]
    lote_nacom = f'LOTE-NACOM-{suf}'
    lote_carvia = f'CARVIA-PED-{suf}'
    numero = (db.session.execute(
        text("SELECT COALESCE(MAX(numero), 0) FROM embarques")).scalar() or 0) + 1
    eid = db.session.execute(text("""
        INSERT INTO embarques (numero, status, criado_em, criado_por, tipo_carga, tipo_cotacao)
        VALUES (:n, 'ativo', NOW(), 'test', 'FRACIONADA', 'FRACIONADA') RETURNING id
    """), {'n': numero}).scalar()
    for lote, local in ((lote_nacom, LOCAL_CD_VICTORIO_MARCHEZINE),
                        (lote_carvia, LOCAL_CD_TENENTE_MARQUES)):
        db.session.execute(text("""
            INSERT INTO embarque_itens
                (embarque_id, separacao_lote_id, local_cd, cliente, pedido, uf_destino, cidade_destino, status)
            VALUES (:eid, :lote, :local, :cli, :ped, 'SP', 'Sao Paulo', 'ativo')
        """), {'eid': eid, 'lote': lote, 'local': local,
               'cli': f'CLI-{suf}', 'ped': f'PED-{suf}'})
    db.session.commit()

    with patch('flask_login.utils._get_user', return_value=_user()):
        resp = client.get(f'/embarques/{eid}')
    assert resp.status_code == 200, resp.status_code
    html = resp.get_data(as_text=True)

    assert 'Ver no Mapa' in html
    # Ambos os lotes (NACOM + CarVia) vao na querystring (lotes[] URL-encoded = lotes%5B%5D)
    assert f'lotes%5B%5D={lote_nacom}' in html
    assert f'lotes%5B%5D={lote_carvia}' in html
