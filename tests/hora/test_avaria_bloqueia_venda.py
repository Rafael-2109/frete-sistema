"""Regra (2026-06-28): moto com avaria ABERTA fica NAO-VENDAVEL — bloqueia a
reserva (_lock_chassi_e_validar_disponivel) e a confirmacao; volta ao vendavel
quando a ULTIMA avaria aberta e resolvida ou ignorada.

Fonte de verdade da vendabilidade: avaria_service.avarias_abertas_por_chassi
(HoraAvaria status='ABERTA') — NAO o tipo do ultimo evento (AVARIADA segue em
EVENTOS_EM_ESTOQUE para a moto continuar aparecendo no estoque).
"""
import pytest

from app import db as _db
from app.hora.services import avaria_service, venda_service
from app.hora.services.venda_service import ChassiIndisponivelError


def _avaria(chassi, loja, desc='dano que bloqueia a venda'):
    a = avaria_service.registrar_avaria(
        numero_chassi=chassi, descricao=desc, fotos=[], usuario='x', loja_id=loja.id)
    _db.session.flush()
    return a


def test_avaria_aberta_bloqueia_reserva(db, chassi_em_estoque, loja_origem):
    _avaria(chassi_em_estoque, loja_origem)
    with pytest.raises(ChassiIndisponivelError, match=r'(?i)avaria'):
        venda_service._lock_chassi_e_validar_disponivel(chassi_em_estoque)


def test_resolver_libera_reserva(db, chassi_em_estoque, loja_origem):
    a = _avaria(chassi_em_estoque, loja_origem)
    with pytest.raises(ChassiIndisponivelError):
        venda_service._lock_chassi_e_validar_disponivel(chassi_em_estoque)
    avaria_service.resolver_avaria(a.id, 'consertada na oficina', 'chefe')
    _db.session.flush()
    moto, _ult = venda_service._lock_chassi_e_validar_disponivel(chassi_em_estoque)
    assert moto.numero_chassi == chassi_em_estoque


def test_ignorar_libera_reserva(db, chassi_em_estoque, loja_origem):
    a = _avaria(chassi_em_estoque, loja_origem)
    avaria_service.ignorar_avaria(a.id, 'dano pre-existente aceitavel', 'chefe')
    _db.session.flush()
    moto, _ult = venda_service._lock_chassi_e_validar_disponivel(chassi_em_estoque)
    assert moto.numero_chassi == chassi_em_estoque


def test_multi_avaria_so_libera_quando_todas_finalizadas(db, chassi_em_estoque, loja_origem):
    a1 = _avaria(chassi_em_estoque, loja_origem, 'primeiro dano aqui')
    a2 = _avaria(chassi_em_estoque, loja_origem, 'segundo dano aqui')
    avaria_service.resolver_avaria(a1.id, 'consertou o primeiro', 'chefe')
    _db.session.flush()
    with pytest.raises(ChassiIndisponivelError):
        venda_service._lock_chassi_e_validar_disponivel(chassi_em_estoque)
    avaria_service.resolver_avaria(a2.id, 'consertou o segundo', 'chefe')
    _db.session.flush()
    moto, _ult = venda_service._lock_chassi_e_validar_disponivel(chassi_em_estoque)
    assert moto.numero_chassi == chassi_em_estoque
