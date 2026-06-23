"""Regressao 500 em `embarques.listar_embarques` no MODO PENDENTES (default).

Bug 2026-06-23: o helper `ControlePortaria.embarques_com_saida_pendente_query`
tem subqueries (`item_cd_pendente`, `tem_item_do_local`) com EmbarqueItem no
proprio FROM. A rota faz `.outerjoin(EmbarqueItem)` + `.paginate()`; sem
`.correlate(Embarque)` nessas subqueries, a auto-correlacao do SQLAlchemy
arrastava o EmbarqueItem para o FROM externo, deixando a subquery "sem FROM" →
`InvalidRequestError` no paginate (HTTP 500).

Diferenca dos testes vizinhos: estes exercitam `mostrar_todos=true` (que NAO
passa pelo helper). O bug so aparece no pre-filtro de pendentes (default) — por
isso passava despercebido. Aqui batemos no caminho default, com e sem `?local_cd=`.

Padrao de auth/captura: igual a tests/embarques/test_listar_filtro_portaria.py.
"""
import uuid

import pytest
from sqlalchemy import text
from unittest.mock import MagicMock, patch

from app.utils.local_cd import (
    LOCAL_CD_VICTORIO_MARCHEZINE as VM,
    LOCAL_CD_TENENTE_MARQUES as TM,
)


def _user():
    u = MagicMock()
    u.is_authenticated = True
    u.pode_acessar_embarques = lambda: True
    u.perfil = 'logistica'
    u.perfil_nome = 'Logistica'
    return u


def _embarque_pendente_com_item(db, local_cd):
    """Embarque ativo SEM data_embarque (pendente puro) + 1 item ativo do CD."""
    numero = (db.session.execute(
        text("SELECT COALESCE(MAX(numero), 0) FROM embarques")).scalar() or 0) + 1
    eid = db.session.execute(text("""
        INSERT INTO embarques (numero, status, criado_em, criado_por, tipo_carga, tipo_cotacao)
        VALUES (:n, 'ativo', NOW(), 'test', 'FRACIONADA', 'FRACIONADA')
        RETURNING id
    """), {'n': numero}).scalar()
    suf = uuid.uuid4().hex[:8]
    db.session.execute(text("""
        INSERT INTO embarque_itens
            (embarque_id, separacao_lote_id, local_cd, cliente, pedido,
             uf_destino, cidade_destino, status)
        VALUES (:eid, :lote, :local, 'Cliente', :ped, 'SP', 'Sao Paulo', 'ativo')
    """), {'eid': eid, 'lote': f'LOTE-{suf}', 'local': local_cd, 'ped': f'P-{suf}'})
    db.session.commit()
    return eid


def _get(client, query_string):
    with patch('flask_login.utils._get_user', return_value=_user()):
        return client.get(query_string)


@pytest.mark.parametrize('query_string', [
    '/embarques/listar_embarques',                                # pendentes default
    f'/embarques/listar_embarques?local_cd={VM}',                 # ramo `if local` (VM)
    f'/embarques/listar_embarques?local_cd={TM}',                 # ramo `if local` (TM)
])
def test_listar_pendentes_nao_estoura_500(db, client, query_string):
    """O pre-filtro de pendentes (com/sem ?local_cd=) deve compilar e paginar (200)."""
    _embarque_pendente_com_item(db, VM)
    _embarque_pendente_com_item(db, TM)
    resp = _get(client, query_string)
    assert resp.status_code == 200, (
        f'{query_string} retornou {resp.status_code} (esperado 200). '
        f'Regressao do auto-correlate no paginate.'
    )
