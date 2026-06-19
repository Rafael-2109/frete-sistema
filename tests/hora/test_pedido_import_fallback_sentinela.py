"""Fix B: import de pedido com modelo desconhecido NAO deixa o pedido sem itens.

Antes: `criar_pedido` chamava get_or_create_moto sem fallback_sentinela; no 1o
modelo nao-reconhecido levantava ModeloPendenteError, abortando os itens — e o
header (ja flushado) vazava no commit do proximo pedido do batch, ficando com 0
itens (bug dos pedidos 119/124/125/126).

Agora: fallback_sentinela=True cria a moto no sentinela DESCONHECIDO + registra a
pendencia + grava modelo_texto_original; ao resolver a pendencia, a retroatividade
corrige item e moto sem edicao manual.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func

from app import db as _db
from app.hora.models import (
    HoraModelo,
    HoraModeloPendente,
    HoraMoto,
    HoraPedido,
    HoraPedidoItem,
)
from app.hora.services import pedido_service
from app.hora.services.modelo_retroatividade_service import propagar_resolucao


_DEL = """
    DELETE FROM hora_pedido_item WHERE numero_chassi LIKE 'ZZFIXB%'
        OR pedido_id IN (SELECT id FROM hora_pedido WHERE numero_pedido LIKE 'FIXB-%');
    DELETE FROM hora_pedido WHERE numero_pedido LIKE 'FIXB-%';
    DELETE FROM hora_moto_evento WHERE numero_chassi LIKE 'ZZFIXB%';
    DELETE FROM hora_moto WHERE numero_chassi LIKE 'ZZFIXB%';
    DELETE FROM hora_modelo_pendente WHERE nome_observado LIKE 'MODELO-INEXISTENTE-FIXB%';
    DELETE FROM hora_modelo WHERE nome_modelo LIKE 'CANONICO-FIXB%';
"""


@pytest.fixture(autouse=True)
def _cleanup_fixb(db):
    # Services commitam (escapam o savepoint do fixture `db`) — limpa por
    # prefixo determinista antes e depois.
    _db.session.execute(_db.text(_DEL))
    _db.session.commit()
    yield
    _db.session.execute(_db.text(_DEL))
    _db.session.commit()


def _criar_pedido(loja, numero, chassi, nome_modelo):
    return pedido_service.criar_pedido(
        numero_pedido=numero,
        cnpj_destino=loja.cnpj,
        data_pedido=date.today(),
        loja_destino_id=loja.id,
        itens=[{
            'numero_chassi': chassi,
            'modelo': nome_modelo,
            'cor': 'PRETO',
            'preco_compra_esperado': Decimal('5000'),
        }],
        origem='XLSX',
    )


def test_import_modelo_desconhecido_cria_pedido_com_itens(db, loja_destino):
    nome_modelo = 'MODELO-INEXISTENTE-FIXB-XYZ'
    chassi = 'ZZFIXB0001'

    pedido = _criar_pedido(loja_destino, 'FIXB-PED-0001', chassi, nome_modelo)

    pedido = HoraPedido.query.get(pedido.id)
    assert len(pedido.itens) == 1                      # NAO ficou orfao
    item = pedido.itens[0]
    assert item.numero_chassi == chassi
    assert item.modelo_texto_original == nome_modelo

    sentinela = HoraModelo.query.filter_by(nome_modelo='DESCONHECIDO').first()
    assert sentinela is not None
    assert item.modelo_id == sentinela.id              # item no sentinela
    moto = HoraMoto.query.get(chassi)
    assert moto is not None and moto.modelo_id == sentinela.id

    pend = (
        HoraModeloPendente.query
        .filter(func.upper(HoraModeloPendente.nome_observado) == nome_modelo.upper())
        .first()
    )
    assert pend is not None                            # pendencia registrada


def test_resolver_pendencia_faz_moto_aparecer_no_pedido(db, loja_destino):
    nome_modelo = 'MODELO-INEXISTENTE-FIXB-ABC'
    chassi = 'ZZFIXB0002'
    _criar_pedido(loja_destino, 'FIXB-PED-0002', chassi, nome_modelo)

    canonico = HoraModelo(nome_modelo='CANONICO-FIXB-ABC', ativo=True)
    _db.session.add(canonico)
    _db.session.flush()

    res = propagar_resolucao(nome_modelo, canonico.id)
    _db.session.commit()

    assert res['pedido_itens_atualizados'] >= 1
    assert res['motos_atualizadas'] >= 1

    item = HoraPedidoItem.query.filter_by(numero_chassi=chassi).first()
    assert item.modelo_id == canonico.id               # apareceu no pedido
    moto = HoraMoto.query.get(chassi)
    assert moto.modelo_id == canonico.id               # identidade corrigida


def test_idempotente_resolver_duas_vezes(db, loja_destino):
    nome_modelo = 'MODELO-INEXISTENTE-FIXB-DEF'
    chassi = 'ZZFIXB0003'
    _criar_pedido(loja_destino, 'FIXB-PED-0003', chassi, nome_modelo)

    canonico = HoraModelo(nome_modelo='CANONICO-FIXB-DEF', ativo=True)
    _db.session.add(canonico)
    _db.session.flush()

    propagar_resolucao(nome_modelo, canonico.id)
    _db.session.commit()
    res2 = propagar_resolucao(nome_modelo, canonico.id)  # 2a vez: nada a fazer
    _db.session.commit()

    assert res2['pedido_itens_atualizados'] == 0
    assert res2['motos_atualizadas'] == 0
    item = HoraPedidoItem.query.filter_by(numero_chassi=chassi).first()
    assert item.modelo_id == canonico.id
