"""Frente B — impressao do embarque por filial (decisao Rafael 2026-06-18).

`GET /embarques/<id>/imprimir_embarque?local_cd=TENENTE_MARQUES` (e imprimir_completo):
a pagina/capa se mantem, mas a LISTAGEM de itens imprime APENAS os EmbarqueItem da
filial. Sem o parametro, imprime todos (comportamento atual).
"""
import uuid
from unittest.mock import patch, MagicMock

from sqlalchemy import text

from app.utils.local_cd import LOCAL_CD_VICTORIO_MARCHEZINE, LOCAL_CD_TENENTE_MARQUES


def _user():
    u = MagicMock()
    u.is_authenticated = True
    u.nome = 'Operador Teste'
    return u


def _embarque_com_2_itens(db, suf):
    numero = (db.session.execute(
        text("SELECT COALESCE(MAX(numero), 0) FROM embarques")).scalar() or 0) + 1
    eid = db.session.execute(text("""
        INSERT INTO embarques (numero, status, criado_em, criado_por, tipo_carga, tipo_cotacao)
        VALUES (:n, 'ativo', NOW(), 'test', 'FRACIONADA', 'FRACIONADA') RETURNING id
    """), {'n': numero}).scalar()
    for local, tag in ((LOCAL_CD_VICTORIO_MARCHEZINE, 'VM'), (LOCAL_CD_TENENTE_MARQUES, 'TM')):
        db.session.execute(text("""
            INSERT INTO embarque_itens
                (embarque_id, separacao_lote_id, local_cd, cliente, pedido, uf_destino, cidade_destino, status)
            VALUES (:eid, :lote, :local, :cli, :ped, 'SP', 'Sao Paulo', 'ativo')
        """), {'eid': eid, 'lote': f'LOTE-{tag}-{suf}', 'local': local,
               'cli': f'CLI{tag}{suf}', 'ped': f'PED{tag}{suf}'})
    db.session.commit()
    return eid


def _html_impressao(client, eid, query=''):
    with patch('flask_login.utils._get_user', return_value=_user()):
        resp = client.get(f'/embarques/{eid}/imprimir_embarque{query}')
    assert resp.status_code == 200, resp.status_code
    return resp.get_data(as_text=True)


def test_imprime_so_itens_da_filial_tm(db, client):
    suf = uuid.uuid4().hex[:8]
    eid = _embarque_com_2_itens(db, suf)
    html = _html_impressao(client, eid, '?local_cd=TENENTE_MARQUES')
    assert f'CLITM{suf}' in html, 'item TM deveria ser impresso'
    assert f'CLIVM{suf}' not in html, 'item VM NAO deveria ser impresso no contexto TM'


def test_imprime_so_itens_da_filial_vm(db, client):
    suf = uuid.uuid4().hex[:8]
    eid = _embarque_com_2_itens(db, suf)
    html = _html_impressao(client, eid, '?local_cd=VICTORIO_MARCHEZINE')
    assert f'CLIVM{suf}' in html
    assert f'CLITM{suf}' not in html


def test_sem_filtro_imprime_todos(db, client):
    suf = uuid.uuid4().hex[:8]
    eid = _embarque_com_2_itens(db, suf)
    html = _html_impressao(client, eid)
    assert f'CLIVM{suf}' in html and f'CLITM{suf}' in html
