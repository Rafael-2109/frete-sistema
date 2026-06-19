"""Regressao: links de impressao nos pop-ups NAO podem usar data-bs-dismiss="modal".

Bug (commit 49dbb9c6a): ao mover os links de impressao para dentro dos modais
"Imprimir Completo"/"Imprimir Capa", cada <a> ganhou data-bs-dismiss="modal".
No Bootstrap 5.3 o handler de dismiss chama event.preventDefault() em elementos
<a>/<area>, o que cancela o target="_blank" — o modal fecha mas a impressao
nunca abre. O modal deve ser fechado via API JS, e o <a> deve navegar nativamente.
"""
import re
import uuid
from unittest.mock import patch, MagicMock

from sqlalchemy import text

from app.utils.local_cd import LOCAL_CD_VICTORIO_MARCHEZINE, LOCAL_CD_TENENTE_MARQUES


def _user():
    u = MagicMock()
    u.is_authenticated = True
    u.nome = 'Operador Teste'
    u.perfil = 'admin'
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


def test_links_impressao_nao_usam_data_bs_dismiss(db, client):
    suf = uuid.uuid4().hex[:8]
    eid = _embarque_com_2_itens(db, suf)
    with patch('flask_login.utils._get_user', return_value=_user()):
        resp = client.get(f'/embarques/{eid}')
    assert resp.status_code == 200, resp.status_code
    html = resp.get_data(as_text=True)

    # Todos os <a> que apontam para rotas de impressao (imprimir_embarque e
    # imprimir_embarque_completo). [^>] casa newline -> pega tags multi-linha.
    links = re.findall(r'<a\b[^>]*\bhref="[^"]*imprimir_embarque[^"]*"[^>]*>', html)
    assert links, 'deveria haver links de impressao renderizados nos pop-ups'

    for a in links:
        assert 'data-bs-dismiss' not in a, (
            'link de impressao NAO pode ter data-bs-dismiss '
            f'(Bootstrap 5 cancela o target="_blank"): {a}')
        assert 'target="_blank"' in a, f'link de impressao deve abrir em nova aba: {a}'
