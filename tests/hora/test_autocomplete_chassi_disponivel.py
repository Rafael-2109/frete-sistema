"""Frente C (2026-06-03): autocomplete de chassi com filtro de disponibilidade.

`autocomplete_service.chassis` ganhou os parametros `disponivel`, `modelo_id` e
`cor`. Com `disponivel=True`, restringe a chassis cujo ULTIMO evento esta em
EVENTOS_EM_ESTOQUE (mesmo criterio do estoque_service) — usado pela tela de
Pedido de Venda, onde so chassis em estoque podem ser vendidos. O JSON passa a
incluir `modelo_id` (para o front preencher o filtro de modelo ao escolher).

Testes auto-contidos (memoria gotcha_testes_hora_residuo): loja via
`loja_factory` (CNPJ unico) e modelo com nome unico — nada de identificadores
fixos que colidem com residuo. A fixture `db` (begin_nested + rollback) reverte
tudo no teardown; `registrar_evento`/`get_or_create_moto` so fazem flush.
"""
from __future__ import annotations

import uuid

from app import db as _db
from app.hora.models import HoraModelo
from app.hora.services import autocomplete_service
from app.hora.services.moto_service import get_or_create_moto, registrar_evento


def _novo_modelo(nome=None):
    nome = nome or ('MOD-AUTOC-' + uuid.uuid4().hex[:8].upper())
    m = HoraModelo(nome_modelo=nome, ativo=True)
    _db.session.add(m)
    _db.session.flush()
    return m


def _moto_com_eventos(modelo_nome, loja_id, *tipos, cor='PRETA'):
    """Cria uma moto com chassi unico (prefixo AUTOC) e registra os eventos."""
    chassi = ('AUTOC' + uuid.uuid4().hex).upper()[:25]
    get_or_create_moto(
        numero_chassi=chassi, modelo_nome=modelo_nome, cor=cor, criado_por='t',
    )
    for tipo in tipos:
        registrar_evento(
            numero_chassi=chassi, tipo=tipo, loja_id=loja_id, operador='t',
        )
    _db.session.flush()
    return chassi


def test_chassis_disponivel_exclui_vendidos(db, loja_factory):
    """disponivel=True retorna so chassis com ultimo evento em estoque."""
    loja = loja_factory()
    modelo = _novo_modelo()
    em_estoque = _moto_com_eventos(modelo.nome_modelo, loja.id, 'RECEBIDA', 'CONFERIDA')
    vendida = _moto_com_eventos(modelo.nome_modelo, loja.id, 'RECEBIDA', 'CONFERIDA', 'VENDIDA')

    res = autocomplete_service.chassis(
        q='AUTOC', lojas_permitidas_ids=None, disponivel=True,
    )
    chassis = {r['chassi'] for r in res}
    assert em_estoque in chassis
    assert vendida not in chassis


def test_chassis_inclui_modelo_id_no_json(db, loja_factory):
    loja = loja_factory()
    modelo = _novo_modelo()
    em_estoque = _moto_com_eventos(modelo.nome_modelo, loja.id, 'RECEBIDA', 'CONFERIDA')
    res = autocomplete_service.chassis(
        q='AUTOC', lojas_permitidas_ids=None, disponivel=True,
    )
    alvo = [r for r in res if r['chassi'] == em_estoque]
    assert alvo, 'chassi em estoque nao retornado'
    assert 'modelo_id' in alvo[0]
    assert 'modelo' in alvo[0]
    assert 'cor' in alvo[0]
    assert alvo[0]['modelo_id'] == modelo.id


def test_chassis_filtra_por_modelo_id(db, loja_factory):
    """modelo_id restringe ao modelo informado."""
    loja = loja_factory()
    modelo_a = _novo_modelo()
    modelo_b = _novo_modelo()
    do_a = _moto_com_eventos(modelo_a.nome_modelo, loja.id, 'RECEBIDA', 'CONFERIDA')
    do_b = _moto_com_eventos(modelo_b.nome_modelo, loja.id, 'RECEBIDA', 'CONFERIDA')

    res = autocomplete_service.chassis(
        q='AUTOC', lojas_permitidas_ids=None, disponivel=True, modelo_id=modelo_a.id,
    )
    chassis = {r['chassi'] for r in res}
    assert do_a in chassis
    assert do_b not in chassis


def test_chassis_sem_disponivel_inclui_vendido(db, loja_factory):
    """Default (disponivel=False) retorna qualquer chassi por substring."""
    loja = loja_factory()
    modelo = _novo_modelo()
    vendida = _moto_com_eventos(modelo.nome_modelo, loja.id, 'RECEBIDA', 'CONFERIDA', 'VENDIDA')
    res = autocomplete_service.chassis(q='AUTOC', lojas_permitidas_ids=None)
    assert vendida in {r['chassi'] for r in res}
