"""Filtro status_portaria da listagem deve classificar embarque misto pelo
estado agregado por CD (PARCIAL), nao pelo registro de maior id.

Padrão de auth: igual a tests/embarques/test_listar_filtro_local_cd.py:
- `app.config['LOGIN_DISABLED'] = True` (setado no conftest)
- patch 'flask_login.utils._get_user' com MagicMock que retorna usuário
  com pode_acessar_embarques() == True e perfil != 'vendedor'.
- Contexto de BD capturado via signal `template_rendered` para inspecionar
  a lista `embarques` passada ao template (mais robusto que parse de HTML).
"""
import uuid
from contextlib import contextmanager
from datetime import date, time
from unittest.mock import MagicMock, patch

from flask import template_rendered
from sqlalchemy import text

from app.portaria.models import ControlePortaria
from app.utils.local_cd import (
    LOCAL_CD_VICTORIO_MARCHEZINE as VM,
    LOCAL_CD_TENENTE_MARQUES as TM,
)


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _user():
    u = MagicMock()
    u.is_authenticated = True
    u.pode_acessar_embarques = lambda: True
    u.perfil = 'logistica'
    u.perfil_nome = 'Logistica'
    return u


@contextmanager
def _capturar_contexto(app):
    capturado = {}

    def _record(sender, template, context, **extra):
        capturado['template'] = template.name
        capturado['context'] = context

    template_rendered.connect(_record, app)
    try:
        yield capturado
    finally:
        template_rendered.disconnect(_record, app)


# ---------------------------------------------------------------------------
# Helpers de fixture de BD
# ---------------------------------------------------------------------------

def _novo_embarque_topo(db):
    """Embarque ativo COM numero no topo (MAX+1) → 1ª página da listagem desc."""
    numero = (db.session.execute(
        text("SELECT COALESCE(MAX(numero), 0) FROM embarques")).scalar() or 0) + 1
    eid = db.session.execute(text("""
        INSERT INTO embarques (numero, status, criado_em, criado_por, tipo_carga,
                               tipo_cotacao, data_embarque)
        VALUES (:n, 'ativo', NOW(), 'test', 'FRACIONADA', 'FRACIONADA', :de)
        RETURNING id
    """), {'n': numero, 'de': date(2026, 1, 10)}).scalar()
    return eid, numero


def _item(db, eid, local_cd, suf):
    db.session.execute(text("""
        INSERT INTO embarque_itens
            (embarque_id, separacao_lote_id, local_cd, cliente, pedido,
             uf_destino, cidade_destino, status)
        VALUES (:eid, :lote, :local, 'Cliente', :ped, 'SP', 'Sao Paulo', 'ativo')
    """), {'eid': eid, 'lote': f'LOTE-{suf}', 'local': local_cd, 'ped': f'P-{suf}'})


def _motorista(db, suf):
    """Cria motorista com CPF único."""
    # CPF no formato XXX.XXX.XXX-XX usando os primeiros 9 dígitos do suf (hex)
    digits = ''.join(c for c in suf if c.isdigit())[:9].ljust(9, '0')
    cpf = f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-00'
    mid = db.session.execute(text("""
        INSERT INTO motoristas (nome_completo, rg, cpf, telefone)
        VALUES (:n, :rg, :cpf, '(11) 90000-0000') RETURNING id
    """), {'n': f'Mot-{suf}', 'rg': f'RG{suf}', 'cpf': cpf}).scalar()
    return mid


def _emb_misto_parcial(db):
    """Embarque misto: item VM (dentro) + item TM (saiu). Status agregado = PARCIAL.

    Bug do código antigo (max id): TM saiu e tem id MAIOR, então max(id)=TM
    que tem data_saida preenchida → o embarque era INCORRETAMENTE classificado
    como SAIU no filtro SQL antigo, aparecendo no filtro SAIU quando deveria
    aparecer em PARCIAL (VM ainda está dentro).

    Novo código: `status_portaria_agregado` detecta que VM=DENTRO, TM=SAIU →
    PARCIAL. Deve aparecer em PARCIAL e NÃO aparecer em SAIU.
    """
    suf = uuid.uuid4().hex[:8]
    eid, numero = _novo_embarque_topo(db)

    _item(db, eid, VM, f'{suf}vm')
    _item(db, eid, TM, f'{suf}tm')

    mid = _motorista(db, suf)

    # VM ainda dentro (inserido primeiro → id menor)
    vm_reg = ControlePortaria(
        motorista_id=mid, placa='ABC-1234', embarque_id=eid, local_cd=VM,
        tipo_carga='Entrega', empresa='CD',
        data_chegada=date(2026, 1, 10), hora_chegada=time(8, 0),
        data_entrada=date(2026, 1, 10), hora_entrada=time(9, 0),
    )
    db.session.add(vm_reg)
    db.session.flush()

    # TM saiu (inserido depois → id MAIOR; max(id) daria SAIU no código antigo)
    tm_reg = ControlePortaria(
        motorista_id=mid, placa='ABC-1234', embarque_id=eid, local_cd=TM,
        tipo_carga='Entrega', empresa='CD',
        data_chegada=date(2026, 1, 10), hora_chegada=time(8, 0),
        data_entrada=date(2026, 1, 10), hora_entrada=time(9, 0),
        data_saida=date(2026, 1, 10), hora_saida=time(17, 0),
    )
    db.session.add(tm_reg)
    db.session.commit()

    return eid, numero


def _ids_da_listagem(client, app, query_string):
    with _capturar_contexto(app) as cap:
        with patch('flask_login.utils._get_user', return_value=_user()):
            resp = client.get(query_string)
        assert resp.status_code == 200, f'HTTP {resp.status_code}'
        return {e.id for e in cap['context'].get('embarques', [])}


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

def test_filtro_parcial_lista_embarque_misto(db, client, app):
    """Embarque misto (VM saiu, TM dentro) DEVE aparecer no filtro PARCIAL."""
    eid, _ = _emb_misto_parcial(db)
    ids = _ids_da_listagem(
        client, app,
        '/embarques/listar_embarques?mostrar_todos=true&status_portaria=PARCIAL',
    )
    assert eid in ids, (
        f'Embarque {eid} com status_portaria=PARCIAL deveria aparecer no filtro PARCIAL, '
        f'mas não apareceu. IDs encontrados: {ids}'
    )


def test_filtro_saiu_nao_lista_misto_parcial(db, client, app):
    """Embarque misto com saída parcial NÃO deve aparecer no filtro SAIU."""
    eid, _ = _emb_misto_parcial(db)
    ids = _ids_da_listagem(
        client, app,
        '/embarques/listar_embarques?mostrar_todos=true&status_portaria=SAIU',
    )
    assert eid not in ids, (
        f'Embarque {eid} com status_portaria=PARCIAL NÃO deveria aparecer no filtro SAIU, '
        f'mas apareceu. IDs encontrados: {ids}'
    )
