import uuid
from decimal import Decimal

import pytest
from app import db
from app.motos_assai.models import AssaiEstoqueMovimento, MOVIMENTO_ENTRADA, MOVIMENTO_DESCARTE
from app.motos_assai.services.peca_service import criar_peca
from app.motos_assai.services.movimento_service import (
    registrar_entrada, saldo, custo_medio, descartar, ajustar, EstoqueError,
)


def _nome():
    return f'PECA_{uuid.uuid4().hex[:8].upper()}'


def _peca(admin_user, custo_referencia=None):
    return criar_peca(nome=_nome(), custo_referencia=custo_referencia, operador_id=admin_user.id)


def test_entrada_soma_saldo_e_custo(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        registrar_entrada(peca_id=p.id, quantidade=10, custo_unitario='5.00', operador_id=admin_user.id)
        registrar_entrada(peca_id=p.id, quantidade=10, custo_unitario='7.00', operador_id=admin_user.id)
        assert saldo(p.id) == Decimal('20.000')
        assert custo_medio(p.id) == Decimal('6.0000')
        db.session.rollback()


def test_entrada_grava_linha_e_custo_total(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        mov = registrar_entrada(peca_id=p.id, quantidade=3, custo_unitario='4.00', operador_id=admin_user.id)
        assert mov.tipo == MOVIMENTO_ENTRADA
        assert mov.delta_almoxarifado == Decimal('3.000')
        assert mov.custo_total == Decimal('12.00')
        db.session.rollback()


def test_custo_medio_fallback_para_referencia(app, admin_user):
    with app.app_context():
        p = _peca(admin_user, custo_referencia='9.50')
        assert custo_medio(p.id) == Decimal('9.5000')
        db.session.rollback()


def test_custo_medio_zero_sem_dados(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        assert custo_medio(p.id) == Decimal('0')
        db.session.rollback()


def test_descartar_de_estoque_baixa_saldo(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        registrar_entrada(peca_id=p.id, quantidade=5, custo_unitario='2.00', operador_id=admin_user.id)
        d = descartar(peca_id=p.id, quantidade=2, operador_id=admin_user.id)
        assert d.tipo == MOVIMENTO_DESCARTE
        assert d.delta_almoxarifado == Decimal('-2.000')
        assert saldo(p.id) == Decimal('3.000')
        db.session.rollback()


def test_descartar_de_moto_nao_mexe_saldo(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        registrar_entrada(peca_id=p.id, quantidade=5, custo_unitario='2.00', operador_id=admin_user.id)
        d = descartar(peca_id=p.id, quantidade=1, operador_id=admin_user.id, chassi_origem='TST_X')
        assert d.delta_almoxarifado == Decimal('0.000')
        assert saldo(p.id) == Decimal('5.000')
        db.session.rollback()


def test_ajustar_positivo_e_negativo(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        ajustar(peca_id=p.id, delta=4, operador_id=admin_user.id, motivo='Contagem fisica')
        assert saldo(p.id) == Decimal('4.000')
        ajustar(peca_id=p.id, delta=-1, operador_id=admin_user.id, motivo='Correcao')
        assert saldo(p.id) == Decimal('3.000')
        db.session.rollback()


def test_entrada_quantidade_invalida_falha(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        with pytest.raises(EstoqueError):
            registrar_entrada(peca_id=p.id, quantidade=0, custo_unitario='1.00', operador_id=admin_user.id)
        db.session.rollback()
