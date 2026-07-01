# tests/motos_assai/test_resolucao_service.py
import uuid
from decimal import Decimal
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo,
    PENDENCIA_TRATATIVA_CONSERTAR, PENDENCIA_TRATATIVA_USAR_ESTOQUE,
    PENDENCIA_TRATATIVA_USAR_OUTRA_MOTO,
    PENDENCIA_CATEGORIA_AVARIA, PENDENCIA_CATEGORIA_FALTA_PECA,
    PENDENCIA_ORIGEM_GALPAO, EVENTO_MONTADA,
)
from app.motos_assai.services.peca_service import criar_peca
from app.motos_assai.services.movimento_service import registrar_entrada, saldo
from app.motos_assai.services.pendencia_service import abrir_pendencia
from app.motos_assai.services.moto_evento_service import status_efetivo
from app.motos_assai.services.resolucao_service import resolver_com_tratativa, ResolucaoError


def _moto(chassi, admin_user):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()


def _uid(p): return f'{p}{uuid.uuid4().hex[:6].upper()}'


def test_consertar_sem_movimento_monta(app, admin_user):
    with app.app_context():
        chassi = _uid('TSTA')
        _moto(chassi, admin_user)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_AVARIA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='fio solto',
                            operador_id=admin_user.id)
        r = resolver_com_tratativa(pendencia_id=f.id, tratativa=PENDENCIA_TRATATIVA_CONSERTAR,
                                   resolucao_descricao='soldado', operador_id=admin_user.id)
        db.session.flush()
        assert r['ok'] and r['montou'] is True
        assert status_efetivo(chassi) == EVENTO_MONTADA
        db.session.rollback()


def test_usar_estoque_consome_e_monta(app, admin_user):
    with app.app_context():
        chassi = _uid('TSTB')
        _moto(chassi, admin_user)
        p = criar_peca(nome=_uid('PZ'), operador_id=admin_user.id)
        registrar_entrada(peca_id=p.id, quantidade=5, custo_unitario='10.00', operador_id=admin_user.id)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='falta peca',
                            operador_id=admin_user.id)
        r = resolver_com_tratativa(pendencia_id=f.id, tratativa=PENDENCIA_TRATATIVA_USAR_ESTOQUE,
                                   resolucao_descricao='aplicada', operador_id=admin_user.id,
                                   peca_id=p.id, quantidade=1)
        db.session.flush()
        assert r['saldo_apos'] == Decimal('4.000')
        assert saldo(p.id) == Decimal('4.000')
        assert status_efetivo(chassi) == EVENTO_MONTADA
        db.session.rollback()


def test_usar_outra_moto_canibaliza_e_abre_falta_no_doador(app, admin_user):
    with app.app_context():
        recep = _uid('TSTR'); doad = _uid('TSTD')
        _moto(recep, admin_user); _moto(doad, admin_user)
        p = criar_peca(nome=_uid('PZ'), operador_id=admin_user.id)
        f = abrir_pendencia(chassi=recep, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='falta',
                            operador_id=admin_user.id)
        r = resolver_com_tratativa(pendencia_id=f.id, tratativa=PENDENCIA_TRATATIVA_USAR_OUTRA_MOTO,
                                   resolucao_descricao='canibalizada', operador_id=admin_user.id,
                                   peca_id=p.id, quantidade=1, chassi_doador=doad)
        db.session.flush()
        assert r['ok']
        from app.motos_assai.models import AssaiPendencia
        assert AssaiPendencia.query.filter_by(chassi=doad, peca_id=p.id).count() == 1
        db.session.rollback()


def test_usar_estoque_exige_peca_e_quantidade(app, admin_user):
    with app.app_context():
        chassi = _uid('TSTC')
        _moto(chassi, admin_user)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='falta',
                            operador_id=admin_user.id)
        with pytest.raises(ResolucaoError):
            resolver_com_tratativa(pendencia_id=f.id, tratativa=PENDENCIA_TRATATIVA_USAR_ESTOQUE,
                                   resolucao_descricao='x', operador_id=admin_user.id)
        db.session.rollback()


def test_saldo_insuficiente_nao_bloqueia_avisa(app, admin_user):
    with app.app_context():
        chassi = _uid('TSTE')
        _moto(chassi, admin_user)
        p = criar_peca(nome=_uid('PZ'), operador_id=admin_user.id)  # saldo 0
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='falta',
                            operador_id=admin_user.id)
        r = resolver_com_tratativa(pendencia_id=f.id, tratativa=PENDENCIA_TRATATIVA_USAR_ESTOQUE,
                                   resolucao_descricao='aplicada', operador_id=admin_user.id,
                                   peca_id=p.id, quantidade=1)
        db.session.flush()
        assert r['saldo_apos'] == Decimal('-1.000')  # negativo, sem travar
        db.session.rollback()
